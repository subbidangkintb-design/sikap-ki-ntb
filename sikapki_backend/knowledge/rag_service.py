from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from .models import ChunkEmbedding, DokumenResmi


CHROMA_COLLECTION_NAME = 'knowledge_chunks'
EMBEDDING_MODEL_NAME = 'BAAI/bge-m3'

logger = logging.getLogger(__name__)

_embedding_model = None
_chroma_client = None
_chroma_collection = None


def chunk_document(teks: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into word-based chunks with a small overlap so context near
    chunk boundaries is not lost during retrieval.
    """
    if chunk_size <= 0:
        raise ValueError('chunk_size must be greater than 0')
    if overlap < 0:
        raise ValueError('overlap must be greater than or equal to 0')
    if overlap >= chunk_size:
        raise ValueError('overlap must be smaller than chunk_size')

    words = re.findall(r'\S+', teks or '')
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]
        if not chunk_words:
            break
        chunks.append(' '.join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def embed_and_store(dokumen_id: int) -> int:
    """
    Rebuild embeddings for a DokumenResmi row and store vectors in ChromaDB.

    Returns the number of chunks indexed.
    """
    dokumen = (
        DokumenResmi.objects
        .select_related('kategori')
        .get(pk=dokumen_id)
    )
    teks = _get_document_text(dokumen)
    chunks = chunk_document(teks)

    collection = get_chroma_collection()
    _delete_document_vectors(collection, dokumen.id)
    ChunkEmbedding.objects.filter(dokumen=dokumen).delete()

    if not chunks:
        return 0

    embeddings = get_embedding_model().encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    ids = [_make_vector_id(dokumen.id, index) for index in range(len(chunks))]
    kategori = dokumen.kategori.nama if dokumen.kategori else ''
    metadatas = [
        {
            'dokumen_id': dokumen.id,
            'judul': dokumen.judul,
            'kategori': kategori,
            'urutan': index,
        }
        for index in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=_to_plain_embeddings(embeddings),
        metadatas=metadatas,
    )

    ChunkEmbedding.objects.bulk_create([
        ChunkEmbedding(
            dokumen=dokumen,
            teks_potongan=chunk,
            urutan=index,
            vector_id=ids[index],
        )
        for index, chunk in enumerate(chunks)
    ])
    return len(chunks)


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Embed a query, search ChromaDB, and return matched chunk text plus source
    document metadata.
    """
    if top_k <= 0:
        return []
    if not query or not query.strip():
        return []

    query_embedding = get_embedding_model().encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    results = get_chroma_collection().query(
        query_embeddings=[_to_plain_embedding(query_embedding)],
        n_results=top_k,
        include=['documents', 'metadatas', 'distances'],
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]
    ids = results.get('ids', [[]])[0]

    chunks = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        chunks.append({
            'text': document,
            'metadata': metadata,
            'vector_id': ids[index] if index < len(ids) else None,
            'distance': distance,
        })
    return chunks


def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            'ChromaDB belum terinstall. Jalankan: pip install -r requirements.txt'
        ) from exc

    chroma_path = Path(settings.BASE_DIR) / 'chroma_data'
    chroma_path.mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    _chroma_collection = _chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine'},
    )
    return _chroma_collection


def get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            'sentence-transformers belum terinstall. Jalankan: pip install -r requirements.txt'
        ) from exc

    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def schedule_embed_and_store(dokumen_id: int) -> None:
    def _run_indexing():
        try:
            embed_and_store(dokumen_id)
        except Exception:
            logger.exception('Gagal membuat embedding untuk DokumenResmi id=%s', dokumen_id)

    transaction.on_commit(_run_indexing)


def _get_document_text(dokumen: DokumenResmi) -> str:
    if dokumen.teks_lengkap:
        return dokumen.teks_lengkap

    if not dokumen.file_asli:
        return ''

    try:
        with dokumen.file_asli.open('rb') as uploaded_file:
            return uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        return ''


def _delete_document_vectors(collection, dokumen_id: int) -> None:
    existing = collection.get(where={'dokumen_id': dokumen_id}, include=[])
    ids = existing.get('ids', [])
    if ids:
        collection.delete(ids=ids)


def _make_vector_id(dokumen_id: int, urutan: int) -> str:
    return f'dokumen_{dokumen_id}_chunk_{urutan}'


def _to_plain_embeddings(embeddings) -> list[list[float]]:
    return [list(map(float, embedding)) for embedding in embeddings]


def _to_plain_embedding(embedding) -> list[float]:
    return list(map(float, embedding))
