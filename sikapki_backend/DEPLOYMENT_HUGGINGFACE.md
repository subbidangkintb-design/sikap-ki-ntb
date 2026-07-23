# Deployment backend ke Hugging Face Spaces

Gunakan **Docker Space** dengan port aplikasi `7860`. Jadikan isi folder
`sikapki_backend` sebagai root repository Space agar `Dockerfile` terdeteksi.

## Secrets

Masukkan nilai berikut melalui **Space Settings > Variables and secrets**.
Jangan menyalin file `.env` ke repository.

- `SECRET_KEY`: secret acak Django.
- `DATABASE_URL`: connection string PostgreSQL Supabase dengan
  `?sslmode=require` bila belum tercantum.
- `GEMINI_API_KEY`: API key Gemini.

## Variables production

```env
DEBUG=False
SERVE_STATIC_FILES=False
ALLOWED_HOSTS=<nama-space>.hf.space
CORS_ALLOWED_ORIGINS=https://<nama-project>.vercel.app
AI_PROVIDER=gemini
AI_MODEL=gemini-3.1-flash-lite
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
```

Naikkan `SECURE_HSTS_SECONDS` menjadi `31536000` hanya setelah HTTPS dan
domain stabil. Jangan aktifkan `INCLUDE_SUBDOMAINS` atau `PRELOAD` pada domain
bersama `hf.space`, karena subdomain lain tidak berada dalam kendali aplikasi.

## Proses startup

Container secara otomatis menjalankan:

1. `python manage.py migrate --noinput`;
2. `python manage.py collectstatic --noinput`;
3. Gunicorn pada `0.0.0.0:7860`.

Periksa kesiapan melalui `GET /healthz`. Respons `200` berarti database dapat
diakses. Respons `503` berarti koneksi atau pemeriksaan database gagal.

Setelah URL Vercel diketahui, perbarui `CORS_ALLOWED_ORIGINS`. Untuk preview
Vercel yang domainnya berubah-ubah, daftarkan hanya domain preview yang sedang
dipakai atau gunakan domain production tetap.
