from rest_framework import serializers
from .models import CekMerekLog, KlasifikasiMerekLog, MirrorPDKI


class CekMerekAISerializer(serializers.Serializer):
    nama_merek = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=255)
    deskripsi_produk = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=2000)
    logo_merek = serializers.FileField(required=False, write_only=True)
    asinkron = serializers.BooleanField(default=False, write_only=True)


class IstilahResmiSerializer(serializers.Serializer):
    istilah = serializers.CharField()
    basic_number = serializers.CharField()
    skor = serializers.FloatField(required=False)
    frasa_pencarian = serializers.CharField(required=False)
    sumber_url = serializers.URLField(required=False, allow_blank=True)


class RekomendasiKelasSerializer(serializers.Serializer):
    kelas = serializers.CharField()
    keyakinan = serializers.FloatField(min_value=0, max_value=1)
    alasan = serializers.CharField()
    deskripsi_kelas = serializers.CharField(allow_blank=True)
    istilah_resmi = IstilahResmiSerializer(many=True)
    sumber = serializers.CharField()
    sumber_url = serializers.URLField(required=False, allow_blank=True)
    skm_url = serializers.URLField(required=False, allow_blank=True)
    skm_terms_tersedia = serializers.IntegerField(required=False, min_value=0)
    skm_version = serializers.CharField(required=False, allow_blank=True)


class CekMerekAIResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nama_merek = serializers.CharField()
    rekomendasi_kelas = RekomendasiKelasSerializer(many=True)
    perlu_klarifikasi = serializers.BooleanField()
    pertanyaan_klarifikasi = serializers.CharField(allow_blank=True)
    logo_dinilai = serializers.BooleanField()
    disclaimer = serializers.CharField()
    sumber_klasifikasi = serializers.CharField(required=False)
    tautan_resmi = serializers.DictField()
    langkah_selanjutnya = serializers.ListField(child=serializers.CharField())
    rangkaian_kelas = serializers.ListField(child=serializers.DictField(), required=False)


class EskalasiKelasSerializer(serializers.Serializer):
    nama_merek = serializers.CharField(max_length=255, required=False, allow_blank=True)
    deskripsi_produk = serializers.CharField(max_length=4000, trim_whitespace=True)
    sesi_id = serializers.UUIDField(required=False)
    email_pengguna = serializers.EmailField(required=False, allow_blank=True)
    rekomendasi_kelas = serializers.ListField(
        child=serializers.DictField(), required=False, default=list,
    )


class MirrorPDKISerializer(serializers.ModelSerializer):
    class Meta:
        model = MirrorPDKI
        fields = [
            'id', 'nomor_permohonan', 'nama_merek', 'kelas_nice', 'status', 'pemilik',
            'uraian_barang_jasa',
            'tanggal_daftar', 'tanggal_penerimaan', 'tanggal_publikasi',
            'sumber_data', 'sumber_data_url', 'label_merek', 'sumber_label_url',
            'visual_embedding_diperbarui', 'tanggal_sinkron_terakhir',
        ]


class CekMerekLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CekMerekLog
        fields = [
            'id', 'nama_merek_diajukan', 'deskripsi_produk',
            'kelas_nice_terdeteksi', 'skor_risiko', 'hasil_lengkap',
            'dibuat_pada',
        ]
        read_only_fields = ['skor_risiko', 'hasil_lengkap', 'dibuat_pada']


class KlasifikasiMerekLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = KlasifikasiMerekLog
        fields = [
            'id', 'nama_merek_diajukan', 'deskripsi_produk',
            'rekomendasi_kelas', 'perlu_klarifikasi', 'logo_disertakan',
            'dibuat_pada',
        ]
        read_only_fields = fields
