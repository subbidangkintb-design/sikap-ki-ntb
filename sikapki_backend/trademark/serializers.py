from rest_framework import serializers
from .models import MirrorPDKI, CekMerekLog


class CekMerekAISerializer(serializers.Serializer):
    nama_merek = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=255)
    deskripsi_produk = serializers.CharField(trim_whitespace=True, allow_blank=False)


class MerekMiripSerializer(serializers.Serializer):
    nama = serializers.CharField()
    kelas = serializers.CharField()
    status = serializers.CharField()
    skor_kemiripan = serializers.IntegerField()


class CekMerekAIResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kelas_nice_terdeteksi = serializers.ListField(child=serializers.CharField())
    merek_mirip = MerekMiripSerializer(many=True)
    skor_risiko = serializers.CharField()
    saran_naratif = serializers.CharField()
    disclaimer = serializers.CharField()


class MirrorPDKISerializer(serializers.ModelSerializer):
    class Meta:
        model = MirrorPDKI
        fields = [
            'id', 'nama_merek', 'kelas_nice', 'status', 'pemilik',
            'tanggal_daftar', 'tanggal_sinkron_terakhir',
        ]


class CekMerekLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CekMerekLog
        fields = [
            'id', 'nama_merek_diajukan', 'deskripsi_produk',
            'kelas_nice_terdeteksi', 'skor_risiko', 'hasil_lengkap',
            'dibuat_pada', 'ip_pengguna',
        ]
        read_only_fields = ['skor_risiko', 'hasil_lengkap', 'dibuat_pada', 'ip_pengguna']
