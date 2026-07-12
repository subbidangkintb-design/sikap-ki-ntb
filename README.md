# SIKAP-KI NTB

SIKAP-KI NTB adalah MVP layanan Kekayaan Intelektual berbasis AI untuk:

- cek awal risiko nama merek,
- saran alternatif nama/arah pembeda visual berbasis teks,
- chatbot tanya jawab berbasis RAG,
- FAQ layanan KI.

## 1. Prasyarat

Install di mesin lokal:

- Python 3.12
- PostgreSQL
- Node.js + npm
- Ollama

Pastikan Ollama punya model:

```powershell
ollama pull qwen2.5
```

Ollama biasanya berjalan sebagai service. Cek:

```powershell
curl http://127.0.0.1:11434/api/tags
```

Jika belum jalan:

```powershell
ollama serve
```

Kalau muncul error port `11434` sudah dipakai, berarti Ollama sudah berjalan.

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
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:latest
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
```

### Pilihan Provider AI

Default backend memakai Ollama lokal:

```env
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:latest
```

Jika PC terasa berat/ngelag, gunakan Gemini API free tier:

```env
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash-lite
GEMINI_API_KEY=isi_api_key_dari_google_ai_studio
```

Atau gunakan DeepSeek API:

```env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=isi_api_key_dari_deepseek
```

Setelah mengganti provider/model di `.env`, restart Django. Dengan Gemini/DeepSeek, Ollama tidak perlu dijalankan untuk fitur chatbot dan saran merek.

Jalankan migrasi dan seed data:

```powershell
python manage.py migrate
python manage.py seed_demo_data
```

Index ulang dokumen RAG:

```powershell
python manage.py reindex_all_documents
```

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
python manage.py createsuperuser
```

Buka:

```text
http://127.0.0.1:8000/admin/
```

Halaman admin sudah memiliki dashboard ringkas, filter eskalasi chatbot, status embedding dokumen, dan textarea nyaman untuk teks panjang.

Untuk langsung melihat pertanyaan dieskalasi:

```text
http://127.0.0.1:8000/admin/chatbot/percakapanchatbot/?dieskalasi__exact=1
```

## 7. Troubleshooting

Jika CORS error:

- pastikan frontend berjalan di `http://127.0.0.1:5173`,
- pastikan backend `.env` punya `http://127.0.0.1:5173` di `CORS_ALLOWED_ORIGINS`,
- restart Django setelah mengubah `.env`.

Jika Ollama error:

```powershell
curl http://127.0.0.1:11434/api/tags
ollama pull qwen2.5
```

Jika test Django gagal membuat database:

```sql
ALTER USER sikapki_user CREATEDB;
```

Jika Vite gagal karena PowerShell memblokir `npm.ps1`, gunakan:

```powershell
npm.cmd run dev
```
