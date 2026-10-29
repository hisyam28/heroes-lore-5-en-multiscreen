# Adaptasi runner Android ARM32/ARM64

APK target 01.01.00 telah diperiksa secara statis. Build lokal pertama memakai
runner ARM64 dari ZIP acuan dengan overlay khusus target. Engine asli tetap
dieksekusi sebagai ARM32 melalui Unicorn; ini bukan kompilasi ulang engine ke ARM64.

## Cakupan

- Host `arm64-v8a` dan, mulai test8, `armeabi-v7a`; varian test8 minimum
  Android 8.0/API26. Test9 menambahkan engine native asli pada API9–20 dan host
  modern API21+; lihat [kompatibilitas Android lama](test9-legacy-android.md).
  Target SDK tetap36. ARM32 belum diuji di ponsel fisik.
- Sasaran uji utama yang diberikan pengguna: Android 16, MediaTek Dimensity 9400+;
  model ponsel dan ukuran halaman memori belum diketahui.
- Guest SO, VFS Korea, dan `mtouchdevice.txt` diambil dari APK target tanpa perubahan byte.
- Tidak ada transfer katalog Inggris, patch font, atau perubahan save format.
- Test5 memasok lebar logis dinamis ke engine target; validasi kamera/HUD pada perangkat masih menunggu.
- Test6 menutup seluruh tepi, menghapus padding cutout dan mempercepat salin framebuffer
  opaque yang terverifikasi. [Catatan test6](test6-fullscreen-performance.md) memisahkan bukti model dari hasil perangkat.
- Test7 menambah raster native terverifikasi untuk intro, menu dan sprite; lihat
  [hasil per adegan](test7-raster-performance.md). Terjemahan tetap ditunda sampai performa diterima.
- Test8 memperbaiki penggunaan ulang heap, persiapan aset dan startup, serta
  menambah host ARM32. Lihat [bukti dan batas test8](test8-stability-startup.md).
- Test9 menjaga resource asli dan memisahkan kode Dalvik/API9 dari runner ART
  modern. Signature v1/v2/v3 dan dua jalur runtime telah diperiksa secara statis.
- Package runner `co.kr.eamobile.hl5.runner` berbeda dari APK asli. Kunci uji lokal
  juga berbeda; build ini bukan update bertanda tangan untuk aplikasi asli.
  Save aplikasi asli tidak otomatis dipindahkan ke sandbox runner.
- x86/x86_64 belum dicakup build ini.

## Perubahan dari acuan

Pointer global `gv` dan vtable dicari melalui symbol ELF. Offset pointer state
target adalah `0x244`, bukan `0x27c`; flag jalur lokal adalah `0x8d`, bukan `0x8e`.
Profil mencatat fingerprint APK, library, fungsi dan bukti instruksi. Tool menolak
profil dengan fingerprint, symbol, hash fungsi atau offset yang tidak cocok.

Runner memakai jalur lokal tanpa layanan operator lama: respons SMS kosong
diisi penolakan `N`, dan jalur penyimpanan lokal dipilih melalui field target
yang diverifikasi. Perubahan ini dilakukan pada memori guest saat berjalan,
terpisah dari resource teks dan tanpa menambal library input.

Pemaksaan opsi fixed D-pad dan penulisan field joystick versi acuan dihapus.
Event sentuh asli tetap diteruskan; panggilan guest yang mungkin memakai grafis
dijadwalkan pada GL thread. Callback pause/resume grafis juga dipindahkan ke
GL thread dan konteks EGL dipertahankan saat pause jika perangkat mengizinkan.
Insets layar/cutout ditangani oleh wrapper.

SO/VFS tersalin ke penyimpanan internal menggunakan verifikasi SHA-256 dan
penggantian atomik. Pembaruan hanya menyentuh dua file runtime tersebut.
Save dan file lain tidak dihapus. Trace save memakai entry symbol, tanpa
delta instruksi milik versi acuan. Loader membedakan import dari entry point
guest dan menangani relokasi ARM ABS32. Batas heap dan timeout diperiksa;
timeout tidak boleh dilaporkan sebagai fungsi yang berhasil selesai.

Host dibangun dengan alignment ELF 16 KB, kemudian APK di-zipalign 16 KB dan
ditandatangani lokal. Pengalokasian halaman native wrapper mengikuti ukuran
halaman host. Alignment ini belum membuktikan Unicorn/JIT berjalan pada perangkat
16 KB; pengujian runtime tetap diperlukan.

## Membuat ulang

