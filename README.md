# SIKAP-KI NTB

SIKAP-KI NTB adalah MVP layanan Kekayaan Intelektual berbasis AI untuk:

- cek awal risiko nama merek,
- arahan peninjauan daya pembeda nama dan label merek,
- chatbot tanya jawab berbasis RAG,
- FAQ layanan KI.

## 1. Prasyarat

Install di mesin lokal:

- Python 3.12
- PostgreSQL
- Node.js + npm
- Koneksi internet dan Gemini API key dari Google AI Studio

## 2. Backend Django

Masuk ke backend:

```powershell
cd D:\VSCODE\sikap-ki-ntb\sikapki_backend
```

Aktifkan virtual environment:

```powershell
.\venv\Scripts\activate
```

Install dependency:

```powershell
pip install -r requirements.txt
```

Pastikan `.env` berisi:

```env
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://sikapki_user:sikapki_pass@localhost:5432/sikapki_db
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
AI_PROVIDER=gemini
AI_MODEL=gemini-3.1-flash-lite
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:latest
GEMINI_API_KEY=isi_api_key_dari_google_ai_studio
DEEPSEEK_API_KEY=
```

### Pilihan Provider AI

Default backend memakai Gemini cloud supaya tidak mengunduh model AI lokal:

```env
AI_PROVIDER=gemini
AI_MODEL=gemini-3.1-flash-lite
```

Untuk kompatibilitas lama, backend masih mendukung Ollama lokal:

```env
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:latest
```

Atau gunakan DeepSeek API:

```env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=isi_api_key_dari_deepseek
```

Setelah mengganti provider/model di `.env`, restart Django. Dengan Gemini/DeepSeek, Ollama tidak perlu dipasang. RAG juga memakai Gemini Embedding API dan hanya menyimpan indeks vektor aplikasi yang berukuran relatif kecil.

Jalankan migrasi dan seed data:

```powershell
python manage.py migrate
python manage.py sync_wipo_nice
python manage.py seed_demo_data
```

