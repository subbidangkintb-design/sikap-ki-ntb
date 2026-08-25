from rest_framework import serializers
from .models import PercakapanChatbot


class TanyaChatbotSerializer(serializers.Serializer):
    pertanyaan = serializers.CharField(
        trim_whitespace=True, allow_blank=False, max_length=1500,
    )
    sesi_id = serializers.UUIDField(required=False)
    asinkron = serializers.BooleanField(required=False, default=False)


class SumberDokumenSerializer(serializers.Serializer):
    judul = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)
    jenis = serializers.CharField(required=False, allow_blank=True)


class TanyaChatbotResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sesi_id = serializers.UUIDField()
    jawaban = serializers.CharField()
    sumber_dokumen = SumberDokumenSerializer(many=True)
    confidence_score = serializers.FloatField(allow_null=True)
    dieskalasi = serializers.BooleanField()
    kode_konsultasi = serializers.CharField(required=False, allow_null=True)
    pelacakan_id = serializers.UUIDField(required=False, allow_null=True)


class StatusKonsultasiSerializer(serializers.Serializer):
    kode_konsultasi = serializers.CharField()
    status = serializers.CharField()
    status_label = serializers.CharField()
    prioritas = serializers.CharField()
    dibuat_pada = serializers.DateTimeField()
    batas_tindak_lanjut = serializers.DateTimeField(allow_null=True)
    ditinjau_pada = serializers.DateTimeField(allow_null=True)
    diselesaikan_pada = serializers.DateTimeField(allow_null=True)
    jawaban_petugas = serializers.CharField(allow_blank=True)


class RatingChatbotSerializer(serializers.Serializer):
    percakapan_id = serializers.IntegerField()
    rating_membantu = serializers.BooleanField()

    def validate_percakapan_id(self, value):
        if not PercakapanChatbot.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Percakapan dengan ID ini tidak ditemukan.')
        return value


class PercakapanChatbotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PercakapanChatbot
        fields = [
            'id', 'sesi_id', 'pertanyaan', 'jawaban', 'sumber_dokumen', 'confidence_score',
            'dieskalasi', 'status_tindak_lanjut', 'ditugaskan_kepada',
            'catatan_tindak_lanjut', 'jawaban_koreksi', 'dikoreksi_oleh',
            'ditinjau_pada', 'diselesaikan_pada', 'dikoreksi_pada',
            'dibuat_pada', 'rating_membantu',
        ]
        read_only_fields = [
            'jawaban', 'sumber_dokumen', 'confidence_score', 'dieskalasi',
            'status_tindak_lanjut', 'ditugaskan_kepada', 'catatan_tindak_lanjut',
            'jawaban_koreksi', 'dikoreksi_oleh', 'ditinjau_pada', 'diselesaikan_pada',
            'dikoreksi_pada', 'dibuat_pada',
        ]
