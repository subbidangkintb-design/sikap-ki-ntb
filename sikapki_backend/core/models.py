from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """
    Profil tambahan untuk django.contrib.auth.User.

    Kita TIDAK mengganti User model bawaan Django (supaya tetap sederhana
    dan kompatibel dengan admin site + auth system bawaan). Sebagai
    gantinya, informasi tambahan (role, jabatan) disimpan di sini dan
    di-link 1-to-1 ke User.
    """

    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Super Admin'
        PETUGAS = 'petugas', 'Petugas KI'
        VERIFIKATOR = 'verifikator', 'Verifikator'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PETUGAS)
    jabatan = models.CharField(max_length=150, blank=True)
    unit_kerja = models.CharField(max_length=150, blank=True, default='Kanwil Kemenkum NTB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil Pengguna'
        verbose_name_plural = 'Profil Pengguna'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'
