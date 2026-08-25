from django import forms
from django.contrib import admin, messages
from django.db import models

from chatbot.ai_client import AIProviderError
from .models import (
    CekMerekLog,
    KlasifikasiMerekLog,
    MirrorPDKI,
    NiceClassificationTerm,
    SinkronisasiPDKILog,
)
from .services import build_visual_embedding_for_reference


class AdaUraianFilter(admin.SimpleListFilter):
    title = 'Uraian barang/jasa'
    parameter_name = 'ada_uraian'

    def lookups(self, request, model_admin):
        return (('yes', 'Tersedia'), ('no', 'Belum tersedia'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(uraian_barang_jasa='')
        if self.value() == 'no':
            return queryset.filter(uraian_barang_jasa='')
        return queryset


class AdaNomorFilter(admin.SimpleListFilter):
    title = 'Nomor permohonan'
    parameter_name = 'ada_nomor'

    def lookups(self, request, model_admin):
        return (('yes', 'Tersedia'), ('no', 'Belum tersedia'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(nomor_permohonan='')
        if self.value() == 'no':
            return queryset.filter(nomor_permohonan='')
        return queryset


@admin.register(NiceClassificationTerm)
class NiceClassificationTermAdmin(admin.ModelAdmin):
    list_display = ('basic_number', 'class_number', 'indication_en', 'source', 'version', 'effective_date')
    list_filter = ('source', 'version', 'class_number')
    search_fields = ('basic_number', 'indication_en')
    readonly_fields = ('updated_at',)

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(MirrorPDKI)
class MirrorPDKIAdmin(admin.ModelAdmin):
    list_display = (
        'nama_merek', 'nomor_permohonan', 'kelas_nice', 'status',
        'status_uraian', 'sumber_data', 'status_visual', 'tanggal_sinkron_terakhir',
    )
    list_filter = ('status', 'sumber_data', 'kelas_nice', AdaUraianFilter, AdaNomorFilter)
    search_fields = ('nama_merek', 'nomor_permohonan', 'pemilik', 'uraian_barang_jasa')
    date_hierarchy = 'tanggal_daftar'
    readonly_fields = ('visual_embedding_diperbarui',)
    list_per_page = 50

    @admin.display(boolean=True, description='Visual siap')
    def status_visual(self, obj):
        return bool(obj.visual_embedding)

    @admin.display(boolean=True, description='Uraian tersedia')
    def status_uraian(self, obj):
        return bool(obj.uraian_barang_jasa.strip())

    def save_model(self, request, obj, form, change):
        label_changed = 'label_merek' in form.changed_data
        if label_changed:
            obj.visual_embedding = []
            obj.visual_embedding_diperbarui = None
        super().save_model(request, obj, form, change)
        if obj.label_merek and (label_changed or not obj.visual_embedding):
            try:
                build_visual_embedding_for_reference(obj)
                self.message_user(request, 'Embedding visual referensi berhasil dibuat.', messages.SUCCESS)
            except (ValueError, AIProviderError) as exc:
                self.message_user(request, f'Etiket tersimpan, tetapi embedding gagal: {exc}', messages.WARNING)


@admin.register(CekMerekLog)
class CekMerekLogAdmin(admin.ModelAdmin):
    list_display = (
        'nama_merek_diajukan', 'kelas_nice_terdeteksi', 'skor_risiko',
        'dibuat_pada',
    )
    list_filter = ('skor_risiko', 'dibuat_pada')
    search_fields = ('nama_merek_diajukan', 'deskripsi_produk')
    readonly_fields = (
        'nama_merek_diajukan', 'deskripsi_produk', 'kelas_nice_terdeteksi',
        'skor_risiko', 'hasil_lengkap', 'dibuat_pada', 'ip_hash',
    )
    ordering = ('-dibuat_pada',)
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 8, 'style': 'min-width: 640px;'}),
        },
    }

    def has_add_permission(self, request):
        return False

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(KlasifikasiMerekLog)
class KlasifikasiMerekLogAdmin(admin.ModelAdmin):
    list_display = (
        'nama_merek_diajukan', 'kelas_direkomendasikan',
        'perlu_klarifikasi', 'logo_disertakan', 'dibuat_pada',
    )
    list_filter = ('perlu_klarifikasi', 'logo_disertakan', 'dibuat_pada')
    search_fields = ('nama_merek_diajukan', 'deskripsi_produk')
    readonly_fields = (
        'nama_merek_diajukan', 'deskripsi_produk', 'rekomendasi_kelas',
        'perlu_klarifikasi', 'logo_disertakan', 'dibuat_pada', 'ip_hash',
    )
    ordering = ('-dibuat_pada',)

    @admin.display(description='Rekomendasi kelas')
    def kelas_direkomendasikan(self, obj):
        return ', '.join(
            str(item.get('kelas', ''))
            for item in obj.rekomendasi_kelas
            if item.get('kelas')
        ) or 'Perlu informasi tambahan'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SinkronisasiPDKILog)
class SinkronisasiPDKILogAdmin(admin.ModelAdmin):
    list_display = ('judul_sumber', 'status', 'jumlah_ditemukan', 'jumlah_baru', 'jumlah_diperbarui', 'dimulai_pada', 'selesai_pada')
    list_filter = ('status', 'sumber', 'dimulai_pada')
    search_fields = ('judul_sumber', 'sumber_url', 'pesan')
    readonly_fields = (
        'sumber', 'sumber_url', 'judul_sumber', 'status', 'jumlah_ditemukan',
        'jumlah_baru', 'jumlah_diperbarui', 'pesan', 'dimulai_pada', 'selesai_pada',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
