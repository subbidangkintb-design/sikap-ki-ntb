from django.conf import settings
from django.db import models


class KategoriKI(models.Model):
    """Kategori jenis Kekayaan Intelektual, mis: Merek, Hak Cipta, Paten, Desain Industri."""
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Kategori KI'
        verbose_name_plural = 'Kategori KI'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class DokumenResmi(models.Model):
    """
    Dokumen resmi (peraturan, SOP, panduan) yang jadi sumber pengetahuan
    untuk fitur RAG chatbot. `teks_lengkap` menyimpan teks bersih hasil
    ekstraksi dari `file_asli`, supaya bisa langsung dipakai untuk proses
    chunking + embedding tanpa perlu parse ulang file setiap saat.
    """
    class StatusValidasi(models.TextChoices):
        DRAF = 'draf', 'Draf / belum diverifikasi'
        TERVERIFIKASI = 'terverifikasi', 'Terverifikasi'
        DINONAKTIFKAN = 'dinonaktifkan', 'Dinonaktifkan'

    class StatusIndexing(models.TextChoices):
        BELUM = 'belum', 'Belum dijadwalkan'
        MENUNGGU = 'menunggu', 'Menunggu diproses'
        DIPROSES = 'diproses', 'Sedang diproses'
        BERHASIL = 'berhasil', 'Berhasil'
        GAGAL = 'gagal', 'Gagal'

    judul = models.CharField(max_length=255)
    kategori = models.ForeignKey(
        KategoriKI, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dokumen',
    )
    file_asli = models.FileField(upload_to='knowledge/dokumen/', blank=True, null=True)
    jumlah_halaman = models.PositiveIntegerField(null=True, blank=True, editable=False)
    ukuran_file = models.PositiveBigIntegerField(default=0, editable=False)
    teks_lengkap = models.TextField(
        blank=True,
        help_text='Teks bersih hasil ekstraksi dari file_asli, sumber untuk proses chunking/RAG.',
    )
    sumber_url = models.URLField(
        blank=True,
        help_text='Tautan halaman resmi asal dokumen, bila tersedia.',
    )
    status_validasi = models.CharField(
        max_length=20,
        choices=StatusValidasi.choices,
        default=StatusValidasi.DRAF,
        db_index=True,
        help_text='Hanya dokumen terverifikasi yang digunakan oleh chatbot.',
    )
    divalidasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dokumen_divalidasi', editable=False,
    )
    divalidasi_pada = models.DateTimeField(null=True, blank=True, editable=False)
    tanggal_upload = models.DateTimeField(auto_now_add=True)
    diupload_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dokumen_diupload',
    )
    status_indexing = models.CharField(
        max_length=20, choices=StatusIndexing.choices,
        default=StatusIndexing.BELUM, db_index=True, editable=False,
    )
    pesan_indexing = models.TextField(blank=True, editable=False)
    indexing_dimulai_pada = models.DateTimeField(null=True, blank=True, editable=False)
    indexing_selesai_pada = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = 'Dokumen Resmi'
        verbose_name_plural = 'Dokumen Resmi'
        ordering = ['-tanggal_upload']

    def __str__(self):
        return self.judul


class ChunkEmbedding(models.Model):
    """
    Metadata potongan (chunk) teks dari sebuah DokumenResmi yang sudah
    di-embed. Vector embedding-nya SENDIRI TIDAK disimpan di sini â€”
    hanya `vector_id` yang menunjuk ke record aslinya di ChromaDB.
    Postgres di sini berfungsi sebagai "index"/metadata store, bukan
    vector store.
    """
    dokumen = models.ForeignKey(
        DokumenResmi, on_delete=models.CASCADE, related_name='chunks',
    )
    teks_potongan = models.TextField()
    urutan = models.PositiveIntegerField(
        help_text='Urutan chunk ini dalam dokumen asal (dimulai dari 0 atau 1).',
    )
    vector_id = models.CharField(
        max_length=255, unique=True,
        help_text='ID record yang bersangkutan di ChromaDB (bukan vector-nya sendiri).',
    )

    class Meta:
        verbose_name = 'Chunk Embedding'
        verbose_name_plural = 'Chunk Embedding'
        ordering = ['dokumen', 'urutan']
        constraints = [
            models.UniqueConstraint(
                fields=['dokumen', 'urutan'], name='unik_urutan_per_dokumen',
            )
        ]

    def __str__(self):
        return f'{self.dokumen.judul} â€” chunk #{self.urutan}'


