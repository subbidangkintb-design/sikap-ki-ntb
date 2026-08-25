"""Job queue berbasis database untuk pekerjaan berat SIKAP-KI."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import BackgroundJob


def enqueue_job(kind, payload, *, created_by=None, max_attempts=None):
    return BackgroundJob.objects.create(
        kind=kind,
        payload=payload,
        created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        max_attempts=max_attempts or settings.BACKGROUND_JOB_MAX_ATTEMPTS,
    )


def claim_next_job():
    now = timezone.now()
    with transaction.atomic():
        stale_before = now - timedelta(
            minutes=getattr(settings, 'BACKGROUND_JOB_STALE_MINUTES', 120),
        )
        BackgroundJob.objects.filter(
            status=BackgroundJob.Status.RUNNING,
            started_at__lt=stale_before,
        ).update(
            status=BackgroundJob.Status.QUEUED,
            available_at=now,
            started_at=None,
            error_message='Worker sebelumnya terhenti; job dijadwalkan ulang.',
        )
        candidate = BackgroundJob.objects.filter(
            status=BackgroundJob.Status.QUEUED,
            available_at__lte=now,
        ).order_by('created_at').first()
        if not candidate:
            return None
        updated = BackgroundJob.objects.filter(
            pk=candidate.pk,
            status=BackgroundJob.Status.QUEUED,
        ).update(
            status=BackgroundJob.Status.RUNNING,
            attempts=candidate.attempts + 1,
            started_at=now,
            error_message='',
        )
        if not updated:
            return None
    return BackgroundJob.objects.get(pk=candidate.pk)


def run_job(job):
    try:
        result = dispatch_job(job)
    except Exception as exc:  # worker harus tetap hidup setelah satu job gagal
        if job.attempts < job.max_attempts:
            delay = min(300, 2 ** max(job.attempts - 1, 0) * 5)
            BackgroundJob.objects.filter(pk=job.pk).update(
                status=BackgroundJob.Status.QUEUED,
                available_at=timezone.now() + timedelta(seconds=delay),
                error_message=str(exc)[:4000],
                finished_at=None,
            )
            return False, f'job dijadwalkan ulang dalam {delay} detik: {exc}'
        BackgroundJob.objects.filter(pk=job.pk).update(
            status=BackgroundJob.Status.FAILED,
            error_message=str(exc)[:4000],
            finished_at=timezone.now(),
        )
        return False, str(exc)

    BackgroundJob.objects.filter(pk=job.pk).update(
        status=BackgroundJob.Status.SUCCEEDED,
        result=result or {},
        error_message='',
        finished_at=timezone.now(),
    )
    return True, result


def dispatch_job(job):
    payload = job.payload or {}
    if job.kind == BackgroundJob.Kind.CHATBOT_AI:
        from rest_framework.test import APIRequestFactory
        from chatbot.views import ChatbotViewSet
        raw_request = APIRequestFactory().post(
            '/api/chatbot/tanya/',
            {
                'pertanyaan': payload['pertanyaan'],
                'sesi_id': payload['sesi_id'],
            },
            format='json',
        )
        response = ChatbotViewSet.as_view({'post': 'tanya'})(raw_request)
        if response.status_code >= 400:
            raise RuntimeError(f'Chatbot mengembalikan HTTP {response.status_code}: {response.data}')
        return dict(response.data)
    if job.kind == BackgroundJob.Kind.CLASSIFICATION_AI:
        from rest_framework.test import APIRequestFactory
        from trademark.views import CekMerekAIViewSet
        raw_request = APIRequestFactory().post(
            '/api/trademark/cek/',
            {
                'nama_merek': payload['nama_merek'],
                'deskripsi_produk': payload['deskripsi_produk'],
            },
            format='json',
        )
        response = CekMerekAIViewSet.as_view({'post': 'cek'})(raw_request)
        if response.status_code >= 400:
            raise RuntimeError(f'Klasifikasi mengembalikan HTTP {response.status_code}: {response.data}')
        return dict(response.data)
    if job.kind == BackgroundJob.Kind.DOCUMENT_INDEX:
        from knowledge.rag_service import embed_and_store
        return {'chunk_count': embed_and_store(payload['document_id'])}
    if job.kind == BackgroundJob.Kind.FAQ_INDEX:
        from knowledge.rag_service import embed_and_store_faq
        return {'chunk_count': embed_and_store_faq(payload['faq_id'])}
    if job.kind == BackgroundJob.Kind.BRM_ENRICH:
        from trademark.pdki_sync import sync_bulletin
        log = sync_bulletin(payload['url'], force=True, include_labels=False)
        return {
            'url': payload['url'],
            'judul': log.judul_sumber,
            'ditemukan': log.jumlah_ditemukan,
            'diperbarui': log.jumlah_diperbarui,
        }
    raise ValueError(f'Jenis background job tidak didukung: {job.kind}')
