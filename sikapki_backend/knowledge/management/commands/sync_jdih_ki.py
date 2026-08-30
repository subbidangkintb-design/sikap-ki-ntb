from django.core.management.base import BaseCommand, CommandError

from knowledge.jdih_sync import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_INDEX_URL,
    JDIHSyncError,
    discover_jdih_candidates,
    import_jdih_candidates,
    load_jdih_manifest,
)


class Command(BaseCommand):
    help = (
        'Temukan dokumen JDIH yang relevan dengan KI dan simpan sebagai '
        'draf yang wajib diverifikasi petugas.'
    )

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group()
        source.add_argument(
            '--index-url', default=DEFAULT_INDEX_URL,
            help='URL halaman indeks JDIH (default: portal yang diberikan).',
        )
        source.add_argument(
            '--manifest-file',
            help='Manifest JSON lokal untuk portal yang memblokir crawler.',
        )
        parser.add_argument('--category', help='Batasi satu kategori KI, misalnya Merek.')
        parser.add_argument('--max-pages', type=int, default=30)
        parser.add_argument('--max-documents', type=int, default=100)
        parser.add_argument('--max-depth', type=int, default=2)
        parser.add_argument('--delay', type=float, default=1.0)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--refresh-verified', action='store_true',
            help='Perbarui dokumen terverifikasi jika konten sumber berubah.',
        )
        parser.add_argument(
            '--allow-host', action='append', dest='allow_hosts',
            help='Tambahkan host JDIH yang diizinkan (boleh diulang).',
        )

    def handle(self, *args, **options):
        if options['max_pages'] < 1 or options['max_pages'] > 200:
            raise CommandError('--max-pages harus antara 1 dan 200.')
        if options['max_documents'] < 1 or options['max_documents'] > 1000:
            raise CommandError('--max-documents harus antara 1 dan 1000.')
        if options['max_depth'] < 0 or options['max_depth'] > 5:
            raise CommandError('--max-depth harus antara 0 dan 5.')
        if options['delay'] < 0.5 or options['delay'] > 30:
            raise CommandError('--delay harus antara 0.5 dan 30 detik.')

        allowed_hosts = set(DEFAULT_ALLOWED_HOSTS)
        allowed_hosts.update(
            host.strip().lower().split(':', 1)[0]
            for host in (options.get('allow_hosts') or [])
            if host.strip()
        )
        try:
            if options.get('manifest_file'):
                candidates = load_jdih_manifest(
                    options['manifest_file'], allowed_hosts=allowed_hosts,
                )
                visited = set()
            else:
                candidates, visited = discover_jdih_candidates(
                    options['index_url'],
                    delay=options['delay'],
                    max_pages=options['max_pages'],
                    max_documents=options['max_documents'],
                    max_depth=options['max_depth'],
                    allowed_hosts=allowed_hosts,
                )
        except (JDIHSyncError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        category_filter = (options.get('category') or '').strip()
        selected = [
            candidate for candidate in candidates
            if not category_filter or candidate.category.lower() == category_filter.lower()
        ][:options['max_documents']]
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(
            f'{prefix}{len(visited)} halaman diperiksa; {len(selected)} kandidat KI ditemukan.',
        )
        for candidate in selected:
            status = f' [{candidate.status}]' if candidate.status else ''
            self.stdout.write(f'- {candidate.category}: {candidate.title}{status}\n  {candidate.url}')

        result = import_jdih_candidates(
            selected,
            dry_run=options['dry_run'],
            category_filter=category_filter,
            refresh_verified=options['refresh_verified'],
        )
        if options['dry_run']:
            return
        self.stdout.write(self.style.SUCCESS(
            'Selesai: '
            f'baru={result["baru"]}, diperbarui={result["diperbarui"]}, '
            f'tetap={result["tetap"]}, dilewati={result["dilewati"]}, gagal={result["gagal"]}. '
            'Semua dokumen baru/berubah tetap berstatus draf.',
        ))
        if result['errors']:
            for error in result['errors']:
                self.stderr.write(self.style.WARNING(error))
            raise CommandError(f'{result["gagal"]} dokumen gagal diimpor.')
