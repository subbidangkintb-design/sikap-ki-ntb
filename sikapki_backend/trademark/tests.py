import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from .models import CekMerekLog, KlasifikasiMerekLog, MirrorPDKI, NiceClassificationTerm
from .pdki_sync import (
    BulletinData,
    BulletinRecord,
    extract_bulletin_labels,
    extract_bulletin_details,
    parse_bulletin,
    sync_bulletin,
)
from .services import (
    build_advice_prompt,
    calculate_goods_services_similarity,
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

    def test_find_similar_trademarks_includes_strong_cross_class_matches(self):
        results = find_similar_trademarks('Kopi Kita', ['30'], threshold=70)
        names = [item['nama'] for item in results]

        self.assertIn('KopiKita', names)
        self.assertIn('Kopi Kita Asli', names)
        self.assertNotIn('Sasak Lombok', names)
        self.assertEqual(results[0]['nama'], 'Kopi Kita')
        cross_class = next(item for item in results if item['nama'] == 'Kopi Kita Asli')
        self.assertFalse(cross_class['kelas_sesuai_rekomendasi'])

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

    def test_goods_services_are_scored_separately_from_brand_name(self):
        record = MirrorPDKI.objects.get(nama_merek='Kopi Kita')
        record.nomor_permohonan = 'DID2026000001'
        record.uraian_barang_jasa = 'kopi bubuk; kopi sangrai; minuman berbahan dasar kopi'
        record.save(update_fields=['nomor_permohonan', 'uraian_barang_jasa'])

        results = find_similar_trademarks(
            'Kopi Kita', ['30'], goods_services_description='produk kopi bubuk kemasan',
        )
        matched = next(item for item in results if item['nama'] == 'Kopi Kita')

        self.assertEqual(matched['nomor_permohonan'], 'DID2026000001')
        self.assertEqual(matched['uraian_barang_jasa'], record.uraian_barang_jasa)
        self.assertGreaterEqual(matched['skor_kesesuaian_barang_jasa'], 60)
        self.assertIn(matched['hubungan_barang_jasa'], {'Sangat terkait', 'Sebagian terkait'})
        self.assertGreater(
            calculate_goods_services_similarity('kopi bubuk', 'kopi bubuk dan kopi sangrai'),
            calculate_goods_services_similarity('kopi bubuk', 'jasa perbaikan kendaraan'),
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


class TrademarkClassificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.classification = {
            'kelas': ['30'],
            'perlu_klarifikasi': False,
            'pertanyaan_klarifikasi': '',
            'sumber_klasifikasi': 'WIPO Nice Classification NCL 13-2026',
            'opsi_kelas': [
                {
                    'kelas': '30',
                    'keyakinan': 0.96,
                    'alasan': 'Cocok dengan istilah resmi WIPO: coffee.',
                    'deskripsi_kelas': 'Kopi, teh, kakao dan penggantinya.',
                    'istilah_resmi': [{
                        'istilah': 'coffee',
                        'basic_number': '300026',
                        'skor': 96,
                        'frasa_pencarian': 'coffee',
                        'sumber_url': 'https://nclpub.wipo.int/',
                    }],
                    'sumber': 'WIPO Nice Classification NCL 13-2026',
                    'sumber_url': 'https://nclpub.wipo.int/',
                    'skm_url': 'https://skm.dgip.go.id/index.php/skm/detailkelas/30',
                },
            ],
        }

    @patch('trademark.views.classify_nice_classes')
    def test_response_contains_classification_but_no_similarity_assessment(self, classify_mock):
        classify_mock.return_value = self.classification
        response = self.client.post(
            reverse('trademark-cek-ai'),
            {
                'nama_merek': 'Kopi Kita',
                'deskripsi_produk': 'Kopi bubuk dalam kemasan',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['rekomendasi_kelas'][0]['kelas'], '30')
        self.assertFalse(response.data['logo_dinilai'])
        self.assertIn('pdki', response.data['tautan_resmi'])
        self.assertNotIn('merek_mirip', response.data)
        self.assertNotIn('skor_risiko', response.data)
        self.assertNotIn('persentase_kemiripan', response.data)
        log = KlasifikasiMerekLog.objects.get(pk=response.data['id'])
        self.assertEqual(log.rekomendasi_kelas[0]['kelas'], '30')

    @patch('trademark.views.classify_nice_classes')
    def test_ambiguous_classification_returns_options_and_clarification(self, classify_mock):
        classify_mock.return_value = {
            **self.classification,
            'kelas': [],
            'perlu_klarifikasi': True,
            'pertanyaan_klarifikasi': 'Apakah kopi dijual kemasan atau disajikan di kafe?',
        }

        response = self.client.post(
            reverse('trademark-cek-ai'),
            {'nama_merek': 'Kopi Kita', 'deskripsi_produk': 'Usaha kopi'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['perlu_klarifikasi'])
        self.assertEqual(len(response.data['rekomendasi_kelas']), 1)
        self.assertTrue(KlasifikasiMerekLog.objects.get().perlu_klarifikasi)

    @patch('trademark.views.classify_nice_classes')
    def test_uploaded_logo_is_not_assessed_or_stored(self, classify_mock):
        classify_mock.return_value = self.classification
        upload = SimpleUploadedFile(
            'logo-pengguna.png',
            b'konten tidak dibaca oleh alur klasifikasi',
            content_type='image/png',
        )
        response = self.client.post(
            reverse('trademark-cek-ai'),
            {
                'nama_merek': 'Kopi Kita',
                'deskripsi_produk': 'Kopi bubuk dalam kemasan.',
                'logo_merek': upload,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['logo_dinilai'])
        log = KlasifikasiMerekLog.objects.get(pk=response.data['id'])
        self.assertTrue(log.logo_disertakan)
        self.assertNotIn('logo-pengguna.png', str(log.rekomendasi_kelas))
        self.assertFalse(CekMerekLog.objects.exists())

    @override_settings(AI_TRADEMARK_CHECK_ENABLED=False)
    def test_optional_similarity_feature_is_hidden_when_disabled(self):
        feature_response = self.client.get(reverse('trademark-fitur'))
        check_response = self.client.post(
            reverse('trademark-cek-kemiripan-ai'),
            {'nama_merek': 'Kopi Kita', 'deskripsi_produk': 'Kopi bubuk kemasan'},
            format='json',
        )

        self.assertFalse(feature_response.data['ai_cek_merek_aktif'])
        self.assertEqual(check_response.status_code, 404)

    @override_settings(AI_TRADEMARK_CHECK_ENABLED=True)
    @patch('trademark.views.classify_nice_classes')
    def test_optional_similarity_feature_can_be_enabled(self, classify_mock):
        classify_mock.return_value = self.classification
        MirrorPDKI.objects.create(
            nama_merek='KOPI KITA',
            nomor_permohonan='DID2026000999',
            kelas_nice='30',
            status=MirrorPDKI.Status.TERDAFTAR,
            pemilik='Pemilik pembanding',
            uraian_barang_jasa='kopi bubuk; kopi sangrai; minuman berbahan dasar kopi',
            sumber_data_url='https://pdki-indonesia.dgip.go.id/',
        )

        feature_response = self.client.get(reverse('trademark-fitur'))
        check_response = self.client.post(
            reverse('trademark-cek-kemiripan-ai'),
            {'nama_merek': 'Kopi Kita', 'deskripsi_produk': 'Kopi bubuk kemasan'},
            format='json',
        )

        self.assertTrue(feature_response.data['ai_cek_merek_aktif'])
        self.assertEqual(check_response.status_code, 201)
        self.assertEqual(check_response.data['kelas_nice_dianalisis'], ['30'])
        self.assertEqual(check_response.data['kandidat_pembanding'][0]['nama'], 'KOPI KITA')
        self.assertEqual(
            check_response.data['kandidat_pembanding'][0]['nomor_permohonan'],
            'DID2026000999',
        )
        self.assertTrue(
            check_response.data['kandidat_pembanding'][0]['uraian_barang_jasa'],
        )
        self.assertEqual(check_response.data['cakupan_data']['uraian_barang_jasa_tersedia'], 1)
        self.assertGreaterEqual(check_response.data['indikator_tertinggi'], 80)
        self.assertEqual(CekMerekLog.objects.count(), 1)


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
    def test_detail_parser_maps_owner_and_description_per_class(self, reader_mock):
        detail_text = (
            'Alamat Pemohon\nNama Pemohon :\n:\nDian Lestari\nJl. Contoh\n'
            '511 Kelas Barang/Jasa : 05, 30\n'
            '510 Uraian Barang/Jasa : ===minuman suplemen kesehatan===\n'
            '===teh kombucha; minuman berbahan dasar teh===\n'
            'Nomor Permohonan\nTanggal Penerimaan\n540 EtiketDID2024098054\n'
        )
        reader_mock.return_value = SimpleNamespace(
            pages=[SimpleNamespace(extract_text=lambda: detail_text)],
        )

        details = extract_bulletin_details(io.BytesIO(b'%PDF-fake'))

        self.assertEqual(details['DID2024098054'].pemilik, 'Dian Lestari')
        self.assertEqual(
            details['DID2024098054'].uraian_per_kelas['5'],
            'minuman suplemen kesehatan',
        )
        self.assertIn('teh kombucha', details['DID2024098054'].uraian_per_kelas['30'])

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

    @patch('trademark.pdki_sync.extract_bulletin_details', return_value={})
    @patch('trademark.pdki_sync.parse_bulletin')
    @patch('trademark.pdki_sync.download_bulletin')
    def test_sync_is_idempotent_per_application_and_class(
        self, download_mock, parse_mock, _details_mock,
    ):
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

    @patch('trademark.pdki_sync.extract_bulletin_details', return_value={})
    @patch('trademark.pdki_sync.parse_bulletin')
    @patch('trademark.pdki_sync.download_bulletin')
    def test_older_archive_does_not_overwrite_newer_publication(
        self, download_mock, parse_mock, _details_mock,
    ):
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
