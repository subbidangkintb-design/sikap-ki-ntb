import uuid
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .admin import PercakapanChatbotAdmin
from .models import PercakapanChatbot
from .views import (
    SIMILARITY_THRESHOLD,
    _build_prompt,
    _build_retrieval_query,
    _calculate_confidence,
    _is_context_dependent_question,
    _rerank_chunks,
)
from .expertise import analyze_question, build_clarification_message, enrich_retrieval_query


class KIExpertiseRoutingTests(SimpleTestCase):
    def test_routes_all_major_ki_domains(self):
        cases = {
            'Apakah nama usaha saya bisa menjadi merek?': 'Merek',
            'Bagaimana melindungi lagu yang saya ciptakan?': 'Hak Cipta',
            'Apa syarat kebaruan untuk paten sederhana?': 'Paten',
            'Saya ingin melindungi tampilan estetis produk': 'Desain Industri',
            'Apa syarat produk khas daerah menjadi indikasi geografis?': 'Indikasi Geografis',
            'Bagaimana mendaftarkan tata letak chip DTLST?': 'DTLST',
            'Bagaimana menjaga formula sebagai rahasia dagang?': 'Rahasia Dagang',
            'Bagaimana mencatat ekspresi budaya tradisional?': 'Kekayaan Intelektual Komunal',
            'Siapa yang dapat mengajukan perlindungan varietas tanaman?': 'Perlindungan Varietas Tanaman',
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertIn(expected, analyze_question(question).domains)

    def test_ambiguous_protection_request_asks_for_object(self):
        profile = analyze_question('Saya mau mendaftarkan dan melindungi hasil usaha saya')

        self.assertTrue(profile.needs_clarification)
        self.assertIn('objek apa', build_clarification_message())

    def test_routes_protection_type_recommendation_across_domains(self):
        profile = analyze_question(
            'Usaha kedai kopi dengan nama merek LUMIHAUS bagusnya didaftarkan '
            'sebagai Hak Cipta, merek, atau indikasi geografis?',
        )

        self.assertEqual(profile.intent, 'pemilihan_rezim')
        self.assertIn('Merek', profile.domains)
        self.assertIn('Hak Cipta', profile.domains)
        self.assertIn('Indikasi Geografis', profile.domains)
        self.assertFalse(profile.needs_clarification)

    def test_high_stakes_dispute_is_detected(self):
        profile = analyze_question('Logo merek saya dipakai tanpa izin, apakah harus gugat?')

        self.assertEqual(profile.intent, 'pelanggaran')
        self.assertTrue(profile.high_stakes)

    def test_retrieval_query_is_enriched_with_domain_and_intent(self):
        profile = analyze_question('Berapa biaya permohonan paten?')
        query = enrich_retrieval_query('Berapa biaya permohonan paten?', profile)

        self.assertIn('Jenis KI: Paten', query)
        self.assertIn('Tarif dan PNBP resmi', query)


class ChatbotConfidenceTests(SimpleTestCase):
    def test_relevant_chunks_pass_threshold(self):
        chunks = [{'distance': 0.31}, {'distance': 0.42}]

        self.assertGreaterEqual(_calculate_confidence(chunks), SIMILARITY_THRESHOLD)

    def test_generic_chunks_trigger_escalation_threshold(self):
        chunks = [{'distance': 0.46}, {'distance': 0.49}]

        self.assertLess(_calculate_confidence(chunks), SIMILARITY_THRESHOLD)

    def test_missing_chunks_have_zero_confidence(self):
        self.assertEqual(_calculate_confidence([]), 0.0)

    def test_answer_prompt_requires_readable_sections(self):
        prompt = _build_prompt('Apa syarat daftar merek?', [{
            'text': 'Pemohon menyiapkan etiket merek.',
            'metadata': {'judul': 'Panduan Merek', 'kategori': 'Merek'},
        }])

        self.assertIn('### Jawaban singkat', prompt)
        self.assertIn('### Rincian', prompt)
        self.assertIn('### Langkah berikutnya', prompt)
        self.assertIn('maksimal sekitar 300 kata', prompt)

    def test_follow_up_question_uses_previous_topic_for_retrieval(self):
        history = [{
            'pertanyaan': 'Bagaimana cara mendaftarkan merek?',
            'jawaban': 'Permohonan merek diajukan melalui layanan resmi.',
        }]

        query = _build_retrieval_query('Apa saja syaratnya?', history)

        self.assertIn('mendaftarkan merek', query)
        self.assertIn('Apa saja syaratnya?', query)

    def test_explicit_new_topic_does_not_use_old_history(self):
        history = [{
            'pertanyaan': 'Bagaimana cara mendaftarkan merek?',
            'jawaban': 'Permohonan merek diajukan melalui layanan resmi.',
        }]

        query = _build_retrieval_query('Bagaimana cara mendaftarkan hak cipta?', history)

        self.assertEqual(query, 'Bagaimana cara mendaftarkan hak cipta?')

    def test_common_indonesian_references_are_context_dependent(self):
        self.assertTrue(_is_context_dependent_question('Apa saja syaratnya?'))
        self.assertTrue(_is_context_dependent_question('Biaya nya berapa?'))
        self.assertTrue(_is_context_dependent_question('Setelah itu bagaimana?'))
        self.assertFalse(_is_context_dependent_question('Apa itu merek kolektif?'))

    def test_prompt_includes_history_but_keeps_verified_context_authoritative(self):
        prompt = _build_prompt(
            'Apa saja syaratnya?',
            [{'text': 'Syarat resmi.', 'metadata': {'judul': 'Panduan'}}],
            [{'pertanyaan': 'Cara daftar merek?', 'jawaban': 'Tahapan awal.'}],
        )

        self.assertIn('RIWAYAT PERCAKAPAN', prompt)
        self.assertIn('Cara daftar merek?', prompt)
        self.assertIn('Fakta jawaban tetap wajib berasal dari KONTEKS TERVERIFIKASI', prompt)

    def test_reranking_prioritizes_specific_official_requirements(self):
        chunks = [
            {
                'distance': 0.20,
                'text': 'Nama pribadi dapat digunakan sebagai merek.',
                'metadata': {'judul': 'FAQ nama pribadi', 'source_type': 'faq_internal'},
            },
            {
                'distance': 0.30,
                'text': (
                    'Persyaratan minimum terdiri atas formulir Permohonan yang telah diisi lengkap, '
                    'label Merek, dan bukti pembayaran biaya.'
                ),
                'metadata': {'judul': 'UU Merek', 'source_type': 'dokumen_resmi'},
            },
        ]

        ranked = _rerank_chunks(
            'Apa saja syaratnya?',
            [{'pertanyaan': 'Bagaimana cara mendaftarkan merek?', 'jawaban': '...'}],
            chunks,
        )

        self.assertEqual(ranked[0]['metadata']['judul'], 'UU Merek')


class PercakapanChatbotAdminTests(SimpleTestCase):
    def test_confidence_badge_formats_numeric_score(self):
        percakapan = PercakapanChatbot(confidence_score=0.7403)
        model_admin = PercakapanChatbotAdmin(PercakapanChatbot, AdminSite())

        badge = model_admin.confidence_badge(percakapan)

        self.assertIn('0.74', badge)


class HumanOversightWorkflowTests(TestCase):
    def test_escalated_conversation_enters_waiting_queue(self):
        conversation = PercakapanChatbot.objects.create(
            pertanyaan='Pertanyaan kompleks', jawaban='Silakan hubungi petugas.',
            dieskalasi=True,
        )

        self.assertEqual(
            conversation.status_tindak_lanjut,
            PercakapanChatbot.StatusTindakLanjut.MENUNGGU,
        )
        self.assertIsNotNone(conversation.batas_tindak_lanjut)

    def test_completed_follow_up_records_timestamps(self):
        conversation = PercakapanChatbot.objects.create(
            pertanyaan='Pertanyaan kompleks', jawaban='Silakan hubungi petugas.',
            dieskalasi=True,
        )
        conversation.status_tindak_lanjut = PercakapanChatbot.StatusTindakLanjut.SELESAI
        conversation.catatan_tindak_lanjut = 'Sudah dikonfirmasi oleh petugas.'
        conversation.save()

        self.assertIsNotNone(conversation.ditinjau_pada)
        self.assertIsNotNone(conversation.diselesaikan_pada)


class MultiTurnChatbotAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sesi_id = uuid.uuid4()
        self.chunks = [{
            'distance': 0.2,
            'text': 'Pendaftaran merek memerlukan etiket dan identitas pemohon.',
            'metadata': {'judul': 'Panduan Pendaftaran Merek', 'kategori': 'Merek'},
        }]

    @patch('chatbot.views.generate_answer')
    @patch('chatbot.views.retrieve_relevant_chunks')
    def test_follow_up_request_reuses_server_side_session_history(self, retrieve, generate):
        retrieve.return_value = self.chunks
        generate.side_effect = [
            'Pendaftaran dilakukan melalui layanan merek.',
            'Syaratnya meliputi etiket dan identitas pemohon.',
        ]

        first = self.client.post('/api/chatbot/tanya/', {
            'pertanyaan': 'Bagaimana cara daftar merek?',
            'sesi_id': str(self.sesi_id),
        }, format='json')
        second = self.client.post('/api/chatbot/tanya/', {
            'pertanyaan': 'Apa saja syaratnya?',
            'sesi_id': str(self.sesi_id),
        }, format='json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data['sesi_id'], str(self.sesi_id))
        self.assertEqual(second.data['sesi_id'], str(self.sesi_id))
        self.assertIn('cara daftar merek', retrieve.call_args_list[1].args[0].lower())
        self.assertIn('Apa saja syaratnya?', retrieve.call_args_list[1].args[0])
        self.assertEqual(PercakapanChatbot.objects.filter(sesi_id=self.sesi_id).count(), 2)


class PublicConsultationTrackingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.conversation = PercakapanChatbot.objects.create(
            pertanyaan='Pertanyaan kompleks dan bersifat pribadi',
            jawaban='Pertanyaan diteruskan kepada petugas.',
            dieskalasi=True,
        )

    def test_random_tracking_token_exposes_status_but_not_question(self):
        response = self.client.get(reverse(
            'chatbot-status', args=[self.conversation.pelacakan_id],
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'menunggu')
        self.assertTrue(response.data['kode_konsultasi'].startswith('KI-'))
        self.assertNotIn('pertanyaan', response.data)
        self.assertNotIn('catatan_tindak_lanjut', response.data)

    def test_staff_correction_is_visible_as_public_follow_up_answer(self):
        self.conversation.jawaban_koreksi = 'Jawaban yang sudah ditinjau petugas.'
        self.conversation.status_tindak_lanjut = PercakapanChatbot.StatusTindakLanjut.SELESAI
        self.conversation.save()

        response = self.client.get(reverse(
            'chatbot-status', args=[self.conversation.pelacakan_id],
        ))

        self.assertEqual(response.data['jawaban_petugas'], 'Jawaban yang sudah ditinjau petugas.')
        self.assertEqual(response.data['status'], 'selesai')
