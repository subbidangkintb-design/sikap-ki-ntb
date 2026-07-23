import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from .models import CekMerekLog, MirrorPDKI, NiceClassificationTerm
from .pdki_sync import (
    BulletinData,
    BulletinRecord,
    extract_bulletin_labels,
    parse_bulletin,
    sync_bulletin,
)
from .services import (
    build_advice_prompt,
    calculate_similarity_percentage,
    calculate_similarity_score,
    calculate_visual_similarity,
    determine_risk,
    explain_similarity,
    find_similar_trademarks,
    load_nice_classes,
    _match_wipo_nice_terms,
    _parse_nice_classification,
    normalize_current_kanwil_name,
    validate_logo_upload,
)


class TrademarkSimilarityTests(TestCase):
    def setUp(self):
        self.seed_like_records = [
            ('KopiKita', '30'),
            ('Kopi Kita', '30'),
            ('KopiKita Premium', '30'),
            ('Kopikita Nusantara', '30'),
            ('Kopi Kita Asli', '29'),
            ('Sasak Lombok', '25'),
        ]
        for nama_merek, kelas_nice in self.seed_like_records:
            MirrorPDKI.objects.create(
                nama_merek=nama_merek,
                kelas_nice=kelas_nice,
                status=MirrorPDKI.Status.TERDAFTAR,
                pemilik='Dummy Seed Owner',
            )

    def test_calculate_similarity_score_handles_spacing_and_case(self):
        score = calculate_similarity_score('kopi kita', 'KopiKita')

        self.assertGreaterEqual(score, 90)

    def test_find_similar_trademarks_uses_only_selected_classes(self):
        results = find_similar_trademarks('Kopi Kita', ['30'], threshold=70)
        names = [item['nama'] for item in results]

        self.assertIn('KopiKita', names)
        self.assertNotIn('Kopi Kita Asli', names)
        self.assertNotIn('Sasak Lombok', names)
        self.assertEqual(results[0]['nama'], 'Kopi Kita')

    def test_short_brand_does_not_match_unrelated_substrings(self):
        self.assertLess(calculate_similarity_score('BENSU', '64 BEANS THE HOME OF CHOFFY'), 72)
        self.assertLess(calculate_similarity_score('BENSU', 'Absensi Tanpa Batas'), 72)
        self.assertGreaterEqual(calculate_similarity_score('BENSU', 'GEPREK BENSU'), 90)

    def test_generic_coffee_word_does_not_hide_distinctive_brand_token(self):
        MirrorPDKI.objects.create(
            nama_merek='SEMBALUN COFFEE', nomor_permohonan='DID2024001473',
            kelas_nice='30', status=MirrorPDKI.Status.DIAJUKAN, pemilik='Pemohon resmi',
        )
        MirrorPDKI.objects.create(
            nama_merek='KEDAI KOPI SATU SEMBILAN', nomor_permohonan='DID2026000001',
            kelas_nice='30', status=MirrorPDKI.Status.DIAJUKAN, pemilik='Pemohon lain',
        )
        MirrorPDKI.objects.create(
            nama_merek='LEMBAH SEMBALUN', nomor_permohonan='DID2025000001',
            kelas_nice='30', status=MirrorPDKI.Status.DIAJUKAN, pemilik='Pemohon lain',
        )

        results = find_similar_trademarks('KOPI SEMBALUN', ['30'], threshold=70)

        self.assertEqual(results[0]['nama'], 'SEMBALUN COFFEE')
        self.assertEqual(results[0]['skor_kemiripan'], 100)
        self.assertGreater(
            calculate_similarity_score('KOPI SEMBALUN', 'SEMBALUN COFFEE'),
            calculate_similarity_score('KOPI SEMBALUN', 'KEDAI KOPI SATU SEMBILAN'),
        )

    def test_determine_risk_is_high_for_strong_seed_cluster(self):
        results = find_similar_trademarks('Kopi Kita', ['30'], threshold=70)
        risk = determine_risk(results)

        self.assertEqual(risk, CekMerekLog.SkorRisiko.TINGGI)

    def test_determine_risk_is_low_when_no_similar_brand(self):
        risk = determine_risk([])

        self.assertEqual(risk, CekMerekLog.SkorRisiko.RENDAH)

    def test_similarity_percentage_uses_highest_match(self):
        results = find_similar_trademarks('Kopi Kita', ['30'])

        self.assertEqual(
            calculate_similarity_percentage(results),
            results[0]['skor_kemiripan'],
        )

    def test_advice_prompt_forbids_brand_name_suggestions(self):
        prompt = build_advice_prompt('Kopi Kita', 'Produk kopi', ['30'], [], 'rendah')

        self.assertIn('JANGAN membuat atau menyarankan nama merek alternatif', prompt)
        self.assertIn(
            'Helpdesk KI Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat', prompt,
        )
        self.assertIn('### Ringkasan hasil', prompt)
        self.assertIn('### Hal yang perlu ditinjau', prompt)
        self.assertIn('### Langkah berikutnya', prompt)
        self.assertIn('Jangan membuat bagian Disclaimer', prompt)
        self.assertIn('Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat', prompt)
        self.assertNotIn('Kanwil Kemenkumham NTB', prompt)

    def test_obsolete_ministry_names_are_normalized_in_advice(self):
        for obsolete in [
            'Kanwil Kemenkumham NTB',
            'Kanwil Kementerian Hukum dan HAM Nusa Tenggara Barat',
            'Kemenkum NTB',
        ]:
            result = normalize_current_kanwil_name(f'Hubungi {obsolete} untuk bantuan.')
            self.assertEqual(
                result,
                'Hubungi Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat untuk bantuan.',
            )

    def test_visual_similarity_and_combined_score(self):
        record = MirrorPDKI.objects.get(nama_merek='Kopi Kita')
        record.visual_embedding = [1.0, 0.0]
        record.save(update_fields=['visual_embedding'])

        results = find_similar_trademarks(
            'Kopi Kita', ['30'], threshold=70, query_visual_embedding=[1.0, 0.0],
        )
        matched = next(item for item in results if item['nama'] == 'Kopi Kita')

        self.assertEqual(calculate_visual_similarity([1.0, 0.0], [1.0, 0.0]), 100)
        self.assertEqual(matched['skor_visual'], 100)
        self.assertEqual(matched['skor_gabungan'], 100)

    def test_similarity_explanation_is_specific_and_transparent(self):
        explanation = explain_similarity('Kopi Sembalun', 'Sembalun Coffee', 100, None)

        self.assertTrue(explanation)
        self.assertTrue(any('pembeda' in item.lower() for item in explanation))

    def test_logo_validation_rejects_non_image(self):
        upload = SimpleUploadedFile('logo.png', b'bukan gambar', content_type='image/png')

        with self.assertRaisesRegex(ValueError, 'PNG atau JPEG'):
            validate_logo_upload(upload)


class TrademarkLogoApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        MirrorPDKI.objects.create(
            nama_merek='Kopi Kita', kelas_nice='30', status=MirrorPDKI.Status.TERDAFTAR,
            pemilik='Pemilik Referensi', visual_embedding=[1.0, 0.0],
        )

    @staticmethod
    def make_logo():
        stream = io.BytesIO()
        Image.new('RGB', (128, 128), color=(20, 70, 140)).save(stream, format='PNG')
        return SimpleUploadedFile('logo-pengguna.png', stream.getvalue(), content_type='image/png')

    @patch('trademark.views.generate_brand_advice', return_value='Hubungi Helpdesk KI Kanwil.')
    @patch('trademark.views.classify_nice_classes', return_value=['30'])
    @patch('trademark.views.generate_image_embedding', return_value=[1.0, 0.0])
    def test_multipart_logo_returns_visual_score_without_storing_file(self, *_mocks):
        response = self.client.post(
            reverse('trademark-cek-ai'),
            {
                'nama_merek': 'Kopi Kita',
                'deskripsi_produk': 'Kopi bubuk',
                'kelas_nice_dipilih': ['30'],
                'logo_merek': self.make_logo(),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['logo_dianalisis'])
        self.assertEqual(response.data['referensi_visual_dibandingkan'], 1)
        self.assertEqual(response.data['persentase_kemiripan_visual'], 100)
        self.assertEqual(response.data['cakupan_data']['total_pembanding_kelas'], 1)
        self.assertEqual(response.data['cakupan_data']['visual_siap_dibandingkan'], 1)
        self.assertTrue(response.data['metodologi'])
        self.assertTrue(response.data['merek_mirip'][0]['alasan_kemiripan'])
        log = CekMerekLog.objects.get(pk=response.data['id'])
        self.assertNotIn('logo-pengguna.png', str(log.hasil_lengkap))

    @patch('trademark.views.classify_nice_classes')
    def test_ambiguous_classification_returns_options_without_creating_log(self, classify_mock):
        classify_mock.return_value = {
            'kelas': [],
            'perlu_klarifikasi': True,
            'pertanyaan_klarifikasi': 'Apakah kopi dijual kemasan atau disajikan di kafe?',
            'opsi_kelas': [
                {'kelas': '30', 'keyakinan': 0.76, 'alasan': 'kopi kemasan', 'deskripsi_kelas': 'Kopi.'},
                {'kelas': '43', 'keyakinan': 0.74, 'alasan': 'layanan kafe', 'deskripsi_kelas': 'Kafe.'},
            ],
        }

        response = self.client.post(
            reverse('trademark-cek-ai'),
            {'nama_merek': 'Kopi Kita', 'deskripsi_produk': 'Usaha kopi'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['perlu_klarifikasi'])
        self.assertEqual(len(response.data['opsi_kelas']), 2)
        self.assertFalse(CekMerekLog.objects.exists())

    @patch('trademark.views.generate_brand_advice', return_value='### Ringkasan hasil\nAman.')
    @patch('trademark.views.classify_nice_classes')
    def test_user_selected_class_bypasses_ai_classification(self, classify_mock, _advice_mock):
        response = self.client.post(
            reverse('trademark-cek-ai'),
            {
                'nama_merek': 'Kopi Kita',
                'deskripsi_produk': 'Kopi disajikan untuk diminum di tempat.',
                'kelas_nice_dipilih': ['43'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['kelas_nice_terdeteksi'], ['43'])
        self.assertEqual(response.data['sumber_klasifikasi'], 'dipilih_pengguna')
        classify_mock.assert_not_called()


class NiceClassificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for class_number, basic_number, indication in [
            ('43', '430102', 'restaurant services'),
            ('41', '410028', 'orchestra services'),
            ('16', '160408', 'tissue paper'),
            ('3', '030251', 'baby wipes impregnated with cleaning preparations'),
            ('1', '010146', 'carbonates'),
            ('1', '010176', 'industrial chemicals'),
            ('5', '050069', 'pharmaceutical preparations'),
        ]:
            NiceClassificationTerm.objects.create(
                class_number=class_number,
                basic_number=basic_number,
                indication_en=indication,
                source=NiceClassificationTerm.Source.WIPO,
                version='NCL13-2026',
                effective_date=date(2026, 1, 1),
                source_url=f'https://nclpub.wipo.int/class/{class_number}',
            )

    def test_wipo_exact_term_is_primary_and_filters_distractors(self):
        result = _match_wipo_nice_terms(
            ['restaurant services'], 'jasa restoran untuk makan di tempat',
        )

        self.assertEqual(result['kelas'], ['43'])
        self.assertEqual([item['kelas'] for item in result['opsi_kelas']], ['43'])
        self.assertEqual(result['opsi_kelas'][0]['istilah_resmi'][0]['basic_number'], '430102')
        self.assertIn('WIPO', result['sumber_klasifikasi'])

    def test_wipo_alternative_interpretations_require_clarification(self):
        result = _match_wipo_nice_terms(
            ['tissue paper', 'baby wipes impregnated with cleaning preparations'],
            'produk tisu untuk pelanggan',
            model_needs_context=True,
        )

        self.assertTrue(result['perlu_klarifikasi'])
        self.assertEqual(
            {item['kelas'] for item in result['opsi_kelas']},
            {'3', '16'},
        )

    def test_purpose_phrases_keep_official_class_options_visible(self):
        result = _match_wipo_nice_terms(
            [
                'calcium carbonate for industrial purposes',
                'calcium carbonate for pharmaceutical purposes',
            ],
            'kalsium karbonat', model_needs_context=True,
        )

        self.assertTrue(result['perlu_klarifikasi'])
        self.assertEqual(
            {item['kelas'] for item in result['opsi_kelas']},
            {'1', '5'},
        )

    def test_clear_high_confidence_class_is_accepted(self):
        response = '{"kandidat":[{"kelas":"43","keyakinan":0.94,"alasan":"jasa restoran"}],"perlu_klarifikasi":false,"pertanyaan_klarifikasi":""}'

        result = _parse_nice_classification(
            response, 'jasa restoran dengan makanan yang disantap di tempat', load_nice_classes(),
        )

        self.assertFalse(result['perlu_klarifikasi'])
        self.assertEqual(result['kelas'], ['43'])

    def test_close_candidate_scores_require_confirmation(self):
        response = '{"kandidat":[{"kelas":"30","keyakinan":0.86,"alasan":"kopi bubuk"},{"kelas":"43","keyakinan":0.82,"alasan":"layanan kafe"}],"perlu_klarifikasi":false,"pertanyaan_klarifikasi":""}'

        result = _parse_nice_classification(
            response, 'usaha kopi untuk pelanggan', load_nice_classes(),
        )

        self.assertTrue(result['perlu_klarifikasi'])
        self.assertEqual([item['kelas'] for item in result['opsi_kelas']], ['30', '43'])

    def test_short_description_requires_confirmation(self):
        response = '{"kandidat":[{"kelas":"25","keyakinan":0.97,"alasan":"pakaian"}],"perlu_klarifikasi":false,"pertanyaan_klarifikasi":""}'

        result = _parse_nice_classification(response, 'usaha baju', load_nice_classes())

        self.assertTrue(result['perlu_klarifikasi'])

    def test_class_mentioned_in_question_is_added_as_option(self):
        response = '{"kandidat":[{"kelas":"16","keyakinan":0.95,"alasan":"tisu kertas"}],"perlu_klarifikasi":true,"pertanyaan_klarifikasi":"Apakah tisu kertas kelas 16 atau tisu basah kosmetik kelas 3?"}'

        result = _parse_nice_classification(response, 'produk tisu', load_nice_classes())

        self.assertEqual([item['kelas'] for item in result['opsi_kelas']], ['16', '3'])


class BeritaResmiMerekSyncTests(TestCase):
    @patch('trademark.pdki_sync.PdfReader')
    def test_label_parser_pairs_images_across_page_boundaries(self, reader_mock):
        label_a = Image.new('RGB', (120, 80), 'red')
        label_b = Image.new('RGB', (80, 120), 'blue')
        reader_mock.return_value = SimpleNamespace(pages=[
            SimpleNamespace(extract_text=lambda: 'SAMPUL', images=[SimpleNamespace(image=label_a)]),
            SimpleNamespace(
                extract_text=lambda: '540 EtiketDID2026060001',
                images=[SimpleNamespace(image=label_a)],
            ),
            SimpleNamespace(extract_text=lambda: '540 EtiketDID2026060002', images=[]),
            SimpleNamespace(extract_text=lambda: 'lanjutan data', images=[SimpleNamespace(image=label_b)]),
        ])

        labels = extract_bulletin_labels(io.BytesIO(b'%PDF-fake'))

        self.assertEqual(set(labels), {'DID2026060001', 'DID2026060002'})
        self.assertTrue(all(value.startswith(b'\xff\xd8') for value in labels.values()))

    @patch('trademark.pdki_sync.PdfReader')
    def test_parser_reads_toc_and_multiple_classes(self, reader_mock):
        pages = [
            'BERITA RESMI MEREK SERI-A\nNo. 141/P-M/VII/A/2026\nDIUMUMKAN TANGGAL 15 JULI 2026 - 15 SEPTEMBER 2026',
            'No Nomor Permohonan Tanggal Penerimaan Kelas Merek\n1 DID2026060001 10/07/2026 30 KOPI AMAN\n2 DID2026060002 11/07/2026 35, 43 WARUNG AMAN',
            '',
            '',
        ]
        reader_mock.return_value = SimpleNamespace(
            pages=[SimpleNamespace(extract_text=lambda value=value: value) for value in pages],
        )

        result = parse_bulletin(io.BytesIO(b'%PDF-fake'))

        self.assertEqual(result.title, 'Berita Resmi Merek Seri-A No. 141/P-M/VII/A/2026')
        self.assertEqual(result.publication_date, date(2026, 7, 15))
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.records[1].kelas, ('35', '43'))

    @patch('trademark.pdki_sync.parse_bulletin')
    @patch('trademark.pdki_sync.download_bulletin')
    def test_sync_is_idempotent_per_application_and_class(self, download_mock, parse_mock):
        download_mock.return_value = io.BytesIO(b'%PDF-fake')
        parse_mock.return_value = BulletinData(
            title='BRM Uji',
            publication_date=date(2026, 7, 15),
            records=(BulletinRecord(
                nomor_permohonan='DID2026060002',
                tanggal_penerimaan=date(2026, 7, 11),
                kelas=('35', '43'),
                nama_merek='WARUNG AMAN',
            ),),
        )
        url = 'https://www.dgip.go.id/berita-resmi/9999/download'

        first = sync_bulletin(url, include_labels=False)
        second = sync_bulletin(url, force=True, include_labels=False)

        self.assertEqual(first.jumlah_baru, 2)
        self.assertEqual(second.jumlah_baru, 0)
        self.assertEqual(second.jumlah_diperbarui, 2)
        self.assertEqual(MirrorPDKI.objects.filter(nomor_permohonan='DID2026060002').count(), 2)

    @patch('trademark.pdki_sync.parse_bulletin')
    @patch('trademark.pdki_sync.download_bulletin')
    def test_older_archive_does_not_overwrite_newer_publication(self, download_mock, parse_mock):
        download_mock.side_effect = [io.BytesIO(b'%PDF-new'), io.BytesIO(b'%PDF-old')]
        parse_mock.side_effect = [
            BulletinData(
                title='BRM Baru', publication_date=date(2026, 7, 15),
                records=(BulletinRecord('DID2026060003', date(2026, 7, 1), ('43',), 'MEREK BARU'),),
            ),
            BulletinData(
                title='BRM Lama', publication_date=date(2025, 7, 15),
                records=(BulletinRecord('DID2026060003', date(2026, 7, 1), ('43',), 'MEREK LAMA'),),
            ),
        ]

        sync_bulletin('https://www.dgip.go.id/berita-resmi/200/download', include_labels=False)
        sync_bulletin('https://www.dgip.go.id/berita-resmi/100/download', include_labels=False)

        record = MirrorPDKI.objects.get(nomor_permohonan='DID2026060003', kelas_nice='43')
        self.assertEqual(record.nama_merek, 'MEREK BARU')
        self.assertEqual(record.sumber_data_url, 'https://www.dgip.go.id/berita-resmi/200/download')
