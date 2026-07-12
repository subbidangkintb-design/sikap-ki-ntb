from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .models import ChunkEmbedding, DokumenResmi, FAQ, KategoriKI


TEXTAREA_WIDGET = {
    models.TextField: {
        'widget': forms.Textarea(attrs={'rows': 10, 'style': 'min-width: 720px;'}),
    },
}


@admin.register(KategoriKI)
class KategoriKIAdmin(admin.ModelAdmin):
    list_display = ('nama', 'jumlah_dokumen', 'jumlah_faq')
    search_fields = ('nama',)

    @admin.display(description='Jumlah Dokumen')
    def jumlah_dokumen(self, obj):
        return obj.dokumen.count()

    @admin.display(description='Jumlah FAQ')
    def jumlah_faq(self, obj):
        return obj.faq.count()


class ChunkEmbeddingInline(admin.TabularInline):
    model = ChunkEmbedding
    extra = 0
    fields = ('urutan', 'teks_potongan', 'vector_id')
    readonly_fields = ('vector_id',)
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 4, 'style': 'min-width: 520px;'}),
        },
    }


@admin.register(DokumenResmi)
class DokumenResmiAdmin(admin.ModelAdmin):
    list_display = ('judul', 'kategori', 'status_embedding', 'diupload_oleh', 'jumlah_chunk', 'tanggal_upload')
    list_filter = ('kategori', 'tanggal_upload')
    search_fields = ('judul', 'teks_lengkap')
    readonly_fields = ('status_embedding',)
    inlines = [ChunkEmbeddingInline]
    formfield_overrides = TEXTAREA_WIDGET

    @admin.display(description='Jumlah Chunk')
    def jumlah_chunk(self, obj):
        return obj.chunks.count()

    @admin.display(description='Status Embedding')
    def status_embedding(self, obj):
        if not obj.pk:
            return format_html('<span style="color:#6b7280;">Belum disimpan</span>')
        chunk_count = obj.chunks.count()
        if chunk_count:
            return format_html(
                '<span style="background:#bbf7d0;color:#14532d;border-radius:999px;padding:3px 9px;font-weight:700;">Sudah di-embed ({} chunk)</span>',
                chunk_count,
            )
        return format_html(
            '<span style="background:#fecaca;color:#7f1d1d;border-radius:999px;padding:3px 9px;font-weight:700;">Belum di-embed</span>'
        )


@admin.register(ChunkEmbedding)
class ChunkEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('dokumen', 'urutan', 'vector_id', 'preview_teks')
    list_filter = ('dokumen',)
    search_fields = ('teks_potongan', 'vector_id')
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 6, 'style': 'min-width: 640px;'}),
        },
    }

    @admin.display(description='Preview Teks')
    def preview_teks(self, obj):
        return (obj.teks_potongan[:75] + '...') if len(obj.teks_potongan) > 75 else obj.teks_potongan


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('pertanyaan', 'kategori', 'jumlah_dilihat', 'rating_membantu')
    list_filter = ('kategori',)
    search_fields = ('pertanyaan', 'jawaban')
    ordering = ('-jumlah_dilihat',)
    formfield_overrides = TEXTAREA_WIDGET
