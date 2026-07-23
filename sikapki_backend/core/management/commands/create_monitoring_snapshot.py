from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import MonitoringSnapshot
from core.monitoring import build_monitoring_metrics


class Command(BaseCommand):
    help = 'Simpan bukti monitoring agregat untuk periode tertentu.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Jumlah hari termasuk hari ini.')
        parser.add_argument('--note', default='Snapshot monitoring berkala dari sistem.')

    def handle(self, *args, **options):
        days = options['days']
        if days < 1 or days > 366:
            raise CommandError('--days harus antara 1 dan 366.')
        end = timezone.localdate()
        start = end - timedelta(days=days - 1)
        snapshot = MonitoringSnapshot.objects.create(
            periode_mulai=start,
            periode_selesai=end,
            metrik=build_monitoring_metrics(start, end),
            catatan=options['note'],
        )
        self.stdout.write(self.style.SUCCESS(
            f'Snapshot #{snapshot.pk} tersimpan untuk {start} sampai {end}.',
        ))
