from django.db import models


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
