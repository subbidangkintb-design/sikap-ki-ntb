from django.conf import settings
from django.db import models


class NiceClassificationTerm(models.Model):
    class Source(models.TextChoices):
        WIPO = 'wipo', 'WIPO Nice Classification'
        SKM_DJKI = 'skm_djki', 'SKM DJKI'

    class_number = models.CharField(max_length=2, db_index=True)
    basic_number = models.CharField(max_length=12, db_index=True)
    indication_en = models.CharField(max_length=700)
    synonyms_en = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WIPO)
    version = models.CharField(max_length=20, db_index=True)
    effective_date = models.DateField()
    source_url = models.URLField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Istilah Klasifikasi Nice'
        verbose_name_plural = 'Istilah Klasifikasi Nice'
        ordering = ['class_number', 'basic_number']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'version', 'basic_number'],
                name='unique_nice_term_source_version_basic_number',
            ),
        ]
        indexes = [
            models.Index(fields=['source', 'version', 'class_number']),
        ]

    def __str__(self):
        return f'Kelas {self.class_number} — {self.indication_en}'


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

    class SumberData(models.TextChoices):
        MANUAL = 'manual', 'Input manual petugas'
        BRM_DJKI = 'brm_djki', 'Berita Resmi Merek DJKI'
        API_PDKI = 'api_pdki', 'API resmi PDKI'
        DEMO = 'demo', 'Data demonstrasi'

    nomor_permohonan = models.CharField(max_length=50, blank=True, db_index=True)
    nama_merek = models.CharField(max_length=255)
    kelas_nice = models.CharField(
        max_length=10, help_text='Kelas Nice Classification, mis: 25, 35.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DIAJUKAN)
    pemilik = models.CharField(max_length=255)
    tanggal_daftar = models.DateField(null=True, blank=True)
    tanggal_penerimaan = models.DateField(null=True, blank=True)
    tanggal_publikasi = models.DateField(null=True, blank=True)
    sumber_data = models.CharField(
        max_length=20, choices=SumberData.choices, default=SumberData.MANUAL, db_index=True,
    )
    sumber_data_url = models.URLField(blank=True)
    label_merek = models.ImageField(
        upload_to='trademark/referensi/', blank=True, null=True,
        help_text='Etiket/logo referensi dari sumber resmi PDKI (PNG/JPEG).',
    )
    sumber_label_url = models.URLField(
        blank=True,
        help_text='Tautan halaman PDKI resmi tempat etiket referensi diverifikasi.',
    )
    visual_embedding = models.JSONField(default=list, blank=True, editable=False)
    visual_embedding_diperbarui = models.DateTimeField(null=True, blank=True, editable=False)
    tanggal_sinkron_terakhir = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mirror PDKI'
        verbose_name_plural = 'Mirror PDKI'
        ordering = ['nama_merek']
        indexes = [
            models.Index(fields=['nama_merek']),
            models.Index(fields=['kelas_nice']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['nomor_permohonan', 'kelas_nice'],
                condition=~models.Q(nomor_permohonan=''),
                name='unik_permohonan_kelas_mirror_pdki',
            ),
        ]

    def __str__(self):
        return f'{self.nama_merek} — kelas {self.kelas_nice} ({self.get_status_display()})'


class SinkronisasiPDKILog(models.Model):
    class Status(models.TextChoices):
        BERJALAN = 'berjalan', 'Berjalan'
        BERHASIL = 'berhasil', 'Berhasil'
        GAGAL = 'gagal', 'Gagal'
        DILEWATI = 'dilewati', 'Dilewati'

    sumber = models.CharField(max_length=30, default=MirrorPDKI.SumberData.BRM_DJKI)
    sumber_url = models.URLField(unique=True)
    judul_sumber = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BERJALAN)
    jumlah_ditemukan = models.PositiveIntegerField(default=0)
    jumlah_baru = models.PositiveIntegerField(default=0)
    jumlah_diperbarui = models.PositiveIntegerField(default=0)
    pesan = models.TextField(blank=True)
    dimulai_pada = models.DateTimeField(auto_now_add=True)
    selesai_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Log Sinkronisasi Data Merek'
        verbose_name_plural = 'Log Sinkronisasi Data Merek'
        ordering = ['-dimulai_pada']

    def __str__(self):
        return f'{self.get_status_display()} — {self.judul_sumber or self.sumber_url}'


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
    ip_hash = models.CharField(
        max_length=64, blank=True, editable=False,
        help_text='Sidik anonim untuk mitigasi penyalahgunaan; alamat IP asli tidak disimpan.',
    )

    class Meta:
        verbose_name = 'Log Cek Merek'
        verbose_name_plural = 'Log Cek Merek'
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f'{self.nama_merek_diajukan} — risiko {self.get_skor_risiko_display()}'
