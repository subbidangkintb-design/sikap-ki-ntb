import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DokumenResmi

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DokumenResmi)
def index_new_document(sender, instance, created, **kwargs):
    if not created:
        return

    from .rag_service import schedule_embed_and_store

    try:
        schedule_embed_and_store(instance.id)
    except Exception:
        logger.exception('Gagal menjadwalkan embedding untuk DokumenResmi id=%s', instance.id)
