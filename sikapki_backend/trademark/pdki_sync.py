from __future__ import annotations

import re
import tempfile
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps
from pypdf import PdfReader
from pypdf._font import Font

from core.http_client import configure_ai_network, request_with_retry

from .models import MirrorPDKI, SinkronisasiPDKILog


BRM_LIST_URL = 'https://www.dgip.go.id/berita-resmi/berita-resmi-merek'
CRAWLER_USER_AGENT = 'SIKAP-KI-NTB/0.1 (Kanwil Kementerian Hukum NTB; kanwilntb@kemenkum.go.id)'
MAX_PDF_BYTES = 150 * 1024 * 1024
REQUEST_TIMEOUT = (10, 90)

APPLICATION_PATTERN = re.compile(
    r'^\s*\d{1,5}\s+([A-Z]{2,6}\d{8,})\s+(\d{2}/\d{2}/\d{4})\s+'
    r'((?:[1-9]|[1-3]\d|4[0-5])(?:\s*,\s*(?:[1-9]|[1-3]\d|4[0-5]))*)\s+(.+?)\s*$'
)
LABEL_PATTERN = re.compile(r'Etiket\s*([A-Z]{2,6}\d{8,})', re.IGNORECASE)
MONTHS_ID = {
    'JANUARI': 1, 'FEBRUARI': 2, 'MARET': 3, 'APRIL': 4, 'MEI': 5, 'JUNI': 6,
    'JULI': 7, 'AGUSTUS': 8, 'SEPTEMBER': 9, 'OKTOBER': 10, 'NOVEMBER': 11, 'DESEMBER': 12,
}


class PDKISyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class BulletinRecord:
    nomor_permohonan: str
    tanggal_penerimaan: datetime.date
    kelas: tuple[str, ...]
    nama_merek: str


@dataclass(frozen=True)
class BulletinData:
    title: str
    publication_date: datetime.date | None
    records: tuple[BulletinRecord, ...]


@dataclass(frozen=True)
class BulletinDetail:
    pemilik: str
    uraian_per_kelas: dict[str, str]


