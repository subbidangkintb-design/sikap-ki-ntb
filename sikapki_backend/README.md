# SIKAP-KI NTB — Backend

Prototipe pendukung transformasi tata kelola layanan informasi dan konsultasi awal Kekayaan Intelektual pada Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat. Artificial Intelligence digunakan sebagai teknologi pendukung, bukan pengganti petugas atau pemeriksaan resmi DJKI.
Backend dibangun dengan Django 5 + Django REST Framework, PostgreSQL, dan
disiapkan untuk konsumsi oleh frontend React terpisah.

> ⚠️ Catatan: kode ini dibuat di lingkungan sandbox tanpa akses internet dan
> tanpa server PostgreSQL, sehingga `pip install`, `migrate`, dan `runserver`
> belum bisa dieksekusi langsung di sana. Semua file sudah dicek sintaksnya
> (`py_compile`) dan direview manual, tapi **jalankan langkah-langkah di
> bawah ini di mesin kamu sendiri** untuk memverifikasi end-to-end.

> ⚠️ **Jika kamu sudah pernah menjalankan `makemigrations` sebelumnya**
> (dengan skema model versi lama), hapus dulu file migrasi lama sebelum
> lanjut, karena skema model `knowledge`, `trademark`, dan `chatbot` sudah
> dirombak total mengikuti desain database di proposal:
> ```powershell
> Remove-Item knowledge\migrations\0*.py, trademark\migrations\0*.py, chatbot\migrations\0*.py -ErrorAction SilentlyContinue
> ```
> (Biarkan file `__init__.py` di masing-masing folder `migrations/` tetap ada.)

## 1. Struktur Folder

```
sikapki_backend/
├── manage.py                # entry point perintah Django (runserver, migrate, dst)
├── requirements.txt          # daftar dependency Python
├── .env.example               # template environment variable (copy jadi .env)
├── .gitignore
├── sikapki/                  # folder KONFIGURASI project (bukan "app")
│   ├── settings.py           # semua konfigurasi Django (baca dari .env)
│   ├── urls.py               # routing utama, include urls tiap app
│   ├── wsgi.py / asgi.py     # entry point untuk deployment
│
├── core/                     # APP: user & autentikasi admin
│   ├── models.py             # UserProfile (role: superadmin/petugas/verifikator)
│   ├── admin.py              # tampilan di Django Admin
│   ├── serializers.py        # konversi model <-> JSON untuk API
│   ├── views.py              # endpoint /api/core/me/ (data user login)
│   └── urls.py
│
├── knowledge/                # APP: sumber data untuk RAG chatbot
│   ├── models.py             # KategoriKI, DokumenResmi, ChunkEmbedding, FAQ
│   ├── admin.py / serializers.py / views.py / urls.py
│
├── trademark/                # APP: mirror data PDKI & log cek merek
│   ├── models.py             # MirrorPDKI, CekMerekLog
│   ├── admin.py / serializers.py / views.py / urls.py
│
├── chatbot/                  # APP: log percakapan chatbot
│   ├── models.py             # PercakapanChatbot
│   ├── admin.py / serializers.py / views.py / urls.py
```

**Kenapa strukturnya begini?**
- Folder `sikapki/` HANYA berisi konfigurasi project (settings, routing utama).
  Ini bukan tempat menaruh logic bisnis.
