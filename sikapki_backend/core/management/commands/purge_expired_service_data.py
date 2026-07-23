from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from chatbot.models import PercakapanChatbot
from core.models import UjiCobaPengguna
from trademark.models import CekMerekLog


class Command(BaseCommand):
    help = 'Hapus log layanan yang melewati masa retensi; gunakan --dry-run lebih dahulu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int,
            default=getattr(settings, 'SERVICE_LOG_RETENTION_DAYS', 365),
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        days = options['days']
        if days < 30:
            raise CommandError('Masa retensi minimum adalah 30 hari.')
        cutoff = timezone.now() - timedelta(days=days)
        targets = {
            'percakapan': PercakapanChatbot.objects.filter(dibuat_pada__lt=cutoff),
            'cek_merek': CekMerekLog.objects.filter(dibuat_pada__lt=cutoff),
            'uji_pengguna': UjiCobaPengguna.objects.filter(dibuat_pada__lt=cutoff),
        }
        counts = {name: queryset.count() for name, queryset in targets.items()}
        self.stdout.write(f'Batas retensi: {cutoff.isoformat()}; kandidat: {counts}')
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN: tidak ada data yang dihapus.'))
            return
        with transaction.atomic():
            for queryset in targets.values():
                queryset.delete()
        self.stdout.write(self.style.SUCCESS('Data melewati retensi berhasil dihapus.'))
