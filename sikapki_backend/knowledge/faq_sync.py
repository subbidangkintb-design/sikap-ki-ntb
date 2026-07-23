from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from django.db import transaction
from django.utils import timezone

from core.http_client import configure_ai_network

from .models import FAQ, KategoriKI, SinkronisasiFAQLog
from .rag_service import remove_faq_from_index


FAQ_MEREK_URL = 'https://dgip.go.id/faq/daftar-faq/merek/merek'
USER_AGENT = 'SIKAP-KI-NTB/1.0 (sinkronisasi FAQ resmi; kanwilntb@kemenkum.go.id)'
REQUEST_TIMEOUT = (10, 45)
MAX_PAGES = 50


class FAQSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrapedFAQ:
    pertanyaan: str
    jawaban: str
    subkategori: str
    sumber_url: str

    @property
    def source_key(self):
        identity = f'{_normalize_identity(self.subkategori)}|{_normalize_identity(self.pertanyaan)}'
        return hashlib.sha256(identity.encode('utf-8')).hexdigest()

    @property
    def content_hash(self):
        content = f'{self.pertanyaan.strip()}\n{self.jawaban.strip()}'
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class _FAQPageParser(HTMLParser):
    BLOCK_TAGS = {'p', 'div', 'li', 'br', 'ol', 'ul', 'section', 'article'}

    def __init__(self, source_url):
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.links = set()
        self.items = []
        self._in_question = False
        self._question_parts = []
        self._answer_parts = []
        self._current_href = None
        self._stopped = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            href = urljoin(self.source_url, attrs['href'])
            self.links.add(href)
            self._current_href = href
        css_classes = (attrs.get('class') or '').lower()
        aria_label = (attrs.get('aria-label') or '').lower()
        is_pagination = (
            (tag in {'nav', 'ul'} and 'pagination' in css_classes)
            or (tag == 'nav' and 'page navigation' in aria_label)
        )
        if tag == 'footer' or is_pagination:
            self._flush_item()
            self._stopped = True
            return
        if tag == 'h5' and not self._stopped:
            self._flush_item()
            self._in_question = True
            self._question_parts = []
            self._answer_parts = []
        elif self._question_parts and tag in self.BLOCK_TAGS:
            self._answer_parts.append('\n')

    def handle_endtag(self, tag):
        if tag == 'h5' and self._in_question:
            self._in_question = False
        if tag == 'a':
            self._current_href = None
        if self._question_parts and tag in self.BLOCK_TAGS:
            self._answer_parts.append('\n')

    def handle_data(self, data):
        if self._stopped:
            return
        text = data.replace('\xa0', ' ')
        if self._in_question:
            self._question_parts.append(text)
        elif self._question_parts:
            self._answer_parts.append(text)

    def close(self):
        super().close()
        self._flush_item()

    def _flush_item(self):
        if not self._question_parts:
            return
        question = _clean_question(' '.join(self._question_parts))
        answer = _clean_answer(''.join(self._answer_parts))
        if question and answer:
            self.items.append((question, answer))
        self._question_parts = []
        self._answer_parts = []
        self._in_question = False


def parse_faq_page(html, source_url, subcategory=None):
    parser = _FAQPageParser(source_url)
    parser.feed(html)
    parser.close()
    subcategory = subcategory or _subcategory_from_url(source_url)
    items = [
        ScrapedFAQ(question, answer, subcategory, source_url)
        for question, answer in parser.items
    ]
    section = _faq_section(source_url)
    links = {
        _canonical_url(link)
        for link in parser.links
        if _is_allowed_faq_url(link, section)
    }
    return items, links


def crawl_faq(start_url=FAQ_MEREK_URL, delay=1.0):
    configure_ai_network()
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'id-ID,id;q=0.9',
    })
    queue = [_canonical_url(start_url)]
    visited = set()
    collected = {}

    while queue and len(visited) < MAX_PAGES:
        url = queue.pop(0)
        if url in visited:
            continue
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FAQSyncError(f'FAQ DJKI tidak dapat diakses: {exc}') from exc
        html = response.text
        if _looks_blocked(html):
            raise FAQSyncError(
                'Akses otomatis dibatasi proteksi situs DJKI (Incapsula). '
                'Jangan mencoba melewati proteksi; gunakan --html-file dari halaman yang '
                'disimpan melalui browser atau mintakan endpoint resmi DJKI.',
            )
        items, links = parse_faq_page(html, url)
        visited.add(url)
        for item in items:
            collected[item.source_key] = item
        for link in sorted(links):
            if link not in visited and link not in queue:
                queue.append(link)
        if queue and delay:
            time.sleep(delay)

    if not collected:
        raise FAQSyncError('Tidak ada pasangan pertanyaan-jawaban yang terbaca dari halaman DJKI.')
    return list(collected.values()), visited


def crawl_faq_merek(start_url=FAQ_MEREK_URL, delay=1.0):
    """Backward-compatible wrapper for existing operational scripts."""
    return crawl_faq(start_url=start_url, delay=delay)


def load_saved_html(path, source_url, subcategory=None):
    html = Path(path).read_text(encoding='utf-8')
    if _looks_blocked(html):
        raise FAQSyncError('File HTML berisi halaman blokir Incapsula, bukan konten FAQ.')
    items, _ = parse_faq_page(html, source_url, subcategory=subcategory)
    if not items:
        raise FAQSyncError('Tidak ada pasangan pertanyaan-jawaban yang terbaca dari file HTML.')
    return items


