from django.core.management.base import BaseCommand

from trademark.models import MirrorPDKI
from trademark.services import build_visual_embedding_for_reference


class Command(BaseCommand):
    help = 'Membuat ulang embedding visual untuk etiket referensi Mirror PDKI.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Indeks ulang data yang sudah memiliki embedding.')

    def handle(self, *args, **options):
        queryset = MirrorPDKI.objects.exclude(label_merek='')
        if not options['force']:
            queryset = queryset.filter(visual_embedding=[])
        success = 0
        failed = 0
        for record in queryset.iterator():
            try:
                build_visual_embedding_for_reference(record)
                success += 1
                self.stdout.write(self.style.SUCCESS(f'OK: {record.nama_merek}'))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f'Gagal {record.nama_merek}: {exc}'))
        self.stdout.write(f'Selesai. Berhasil: {success}; gagal: {failed}.')
