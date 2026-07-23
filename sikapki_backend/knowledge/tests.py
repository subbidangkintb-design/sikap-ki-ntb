from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter

from .admin import DokumenResmiAdminForm
from .faq_sync import FAQSyncError, ScrapedFAQ, parse_faq_page, sync_faq_items
from .official_sources import extract_official_page_text
from .models import DokumenResmi, FAQ
from .rag_service import (
    _extract_pdf_with_gemini_ocr, _get_document_text, chunk_document,
    embed_and_store, generate_embeddings,
)


class DocumentExtractionTests(SimpleTestCase):
    def test_chunk_document_keeps_overlap(self):
        chunks = chunk_document('satu dua tiga empat lima', chunk_size=3, overlap=1)

        self.assertEqual(chunks, ['satu dua tiga', 'tiga empat lima'])

    @patch('knowledge.rag_service.PdfReader')
    def test_pdf_text_is_extracted_per_page(self, pdf_reader):
        pdf_reader.return_value.pages = [
            MagicMock(extract_text=MagicMock(return_value='Halaman pertama')),
            MagicMock(extract_text=MagicMock(return_value='Halaman kedua')),
        ]
        dokumen = SimpleNamespace(
            teks_lengkap='',
            file_asli=SimpleUploadedFile('panduan.pdf', b'%PDF-test'),
        )

        text = _get_document_text(dokumen)

        self.assertEqual(text, 'Halaman pertama\n\nHalaman kedua')

    def test_manual_text_has_priority_over_uploaded_file(self):
        dokumen = SimpleNamespace(
            teks_lengkap='Teks yang sudah divalidasi petugas',
            file_asli=SimpleUploadedFile('panduan.pdf', b'%PDF-test'),
        )

        self.assertEqual(_get_document_text(dokumen), dokumen.teks_lengkap)

    @override_settings(PDF_OCR_WITH_GEMINI=True)
    @patch('knowledge.rag_service._extract_pdf_with_gemini_ocr', return_value='Teks hasil OCR')
    @patch('knowledge.rag_service.PdfReader')
    def test_image_only_pdf_uses_cloud_ocr_fallback(self, pdf_reader, ocr_mock):
        pdf_reader.return_value.pages = [MagicMock(extract_text=MagicMock(return_value=''))]
        dokumen = SimpleNamespace(
            teks_lengkap='',
            file_asli=SimpleUploadedFile('scan.pdf', b'%PDF-test'),
        )

        self.assertEqual(_get_document_text(dokumen), 'Teks hasil OCR')
        ocr_mock.assert_called_once()


class DocumentValidationTests(TestCase):
    @patch('knowledge.rag_service.remove_document_from_index')
    def test_draft_document_is_not_embedded(self, remove_document):
        dokumen = DokumenResmi.objects.create(
            judul='Dokumen yang belum diverifikasi',
            teks_lengkap='Isi dokumen draf.',
        )

        chunk_count = embed_and_store(dokumen.id)

        self.assertEqual(chunk_count, 0)
        remove_document.assert_called_once_with(dokumen.id)

    def test_verified_document_is_queued_without_embedding_in_save_request(self):
        dokumen = DokumenResmi.objects.create(
            judul='Dokumen antrean', teks_lengkap='Isi yang dapat dicari.',
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
        )

        dokumen.refresh_from_db()

        self.assertEqual(dokumen.status_indexing, DokumenResmi.StatusIndexing.MENUNGGU)

    @patch('knowledge.management.commands.process_document_queue.embed_and_store', return_value=3)
    def test_queue_command_claims_pending_document(self, embed_mock):
        dokumen = DokumenResmi.objects.create(
            judul='Dokumen untuk worker', teks_lengkap='Isi dokumen worker.',
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
        )

        call_command('process_document_queue', limit=1)

        embed_mock.assert_called_once_with(dokumen.id)


