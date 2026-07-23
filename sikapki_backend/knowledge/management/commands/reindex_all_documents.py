from django.core.management.base import BaseCommand

from knowledge.models import DokumenResmi, FAQ
from knowledge.rag_service import embed_and_store, embed_and_store_faq


class Command(BaseCommand):
    help = 'Memproses ulang dokumen terverifikasi dan membersihkan indeks dokumen lainnya.'

    def handle(self, *args, **options):
        total_documents = DokumenResmi.objects.count()
        total_verified = DokumenResmi.objects.filter(
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
        ).count()
        total_chunks = 0

        if total_documents == 0:
            self.stdout.write(self.style.WARNING('Belum ada DokumenResmi untuk diindex.'))
            return

        for dokumen in DokumenResmi.objects.order_by('id'):
            chunk_count = embed_and_store(dokumen.id)
            total_chunks += chunk_count
            self.stdout.write(f'  indexed #{dokumen.id} {dokumen.judul}: {chunk_count} chunk')

        faq_verified = FAQ.objects.filter(
            status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
            aktif_sumber=True,
        )
        faq_indexed = 0
        for faq in FAQ.objects.order_by('id'):
            faq_indexed += embed_and_store_faq(faq.id)
            self.stdout.write(f'  indexed FAQ #{faq.id}: {faq.status_validasi}')

        self.stdout.write(self.style.SUCCESS(
            f'Reindex selesai: {total_verified}/{total_documents} dokumen terverifikasi, '
            f'{total_chunks} chunk aktif; {faq_indexed}/{faq_verified.count()} FAQ aktif.'
        ))
