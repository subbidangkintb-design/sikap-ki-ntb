from django.core.management.base import BaseCommand

from knowledge.models import DokumenResmi
from knowledge.rag_service import embed_and_store


class Command(BaseCommand):
    help = 'Memproses ulang semua DokumenResmi ke ChromaDB dan ChunkEmbedding.'

    def handle(self, *args, **options):
        total_documents = DokumenResmi.objects.count()
        total_chunks = 0

        if total_documents == 0:
            self.stdout.write(self.style.WARNING('Belum ada DokumenResmi untuk diindex.'))
            return

        for dokumen in DokumenResmi.objects.order_by('id'):
            chunk_count = embed_and_store(dokumen.id)
            total_chunks += chunk_count
            self.stdout.write(f'  indexed #{dokumen.id} {dokumen.judul}: {chunk_count} chunk')

        self.stdout.write(self.style.SUCCESS(
            f'Reindex selesai: {total_documents} dokumen, {total_chunks} chunk.'
        ))
