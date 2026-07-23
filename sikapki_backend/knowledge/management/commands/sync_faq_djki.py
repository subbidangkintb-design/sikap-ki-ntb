from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from knowledge.faq_sync import (
    FAQ_MEREK_URL, FAQSyncError, crawl_faq, load_saved_html, sync_faq_items,
)
from knowledge.models import SinkronisasiFAQLog


class Command(BaseCommand):
    help = 'Sinkronkan FAQ resmi DJKI per kategori sebagai draf yang wajib diverifikasi petugas.'

    def add_arguments(self, parser):
        parser.add_argument('--url', default=FAQ_MEREK_URL)
        parser.add_argument('--delay', type=float, default=1.0)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--html-file', help='Impor HTML resmi yang disimpan melalui browser.')
        parser.add_argument('--subcategory', help='Nama subkategori untuk mode --html-file.')
        parser.add_argument('--category', default='Merek', help='Nama KategoriKI tujuan.')

    def handle(self, *args, **options):
        if options['delay'] < 0.5 or options['delay'] > 30:
            raise CommandError('--delay harus antara 0.5 dan 30 detik.')
        try:
            if options['html_file']:
                items = load_saved_html(
                    options['html_file'], options['url'], options['subcategory'],
                )
                pages = {options['url']}
                full_sync = False
            else:
                items, pages = crawl_faq(options['url'], options['delay'])
                full_sync = True
            result = sync_faq_items(
                items, source_url=options['url'], full_sync=full_sync,
                dry_run=options['dry_run'], category_name=options['category'].strip(),
            )
        except (FAQSyncError, OSError, ValueError) as exc:
            SinkronisasiFAQLog.objects.create(
                sumber_url=options['url'],
                status=SinkronisasiFAQLog.Status.GAGAL,
                pesan=str(exc)[:2000],
                selesai_pada=timezone.now(),
            )
            raise CommandError(str(exc)) from exc

        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}{len(pages)} halaman; {result["ditemukan"]} FAQ ditemukan; '
            f'{result["baru"]} baru; {result["diperbarui"]} diperbarui; '
            f'{result["dinonaktifkan"]} dinonaktifkan.',
        ))
