from django.conf import settings
from django.db import models


class MirrorPDKI(models.Model):
    """
    Data merek hasil mirror/sinkronisasi dari PDKI (Pangkalan Data
    Kekayaan Intelektual). Dipakai sebagai basis pembanding saat
    pengguna melakukan pengecekan kemiripan merek.
    """

    class Status(models.TextChoices):
        TERDAFTAR = 'terdaftar', 'Terdaftar'
        DIAJUKAN = 'diajukan', 'Dalam Proses Pengajuan'
        DITOLAK = 'ditolak', 'Ditolak'
        KEDALUWARSA = 'kedaluwarsa', 'Kedaluwarsa'

    nama_merek = models.CharField(max_length=255)
    kelas_nice = models.CharField(
        max_length=10, help_text='Kelas Nice Classification, mis: 25, 35.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DIAJUKAN)
    pemilik = models.CharField(max_length=255)
    tanggal_daftar = models.DateField(null=True, blank=True)
    tanggal_sinkron_terakhir = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mirror PDKI'
        verbose_name_plural = 'Mirror PDKI'
        ordering = ['nama_merek']
        indexes = [
            models.Index(fields=['nama_merek']),
            models.Index(fields=['kelas_nice']),
        ]

    def __str__(self):
        return f'{self.nama_merek} — kelas {self.kelas_nice} ({self.get_status_display()})'


class CekMerekLog(models.Model):
    """Log setiap kali pengguna melakukan pengecekan risiko/kemiripan merek."""

    class SkorRisiko(models.TextChoices):
        RENDAH = 'rendah', 'Rendah'
        SEDANG = 'sedang', 'Sedang'
        TINGGI = 'tinggi', 'Tinggi'

    nama_merek_diajukan = models.CharField(max_length=255)
    deskripsi_produk = models.TextField(blank=True)
    kelas_nice_terdeteksi = models.CharField(
        max_length=10, blank=True,
        help_text='Kelas Nice hasil deteksi otomatis (mis. dari deskripsi produk).',
    )
    skor_risiko = models.CharField(max_length=10, choices=SkorRisiko.choices)
    hasil_lengkap = models.JSONField(
        default=dict, blank=True,
        help_text='Detail lengkap hasil pengecekan (mis. daftar merek mirip beserta skornya).',
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    ip_pengguna = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'Log Cek Merek'
        verbose_name_plural = 'Log Cek Merek'
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f'{self.nama_merek_diajukan} — risiko {self.get_skor_risiko_display()}'
