# Panduan Knowledge Base Chatbot Ahli KI

Chatbot telah memiliki routing pertanyaan untuk sembilan kelompok Kekayaan Intelektual (KI). Namun, jawaban ahli tetap bergantung pada sumber resmi yang sudah diverifikasi dan diindeks. Jangan mengisi celah pengetahuan hanya dengan instruksi model karena itu meningkatkan risiko jawaban hukum yang keliru.

## Cakupan yang harus tersedia

Lengkapi basis pengetahuan untuk:

1. Merek
2. Hak Cipta
3. Paten
4. Desain Industri
5. Indikasi Geografis
6. Desain Tata Letak Sirkuit Terpadu (DTLST)
7. Rahasia Dagang
8. Kekayaan Intelektual Komunal (KIK)
9. Perlindungan Varietas Tanaman (PVT)

Untuk setiap jenis, sediakan dokumen atau FAQ resmi mengenai:

- definisi, objek, dan batas perlindungan;
- dasar hukum dan peraturan terbaru;
- syarat serta dokumen permohonan;
- tahapan dan kanal pengajuan resmi;
- biaya, waktu proses, dan masa perlindungan;
- pemeriksaan, keberatan, penolakan, dan upaya lanjutan;
- lisensi, pengalihan, pencatatan, dan pemeliharaan hak;
- pelanggaran, penyelesaian sengketa, dan kanal pengaduan;
- contoh kasus edukatif dan pertanyaan yang sering diajukan.

Utamakan DJKI untuk domain yang berada di bawah DJKI. Untuk PVT, gunakan sumber resmi Pusat Perlindungan Varietas Tanaman dan Perizinan Pertanian (PVTPP), Kementerian Pertanian. Simpan URL sumber dan tanggal berlakunya informasi, terutama untuk biaya dan prosedur.

## Alur pengisian yang aman

1. Tambahkan dokumen atau impor FAQ resmi sebagai **draf**.
2. Petugas memeriksa isi, kategori, sumber, versi peraturan, dan tanggal berlaku.
3. Ubah status menjadi **terverifikasi** hanya setelah pemeriksaan manusia.
4. Jalankan proses indexing.
5. Audit cakupan dan uji pertanyaan per jenis KI.

Perintah dari folder `sikapki_backend`:

```powershell
.\.venv\Scripts\python.exe manage.py import_official_ki_sources --dry-run
.\.venv\Scripts\python.exe manage.py import_official_ki_sources
.\.venv\Scripts\python.exe manage.py audit_ki_coverage
.\.venv\Scripts\python.exe manage.py process_document_queue
.\.venv\Scripts\python.exe manage.py reindex_all_documents
```

Importer mengambil katalog halaman pemerintah DJKI dan PVTPP. Dokumen baru selalu
masuk sebagai draf. Untuk mengecek perubahan pada sumber yang sudah terverifikasi:

```powershell
.\.venv\Scripts\python.exe manage.py import_official_ki_sources --refresh-verified
```

Jika isi sumber berubah, dokumen otomatis dikembalikan ke draf dan dikeluarkan dari
indeks sampai diverifikasi ulang.

## Sinkronisasi FAQ resmi

Perintah sinkronisasi sekarang dapat dipakai untuk kategori selain Merek:

```powershell
.\.venv\Scripts\python.exe manage.py sync_faq_djki `
  --category "Desain Industri" `
  --url "URL-FAQ-RESMI" `
  --dry-run
```

Selalu mulai dengan `--dry-run`. Jika situs resmi membatasi akses otomatis, simpan halaman melalui browser dan gunakan file tersebut—jangan mencoba melewati proteksi situs:

```powershell
.\.venv\Scripts\python.exe manage.py sync_faq_djki `
  --category "Desain Industri" `
  --url "URL-FAQ-RESMI" `
  --html-file ".\data\faq-desain-industri.html" `
  --subcategory "Desain Industri Umum" `
  --dry-run
```

Hapus `--dry-run` setelah hasil ekstraksi diperiksa. Konten baru tetap berstatus draf dan tidak langsung dipercaya chatbot.

## Matriks evaluasi minimum

Untuk setiap jenis KI, siapkan pertanyaan uji untuk definisi, syarat, prosedur, biaya, waktu, masa perlindungan, lisensi/pengalihan, dan sengketa. Tambahkan pula:

- pertanyaan ambigu, agar chatbot meminta klarifikasi objek;
- perbandingan lintas KI, misalnya merek vs hak cipta;
- pertanyaan di luar basis pengetahuan, agar chatbot mengakui keterbatasan;
- pertanyaan berisiko hukum tinggi, agar chatbot tidak memberi kepastian atau strategi hukum personal;
- pertanyaan dengan angka atau aturan lama, agar jawaban mengikuti sumber terbaru yang terverifikasi.

Target operasional yang disarankan: seluruh kategori memiliki sumber terverifikasi dan terindeks, jawaban selalu menyertakan sumber, dan tidak ada jawaban substantif ketika bukti untuk domain yang ditanyakan belum tersedia.
