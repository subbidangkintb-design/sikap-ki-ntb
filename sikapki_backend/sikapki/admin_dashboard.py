from types import MethodType
from datetime import datetime, time, timedelta

from django.contrib import admin
from django.core.cache import cache
from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone


def configure_admin_dashboard():
    admin.site.site_header = 'SIKAP-KI NTB Admin'
    admin.site.site_title = 'SIKAP-KI NTB'
    admin.site.index_title = 'Dashboard Petugas'
    admin.site.index_template = 'admin/sikapki_index.html'

    original_each_context = admin.site.each_context

    def each_context_with_metrics(self, request):
        context = original_each_context(request)
        admin_index_path = reverse('admin:index').rstrip('/')
        if request.path.rstrip('/') == admin_index_path:
            context['dashboard_metrics'] = cache.get_or_set(
                'sikapki-admin-dashboard-metrics', get_dashboard_metrics, 20,
            )
        else:
            context['dashboard_metrics'] = {}
        hostname = request.get_host().split(':', 1)[0]
        context['sikap_frontend_url'] = f'{request.scheme}://{hostname}:5173'
        return context

    admin.site.each_context = MethodType(each_context_with_metrics, admin.site)


def get_dashboard_metrics():
    from chatbot.models import PercakapanChatbot
    from core.models import MonitoringSnapshot, SlaNotification, UjiCobaPengguna
    from knowledge.models import DokumenResmi, FAQ
    from trademark.models import KlasifikasiMerekLog

    today = timezone.localdate()
    start_today = timezone.make_aware(datetime.combine(today, time.min))
    start_week_date = today - timedelta(days=today.weekday())
    start_week = timezone.make_aware(datetime.combine(start_week_date, time.min))

    try:
        chatbot_today = PercakapanChatbot.objects.filter(dibuat_pada__gte=start_today).count()
        chatbot_week = PercakapanChatbot.objects.filter(dibuat_pada__gte=start_week).count()
        escalated_total = PercakapanChatbot.objects.filter(dieskalasi=True).count()
        escalated_waiting = PercakapanChatbot.objects.filter(
            dieskalasi=True,
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.MENUNGGU,
        ).count()
        escalated_processing = PercakapanChatbot.objects.filter(
            dieskalasi=True,
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.DIPROSES,
        ).count()
        escalated_resolved = PercakapanChatbot.objects.filter(
            dieskalasi=True,
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI,
        ).count()
        escalated_open = escalated_waiting + escalated_processing
        escalated_overdue = PercakapanChatbot.objects.filter(
            dieskalasi=True, batas_tindak_lanjut__lt=timezone.now(),
        ).exclude(status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI).count()
        cek_merek_today = KlasifikasiMerekLog.objects.filter(
            dibuat_pada__gte=start_today,
        ).count()
        cek_merek_week = KlasifikasiMerekLog.objects.filter(
            dibuat_pada__gte=start_week,
        ).count()
        klasifikasi_perlu_klarifikasi = KlasifikasiMerekLog.objects.filter(
            perlu_klarifikasi=True,
        ).count()
        documents_verified = DokumenResmi.objects.filter(
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
        ).count()
        documents_queued = DokumenResmi.objects.filter(
            status_indexing__in=[
                DokumenResmi.StatusIndexing.MENUNGGU,
                DokumenResmi.StatusIndexing.DIPROSES,
            ],
        ).count()
        documents_failed = DokumenResmi.objects.filter(
            status_indexing=DokumenResmi.StatusIndexing.GAGAL,
        ).count()
        faq_drafts = FAQ.objects.filter(status_validasi=FAQ.StatusValidasi.DRAF).count()
        faq_verified = FAQ.objects.filter(
            status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
            aktif_sumber=True,
        ).count()
        user_tests = UjiCobaPengguna.objects.count()
        snapshots = MonitoringSnapshot.objects.count()
        unread_sla_notifications = SlaNotification.objects.filter(read_at__isnull=True).count()
    except DatabaseError:
        return _empty_metrics()

    return {
        'chatbot_today': chatbot_today,
        'chatbot_week': chatbot_week,
        'escalated_total': escalated_total,
        'escalated_open': escalated_open,
        'escalated_waiting': escalated_waiting,
        'escalated_processing': escalated_processing,
        'escalated_resolved': escalated_resolved,
        'escalated_overdue': escalated_overdue,
        'cek_merek_today': cek_merek_today,
        'cek_merek_week': cek_merek_week,
        'klasifikasi_perlu_klarifikasi': klasifikasi_perlu_klarifikasi,
        'documents_verified': documents_verified,
        'documents_queued': documents_queued,
        'documents_failed': documents_failed,
        'faq_drafts': faq_drafts,
        'faq_verified': faq_verified,
        'user_tests': user_tests,
        'snapshots': snapshots,
        'unread_sla_notifications': unread_sla_notifications,
    }


def _empty_metrics():
    return {
        'chatbot_today': 0,
        'chatbot_week': 0,
        'escalated_total': 0,
        'escalated_open': 0,
        'escalated_waiting': 0,
        'escalated_processing': 0,
        'escalated_resolved': 0,
        'escalated_overdue': 0,
        'cek_merek_today': 0,
        'cek_merek_week': 0,
        'klasifikasi_perlu_klarifikasi': 0,
        'documents_verified': 0,
        'documents_queued': 0,
        'documents_failed': 0,
        'faq_drafts': 0,
        'faq_verified': 0,
        'user_tests': 0,
        'snapshots': 0,
        'unread_sla_notifications': 0,
    }
