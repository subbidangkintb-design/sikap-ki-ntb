"""
Management command untuk mengisi database dengan data contoh (demo/dummy)
supaya development & testing fitur (terutama similarity check merek) bisa
langsung dicoba tanpa menunggu data asli dari PDKI.

Cara pakai:
    python manage.py seed_demo_data

Command ini AMAN dijalankan berkali-kali (idempotent) — memakai
get_or_create, jadi tidak akan menghasilkan data duplikat kalau dijalankan
ulang.
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from knowledge.models import KategoriKI, DokumenResmi, FAQ
from trademark.models import MirrorPDKI


class Command(BaseCommand):
    help = 'Mengisi database dengan data contoh: kategori KI, dokumen resmi, FAQ, dan mirror PDKI.'

    @transaction.atomic
    def handle(self, *args, **options):
        kategori_map = self._seed_kategori()
        self._seed_dokumen(kategori_map)
        self._seed_faq(kategori_map)
        self._seed_mirror_pdki()

        self.stdout.write(self.style.SUCCESS('Seeding data demo selesai.'))

    # ------------------------------------------------------------------
    # 1. Kategori KI
    # ------------------------------------------------------------------
    def _seed_kategori(self):
        data = [
            ('Merek', 'Tanda yang digunakan untuk membedakan barang/jasa satu pelaku usaha dengan lainnya.'),
            ('Hak Cipta', 'Hak eksklusif atas ciptaan di bidang ilmu pengetahuan, seni, dan sastra.'),
            ('Paten', 'Hak eksklusif atas invensi di bidang teknologi untuk jangka waktu tertentu.'),
            ('Desain Industri', 'Kreasi bentuk, konfigurasi, atau komposisi garis/warna suatu produk.'),
            ('Indikasi Geografis', 'Tanda asal produk yang terkait reputasi, kualitas, atau karakteristik geografis.'),
            ('DTLST', 'Pelindungan atas desain tata letak sirkuit terpadu.'),
            ('Rahasia Dagang', 'Informasi teknologi atau bisnis bernilai ekonomi yang dijaga kerahasiaannya.'),
            ('Kekayaan Intelektual Komunal', 'Pengetahuan, ekspresi budaya, dan sumber daya yang dipelihara secara komunal.'),
            ('Perlindungan Varietas Tanaman', 'Pelindungan atas varietas tanaman hasil kegiatan pemuliaan.'),
        ]
        kategori_map = {}
        for nama, deskripsi in data:
            obj, created = KategoriKI.objects.get_or_create(
                nama=nama, defaults={'deskripsi': deskripsi},
            )
            kategori_map[nama] = obj
            self._log(created, 'KategoriKI', nama)
        return kategori_map

    # ------------------------------------------------------------------
    # 2. Dokumen Resmi (10)
    # ------------------------------------------------------------------
    def _seed_dokumen(self, kategori_map):
        dokumen_data = [
            ('Panduan Umum Pendaftaran Merek', 'Merek',
             'Dokumen ini menjelaskan tahapan pendaftaran merek mulai dari pengecekan '
             'ketersediaan nama, pengisian formulir permohonan, pembayaran PNBP, hingga '
             'pemeriksaan formalitas dan substantif oleh pemeriksa merek di Kanwil.'),
            ('SOP Pemeriksaan Substantif Merek', 'Merek',
             'Standar operasional prosedur bagi pemeriksa dalam menilai daya pembeda '
             'suatu merek, termasuk kriteria penolakan karena persamaan pada pokoknya '
             'atau keseluruhannya dengan merek terdaftar lain.'),
            ('Panduan Klasifikasi Kelas Nice', 'Merek',
             'Penjelasan mengenai 45 kelas Nice Classification yang digunakan untuk '
             'mengelompokkan jenis barang dan jasa dalam permohonan merek internasional.'),
            ('Panduan Pendaftaran Hak Cipta Online', 'Hak Cipta',
             'Tata cara pencatatan ciptaan melalui sistem online, termasuk jenis '
             'ciptaan yang dapat didaftarkan seperti buku, lagu, program komputer, '
             'dan karya seni rupa.'),
            ('Perlindungan Hak Cipta Program Komputer', 'Hak Cipta',
             'Ketentuan khusus mengenai jangka waktu perlindungan dan syarat '
             'pencatatan ciptaan program komputer/perangkat lunak.'),
            ('Panduan Permohonan Paten Sederhana', 'Paten',
             'Perbedaan paten biasa dan paten sederhana, termasuk syarat kebaruan '
             'dan jangka waktu perlindungan masing-masing selama 20 dan 10 tahun.'),
            ('SOP Pemeriksaan Substantif Paten', 'Paten',
             'Prosedur pemeriksaan aspek kebaruan (novelty), langkah inventif, dan '
             'kegunaan industri suatu invensi yang diajukan sebagai permohonan paten.'),
            ('Panduan Biaya dan Tarif Layanan Paten', 'Paten',
             'Rincian tarif PNBP untuk setiap tahapan permohonan paten, mulai dari '
             'pendaftaran, pemeriksaan substantif, hingga pemeliharaan tahunan.'),
            ('Panduan Pendaftaran Desain Industri', 'Desain Industri',
             'Persyaratan kebaruan desain industri dan tata cara pengajuan permohonan '
             'beserta lampiran gambar/foto produk yang diperlukan.'),
            ('FAQ Umum Layanan Kekayaan Intelektual Kanwil NTB', 'Desain Industri',
             'Kumpulan pertanyaan umum lintas jenis KI mengenai alur layanan, '
             'estimasi waktu proses, dan kontak layanan Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat.'),
        ]

        for judul, nama_kategori, teks in dokumen_data:
            obj, created = DokumenResmi.objects.get_or_create(
                judul=judul,
                defaults={
                    'kategori': kategori_map.get(nama_kategori),
                    'teks_lengkap': teks,
                },
            )
            self._log(created, 'DokumenResmi', judul)

    # ------------------------------------------------------------------
    # 3. FAQ seputar merek (15)
    # ------------------------------------------------------------------
    def _seed_faq(self, kategori_map):
        merek = kategori_map.get('Merek')
        faq_data = [
            ('Berapa lama proses pendaftaran merek hingga terbit sertifikat?',
             'Secara umum proses pendaftaran merek memakan waktu sekitar 14-18 bulan, '
             'terhitung sejak tanggal penerimaan permohonan, dengan asumsi tidak ada '
             'keberatan/oposisi dari pihak lain.'),
            ('Apa itu kelas Nice dalam pendaftaran merek?',
             'Kelas Nice adalah sistem klasifikasi internasional yang mengelompokkan '
             'barang dan jasa ke dalam 45 kelas, digunakan untuk menentukan ruang '
             'lingkup perlindungan suatu merek.'),
            ('Apakah saya bisa mendaftarkan merek di lebih dari satu kelas sekaligus?',
             'Bisa. Satu permohonan dapat mencakup lebih dari satu kelas, namun biaya '
             'PNBP dihitung per kelas yang diajukan.'),
            ('Berapa lama masa berlaku sertifikat merek?',
             'Sertifikat merek berlaku selama 10 tahun sejak tanggal penerimaan '
             'dan dapat diperpanjang untuk jangka waktu yang sama secara berulang.'),
            ('Apa yang dimaksud dengan persamaan pada pokoknya?',
             'Persamaan pada pokoknya adalah kemiripan yang disebabkan oleh unsur '
             'dominan antara merek yang diajukan dengan merek terdaftar milik pihak '
             'lain, baik dari segi bentuk, cara penempatan, cara penulisan, kombinasi '
             'unsur, maupun bunyi ucapan.'),
            ('Apakah nama pribadi bisa didaftarkan sebagai merek?',
             'Bisa, selama tidak memiliki persamaan dengan nama orang terkenal tanpa '
             'izin yang bersangkutan dan memenuhi syarat daya pembeda.'),
            ('Bagaimana cara mengecek apakah nama merek saya masih tersedia?',
             'Penelusuran awal dapat dilakukan melalui Asisten Penelusuran Awal Merek '
             'ini, atau melalui laman resmi PDKI, sebelum mengajukan permohonan resmi.'),
            ('Apa yang terjadi jika merek saya ditolak pemeriksa substantif?',
             'Pemohon berhak mengajukan tanggapan atas penolakan sementara dalam '
             'jangka waktu yang ditentukan, atau mengajukan banding ke Komisi Banding '
             'Merek jika penolakan tetap dipertahankan.'),
            ('Apakah logo dan nama merek harus didaftarkan terpisah?',
             'Tidak wajib, namun disarankan mendaftarkan logo dan nama merek secara '
             'terpisah agar masing-masing elemen mendapat perlindungan yang lebih kuat.'),
            ('Berapa biaya PNBP untuk pendaftaran merek UMKM?',
             'Pemohon UMKM yang terdaftar mendapatkan tarif PNBP khusus yang lebih '
             'rendah dibanding tarif umum, dengan melampirkan surat rekomendasi UMKM.'),
            ('Apakah merek yang sudah kedaluwarsa bisa didaftarkan pihak lain?',
             'Bisa, merek yang tidak diperpanjang dan telah kedaluwarsa dapat diajukan '
             'kembali oleh pihak lain melalui prosedur pendaftaran baru.'),
            ('Apa perbedaan merek dagang dan merek jasa?',
             'Merek dagang digunakan pada barang yang diperdagangkan, sedangkan merek '
             'jasa digunakan pada jasa yang diperdagangkan oleh seseorang/badan hukum.'),
            ('Apakah saya perlu menggunakan jasa konsultan KI untuk mendaftar merek?',
             'Tidak wajib, pemohon dapat mengajukan permohonan secara mandiri melalui '
             'sistem online, namun penggunaan konsultan KI terdaftar dapat membantu '
             'proses administratif.'),
            ('Bagaimana cara memperpanjang merek yang akan habis masa berlakunya?',
             'Perpanjangan dapat diajukan mulai 6 bulan sebelum tanggal kedaluwarsa '
             'hingga paling lambat 6 bulan setelahnya (dengan denda keterlambatan).'),
            ('Apakah hasil cek kemiripan merek di aplikasi ini bersifat final?',
             'Tidak. Hasil cek pada aplikasi ini bersifat indikatif untuk membantu '
             'estimasi risiko awal; keputusan final tetap berada pada pemeriksa '
             'substantif PDKI.'),
        ]

        for pertanyaan, jawaban in faq_data:
            obj, created = FAQ.objects.get_or_create(
                pertanyaan=pertanyaan,
                defaults={
                    'jawaban': jawaban,
                    'kategori': merek,
                    'jumlah_dilihat': random.randint(5, 500),
                    'rating_membantu': random.randint(0, 50),
                },
            )
            self._log(created, 'FAQ', pertanyaan[:60])

    # ------------------------------------------------------------------
    # 4. Mirror PDKI (20) — sengaja dibuat mirip satu sama lain per klaster
    #    untuk testing fitur similarity check.
    # ------------------------------------------------------------------
    def _seed_mirror_pdki(self):
        klaster = {
            'KopiKita': ['KopiKita', 'Kopi Kita', 'KopiKita Premium', 'Kopikita Nusantara', 'Kopi Kita Asli'],
            'Nusantara Jaya': ['Nusantara Jaya', 'NusantaraJaya', 'Nusantara Djaya', 'Nusantara Jaya Sejahtera', 'Nusa Jaya'],
            'Sasak Lombok': ['Sasak Lombok', 'Sasak Lombok Asli', 'SasakLombok', 'Lombok Sasak Original', 'Sasak Lombok Mandiri'],
            'Mutiara Selaparang': ['Mutiara Selaparang', 'Mutiara Selaparang Indah', 'Selaparang Mutiara', 'Mutiara Selaparang Jaya', 'Mutiara Selaparang NTB'],
        }
        kelas_demo = {
            'KopiKita': '30',
            'Kopi Kita': '43',
            'KopiKita Premium': '30',
            'Kopikita Nusantara': '30',
            'Kopi Kita Asli': '30',
            'Sasak Lombok': '43',
            'Sasak Lombok Asli': '43',
            'SasakLombok': '43',
            'Lombok Sasak Original': '43',
            'Sasak Lombok Mandiri': '43',
        }
        kelas_pilihan = ['25', '29', '30', '32', '35', '43']
        status_pilihan = list(MirrorPDKI.Status.values)
        pemilik_pilihan = [
            'CV Berkah Mandiri', 'PT Sumber Rejeki Abadi', 'UD Cahaya Lombok',
            'PT Nusantara Indah Sejahtera', 'CV Selaparang Makmur', 'UD Mutiara Alam',
        ]

        hari_ini = date.today()
        for nama_dasar, variasi_list in klaster.items():
            for variasi in variasi_list:
                obj, created = MirrorPDKI.objects.update_or_create(
                    nama_merek=variasi,
                    defaults={
                        'kelas_nice': kelas_demo.get(variasi, random.choice(kelas_pilihan)),
                        'status': random.choice(status_pilihan),
                        'pemilik': random.choice(pemilik_pilihan),
                        'tanggal_daftar': hari_ini - timedelta(days=random.randint(30, 2000)),
                    },
                )
                self._log(created, 'MirrorPDKI', variasi)

    # ------------------------------------------------------------------
    def _log(self, created, label, nama):
        if created:
            self.stdout.write(f'  + {label}: {nama}')
        else:
            self.stdout.write(f'  = {label} sudah ada, dilewati: {nama}')
