from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid


class PercakapanChatbot(models.Model):
    """
    Satu pasang tanya-jawab dengan chatbot RAG. Berbeda dari desain
    percakapan multi-turn (Conversation+Message) sebelumnya — di sini
    setiap baris merepresentasikan satu interaksi tanya-jawab yang berdiri
    sendiri, sesuai skema di proposal. `sumber_dokumen` menyimpan daftar
    dokumen/FAQ yang disitasi AI saat menyusun jawaban, dan `dieskalasi`
    menandai apakah pertanyaan ini perlu ditangani manusia (mis. AI tidak
    yakin dengan jawabannya).
    """
    class StatusTindakLanjut(models.TextChoices):
        TIDAK_PERLU = 'tidak_perlu', 'Tidak perlu eskalasi'
        MENUNGGU = 'menunggu', 'Menunggu ditinjau petugas'
        DIPROSES = 'diproses', 'Sedang ditangani'
        SELESAI = 'selesai', 'Selesai ditindaklanjuti'

    class Prioritas(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        TINGGI = 'tinggi', 'Tinggi'
        MENDESAK = 'mendesak', 'Mendesak'

    sesi_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        editable=False,
        help_text='ID anonim yang menghubungkan beberapa tanya-jawab dalam satu sesi pengguna.',
    )
    pelacakan_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Token acak untuk pelacakan status konsultasi oleh pengguna tanpa login.',
    )
    pertanyaan = models.TextField()
    jawaban = models.TextField()
    sumber_dokumen = models.JSONField(
        default=list, blank=True,
        help_text='Daftar dokumen/FAQ yang disitasi AI untuk menyusun jawaban ini.',
    )
    confidence_score = models.FloatField(
        null=True, blank=True,
        help_text='Skor keyakinan model AI terhadap jawaban (0.0 - 1.0).',
    )
    dieskalasi = models.BooleanField(
        default=False,
        help_text='True jika percakapan ini perlu ditindaklanjuti oleh petugas manusia.',
    )
    status_tindak_lanjut = models.CharField(
        max_length=20, choices=StatusTindakLanjut.choices,
        default=StatusTindakLanjut.TIDAK_PERLU, db_index=True,
    )
    prioritas = models.CharField(
        max_length=12, choices=Prioritas.choices, default=Prioritas.NORMAL, db_index=True,
    )
    batas_tindak_lanjut = models.DateTimeField(null=True, blank=True, db_index=True)
    ditugaskan_kepada = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='konsultasi_ditugaskan',
    )
    catatan_tindak_lanjut = models.TextField(
        blank=True,
        help_text='Catatan internal petugas; tidak ditampilkan kepada pengguna publik.',
    )
    jawaban_koreksi = models.TextField(
        blank=True,
        help_text='Koreksi petugas bila jawaban sistem perlu diperbaiki.',
    )
    dikoreksi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='konsultasi_dikoreksi', editable=False,
    )
    ditinjau_pada = models.DateTimeField(null=True, blank=True, editable=False)
    diselesaikan_pada = models.DateTimeField(null=True, blank=True, editable=False)
    dikoreksi_pada = models.DateTimeField(null=True, blank=True, editable=False)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    rating_membantu = models.BooleanField(
        null=True, blank=True,
        help_text='Feedback pengguna: True = membantu, False = tidak membantu, null = belum ada feedback.',
    )

    class Meta:
        verbose_name = 'Percakapan Chatbot'
        verbose_name_plural = 'Percakapan Chatbot'
        ordering = ['-dibuat_pada']

    def __str__(self):
        potongan = self.pertanyaan[:60] + ('…' if len(self.pertanyaan) > 60 else '')
        return potongan

    def save(self, *args, **kwargs):
        now = timezone.now()
        if self.dieskalasi and self.status_tindak_lanjut == self.StatusTindakLanjut.TIDAK_PERLU:
            self.status_tindak_lanjut = self.StatusTindakLanjut.MENUNGGU
        elif not self.dieskalasi:
            self.status_tindak_lanjut = self.StatusTindakLanjut.TIDAK_PERLU

        if self.dieskalasi and self.batas_tindak_lanjut is None:
            jam_sla = getattr(settings, 'HUMAN_OVERSIGHT_SLA_HOURS', 24)
            self.batas_tindak_lanjut = now + timedelta(hours=jam_sla)
        elif not self.dieskalasi:
            self.batas_tindak_lanjut = None

        if self.status_tindak_lanjut in {
            self.StatusTindakLanjut.DIPROSES, self.StatusTindakLanjut.SELESAI,
        } and self.ditinjau_pada is None:
            self.ditinjau_pada = now
        if self.status_tindak_lanjut == self.StatusTindakLanjut.SELESAI:
            self.diselesaikan_pada = self.diselesaikan_pada or now
        else:
            self.diselesaikan_pada = None
        if self.jawaban_koreksi and self.dikoreksi_pada is None:
            self.dikoreksi_pada = now
        super().save(*args, **kwargs)

    @property
    def terlambat(self):
        return bool(
            self.dieskalasi
            and self.status_tindak_lanjut != self.StatusTindakLanjut.SELESAI
            and self.batas_tindak_lanjut
            and self.batas_tindak_lanjut < timezone.now()
        )


class TindakLanjutKonsultasiLog(models.Model):
    percakapan = models.ForeignKey(
        PercakapanChatbot, on_delete=models.CASCADE, related_name='riwayat_tindak_lanjut',
    )
    status_sebelum = models.CharField(
        max_length=20, choices=PercakapanChatbot.StatusTindakLanjut.choices,
    )
    status_sesudah = models.CharField(
        max_length=20, choices=PercakapanChatbot.StatusTindakLanjut.choices,
    )
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    catatan = models.TextField(blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']
        verbose_name = 'Jejak Tindak Lanjut Konsultasi'
        verbose_name_plural = 'Jejak Tindak Lanjut Konsultasi'

    def __str__(self):
        return f'{self.percakapan_id}: {self.status_sebelum} -> {self.status_sesudah}'
