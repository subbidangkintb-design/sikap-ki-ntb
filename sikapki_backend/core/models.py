from django.conf import settings
from django.db import models
import uuid


class UserProfile(models.Model):
    """
    Profil tambahan untuk django.contrib.auth.User.

    Kita TIDAK mengganti User model bawaan Django (supaya tetap sederhana
    dan kompatibel dengan admin site + auth system bawaan). Sebagai
    gantinya, informasi tambahan (role, jabatan) disimpan di sini dan
    di-link 1-to-1 ke User.
    """

    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Super Admin'
        PETUGAS = 'petugas', 'Petugas KI'
        VERIFIKATOR = 'verifikator', 'Verifikator'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PETUGAS)
    jabatan = models.CharField(max_length=150, blank=True)
    unit_kerja = models.CharField(
        max_length=150, blank=True,
        default='Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil Pengguna'
        verbose_name_plural = 'Profil Pengguna'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class UjiCobaPengguna(models.Model):
    class Peran(models.TextChoices):
        MASYARAKAT = 'masyarakat', 'Masyarakat/pemohon'
        UMKM = 'umkm', 'Pelaku UMKM'
        PETUGAS = 'petugas', 'Petugas layanan'
        LAINNYA = 'lainnya', 'Lainnya'

    class Layanan(models.TextChoices):
        KESELURUHAN = 'keseluruhan', 'Keseluruhan portal'
        CHATBOT = 'chatbot', 'Chatbot Helpdesk KI'
        MEREK = 'cek_merek', 'Penelusuran awal merek'
        CHECKLIST = 'checklist', 'Checklist dokumen'
        INFORMASI = 'informasi', 'Pusat informasi'

    kode_respons = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    peran = models.CharField(max_length=20, choices=Peran.choices)
    layanan = models.CharField(max_length=20, choices=Layanan.choices)
    tugas_berhasil = models.BooleanField()
    kemudahan = models.PositiveSmallIntegerField()
    kejelasan = models.PositiveSmallIntegerField()
    kepercayaan = models.PositiveSmallIntegerField()
    kepuasan = models.PositiveSmallIntegerField()
    masukan = models.TextField(blank=True)
    persetujuan = models.BooleanField(default=False)
    ip_hash = models.CharField(max_length=64, blank=True, editable=False)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']
        verbose_name = 'Hasil Uji Coba Pengguna'
        verbose_name_plural = 'Hasil Uji Coba Pengguna'

    def __str__(self):
        return f'{self.get_layanan_display()} - {str(self.kode_respons)[:8]}'


class MonitoringSnapshot(models.Model):
    periode_mulai = models.DateField()
    periode_selesai = models.DateField()
    metrik = models.JSONField(default=dict, editable=False)
    catatan = models.TextField(blank=True)
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='snapshot_monitoring_dibuat', editable=False,
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-periode_selesai', '-dibuat_pada']
        verbose_name = 'Snapshot Monitoring'
        verbose_name_plural = 'Snapshot Monitoring'
        constraints = [
            models.CheckConstraint(
                check=models.Q(periode_selesai__gte=models.F('periode_mulai')),
                name='monitoring_periode_valid',
            ),
        ]

    def __str__(self):
        return f'Monitoring {self.periode_mulai:%d/%m/%Y} - {self.periode_selesai:%d/%m/%Y}'
