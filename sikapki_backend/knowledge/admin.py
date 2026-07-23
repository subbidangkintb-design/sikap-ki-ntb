from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.db import models
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from pypdf import PdfReader

from .models import ChunkEmbedding, DokumenResmi, FAQ, KategoriKI, SinkronisasiFAQLog


TEXTAREA_WIDGET = {
    models.TextField: {
        'widget': forms.Textarea(attrs={'rows': 10, 'style': 'min-width: 720px;'}),
    },
}


class DokumenResmiAdminForm(forms.ModelForm):
    class Meta:
        model = DokumenResmi
        fields = '__all__'

    def clean_file_asli(self):
        uploaded = self.cleaned_data.get('file_asli')
        if not uploaded or 'file_asli' not in self.changed_data:
            return uploaded
        max_size = settings.MAX_DOCUMENT_UPLOAD_SIZE
        if uploaded.size > max_size:
            raise forms.ValidationError(
                f'Ukuran dokumen maksimal {max_size // (1024 * 1024)} MB.',
            )
        suffix = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if suffix not in {'pdf', 'txt', 'md'}:
            raise forms.ValidationError('Format yang didukung: PDF, TXT, atau Markdown (.md).')

        self.document_file_size = uploaded.size
        self.document_page_count = None
        if suffix == 'pdf':
            try:
                uploaded.seek(0)
                if uploaded.read(5) != b'%PDF-':
                    raise forms.ValidationError('File tidak memiliki struktur PDF yang valid.')
                uploaded.seek(0)
                reader = PdfReader(uploaded)
                if reader.is_encrypted:
                    raise forms.ValidationError('PDF berpassword/terenkripsi belum didukung.')
                self.document_page_count = len(reader.pages)
                if not self.document_page_count:
                    raise forms.ValidationError('PDF tidak memiliki halaman.')
            except forms.ValidationError:
                raise
            except Exception as exc:
                raise forms.ValidationError(f'PDF tidak dapat dibaca: {exc}') from exc
            finally:
                uploaded.seek(0)
        return uploaded

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('file_asli') and not (cleaned.get('teks_lengkap') or '').strip():
            raise forms.ValidationError('Unggah file atau isi teks lengkap dokumen.')
        return cleaned


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
    form = DokumenResmiAdminForm
    list_display = (
        'judul', 'kategori', 'status_validasi', 'status_indexing_badge',
        'info_file_ringkas', 'jumlah_chunk', 'diupload_oleh', 'tanggal_upload',
    )
    list_filter = ('status_validasi', 'status_indexing', 'kategori', 'tanggal_upload')
    search_fields = ('judul', 'teks_lengkap', 'sumber_url')
    readonly_fields = (
        'status_embedding', 'status_indexing_badge', 'info_file_lengkap',
        'divalidasi_oleh', 'divalidasi_pada', 'indexing_dimulai_pada',
        'indexing_selesai_pada', 'pesan_indexing',
    )
    actions = ('verifikasi_dan_antrekan', 'antrekan_indexing_ulang')
    list_select_related = ('kategori', 'diupload_oleh')
    list_per_page = 30
    fieldsets = (
        ('Identitas dokumen', {'fields': ('judul', 'kategori', 'sumber_url')}),
        ('Berkas sumber', {
            'fields': ('file_asli', 'info_file_lengkap'),
            'description': 'PDF/TXT/MD maksimal 100 MB. PDF hasil scan perlu di-OCR terlebih dahulu agar teks dapat dicari.',
        }),
        ('Teks manual (opsional)', {
            'fields': ('teks_lengkap',),
            'classes': ('collapse',),
            'description': 'Isi ini diprioritaskan bila tersedia. Biarkan kosong untuk mengekstrak teks dari file.',
        }),
        ('Validasi petugas', {
            'fields': ('status_validasi', 'divalidasi_oleh', 'divalidasi_pada', 'diupload_oleh'),
        }),
        ('Status knowledge base', {
            'fields': (
                'status_indexing_badge', 'status_embedding', 'indexing_dimulai_pada',
                'indexing_selesai_pada', 'pesan_indexing',
            ),
        }),
    )
    formfield_overrides = TEXTAREA_WIDGET

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_chunk_count=Count('chunks'))

    def save_model(self, request, obj, form, change):
        if obj.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI:
            if not obj.divalidasi_pada or 'status_validasi' in form.changed_data:
                obj.divalidasi_oleh = request.user
                obj.divalidasi_pada = timezone.now()
        elif 'status_validasi' in form.changed_data:
            obj.divalidasi_oleh = None
            obj.divalidasi_pada = None
        if not obj.diupload_oleh_id:
            obj.diupload_oleh = request.user
        if 'file_asli' in form.changed_data:
            obj.ukuran_file = getattr(form, 'document_file_size', 0)
            obj.jumlah_halaman = getattr(form, 'document_page_count', None)
        if obj.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI and (
            not change or {'file_asli', 'teks_lengkap', 'status_validasi'} & set(form.changed_data)
        ):
            obj.status_indexing = DokumenResmi.StatusIndexing.MENUNGGU
            obj.pesan_indexing = ''
            obj.indexing_dimulai_pada = None
            obj.indexing_selesai_pada = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Verifikasi dan antrekan dokumen terpilih untuk indexing')
    def verifikasi_dan_antrekan(self, request, queryset):
        total = queryset.update(
            status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
            divalidasi_oleh=request.user,
            divalidasi_pada=timezone.now(),
            status_indexing=DokumenResmi.StatusIndexing.MENUNGGU,
            pesan_indexing='', indexing_dimulai_pada=None, indexing_selesai_pada=None,
        )
        self.message_user(
            request, f'{total} dokumen diverifikasi dan masuk antrean indexing.', messages.SUCCESS,
        )

    @admin.action(description='Antrekan ulang indexing dokumen terverifikasi')
    def antrekan_indexing_ulang(self, request, queryset):
        eligible = queryset.filter(status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI)
        total = eligible.update(
            status_indexing=DokumenResmi.StatusIndexing.MENUNGGU,
            pesan_indexing='', indexing_dimulai_pada=None, indexing_selesai_pada=None,
        )
        self.message_user(
            request, f'{total} dokumen terverifikasi masuk antrean indexing ulang.',
            messages.SUCCESS if total else messages.WARNING,
        )

    @admin.display(description='Jumlah Chunk')
    def jumlah_chunk(self, obj):
        count = getattr(obj, '_chunk_count', None)
        if count is None:
            count = obj.chunks.count()
        if not count:
            return '0'
        url = reverse('admin:knowledge_chunkembedding_changelist')
        return format_html('<a href="{}?dokumen__id__exact={}">{} chunk</a>', url, obj.pk, count)

    @admin.display(description='Berkas')
    def info_file_ringkas(self, obj):
        if not obj.file_asli:
            return 'Teks manual'
        size = _human_file_size(obj.ukuran_file or obj.file_asli.size)
        pages = f'{obj.jumlah_halaman} hlm · ' if obj.jumlah_halaman else ''
        return f'{pages}{size}'

    @admin.display(description='Informasi berkas')
    def info_file_lengkap(self, obj):
        if not obj or not obj.file_asli:
            return 'Belum ada berkas; sistem akan menggunakan teks manual.'
        pages = f'{obj.jumlah_halaman} halaman' if obj.jumlah_halaman else 'Jumlah halaman tidak berlaku/belum terbaca'
        return f'{obj.file_asli.name} · {pages} · {_human_file_size(obj.ukuran_file or obj.file_asli.size)}'

    @admin.display(description='Status Indexing', ordering='status_indexing')
    def status_indexing_badge(self, obj):
        if not obj:
            return 'Akan ditentukan setelah dokumen disimpan.'
        colors = {
            DokumenResmi.StatusIndexing.BELUM: ('#e5e7eb', '#374151'),
            DokumenResmi.StatusIndexing.MENUNGGU: ('#fef3c7', '#92400e'),
            DokumenResmi.StatusIndexing.DIPROSES: ('#dbeafe', '#1e40af'),
            DokumenResmi.StatusIndexing.BERHASIL: ('#bbf7d0', '#14532d'),
            DokumenResmi.StatusIndexing.GAGAL: ('#fecaca', '#7f1d1d'),
        }
        background, foreground = colors.get(obj.status_indexing, colors[DokumenResmi.StatusIndexing.BELUM])
        return format_html(
            '<span style="background:{};color:{};border-radius:999px;padding:3px 9px;font-weight:700;">{}</span>',
            background, foreground, obj.get_status_indexing_display(),
        )

    @admin.display(description='Status Embedding')
    def status_embedding(self, obj):
        if not obj or not obj.pk:
            return format_html('<span style="color:#6b7280;">Belum disimpan</span>')
        chunk_count = getattr(obj, '_chunk_count', None)
        if chunk_count is None:
            chunk_count = obj.chunks.count()
        if obj.status_validasi != DokumenResmi.StatusValidasi.TERVERIFIKASI:
            return format_html(
                '<span style="background:#e5e7eb;color:#374151;border-radius:999px;padding:3px 9px;font-weight:700;">Tidak aktif untuk RAG</span>'
            )
        if chunk_count:
            return format_html(
                '<span style="background:#bbf7d0;color:#14532d;border-radius:999px;padding:3px 9px;font-weight:700;">Sudah di-embed ({} chunk)</span>',
                chunk_count,
            )
        return format_html(
            '<span style="background:#fecaca;color:#7f1d1d;border-radius:999px;padding:3px 9px;font-weight:700;">Belum di-embed</span>'
        )


