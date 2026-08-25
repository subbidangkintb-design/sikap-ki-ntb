# Operasional, Keamanan, dan Keberlanjutan SIKAP-KI NTB

## Pembagian peran

- Super Admin: akun, konfigurasi, pemulihan, dan persetujuan perubahan produksi.
- Verifikator: validasi dokumen resmi dan pemeriksaan kualitas basis pengetahuan.
- Petugas KI: menangani eskalasi, koreksi jawaban, dan monitoring layanan.

Gunakan akun individual, kata sandi unik, dan nonaktifkan akun petugas yang berpindah tugas. Jangan membagikan akun admin.

## Pemeriksaan rutin

Harian:

- buka Dashboard Petugas dan selesaikan antrean yang melewati SLA;
- periksa dokumen gagal diproses dan sinkronisasi yang gagal;
- buka `/api/core/health/` dan pastikan status sehat.

Mingguan:

- buat snapshot monitoring dari Admin atau jalankan `python manage.py create_monitoring_snapshot --days 7`;
- tinjau koreksi jawaban dan tambahkan sumber resmi yang kurang;
- jalankan sinkronisasi BRM secara bertahap dan beretika.
- jalankan `python manage.py sync_faq_djki --delay 1` untuk FAQ DJKI. Jika
  proteksi situs menolak request otomatis, jangan mencoba melewatinya; simpan
  halaman resmi melalui browser lalu impor dengan
  `python manage.py sync_faq_djki --html-file halaman.html --url URL_RESMI --subcategory "Nama kategori"`.
- buka Admin > FAQ, tinjau perubahan berstatus draf, lalu gunakan aksi
  **Verifikasi dan antrekan FAQ terpilih untuk indexing**. Jalankan
  `python manage.py process_document_queue --limit 100` setelah verifikasi.

Bulanan:

- uji pemulihan backup pada lingkungan terpisah;
- tinjau akun, pembatasan trafik, kapasitas disk, dan masa retensi;
- jalankan `python manage.py purge_expired_service_data --dry-run`, periksa hasil, lalu jalankan tanpa `--dry-run` setelah disetujui.

## Backup dan pemulihan PostgreSQL

Backup basis data:

```powershell
pg_dump --format=custom --file=sikapki_YYYYMMDD.dump sikapki_db
```

Backup juga folder `media/` dan file konfigurasi environment melalui penyimpanan terenkripsi. Jangan memasukkan `.env` ke Git. Simpan minimal tiga generasi backup dengan satu salinan di lokasi berbeda.

Uji pemulihan pada database kosong:

```powershell
createdb sikapki_restore_test
pg_restore --dbname=sikapki_restore_test --clean --if-exists sikapki_YYYYMMDD.dump
```

Catat tanggal, petugas, ukuran backup, checksum, dan hasil uji restore. Backup belum dapat dianggap berhasil sebelum pernah dipulihkan.

## Deployment aman

Mode localhost saat ini sengaja tidak memakai HTTPS. Untuk deployment publik gunakan reverse proxy TLS, kemudian set `DEBUG=False`, host/origin yang spesifik, dan aktifkan `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, serta `CSRF_COOKIE_SECURE`. Simpan secret dan API key pada secret manager atau environment server.

API chatbot, klasifikasi merek, dan uji pengguna sudah memiliki rate limit.
Logo pada asisten klasifikasi hanya menjadi pratinjau lokal: tidak dikirim,
disimpan, atau dinilai AI. Health check hanya menampilkan status konfigurasi,
tidak pernah nilai API key.

Mode opsional `AI_TRADEMARK_CHECK_ENABLED=True` mengirim logo sementara ke
backend untuk membuat embedding dan membandingkannya dengan referensi lokal;
file pengguna tidak disimpan. Aktifkan hanya bila cakupan, sumber, dan usia data
pembanding telah ditinjau petugas. Setelah mengubah mode, restart backend dan
uji kembali tautan verifikasi PDKI serta disclaimer hasil.

## Respons insiden

Jika terjadi dugaan kebocoran, penyalahgunaan, atau jawaban berisiko: hentikan akses publik bila perlu, simpan log relevan, ganti credential terdampak, laporkan kepada penanggung jawab, perbaiki akar masalah, lalu dokumentasikan waktu dan tindakan pemulihan. Jangan menghapus bukti sebelum evaluasi selesai.

## Prinsip keberlanjutan

Basis pengetahuan hanya memakai sumber terverifikasi. AI adalah teknologi pendukung, sedangkan keputusan dan konsultasi kompleks tetap ditangani petugas. Setiap perubahan model, prompt, data, atau aturan klasifikasi harus diuji ulang menggunakan skenario pada protokol uji pengguna dan dicatat dalam riwayat rilis.

FAQ hasil sinkronisasi menyimpan URL sumber, hash konten, subkategori, dan waktu
sinkronisasi. Perubahan pada jawaban sumber otomatis mengembalikan FAQ menjadi
draf dan mencabut indeks lamanya. Jika FAQ bertentangan dengan peraturan resmi
yang lebih baru, dokumen peraturan terverifikasi harus diutamakan.
