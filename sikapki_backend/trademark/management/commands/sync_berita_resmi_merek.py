import time
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from core.jobs import enqueue_job
from core.models import BackgroundJob
from trademark.models import MirrorPDKI, SinkronisasiPDKILog
from trademark.pdki_sync import (
    PDKISyncError,
    discover_bulletin_urls,
    download_bulletin,
    parse_bulletin,
    sync_bulletin,
)


class Command(BaseCommand):
    help = 'Sinkronkan data tekstual merek dari PDF Berita Resmi Merek DJKI.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1, help='Jumlah publikasi terbaru yang diperiksa (default: 1).')
        parser.add_argument('--all', action='store_true', help='Periksa seluruh arsip publikasi yang tersedia.')
        parser.add_argument(
            '--batch-size', type=int, default=20,
            help='Maksimum publikasi baru per eksekusi mode --all (default: 20).',
        )
        parser.add_argument(
            '--delay', type=float, default=1.0,
            help='Jeda antarpublikasi dalam detik untuk menjaga beban server DJKI.',
        )
        parser.add_argument('--force', action='store_true', help='Proses ulang publikasi yang sudah berhasil.')
        parser.add_argument('--dry-run', action='store_true', help='Unduh dan validasi parser tanpa menyimpan data.')
        parser.add_argument('--url', help='Proses satu URL PDF DJKI tertentu.')
        parser.add_argument(
            '--without-labels', action='store_true',
            help='Sinkronkan data tekstual saja tanpa mengekstrak etiket.',
        )
        parser.add_argument(
            '--enrich-details', action='store_true',
            help=(
                'Proses publikasi yang uraian barang/jasanya masih kosong. '
                'Gunakan --batch-size untuk membatasi satu eksekusi.'
            ),
        )
        parser.add_argument(
            '--enqueue', action='store_true',
            help='Masukkan pekerjaan pengayaan ke worker tanpa mengunduh PDF pada request ini.',
        )

    def handle(self, *args, **options):
        stale_limit = timezone.now() - timedelta(hours=2)
        stale_logs = SinkronisasiPDKILog.objects.filter(
            status=SinkronisasiPDKILog.Status.BERJALAN,
            dimulai_pada__lt=stale_limit,
        )
        stale_count = stale_logs.update(
            status=SinkronisasiPDKILog.Status.GAGAL,
            selesai_pada=timezone.now(),
            pesan='Proses sebelumnya terhenti atau melewati batas 2 jam; dijadwalkan ulang.',
        )
        if stale_count:
            self.stdout.write(self.style.WARNING(
                f'{stale_count} log sinkronisasi stale ditandai gagal agar dapat diproses ulang.',
            ))
        limit = options['limit']
        if options['enqueue'] and not options['enrich_details']:
            raise CommandError('--enqueue hanya dapat digunakan bersama --enrich-details.')
        if options['enrich_details'] and (options['all'] or options['url'] or options['dry_run']):
            raise CommandError(
                '--enrich-details tidak dapat digabungkan dengan --all, --url, atau --dry-run.',
            )
        if not options['all'] and (limit < 1 or limit > 20):
            raise CommandError('--limit harus antara 1 dan 20 untuk menjaga beban sumber resmi.')
        if options['all'] and options['url']:
            raise CommandError('--all tidak dapat digabungkan dengan --url.')
        if options['all'] and options['dry_run']:
            raise CommandError('--dry-run tidak dapat digabungkan dengan --all.')
        if options['all'] and not options['without_labels']:
            raise CommandError(
                'Mode --all wajib memakai --without-labels agar arsip penuh tidak menghabiskan '
                'beberapa GB penyimpanan lokal.',
            )
        if options['batch_size'] < 1 or options['batch_size'] > 2000:
            raise CommandError('--batch-size harus antara 1 dan 2000.')
        if options['delay'] < 0 or options['delay'] > 30:
            raise CommandError('--delay harus antara 0 dan 30 detik.')
        try:
            if options['enrich_details']:
                enriched_urls = SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.BERHASIL,
                    pesan__contains='detail uraian dibaca',
                ).values_list('sumber_url', flat=True)
                urls = list(
                    MirrorPDKI.objects.filter(
                        sumber_data=MirrorPDKI.SumberData.BRM_DJKI,
                        uraian_barang_jasa='',
                    ).exclude(sumber_data_url='').exclude(
                        sumber_data_url__in=enriched_urls,
                    ).values_list(
                        'sumber_data_url', flat=True,
                    ).distinct()[:options['batch_size']]
                )
                self.stdout.write(
                    f'Batch pengayaan detail: {len(urls)} publikasi; etiket tidak diproses ulang.',
                )
                if not urls:
                    self.stdout.write(self.style.SUCCESS(
                        'Seluruh data BRM yang ditemukan sudah memiliki uraian barang/jasa.',
                    ))
                    return
                if options['enqueue']:
                    created = 0
                    pending = list(BackgroundJob.objects.filter(
                        kind=BackgroundJob.Kind.BRM_ENRICH,
                        status__in=[BackgroundJob.Status.QUEUED, BackgroundJob.Status.RUNNING],
                    ).only('payload'))
                    for url in urls:
                        if any((job.payload or {}).get('url') == url for job in pending):
                            continue
                        enqueue_job(BackgroundJob.Kind.BRM_ENRICH, {'url': url})
                        created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'{created} job pengayaan BRM masuk antrean background worker.',
                    ))
                    return
            else:
                discovery_limit = 100_000 if options['all'] else limit
                urls = [options['url']] if options['url'] else discover_bulletin_urls(
                    limit=discovery_limit,
                )
            if options['all'] and not options['force']:
                completed_urls = set(SinkronisasiPDKILog.objects.filter(
                    status=SinkronisasiPDKILog.Status.BERHASIL,
                ).values_list('sumber_url', flat=True))
                urls = [url for url in urls if url not in completed_urls]
            if options['all']:
                total_pending = len(urls)
                urls = urls[:options['batch_size']]
                self.stdout.write(
                    f'Arsip ditemukan: {total_pending + SinkronisasiPDKILog.objects.filter(status=SinkronisasiPDKILog.Status.BERHASIL).count()} URL; '
                    f'tersisa {total_pending}; batch ini {len(urls)} publikasi.',
                )
                if not urls:
                    self.stdout.write(self.style.SUCCESS('Seluruh arsip yang ditemukan sudah tersinkron.'))
                    return
            failures = []
            for index, url in enumerate(urls):
                try:
                    if options['dry_run']:
                        pdf_file = download_bulletin(url)
                        try:
                            data = parse_bulletin(pdf_file)
                        finally:
                            pdf_file.close()
                        self.stdout.write(self.style.SUCCESS(
                            f'DRY RUN OK: {data.title}; {len(data.records)} permohonan terbaca.',
                        ))
                        continue

                    previous = SinkronisasiPDKILog.objects.filter(sumber_url=url).first()
                    labels_missing = MirrorPDKI.objects.filter(sumber_data_url=url).filter(
                        Q(label_merek='') | Q(label_merek__isnull=True),
                    ).exists()
                    labels_complete = options['without_labels'] or not labels_missing
                    if (
                        previous and previous.status == SinkronisasiPDKILog.Status.BERHASIL
                        and labels_complete
                        and not (options['force'] or options['enrich_details'])
                    ):
                        self.stdout.write(f'Dilewati (sudah tersinkron): {previous.judul_sumber or url}')
                        continue
                    log = sync_bulletin(
                        url,
                        force=options['force'] or options['enrich_details'],
                        include_labels=not (
                            options['without_labels'] or options['enrich_details']
                        ),
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'{log.judul_sumber}: {log.jumlah_ditemukan} permohonan, '
                        f'{log.jumlah_baru} baris baru, {log.jumlah_diperbarui} diperbarui.',
                    ))
                except Exception as exc:
                    failures.append(f'{url}: {exc}')
                    self.stderr.write(self.style.ERROR(f'Gagal memproses {url}: {exc}'))
                if (
                    (options['all'] or options['enrich_details'])
                    and index < len(urls) - 1 and options['delay']
                ):
                    time.sleep(options['delay'])
            if failures:
                raise CommandError(
                    f'{len(failures)} publikasi gagal; publikasi lainnya tetap diproses. '
                    'Jalankan ulang task untuk mencoba lagi.',
                )
        except (PDKISyncError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
