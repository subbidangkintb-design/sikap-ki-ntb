from rest_framework import serializers
from .models import KategoriKI, DokumenResmi, ChunkEmbedding, FAQ


class KategoriKISerializer(serializers.ModelSerializer):
    class Meta:
        model = KategoriKI
        fields = ['id', 'nama', 'deskripsi']


class ChunkEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChunkEmbedding
        fields = ['id', 'dokumen', 'teks_potongan', 'urutan', 'vector_id']


class DokumenResmiSerializer(serializers.ModelSerializer):
    kategori_nama = serializers.CharField(source='kategori.nama', read_only=True)

    class Meta:
        model = DokumenResmi
        fields = [
            'id', 'judul', 'kategori', 'kategori_nama', 'file_asli',
            'teks_lengkap', 'sumber_url', 'status_validasi',
            'divalidasi_oleh', 'divalidasi_pada', 'tanggal_upload',
            'diupload_oleh',
        ]
        read_only_fields = [
            'status_validasi', 'divalidasi_oleh', 'divalidasi_pada',
            'tanggal_upload', 'diupload_oleh',
        ]


class FAQSerializer(serializers.ModelSerializer):
    kategori_nama = serializers.CharField(source='kategori.nama', read_only=True)

    class Meta:
        model = FAQ
        fields = [
            'id', 'kategori', 'kategori_nama', 'pertanyaan', 'jawaban',
            'jumlah_dilihat', 'rating_membantu', 'sumber_url',
            'subkategori_sumber', 'divalidasi_pada', 'sinkronisasi_pada',
        ]
        read_only_fields = [
            'jumlah_dilihat', 'rating_membantu', 'sumber_url',
            'subkategori_sumber', 'divalidasi_pada', 'sinkronisasi_pada',
        ]
