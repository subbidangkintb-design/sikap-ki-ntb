# Pengujian Aksesibilitas SIKAP-KI NTB

Target awal: WCAG 2.2 Level AA. Jalankan pengujian pada Beranda, Penelusuran
Merek, Chatbot, Checklist, Pusat Informasi, dan Statistik.

## Pemeriksaan otomatis

```powershell
cd sikapki_frontend
npm run lint
npm run build
```

Lint memuat aturan `eslint-plugin-jsx-a11y`. Kelulusan otomatis tidak
menggantikan pengujian pengguna atau pembaca layar.

## Keyboard tanpa mouse

1. Muat ulang halaman lalu tekan `Tab`. Tautan **Lewati ke konten utama**
   harus terlihat dan memindahkan fokus ke konten.
2. Telusuri semua kontrol dengan `Tab` dan `Shift+Tab`. Fokus harus selalu
   tampak, berurutan, dan tidak tertutup header atau tombol mengambang.
3. Buka navbar mobile dan panel aksesibilitas memakai `Enter`/`Space`.
4. Di panel aksesibilitas, fokus harus tetap berada di dalam panel. `Escape`
   harus menutup panel dan mengembalikan fokus ke tombol pemicu.
5. Semua tombol, pilihan kelas, detail, tautan, rating, dan kontrol suara harus
   dapat dioperasikan tanpa mouse.

## NVDA di Windows

1. Jalankan NVDA dan Chrome/Edge, lalu gunakan mode browse.
2. Tekan `H` untuk menelusuri heading. Pastikan hierarki halaman masuk akal.
3. Tekan `F` untuk field formulir dan pastikan label, bantuan, status wajib,
   serta pesan kesalahan terbaca.
4. Kirim formulir kosong. Jumlah kesalahan harus diumumkan dan fokus berpindah
   ke field pertama yang salah.
5. Kirim pertanyaan chatbot. Status pemrosesan dan jawaban baru harus
   diumumkan sekali, tanpa membaca ulang seluruh percakapan.
6. Jalankan penelusuran merek. Loading, error, klarifikasi, atau hasil harus
   diumumkan dan fokus berpindah ke wilayah hasil.
7. Pada tabel desktop gunakan navigasi tabel NVDA; header kolom harus dibaca
   bersama setiap sel.

## Visual dan pembesaran

1. Uji zoom browser 200% dan 400% pada lebar 1280 px.
2. Uji viewport 320 px tanpa scroll horizontal halaman.
3. Aktifkan ukuran teks Besar dan Sangat besar; konten dan kontrol tidak boleh
   terpotong atau saling menimpa.
4. Aktifkan kontras tinggi; teks, border, fokus, dan status tetap terbaca.
5. Aktifkan Kurangi animasi dan preferensi sistem `prefers-reduced-motion`;
   spinner boleh tetap memberi status tekstual tanpa gerakan yang berarti.

## Text-to-speech

1. Pilih **Bacakan jawaban**, lalu uji Jeda, Lanjutkan, dan Berhenti.
2. Ubah kecepatan Lambat, Normal, dan Cepat.
3. Memulai jawaban lain harus menghentikan pembacaan sebelumnya.
4. Berpindah halaman harus menghentikan pembacaan aktif.

Catat browser, versi NVDA, halaman, langkah reproduksi, hasil aktual, hasil
yang diharapkan, dan tingkat dampak untuk setiap temuan.