- Setiap "app" (`core`, `knowledge`, `trademark`, `chatbot`) itu modul mandiri
  dengan tanggung jawab jelas — sengaja dipisah per domain, bukan per jenis
  file, supaya kamu gampang cari kode ("mau edit soal merek? buka folder
  `trademark/`, selesai").
- Tiap app polanya SAMA PERSIS: `models.py` (struktur data) → `serializers.py`
  (bentuk JSON untuk API) → `views.py` (logic endpoint) → `urls.py` (alamat
  endpoint) → `admin.py` (biar bisa dikelola lewat Django Admin tanpa bikin
  UI sendiri dulu). Sekali kamu paham pola ini, semua app terasa familiar.

## 2. Setup Awal (jalankan di komputer kamu)

### a. Buat virtual environment
```bash
cd sikapki_backend
python3 -m venv venv

# aktifkan venv
source venv/bin/activate        # Linux/Mac
# atau
venv\Scripts\activate           # Windows
```

### b. Install dependency
```bash
pip install -r requirements.txt
```

### c. Siapkan PostgreSQL
Pastikan PostgreSQL sudah terinstall dan jalan, lalu buat database & user:
```sql
CREATE DATABASE sikapki_db;
CREATE USER sikapki_user WITH PASSWORD 'sikapki_pass';
GRANT ALL PRIVILEGES ON DATABASE sikapki_db TO sikapki_user;
```
(Sesuaikan nama/password sesuai keinginan kamu, lalu cocokkan dengan `.env`.)

### d. Buat file `.env`
```bash
cp .env.example .env
```
Lalu edit `.env` dan isi:
- `SECRET_KEY` — generate dengan:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DATABASE_URL` — sesuaikan dengan user/password/db PostgreSQL kamu, format:
  `postgres://USER:PASSWORD@HOST:PORT/NAME`

### e. Migrasi database
```bash
python manage.py makemigrations core knowledge trademark chatbot
python manage.py migrate
```

### f. Buat akun admin (superuser)
```bash
python manage.py createsuperuser
```

### g. Jalankan server
```bash
python manage.py runserver
```
Buka `http://127.0.0.1:8000/admin/` untuk masuk ke Django Admin, atau
`http://127.0.0.1:8000/api/knowledge/faq/` untuk cek endpoint API.

## 3. Daftar Endpoint API (ringkas)

| App        | Endpoint                                                  | Keterangan                                  |
|------------|-------------------------------------------------------------|-----------------------------------------------|
| core       | `GET /api/core/me/`                                          | Data user yang sedang login                   |
| knowledge  | `/api/knowledge/kategori/`                                    | CRUD kategori KI                              |
| knowledge  | `/api/knowledge/dokumen/`                                      | CRUD dokumen resmi (sumber RAG)               |
| knowledge  | `/api/knowledge/faq/`                                            | CRUD FAQ (sumber RAG), `retrieve` auto-tambah `jumlah_dilihat` |
| trademark  | `/api/trademark/mirror-pdki/`                                    | Data merek (read-only, hasil mirror PDKI)     |
| trademark  | `POST /api/trademark/cek/`                                        | Rekomendasi kelas/istilah Nice; tanpa penilaian kemiripan |
| trademark  | `GET /api/trademark/klasifikasi-merek-log/`                       | Riwayat klasifikasi (khusus petugas)           |
| trademark  | `/api/trademark/mirror-pdki/search/?q=<nama>`                     | Arsip pencarian data mirror (bukan alur publik) |
| trademark  | `GET /api/trademark/cek-merek-log/`                               | Arsip log alur kemiripan versi sebelumnya      |
| chatbot    | `/api/chatbot/percakapan/` (POST)                                  | Ajukan pertanyaan ke chatbot                  |
| chatbot    | `/api/chatbot/percakapan/<id>/beri-rating/` (PATCH)                | Kirim feedback membantu/tidak                 |

Semua endpoint CRUD di atas otomatis mendukung format list + pagination
(20 data per halaman) berkat DRF `DefaultRouter` + `ModelViewSet`.

Catatan: `ChunkEmbedding` (app `knowledge`) sengaja belum diekspos lewat API
publik — model ini akan diisi/dibaca secara internal oleh modul RAG nanti
(bukan lewat CRUD manual dari frontend).

## 4. Data Contoh (Seed Demo Data)

Setelah migrasi berhasil, isi database dengan data contoh supaya bisa
langsung dicoba (termasuk data merek yang sengaja dibuat mirip-mirip untuk
testing fitur similarity check):
```powershell
python manage.py seed_demo_data
```
Command ini idempotent (aman dijalankan berkali-kali, tidak akan
menghasilkan duplikat) dan akan mengisi:
- 4 kategori KI (Merek, Hak Cipta, Paten, Desain Industri)
- 10 dokumen resmi contoh
- 15 FAQ seputar merek
- 20 entri Mirror PDKI (4 klaster nama merek yang saling mirip, 5 varian per klaster)

## 5. Langkah Selanjutnya (di luar scope fondasi ini)

Untuk memperkaya data BRM yang telah tersimpan dengan pemilik dan uraian
barang/jasa, jalankan dari folder backend:

```powershell
.\.venv\Scripts\python.exe manage.py sync_berita_resmi_merek --enrich-details --batch-size 5 --delay 2
```

Mode ini tidak mengekstrak ulang etiket, tidak menghapus detail lama jika
sumber gagal dibaca, dan dapat dijalankan kembali sampai seluruh publikasi
selesai diperkaya.

- Implementasi modul RAG (embedding `knowledge.DokumenResmi` /
  `knowledge.FAQ` ke ChromaDB, simpan `vector_id` hasilnya ke
  `knowledge.ChunkEmbedding`, lalu hubungkan ke
  `chatbot.views.PercakapanChatbotViewSet.perform_create` supaya jawaban
  AI sungguhan tersimpan, bukan placeholder).
- Management command untuk sinkronisasi berkala data asli PDKI ke
  `trademark.MirrorPDKI` (menggantikan/melengkapi `seed_demo_data`).
- Ganti heuristik `skor_risiko` di `trademark.views.CekMerekLogViewSet`
  (saat ini masih hitung jumlah kecocokan nama sederhana) dengan
  similarity search berbasis embedding.
- Autentikasi API yang lebih production-ready (mis. token/JWT) jika frontend
  React tidak memakai session cookie.

## 6. Worker background, retry, dan audit

Jalankan worker terpisah agar proses AI, indexing, dan pengayaan BRM tidak
menahan request web:

```powershell
.\.venv\Scripts\python.exe manage.py process_background_jobs --watch
```

Perintah pendukung:

```powershell
.\.venv\Scripts\python.exe manage.py enqueue_knowledge_indexing --limit 50
.\.venv\Scripts\python.exe manage.py sync_berita_resmi_merek --enrich-details --enqueue --batch-size 20
.\.venv\Scripts\python.exe manage.py notify_overdue_consultations
```

Provider AI dan sumber DJKI memiliki retry dengan backoff. Isi
`AI_FALLBACK_PROVIDER` hanya jika API key provider cadangan tersedia. Perubahan
melalui Django Admin dicatat pada **Audit Log Admin**. Endpoint pencarian mirror
mendukung pagination dan filter `q`, `kelas_nice`, `status`, `sumber_data`,
`ada_uraian`, `ada_nomor`, serta `ada_etiket`.
