from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UjiCobaPengguna, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role', 'jabatan', 'unit_kerja']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class UjiCobaPenggunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UjiCobaPengguna
        fields = [
            'kode_respons', 'peran', 'layanan', 'tugas_berhasil', 'kemudahan',
            'kejelasan', 'kepercayaan', 'kepuasan', 'masukan', 'persetujuan',
            'dibuat_pada',
        ]
        read_only_fields = ['kode_respons', 'dibuat_pada']

    def validate(self, attrs):
        for field in ('kemudahan', 'kejelasan', 'kepercayaan', 'kepuasan'):
            value = attrs.get(field)
            if value is None or not 1 <= value <= 5:
                raise serializers.ValidationError({field: 'Nilai harus antara 1 sampai 5.'})
        if not attrs.get('persetujuan'):
            raise serializers.ValidationError({
                'persetujuan': 'Persetujuan diperlukan untuk menyimpan evaluasi anonim.',
            })
        return attrs
