"""Curated catalog of primary KI legislation (UU/PP) sourced from peraturan.bpk.go.id.

Unlike `jdih_sync` (which discovers candidate documents by crawling a JDIH index)
this list is manually curated and verified: each entry was checked against BPK's
own "Status Peraturan" metadata to confirm it is either unamended or, where it has
been amended, its full amendment chain is included as separate entries so a
petugas can see the whole picture before verifying (this module deliberately never
tries to "resolve" which amendment is currently authoritative on its own).

Every import lands as a draft DokumenResmi, exactly like every other source in this
app — nothing here is ever auto-verified.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LawSource:
    category: str
    title: str
    detail_url: str
    pdf_url: str


LAW_SOURCES = (
    LawSource(
        'Hak Cipta', 'UU No. 28 Tahun 2014 tentang Hak Cipta',
        'https://peraturan.bpk.go.id/Details/38690/uu-no-28-tahun-2014',
        'https://peraturan.bpk.go.id/Download/28018/UU%20Nomor%2028%20Tahun%202014.pdf',
    ),
    LawSource(
        'Desain Industri', 'UU No. 31 Tahun 2000 tentang Desain Industri',
        'https://peraturan.bpk.go.id/Details/45076/uu-no-31-tahun-2000',
        'https://peraturan.bpk.go.id/Download/33520/UU%20Nomor%2031%20Tahun%202000.pdf',
    ),
    LawSource(
        'Rahasia Dagang', 'UU No. 30 Tahun 2000 tentang Rahasia Dagang',
        'https://peraturan.bpk.go.id/Details/45002/uu-no-30-tahun-2000',
        'https://peraturan.bpk.go.id/Download/33395/UU%20Nomor%2030%20Tahun%202000.pdf',
    ),
    LawSource(
        'DTLST', 'UU No. 32 Tahun 2000 tentang Desain Tata Letak Sirkuit Terpadu',
        'https://peraturan.bpk.go.id/Details/45236/uu-no-32-tahun-2000',
        'https://peraturan.bpk.go.id/Download/33720/UU%20Nomor%2032%20Tahun%202000.pdf',
    ),
    # Paten: UU 13/2016 telah diamandemen 3 kali. Semua diimpor terpisah supaya
    # petugas bisa menilai sendiri ketentuan mana yang masih berlaku, alih-alih
    # chatbot mengutip satu versi yang seolah-olah lengkap.
    LawSource(
        'Paten', 'UU No. 13 Tahun 2016 tentang Paten (teks asli)',
        'https://peraturan.bpk.go.id/Details/37536/uu-no-13-tahun-2016',
        'https://peraturan.bpk.go.id/Download/26629/UU%20Nomor%2013%20Tahun%202016.pdf',
    ),
    LawSource(
        'Paten', 'UU No. 11 Tahun 2020 tentang Cipta Kerja (mengubah UU Paten)',
        'https://peraturan.bpk.go.id/Details/149750/uu-no-11-tahun-2020',
        'https://peraturan.bpk.go.id/Download/153567/UU_Nomor_11_Tahun_2020-compressed.pdf',
    ),
    LawSource(
        'Paten', 'PERPU No. 2 Tahun 2022 tentang Cipta Kerja (mengubah UU Paten)',
        'https://peraturan.bpk.go.id/Details/234926/perpu-no-2-tahun-2022',
        'https://peraturan.bpk.go.id/Download/287447/Perpu%20Nomor%202%20Tahun%202022.pdf',
    ),
    LawSource(
        'Paten', 'UU No. 6 Tahun 2023 tentang Penetapan PERPU 2/2022 (Cipta Kerja) menjadi UU',
        'https://peraturan.bpk.go.id/Details/246523/uu-no-6-tahun-2023',
        'https://peraturan.bpk.go.id/Download/302681/UU%20Nomor%206%20Tahun%202023.pdf',
    ),
    LawSource(
        'Paten', 'UU No. 65 Tahun 2024 tentang Perubahan Ketiga atas UU No. 13 Tahun 2016 tentang Paten',
        'https://peraturan.bpk.go.id/Details/306515/uu-no-65-tahun-2024',
        'https://peraturan.bpk.go.id/Download/366767/UU%20Nomor%2065%20Tahun%202024.pdf',
    ),
    # PVT: UU 29/2000 juga tersentuh Cipta Kerja lewat UU yang sama dengan Paten.
    LawSource(
        'Perlindungan Varietas Tanaman', 'UU No. 29 Tahun 2000 tentang Perlindungan Varietas Tanaman (teks asli)',
        'https://peraturan.bpk.go.id/Details/45000/uu-no-29-tahun-2000',
        'https://peraturan.bpk.go.id/Download/33393/UU%20Nomor%2029%20Tahun%202000.pdf',
    ),
    LawSource(
        'Perlindungan Varietas Tanaman',
        'UU No. 6 Tahun 2023 tentang Penetapan PERPU 2/2022 (Cipta Kerja) menjadi UU',
        'https://peraturan.bpk.go.id/Details/246523/uu-no-6-tahun-2023',
        'https://peraturan.bpk.go.id/Download/302681/UU%20Nomor%206%20Tahun%202023.pdf',
    ),
    LawSource(
        'Indikasi Geografis', 'PP No. 51 Tahun 2007 tentang Indikasi Geografis',
        'https://peraturan.bpk.go.id/Details/4773/pp-no-51-tahun-2007',
        'https://peraturan.bpk.go.id/Download/37888/PP%2051%20Tahun%202007.pdf',
    ),
    LawSource(
        'Kekayaan Intelektual Komunal', 'PP No. 56 Tahun 2022 tentang Kekayaan Intelektual Komunal',
        'https://peraturan.bpk.go.id/Details/233504/pp-no-56-tahun-2022',
        'https://peraturan.bpk.go.id/Download/284126/PP%20Nomor%2056%20Tahun%202022.pdf',
    ),
)
