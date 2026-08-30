"""Discovery and import helpers for public JDIH document indexes.

The importer is deliberately conservative: it only follows links on an
allow-listed JDIH host, keeps imported documents as drafts, and never marks a
document as verified automatically.  A petugas must confirm the document's
identity and current status before it can be used by the chatbot.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from django.core.files.base import ContentFile
from django.db import transaction
from pypdf import PdfReader

from core.http_client import configure_ai_network

from .models import DokumenResmi, KategoriKI
from .rag_service import remove_document_from_index


DEFAULT_INDEX_URL = 'https://jdih.kemenkumhamri.com/'
DEFAULT_ALLOWED_HOSTS = {
    'jdih.kemenkumhamri.com',
    'www.jdih.kemenkumhamri.com',
    'jdih.kemenham.go.id',
    'www.jdih.kemenham.go.id',
}
REQUEST_TIMEOUT = (10, 45)
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


class JDIHSyncError(RuntimeError):
    """Raised when the JDIH source cannot be read safely."""


@dataclass(frozen=True)
class JDIHDocumentCandidate:
    title: str
    url: str
    source_page: str = ''
    category: str = ''
    status: str = ''


KI_KEYWORDS = (
    ('Indikasi Geografis', ('indikasi geografis',)),
    ('Hak Cipta', ('hak cipta', 'ciptaan', 'hak terkait')),
    ('Desain Industri', ('desain industri',)),
    ('DTLST', ('desain tata letak sirkuit terpadu', 'dtlst', 'sirkuit terpadu')),
    ('Rahasia Dagang', ('rahasia dagang',)),
    ('Perlindungan Varietas Tanaman', ('perlindungan varietas tanaman', 'varietas tanaman', 'pvt')),
    ('Paten', ('paten', 'invensi')),
    ('Merek', ('merek', 'merek dagang', 'merek jasa')),
    ('Kekayaan Intelektual Komunal', ('kekayaan intelektual komunal', 'ki komunal', 'kik')),
)


def infer_ki_category(value: str) -> str:
    """Return the most specific KI category found in title/URL text."""
    text = _normalize(value)
    for category, keywords in KI_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return ''


class _LinkParser(HTMLParser):
    """Extract links and a small amount of page context from HTML."""

    IGNORED = {'script', 'style', 'svg', 'nav', 'footer', 'header', 'form'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.headings: list[str] = []
        self._ignored_depth = 0
        self._href = ''
        self._anchor_parts: list[str] = []
        self._heading_tag = ''
        self._heading_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.IGNORED:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == 'a' and attrs.get('href'):
            self._href = attrs['href']
            self._anchor_parts = []
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'title'}:
            self._heading_tag = tag
            self._heading_parts = []

    def handle_endtag(self, tag):
        if tag in self.IGNORED:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if self._ignored_depth:
            return
        if tag == 'a' and self._href:
            text = _clean_text(' '.join(self._anchor_parts))
            self.links.append((self._href, text))
            self._href = ''
            self._anchor_parts = []
        if self._heading_tag == tag:
            heading = _clean_text(' '.join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_tag = ''
            self._heading_parts = []

    def handle_data(self, data):
        if self._ignored_depth:
            return
        if self._href:
            self._anchor_parts.append(data)
        if self._heading_tag:
            self._heading_parts.append(data)


def parse_jdih_page(html: str, page_url: str, allowed_hosts=None):
    """Parse an index/detail page into safe absolute links and context."""
    parser = _LinkParser()
    parser.feed(html)
    parser.close()
    allowed = set(allowed_hosts or DEFAULT_ALLOWED_HOSTS)
    links = []
    seen = set()
    for href, label in parser.links:
        absolute = _canonical_url(urljoin(page_url, href))
        if not _is_allowed_url(absolute, allowed):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append((absolute, label))
    return links, parser.headings


def discover_jdih_candidates(
    start_url=DEFAULT_INDEX_URL,
    *,
    delay=1.0,
    max_pages=30,
    max_documents=100,
    max_depth=2,
    allowed_hosts=None,
    session=None,
):
    """Discover likely PDF documents without bypassing site protections."""
    allowed = set(allowed_hosts or DEFAULT_ALLOWED_HOSTS)
    start_url = _canonical_url(start_url)
    if not _is_allowed_url(start_url, allowed):
        raise JDIHSyncError('URL awal bukan host JDIH yang diizinkan.')

    configure_ai_network()
    client = session or requests.Session()
    client.headers.update({
        'User-Agent': 'SIKAP-KI-NTB/1.0 (kurasi dokumen JDIH; kanwilntb@kemenkum.go.id)',
        'Accept': 'text/html,application/xhtml+xml,application/pdf',
        'Accept-Language': 'id-ID,id;q=0.9',
    })
    queue = [(start_url, 0)]
    visited = set()
    candidates = {}

    while queue and len(visited) < max_pages and len(candidates) < max_documents:
        page_url, depth = queue.pop(0)
        if page_url in visited:
            continue
        try:
            response = client.get(page_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            if getattr(exc.response, 'status_code', None) in {401, 403, 429}:
                raise JDIHSyncError(
                    'Akses JDIH dibatasi atau memerlukan autentikasi. '
                    'Jangan mencoba melewati proteksi; gunakan --manifest-file atau minta endpoint resmi.',
                ) from exc
            raise JDIHSyncError(f'JDIH tidak dapat diakses: {exc}') from exc

        visited.add(page_url)
        content_type = response.headers.get('content-type', '').lower()
        if _is_pdf_url(page_url, '') or 'application/pdf' in content_type:
            title = _title_from_url(page_url)
            category = infer_ki_category(title + ' ' + page_url)
            if category:
                candidates[page_url] = JDIHDocumentCandidate(
                    title=title, url=page_url, source_page=page_url, category=category,
                )
            continue

        links, headings = parse_jdih_page(response.text, page_url, allowed)
        page_context = ' '.join(headings)
        for link, label in links:
            if _is_pdf_url(link, label):
                context = f'{page_context} {page_url}'
                title = _clean_title(label, link, context)
                category = infer_ki_category(f'{title} {link} {context}')
                if category:
                    candidates.setdefault(
                        link,
                        JDIHDocumentCandidate(
                            title=title, url=link, source_page=page_url, category=category,
                        ),
                    )
            elif depth < max_depth and (
                _looks_like_document_link(link, label)
                or _looks_like_listing_link(link, label)
            ):
                if link not in visited and all(link != queued[0] for queued in queue):
                    queue.append((link, depth + 1))
        if queue and delay:
            _sleep(delay)

    return list(candidates.values())[:max_documents], visited


def load_jdih_manifest(path: str, allowed_hosts=None):
    """Load a browser/API-exported JSON manifest for sites blocking crawlers."""
    allowed = set(allowed_hosts or DEFAULT_ALLOWED_HOSTS)
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        payload = payload.get('documents', payload.get('items', []))
    if not isinstance(payload, list):
        raise JDIHSyncError('Manifest harus berupa array JSON atau memiliki kunci documents/items.')
    candidates = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        url = _canonical_url(str(item.get('url') or item.get('pdf_url') or ''))
        title = _clean_text(str(item.get('title') or item.get('judul') or ''))
        if not url or not title or not _is_allowed_url(url, allowed):
            continue
        category = str(item.get('category') or item.get('kategori') or '').strip()
        category = category or infer_ki_category(f'{title} {url}')
        if not category:
            continue
        candidates.append(JDIHDocumentCandidate(
            title=title,
            url=url,
            source_page=str(item.get('source_page') or item.get('sumber_url') or url),
            category=category,
            status=str(item.get('status') or '').strip(),
        ))
    if not candidates:
        raise JDIHSyncError('Manifest tidak berisi dokumen JDIH yang relevan dengan KI.')
    return candidates


def download_jdih_pdf(session, candidate: JDIHDocumentCandidate, max_bytes=MAX_DOWNLOAD_BYTES):
    response = session.get(candidate.url, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True)
    response.raise_for_status()
    declared_size = response.headers.get('content-length')
    if declared_size and int(declared_size) > max_bytes:
        raise JDIHSyncError(f'File terlalu besar ({declared_size} byte): {candidate.title}')
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=1024 * 256):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise JDIHSyncError(f'File melebihi batas {max_bytes} byte: {candidate.title}')
        chunks.append(chunk)
    content = b''.join(chunks)
    content_type = response.headers.get('content-type', '').lower()
    if not content.startswith(b'%PDF') and 'application/pdf' not in content_type:
        raise JDIHSyncError(f'Tautan bukan PDF yang dapat diproses: {candidate.url}')
    return content


def extract_pdf_text(content: bytes):
    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append((page.extract_text() or '').strip())
    text = '\n\n'.join(page for page in pages if page).strip()
    return text, len(reader.pages)


def import_jdih_candidates(
    candidates,
    *,
    session=None,
    dry_run=False,
    category_filter='',
    refresh_verified=False,
):
    """Download and save candidates as draft DokumenResmi records."""
    configure_ai_network()
    client = session or requests.Session()
    client.headers.update({
        'User-Agent': 'SIKAP-KI-NTB/1.0 (kurasi dokumen JDIH; kanwilntb@kemenkum.go.id)',
        'Accept': 'application/pdf',
    })
    result = {
        'ditemukan': len(candidates), 'baru': 0, 'diperbarui': 0,
        'tetap': 0, 'dilewati': 0, 'gagal': 0, 'errors': [],
    }
    selected = [
        candidate for candidate in candidates
        if not category_filter or candidate.category.lower() == category_filter.lower()
    ]
    result['ditemukan'] = len(selected)
    for candidate in selected:
        if dry_run:
            continue
        try:
            existing = DokumenResmi.objects.filter(sumber_url=candidate.url).first()
            if (
                existing
                and existing.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI
                and not refresh_verified
            ):
                result['dilewati'] += 1
                continue
            content = download_jdih_pdf(client, candidate)
            text, page_count = extract_pdf_text(content)
            category, _ = KategoriKI.objects.get_or_create(
                nama=candidate.category,
                defaults={'deskripsi': f'Informasi resmi mengenai {candidate.category}.'},
            )
            with transaction.atomic():
                if existing is None:
                    document = DokumenResmi(
                        judul=candidate.title,
                        kategori=category,
                        sumber_url=candidate.url,
                        teks_lengkap=text,
                        jumlah_halaman=page_count,
                        ukuran_file=len(content),
                        status_validasi=DokumenResmi.StatusValidasi.DRAF,
                        pesan_indexing=(
                            'Ditemukan otomatis dari JDIH; periksa status berlaku dan '
                            'verifikasi petugas sebelum indexing.'
                        ),
                    )
                    filename = _safe_filename(candidate.title) + '.pdf'
                    document.file_asli.save(filename, ContentFile(content), save=False)
                    document.save()
                    result['baru'] += 1
                    continue

                changed = (
                    existing.judul != candidate.title
                    or existing.teks_lengkap != text
                    or existing.ukuran_file != len(content)
                )
                if not changed:
                    result['tetap'] += 1
                    continue
                remove_document_from_index(existing.id)
                existing.judul = candidate.title
                existing.kategori = category
                existing.teks_lengkap = text
                existing.jumlah_halaman = page_count
                existing.ukuran_file = len(content)
                existing.status_validasi = DokumenResmi.StatusValidasi.DRAF
                existing.status_indexing = DokumenResmi.StatusIndexing.BELUM
                existing.pesan_indexing = (
                    'Konten JDIH berubah; menunggu pemeriksaan dan verifikasi ulang.'
                )
                existing.divalidasi_oleh = None
                existing.divalidasi_pada = None
                existing.file_asli.save(
                    _safe_filename(candidate.title) + '.pdf',
                    ContentFile(content), save=False,
                )
                existing.save()
                result['diperbarui'] += 1
        except Exception as exc:  # per-document isolation; remaining candidates continue
            result['gagal'] += 1
            result['errors'].append(f'{candidate.title}: {exc}')
    return result


def _normalize(value):
    return re.sub(r'\s+', ' ', str(value or '').lower()).strip()


def _clean_text(value):
    return re.sub(r'\s+', ' ', str(value or '').replace('\xa0', ' ')).strip()


def _canonical_url(value):
    parsed = urlparse(str(value or '').strip())
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return ''
    return urlunparse((
        'https', parsed.netloc.lower(), parsed.path.rstrip('/') or '/', '',
        parsed.query, '',
    ))


def _is_allowed_url(url, allowed_hosts):
    host = urlparse(url).netloc.lower().split(':', 1)[0]
    return bool(host) and host in allowed_hosts


def _is_pdf_url(url, label):
    path = urlparse(url).path.lower()
    value = f'{path} {_normalize(label)}'
    return path.endswith('.pdf') or bool(re.search(r'\bpdf\b|download|unduh', value))


def _looks_like_document_link(url, label):
    value = _normalize(f'{url} {label}')
    return bool(re.search(r'produk|peraturan|dokumen|detail|putusan|unduh|download|regulasi', value))


def _looks_like_listing_link(url, label):
    value = _normalize(f'{url} {label}')
    return bool(re.search(r'produk|peraturan|dokumen|pencarian|search|page=|halaman|hukum', value))


def _title_from_url(url):
    name = unquote(urlparse(url).path.rstrip('/').rsplit('/', 1)[-1])
    name = re.sub(r'\.(pdf|html?)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]+', ' ', name)
    return _clean_text(name).title() or 'Dokumen JDIH'


def _clean_title(label, url, context):
    title = _clean_text(label)
    if not title or _normalize(title) in {'download', 'unduh', 'unduh pdf', 'lihat detail', 'pdf'}:
        title = _title_from_url(url)
    if not infer_ki_category(f'{title} {url}') and context:
        context_title = _clean_text(context.split('|', 1)[0])
        if infer_ki_category(context_title):
            title = f'{title} - {context_title}'
    return title[:255]


def _safe_filename(title):
    value = re.sub(r'[^a-zA-Z0-9]+', '-', _normalize(title)).strip('-')
    digest = hashlib.sha1(title.encode('utf-8')).hexdigest()[:8]
    return f'{value[:100] or "dokumen-jdih"}-{digest}'


def _sleep(seconds):
    import time
    time.sleep(seconds)