class LargeDocumentAdminFormTests(SimpleTestCase):
    @staticmethod
    def make_pdf(page_count):
        stream = __import__('io').BytesIO()
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=595, height=842)
        writer.write(stream)
        return SimpleUploadedFile('panduan-besar.pdf', stream.getvalue(), content_type='application/pdf')

    def test_pdf_over_100_pages_is_accepted_and_counted(self):
        form = DokumenResmiAdminForm(
            data={'judul': 'Panduan 120 halaman', 'status_validasi': 'draf'},
            files={'file_asli': self.make_pdf(120)},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.document_page_count, 120)

    @override_settings(MAX_DOCUMENT_UPLOAD_SIZE=10)
    def test_document_over_size_limit_is_rejected(self):
        form = DokumenResmiAdminForm(
            data={'judul': 'Terlalu besar', 'status_validasi': 'draf'},
            files={'file_asli': SimpleUploadedFile('besar.txt', b'lebih dari sepuluh byte')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Ukuran dokumen maksimal', str(form.errors))


class DocumentAdminPageTests(TestCase):
    def test_add_page_renders_for_staff(self):
        user = get_user_model().objects.create_superuser(
            username='admin-dokumen', email='admin@example.com', password='test-password',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('admin:knowledge_dokumenresmi_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PDF/TXT/MD maksimal 100 MB')


class EmbeddingBatchTests(SimpleTestCase):
    @override_settings(
        GEMINI_API_KEY='test-key', GEMINI_BASE_URL='https://example.test',
        GEMINI_EMBEDDING_MODEL='gemini-embedding-2', GEMINI_EMBEDDING_DIMENSIONS=2,
        GEMINI_EMBEDDING_BATCH_SIZE=20,
    )
    @patch('knowledge.rag_service.configure_ai_network')
    @patch('knowledge.rag_service.requests.post')
    def test_embeddings_are_sent_in_batches(self, post_mock, _network_mock):
        def response_for_batch(*_args, **kwargs):
            response = MagicMock()
            response.json.return_value = {
                'embeddings': [{'values': [3, 4]} for _ in kwargs['json']['requests']],
            }
            return response

        post_mock.side_effect = response_for_batch

        embeddings = generate_embeddings([f'potongan {number}' for number in range(45)])

        self.assertEqual(len(embeddings), 45)
        self.assertEqual(post_mock.call_count, 3)
        self.assertEqual(embeddings[0], [0.6, 0.8])


class DJKIFAQParserTests(SimpleTestCase):
    def test_parser_extracts_questions_answers_and_pagination(self):
        html = '''
        <main>
          <h5>1. Apa syarat label merek?</h5>
          <p>Format JPG.</p><ul><li>Maksimal 5 MB</li></ul>
          <h5>2. Di mana cek kelas?</h5><p>Cek pada SKM DJKI.</p>
          <nav aria-label="Page navigation example"><ul class="pagination">
            <li><a href="/faq/daftar-faq/merek/Merek-Permohonan?page=1" aria-label="Sebelumnya">« Sebelumnya</a></li>
            <li><a href="/faq/daftar-faq/merek/Merek-Permohonan?page=2">2</a></li>
            <li><a href="/faq/daftar-faq/merek/Merek-Permohonan?page=2" aria-label="Selanjutnya">» Selanjutnya</a></li>
          </ul></nav>
        </main><footer><h4>Alamat Kantor</h4></footer>
        '''

        items, links = parse_faq_page(
            html, 'https://dgip.go.id/faq/daftar-faq/merek/Merek-Permohonan',
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].pertanyaan, 'Apa syarat label merek?')
        self.assertIn('Maksimal 5 MB', items[0].jawaban)
        self.assertNotIn('Sebelumnya', items[-1].jawaban)
        self.assertNotIn('Selanjutnya', items[-1].jawaban)
        self.assertNotIn('«', items[-1].jawaban)
        self.assertTrue(any('page=2' in link for link in links))

    def test_blocked_page_is_rejected(self):
        from knowledge.faq_sync import _looks_blocked

        self.assertTrue(_looks_blocked(
            '<meta name="ROBOTS" content="NOINDEX, NOFOLLOW">Request unsuccessful. '
            '/_Incapsula_Resource',
        ))


class OfficialSourceParserTests(SimpleTestCase):
    def test_extracts_main_content_without_navigation_or_footer(self):
        html = '''
        <html><head><title>Judul situs</title></head><body>
          <nav>Menu yang tidak boleh masuk</nav>
          <main><h1>Paten</h1><p>Paten melindungi invensi teknologi.</p></main>
          <footer>Alamat Kantor dan media sosial</footer>
        </body></html>
        '''

        text = extract_official_page_text(html)

        self.assertIn('Paten melindungi invensi teknologi.', text)
        self.assertNotIn('Menu yang tidak boleh masuk', text)
        self.assertNotIn('media sosial', text)


class DJKIFAQSyncTests(TestCase):
    @patch('knowledge.faq_sync.remove_faq_from_index')
    def test_new_external_faq_is_saved_as_draft(self, remove_mock):
        item = ScrapedFAQ(
            'Apa itu merek?', 'Merek adalah tanda pembeda.', 'Merek Umum',
            'https://dgip.go.id/faq/daftar-faq/merek/merek',
        )

        result = sync_faq_items([item])
        faq = FAQ.objects.get()

        self.assertEqual(result['baru'], 1)
        self.assertEqual(faq.status_validasi, FAQ.StatusValidasi.DRAF)
        self.assertTrue(faq.aktif_sumber)
        remove_mock.assert_not_called()

    @patch('knowledge.faq_sync.remove_faq_from_index')
    def test_changed_verified_faq_requires_reverification(self, remove_mock):
        original = ScrapedFAQ(
            'Apa itu merek?', 'Jawaban lama.', 'Merek Umum',
            'https://dgip.go.id/faq/daftar-faq/merek/merek',
        )
        sync_faq_items([original])
        faq = FAQ.objects.get()
        FAQ.objects.filter(pk=faq.pk).update(
            status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
            status_indexing=FAQ.StatusIndexing.BERHASIL,
            vector_id=f'faq_{faq.id}',
        )
        changed = ScrapedFAQ(
            original.pertanyaan, 'Jawaban resmi yang diperbarui.', original.subkategori,
            original.sumber_url,
        )

        result = sync_faq_items([changed])
        faq.refresh_from_db()

        self.assertEqual(result['diperbarui'], 1)
        self.assertEqual(faq.status_validasi, FAQ.StatusValidasi.DRAF)
        self.assertEqual(faq.status_indexing, FAQ.StatusIndexing.BELUM)
        remove_mock.assert_called_once_with(faq.id)

    @patch('knowledge.faq_sync.remove_faq_from_index')
    def test_full_sync_only_deactivates_faq_in_selected_category(self, remove_mock):
        merek = ScrapedFAQ(
            'Apa itu merek?', 'Merek adalah tanda pembeda.', 'Merek Umum',
            'https://dgip.go.id/faq/daftar-faq/merek/merek',
        )
        paten = ScrapedFAQ(
            'Apa itu paten?', 'Paten melindungi invensi.', 'Paten Umum',
            'https://dgip.go.id/faq/daftar-faq/paten/paten',
        )
        sync_faq_items([merek], category_name='Merek')
        sync_faq_items([paten], category_name='Paten')

        result = sync_faq_items([], full_sync=True, category_name='Merek')

        merek_faq = FAQ.objects.get(pertanyaan='Apa itu merek?')
        paten_faq = FAQ.objects.get(pertanyaan='Apa itu paten?')
        self.assertEqual(result['dinonaktifkan'], 1)
        self.assertFalse(merek_faq.aktif_sumber)
        self.assertTrue(paten_faq.aktif_sumber)
        remove_mock.assert_called_once_with(merek_faq.id)


class PdfCloudOcrTests(SimpleTestCase):
    @override_settings(
        GEMINI_API_KEY='test-key', GEMINI_BASE_URL='https://example.test',
        GEMINI_OCR_MODEL='gemini-test', PDF_OCR_BATCH_PAGES=2,
    )
    @patch('knowledge.rag_service.configure_ai_network')
    @patch('knowledge.rag_service.requests.post')
    def test_scanned_pdf_is_transcribed_in_page_batches(self, post_mock, _network_mock):
        stream = __import__('io').BytesIO()
        writer = PdfWriter()
        for _ in range(5):
            writer.add_blank_page(width=595, height=842)
        writer.write(stream)
        stream.seek(0)
        post_mock.return_value.json.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'Teks halaman'}]}}],
        }

        result = _extract_pdf_with_gemini_ocr(stream)

        self.assertEqual(post_mock.call_count, 3)
        self.assertIn('Halaman 1-2', result)
        self.assertIn('Halaman 5-5', result)
