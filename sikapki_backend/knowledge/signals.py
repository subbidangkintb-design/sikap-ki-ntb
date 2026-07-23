import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DokumenResmi, FAQ

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DokumenResmi)
def index_new_document(sender, instance, created, **kwargs):
    from .rag_service import schedule_remove_from_index

    try:
        if instance.status_validasi == DokumenResmi.StatusValidasi.TERVERIFIKASI:
            if instance.status_indexing == DokumenResmi.StatusIndexing.BELUM:
                DokumenResmi.objects.filter(pk=instance.id).update(
                    status_indexing=DokumenResmi.StatusIndexing.MENUNGGU,
                    pesan_indexing='',
                )
        else:
            DokumenResmi.objects.filter(pk=instance.id).update(
                status_indexing=DokumenResmi.StatusIndexing.BELUM,
                pesan_indexing='', indexing_dimulai_pada=None, indexing_selesai_pada=None,
            )
            schedule_remove_from_index(instance.id)
    except Exception:
        logger.exception('Gagal memperbarui indeks DokumenResmi id=%s', instance.id)


@receiver(post_delete, sender=DokumenResmi)
def remove_deleted_document(sender, instance, **kwargs):
    from .rag_service import schedule_remove_from_index

    schedule_remove_from_index(instance.id)


@receiver(post_save, sender=FAQ)
def queue_verified_faq(sender, instance, **kwargs):
    if (
        instance.status_validasi == FAQ.StatusValidasi.TERVERIFIKASI
        and instance.aktif_sumber
        and instance.status_indexing == FAQ.StatusIndexing.BELUM
    ):
        FAQ.objects.filter(pk=instance.pk).update(
            status_indexing=FAQ.StatusIndexing.MENUNGGU,
            pesan_indexing='',
        )
    elif instance.vector_id and (
        instance.status_validasi != FAQ.StatusValidasi.TERVERIFIKASI
        or not instance.aktif_sumber
    ):
        from .rag_service import remove_faq_from_index

        try:
            remove_faq_from_index(instance.id)
            FAQ.objects.filter(pk=instance.pk).update(
                status_indexing=FAQ.StatusIndexing.BELUM,
                vector_id=None, diindeks_pada=None,
            )
        except Exception:
            logger.exception('Gagal menonaktifkan indeks FAQ id=%s', instance.id)


@receiver(post_delete, sender=FAQ)
def remove_deleted_faq(sender, instance, **kwargs):
    from .rag_service import remove_faq_from_index

    try:
        remove_faq_from_index(instance.id)
    except Exception:
        logger.exception('Gagal menghapus indeks FAQ id=%s', instance.id)
