import hashlib

from django.conf import settings
from django.db.models import Max, Min
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from chatbot.ai_client import AIProviderError
from core.permissions import IsSIKAPStaff

from .models import MirrorPDKI, CekMerekLog
from .serializers import (
    CekMerekAIResponseSerializer,
    CekMerekAISerializer,
    CekMerekLogSerializer,
    MirrorPDKISerializer,
)
from .services import (
    DISCLAIMER,
    classify_nice_classes,
    calculate_similarity_percentage,
    calculate_visual_percentage,
    determine_risk,
    find_similar_trademarks,
    generate_brand_advice,
    generate_image_embedding,
    validate_logo_upload,
)


def _get_client_ip_hash(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    if not ip:
        return ''
    return hashlib.sha256(f'{settings.SECRET_KEY}:{ip}'.encode('utf-8')).hexdigest()


class MirrorPDKIViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only: data ini di-populate lewat proses sinkronisasi/mirror dari
    PDKI (mis. management command terpisah), bukan lewat API publik.
    """
    queryset = MirrorPDKI.objects.all()
    serializer_class = MirrorPDKISerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

        results = self.get_queryset().filter(nama_merek__icontains=q)[:50]
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)


class CekMerekAIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'cek_merek'

    def cek(self, request):
        """
        POST /api/trademark/cek/
        Body: {"nama_merek": "...", "deskripsi_produk": "..."}
        """
        serializer = CekMerekAISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nama_merek = serializer.validated_data['nama_merek']
        deskripsi_produk = serializer.validated_data['deskripsi_produk']
        uploaded_logo = serializer.validated_data.get('logo_merek')
        selected_classes = serializer.validated_data.get('kelas_nice_dipilih')
        classification_evidence = []

        if selected_classes:
            kelas_nice = selected_classes
            classification_source = 'dipilih_pengguna'
        else:
            try:
                classification = classify_nice_classes(deskripsi_produk)
            except AIProviderError as exc:
                return Response(
                    {
                        'detail': (
                            'Gagal menghubungi provider AI untuk klasifikasi kelas Nice. '
                            'Pastikan konfigurasi provider AI di .env sudah benar.'
                        ),
                        'error': str(exc),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            # Compatibility for mocked/legacy integrations that still return a class list.
            if isinstance(classification, list):
                classification = {
                    'kelas': classification,
                    'opsi_kelas': [],
                    'perlu_klarifikasi': False,
                    'pertanyaan_klarifikasi': '',
                }
            if classification.get('perlu_klarifikasi'):
                return Response({
                    'perlu_klarifikasi': True,
                    'pertanyaan_klarifikasi': classification.get('pertanyaan_klarifikasi'),
                    'opsi_kelas': classification.get('opsi_kelas', []),
                    'detail': 'Deskripsi perlu dikonfirmasi sebelum pengecekan merek dilanjutkan.',
                }, status=status.HTTP_200_OK)
            kelas_nice = classification.get('kelas', [])
            classification_source = classification.get(
                'sumber_klasifikasi', 'analisis_ai',
            )
            classification_evidence = [
                option for option in classification.get('opsi_kelas', [])
                if option.get('kelas') in kelas_nice
            ]

        if not kelas_nice:
            return Response(
                {'detail': 'AI tidak berhasil menentukan kelas Nice dari deskripsi produk.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        query_visual_embedding = None
        if uploaded_logo:
            try:
                image_bytes, mime_type = validate_logo_upload(uploaded_logo)
                query_visual_embedding = generate_image_embedding(image_bytes, mime_type)
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except AIProviderError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        merek_mirip = find_similar_trademarks(
            nama_merek, kelas_nice, query_visual_embedding=query_visual_embedding,
        )
        for item in merek_mirip:
            if item.get('label_merek_url'):
                item['label_merek_url'] = request.build_absolute_uri(item['label_merek_url'])
        skor_risiko = determine_risk(merek_mirip)
        persentase_kemiripan = calculate_similarity_percentage(merek_mirip)
        persentase_visual = calculate_visual_percentage(merek_mirip)
        referensi_visual = sum(1 for item in merek_mirip if item.get('skor_visual') is not None)
        cakupan_data = _get_data_coverage(kelas_nice)
        metodologi = [
            'Nama dibandingkan setelah normalisasi tanda baca dan kata label umum.',
            'Pembanding dibatasi pada kelas Nice yang dipilih atau dikonfirmasi.',
            'Skor visual hanya dihitung jika pengguna mengunggah logo dan etiket pembanding tersedia.',
            'Hasil merupakan indikator penelusuran awal, bukan probabilitas keputusan pemeriksa DJKI.',
        ]

        try:
            saran_naratif = generate_brand_advice(
                nama_merek=nama_merek,
                deskripsi_produk=deskripsi_produk,
                kelas_nice=kelas_nice,
                similar_trademarks=merek_mirip,
                skor_risiko=skor_risiko,
            )
        except AIProviderError as exc:
            return Response(
                {
                    'detail': (
                        'Kelas Nice dan similarity berhasil dihitung, tetapi provider AI gagal '
                        'menyusun saran naratif.'
                    ),
                    'error': str(exc),
                    'kelas_nice_terdeteksi': kelas_nice,
                    'merek_mirip': merek_mirip,
                    'skor_risiko': skor_risiko,
                    'persentase_kemiripan': persentase_kemiripan,
                    'persentase_kemiripan_visual': persentase_visual,
                    'logo_dianalisis': bool(uploaded_logo),
                    'referensi_visual_dibandingkan': referensi_visual,
                    'disclaimer': DISCLAIMER,
                    'cakupan_data': cakupan_data,
                    'metodologi': metodologi,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        hasil_lengkap = {
            'kelas_nice_terdeteksi': kelas_nice,
            'merek_mirip': merek_mirip,
            'saran_naratif': saran_naratif,
            'disclaimer': DISCLAIMER,
            'persentase_kemiripan': persentase_kemiripan,
            'persentase_kemiripan_visual': persentase_visual,
            'logo_dianalisis': bool(uploaded_logo),
            'referensi_visual_dibandingkan': referensi_visual,
            'sumber_klasifikasi': classification_source,
            'bukti_klasifikasi': classification_evidence,
            'cakupan_data': cakupan_data,
            'metodologi': metodologi,
        }
        log = CekMerekLog.objects.create(
            nama_merek_diajukan=nama_merek,
            deskripsi_produk=deskripsi_produk,
            kelas_nice_terdeteksi=', '.join(kelas_nice),
            skor_risiko=skor_risiko,
            hasil_lengkap=hasil_lengkap,
            ip_hash=_get_client_ip_hash(request),
        )
        response = {
            'id': log.id,
            'kelas_nice_terdeteksi': kelas_nice,
            'merek_mirip': merek_mirip,
            'skor_risiko': skor_risiko,
            'persentase_kemiripan': persentase_kemiripan,
            'persentase_kemiripan_visual': persentase_visual,
            'logo_dianalisis': bool(uploaded_logo),
            'referensi_visual_dibandingkan': referensi_visual,
            'saran_naratif': saran_naratif,
            'disclaimer': DISCLAIMER,
            'sumber_klasifikasi': classification_source,
            'bukti_klasifikasi': classification_evidence,
            'cakupan_data': cakupan_data,
            'metodologi': metodologi,
        }
        return Response(CekMerekAIResponseSerializer(response).data, status=status.HTTP_201_CREATED)


def _get_data_coverage(kelas_nice):
    queryset = MirrorPDKI.objects.filter(kelas_nice__in=kelas_nice)
    dates = queryset.aggregate(
        publikasi_awal=Min('tanggal_publikasi'),
        publikasi_akhir=Max('tanggal_publikasi'),
        sinkron_terakhir=Max('tanggal_sinkron_terakhir'),
    )
    total = queryset.count()
    visual = queryset.exclude(visual_embedding=[]).count()
    labels = queryset.exclude(label_merek='').filter(label_merek__isnull=False).count()
    return {
        'kelas': [str(value) for value in kelas_nice],
        'total_pembanding_kelas': total,
        'etiket_tersedia': labels,
        'visual_siap_dibandingkan': visual,
        'cakupan_visual_persen': round((visual / total) * 100, 1) if total else 0,
        'publikasi_awal': dates['publikasi_awal'].isoformat() if dates['publikasi_awal'] else None,
        'publikasi_akhir': dates['publikasi_akhir'].isoformat() if dates['publikasi_akhir'] else None,
        'sinkron_terakhir': dates['sinkron_terakhir'].isoformat() if dates['sinkron_terakhir'] else None,
    }


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