def discover_bulletin_urls(limit: int = 1) -> list[str]:
    configure_ai_network()
    try:
        response = request_with_retry(
            lambda: requests.get(
                BRM_LIST_URL,
                headers={'User-Agent': CRAWLER_USER_AGENT, 'Accept': 'text/html'},
                timeout=REQUEST_TIMEOUT,
            ),
            attempts=getattr(settings, 'DJKI_REQUEST_RETRIES', 3) + 1,
            backoff=getattr(settings, 'DJKI_RETRY_BACKOFF_SECONDS', 2),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PDKISyncError(f'Daftar Berita Resmi Merek DJKI tidak dapat diakses: {exc}') from exc

    paths = re.findall(r'href=["\']([^"\']*/berita-resmi/\d+/download)["\']', response.text)
    urls = []
    for path in paths:
        url = urljoin(BRM_LIST_URL, path)
        if url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    if not urls:
        raise PDKISyncError('Tautan PDF Berita Resmi Merek tidak ditemukan pada halaman DJKI.')
    return urls


def download_bulletin(url: str) -> BinaryIO:
    configure_ai_network()
    target = tempfile.SpooledTemporaryFile(max_size=12 * 1024 * 1024, mode='w+b')
    downloaded = 0
    try:
        response = request_with_retry(
            lambda: requests.get(
                url,
                headers={'User-Agent': CRAWLER_USER_AGENT, 'Accept': 'application/pdf'},
                timeout=REQUEST_TIMEOUT,
                stream=True,
            ),
            attempts=getattr(settings, 'DJKI_REQUEST_RETRIES', 3) + 1,
            backoff=getattr(settings, 'DJKI_RETRY_BACKOFF_SECONDS', 2),
        )
        with response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > MAX_PDF_BYTES:
                    raise PDKISyncError('Ukuran PDF melebihi batas aman 150 MB.')
                target.write(chunk)
    except Exception:
        target.close()
        raise
    target.seek(0)
    if target.read(5) != b'%PDF-':
        target.close()
        raise PDKISyncError('Sumber DJKI tidak mengembalikan file PDF yang valid.')
    target.seek(0)
    return target


def parse_bulletin(pdf_file: BinaryIO) -> BulletinData:
    _install_pypdf_font_width_workaround()
    reader = PdfReader(pdf_file)
    if len(reader.pages) < 2:
        raise PDKISyncError('PDF Berita Resmi Merek tidak memiliki halaman data.')
    cover = reader.pages[0].extract_text() or ''
    title = _extract_title(cover)
    publication_date = _extract_publication_date(cover)
    records = []
    seen = set()
    empty_pages_after_data = 0

    for page_number in range(1, min(len(reader.pages), 60)):
        text = reader.pages[page_number].extract_text() or ''
        text = re.sub(
            rf'Halaman\s+\d+\s+dari\s+{len(reader.pages)}', '\n', text, flags=re.IGNORECASE,
        )
        page_records = 0
        for raw_line in text.splitlines():
            match = APPLICATION_PATTERN.match(' '.join(raw_line.split()))
            if not match:
                continue
            number, received_at, class_text, brand_name = match.groups()
            key = number.upper()
            if key in seen:
                continue
            seen.add(key)
            classes = tuple(part.strip() for part in class_text.split(','))
            records.append(BulletinRecord(
                nomor_permohonan=key,
                tanggal_penerimaan=datetime.strptime(received_at, '%d/%m/%Y').date(),
                kelas=classes,
                nama_merek=_clean_brand_name(brand_name),
            ))
            page_records += 1
        if page_records:
            empty_pages_after_data = 0
        elif records:
            empty_pages_after_data += 1
            if empty_pages_after_data >= 2:
                break

    if not records:
        raise PDKISyncError('Daftar merek tidak berhasil dibaca dari PDF DJKI.')
    return BulletinData(title=title, publication_date=publication_date, records=tuple(records))


def extract_bulletin_labels(pdf_file: BinaryIO) -> dict[str, bytes]:
    """Pair detail-page etiket images with application numbers in document order."""
    _install_pypdf_font_width_workaround()
    reader = PdfReader(pdf_file)
    application_numbers = []
    source_images = []
    detail_started = False

    for page in reader.pages:
        text = page.extract_text() or ''
        page_numbers = [number.upper() for number in LABEL_PATTERN.findall(text)]
        if page_numbers:
            detail_started = True
        if not detail_started:
            continue
        application_numbers.extend(page_numbers)
        source_images.extend(page.images)

    if not application_numbers:
        raise PDKISyncError('Penanda nomor permohonan pada halaman etiket tidak ditemukan.')
    if len(application_numbers) != len(set(application_numbers)):
        raise PDKISyncError('Nomor permohonan etiket duplikat ditemukan dalam PDF DJKI.')
    if len(application_numbers) != len(source_images):
        raise PDKISyncError(
            f'Pasangan etiket tidak konsisten: {len(application_numbers)} nomor dan '
            f'{len(source_images)} gambar. Data visual tidak disimpan untuk mencegah salah pasangan.',
        )

    return {
        number: _compress_label_image(image_file.image)
        for number, image_file in zip(application_numbers, source_images)
    }


def extract_bulletin_details(pdf_file: BinaryIO) -> dict[str, BulletinDetail]:
    """Baca pemilik dan uraian per kelas dari halaman detail BRM."""
    _install_pypdf_font_width_workaround()
    reader = PdfReader(pdf_file)
    collected = []
    detail_started = False
    for page in reader.pages:
        text = page.extract_text() or ''
        if LABEL_PATTERN.search(text):
            detail_started = True
        if detail_started:
            collected.append(text)
    full_text = '\n'.join(collected)
    details = {}
    marker = re.compile(r'540\s+Etiket\s*([A-Z]{2,6}\d{8,})', re.IGNORECASE)
    previous_end = 0
    for match in marker.finditer(full_text):
        block = full_text[previous_end:match.start()]
        previous_end = match.end()
        number = match.group(1).upper()
        classes_match = re.search(
            r'511\s+Kelas\s+Barang/Jasa\s*:[ \t]*([0-9, \t]+)', block, re.IGNORECASE,
        )
        description_match = re.search(
            r'510\s+Uraian\s+Barang/Jasa\s*:\s*(.+?)(?=Nomor\s+Permohonan)',
            block, re.IGNORECASE | re.DOTALL,
        )
        if not classes_match or not description_match:
            continue
        classes = [
            str(int(value.strip()))
            for value in classes_match.group(1).split(',')
            if value.strip().isdigit() and 1 <= int(value.strip()) <= 45
        ]
        descriptions = [
            _clean_goods_services(value)
            for value in re.findall(r'===\s*(.*?)\s*===', description_match.group(1), re.DOTALL)
            if _clean_goods_services(value)
        ]
        if not descriptions:
            fallback = _clean_goods_services(description_match.group(1).replace('===', ' '))
            descriptions = [fallback] if fallback else []
        if not descriptions:
            continue
        if len(descriptions) == len(classes):
            per_class = dict(zip(classes, descriptions))
        else:
            combined = '; '.join(descriptions)
            per_class = {class_number: combined for class_number in classes}
        details[number] = BulletinDetail(
            pemilik=_extract_owner(block),
            uraian_per_kelas=per_class,
        )
    return details


def sync_bulletin(
    url: str, force: bool = False, include_labels: bool = True,
) -> SinkronisasiPDKILog:
    log, _ = SinkronisasiPDKILog.objects.update_or_create(
        sumber_url=url,
        defaults={
            'sumber': MirrorPDKI.SumberData.BRM_DJKI,
            'status': SinkronisasiPDKILog.Status.BERJALAN,
            'pesan': '',
            'selesai_pada': None,
        },
    )
    pdf_file = None
    try:
        pdf_file = download_bulletin(url)
        bulletin = parse_bulletin(pdf_file)
        details = extract_bulletin_details(pdf_file)
        labels = extract_bulletin_labels(pdf_file) if include_labels else {}
        label_assets = _store_label_assets(labels, bulletin.records, url)
        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for record in bulletin.records:
                for nice_class in record.kelas:
                    detail = details.get(record.nomor_permohonan)
                    current = MirrorPDKI.objects.filter(
                        nomor_permohonan=record.nomor_permohonan,
                        kelas_nice=nice_class,
                    ).first()
                    if current and current.sumber_data == MirrorPDKI.SumberData.API_PDKI:
                        continue
                    if current and _current_record_is_newer(
                        current, bulletin.publication_date, url,
                    ):
                        continue
                    defaults = {
                        'nama_merek': record.nama_merek,
                        'status': MirrorPDKI.Status.DIAJUKAN,
                        'tanggal_penerimaan': record.tanggal_penerimaan,
                        'tanggal_publikasi': bulletin.publication_date,
                        'sumber_data': MirrorPDKI.SumberData.BRM_DJKI,
                        'sumber_data_url': url,
                    }
                    if detail and detail.pemilik:
                        defaults['pemilik'] = detail.pemilik
                    elif not current:
                        defaults['pemilik'] = 'Lihat dokumen sumber DJKI'
                    goods_services = ''
                    if detail:
                        goods_services = detail.uraian_per_kelas.get(nice_class, '')
                        unique_descriptions = list(dict.fromkeys(
                            value for value in detail.uraian_per_kelas.values() if value
                        ))
                        if not goods_services and len(unique_descriptions) == 1:
                            # Beberapa BRM mengekstrak nomor kelas secara tidak konsisten,
                            # tetapi satu uraian tetap aman dipasangkan ke satu permohonan.
                            goods_services = unique_descriptions[0]
                    if goods_services:
                        defaults['uraian_barang_jasa'] = goods_services
                    elif not current:
                        defaults['uraian_barang_jasa'] = ''
                    label_asset = label_assets.get(record.nomor_permohonan)
                    if label_asset:
                        defaults.update({
                            'label_merek': label_asset['path'],
                            'sumber_label_url': url,
                            'visual_embedding': label_asset['embedding'],
                            'visual_embedding_diperbarui': timezone.now(),
                        })
                    _, created = MirrorPDKI.objects.update_or_create(
                        nomor_permohonan=record.nomor_permohonan,
                        kelas_nice=nice_class,
                        defaults=defaults,
                    )
                    created_count += int(created)
                    updated_count += int(not created)
            log.judul_sumber = bulletin.title
            log.status = SinkronisasiPDKILog.Status.BERHASIL
            log.jumlah_ditemukan = len(bulletin.records)
            log.jumlah_baru = created_count
            log.jumlah_diperbarui = updated_count
            log.selesai_pada = timezone.now()
            log.pesan = (
                f'Data berasal dari Berita Resmi Merek DJKI; {len(details)} detail uraian dibaca '
                f'dan {len(label_assets)} etiket dipasangkan. '
                'Verifikasi status terkini tetap melalui PDKI.'
            )
            log.save()
    except Exception as exc:
        log.status = SinkronisasiPDKILog.Status.GAGAL
        log.pesan = str(exc)[:2000]
        log.selesai_pada = timezone.now()
        log.save(update_fields=['status', 'pesan', 'selesai_pada'])
        raise
    finally:
        if pdf_file is not None:
            pdf_file.close()
    return log


def _extract_title(cover: str) -> str:
    number = re.search(r'No\.\s*([^\n]+)', cover, flags=re.IGNORECASE)
    return f'Berita Resmi Merek Seri-A No. {number.group(1).strip()}' if number else 'Berita Resmi Merek DJKI'


def _current_record_is_newer(
    current: MirrorPDKI, incoming_date: datetime.date | None, incoming_url: str,
) -> bool:
    if current.sumber_data != MirrorPDKI.SumberData.BRM_DJKI:
        return False
    if current.tanggal_publikasi and not incoming_date:
        return True
    if current.tanggal_publikasi and incoming_date:
        if current.tanggal_publikasi > incoming_date:
            return True
        if current.tanggal_publikasi == incoming_date and current.sumber_data_url != incoming_url:
            current_id = _bulletin_url_id(current.sumber_data_url)
            incoming_id = _bulletin_url_id(incoming_url)
            return current_id >= incoming_id
    return False


def _bulletin_url_id(url: str) -> int:
    match = re.search(r'/berita-resmi/(\d+)/download', url or '')
    return int(match.group(1)) if match else 0


def _extract_publication_date(cover: str):
    match = re.search(r'DIUMUMKAN\s+TANGGAL\s+(\d{1,2})\s+([A-Z]+)\s+(\d{4})', cover.upper())
    if not match:
        return None
    day, month_name, year = match.groups()
    month = MONTHS_ID.get(month_name)
    return datetime(int(year), month, int(day)).date() if month else None


def _clean_brand_name(value: str) -> str:
    cleaned = re.sub(r'\s+', ' ', value).strip(' -')
    return cleaned[:255] or '(Merek tanpa unsur kata)'


def _clean_goods_services(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip(' ;')


def _extract_owner(block: str) -> str:
    match = re.search(
        r'Nama\s+Pemohon\s*:\s*\n\s*:\s*([^\n:]+)', block, re.IGNORECASE,
    )
    if not match:
        match = re.search(r'Nama\s+Pemohon\s*:\s*([^\n:]+)', block, re.IGNORECASE)
    return re.sub(r'\s+', ' ', match.group(1)).strip()[:255] if match else ''


def _compress_label_image(image: Image.Image) -> bytes:
    image = ImageOps.exif_transpose(image).convert('RGBA')
    image.thumbnail((384, 384), Image.Resampling.LANCZOS)
    background = Image.new('RGB', image.size, 'white')
    background.paste(image, mask=image.getchannel('A'))
    output = BytesIO()
    background.save(output, format='JPEG', quality=74, optimize=True, progressive=True)
    return output.getvalue()


def _store_label_assets(
    labels: dict[str, bytes], records: tuple[BulletinRecord, ...], source_url: str,
) -> dict[str, dict]:
    from .services import generate_image_embedding

    known_numbers = {record.nomor_permohonan for record in records}
    assets = {}
    for number, image_bytes in labels.items():
        if number not in known_numbers:
            continue
        path = f'trademark/referensi/brm/{number}.jpg'
        if not default_storage.exists(path):
            path = default_storage.save(path, ContentFile(image_bytes))
        assets[number] = {
            'path': path,
            'embedding': generate_image_embedding(image_bytes, 'image/jpeg'),
            'source_url': source_url,
        }
    return assets


def _install_pypdf_font_width_workaround() -> None:
    """Resolve malformed indirect font widths found in some official DJKI PDFs."""
    if getattr(Font.get_text_width, '_sikapki_safe_widths', False):
        return

    def safe_get_text_width(font, text: str = '') -> float:
        total = 0.0
        for character in text:
            value = font.character_widths.get(character, font.character_widths.get('default', 0))
            for _ in range(3):
                get_object = getattr(value, 'get_object', None)
                if not callable(get_object):
                    break
                resolved = get_object()
                if resolved is value:
                    break
                value = resolved
            try:
                total += float(value)
            except (TypeError, ValueError):
                continue
        return total

    safe_get_text_width._sikapki_safe_widths = True
    Font.get_text_width = safe_get_text_width
