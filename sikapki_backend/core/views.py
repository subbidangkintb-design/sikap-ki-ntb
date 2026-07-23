from datetime import timedelta
import hashlib

from django.conf import settings
from django.db import connection
from django.db.models import Avg, Count, F, Max, Min, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import MonitoringSnapshot, UjiCobaPengguna
from .serializers import UjiCobaPenggunaSerializer, UserSerializer

from chatbot.models import PercakapanChatbot
from knowledge.models import DokumenResmi, FAQ, SinkronisasiFAQLog
from trademark.models import CekMerekLog, MirrorPDKI, SinkronisasiPDKILog


class MeView(APIView):
    """
    GET /api/core/me/  -> data user yang sedang login.
    Berguna untuk frontend React mengecek status login & role user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class StatistikLayananView(APIView):
    """Public aggregate statistics; never exposes individual service logs."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            period_days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            period_days = 7
        if period_days not in {7, 30, 90}:
            period_days = 7
        risk_rows = CekMerekLog.objects.values('skor_risiko').annotate(total=Count('id'))
        risk_distribution = {
            row['skor_risiko']: row['total']
            for row in risk_rows
        }
        chatbot_total = PercakapanChatbot.objects.count()
        escalated_total = PercakapanChatbot.objects.filter(dieskalasi=True).count()
        escalation_status = {
            row['status_tindak_lanjut']: row['total']
            for row in PercakapanChatbot.objects.filter(dieskalasi=True)
            .values('status_tindak_lanjut').annotate(total=Count('id'))
        }
        helpful_total = PercakapanChatbot.objects.filter(rating_membantu=True).count()
        unhelpful_total = PercakapanChatbot.objects.filter(rating_membantu=False).count()
        rated_total = helpful_total + unhelpful_total
        today = timezone.localdate()
        first_day = today - timedelta(days=period_days - 1)
        chatbot_daily = {
            row['day']: row['total']
            for row in PercakapanChatbot.objects.filter(dibuat_pada__date__gte=first_day)
            .annotate(day=TruncDate('dibuat_pada')).values('day').annotate(total=Count('id'))
        }
        trademark_daily = {
            row['day']: row['total']
            for row in CekMerekLog.objects.filter(dibuat_pada__date__gte=first_day)
            .annotate(day=TruncDate('dibuat_pada')).values('day').annotate(total=Count('id'))
        }
        activity_trend = [
            {
                'tanggal': first_day + timedelta(days=offset),
                'chatbot': chatbot_daily.get(first_day + timedelta(days=offset), 0),
                'cek_merek': trademark_daily.get(first_day + timedelta(days=offset), 0),
            }
            for offset in range(period_days)
        ]
        last_sync = SinkronisasiPDKILog.objects.filter(
            status=SinkronisasiPDKILog.Status.BERHASIL,
        ).first()
        latest_bulletin_log = SinkronisasiPDKILog.objects.filter(
            status=SinkronisasiPDKILog.Status.BERHASIL,
            sumber=MirrorPDKI.SumberData.BRM_DJKI,
        ).order_by('-sumber_url').first()
        now = timezone.now()
        overdue_total = PercakapanChatbot.objects.filter(
            dieskalasi=True, batas_tindak_lanjut__lt=now,
        ).exclude(status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI).count()
        completed = PercakapanChatbot.objects.filter(
            dieskalasi=True,
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI,
            diselesaikan_pada__isnull=False,
        )
        completed_with_sla = completed.filter(batas_tindak_lanjut__isnull=False)
        completed_on_time = completed_with_sla.filter(
            diselesaikan_pada__lte=F('batas_tindak_lanjut'),
        ).count()
        completed_sla_total = completed_with_sla.count()
        average_duration = completed.aggregate(
            value=Avg(F('diselesaikan_pada') - F('dibuat_pada')),
        )['value']
        user_test = UjiCobaPengguna.objects.aggregate(
            total=Count('id'), berhasil=Count('id', filter=Q(tugas_berhasil=True)),
            kepuasan=Avg('kepuasan'), kemudahan=Avg('kemudahan'),
        )
        brm_range = MirrorPDKI.objects.filter(
            sumber_data=MirrorPDKI.SumberData.BRM_DJKI,
        ).aggregate(awal=Min('tanggal_publikasi'), akhir=Max('tanggal_publikasi'))
        latest_snapshot = MonitoringSnapshot.objects.first()
        latest_faq_sync = SinkronisasiFAQLog.objects.first()

        return Response({
            'cek_merek_total': CekMerekLog.objects.count(),
            'chatbot_total': chatbot_total,
            'faq_total': FAQ.objects.filter(
                status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
                aktif_sumber=True,
            ).count(),
            'faq_djki_total': FAQ.objects.filter(
                status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
                aktif_sumber=True,
            ).exclude(sumber_url='').count(),
            'sinkronisasi_faq_terakhir': ({
                'status': latest_faq_sync.status,
                'ditemukan': latest_faq_sync.jumlah_ditemukan,
                'selesai_pada': latest_faq_sync.selesai_pada,
            } if latest_faq_sync else None),
            'dokumen_terverifikasi_total': DokumenResmi.objects.filter(
                status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
            ).count(),
            'mirror_merek_total': MirrorPDKI.objects.count(),
            'mirror_berita_resmi_total': MirrorPDKI.objects.filter(
                sumber_data=MirrorPDKI.SumberData.BRM_DJKI,
            ).count(),
            'mirror_etiket_total': MirrorPDKI.objects.exclude(label_merek='').filter(
                label_merek__isnull=False,
            ).count(),
            'mirror_visual_siap_total': MirrorPDKI.objects.exclude(visual_embedding=[]).count(),
            'sinkronisasi_merek_terakhir': last_sync.selesai_pada if last_sync else None,
            'sumber_sinkronisasi_merek': (
                latest_bulletin_log.judul_sumber if latest_bulletin_log else None
            ),
            'chatbot_terjawab_total': max(chatbot_total - escalated_total, 0),
            'chatbot_diarahkan_helpdesk_total': escalated_total,
            'eskalasi': {
                'menunggu': escalation_status.get(
                    PercakapanChatbot.StatusTindakLanjut.MENUNGGU, 0,
                ),
                'diproses': escalation_status.get(
                    PercakapanChatbot.StatusTindakLanjut.DIPROSES, 0,
                ),
                'selesai': escalation_status.get(
                    PercakapanChatbot.StatusTindakLanjut.SELESAI, 0,
                ),
                'melewati_sla': overdue_total,
                'kepatuhan_sla_persen': round(
                    (completed_on_time / completed_sla_total) * 100,
                ) if completed_sla_total else 0,
                'rata_rata_jam_tindak_lanjut': round(
                    average_duration.total_seconds() / 3600, 1,
                ) if average_duration else 0,
            },
            'feedback': {
                'membantu': helpful_total,
                'tidak_membantu': unhelpful_total,
                'tingkat_membantu': round((helpful_total / rated_total) * 100) if rated_total else 0,
            },
            'tren_7_hari': activity_trend,
            'tren_periode': activity_trend,
            'periode_hari': period_days,
            'sinkronisasi': {
                'berhasil': SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.BERHASIL,
                ).count(),
                'gagal': SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.GAGAL,
                ).count(),
                'berjalan': SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.BERJALAN,
                ).count(),
                'cakupan_awal': brm_range['awal'],
                'cakupan_akhir': brm_range['akhir'],
            },
            'uji_pengguna': {
                'responden': user_test['total'] or 0,
                'tugas_berhasil': user_test['berhasil'] or 0,
                'rata_rata_kepuasan': round(user_test['kepuasan'] or 0, 2),
                'rata_rata_kemudahan': round(user_test['kemudahan'] or 0, 2),
            },
            'monitoring_terakhir': ({
                'periode_mulai': latest_snapshot.periode_mulai,
                'periode_selesai': latest_snapshot.periode_selesai,
                'dibuat_pada': latest_snapshot.dibuat_pada,
            } if latest_snapshot else None),
            'risiko': {
                'rendah': risk_distribution.get(CekMerekLog.SkorRisiko.RENDAH, 0),
                'sedang': risk_distribution.get(CekMerekLog.SkorRisiko.SEDANG, 0),
                'tinggi': risk_distribution.get(CekMerekLog.SkorRisiko.TINGGI, 0),
            },
            'diperbarui_pada': timezone.now(),
            'cakupan': (
                'Aktivitas agregat pada portal SIKAP-KI NTB dan data pembanding dari '
                'publikasi resmi DJKI yang telah tersinkron, bukan statistik seluruh '
                'permohonan KI di NTB maupun salinan lengkap PDKI.'
            ),
        })


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        database_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            database_ok = False

        stale_sync = None
        verified_documents = None
        comparison_data = None
        if database_ok:
            try:
                stale_limit = timezone.now() - timedelta(hours=2)
                stale_sync = SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.BERJALAN,
                    dimulai_pada__lt=stale_limit,
                ).count()
                verified_documents = DokumenResmi.objects.filter(
                    status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
                ).count()
                comparison_data = MirrorPDKI.objects.count()
            except Exception:
                database_ok = False
        ai_provider = getattr(settings, 'AI_PROVIDER', '')
        ai_configured = bool(
            (ai_provider == 'gemini' and getattr(settings, 'GEMINI_API_KEY', ''))
            or (ai_provider == 'deepseek' and getattr(settings, 'DEEPSEEK_API_KEY', ''))
            or ai_provider == 'ollama'
        )
        healthy = database_ok and ai_configured and stale_sync == 0
        return Response({
            'status': 'sehat' if healthy else 'perlu_perhatian',
            'database': database_ok,
            'ai_provider': ai_provider,
            'ai_terkonfigurasi': ai_configured,
            'dokumen_terverifikasi': verified_documents,
            'data_pembanding': comparison_data,
            'sinkronisasi_stale': stale_sync,
            'diperiksa_pada': timezone.now(),
        }, status=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE)


class UjiCobaPenggunaView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'uji_pengguna'

    def post(self, request):
        serializer = UjiCobaPenggunaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        remote = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
        ip_hash = hashlib.sha256(
            f'{settings.SECRET_KEY}:{remote}'.encode('utf-8'),
        ).hexdigest() if remote else ''
        instance = serializer.save(ip_hash=ip_hash)
        return Response(
            UjiCobaPenggunaSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )
