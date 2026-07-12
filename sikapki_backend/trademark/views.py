from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from chatbot.ai_client import AIProviderError

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
    determine_risk,
    find_similar_trademarks,
    generate_brand_advice,
)


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


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

    def cek(self, request):
        """
        POST /api/trademark/cek/
        Body: {"nama_merek": "...", "deskripsi_produk": "..."}
        """
        serializer = CekMerekAISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nama_merek = serializer.validated_data['nama_merek']
        deskripsi_produk = serializer.validated_data['deskripsi_produk']

        try:
            kelas_nice = classify_nice_classes(deskripsi_produk)
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

        if not kelas_nice:
            return Response(
                {'detail': 'AI tidak berhasil menentukan kelas Nice dari deskripsi produk.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        merek_mirip = find_similar_trademarks(nama_merek, kelas_nice)
        skor_risiko = determine_risk(merek_mirip)

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
                    'disclaimer': DISCLAIMER,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        hasil_lengkap = {
            'kelas_nice_terdeteksi': kelas_nice,
            'merek_mirip': merek_mirip,
            'saran_naratif': saran_naratif,
            'disclaimer': DISCLAIMER,
        }
        log = CekMerekLog.objects.create(
            nama_merek_diajukan=nama_merek,
            deskripsi_produk=deskripsi_produk,
            kelas_nice_terdeteksi=', '.join(kelas_nice),
            skor_risiko=skor_risiko,
            hasil_lengkap=hasil_lengkap,
            ip_pengguna=_get_client_ip(request),
        )
        response = {
            'id': log.id,
            'kelas_nice_terdeteksi': kelas_nice,
            'merek_mirip': merek_mirip,
            'skor_risiko': skor_risiko,
            'saran_naratif': saran_naratif,
            'disclaimer': DISCLAIMER,
        }
        return Response(CekMerekAIResponseSerializer(response).data, status=status.HTTP_201_CREATED)


class CekMerekLogViewSet(viewsets.ModelViewSet):
    """
    Membuat entri log setiap kali pengguna mengecek risiko sebuah nama
    merek. `skor_risiko` dan `hasil_lengkap` dihitung otomatis di
    perform_create (logic penilaian AI/similarity sesungguhnya akan
    dipasang di sini nanti — untuk saat ini masih heuristik sederhana
    berbasis jumlah kecocokan nama).
    """
    queryset = CekMerekLog.objects.all()
    serializer_class = CekMerekLogSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        nama = serializer.validated_data.get('nama_merek_diajukan', '')
        mirip = MirrorPDKI.objects.filter(nama_merek__icontains=nama)
        jumlah_mirip = mirip.count()

        if jumlah_mirip == 0:
            skor = CekMerekLog.SkorRisiko.RENDAH
        elif jumlah_mirip <= 2:
            skor = CekMerekLog.SkorRisiko.SEDANG
        else:
            skor = CekMerekLog.SkorRisiko.TINGGI

        hasil_lengkap = {
            'jumlah_merek_mirip': jumlah_mirip,
            'contoh_merek_mirip': list(mirip.values_list('nama_merek', flat=True)[:5]),
        }

        serializer.save(
            skor_risiko=skor,
            hasil_lengkap=hasil_lengkap,
            ip_pengguna=_get_client_ip(self.request),
        )
