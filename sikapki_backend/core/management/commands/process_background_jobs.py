import time

from django.conf import settings
from django.core.management.base import BaseCommand

from core.jobs import claim_next_job, run_job


class Command(BaseCommand):
    help = 'Jalankan worker antrean background job SIKAP-KI.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true', help='Pantau antrean terus-menerus.')
        parser.add_argument('--interval', type=int, default=settings.BACKGROUND_JOB_POLL_SECONDS)
        parser.add_argument('--limit', type=int, default=10, help='Jumlah job dalam satu putaran.')

    def handle(self, *args, **options):
        interval = max(1, min(options['interval'], 300))
        limit = max(1, min(options['limit'], 100))
        while True:
            processed = 0
            while processed < limit:
                job = claim_next_job()
                if not job:
                    break
                processed += 1
                ok, detail = run_job(job)
                prefix = self.style.SUCCESS if ok else self.style.WARNING
                self.stdout.write(prefix(f'Job {job.job_id}: {detail}'))
            if not options['watch']:
                if not processed:
                    self.stdout.write('Tidak ada background job dalam antrean.')
                return
            if not processed:
                time.sleep(interval)
