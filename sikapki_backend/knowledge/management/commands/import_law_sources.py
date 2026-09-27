import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.http_client import configure_ai_network
from knowledge.jdih_sync import _safe_filename, extract_pdf_text
from knowledge.law_sources import LAW_SOURCES
from knowledge.models import DokumenResmi, KategoriKI
from knowledge.rag_service import remove_document_from_index

MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


class Command(BaseCommand):
    help = (
        'Impor teks lengkap UU/PP utama per kategori KI dari peraturan.bpk.go.id '
        'sebagai dokumen draf yang wajib diverifikasi petugas.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--category', help='Batasi impor pada satu nama kategori.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--refresh-verified', action='store_true',
            help='Periksa ulang dokumen terverifikasi; konten berubah akan dikembalikan ke draf.',
        )

    def handle(self, *args, **options):
        sources = [
            source for source in LAW_SOURCES
            if not options['category'] or source.category == options['category']
        ]
        if not sources:
            raise CommandError('Kategori tidak ditemukan dalam katalog sumber UU/PP.')

        configure_ai_network()
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'SIKAP-KI-NTB/1.0 (kurasi sumber UU/PP; kanwilntb@kemenkum.go.id)',
            'Accept': 'application/pdf',
        })

        created = updated = unchanged = failed = 0
        for source in sources:
            existing = DokumenResmi.objects.filter(sumber_url=source.detail_url).first()
            if (
                existing
                and existing.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI
                and not options['refresh_verified']
            ):
                unchanged += 1
                self.stdout.write(f'[LEWATI TERVERIFIKASI] {source.title}')
                continue

            try:
                content = self._download_pdf(session, source.pdf_url)
                text, page_count = extract_pdf_text(content)
                if len(text) < 180:
                    raise ValueError('teks hasil ekstraksi PDF terlalu pendek atau tidak terbaca')
            except (requests.RequestException, ValueError) as exc:
                failed += 1
                self.stderr.write(self.style.WARNING(f'[GAGAL] {source.title}: {exc}'))
                continue

            if options['dry_run']:
                self.stdout.write(f'[SIAP] {source.title}: {len(text)} karakter, {page_count} halaman')
                continue

            category, _ = KategoriKI.objects.get_or_create(
                nama=source.category,
                defaults={'deskripsi': f'Informasi resmi mengenai {source.category}.'},
            )
            filename = _safe_filename(source.title) + '.pdf'
            catatan_baru = 'Sumber UU/PP baru; menunggu verifikasi petugas.'
            if page_count > 200:
                catatan_baru = (
                    'PERHATIAN: dokumen ini adalah UU omnibus (>200 halaman) yang mencakup '
                    'banyak sektor, bukan hanya ' + source.category + '. Pertimbangkan untuk '
                    'mengekstrak/menyalin hanya pasal-pasal yang relevan dengan ' + source.category
                    + ' sebelum memverifikasi, agar tidak mencemari basis pengetahuan dengan '
                    'materi sektor lain. ' + catatan_baru
                )
            with transaction.atomic():
                document = DokumenResmi.objects.select_for_update().filter(
                    sumber_url=source.detail_url,
                ).first()
                if document is None:
                    document = DokumenResmi(
                        judul=source.title, kategori=category, sumber_url=source.detail_url,
                        teks_lengkap=text, jumlah_halaman=page_count, ukuran_file=len(content),
                        status_validasi=DokumenResmi.StatusValidasi.DRAF,
                        pesan_indexing=catatan_baru,
                    )
                    document.file_asli.save(filename, ContentFile(content), save=False)
                    document.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'[BARU] {source.title}'))
                elif document.teks_lengkap != text:
                    remove_document_from_index(document.id)
                    document.judul = source.title
                    document.kategori = category
                    document.teks_lengkap = text
                    document.jumlah_halaman = page_count
                    document.ukuran_file = len(content)
                    document.status_validasi = DokumenResmi.StatusValidasi.DRAF
                    document.status_indexing = DokumenResmi.StatusIndexing.BELUM
                    document.pesan_indexing = 'Sumber UU/PP berubah; menunggu verifikasi ulang.'
                    document.divalidasi_oleh = None
                    document.divalidasi_pada = None
                    document.file_asli.save(filename, ContentFile(content), save=False)
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

    @staticmethod
    def _download_pdf(session, url, max_bytes=MAX_DOWNLOAD_BYTES):
        response = session.get(url, timeout=(10, 60), stream=True)
        response.raise_for_status()
        declared_size = response.headers.get('content-length')
        if declared_size and int(declared_size) > max_bytes:
            raise ValueError(f'File terlalu besar ({declared_size} byte)')
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f'File melebihi batas {max_bytes} byte')
            chunks.append(chunk)
        content = b''.join(chunks)
        content_type = response.headers.get('content-type', '').lower()
        if not content.startswith(b'%PDF') and 'application/pdf' not in content_type:
            raise ValueError(f'Tautan bukan PDF yang dapat diproses: {url}')
        return content
