from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from knowledge.rag_service import retrieve_relevant_chunks

from .models import PercakapanChatbot
from .ai_client import AIProviderError, generate_answer
from .serializers import (
    PercakapanChatbotSerializer,
    RatingChatbotSerializer,
    TanyaChatbotResponseSerializer,
    TanyaChatbotSerializer,
)


SIMILARITY_THRESHOLD = 0.35
ESCALATION_MESSAGE = (
    'Maaf, saya belum menemukan konteks yang cukup kuat untuk menjawab pertanyaan ini '
    'dengan aman. Silakan hubungi petugas layanan KI Kanwil Kemenkum NTB agar bisa '
    'mendapatkan arahan yang lebih tepat.'
)


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def tanya(self, request):
        """
        POST /api/chatbot/tanya/
        Body: {"pertanyaan": "..."}
        """
        serializer = TanyaChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pertanyaan = serializer.validated_data['pertanyaan']

        try:
            chunks = retrieve_relevant_chunks(pertanyaan, top_k=5)
        except Exception as exc:
            return Response(
                {
                    'detail': (
                        'Gagal mengambil konteks dari knowledge base. Pastikan ChromaDB, '
                        'model embedding, dan data index sudah siap.'
                    ),
                    'error': str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        confidence_score = _calculate_confidence(chunks)
        if confidence_score < SIMILARITY_THRESHOLD:
            percakapan = PercakapanChatbot.objects.create(
                pertanyaan=pertanyaan,
                jawaban=ESCALATION_MESSAGE,
                sumber_dokumen=[],
                confidence_score=confidence_score,
                dieskalasi=True,
            )
            return Response(_serialize_chat_response(percakapan), status=status.HTTP_200_OK)

        sumber_dokumen = _extract_sources(chunks)
        prompt = _build_prompt(pertanyaan, chunks)

        try:
            jawaban = generate_answer(prompt)
        except AIProviderError as exc:
            jawaban = (
                'Maaf, layanan AI sedang tidak bisa dihubungi. Pastikan konfigurasi '
                'provider AI sudah benar, lalu coba lagi.'
            )
            percakapan = PercakapanChatbot.objects.create(
                pertanyaan=pertanyaan,
                jawaban=jawaban,
                sumber_dokumen=sumber_dokumen,
                confidence_score=confidence_score,
                dieskalasi=True,
            )
            return Response(
                {
                    **_serialize_chat_response(percakapan),
                    'detail': str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        percakapan = PercakapanChatbot.objects.create(
            pertanyaan=pertanyaan,
            jawaban=jawaban,
            sumber_dokumen=sumber_dokumen,
            confidence_score=confidence_score,
            dieskalasi=False,
        )
        return Response(_serialize_chat_response(percakapan), status=status.HTTP_201_CREATED)

    def rating(self, request):
        """
        POST /api/chatbot/rating/
        Body: {"percakapan_id": 1, "rating_membantu": true}
        """
        serializer = RatingChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        percakapan = PercakapanChatbot.objects.get(pk=serializer.validated_data['percakapan_id'])
        percakapan.rating_membantu = serializer.validated_data['rating_membantu']
        percakapan.save(update_fields=['rating_membantu'])
        return Response(PercakapanChatbotSerializer(percakapan).data, status=status.HTTP_200_OK)


class PercakapanChatbotViewSet(viewsets.ModelViewSet):
    """
    Endpoint utama chatbot. POST membuat pertanyaan baru; logic pemanggilan
    model AI/RAG untuk mengisi `jawaban`, `sumber_dokumen`, dan
    `confidence_score` belum diimplementasikan di sini — ini murni
    fondasi penyimpanan log percakapan (lihat perform_create).
    """
    queryset = PercakapanChatbot.objects.all()
    serializer_class = PercakapanChatbotSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        # TODO: panggil modul RAG di sini untuk menghasilkan jawaban,
        # sumber_dokumen, dan confidence_score sesungguhnya.
        serializer.save(
            jawaban='(jawaban akan diisi oleh modul RAG — belum diimplementasikan)',
            sumber_dokumen=[],
            confidence_score=None,
            dieskalasi=False,
        )

    @action(detail=True, methods=['patch'], url_path='beri-rating')
    def beri_rating(self, request, pk=None):
        """
        PATCH /api/chatbot/percakapan/<id>/beri-rating/
        Body: {"rating_membantu": true|false}
        """
        percakapan = self.get_object()
        nilai = request.data.get('rating_membantu')
        if not isinstance(nilai, bool):
            return Response(
                {'detail': 'Field "rating_membantu" wajib bertipe boolean (true/false).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        percakapan.rating_membantu = nilai
        percakapan.save(update_fields=['rating_membantu'])
        return Response(self.get_serializer(percakapan).data)


def _calculate_confidence(chunks):
    similarities = [
        _distance_to_similarity(chunk.get('distance'))
        for chunk in chunks
    ]
    return round(max(similarities), 4) if similarities else 0.0


def _distance_to_similarity(distance):
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _extract_sources(chunks):
    sources = []
    seen = set()
    for chunk in chunks:
        metadata = chunk.get('metadata') or {}
        judul = metadata.get('judul')
        if not judul or judul in seen:
            continue
        seen.add(judul)
        sources.append({'judul': judul})
    return sources


def _build_prompt(pertanyaan, chunks):
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get('metadata') or {}
        judul = metadata.get('judul') or 'Dokumen tanpa judul'
        kategori = metadata.get('kategori') or '-'
        text = chunk.get('text') or ''
        context_blocks.append(
            f'[Konteks {index}]\n'
            f'Judul: {judul}\n'
            f'Kategori: {kategori}\n'
            f'Isi: {text}'
        )

    context = '\n\n'.join(context_blocks)
    return (
        'Anda adalah asisten layanan Kekayaan Intelektual Kanwil Kemenkum NTB.\n'
        'Jawab HANYA berdasarkan konteks yang diberikan di bawah ini.\n'
        'Gunakan Bahasa Indonesia yang mudah dipahami orang awam.\n'
        'Jangan mengarang informasi, aturan, biaya, jangka waktu, atau prosedur yang tidak ada di konteks.\n'
        'Jika konteks tidak cukup untuk menjawab, katakan terus terang bahwa Anda tidak tahu berdasarkan konteks yang tersedia.\n\n'
        f'KONTEKS:\n{context}\n\n'
        f'PERTANYAAN:\n{pertanyaan}\n\n'
        'JAWABAN:'
    )


def _serialize_chat_response(percakapan):
    return TanyaChatbotResponseSerializer({
        'id': percakapan.id,
        'jawaban': percakapan.jawaban,
        'sumber_dokumen': percakapan.sumber_dokumen,
        'confidence_score': percakapan.confidence_score,
        'dieskalasi': percakapan.dieskalasi,
    }).data
