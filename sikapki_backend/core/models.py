from django.conf import settings
from django.db import models
from django.utils import timezone
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


class PortalConfiguration(models.Model):
    """Pengaturan fitur publik yang dapat diubah admin tanpa redeploy."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    ai_cek_merek_aktif = models.BooleanField(
        default=False,
        help_text='Aktifkan hanya jika data pembanding dan prosedur peninjauan sudah siap.',
    )
    diperbarui_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='konfigurasi_portal_diperbarui', editable=False,
    )
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Konfigurasi Portal'
        verbose_name_plural = 'Konfigurasi Portal'

    def __str__(self):
        return 'Pengaturan fitur SIKAP-KI NTB'

    @classmethod
    def current(cls):
        return cls.objects.first()


class UjiCobaPengguna(models.Model):
    class Peran(models.TextChoices):
        MASYARAKAT = 'masyarakat', 'Masyarakat/pemohon'
        UMKM = 'umkm', 'Pelaku UMKM'
        PETUGAS = 'petugas', 'Petugas layanan'
        LAINNYA = 'lainnya', 'Lainnya'

    class Layanan(models.TextChoices):
        KESELURUHAN = 'keseluruhan', 'Keseluruhan portal'
        CHATBOT = 'chatbot', 'Chatbot Helpdesk KI'
        MEREK = 'cek_merek', 'Asisten klasifikasi awal merek'
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


class BackgroundJob(models.Model):
    """Antrean pekerjaan berat yang diproses worker di luar request web."""

    class Kind(models.TextChoices):
        CHATBOT_AI = 'chatbot_ai', 'Jawaban Chatbot AI'
        CLASSIFICATION_AI = 'classification_ai', 'Klasifikasi Kelas AI'
        TRADEMARK_AI = 'trademark_ai', 'Penelusuran Merek AI'
        DOCUMENT_INDEX = 'document_index', 'Indexing Dokumen'
        FAQ_INDEX = 'faq_index', 'Indexing FAQ'
        BRM_ENRICH = 'brm_enrich', 'Pengayaan BRM DJKI'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Menunggu'
        RUNNING = 'running', 'Sedang diproses'
        SUCCEEDED = 'succeeded', 'Berhasil'
        FAILED = 'failed', 'Gagal'

    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='background_jobs_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'available_at']),
            models.Index(fields=['kind', 'status']),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} - {self.get_status_display()} ({self.job_id})'


class AdminAuditLog(models.Model):
    """Jejak perubahan data yang dilakukan melalui Django Admin."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Tambah'
        UPDATE = 'update', 'Ubah'
        DELETE = 'delete', 'Hapus'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_audit_logs',
    )
    action = models.CharField(max_length=12, choices=Action.choices)
    model_label = models.CharField(max_length=160, db_index=True)
    object_id = models.CharField(max_length=128, blank=True, db_index=True)
    object_repr = models.CharField(max_length=500)
    changed_fields = models.JSONField(default=list, blank=True)
    before_data = models.JSONField(default=dict, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log Admin'
        verbose_name_plural = 'Audit Log Admin'

    def __str__(self):
        return f'{self.get_action_display()} {self.model_label} #{self.object_id}'


class SlaNotification(models.Model):
    """Notifikasi internal untuk konsultasi yang melewati target SLA."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sla_notifications',
    )
    consultation_id = models.UUIDField(db_index=True)
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['read_at', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['recipient', 'consultation_id'],
                name='unique_sla_notification_recipient_consultation',
            ),
        ]

    def __str__(self):
        return f'Notifikasi SLA {self.consultation_id} untuk {self.recipient}'


class _BackgroundJobDuplicate(models.Model):
    """Antrean pekerjaan berat yang diproses worker di luar request web."""

    class Kind(models.TextChoices):
        CHATBOT_AI = 'chatbot_ai', 'Jawaban Chatbot AI'
        CLASSIFICATION_AI = 'classification_ai', 'Klasifikasi Kelas AI'
        TRADEMARK_AI = 'trademark_ai', 'Penelusuran Merek AI'
        DOCUMENT_INDEX = 'document_index', 'Indexing Dokumen'
        FAQ_INDEX = 'faq_index', 'Indexing FAQ'
        BRM_ENRICH = 'brm_enrich', 'Pengayaan BRM DJKI'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Menunggu'
        RUNNING = 'running', 'Sedang diproses'
        SUCCEEDED = 'succeeded', 'Berhasil'
        FAILED = 'failed', 'Gagal'

    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='background_jobs_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'available_at']),
            models.Index(fields=['kind', 'status']),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} - {self.get_status_display()} ({self.job_id})'


class _AdminAuditLogDuplicate(models.Model):
    """Jejak perubahan data yang dilakukan melalui Django Admin."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Tambah'
        UPDATE = 'update', 'Ubah'
        DELETE = 'delete', 'Hapus'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_audit_logs',
    )
    action = models.CharField(max_length=12, choices=Action.choices)
    model_label = models.CharField(max_length=160, db_index=True)
    object_id = models.CharField(max_length=128, blank=True, db_index=True)
    object_repr = models.CharField(max_length=500)
    changed_fields = models.JSONField(default=list, blank=True)
    before_data = models.JSONField(default=dict, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
        verbose_name = 'Audit Log Admin'
        verbose_name_plural = 'Audit Log Admin'

    def __str__(self):
        return f'{self.get_action_display()} {self.model_label} #{self.object_id}'


