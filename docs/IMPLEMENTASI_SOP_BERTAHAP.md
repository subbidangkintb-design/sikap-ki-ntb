# Implementasi SOP SIKAP-KI NTB Bertahap

Dokumen ini menjadi peta penerapan aplikasi terhadap **SOP Pengelolaan dan
Penggunaan SIKAP-KI NTB versi 1.0**. Isi SOP adalah standar operasional; kolom
status di bawah menunjukkan implementasi teknis saat ini, bukan pengesahan
administratif SOP.

## Tahap 1 — Alur Cek Kelas dan human oversight

Status: **diterapkan dan diuji**.

- Pengguna mengisi nama merek dan uraian barang/jasa.
- Sistem menampilkan satu atau beberapa rekomendasi kelas, istilah resmi,
  alasan, sumber, dan disclaimer.
- Hasil tidak diposisikan sebagai keputusan resmi atau jaminan pendaftaran.
- Jika pengguna masih ragu, tersedia tombol **Minta bantuan Petugas Helpdesk
  KI**.
- Pengalihan menyimpan uraian, kelas yang dianalisis, dan konteks konsultasi.
- Sistem menghasilkan `kode_konsultasi` dan `pelacakan_id`.
- Status awal otomatis menjadi **Menunggu ditinjau petugas** dan batas waktu
  tindak lanjut mengikuti konfigurasi SLA.
- Pengguna dapat membuka halaman status konsultasi.

Endpoint internal tahap ini:

```text
POST /api/trademark/cek-kelas/eskalasi/
GET  /api/chatbot/status/<pelacakan_id>/
```

## Tahap 2 — Chatbot Helpdesk dan tindak lanjut petugas

Status: **fondasi sudah tersedia; perlu uji operasional petugas**.

Fondasi yang sudah ada: konteks percakapan lanjutan, sumber jawaban, rating,
eskalasi otomatis, status konsultasi, koreksi jawaban, audit admin, worker AI,
retry/fallback, dan notifikasi konsultasi melewati SLA.

Uji berikutnya bersama petugas:

1. Pertanyaan umum dengan sumber aktif.
2. Pertanyaan lanjutan dalam sesi yang sama.
3. Jawaban tanpa sumber memadai.
4. Permintaan bantuan petugas.
5. Perubahan status Menunggu → Diproses → Selesai.
6. Koreksi jawaban dan pencatatan sumber koreksi.

## Tahap 3 — Basis pengetahuan dan klasifikasi

Status: **fondasi teknis tersedia; validasi substansi harus dilakukan petugas**.

- Dokumen/FAQ memiliki status validasi dan status indexing.
- Sumber tidak aktif tidak digunakan chatbot.
- Indexing dapat dijalankan sebagai background job.
- Data klasifikasi dapat diimpor dari berkas lokal SKM DJKI tanpa akses otomatis
  berulang ke situs.
- WIPO dan SKM dapat dipakai sebagai validasi silang, dengan URL sumber dan
  versi tersimpan.

Yang perlu ditetapkan oleh Pengelola Basis Pengetahuan:

- daftar sumber resmi yang disetujui;
- versi dan tanggal efektif klasifikasi;
- pemeriksa substansi dan pemeriksa akhir;
- jadwal peninjauan/pembaruan;
- prosedur penonaktifan sumber yang tidak berlaku.

## Tahap 4 — Akun, keamanan, backup, dan gangguan

Status: **sebagian tersedia; perlu pengesahan konfigurasi operasional**.

Fondasi yang sudah ada: role petugas, audit log admin, pembatasan endpoint,
retry provider, health check, worker stale-job recovery, dan dokumentasi
keamanan.

Sebelum go-live, tetapkan dan uji:

- domain resmi dan HTTPS;
- penanggung jawab setiap role;
- jadwal backup serta uji restore;
- kanal pelaporan gangguan;
- target pemulihan layanan;
- prosedur pergantian kredensial dan penonaktifan akun.

## Tahap 5 — Monitoring dan evaluasi

Status: **dashboard dan metrik fondasi tersedia; format laporan perlu ditetapkan**.

Metrik yang perlu ditinjau secara berkala:

- jumlah pertanyaan dan sesi;
- jawaban berhasil, klarifikasi, dan eskalasi;
- rating membantu/tidak membantu;
- status serta kepatuhan SLA konsultasi;
- penggunaan dan kualitas Cek Kelas Merek;
- status dokumen/FAQ dan kegagalan indexing;
- gangguan teknis, backup, dan pemulihan;
- daftar temuan, rekomendasi, penanggung jawab, dan status tindak lanjut.

## Konfirmasi administratif yang masih diperlukan

SOP memuat beberapa penanda `[PERLU DIKONFIRMASI]`. Aplikasi tidak boleh
menebak nilai tersebut. Sebelum penetapan resmi, lengkapi minimal:

- nomenklatur unit pengelola;
- pejabat penanggung jawab dan pejabat pengesah;
- nomor, tanggal berlaku, dan nomor revisi SOP;
- domain resmi aplikasi;
- target respons awal dan penyelesaian konsultasi;
- kanal alternatif Helpdesk saat aplikasi terganggu;
- periode laporan monitoring dan penerima laporan.
