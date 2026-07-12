from django import forms
from django.contrib import admin
from django.db import models

from .models import CekMerekLog, MirrorPDKI


@admin.register(MirrorPDKI)
class MirrorPDKIAdmin(admin.ModelAdmin):
    list_display = ('nama_merek', 'kelas_nice', 'status', 'pemilik', 'tanggal_daftar', 'tanggal_sinkron_terakhir')
    list_filter = ('status', 'kelas_nice')
    search_fields = ('nama_merek', 'pemilik')
    date_hierarchy = 'tanggal_daftar'


@admin.register(CekMerekLog)
class CekMerekLogAdmin(admin.ModelAdmin):
    list_display = (
        'nama_merek_diajukan', 'kelas_nice_terdeteksi', 'skor_risiko',
        'ip_pengguna', 'dibuat_pada',
    )
    list_filter = ('skor_risiko', 'dibuat_pada')
    search_fields = ('nama_merek_diajukan', 'deskripsi_produk')
    readonly_fields = ('dibuat_pada',)
    ordering = ('-dibuat_pada',)
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 8, 'style': 'min-width: 640px;'}),
        },
    }
