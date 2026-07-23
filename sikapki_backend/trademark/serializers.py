from rest_framework import serializers
from .models import MirrorPDKI, CekMerekLog


class CekMerekAISerializer(serializers.Serializer):
    nama_merek = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=255)
    deskripsi_produk = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=2000)
    logo_merek = serializers.FileField(required=False, write_only=True)
    kelas_nice_dipilih = serializers.ListField(
        child=serializers.ChoiceField(choices=[str(number) for number in range(1, 46)]),
        required=False, allow_empty=True, max_length=2,
    )

    def validate_kelas_nice_dipilih(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Kelas Nice yang dipilih tidak boleh duplikat.')
        return value


class MerekMiripSerializer(serializers.Serializer):
    nomor_permohonan = serializers.CharField(required=False, allow_blank=True)
    nama = serializers.CharField()
    kelas = serializers.CharField()
    status = serializers.CharField()
    skor_kemiripan = serializers.IntegerField()
    skor_visual = serializers.IntegerField(required=False, allow_null=True)
    skor_gabungan = serializers.IntegerField(required=False)
    label_merek_url = serializers.URLField(required=False, allow_null=True)
    sumber_label_url = serializers.URLField(required=False, allow_blank=True)
    sumber_data = serializers.CharField(required=False, allow_blank=True)
    sumber_data_url = serializers.URLField(required=False, allow_blank=True)
    alasan_kemiripan = serializers.ListField(
        child=serializers.CharField(), required=False,
    )


class CekMerekAIResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kelas_nice_terdeteksi = serializers.ListField(child=serializers.CharField())
    merek_mirip = MerekMiripSerializer(many=True)
    skor_risiko = serializers.CharField()
    persentase_kemiripan = serializers.IntegerField(min_value=0, max_value=100)
    persentase_kemiripan_visual = serializers.IntegerField(min_value=0, max_value=100, allow_null=True)
    logo_dianalisis = serializers.BooleanField()
    referensi_visual_dibandingkan = serializers.IntegerField(min_value=0)
    saran_naratif = serializers.CharField()
    disclaimer = serializers.CharField()
    sumber_klasifikasi = serializers.CharField(required=False)
    bukti_klasifikasi = serializers.ListField(
        child=serializers.DictField(), required=False,
    )
    cakupan_data = serializers.DictField(required=False)
    metodologi = serializers.ListField(child=serializers.CharField(), required=False)


class MirrorPDKISerializer(serializers.ModelSerializer):
    class Meta:
        model = MirrorPDKI
        fields = [
            'id', 'nomor_permohonan', 'nama_merek', 'kelas_nice', 'status', 'pemilik',
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
