# Alur kerja APK target baru

1. **Penerimaan baseline.** Simpan APK asli di `inputs/`. Jalankan inventaris,
   catat SHA-256, identitas package/version melalui pemeriksa manifest Android,
   ABI, library dan arsip resource. Tool inventaris awal hanya mengidentifikasi
   kandidat struktur; ia belum menyatakan APK kompatibel.
2. **Pengenalan format.** Cocokkan target dengan kajian acuan. Tentukan profil
   berdasarkan hash dan struktur yang terbukti. Jangan menyalin alamat patch
   atau batas buffer dari versi lain tanpa verifikasi.
3. **Repack baseline.** Buktikan parser dan compiler mampu menghasilkan kembali
   byte asli tanpa perubahan. Tolak file terpotong, struktur tidak dikenal,
   path ekstraksi keluar workspace dan indeks yang tidak sesuai.
4. **Katalog baru.** Ekstrak teks dari APK target. Simpan file, konteks, source,
   slot target dan batas field yang terverifikasi. Pindahkan translation memory
   dari acuan hanya setelah teks sumber dan konteks cocok.
5. **Terjemahan dan UI.** Jaga placeholder, kode warna dan pemisah baris.
   Uji encoding, kapasitas buffer, lebar/tinggi panel dan font target. Gunakan
   override untuk teks identik dengan konteks berbeda. Jangan memotong makna
   secara otomatis agar lolos batas.
6. **Build terisolasi.** Gunakan baseline dan overlay untuk menghasilkan output
   baru. Jangan menimpa input. Build pipeline nyata ditambahkan setelah format
   target terverifikasi; workspace awal belum menyediakan build game.
7. **Verifikasi cakupan.** Bandingkan metadata, bytecode, save, library, audio
   dan konfigurasi input dengan baseline. Setiap perubahan di luar terjemahan
   dicatat dan diuji sesuai tujuan.
8. **Pengujian akhir.** Periksa signature, signer, alignment ELF dan ZIP 16 KB
   sesuai ABI target. Uji instalasi/update, pembaruan assets, kelanjutan save,
   dialog/menu, input dan gameplay di perangkat. Simpan hasil serta batas uji.

Terjemahan pada APK yang sudah berfungsi sebaiknya mempertahankan runtime APK
tersebut lebih dahulu. Port runner ARM64, perluasan viewport, pengaturan input
atau perubahan gameplay adalah pekerjaan terpisah sesuai kebutuhan target.

File inventaris lengkap tetap di `work/` agar nama input, path lokal dan rincian
binary tidak otomatis ikut ke source publik. Laporan publik dibuat sebagai
ringkasan yang telah diperiksa.
