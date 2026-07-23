from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from knowledge.models import DokumenResmi, FAQ, KategoriKI


REQUIRED_DOMAINS = (
    'Merek', 'Hak Cipta', 'Paten', 'Desain Industri', 'Indikasi Geografis',
    'DTLST', 'Rahasia Dagang', 'Kekayaan Intelektual Komunal',
    'Perlindungan Varietas Tanaman',
)


class Command(BaseCommand):
    help = 'Audit kelengkapan knowledge base terverifikasi untuk seluruh rumpun KI.'

    def handle(self, *args, **options):
        rows = {
            row['nama']: row
            for row in KategoriKI.objects.annotate(
                verified_documents=Count('dokumen', filter=Q(
                    dokumen__status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
                ), distinct=True),
                indexed_documents=Count('dokumen', filter=Q(
                    dokumen__status_validasi=DokumenResmi.StatusValidasi.TERVERIFIKASI,
                    dokumen__status_indexing=DokumenResmi.StatusIndexing.BERHASIL,
                ), distinct=True),
                verified_faq=Count('faq', filter=Q(
                    faq__status_validasi=FAQ.StatusValidasi.TERVERIFIKASI,
                    faq__aktif_sumber=True,
                ), distinct=True),
            ).values('nama', 'verified_documents', 'indexed_documents', 'verified_faq')
        }
        incomplete = []
        self.stdout.write('Cakupan knowledge base KI:')
        for domain in REQUIRED_DOMAINS:
            row = rows.get(domain, {})
            documents = row.get('verified_documents', 0)
            indexed = row.get('indexed_documents', 0)
            faq = row.get('verified_faq', 0)
            ready = indexed > 0 or faq > 0
            marker = 'SIAP' if ready else 'KOSONG'
            self.stdout.write(
                f'  [{marker}] {domain}: dokumen terverifikasi={documents}, '
                f'dokumen terindeks={indexed}, FAQ terverifikasi={faq}',
            )
            if not ready:
                incomplete.append(domain)
        if incomplete:
            self.stdout.write(self.style.WARNING(
                'Belum siap menjawab secara ahli: ' + ', '.join(incomplete),
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Seluruh rumpun KI memiliki sumber terindeks.'))
