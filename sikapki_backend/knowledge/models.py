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
    judul = models.CharField(max_length=255)
    kategori = models.ForeignKey(
        KategoriKI, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dokumen',
    )
    file_asli = models.FileField(upload_to='knowledge/dokumen/', blank=True, null=True)
    teks_lengkap = models.TextField(
        blank=True,
        help_text='Teks bersih hasil ekstraksi dari file_asli, sumber untuk proses chunking/RAG.',
    )
    tanggal_upload = models.DateTimeField(auto_now_add=True)
    diupload_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dokumen_diupload',
    )

    class Meta:
        verbose_name = 'Dokumen Resmi'
        verbose_name_plural = 'Dokumen Resmi'
        ordering = ['-tanggal_upload']

    def __str__(self):
        return self.judul


class ChunkEmbedding(models.Model):
    """
    Metadata potongan (chunk) teks dari sebuah DokumenResmi yang sudah
    di-embed. Vector embedding-nya SENDIRI TIDAK disimpan di sini —
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
        return f'{self.dokumen.judul} — chunk #{self.urutan}'


class FAQ(models.Model):
    """Pertanyaan yang sering diajukan, juga dipakai sebagai sumber RAG."""
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

    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['-jumlah_dilihat']

    def __str__(self):
        return self.pertanyaan