Perintah `sync_wipo_nice` mengunduh 10.123 istilah resmi Nice Classification NCL 13-2026 dari WIPO dan menyimpannya untuk mesin klasifikasi. Jalankan kembali saat versi Nice aplikasi diperbarui. Hasil kelas tetap perlu diverifikasi melalui [SKM DJKI](https://skm.dgip.go.id/); akses otomatis SKM dapat dibatasi oleh perlindungan situs.

Index ulang dokumen RAG:

```powershell
python manage.py reindex_all_documents
```

Untuk upload dokumen melalui Django Admin, buka `/admin/knowledge/dokumenresmi/`. Sistem menerima PDF, TXT, atau Markdown hingga 100 MB dan PDF di atas 100 halaman. Simpan sebagai draf untuk pemeriksaan, lalu pilih aksi **Verifikasi dan antrekan dokumen terpilih untuk indexing**. Jalankan worker antrean pada terminal backend terpisah:

```powershell
python manage.py process_document_queue --watch
```

Upload dan indexing dipisahkan agar halaman admin tidak timeout. Status `Menunggu`, `Sedang diproses`, `Berhasil`, atau `Gagal` terlihat di daftar dokumen. PDF hasil pemindaian gambar otomatis memakai OCR Gemini cloud dalam batch kecil; tidak ada model OCR lokal yang perlu dipasang. Pastikan dokumen boleh dikirim ke layanan Gemini sebelum memverifikasinya.

Jalankan backend:

```powershell
python manage.py runserver 127.0.0.1:8000
```

Tes cepat:

```powershell
curl http://127.0.0.1:8000/api/knowledge/faq/
```

## 3. Frontend React

Buka terminal baru:

```powershell
cd D:\VSCODE\sikap-ki-ntb\sikapki_frontend
```

Pastikan `.env` berisi:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Install dependency:

```powershell
npm.cmd install
```

Jalankan frontend:

```powershell
npm.cmd run dev
```

Buka:

```text
http://127.0.0.1:5173
```

## 4. Skenario Demo Kadiv

### A. Cek & Saran Merek

Buka:

```text
http://127.0.0.1:5173/cek-merek
```

Input:

```text
Nama merek:
Kopi Lombok Asli

Deskripsi produk/jasa:
kedai kopi kemasan dan minuman siap saji
```

Hasil yang diharapkan:

- kelas Nice terdeteksi sekitar `30` dan/atau `43`,
- muncul merek mirip dari data seed seperti varian `Kopi Kita` atau `Sasak Lombok`,
- skor risiko idealnya `sedang` untuk demo,
- saran naratif muncul,
- disclaimer terlihat jelas.

Jika daftar merek mirip kosong, jalankan ulang:

```powershell
python manage.py seed_demo_data
```

Lalu cek data mirror:

```powershell
python manage.py shell -c "from trademark.models import MirrorPDKI; print(list(MirrorPDKI.objects.values_list('nama_merek','kelas_nice')[:20]))"
```

### B. Chatbot Pertanyaan KI

Buka:

```text
http://127.0.0.1:5173/chatbot
```

Tanyakan:

```text
Berapa lama proses pendaftaran merek?
```

Hasil yang diharapkan:

- AI menjawab dalam Bahasa Indonesia,
- jawaban mengutip sumber dokumen/FAQ seed,
- ada tombol rating membantu/tidak membantu.

### C. Chatbot Pertanyaan di Luar Topik

Tanyakan:

```text
bagaimana cara membuat SIM?
```

Hasil yang diharapkan:

- sistem tidak mengarang jawaban,
- jika konteks tidak cukup, response `dieskalasi=true`,
- frontend menampilkan kotak "Perlu arahan petugas".

## 5. Test API Langsung

Cek merek:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/trademark/cek/" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"nama_merek":"Kopi Lombok Asli","deskripsi_produk":"kedai kopi kemasan dan minuman siap saji"}'
```

Chatbot:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/chatbot/tanya/" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"pertanyaan":"Berapa lama proses pendaftaran merek?"}'
```

FAQ:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/knowledge/faq/?q=merek"
```

## 6. Admin Petugas

Jalankan:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Buka:

```text
http://127.0.0.1:8000/admin/
```

Halaman admin sudah memiliki dashboard ringkas, filter eskalasi chatbot, status embedding dokumen, dan textarea nyaman untuk teks panjang.

### Menyiapkan pembanding visual etiket merek

Upload logo pengguna tidak disimpan. Logo hanya dibaca di memori, diubah menjadi sidik visual ringkas, lalu dibandingkan dengan sidik etiket referensi yang tersedia. Proses ini tidak mengunduh model AI lokal dan tidak mengirim logo pengguna ke layanan pihak ketiga.

1. Di admin, buka **Mirror PDKI** lalu pilih data merek.
2. Unggah **Label merek** PNG/JPEG dari data resmi yang sudah diverifikasi.
3. Isi **Sumber label URL** dengan tautan halaman PDKI resmi sebagai jejak audit.
4. Simpan. Kolom **Visual siap** akan aktif setelah embedding berhasil dibuat.

Untuk mengindeks ulang semua etiket yang sudah diunggah:

```powershell
.\.venv\Scripts\python.exe manage.py reindex_visual_merek --force
```

Etiket dari Berita Resmi Merek DJKI diekstrak otomatis, diperkecil maksimal 384 × 384 piksel, dan disimpan sebagai JPEG hemat ruang. Cakupan hasil visual selalu mengikuti jumlah etiket publikasi yang berhasil tersinkron dan tidak boleh disebut sebagai penelusuran seluruh PDKI.

### Sinkronisasi data pembanding merek resmi

Situs pencarian PDKI melindungi akses otomatis dengan WAF, sehingga aplikasi tidak mencoba melewati CAPTCHA atau mekanisme pengaman tersebut. Sebagai sumber awal yang dapat diaudit, backend membaca daftar permohonan pada **Berita Resmi Merek Seri-A** yang dipublikasikan DJKI.

Ambil publikasi terbaru:

```powershell
.\.venv\Scripts\python.exe manage.py sync_berita_resmi_merek --limit 5
```

Periksa satu publikasi tanpa menyimpan data:

```powershell
.\.venv\Scripts\python.exe manage.py sync_berita_resmi_merek --dry-run --url https://www.dgip.go.id/berita-resmi/2840/download
```

Perintah akan melewati URL publikasi yang data teks dan etiketnya sudah berhasil diproses. Opsi `--force` hanya diperlukan jika petugas memang ingin membaca ulang publikasi yang sama. File PDF dipakai sebagai berkas sementara dan ditutup setelah pemrosesan; database menyimpan nomor permohonan, nama merek, kelas Nice, tanggal, tautan sumber resmi, etiket terkompresi, dan sidik visual. Gunakan `--without-labels` hanya jika sinkronisasi darurat perlu dilakukan tanpa gambar.

Untuk mengisi seluruh arsip historis secara hemat ruang, jalankan berulang:

```powershell
.\.venv\Scripts\python.exe manage.py sync_berita_resmi_merek --all --without-labels --batch-size 20 --delay 1
```

Mode arsip penuh memproses maksimal 20 PDF yang belum selesai pada setiap eksekusi, melewati log sukses, dan melanjutkan dari posisi terakhir. PDF diunduh satu per satu sebagai berkas sementara. Etiket historis tidak disimpan dalam mode ini karena seluruh arsip dapat menghabiskan beberapa GB; etiket publikasi terbaru tetap disinkronkan oleh perintah reguler `--limit 5`. Data dari publikasi lama tidak akan menimpa versi permohonan yang berasal dari publikasi lebih baru.

Jika bootstrap dijalankan sebagai proses latar belakang, pantau progresnya dengan:

```powershell
Get-Content .\logs\sync-arsip-merek.log -Wait
```

Apabila komputer mati atau koneksi terputus, jalankan kembali perintah mode `--all`. Publikasi berstatus berhasil akan dilewati dan hanya publikasi gagal/belum diproses yang dicoba kembali.

Untuk menjalankannya berkala di Windows Task Scheduler:

1. Buat task bernama `SIKAP-KI - Sinkronisasi Merek DJKI` dan pilih pemicu harian, misalnya pukul `02.00 WITA`.
2. Isi **Program/script** dengan path absolut `sikapki_backend\.venv\Scripts\python.exe`.
3. Isi **Add arguments** dengan `manage.py sync_berita_resmi_merek --limit 5`.
4. Isi **Start in** dengan path absolut folder `sikapki_backend`.
5. Aktifkan percobaan ulang bila task gagal, misalnya setiap 30 menit maksimal 3 kali.

Riwayat proses dapat dilihat di admin pada menu **Sinkronisasi PDKI Log**. Data Berita Resmi Merek adalah data publikasi permohonan, bukan salinan lengkap PDKI dan bukan status hukum terkini. Hasil cek tetap harus menyediakan tautan sumber serta mengarahkan verifikasi akhir ke PDKI/Helpdesk KI Kanwil Kementerian Hukum NTB.

### Role dan keamanan akses

- `Super Admin`: akses penuh dan dapat membuat akun petugas.
- `Petugas KI`: mengelola knowledge base serta membaca histori layanan.
- `Verifikator`: memeriksa knowledge base dan histori layanan.
- Pengguna publik hanya dapat memakai layanan cek merek, chatbot, dan membaca FAQ.
- Histori chatbot dan cek merek tidak dapat dibaca melalui API tanpa akun petugas.

Untuk membuat akun petugas melalui admin:

1. Buka menu **Users**, buat pengguna, lalu aktifkan **Staff status**.
2. Buka menu **Profil Pengguna** dan hubungkan pengguna tersebut.
3. Pilih role `Petugas KI` atau `Verifikator`.

Jangan memberikan `Superuser status` kepada akun operasional harian.

### Memasukkan dokumen resmi ke knowledge base

1. Masuk ke admin dan buka **Dokumen Resmi**.
2. Pilih kategori KI dan isi judul yang menyebutkan nama dokumen/sumber.
3. Isi **Sumber URL** dengan halaman resmi asal dokumen bila tersedia.
4. Unggah PDF berbasis teks atau tempel teks yang sudah diperiksa petugas pada **Teks lengkap**.
5. Simpan sebagai **Draf / belum diverifikasi**. Dokumen draf tidak dipakai oleh chatbot.
6. Periksa judul, kategori, sumber, dan hasil ekstraksi teks. Setelah benar, ubah **Status validasi** menjadi **Terverifikasi** lalu simpan.
7. Pastikan **Status Embedding** berubah menjadi **Sudah di-embed**, kemudian uji pertanyaan terkait melalui chatbot dan periksa sumber jawabannya.

Dokumen yang sudah kedaluwarsa atau tidak lagi berlaku harus diubah menjadi **Dinonaktifkan**. Sistem otomatis menghapusnya dari indeks chatbot tanpa menghapus arsip dokumen.

Gunakan hanya regulasi, SOP, panduan DJKI, dan FAQ yang telah divalidasi petugas. PDF hasil scan gambar tidak dapat diekstrak tanpa OCR; untuk dokumen tersebut, isi **Teks lengkap** secara manual.

Untuk langsung melihat pertanyaan dieskalasi:

```text
http://127.0.0.1:8000/admin/chatbot/percakapanchatbot/?dieskalasi__exact=1
```

## 7. Troubleshooting

Jika CORS error:

- pastikan frontend berjalan di `http://127.0.0.1:5173`,
- pastikan backend `.env` punya `http://127.0.0.1:5173` di `CORS_ALLOWED_ORIGINS`,
- restart Django setelah mengubah `.env`.

Jika test Django gagal membuat database:

```sql
ALTER USER sikapki_user CREATEDB;
```

Jika Vite gagal karena PowerShell memblokir `npm.ps1`, gunakan:

```powershell
npm.cmd run dev
```
