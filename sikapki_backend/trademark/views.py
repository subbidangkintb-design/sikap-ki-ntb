import hashlib
import uuid

from django.conf import settings
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from chatbot.ai_client import AIProviderError
from chatbot.models import PercakapanChatbot
from core.jobs import enqueue_job
from core.models import BackgroundJob
from core.permissions import IsSIKAPStaff

from .models import CekMerekLog, KlasifikasiMerekLog, MirrorPDKI
from .serializers import (
    CekMerekAIResponseSerializer,
    CekMerekAISerializer,
    CekMerekLogSerializer,
    EskalasiKelasSerializer,
    KlasifikasiMerekLogSerializer,
    MirrorPDKISerializer,
)
from .services import (
    DISCLAIMER,
    calculate_similarity_percentage,
    calculate_visual_percentage,
    classify_nice_classes,
    determine_risk,
    find_similar_trademarks,
    generate_image_embedding,
    validate_logo_upload,
)


KLASIFIKASI_DISCLAIMER = (
    'Rekomendasi ini hanya membantu memilih klasifikasi barang/jasa. Sistem tidak menilai '
    'kemiripan nama atau logo, daya pembeda, peluang diterima, maupun keputusan pemeriksa DJKI. '
    'Lakukan penelusuran resmi di PDKI dan konfirmasi uraian barang/jasa pada SKM DJKI.'
)
PDKI_URL = 'https://pdki-indonesia.dgip.go.id/'
SKM_URL = 'https://skm.dgip.go.id/'


