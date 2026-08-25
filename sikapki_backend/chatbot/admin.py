from django import forms
from django.contrib import admin
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.html import format_html

from .models import PercakapanChatbot, TindakLanjutKonsultasiLog


class TindakLanjutKonsultasiLogInline(admin.TabularInline):
    model = TindakLanjutKonsultasiLog
    extra = 0
    can_delete = False
    readonly_fields = ('status_sebelum', 'status_sesudah', 'petugas', 'catatan', 'dibuat_pada')
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PercakapanChatbot)
class PercakapanChatbotAdmin(admin.ModelAdmin):
    list_display = (
        'preview_pertanyaan', 'status_badge', 'prioritas', 'sla_badge', 'ditugaskan_kepada',
        'confidence_badge', 'rating_membantu', 'dibuat_pada',
    )
    list_filter = ('status_tindak_lanjut', 'prioritas', 'dieskalasi', 'rating_membantu', 'dibuat_pada')
    search_fields = ('pertanyaan', 'jawaban', 'catatan_tindak_lanjut', 'jawaban_koreksi')
    readonly_fields = (
            'sesi_id', 'pelacakan_id', 'email_pengguna', 'pertanyaan', 'jawaban', 'sumber_dokumen', 'confidence_score',
        'dieskalasi', 'rating_membantu', 'dibuat_pada', 'ditinjau_pada',
        'diselesaikan_pada', 'dikoreksi_oleh', 'dikoreksi_pada',
    )
    inlines = (TindakLanjutKonsultasiLogInline,)
    ordering = ('-dibuat_pada',)
    date_hierarchy = 'dibuat_pada'
    list_per_page = 25
    list_select_related = ('ditugaskan_kepada', 'dikoreksi_oleh')
    actions = ('tandai_diproses', 'tandai_selesai')
    fieldsets = (
        ('Pertanyaan dan jawaban sistem', {
            'fields': ('sesi_id', 'email_pengguna', 'pertanyaan', 'jawaban', 'rating_membantu', 'dibuat_pada'),
            'description': 'Data asli interaksi tidak dapat diubah agar riwayat layanan tetap utuh.',
        }),
        ('Tindak lanjut petugas', {'fields': (
            'status_tindak_lanjut', 'prioritas', 'batas_tindak_lanjut', 'ditugaskan_kepada',
            'catatan_tindak_lanjut', 'ditinjau_pada', 'diselesaikan_pada',
        ), 'description': 'Pilih status, tetapkan petugas, lalu tuliskan hasil tindak lanjut.'}),
        ('Koreksi jawaban', {'fields': (
            'jawaban_koreksi', 'dikoreksi_oleh', 'dikoreksi_pada',
        ), 'description': 'Isi bila jawaban sistem perlu dikoreksi. Koreksi menjadi bahan evaluasi basis pengetahuan.'}),
        ('Bukti sistem', {
            'fields': ('pelacakan_id', 'sumber_dokumen', 'confidence_score', 'dieskalasi'),
            'classes': ('collapse',),
        }),
    )
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 8, 'style': 'min-width: 640px;'}),
        },
    }

    @admin.display(description='Pertanyaan')
    def preview_pertanyaan(self, obj):
        return (obj.pertanyaan[:75] + '...') if len(obj.pertanyaan) > 75 else obj.pertanyaan

    @admin.display(description='Status tindak lanjut', ordering='status_tindak_lanjut')
    def status_badge(self, obj):
        colors = {
            PercakapanChatbot.StatusTindakLanjut.TIDAK_PERLU: ('#e5e7eb', '#374151'),
            PercakapanChatbot.StatusTindakLanjut.MENUNGGU: ('#fef3c7', '#92400e'),
            PercakapanChatbot.StatusTindakLanjut.DIPROSES: ('#dbeafe', '#1e40af'),
            PercakapanChatbot.StatusTindakLanjut.SELESAI: ('#dcfce7', '#166534'),
        }
        background, color = colors[obj.status_tindak_lanjut]
        return format_html(
            '<span style="background:{};color:{};border-radius:999px;padding:5px 10px;font-weight:800;white-space:nowrap;">{}</span>',
            background, color, obj.get_status_tindak_lanjut_display(),
        )

    @admin.display(description='Kekuatan konteks', ordering='confidence_score')
    def confidence_badge(self, obj):
        if obj.confidence_score is None:
            return format_html('<span style="color:#6b7280;">-</span>')

        score = float(obj.confidence_score)
        if score < 0.35:
            background, color = '#fecaca', '#7f1d1d'
        elif score < 0.65:
            background, color = '#fde68a', '#713f12'
        else:
            background, color = '#bbf7d0', '#14532d'

        return format_html(
            '<span style="background:{};color:{};border-radius:999px;padding:3px 9px;font-weight:700;">{}</span>',
            background,
            color,
            f'{score:.2f}',
        )

    @admin.display(description='SLA', ordering='batas_tindak_lanjut')
    def sla_badge(self, obj):
        if not obj.dieskalasi or not obj.batas_tindak_lanjut:
            return '-'
        if obj.status_tindak_lanjut == PercakapanChatbot.StatusTindakLanjut.SELESAI:
            return format_html('<span style="color:#166534;font-weight:800;">Selesai</span>')
        if obj.terlambat:
            return format_html('<span style="color:#991b1b;font-weight:800;">Terlambat</span>')
        return format_html(
            '<span style="color:#075985;font-weight:800;">{}</span>',
            timezone.localtime(obj.batas_tindak_lanjut).strftime('%d/%m %H:%M'),
        )

    def save_model(self, request, obj, form, change):
        old_status = PercakapanChatbot.StatusTindakLanjut.TIDAK_PERLU
        if change:
            old_status = PercakapanChatbot.objects.only('status_tindak_lanjut').get(pk=obj.pk).status_tindak_lanjut
        if (
            obj.dieskalasi
            and obj.status_tindak_lanjut in {
                PercakapanChatbot.StatusTindakLanjut.DIPROSES,
                PercakapanChatbot.StatusTindakLanjut.SELESAI,
            }
            and not obj.ditugaskan_kepada_id
        ):
            obj.ditugaskan_kepada = request.user
        if 'jawaban_koreksi' in form.changed_data and obj.jawaban_koreksi:
            obj.dikoreksi_oleh = request.user
            obj.dikoreksi_pada = timezone.now()
        super().save_model(request, obj, form, change)
        if change and form.changed_data:
            TindakLanjutKonsultasiLog.objects.create(
                percakapan=obj,
                status_sebelum=old_status,
                status_sesudah=obj.status_tindak_lanjut,
                petugas=request.user,
                catatan=(
                    f'Perubahan: {", ".join(form.changed_data)}. '
                    f'{obj.catatan_tindak_lanjut}'.strip()
                ),
            )
            if 'status_tindak_lanjut' in form.changed_data and obj.email_pengguna:
                send_mail(
                    subject='Pembaruan konsultasi SIKAP-KI NTB',
                    message=(
                        f'Status konsultasi Anda kini: {obj.get_status_tindak_lanjut_display()}. '
                        f'Gunakan nomor pelacakan {obj.pelacakan_id} untuk memantau layanan.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.email_pengguna],
                    fail_silently=True,
                )

    @admin.action(description='Tandai konsultasi diproses oleh saya')
    def tandai_diproses(self, request, queryset):
        now = timezone.now()
        targets = list(queryset.filter(dieskalasi=True))
        updated = queryset.filter(pk__in=[item.pk for item in targets]).update(
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.DIPROSES,
            ditugaskan_kepada=request.user,
            ditinjau_pada=now,
            diselesaikan_pada=None,
        )
        TindakLanjutKonsultasiLog.objects.bulk_create([
            TindakLanjutKonsultasiLog(
                percakapan=item, status_sebelum=item.status_tindak_lanjut,
                status_sesudah=PercakapanChatbot.StatusTindakLanjut.DIPROSES,
                petugas=request.user, catatan='Aksi massal: ditandai sedang diproses.',
            ) for item in targets
        ])
        self.message_user(request, f'{updated} konsultasi ditandai sedang diproses.')

    @admin.action(description='Tandai konsultasi selesai')
    def tandai_selesai(self, request, queryset):
        now = timezone.now()
        targets = list(queryset.filter(dieskalasi=True))
        updated = queryset.filter(pk__in=[item.pk for item in targets]).update(
            status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI,
            ditugaskan_kepada=request.user,
            ditinjau_pada=now,
            diselesaikan_pada=now,
        )
        TindakLanjutKonsultasiLog.objects.bulk_create([
            TindakLanjutKonsultasiLog(
                percakapan=item, status_sebelum=item.status_tindak_lanjut,
                status_sesudah=PercakapanChatbot.StatusTindakLanjut.SELESAI,
                petugas=request.user, catatan='Aksi massal: ditandai selesai.',
            ) for item in targets
        ])
        self.message_user(request, f'{updated} konsultasi ditandai selesai.')


@admin.register(TindakLanjutKonsultasiLog)
class TindakLanjutKonsultasiLogAdmin(admin.ModelAdmin):
    list_display = ('percakapan', 'status_sebelum', 'status_sesudah', 'petugas', 'dibuat_pada')
    list_filter = ('status_sesudah', 'dibuat_pada')
    search_fields = ('percakapan__pertanyaan', 'catatan', 'petugas__username')
    readonly_fields = ('percakapan', 'status_sebelum', 'status_sesudah', 'petugas', 'catatan', 'dibuat_pada')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
