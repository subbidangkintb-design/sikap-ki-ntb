from django.test import TestCase

from .models import CekMerekLog, MirrorPDKI
from .services import calculate_similarity_score, determine_risk, find_similar_trademarks


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

    def test_find_similar_trademarks_uses_same_or_adjacent_classes(self):
        results = find_similar_trademarks('Kopi Kita', ['30'], threshold=70)
        names = [item['nama'] for item in results]

        self.assertIn('KopiKita', names)
        self.assertIn('Kopi Kita Asli', names)
        self.assertNotIn('Sasak Lombok', names)
        self.assertEqual(results[0]['nama'], 'Kopi Kita')

    def test_determine_risk_is_high_for_strong_seed_cluster(self):
        results = find_similar_trademarks('Kopi Kita', ['30'], threshold=70)
        risk = determine_risk(results)

        self.assertEqual(risk, CekMerekLog.SkorRisiko.TINGGI)

    def test_determine_risk_is_low_when_no_similar_brand(self):
        risk = determine_risk([])

        self.assertEqual(risk, CekMerekLog.SkorRisiko.RENDAH)