def _get_client_ip_hash(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    if not ip:
        return ''
    return hashlib.sha256(f'{settings.SECRET_KEY}:{ip}'.encode('utf-8')).hexdigest()


def _consultation_code(percakapan):
    local_date = percakapan.dibuat_pada.astimezone().strftime('%Y%m%d')
    return f'KI-{local_date}-{percakapan.pk:06d}'


class MirrorPDKIViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only: data ini di-populate lewat proses sinkronisasi/mirror dari
    PDKI (mis. management command terpisah), bukan lewat API publik.
    """
    queryset = MirrorPDKI.objects.all()
    serializer_class = MirrorPDKISerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        query = params.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(nama_merek__icontains=query)
                | Q(nomor_permohonan__icontains=query)
                | Q(pemilik__icontains=query)
                | Q(uraian_barang_jasa__icontains=query)
            )
        for field in ('kelas_nice', 'status', 'sumber_data'):
            value = params.get(field, '').strip()
            if value:
                queryset = queryset.filter(**{field: value})
        if params.get('ada_uraian') == '1':
            queryset = queryset.exclude(uraian_barang_jasa='')
        if params.get('ada_nomor') == '1':
            queryset = queryset.exclude(nomor_permohonan='')
        if params.get('ada_etiket') == '1':
            queryset = queryset.exclude(label_merek='').exclude(label_merek__isnull=True)
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        GET /api/trademark/mirror-pdki/search/?q=<nama_merek>
        Pencarian sederhana berdasarkan kemiripan nama merek (icontains).
        Nanti bisa diganti/dilengkapi dengan similarity search berbasis AI.
        """
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'detail': 'Parameter "q" wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(nama_merek__icontains=q)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class CekMerekAIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'cek_merek'

    def fitur(self, request):
        """Konfigurasi publik non-sensitif untuk mengatur tampilan fitur."""
        return Response({
            'ai_cek_merek_aktif': settings.AI_TRADEMARK_CHECK_ENABLED,
        })

    def eskalasi_kelas(self, request):
        """Teruskan hasil Cek Kelas yang belum cukup kepada Helpdesk KI."""
        serializer = EskalasiKelasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sesi_id = data.get('sesi_id')
        rekomendasi = data.get('rekomendasi_kelas', [])[:10]
        kelas = ', '.join(
            str(item.get('kelas')) for item in rekomendasi if item.get('kelas')
        ) or 'belum teridentifikasi'
        brand_suffix = f" untuk merek {data['nama_merek']}" if data.get('nama_merek') else ''
        pertanyaan = (
            f'Permintaan bantuan Cek Kelas Merek{brand_suffix}.\n'
            f"Uraian barang/jasa: {data['deskripsi_produk']}\n"
            f'Kelas yang dianalisis sistem: {kelas}.'
        )
        percakapan = PercakapanChatbot.objects.create(
            sesi_id=sesi_id or uuid.uuid4(),
            pertanyaan=pertanyaan,
            jawaban=(
                'Permintaan Anda sudah diteruskan kepada Petugas Helpdesk KI. '
                'Petugas akan memeriksa uraian barang/jasa dan memberikan arahan awal '
                'berdasarkan sumber resmi yang tersedia.'
            ),
            sumber_dokumen=[
                {'tipe': 'cek_kelas', 'rekomendasi_kelas': rekomendasi},
            ],
            confidence_score=None,
            dieskalasi=True,
        )
        return Response({
            'kode_konsultasi': _consultation_code(percakapan),
            'pelacakan_id': percakapan.pelacakan_id,
            'status': percakapan.status_tindak_lanjut,
            'status_label': percakapan.get_status_tindak_lanjut_display(),
            'batas_tindak_lanjut': percakapan.batas_tindak_lanjut,
            'message': 'Konsultasi berhasil diteruskan kepada Petugas Helpdesk KI.',
        }, status=status.HTTP_201_CREATED)

    def cek(self, request):
        """
        POST /api/trademark/cek/
        Memberikan rekomendasi kelas dan istilah barang/jasa resmi.
        Endpoint ini tidak menilai kemiripan nama maupun logo.
        """
        serializer = CekMerekAISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nama_merek = serializer.validated_data['nama_merek']
        deskripsi_produk = serializer.validated_data['deskripsi_produk']
        uploaded_logo = serializer.validated_data.get('logo_merek')
        if serializer.validated_data.get('asinkron'):
            job = enqueue_job(
                BackgroundJob.Kind.CLASSIFICATION_AI,
                {
                    'nama_merek': nama_merek,
                    'deskripsi_produk': deskripsi_produk,
                    'logo_disertakan': bool(uploaded_logo),
                },
                created_by=request.user,
            )
            return Response(
                {'job_id': str(job.job_id), 'status': job.status, 'message': 'Klasifikasi masuk antrean.'},
                status=status.HTTP_202_ACCEPTED,
            )
        try:
            classification = classify_nice_classes(deskripsi_produk)
        except AIProviderError as exc:
            return Response(
                {
                    'detail': (
                        'Layanan klasifikasi belum dapat dihubungi. Periksa konfigurasi provider '
                        'AI dan pastikan data Nice Classification sudah tersinkron.'
                    ),
                    'error': str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if isinstance(classification, list):
            classification = {
                'opsi_kelas': [],
                'perlu_klarifikasi': not classification,
                'pertanyaan_klarifikasi': '',
                'sumber_klasifikasi': 'Nice Classification',
            }
        recommendations = classification.get('opsi_kelas', [])[:3]
        needs_clarification = bool(classification.get('perlu_klarifikasi'))
        question = classification.get('pertanyaan_klarifikasi', '')
        if not recommendations and not question:
            needs_clarification = True
            question = (
                'Mohon jelaskan jenis barang atau jasa, fungsi utamanya, siapa penggunanya, '
                'dan apakah Anda memproduksi, menjual, atau memberikan layanan.'
            )

        log = KlasifikasiMerekLog.objects.create(
            nama_merek_diajukan=nama_merek,
            deskripsi_produk=deskripsi_produk,
            rekomendasi_kelas=recommendations,
            perlu_klarifikasi=needs_clarification,
            logo_disertakan=bool(uploaded_logo),
            ip_hash=_get_client_ip_hash(request),
        )
        response = {
            'id': log.id,
            'nama_merek': nama_merek,
            'rekomendasi_kelas': recommendations,
            'perlu_klarifikasi': needs_clarification,
            'pertanyaan_klarifikasi': question,
            'logo_dinilai': False,
            'disclaimer': KLASIFIKASI_DISCLAIMER,
            'sumber_klasifikasi': classification.get(
                'sumber_klasifikasi', 'Nice Classification',
            ),
            'tautan_resmi': {
                'pdki': PDKI_URL,
                'skm': SKM_URL,
                'helpdesk': '/chatbot',
            },
            'langkah_selanjutnya': [
                'Tinjau kelas dan istilah barang/jasa yang paling sesuai dengan kegiatan Anda.',
                'Konfirmasi uraian barang/jasa melalui SKM DJKI.',
                'Lakukan penelusuran nama dan logo secara resmi melalui PDKI.',
                'Hubungi petugas Helpdesk KI Kanwil Kementerian Hukum NTB jika masih ragu.',
            ],
            'rangkaian_kelas': classification.get('rangkaian_kelas', []),
        }
        return Response(CekMerekAIResponseSerializer(response).data, status=status.HTTP_201_CREATED)

    def cek_kemiripan(self, request):
        """Fitur opsional penelusuran awal terhadap data pembanding lokal."""
        if not settings.AI_TRADEMARK_CHECK_ENABLED:
            return Response(
                {'detail': 'Fitur AI Cek Merek sedang dinonaktifkan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CekMerekAISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nama_merek = serializer.validated_data['nama_merek']
        deskripsi_produk = serializer.validated_data['deskripsi_produk']
        uploaded_logo = serializer.validated_data.get('logo_merek')

        try:
            classification = classify_nice_classes(deskripsi_produk)
        except AIProviderError as exc:
            return Response(
                {'detail': 'Klasifikasi kelas belum dapat diproses.', 'error': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if isinstance(classification, list):
            class_options = [str(value) for value in classification]
            needs_clarification = False
            clarification_question = ''
        else:
            class_options = [
                str(item.get('kelas'))
                for item in classification.get('opsi_kelas', [])[:3]
                if item.get('kelas')
            ]
            if not class_options:
                class_options = [str(value) for value in classification.get('kelas', [])]
            needs_clarification = bool(classification.get('perlu_klarifikasi'))
            clarification_question = classification.get('pertanyaan_klarifikasi', '')

        if not class_options:
            return Response({
                'perlu_klarifikasi': True,
                'pertanyaan_klarifikasi': clarification_question or (
                    'Jelaskan lebih rinci bentuk, fungsi, dan cara produk atau jasa disediakan.'
                ),
                'detail': 'Kelas perlu dipastikan sebelum penelusuran pembanding dilakukan.',
            }, status=status.HTTP_200_OK)

        query_visual_embedding = None
        if uploaded_logo:
            try:
                image_bytes, mime_type = validate_logo_upload(uploaded_logo)
                query_visual_embedding = generate_image_embedding(image_bytes, mime_type)
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except AIProviderError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        candidates = find_similar_trademarks(
            nama_merek,
            class_options,
            query_visual_embedding=query_visual_embedding,
            goods_services_description=deskripsi_produk,
        )
        for item in candidates:
            if item.get('label_merek_url'):
                item['label_merek_url'] = request.build_absolute_uri(item['label_merek_url'])

        attention_level = determine_risk(candidates)
        highest_indicator = calculate_similarity_percentage(candidates)
        highest_visual = calculate_visual_percentage(candidates)
        visual_references = sum(
            1 for item in candidates if item.get('skor_visual') is not None
        )
        coverage_queryset = MirrorPDKI.objects.filter(kelas_nice__in=class_options)
        coverage = {
            'total_data_kelas': coverage_queryset.count(),
            'nomor_permohonan_tersedia': coverage_queryset.exclude(
                nomor_permohonan='',
            ).count(),
            'uraian_barang_jasa_tersedia': coverage_queryset.exclude(
                uraian_barang_jasa='',
            ).count(),
            'etiket_tersedia': coverage_queryset.exclude(
                label_merek='',
            ).filter(label_merek__isnull=False).count(),
        }
        result = {
            'kelas_nice_dianalisis': class_options,
            'kandidat_pembanding': candidates,
            'tingkat_perhatian': attention_level,
            'indikator_tertinggi': highest_indicator,
            'indikator_visual_tertinggi': highest_visual,
            'logo_dianalisis': bool(uploaded_logo),
            'referensi_visual_dibandingkan': visual_references,
            'cakupan_data': coverage,
            'perlu_klarifikasi_kelas': needs_clarification,
            'pertanyaan_klarifikasi': clarification_question,
            'disclaimer': DISCLAIMER,
            'tautan_pdki': PDKI_URL,
        }
        log = CekMerekLog.objects.create(
            nama_merek_diajukan=nama_merek,
            deskripsi_produk=deskripsi_produk,
            kelas_nice_terdeteksi=', '.join(class_options),
            skor_risiko=attention_level,
            hasil_lengkap=result,
            ip_hash=_get_client_ip_hash(request),
        )
        return Response({'id': log.id, **result}, status=status.HTTP_201_CREATED)


class CekMerekLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Membuat entri log setiap kali pengguna mengecek risiko sebuah nama
    merek. `skor_risiko` dan `hasil_lengkap` dihitung otomatis di
    perform_create (logic penilaian AI/similarity sesungguhnya akan
    dipasang di sini nanti — untuk saat ini masih heuristik sederhana
    berbasis jumlah kecocokan nama).
    """
    queryset = CekMerekLog.objects.all()
    serializer_class = CekMerekLogSerializer
    permission_classes = [IsSIKAPStaff]


class KlasifikasiMerekLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Riwayat anonim rekomendasi klasifikasi untuk petugas."""

    queryset = KlasifikasiMerekLog.objects.all()
    serializer_class = KlasifikasiMerekLogSerializer
    permission_classes = [IsSIKAPStaff]
