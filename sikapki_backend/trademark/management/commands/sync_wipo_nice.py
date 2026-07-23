from __future__ import annotations

import io
import zipfile
from datetime import date
from xml.etree import ElementTree

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from trademark.models import NiceClassificationTerm


VERSION = 'NCL13-2026'
DATE_IN_FORCE = date(2026, 1, 1)
BASE_DOWNLOAD = 'https://www.wipo.int/classifications/data/nice/ITSupport_and_download_area/20260101/MasterFiles'
STRUCTURE_URL = f'{BASE_DOWNLOAD}/ncl-20260101-classification_top_structure-20250610.zip'
TEXTS_URL = f'{BASE_DOWNLOAD}/ncl-20260101-classification_texts-20251212.zip'
WIPO_CLASS_URL = (
    'https://nclpub.wipo.int/enfr/?basic_numbers=show&class_number={class_number}'
    '&lang=en&menulang=en&mode=flat&notion=&pagination=no&version=20260101'
)
USER_AGENT = 'SIKAP-KI-NTB/0.1 (Kanwil Kementerian Hukum NTB)'
MAX_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_XML_BYTES = 25 * 1024 * 1024
NAMESPACE = {'ncl': 'http://www.wipo.int/classifications/ncl'}


class Command(BaseCommand):
    help = 'Sinkronkan istilah resmi WIPO Nice Classification NCL 13-2026.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Validasi unduhan tanpa menyimpan database.')

    def handle(self, *args, **options):
        try:
            structure_xml = _download_xml_from_zip(STRUCTURE_URL)
            texts_xml = _download_xml_from_zip(TEXTS_URL, filename_contains='-en-')
            terms = _parse_terms(structure_xml, texts_xml)
        except (requests.RequestException, zipfile.BadZipFile, ElementTree.ParseError, ValueError) as exc:
            raise CommandError(f'Sinkronisasi WIPO Nice gagal: {exc}') from exc

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'DRY RUN OK: {len(terms)} istilah resmi {VERSION} berhasil divalidasi.',
            ))
            return

        with transaction.atomic():
            NiceClassificationTerm.objects.filter(
                source=NiceClassificationTerm.Source.WIPO,
            ).delete()
            NiceClassificationTerm.objects.bulk_create(terms, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f'{len(terms)} istilah resmi WIPO {VERSION} tersinkron. '
            'WIPO harus dicantumkan sebagai sumber klasifikasi.',
        ))


def _download_xml_from_zip(url: str, filename_contains: str | None = None) -> bytes:
    response = requests.get(
        url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/zip'}, timeout=(10, 90),
    )
    response.raise_for_status()
    if len(response.content) > MAX_ARCHIVE_BYTES:
        raise ValueError('Arsip WIPO melebihi batas aman 5 MB.')
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    candidates = [
        info for info in archive.infolist()
        if info.filename.lower().endswith('.xml')
        and (not filename_contains or filename_contains in info.filename)
    ]
    if len(candidates) != 1:
        raise ValueError(f'XML WIPO yang diharapkan tidak ditemukan secara unik pada {url}.')
    info = candidates[0]
    if info.file_size > MAX_XML_BYTES:
        raise ValueError('XML WIPO melebihi batas aman 25 MB.')
    return archive.read(info)


def _parse_terms(structure_xml: bytes, texts_xml: bytes) -> list[NiceClassificationTerm]:
    structure_root = ElementTree.fromstring(structure_xml)
    texts_root = ElementTree.fromstring(texts_xml)
    mapping = {}
    for class_element in structure_root.findall('ncl:Class', NAMESPACE):
        class_number = class_element.attrib['classNumber']
        for item in class_element.findall('ncl:GoodOrService', NAMESPACE):
            basic_number = f'{int(class_number):02d}{item.attrib["basicNumber"].zfill(4)}'
            mapping[item.attrib['id']] = (class_number, basic_number)

    terms = []
    goods_services = texts_root.find('ncl:GoodsAndServicesTexts', NAMESPACE)
    if goods_services is None:
        raise ValueError('Bagian GoodsAndServicesTexts tidak ditemukan.')
    for text_element in goods_services.findall('ncl:GoodOrServiceTexts', NAMESPACE):
        mapped = mapping.get(text_element.attrib.get('idRef'))
        if not mapped:
            continue
        indication = text_element.find('ncl:Indication/ncl:Label', NAMESPACE)
        if indication is None or not (indication.text or '').strip():
            continue
        synonyms = [
            (label.text or '').strip()
            for label in text_element.findall('ncl:SynonymIndication/ncl:Label', NAMESPACE)
            if (label.text or '').strip()
        ]
        class_number, basic_number = mapped
        terms.append(NiceClassificationTerm(
            class_number=class_number,
            basic_number=basic_number,
            indication_en=(indication.text or '').strip(),
            synonyms_en=synonyms,
            source=NiceClassificationTerm.Source.WIPO,
            version=VERSION,
            effective_date=DATE_IN_FORCE,
            source_url=WIPO_CLASS_URL.format(class_number=class_number),
        ))
    if len(terms) < 10_000:
        raise ValueError(f'Jumlah istilah terlalu sedikit ({len(terms)}); sinkronisasi dibatalkan.')
    return terms
