import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import MonitoringSnapshot, UjiCobaPengguna, UserProfile
from .monitoring import build_monitoring_metrics


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'jabatan', 'unit_kerja', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'jabatan')


@admin.register(UjiCobaPengguna)
class UjiCobaPenggunaAdmin(admin.ModelAdmin):
    list_display = (
        'kode_pendek', 'peran', 'layanan', 'tugas_berhasil', 'kemudahan',
        'kejelasan', 'kepercayaan', 'kepuasan', 'dibuat_pada',
    )
    list_filter = ('peran', 'layanan', 'tugas_berhasil', 'dibuat_pada')
    search_fields = ('kode_respons', 'masukan')
    readonly_fields = [field.name for field in UjiCobaPengguna._meta.fields]
    actions = ('ekspor_csv',)

    @admin.display(description='Kode respons')
    def kode_pendek(self, obj):
        return str(obj.kode_respons)[:8]

    @admin.action(description='Ekspor hasil terpilih ke CSV')
    def ekspor_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="uji-coba-sikap-ki.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'kode', 'tanggal', 'peran', 'layanan', 'tugas_berhasil', 'kemudahan',
            'kejelasan', 'kepercayaan', 'kepuasan', 'masukan',
        ])
        for row in queryset.iterator():
            writer.writerow([
                row.kode_respons, row.dibuat_pada, row.get_peran_display(),
                row.get_layanan_display(), row.tugas_berhasil, row.kemudahan,
                row.kejelasan, row.kepercayaan, row.kepuasan, row.masukan,
            ])
        return response


@admin.register(MonitoringSnapshot)
class MonitoringSnapshotAdmin(admin.ModelAdmin):
    list_display = ('periode_mulai', 'periode_selesai', 'ringkasan', 'dibuat_oleh', 'dibuat_pada')
    readonly_fields = ('metrik_terformat', 'dibuat_oleh', 'dibuat_pada')
    fields = ('periode_mulai', 'periode_selesai', 'catatan', 'metrik_terformat', 'dibuat_oleh', 'dibuat_pada')
    date_hierarchy = 'periode_selesai'

    @admin.display(description='Ringkasan')
    def ringkasan(self, obj):
        layanan = obj.metrik.get('layanan', {})
        return f"Chatbot {layanan.get('chatbot', 0)} | Cek merek {layanan.get('cek_merek', 0)}"

    @admin.display(description='Metrik tersimpan')
    def metrik_terformat(self, obj):
        if not obj or not obj.metrik:
            return 'Metrik akan dibuat otomatis saat disimpan.'
        import json
        return format_html('<pre style="white-space:pre-wrap">{}</pre>', json.dumps(obj.metrik, indent=2, ensure_ascii=False))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.dibuat_oleh = request.user
        obj.metrik = build_monitoring_metrics(obj.periode_mulai, obj.periode_selesai)
        super().save_model(request, obj, form, change)
