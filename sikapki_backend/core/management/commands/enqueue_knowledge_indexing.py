from django.core.management.base import BaseCommand

from core.jobs import enqueue_job
from core.models import BackgroundJob
from knowledge.models import DokumenResmi, FAQ


class Command(BaseCommand):
    help = 'Masukkan dokumen/FAQ terverifikasi ke antrean background indexing.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        limit = max(1, min(options['limit'], 500))
        created = 0
        for document_id in DokumenResmi.objects.filter(
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
            status_indexing__in=[
                DokumenResmi.StatusIndexing.MENUNGGU,
                DokumenResmi.StatusIndexing.GAGAL,
            ],
        ).values_list('id', flat=True)[:limit]:
            if _pending_exists(BackgroundJob.Kind.DOCUMENT_INDEX, document_id):
                continue
            enqueue_job(BackgroundJob.Kind.DOCUMENT_INDEX, {'document_id': document_id})
            created += 1

        remaining = max(0, limit - created)
        for faq_id in FAQ.objects.filter(
            status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
            aktif_sumber=True,
            status_indexing__in=[FAQ.StatusIndexing.MENUNGGU, FAQ.StatusIndexing.GAGAL],
        ).values_list('id', flat=True)[:remaining]:
            if _pending_exists(BackgroundJob.Kind.FAQ_INDEX, faq_id):
                continue
            enqueue_job(BackgroundJob.Kind.FAQ_INDEX, {'faq_id': faq_id})
            created += 1
        self.stdout.write(self.style.SUCCESS(f'{created} job indexing masuk antrean.'))


def _pending_exists(kind, object_id):
    key = 'document_id' if kind == BackgroundJob.Kind.DOCUMENT_INDEX else 'faq_id'
    return any(
        (job.payload or {}).get(key) == object_id
        for job in BackgroundJob.objects.filter(
            kind=kind,
            status__in=[BackgroundJob.Status.QUEUED, BackgroundJob.Status.RUNNING],
        ).only('payload')
    )