def _human_file_size(size):
    value = float(size or 0)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{value:.1f} {unit}'
        value /= 1024


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

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='Preview Teks')
    def preview_teks(self, obj):
        return (obj.teks_potongan[:75] + '...') if len(obj.teks_potongan) > 75 else obj.teks_potongan


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        'pertanyaan', 'subkategori_sumber', 'status_validasi', 'status_indexing',
        'aktif_sumber', 'sumber_ringkas', 'sinkronisasi_pada',
    )
    list_filter = (
        'status_validasi', 'status_indexing', 'aktif_sumber', 'kategori',
        'subkategori_sumber',
    )
    search_fields = ('pertanyaan', 'jawaban', 'sumber_url', 'subkategori_sumber')
    ordering = ('-jumlah_dilihat',)
    readonly_fields = (
        'sumber_kunci', 'hash_konten', 'sinkronisasi_pada', 'divalidasi_oleh',
        'divalidasi_pada', 'status_indexing', 'vector_id', 'diindeks_pada',
        'pesan_indexing', 'jumlah_dilihat', 'rating_membantu',
    )
    actions = ('verifikasi_dan_antrekan', 'nonaktifkan_faq')
    fieldsets = (
        ('Isi FAQ', {'fields': ('pertanyaan', 'jawaban', 'kategori')}),
        ('Sumber resmi', {'fields': (
            'sumber_url', 'subkategori_sumber', 'aktif_sumber', 'sumber_kunci',
            'hash_konten', 'sinkronisasi_pada',
        )}),
        ('Validasi petugas', {'fields': (
            'status_validasi', 'divalidasi_oleh', 'divalidasi_pada',
        )}),
        ('Status knowledge base', {'fields': (
            'status_indexing', 'vector_id', 'diindeks_pada', 'pesan_indexing',
        )}),
        ('Statistik publik', {'fields': ('jumlah_dilihat', 'rating_membantu'), 'classes': ('collapse',)}),
    )
    formfield_overrides = TEXTAREA_WIDGET

    @admin.display(description='Sumber')
    def sumber_ringkas(self, obj):
        if not obj.sumber_url:
            return 'Internal'
        return format_html('<a href="{}" target="_blank" rel="noreferrer">DJKI ↗</a>', obj.sumber_url)

    def save_model(self, request, obj, form, change):
        if obj.status_validasi == FAQ.StatusValidasi.TERVERIFIKASI:
            if not obj.divalidasi_pada or 'status_validasi' in form.changed_data:
                obj.divalidasi_oleh = request.user
                obj.divalidasi_pada = timezone.now()
            if {'pertanyaan', 'jawaban', 'status_validasi'} & set(form.changed_data):
                obj.status_indexing = FAQ.StatusIndexing.MENUNGGU
                obj.pesan_indexing = ''
        elif 'status_validasi' in form.changed_data:
            obj.divalidasi_oleh = None
            obj.divalidasi_pada = None
            obj.status_indexing = FAQ.StatusIndexing.BELUM
        super().save_model(request, obj, form, change)

    @admin.action(description='Verifikasi dan antrekan FAQ terpilih untuk indexing')
    def verifikasi_dan_antrekan(self, request, queryset):
        total = queryset.filter(aktif_sumber=True).update(
            status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
            divalidasi_oleh=request.user,
            divalidasi_pada=timezone.now(),
            status_indexing=FAQ.StatusIndexing.MENUNGGU,
            pesan_indexing='',
        )
        self.message_user(request, f'{total} FAQ diverifikasi dan masuk antrean indexing.', messages.SUCCESS)

    @admin.action(description='Nonaktifkan FAQ terpilih')
    def nonaktifkan_faq(self, request, queryset):
        from .rag_service import remove_faq_from_index

        targets = list(queryset)
        for faq in targets:
            try:
                remove_faq_from_index(faq.id)
            except Exception:
                pass
        total = queryset.update(
            status_validasi=FAQ.StatusValidasi.DINONAKTIFKAN,
            aktif_sumber=False,
            status_indexing=FAQ.StatusIndexing.BELUM,
            vector_id=None,
            diindeks_pada=None,
        )
        self.message_user(request, f'{total} FAQ dinonaktifkan.', messages.SUCCESS)


@admin.register(SinkronisasiFAQLog)
class SinkronisasiFAQLogAdmin(admin.ModelAdmin):
    list_display = (
        'status', 'jumlah_halaman', 'jumlah_ditemukan', 'jumlah_baru',
        'jumlah_diperbarui', 'jumlah_dinonaktifkan', 'dimulai_pada',
    )
    list_filter = ('status', 'dimulai_pada')
    readonly_fields = [field.name for field in SinkronisasiFAQLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
