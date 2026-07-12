from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .models import PercakapanChatbot


@admin.register(PercakapanChatbot)
class PercakapanChatbotAdmin(admin.ModelAdmin):
    list_display = (
        'preview_pertanyaan', 'confidence_badge', 'dieskalasi',
        'rating_membantu', 'dibuat_pada',
    )
    list_filter = ('dieskalasi', 'rating_membantu', 'dibuat_pada')
    search_fields = ('pertanyaan', 'jawaban')
    readonly_fields = ('dibuat_pada',)
    ordering = ('-dibuat_pada',)
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 8, 'style': 'min-width: 640px;'}),
        },
    }

    @admin.display(description='Pertanyaan')
    def preview_pertanyaan(self, obj):
        return (obj.pertanyaan[:75] + '...') if len(obj.pertanyaan) > 75 else obj.pertanyaan

    @admin.display(description='Confidence', ordering='confidence_score')
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
            '<span style="background:{};color:{};border-radius:999px;padding:3px 9px;font-weight:700;">{:.2f}</span>',
            background,
            color,
            score,
        )
