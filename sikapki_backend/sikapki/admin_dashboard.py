from types import MethodType
from datetime import datetime, time, timedelta

from django.contrib import admin
from django.db import DatabaseError
from django.db.models import Count
from django.utils import timezone


def configure_admin_dashboard():
    admin.site.site_header = 'SIKAP-KI NTB Admin'
    admin.site.site_title = 'SIKAP-KI NTB'
    admin.site.index_title = 'Dashboard Petugas'
    admin.site.index_template = 'admin/sikapki_index.html'

    original_each_context = admin.site.each_context

    def each_context_with_metrics(self, request):
        context = original_each_context(request)
        context['dashboard_metrics'] = get_dashboard_metrics()
        return context

    admin.site.each_context = MethodType(each_context_with_metrics, admin.site)


def get_dashboard_metrics():
    from chatbot.models import PercakapanChatbot
    from trademark.models import CekMerekLog

    today = timezone.localdate()
    start_today = timezone.make_aware(datetime.combine(today, time.min))
    start_week_date = today - timedelta(days=today.weekday())
    start_week = timezone.make_aware(datetime.combine(start_week_date, time.min))

    try:
        chatbot_today = PercakapanChatbot.objects.filter(dibuat_pada__gte=start_today).count()
        chatbot_week = PercakapanChatbot.objects.filter(dibuat_pada__gte=start_week).count()
        escalated_total = PercakapanChatbot.objects.filter(dieskalasi=True).count()
        escalated_open = PercakapanChatbot.objects.filter(dieskalasi=True, rating_membantu__isnull=True).count()
        cek_merek_today = CekMerekLog.objects.filter(dibuat_pada__gte=start_today).count()
        cek_merek_week = CekMerekLog.objects.filter(dibuat_pada__gte=start_week).count()
        risk_rows = CekMerekLog.objects.values('skor_risiko').annotate(total=Count('id'))
    except DatabaseError:
        return _empty_metrics()

    risk_distribution = {
        'rendah': 0,
        'sedang': 0,
        'tinggi': 0,
    }
    for row in risk_rows:
        risk_distribution[row['skor_risiko']] = row['total']

    return {
        'chatbot_today': chatbot_today,
        'chatbot_week': chatbot_week,
        'escalated_total': escalated_total,
        'escalated_open': escalated_open,
        'cek_merek_today': cek_merek_today,
        'cek_merek_week': cek_merek_week,
        'risk_distribution': risk_distribution,
    }


def _empty_metrics():
    return {
        'chatbot_today': 0,
        'chatbot_week': 0,
        'escalated_total': 0,
        'escalated_open': 0,
        'cek_merek_today': 0,
        'cek_merek_week': 0,
        'risk_distribution': {'rendah': 0, 'sedang': 0, 'tinggi': 0},
    }
