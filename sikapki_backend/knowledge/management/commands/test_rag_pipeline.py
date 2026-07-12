from django.core.management.base import BaseCommand

from knowledge.models import DokumenResmi, KategoriKI
from knowledge.rag_service import embed_and_store, retrieve_relevant_chunks


class Command(BaseCommand):
    help = 'Smoke test sederhana untuk memastikan pipeline RAG knowledge berjalan.'

    def handle(self, *args, **options):
        kategori, _ = KategoriKI.objects.get_or_create(
            nama='Merek',
            defaults={
                'deskripsi': 'Tanda untuk membedakan barang atau jasa satu pelaku usaha dengan lainnya.',
            },
        )
        dokumen, _ = DokumenResmi.objects.update_or_create(
            judul='Dummy Syarat Pendaftaran Merek',
            defaults={
                'kategori': kategori,
                'teks_lengkap': (
                    'Syarat pendaftaran merek meliputi identitas pemohon, label atau etiket merek, '
                    'kelas barang atau jasa sesuai Nice Classification, deskripsi produk, surat '
                    'pernyataan kepemilikan merek, dan bukti pembayaran PNBP. Pemohon UMKM dapat '
                    'melampirkan surat rekomendasi UMKM untuk memperoleh tarif khusus.'
                ),
            },
        )

        chunk_count = embed_and_store(dokumen.id)
        results = retrieve_relevant_chunks('apa saja syarat daftar merek', top_k=3)

        self.stdout.write(f'Indexed chunks: {chunk_count}')
        if not results:
            self.stdout.write(self.style.ERROR('Tidak ada chunk yang ditemukan.'))
            return

        top_result = results[0]
        self.stdout.write(self.style.SUCCESS('Top result:'))
        self.stdout.write(f"Judul: {top_result['metadata'].get('judul')}")
        self.stdout.write(f"Kategori: {top_result['metadata'].get('kategori')}")
        self.stdout.write(f"Distance: {top_result.get('distance')}")
        self.stdout.write(f"Text: {top_result['text']}")