def sync_faq_items(
    items, source_url=FAQ_MEREK_URL, full_sync=False, dry_run=False,
    category_name='Merek',
):
    items = list(items)
    if dry_run:
        return {
            'ditemukan': len(items), 'baru': 0, 'diperbarui': 0, 'dinonaktifkan': 0,
        }
    log = SinkronisasiFAQLog.objects.create(sumber_url=source_url)
    now = timezone.now()
    created = updated = deactivated = 0
    seen_keys = {item.source_key for item in items}
    try:
        category, _ = KategoriKI.objects.get_or_create(
            nama=category_name, defaults={'deskripsi': f'Informasi layanan {category_name}.'},
        )
        with transaction.atomic():
            for item in items:
                current = FAQ.objects.filter(sumber_kunci=item.source_key).first()
                if current is None:
                    FAQ.objects.create(
                        pertanyaan=item.pertanyaan,
                        jawaban=item.jawaban,
                        kategori=category,
                        status_validasi=FAQ.StatusValidasi.DRAF,
                        sumber_url=item.sumber_url,
                        sumber_kunci=item.source_key,
                        subkategori_sumber=item.subkategori,
                        hash_konten=item.content_hash,
                        aktif_sumber=True,
                        sinkronisasi_pada=now,
                    )
                    created += 1
                    continue
                changed = current.hash_konten != item.content_hash
                current.pertanyaan = item.pertanyaan
                current.jawaban = item.jawaban
                current.kategori = category
                current.sumber_url = item.sumber_url
                current.subkategori_sumber = item.subkategori
                current.hash_konten = item.content_hash
                current.aktif_sumber = True
                current.sinkronisasi_pada = now
                update_fields = [
                    'pertanyaan', 'jawaban', 'kategori', 'sumber_url', 'subkategori_sumber',
                    'hash_konten', 'aktif_sumber', 'sinkronisasi_pada',
                ]
                if changed:
                    remove_faq_from_index(current.id)
                    current.status_validasi = FAQ.StatusValidasi.DRAF
                    current.status_indexing = FAQ.StatusIndexing.BELUM
                    current.vector_id = None
                    current.diindeks_pada = None
                    current.pesan_indexing = 'Konten sumber berubah; menunggu verifikasi ulang.'
                    update_fields.extend([
                        'status_validasi', 'status_indexing', 'vector_id',
                        'diindeks_pada', 'pesan_indexing',
                    ])
                    updated += 1
                current.save(update_fields=update_fields)

            if full_sync:
                missing = FAQ.objects.filter(
                    kategori=category, sumber_kunci__isnull=False, aktif_sumber=True,
                ).exclude(sumber_kunci__in=seen_keys)
                for faq in missing.iterator():
                    remove_faq_from_index(faq.id)
                deactivated = missing.update(
                    aktif_sumber=False,
                    status_validasi=FAQ.StatusValidasi.DINONAKTIFKAN,
                    status_indexing=FAQ.StatusIndexing.BELUM,
                    vector_id=None,
                    diindeks_pada=None,
                    pesan_indexing='Tidak lagi ditemukan pada sinkronisasi sumber lengkap.',
                )
        log.status = SinkronisasiFAQLog.Status.BERHASIL
        log.jumlah_halaman = len({item.sumber_url for item in items})
        log.jumlah_ditemukan = len(items)
        log.jumlah_baru = created
        log.jumlah_diperbarui = updated
        log.jumlah_dinonaktifkan = deactivated
        log.selesai_pada = timezone.now()
        log.save()
    except Exception as exc:
        log.status = SinkronisasiFAQLog.Status.GAGAL
        log.pesan = str(exc)[:2000]
        log.selesai_pada = timezone.now()
        log.save(update_fields=['status', 'pesan', 'selesai_pada'])
        raise
    return {
        'ditemukan': len(items), 'baru': created,
        'diperbarui': updated, 'dinonaktifkan': deactivated,
    }


def _clean_question(value):
    value = re.sub(r'\s+', ' ', value).strip()
    return re.sub(r'^\s*\d+\s*[.)]\s*', '', value).strip()


def _clean_answer(value):
    value = value.replace('\r', '')
    for marker in ('Alamat Kantor', 'Call Center', 'Copyright ©'):
        value = value.split(marker, 1)[0]
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in value.split('\n')]
    compact = []
    for line in lines:
        if line and (not compact or compact[-1] != line):
            compact.append(line)
    for index, line in enumerate(compact):
        if line in {'«', '»', 'Sebelumnya', 'Selanjutnya'}:
            compact = compact[:index]
            break
    return '\n'.join(compact).strip()


def _normalize_identity(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def _subcategory_from_url(url):
    slug = urlparse(url).path.rstrip('/').rsplit('/', 1)[-1]
    return re.sub(r'[-_]+', ' ', unquote(slug)).strip().title()


def _canonical_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix('www.')
    return urlunparse(('https', host, parsed.path.rstrip('/'), '', parsed.query, ''))


def _faq_section(url):
    match = re.match(r'^/faq/daftar-faq/([^/]+)/', urlparse(url).path.lower())
    return match.group(1) if match else ''


def _is_allowed_faq_url(url, section='merek'):
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix('www.')
    safe_section = re.sub(r'[^a-z0-9-]', '', section or '')
    return bool(safe_section) and host == 'dgip.go.id' and parsed.path.lower().startswith(
        f'/faq/daftar-faq/{safe_section}/',
    )


def _looks_blocked(html):
    lower = html.lower()
    return (
        '_incapsula_resource' in lower
        or 'request unsuccessful' in lower
        or ('noindex, nofollow' in lower and len(html) < 5000)
    )
