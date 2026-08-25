"""Import satu kali daftar barang/jasa dari halaman kelas SKM DJKI.

Perintah ini sengaja menggunakan akses HTTP biasa dengan jeda dan user-agent
yang jelas. Ia tidak melewati CAPTCHA/WAF. Jika DJKI mengembalikan 403/429,
proses berhenti dan petugas perlu memakai dataset/akses resmi.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.http_client import request_with_retry
from trademark.models import NiceClassificationTerm


VERSION = 'NCL11-SKM-DJKI'
DATE_IN_FORCE = date(2017, 1, 1)
CLASS_URL = 'https://skm.dgip.go.id/index.php/skm/detailkelas/{class_number}'
USER_AGENT = 'SIKAP-KI-NTB/0.1 (Kanwil Kementerian Hukum NTB; helpdesk resmi)'


class _SkmParser(HTMLParser):
    """Parser ringan untuk tabel barang/jasa tanpa dependency scraping tambahan."""

    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.row = []
        self.rows = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'tr':
            self.in_row = True
            self.row = []
        elif self.in_row and tag in {'td', 'th'}:
            self.in_cell = True
            self.text = []

    def handle_data(self, data):
        if self.in_cell:
            self.text.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {'td', 'th'} and self.in_cell:
            value = re.sub(r'\s+', ' ', ''.join(self.text)).strip()
            self.row.append(value)
            self.in_cell = False
        elif tag == 'tr' and self.in_row:
            if self.row:
                self.rows.append(self.row)
            self.in_row = False


class Command(BaseCommand):
    help = 'Import daftar istilah barang/jasa dari SKM DJKI (satu kali, 45 kelas).'

    def add_arguments(self, parser):
        parser.add_argument('--class-number', type=int, help='Hanya import satu kelas (1-45).')
        parser.add_argument(
            '--local-dir',
            help='Folder HTML hasil Save Page As dari browser; jika diisi, tidak ada akses jaringan.',
        )
        parser.add_argument('--delay', type=float, default=2.0, help='Jeda antar halaman dalam detik.')
        parser.add_argument('--dry-run', action='store_true', help='Ambil dan validasi tanpa menyimpan.')
        parser.add_argument('--force', action='store_true', help='Hapus data SKM versi ini sebelum import.')
        parser.add_argument(
            '--allow-missing', action='store_true',
            help='Lewati kelas yang belum memiliki file HTML lokal.',
        )

    def handle(self, *args, **options):
        class_number = options.get('class_number')
        if class_number is not None and not 1 <= class_number <= 45:
            raise CommandError('--class-number harus antara 1 dan 45.')
        delay = max(0.5, min(float(options['delay']), 30.0))
        terms = []
        local_dir = Path(options['local_dir']).expanduser() if options.get('local_dir') else None
        if local_dir and not local_dir.is_dir():
            raise CommandError(f'Folder HTML tidak ditemukan: {local_dir}')
        if class_number:
            classes = [class_number]
        elif local_dir:
            classes = [number for number in range(1, 46) if _find_local_html(local_dir, number)]
            if not classes:
                raise CommandError('Tidak ditemukan file HTML kelas 1-45 di folder lokal.')
        else:
            classes = list(range(1, 46))
        for index, number in enumerate(classes):
            url = CLASS_URL.format(class_number=number)
            try:
                if local_dir:
                    html_path = _find_local_html(local_dir, number)
                    if not html_path:
                        if local_dir and options['allow_missing']:
                            self.stdout.write(self.style.WARNING(
                                f'Kelas {number}: file belum ada, dilewati.'
                            ))
                            continue
                        raise ValueError(
                            f'File kelas {number} tidak ditemukan. Gunakan nama {number}.html '
                            'atau kelas-<nomor>.html.'
                        )
                    html = html_path.read_text(encoding='utf-8', errors='replace')
                else:
                    response = request_with_retry(
                        lambda url=url: requests.get(
                            url,
                            headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'},
                            timeout=(10, 45),
                        ),
                        attempts=2,
                        backoff=2,
                    )
                    if response.status_code in {403, 429}:
                        raise CommandError(
                            f'SKM menolak akses otomatis (HTTP {response.status_code}) pada kelas {number}. '
                            'Gunakan --local-dir dengan halaman yang disimpan lewat browser.'
                        )
                    response.raise_for_status()
                    html = response.text
                parsed = _parse_class_page(html, number, url)
                if not parsed:
                    raise ValueError('Tidak ada baris barang/jasa yang dikenali.')
                terms.extend(parsed)
                self.stdout.write(f'Kelas {number}: {len(parsed)} istilah.')
            except requests.RequestException as exc:
                raise CommandError(f'Gagal mengambil SKM kelas {number}: {exc}') from exc
            except ValueError as exc:
                raise CommandError(f'Gagal membaca SKM kelas {number}: {exc}') from exc
            if not local_dir and index < len(classes) - 1:
                time.sleep(delay)

        if len(terms) < 100:
            raise CommandError(f'Hanya ditemukan {len(terms)} istilah; import dibatalkan.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'DRY RUN OK: {len(terms)} istilah SKM {VERSION} terbaca dari {len(classes)} kelas.'
            ))
            return
        with transaction.atomic():
            if options['force']:
                NiceClassificationTerm.objects.filter(
                    source=NiceClassificationTerm.Source.SKM_DJKI,
                    version=VERSION,
                ).delete()
            NiceClassificationTerm.objects.bulk_create(terms, batch_size=1000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f'{len(terms)} istilah SKM DJKI tersimpan sebagai sumber pembanding {VERSION}.'
        ))


def _parse_class_page(html: str, class_number: int, source_url: str):
    parser = _SkmParser()
    parser.feed(html)
    results = []
    seen = set()
    for row_index, row in enumerate(parser.rows, start=1):
        if not row:
            continue
        indication = row[0].strip()
        if indication.lower() in {'nama barang', 'nama barang/jasa', 'barang/jasa'}:
            continue
        if len(indication) < 2 or len(indication) > 700:
            continue
        key = indication.casefold()
        if key in seen:
            continue
        seen.add(key)
        english = row[1].strip() if len(row) > 1 else ''
        basic = 'S' + hashlib.sha1(
            f'{class_number}:{indication}'.encode('utf-8'),
        ).hexdigest()[:10]
        results.append(NiceClassificationTerm(
            class_number=str(class_number),
            basic_number=basic,
            indication_en=indication,
            synonyms_en=[english] if english and english != '-' else [],
            source=NiceClassificationTerm.Source.SKM_DJKI,
            version=VERSION,
            effective_date=DATE_IN_FORCE,
            source_url=source_url,
        ))
    return results


def _find_local_html(folder: Path, class_number: int) -> Path | None:
    candidates = (
        folder / f'{class_number}.html',
        folder / f'kelas-{class_number}.html',
        folder / f'kelas_{class_number}.html',
        folder / f'detailkelas-{class_number}.html',
    )
    direct = next((path for path in candidates if path.is_file()), None)
    if direct:
        return direct
    pattern = re.compile(rf'kelas[ _-]*\(?{class_number}\)?', re.IGNORECASE)
    return next(
        (path for path in folder.glob('*.html') if pattern.search(path.stem)),
        None,
    )
