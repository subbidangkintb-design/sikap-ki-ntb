"""Deterministic routing for the multi-domain KI assistant.

This module identifies a likely KI domain and service intent. It never supplies
legal facts; facts must still come from verified RAG sources.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


DOMAIN_TERMS = {
    'Merek': (
        'merek', 'nama merek', 'brand', 'logo', 'nama usaha', 'nama produk', 'kelas nice',
        'merek dagang', 'merek jasa',
    ),
    'Hak Cipta': (
        'hak cipta', 'ciptaan', 'pencipta', 'copyright', 'lagu', 'musik', 'buku',
        'film', 'foto', 'fotografi', 'program komputer', 'software', 'aplikasi',
        'karya seni', 'konten', 'royalti',
    ),
    'Paten': (
        'paten', 'invensi', 'inventor', 'teknologi', 'paten sederhana',
        'langkah inventif', 'klaim paten',
    ),
    'Desain Industri': (
        'desain industri', 'desain produk', 'tampilan produk', 'bentuk produk',
        'konfigurasi produk', 'kesan estetis', 'tampilan estetis',
    ),
    'Indikasi Geografis': (
        'indikasi geografis', 'produk khas daerah', 'reputasi daerah',
        'asal geografis', 'geographical indication',
    ),
    'DTLST': (
        'dtlst', 'desain tata letak sirkuit terpadu', 'tata letak chip',
        'layout chip', 'sirkuit terpadu', 'integrated circuit',
    ),
    'Rahasia Dagang': (
        'rahasia dagang', 'trade secret', 'informasi rahasia', 'resep rahasia',
        'formula rahasia', 'metode bisnis rahasia', 'nda',
    ),
    'Kekayaan Intelektual Komunal': (
        'ki komunal', 'kik', 'ekspresi budaya tradisional', 'pengetahuan tradisional',
        'sumber daya genetik', 'potensi indikasi geografis', 'warisan budaya',
        'masyarakat adat', 'komunal',
    ),
    'Perlindungan Varietas Tanaman': (
        'perlindungan varietas tanaman', 'pvt', 'varietas tanaman', 'pemulia tanaman',
    ),
}

INTENT_TERMS = {
    'persyaratan': ('syarat', 'dokumen', 'berkas', 'lampiran', 'kelengkapan'),
    'prosedur': ('cara', 'bagaimana', 'tahap', 'alur', 'prosedur', 'mengajukan', 'mendaftar'),
    'biaya': ('biaya', 'tarif', 'pnbp', 'bayar', 'pembayaran'),
    'jangka_waktu': ('berapa lama', 'jangka waktu', 'masa berlaku', 'kedaluwarsa', 'daluarsa'),
    'definisi': ('apa itu', 'pengertian', 'definisi', 'dimaksud dengan'),
    'pemilihan_rezim': (
        'cocok', 'cocoknya', 'bagusnya', 'sebaiknya', 'paling tepat', 'yang tepat',
        'jenis ki', 'dilindungi apa', 'perlindungan apa', 'daftar apa',
        'daftarkan kemana', 'didaftarkan kemana', 'pilih yang mana',
    ),
    'pelanggaran': ('pelanggaran', 'menjiplak', 'meniru', 'dipakai tanpa izin', 'sengketa', 'gugat'),
    'lisensi_pengalihan': ('lisensi', 'pengalihan', 'jual hak', 'waris', 'royalti'),
    'perbandingan': ('perbedaan', 'beda', 'dibandingkan', 'versus', ' vs '),
    'status_penelusuran': ('status permohonan', 'cek status', 'penelusuran', 'sudah terdaftar'),
}

HIGH_STAKES_INTENTS = {'pelanggaran', 'lisensi_pengalihan'}


@dataclass(frozen=True)
class ExpertiseProfile:
    domains: tuple[str, ...]
    intent: str
    high_stakes: bool
    needs_clarification: bool

    @property
    def domain_label(self):
        return ', '.join(self.domains) if self.domains else 'KI umum/lintas jenis'


def analyze_question(question: str, history=None) -> ExpertiseProfile:
    normalized = _normalize(question)
    history_text = ' '.join(item.get('pertanyaan', '') for item in (history or [])[-2:])
    routing_text = normalized
    if _looks_context_dependent(normalized):
        routing_text = f'{_normalize(history_text)} {normalized}'.strip()

    scored = []
    for domain, terms in DOMAIN_TERMS.items():
        score = sum(
            3 if ' ' in term else 1
            for term in terms if _contains_term(routing_text, term)
        )
        if score:
            scored.append((score, domain))
    scored.sort(key=lambda item: (-item[0], item[1]))
    best_score = scored[0][0] if scored else 0
    domains = tuple(domain for score, domain in scored if score >= max(1, best_score - 1))[:3]

    intent_scores = [
        (sum(_contains_term(normalized, term) for term in terms), intent)
        for intent, terms in INTENT_TERMS.items()
    ]
    intent_priority = {
        'pemilihan_rezim': 3,
        'perbandingan': 2,
        'prosedur': 1,
    }
    intent_score, intent = max(
        intent_scores,
        key=lambda item: (item[0], intent_priority.get(item[1], 0)),
        default=(0, 'informasi_umum'),
    )
    if intent_score == 0:
        intent = 'informasi_umum'

    # A recommendation/comparison must retain every explicitly named KI type;
    # detailed wording about one object should not hide the alternatives.
    if intent in {'pemilihan_rezim', 'perbandingan'}:
        domains = tuple(domain for _, domain in scored[:3])

    asks_for_protection = any(_contains_term(normalized, term) for term in (
        'lindungi', 'melindungi', 'perlindungan', 'daftar', 'mendaftarkan',
        'hak apa', 'jenis ki',
    ))
    general_ki = any(_contains_term(normalized, term) for term in ('kekayaan intelektual', 'semua jenis ki', 'ki itu'))
    needs_clarification = asks_for_protection and not domains and not general_ki
    return ExpertiseProfile(
        domains=domains,
        intent=intent,
        high_stakes=intent in HIGH_STAKES_INTENTS,
        needs_clarification=needs_clarification,
    )


def build_clarification_message() -> str:
    return (
        '### Perlu sedikit informasi\n'
        'Agar saya dapat menentukan jenis Kekayaan Intelektual yang relevan, objek apa yang ingin Anda lindungi?\n\n'
        'Pilih atau jelaskan yang paling mendekati:\n'
        '- nama, logo, atau tanda pembeda usaha;\n'
        '- tulisan, musik, foto, video, seni, atau program komputer;\n'
        '- invensi atau solusi teknis;\n'
        '- tampilan estetis suatu produk;\n'
        '- produk khas yang terkait daerah asal;\n'
        '- informasi bisnis yang dijaga rahasia;\n'
        '- tata letak sirkuit terpadu; atau\n'
        '- pengetahuan, budaya, atau sumber daya yang dimiliki secara komunal.\n\n'
        'Sebutkan juga siapa pemiliknya, apakah sudah diumumkan/dijual, dan tujuan Anda '
        '(mencatatkan, mendaftarkan, memberi lisensi, atau menangani dugaan pelanggaran).'
    )


def enrich_retrieval_query(question: str, profile: ExpertiseProfile) -> str:
    domain_part = f'Jenis KI: {profile.domain_label}.'
    intent_labels = {
        'persyaratan': 'Persyaratan dan dokumen resmi',
        'prosedur': 'Tata cara, tahapan, dan kanal permohonan resmi',
        'biaya': 'Tarif dan PNBP resmi yang berlaku',
        'jangka_waktu': 'Jangka waktu proses dan masa pelindungan',
        'definisi': 'Definisi, objek, dan ruang lingkup pelindungan',
        'pemilihan_rezim': 'Pemilihan jenis pelindungan KI yang tepat',
        'pelanggaran': 'Penanganan dugaan pelanggaran dan batas layanan informasi awal',
        'lisensi_pengalihan': 'Lisensi, pengalihan hak, dan pencatatannya',
        'perbandingan': 'Perbedaan objek, syarat, dan mekanisme antarjenis KI',
        'status_penelusuran': 'Penelusuran dan status permohonan melalui sumber resmi',
    }
    intent_part = intent_labels.get(profile.intent, 'Informasi layanan Kekayaan Intelektual')
    return f'{domain_part}\nKebutuhan: {intent_part}.\nPertanyaan pengguna: {question}'


def _looks_context_dependent(text):
    return bool(re.search(
        r'\b(itu|ini|tersebut|tadi|syaratnya|syarat\s+nya|biayanya|biaya\s+nya|'
        r'prosesnya|proses\s+nya|persyaratannya|persyaratan\s+nya|selanjutnya)\b',
        text,
    ))


def _normalize(value):
    return re.sub(r'\s+', ' ', str(value or '').lower()).strip()


def _contains_term(text, term):
    return bool(re.search(rf'(?<!\w){re.escape(term)}(?!\w)', text))
