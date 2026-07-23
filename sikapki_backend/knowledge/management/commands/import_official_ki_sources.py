import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.http_client import configure_ai_network
from knowledge.models import DokumenResmi, KategoriKI
from knowledge.official_sources import OFFICIAL_SOURCES, extract_official_page_text
from knowledge.rag_service import remove_document_from_index


class Command(BaseCommand):
    help = 'Impor halaman referensi resmi DJKI/PVTPP sebagai dokumen draf knowledge base.'

    def add_arguments(self, parser):
        parser.add_argument('--category', help='Batasi impor pada satu nama kategori.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--refresh-verified', action='store_true',
            help='Periksa ulang dokumen terverifikasi; konten berubah akan dikembalikan ke draf.',
        )

    def handle(self, *args, **options):
        sources = [
            source for source in OFFICIAL_SOURCES
            if not options['category'] or source.category == options['category']
        ]
        if not sources:
            raise CommandError('Kategori tidak ditemukan dalam katalog sumber resmi.')
        configure_ai_network()
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'SIKAP-KI-NTB/1.0 (kurasi sumber resmi; kanwilntb@kemenkum.go.id)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'id-ID,id;q=0.9',
        })
        created = updated = unchanged = failed = 0
        for source in sources:
            existing = DokumenResmi.objects.filter(sumber_url=source.url).first()
            if (
                existing
                and existing.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI
                and not options['refresh_verified']
            ):
                unchanged += 1
                self.stdout.write(f'[LEWATI TERVERIFIKASI] {source.title}')
                continue
            try:
                response = session.get(source.url, timeout=(10, 45))
                response.raise_for_status()
                text = extract_official_page_text(response.text)
                if len(text) < 180:
                    raise ValueError('konten utama terlalu pendek atau tidak terbaca')
            except (requests.RequestException, ValueError) as exc:
                failed += 1
                self.stderr.write(self.style.WARNING(f'[GAGAL] {source.title}: {exc}'))
                continue
            if options['dry_run']:
                self.stdout.write(f'[SIAP] {source.title}: {len(text)} karakter')
                continue
            category, _ = KategoriKI.objects.get_or_create(
                nama=source.category,
                defaults={'deskripsi': f'Informasi resmi mengenai {source.category}.'},
            )
            with transaction.atomic():
                document = DokumenResmi.objects.select_for_update().filter(
                    sumber_url=source.url,
                ).first()
                if document is None:
                    DokumenResmi.objects.create(
                        judul=source.title, kategori=category, sumber_url=source.url,
                        teks_lengkap=text, status_validasi=DokumenResmi.StatusValidasi.DRAF,
                        pesan_indexing='Sumber resmi baru; menunggu verifikasi petugas.',
                    )
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'[BARU] {source.title}'))
                elif document.teks_lengkap != text:
                    remove_document_from_index(document.id)
                    document.judul = source.title
                    document.kategori = category
                    document.teks_lengkap = text
                    document.status_validasi = DokumenResmi.StatusValidasi.DRAF
                    document.status_indexing = DokumenResmi.StatusIndexing.BELUM
                    document.pesan_indexing = 'Sumber resmi berubah; menunggu verifikasi ulang.'
                    document.divalidasi_oleh = None
                    document.divalidasi_pada = None
                    document.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f'[DIPERBARUI] {source.title}'))
                else:
                    unchanged += 1
                    self.stdout.write(f'[TETAP] {source.title}')
        self.stdout.write(
            f'Selesai: baru={created}, diperbarui={updated}, tetap={unchanged}, gagal={failed}. '
            'Dokumen baru/berubah tetap draf sampai diverifikasi petugas.',
        )
        if failed:
            raise CommandError(f'{failed} sumber gagal diimpor; periksa pesan di atas.')
