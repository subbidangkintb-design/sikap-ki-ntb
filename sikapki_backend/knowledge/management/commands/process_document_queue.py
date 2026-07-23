import time

from django.core.management.base import BaseCommand

from knowledge.models import DokumenResmi, FAQ
from knowledge.rag_service import embed_and_store, embed_and_store_faq


class Command(BaseCommand):
    help = 'Proses antrean indexing dokumen resmi dan FAQ di luar request Django Admin.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=5, help='Maksimal dokumen per putaran.')
        parser.add_argument('--watch', action='store_true', help='Pantau antrean terus-menerus.')
        parser.add_argument('--interval', type=int, default=5, help='Jeda pemantauan dalam detik.')

    def handle(self, *args, **options):
        limit = max(1, min(options['limit'], 100))
        interval = max(2, min(options['interval'], 300))
        while True:
            processed = self._process_batch(limit)
            if not options['watch']:
                if not processed:
                    self.stdout.write('Tidak ada dokumen dalam antrean.')
                return
            if not processed:
                time.sleep(interval)

    def _process_batch(self, limit):
        document_ids = list(
            DokumenResmi.objects.filter(
                status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
                status_indexing=DokumenResmi.StatusIndexing.MENUNGGU,
            ).order_by('tanggal_upload').values_list('id', flat=True)[:limit]
        )
        for document_id in document_ids:
            claimed = DokumenResmi.objects.filter(
                pk=document_id,
                status_indexing=DokumenResmi.StatusIndexing.MENUNGGU,
            ).update(status_indexing=DokumenResmi.StatusIndexing.DIPROSES)
            if not claimed:
                continue
            try:
                chunk_count = embed_and_store(document_id)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'#{document_id} gagal: {exc}'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'#{document_id} berhasil: {chunk_count} chunk.',
                ))
        remaining = max(0, limit - len(document_ids))
        faq_ids = list(
            FAQ.objects.filter(
                status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
                aktif_sumber=True,
                status_indexing=FAQ.StatusIndexing.MENUNGGU,
            ).order_by('id').values_list('id', flat=True)[:remaining]
        )
        for faq_id in faq_ids:
            claimed = FAQ.objects.filter(
                pk=faq_id,
                status_indexing=FAQ.StatusIndexing.MENUNGGU,
            ).update(status_indexing=FAQ.StatusIndexing.DIPROSES)
            if not claimed:
                continue
            try:
                embed_and_store_faq(faq_id)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'FAQ #{faq_id} gagal: {exc}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'FAQ #{faq_id} berhasil diindeks.'))
        return len(document_ids) + len(faq_ids)
