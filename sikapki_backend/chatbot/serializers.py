from rest_framework import serializers
from .models import PercakapanChatbot


class TanyaChatbotSerializer(serializers.Serializer):
    pertanyaan = serializers.CharField(trim_whitespace=True, allow_blank=False)


class SumberDokumenSerializer(serializers.Serializer):
    judul = serializers.CharField()


class TanyaChatbotResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    jawaban = serializers.CharField()
    sumber_dokumen = SumberDokumenSerializer(many=True)
    confidence_score = serializers.FloatField(allow_null=True)
    dieskalasi = serializers.BooleanField()


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
            'id', 'pertanyaan', 'jawaban', 'sumber_dokumen', 'confidence_score',
            'dieskalasi', 'dibuat_pada', 'rating_membantu',
        ]
        read_only_fields = [
            'jawaban', 'sumber_dokumen', 'confidence_score', 'dieskalasi', 'dibuat_pada',
        ]
