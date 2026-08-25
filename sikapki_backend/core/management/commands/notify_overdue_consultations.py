from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatbot.models import PercakapanChatbot
from core.models import SlaNotification


class Command(BaseCommand):
    help = 'Buat notifikasi admin untuk konsultasi Helpdesk KI yang melewati SLA.'

    def handle(self, *args, **options):
        overdue = PercakapanChatbot.objects.filter(
            dieskalasi=True,
            batas_tindak_lanjut__lt=timezone.now(),
        ).exclude(status_tindak_lanjut=PercakapanChatbot.StatusTindakLanjut.SELESAI)
        recipients = get_user_model().objects.filter(is_active=True, is_staff=True)
        created = 0
        for consultation in overdue.iterator():
            message = (
                f'Konsultasi {_consultation_code(consultation)} melewati target tindak lanjut '
                f'{consultation.batas_tindak_lanjut:%d/%m/%Y %H:%M} WITA.'
            )
            for recipient in recipients:
                _, was_created = SlaNotification.objects.get_or_create(
                    recipient=recipient,
                    consultation_id=consultation.pelacakan_id,
                    defaults={'message': message},
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f'{created} notifikasi SLA dibuat untuk {overdue.count()} konsultasi terlambat.',
        ))


def _consultation_code(consultation):
    local_date = consultation.dibuat_pada.astimezone().strftime('%Y%m%d')
    return f'KI-{local_date}-{consultation.pk:06d}'
