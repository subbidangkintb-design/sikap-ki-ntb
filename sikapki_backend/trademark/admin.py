from django import forms
from django.contrib import admin, messages
from django.db import models

from chatbot.ai_client import AIProviderError
from .models import CekMerekLog, MirrorPDKI, NiceClassificationTerm, SinkronisasiPDKILog
from .services import build_visual_embedding_for_reference


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
    list_display = ('nama_merek', 'nomor_permohonan', 'kelas_nice', 'status', 'sumber_data', 'status_visual', 'tanggal_sinkron_terakhir')
    list_filter = ('status', 'sumber_data', 'kelas_nice')
    search_fields = ('nama_merek', 'nomor_permohonan', 'pemilik')
    date_hierarchy = 'tanggal_daftar'
    readonly_fields = ('visual_embedding_diperbarui',)

    @admin.display(boolean=True, description='Visual siap')
    def status_visual(self, obj):
        return bool(obj.visual_embedding)

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
