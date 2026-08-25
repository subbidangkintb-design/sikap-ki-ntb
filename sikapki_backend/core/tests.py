from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chatbot.models import PercakapanChatbot
from trademark.models import CekMerekLog, KlasifikasiMerekLog

from .models import MonitoringSnapshot, UjiCobaPengguna, UserProfile
from .http_client import configure_ai_network
from .audit import _json_value


class AccessControlTests(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user('regular', password='test-pass')
        self.staff_user = User.objects.create_user(
            'petugas', password='test-pass', is_staff=True,
        )
        UserProfile.objects.create(
            user=self.staff_user,
            role=UserProfile.Role.PETUGAS,
        )
        self.chat = PercakapanChatbot.objects.create(
            pertanyaan='Pertanyaan pengguna',
            jawaban='Jawaban layanan',
        )
        self.brand_log = CekMerekLog.objects.create(
            nama_merek_diajukan='Merek Rahasia',
            deskripsi_produk='Deskripsi usaha pengguna',
            kelas_nice_terdeteksi='30',
            skor_risiko=CekMerekLog.SkorRisiko.RENDAH,
        )
        self.classification_log = KlasifikasiMerekLog.objects.create(
            nama_merek_diajukan='Merek Uji Klasifikasi',
            deskripsi_produk='Kopi bubuk dalam kemasan',
            rekomendasi_kelas=[{'kelas': '30'}],
        )

    def test_public_can_read_faq_but_cannot_create_it(self):
        list_response = self.client.get(reverse('faq-list'))
        create_response = self.client.post(
            reverse('faq-list'),
            {'pertanyaan': 'FAQ baru?', 'jawaban': 'Jawaban'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_authenticated_user_cannot_change_knowledge(self):
        self.client.force_authenticate(self.regular_user)

        response = self.client.post(
            reverse('faq-list'),
            {'pertanyaan': 'FAQ baru?', 'jawaban': 'Jawaban'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_staff_can_change_knowledge(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.post(
            reverse('faq-list'),
            {'pertanyaan': 'FAQ petugas?', 'jawaban': 'Jawaban resmi'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_public_cannot_list_sensitive_service_records(self):
        chat_response = self.client.get(reverse('percakapanchatbot-list'))
        brand_response = self.client.get(reverse('cekmereklog-list'))
        classification_response = self.client.get(reverse('klasifikasimereklog-list'))

        self.assertEqual(chat_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(brand_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(classification_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_statistics_are_aggregate_only(self):
        response = self.client.get(reverse('statistik-layanan'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cek_merek_total'], 1)
        self.assertEqual(response.data['chatbot_total'], 1)
        self.assertNotIn('pertanyaan', response.data)
        self.assertNotIn('ip_pengguna', response.data)

    def test_public_statistics_support_safe_monitoring_periods(self):
        response = self.client.get(reverse('statistik-layanan'), {'days': 30})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['periode_hari'], 30)
        self.assertEqual(len(response.data['tren_periode']), 30)
        self.assertIn('kepatuhan_sla_persen', response.data['eskalasi'])
        self.assertIn('rata_rata_jam_tindak_lanjut', response.data['eskalasi'])

    def test_staff_can_read_but_cannot_create_sensitive_records_directly(self):
        self.client.force_authenticate(self.staff_user)

        chat_list = self.client.get(reverse('percakapanchatbot-list'))
        brand_list = self.client.get(reverse('cekmereklog-list'))
        classification_list = self.client.get(reverse('klasifikasimereklog-list'))
        chat_create = self.client.post(
            reverse('percakapanchatbot-list'),
            {'pertanyaan': 'Bypass', 'jawaban': 'Bypass'},
            format='json',
        )
        brand_create = self.client.post(
            reverse('cekmereklog-list'),
            {'nama_merek_diajukan': 'Bypass'},
            format='json',
        )

        self.assertEqual(chat_list.status_code, status.HTTP_200_OK)
        self.assertEqual(brand_list.status_code, status.HTTP_200_OK)
        self.assertEqual(classification_list.status_code, status.HTTP_200_OK)
        self.assertEqual(chat_create.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(brand_create.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
class AINetworkConfigurationTests(SimpleTestCase):
    @override_settings(AI_FORCE_IPV4=True)
    def test_force_ipv4_disables_urllib3_ipv6_resolution(self):
        with patch('core.http_client.connection.HAS_IPV6', True):
            configure_ai_network()

            from urllib3.util import connection
            self.assertFalse(connection.HAS_IPV6)


class AdminAuditSerializationTests(SimpleTestCase):
    def test_uuid_values_are_json_safe(self):
        value = uuid4()

        self.assertEqual(_json_value(value), str(value))


class AdminWorkspaceTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            'admin-workspace', 'admin@example.com', 'test-pass',
        )
        self.client.force_login(self.admin_user)

    def test_admin_index_emphasizes_daily_workflow(self):
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Tugas yang perlu ditangani')
        self.assertContains(response, 'Aksi cepat')
        self.assertContains(response, 'Konsultasi menunggu')
        self.assertContains(response, 'Ruang Kerja Petugas')


class PilotReadinessTests(APITestCase):
    def test_health_check_does_not_expose_secret(self):
        response = self.client.get(reverse('health-check'))

        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE))
        self.assertIn('ai_terkonfigurasi', response.data)
        self.assertNotIn('api_key', response.data)

    def test_container_health_check_alias_is_available(self):
        response = self.client.get(reverse('healthz'))

        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE))
        self.assertIn('database', response.data)

    def test_anonymous_user_test_is_recorded(self):
        response = self.client.post(reverse('uji-coba-pengguna'), {
            'peran': 'masyarakat', 'layanan': 'chatbot', 'tugas_berhasil': True,
            'kemudahan': 4, 'kejelasan': 5, 'kepercayaan': 4, 'kepuasan': 5,
            'masukan': 'Mudah dipahami.', 'persetujuan': True,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UjiCobaPengguna.objects.count(), 1)
        self.assertNotEqual(UjiCobaPengguna.objects.get().ip_hash, '127.0.0.1')

    def test_user_test_rejects_invalid_rating_and_missing_consent(self):
        response = self.client.post(reverse('uji-coba-pengguna'), {
            'peran': 'umkm', 'layanan': 'cek_merek', 'tugas_berhasil': False,
            'kemudahan': 6, 'kejelasan': 3, 'kepercayaan': 3, 'kepuasan': 2,
            'persetujuan': False,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UjiCobaPengguna.objects.count(), 0)
