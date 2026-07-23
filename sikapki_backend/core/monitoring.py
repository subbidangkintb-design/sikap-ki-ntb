from datetime import datetime, time

from django.db.models import Avg
from django.utils import timezone

from chatbot.models import PercakapanChatbot
from knowledge.models import DokumenResmi
from trademark.models import CekMerekLog, MirrorPDKI, SinkronisasiPDKILog

from .models import UjiCobaPengguna


def build_monitoring_metrics(periode_mulai, periode_selesai):
    start = timezone.make_aware(datetime.combine(periode_mulai, time.min))
    end = timezone.make_aware(datetime.combine(periode_selesai, time.max))
    conversations = PercakapanChatbot.objects.filter(dibuat_pada__range=(start, end))
    tests = UjiCobaPengguna.objects.filter(dibuat_pada__range=(start, end))
    checks = CekMerekLog.objects.filter(dibuat_pada__range=(start, end))
    now = timezone.now()
    overdue = conversations.filter(
        dieskalasi=True,
        batas_tindak_lanjut__lt=now,
    ).exclude(status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI)
    ratings = tests.aggregate(
        kemudahan=Avg('kemudahan'), kejelasan=Avg('kejelasan'),
        kepercayaan=Avg('kepercayaan'), kepuasan=Avg('kepuasan'),
    )
    return {
        'periode': {'mulai': str(periode_mulai), 'selesai': str(periode_selesai)},
        'layanan': {
            'chatbot': conversations.count(),
            'cek_merek': checks.count(),
            'eskalasi': conversations.filter(dieskalasi=True).count(),
            'eskalasi_selesai': conversations.filter(
                status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI,
            ).count(),
            'eskalasi_terlambat': overdue.count(),
            'feedback_membantu': conversations.filter(rating_membantu=True).count(),
        },
        'uji_pengguna': {
            'jumlah_responden': tests.count(),
            'tugas_berhasil': tests.filter(tugas_berhasil=True).count(),
            'rata_rata': {
                key: round(value, 2) if value is not None else None
                for key, value in ratings.items()
            },
        },
        'data': {
            'dokumen_terverifikasi': DokumenResmi.objects.filter(
                status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
            ).count(),
            'merek_pembanding': MirrorPDKI.objects.count(),
            'sinkronisasi_berhasil': SinkronisasiPDKILog.objects.filter(
                status=SinkronisasiPDKILog.Status.BERHASIL,
            ).count(),
            'sinkronisasi_gagal': SinkronisasiPDKILog.objects.filter(
                status=SinkronisasiPDKILog.Status.GAGAL,
            ).count(),
        },
        'dibuat_pada': timezone.now().isoformat(),
    }