Sediakan ZIP acuan asli secara lokal, Android NDK r28c, JDK 17, Android SDK
Build Tools 36.0.0 dan platform Android 36. Detail lokasi tool lokal tidak
disimpan dalam konfigurasi publik. Jangan memakai APK hasil modifikasi sebagai input.
Build dependency ARM32 terlebih dahulu sesuai [petunjuk test8](test8-stability-startup.md).

```powershell
python -B tools/prepare_android_runner.py --reference <zip-acuan> --out work/runner-target
python -B tools/build_android_test.py --ndk <ndk> --jdk <jdk> --build-tools <build-tools> --android-jar <android.jar>
python -B tools/check_workspace.py
python -B -m unittest discover -s tests -v
```

Direktori staging harus baru. Untuk percobaan berikutnya gunakan `--out` baru dan
berikan `--runner <staging>/app/src/main` ke builder. Builder memeriksa manifest
hash staging, membuat direktori kompilasi baru dan memverifikasi aset APK akhir
terhadap baseline. Input, dependency binary, kunci, build dan laporan rinci tetap lokal.

## Bukti dan batas uji

- **Statis/build:** identitas target dibaca dengan Android SDK `aapt2`; hash
  baseline, symbol/fungsi, field runtime, aset akhir, signature dan alignment
  diperiksa. Laporan build lengkap berada di `work/android-build-report.json`.
- **Simulasi:** engine dan VFS target mencapai menu utama, lalu masuk state
  permainan baru. Model awal menjalankan enam tick loop. Ekstraksi framebuffer yang
  diperbaiki menunjukkan layar loading; angka lama 84 warna ditarik sebagai bukti
  rendering karena berasal dari wilayah descriptor. New game dipanggil melalui metode game yang diekspor. JNI/libc/GLES
  dimodelkan dengan sejumlah stub Python; ini bukan eksekusi APK Android hasil build.
  Setelah hook memmove ditambahkan, model 400x240 dan 520x240 melewati 80 tick awal
  dan memperlihatkan intro bertanda Skip. Pengujian map, gameplay dan kamera belum selesai.
  Bukti lokal berada di `work/target-simulation-report.json`.
- **Perangkat:** setelah crash test1, layar hitam test2 dan penolakan ELF test3,
  pengguna mengirim video, screenshot gameplay/cutscene dan telemetry test4 pada
  Android 16/Dimensity 9400+. Ini membuktikan render dan pengiriman sentuhan,
  termasuk DrawArrays 3840 dan Touch Rx/Tx 1653/1653. Pengguna melaporkan rasio
  tetap 5:3, overlay mengganggu, Exit tidak menutup dan kembali dari Home mengulang
  menu. Pengguna kemudian mengonfirmasi test5 lebih lebar, tetapi masih menyisakan
  tepi kosong dan sangat lambat pada Galaxy A24/Helio G99 dengan Android 16.
  Pengguna kemudian mengonfirmasi test6 dan test7 meningkatkan performa, tetapi
  test7 masih putih 2–4 detik saat dibuka dan bisa force close saat keluar-masuk
  portal cepat pada kedua ponsel. Test8 belum diuji fisik. Tidak ada perangkat
  terhubung ke workspace; audio, FPS dan persistensi save belum diverifikasi.

Runner acuan sampai test7 memakai allocator linear dengan `free` no-op. Test8
menggantinya dengan allocator yang memakai ulang dan menggabungkan blok bebas.
Sejumlah import tetap berupa stub; sesi panjang, portal, input dan save perlu
diuji pada perangkat. Tidak ada klaim dukungan semua versi Android atau semua smartphone.

Instal `dist/hl5-01.01.00-test10-install.apk` sebagai update runner test8.
Test9 ditolak pengguna; [test10 memperbaiki kompresi resource table](test10-install-packaging.md).
Package dan penandatangan tetap sama; penghapusan aplikasi tidak diperlukan.
Bandingkan map pada posisi karakter yang sama, coba semua tombol terutama sisi
kanan, tekan Home lalu kembali melalui Recents, dan pilih Exit dari menu game.
Petunjuk diagnostik opsional dan batas pemulihan ada di [catatan test5](test5-wide-lifecycle.md).
Perubahan fullscreen, profil beban dan pengurangan ukuran ada di [catatan test6](test6-fullscreen-performance.md).

Panduan platform: [dukungan 16 KB](https://developer.android.com/guide/practices/page-sizes)
dan [perubahan Android 16](https://developer.android.com/about/versions/16/behavior-changes-16).
