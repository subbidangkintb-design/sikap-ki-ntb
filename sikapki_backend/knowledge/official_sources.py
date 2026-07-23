from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class OfficialSource:
    category: str
    title: str
    url: str


def _djki_sources(category, slug):
    base = f'https://www.dgip.go.id/menu-utama/{slug}'
    return (
        OfficialSource(category, f'{category} - Pengenalan Resmi DJKI', f'{base}/pengenalan'),
        OfficialSource(category, f'{category} - Syarat dan Prosedur DJKI', f'{base}/syarat-prosedur'),
        OfficialSource(category, f'{category} - Biaya Layanan DJKI', f'{base}/biaya'),
    )


OFFICIAL_SOURCES = (
    *_djki_sources('Hak Cipta', 'hak-cipta'),
    *_djki_sources('Paten', 'paten'),
    *_djki_sources('Desain Industri', 'desain-industri'),
    *_djki_sources('Indikasi Geografis', 'indikasi-geografis'),
    *_djki_sources('DTLST', 'dtlst'),
    *_djki_sources('Rahasia Dagang', 'rahasia-dagang'),
    OfficialSource(
        'Kekayaan Intelektual Komunal', 'KIK - Pengenalan Resmi DJKI',
        'https://www.dgip.go.id/menu-utama/ki-komunal/pengenalan',
    ),
    OfficialSource(
        'Kekayaan Intelektual Komunal', 'KIK - Syarat dan Prosedur DJKI',
        'https://www.dgip.go.id/menu-utama/ki-komunal/syarat-prosedur',
    ),
    OfficialSource(
        'Perlindungan Varietas Tanaman', 'PVT - Standar Pelayanan Permohonan Hak PVT',
        'https://ppvtpp.setjen.pertanian.go.id/publikasi/spp-layanan/'
        'ijnlt-1756283523/test-spp',
    ),
    OfficialSource(
        'Perlindungan Varietas Tanaman', 'PVT - Pengenalan Sistem Perlindungan Varietas Tanaman',
        'https://ppvtpp.setjen.pertanian.go.id/publikasi/kegiatan/'
        'qktul-1720781043/mengenal-lebih-dekat-sistem-perlindungan-varietas-tanaman',
    ),
    OfficialSource(
        'Perlindungan Varietas Tanaman', 'PVT - Layanan Permohonan melalui Apply PVT',
        'https://ppvtpp.setjen.pertanian.go.id/publikasi/kegiatan/'
        'pmcpa-1735456539/permohonan-lebih-mudah-dan-cepat-melalui-apply-pvt',
    ),
)


class OfficialPageParser(HTMLParser):
    """Extract readable page text while excluding navigation and boilerplate."""

    BLOCKS = {'p', 'div', 'li', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr'}
    IGNORED = {'script', 'style', 'svg', 'nav', 'footer', 'header', 'form'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._main_depth = 0
        self._ignored_depth = 0
        self._saw_main = False
        self.parts = []
        self.main_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self._main_depth += 1
            self._saw_main = True
        if tag in self.IGNORED:
            self._ignored_depth += 1
        if self._active and tag in self.BLOCKS:
            self._append('\n')

    def handle_endtag(self, tag):
        if self._active and tag in self.BLOCKS:
            self._append('\n')
        if tag in self.IGNORED and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == 'main' and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data):
        if self._active:
            self._append(data)

    def _append(self, value):
        self.parts.append(value)
        if self._main_depth:
            self.main_parts.append(value)

    @property
    def _active(self):
        return not self._ignored_depth


def extract_official_page_text(html):
    parser = OfficialPageParser()
    parser.feed(html)
    parser.close()
    text = ' '.join(parser.main_parts if parser._saw_main else parser.parts)
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    # DJKI pages place this heading immediately before universal contact/footer content.
    text = re.split(r'\n\s*Alamat Kantor\s*\n', text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip()