class FAQ(models.Model):
    """Pertanyaan yang sering diajukan, juga dipakai sebagai sumber RAG."""
    class StatusValidasi(models.TextChoices):
        DRAF = 'draf', 'Draf / belum diverifikasi'
        TERVERIFIKASI = 'terverifikasi', 'Terverifikasi'
        DINONAKTIFKAN = 'dinonaktifkan', 'Dinonaktifkan'

    class StatusIndexing(models.TextChoices):
        BELUM = 'belum', 'Belum diindeks'
        MENUNGGU = 'menunggu', 'Menunggu diproses'
        DIPROSES = 'diproses', 'Sedang diproses'
        BERHASIL = 'berhasil', 'Berhasil'
        GAGAL = 'gagal', 'Gagal'

    pertanyaan = models.CharField(max_length=500)
    jawaban = models.TextField()
    kategori = models.ForeignKey(
        KategoriKI, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='faq',
    )
    jumlah_dilihat = models.PositiveIntegerField(default=0)
    rating_membantu = models.PositiveIntegerField(
        default=0,
        help_text='Jumlah pengguna yang menandai FAQ ini membantu.',
    )
    status_validasi = models.CharField(
        max_length=20, choices=StatusValidasi.choices, default=StatusValidasi.DRAF,
        db_index=True,
        help_text='FAQ hasil sinkronisasi wajib diverifikasi sebelum digunakan chatbot.',
    )
    sumber_url = models.URLField(blank=True)
    sumber_kunci = models.CharField(
        max_length=64, null=True, blank=True, unique=True, editable=False,
        help_text='Identitas stabil pertanyaan dari sumber eksternal.',
    )
    subkategori_sumber = models.CharField(max_length=120, blank=True)
    hash_konten = models.CharField(max_length=64, blank=True, editable=False)
    aktif_sumber = models.BooleanField(default=True, db_index=True)
    sinkronisasi_pada = models.DateTimeField(null=True, blank=True, editable=False)
    divalidasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='faq_divalidasi', editable=False,
    )
    divalidasi_pada = models.DateTimeField(null=True, blank=True, editable=False)
    status_indexing = models.CharField(
        max_length=20, choices=StatusIndexing.choices,
        default=StatusIndexing.BELUM, db_index=True, editable=False,
    )
    vector_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True, editable=False,
    )
    diindeks_pada = models.DateTimeField(null=True, blank=True, editable=False)
    pesan_indexing = models.TextField(blank=True, editable=False)

    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['-jumlah_dilihat']
        indexes = [
            models.Index(fields=['status_validasi', 'aktif_sumber']),
        ]

    def __str__(self):
        return self.pertanyaan


class SinkronisasiFAQLog(models.Model):
    class Status(models.TextChoices):
        BERJALAN = 'berjalan', 'Berjalan'
        BERHASIL = 'berhasil', 'Berhasil'
        GAGAL = 'gagal', 'Gagal'

    sumber_url = models.URLField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BERJALAN)
    jumlah_halaman = models.PositiveIntegerField(default=0)
    jumlah_ditemukan = models.PositiveIntegerField(default=0)
    jumlah_baru = models.PositiveIntegerField(default=0)
    jumlah_diperbarui = models.PositiveIntegerField(default=0)
    jumlah_dinonaktifkan = models.PositiveIntegerField(default=0)
    pesan = models.TextField(blank=True)
    dimulai_pada = models.DateTimeField(auto_now_add=True)
    selesai_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-dimulai_pada']
        verbose_name = 'Log Sinkronisasi FAQ DJKI'
        verbose_name_plural = 'Log Sinkronisasi FAQ DJKI'

    def __str__(self):
        return f'{self.get_status_display()} - {self.dimulai_pada:%d/%m/%Y %H:%M}'

