from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, utils

from chatbot.ai_client import generate_answer

from .models import CekMerekLog, MirrorPDKI


SIMILARITY_THRESHOLD = 70
DISCLAIMER = (
    'Hasil ini merupakan bantuan awal berbasis AI dan data pembanding yang tersedia, '
    'bukan jaminan hukum atau keputusan resmi pemeriksa merek.'
)


@lru_cache(maxsize=1)
def load_nice_classes() -> list[dict[str, str]]:
    path = Path(__file__).resolve().parent / 'nice_classification.json'
    return json.loads(path.read_text(encoding='utf-8'))


def classify_nice_classes(deskripsi_produk: str) -> list[str]:
    classes = load_nice_classes()
    reference = '\n'.join(
        f"Kelas {item['kelas']}: {item['deskripsi']}"
        for item in classes
    )
    prompt = (
        'Anda adalah asisten klasifikasi Nice untuk pendaftaran merek.\n'
        'Analisis deskripsi produk/jasa pengguna dan pilih 1 sampai 2 kelas Nice yang paling relevan.\n'
        'Gunakan hanya nomor kelas dari referensi 45 kelas berikut.\n'
        'Jawab HANYA dalam JSON valid dengan format: {"kelas": ["30", "43"], "alasan": "ringkas"}.\n\n'
        f'REFERENSI KELAS NICE:\n{reference}\n\n'
        f'DESKRIPSI PRODUK/JASA:\n{deskripsi_produk or "-"}'
    )
    response = generate_answer(prompt)
    return _extract_class_numbers(response)[:2]


def find_similar_trademarks(
    nama_merek: str,
    kelas_nice: list[str],
    threshold: int = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    target_classes = expand_adjacent_classes(kelas_nice)
    queryset = MirrorPDKI.objects.all()
    if target_classes:
        queryset = queryset.filter(kelas_nice__in=target_classes)

    matches = []
    for record in queryset:
        score = calculate_similarity_score(nama_merek, record.nama_merek)
        if score < threshold:
            continue
        matches.append({
            'id': record.id,
            'nama': record.nama_merek,
            'kelas': record.kelas_nice,
            'status': record.get_status_display(),
            'skor_kemiripan': score,
        })

    matches.sort(key=lambda item: item['skor_kemiripan'], reverse=True)
    return matches


def calculate_similarity_score(left: str, right: str) -> int:
    left_processed = utils.default_process(left or '') or ''
    right_processed = utils.default_process(right or '') or ''
    if not left_processed or not right_processed:
        return 0

    score = max(
        fuzz.WRatio(left_processed, right_processed),
        fuzz.token_set_ratio(left_processed, right_processed),
        fuzz.ratio(left_processed, right_processed),
    )
    return int(round(score))


def expand_adjacent_classes(kelas_nice: list[str]) -> list[str]:
    expanded = set()
    for kelas in kelas_nice:
        try:
            number = int(kelas)
        except (TypeError, ValueError):
            continue
        for candidate in (number - 1, number, number + 1):
            if 1 <= candidate <= 45:
                expanded.add(str(candidate))
    return sorted(expanded, key=int)


def determine_risk(similar_trademarks: list[dict[str, Any]]) -> str:
    if not similar_trademarks:
        return CekMerekLog.SkorRisiko.RENDAH

    highest = max(item['skor_kemiripan'] for item in similar_trademarks)
    strong_matches = sum(1 for item in similar_trademarks if item['skor_kemiripan'] >= 80)

    if highest >= 90 or strong_matches >= 3:
        return CekMerekLog.SkorRisiko.TINGGI
    if highest >= 75 or len(similar_trademarks) >= 2:
        return CekMerekLog.SkorRisiko.SEDANG
    return CekMerekLog.SkorRisiko.RENDAH


def build_advice_prompt(
    nama_merek: str,
    deskripsi_produk: str,
    kelas_nice: list[str],
    similar_trademarks: list[dict[str, Any]],
    skor_risiko: str,
) -> str:
    similar_text = json.dumps(similar_trademarks[:10], ensure_ascii=False, indent=2)
    return (
        'Anda adalah asisten awal pengecekan merek untuk UMKM.\n'
        'Buat saran naratif dalam Bahasa Indonesia yang mudah dipahami.\n'
        'Gunakan hanya data risiko dan daftar merek mirip berikut.\n'
        'PENTING: berikan HANYA saran nama alternatif berupa variasi kata dan arah pembeda visual dalam bentuk DESKRIPSI TEKS.\n'
        'Jangan membuat klaim hukum final, jangan menyatakan merek pasti diterima, dan jangan menghasilkan gambar.\n'
        'Selalu sertakan disclaimer bahwa ini bantuan awal, bukan jaminan hukum.\n\n'
        f'NAMA MEREK DIAJUKAN: {nama_merek}\n'
        f'DESKRIPSI PRODUK/JASA: {deskripsi_produk or "-"}\n'
        f'KELAS NICE TERDETEKSI: {", ".join(kelas_nice) or "-"}\n'
        f'SKOR RISIKO: {skor_risiko}\n'
        f'MEREK MIRIP:\n{similar_text}\n\n'
        'Susun jawaban dengan bagian: Ringkasan Risiko, Saran Nama Alternatif, Arah Pembeda Visual, Disclaimer.'
    )


def generate_brand_advice(
    nama_merek: str,
    deskripsi_produk: str,
    kelas_nice: list[str],
    similar_trademarks: list[dict[str, Any]],
    skor_risiko: str,
) -> str:
    return generate_answer(
        build_advice_prompt(
            nama_merek=nama_merek,
            deskripsi_produk=deskripsi_produk,
            kelas_nice=kelas_nice,
            similar_trademarks=similar_trademarks,
            skor_risiko=skor_risiko,
        )
    )


def _extract_class_numbers(text: str) -> list[str]:
    try:
        data = json.loads(_extract_json_object(text))
        raw_classes = data.get('kelas', [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        raw_classes = re.findall(r'\b(?:[1-9]|[1-3][0-9]|4[0-5])\b', text or '')

    valid = []
    seen = set()
    for item in raw_classes:
        kelas = str(item).strip()
        if not re.fullmatch(r'(?:[1-9]|[1-3][0-9]|4[0-5])', kelas):
            continue
        if kelas in seen:
            continue
        seen.add(kelas)
        valid.append(kelas)
    return valid


def _extract_json_object(text: str) -> str:
    start = (text or '').find('{')
    end = (text or '').rfind('}')
    if start == -1 or end == -1 or end < start:
        return text or ''
    return text[start:end + 1]
