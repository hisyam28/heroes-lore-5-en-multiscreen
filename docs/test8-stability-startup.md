# Test8: memori, startup dan dua ABI

Pengguna mengonfirmasi performa test7 meningkat pada Dimensity 9400+ dan Galaxy
A24/Helio G99, keduanya Android 16. Masalah berikutnya ialah layar putih 2–4 detik
saat membuka aplikasi dan force close setelah keluar-masuk **map/portal** dengan
cepat. Tidak ada stack trace untuk force close portal yang tersedia. Terjemahan
tetap ditunda sampai performa dan kestabilan diterima pengguna.

## Perbaikan runtime

Allocator runner sebelumnya hanya menaikkan pointer di heap guest 16 MiB;
`free` tidak melakukan apa pun. Dengan demikian, pelepasan resource oleh game
tidak mengembalikan ruang untuk lokasi berikutnya. Ini adalah cacat konkret yang
konsisten dengan gejala perpindahan berulang, tetapi belum membuktikan seluruh
penyebab crash di perangkat.

Test8 menggunakan allocator dengan metadata di host: blok bebas digabung dan
digunakan kembali, pencarian alokasi dilanjutkan dari cursor terakhir, dan
`realloc` mempertahankan data lama. Batas heap dan alamat guest tidak berubah.
`calloc` memeriksa perkalian 64-bit sebelum mengalokasikan. Pointer tidak sah
atau double free menjadi kesalahan runtime yang tercatat.

Exception dari callback host ditangkap sebelum keluar ke kode JIT Unicorn.
Emulasi dihentikan lalu kesalahan diteruskan dari batas C++ yang biasa, sehingga
exception tidak perlu melintasi stack JIT. Ini tidak menjanjikan pemulihan dari
semua sinyal native, kerusakan memori atau kegagalan driver. Salinan JNI
`GetStringUTFChars` kini memiliki kepemilikan sendiri dan dilepas oleh
`ReleaseStringUTFChars`, tanpa membebaskan sumber string game.

Cache translasi JIT dibatasi 64 MiB pada host 64-bit dan 32 MiB pada host 32-bit,
sebelum pemetaan guest. Jalur raster native test7 dan fallback engine target
tetap dipakai; tidak ada percepatan dengan melewati scene atau mengubah tick game.

## Pembukaan aplikasi

Theme Android dan jendela awal berlatar hitam. Activity langsung menampilkan
“Memuat game…” dan menyiapkan aset melalui thread background, kemudian membuat
renderer setelah Activity resumed. Jika persiapan selesai ketika aplikasi
dipause, renderer menunggu resume; completion juga memeriksa finish/destroy.

SO/VFS tetap diperiksa SHA-256 pada pemasangan pertama atau ketika cache berubah,
dan penggantian file memakai `AtomicFile`. Pada pembukaan berikutnya, fingerprint
yang diharapkan, panjang file dan waktu modifikasi yang sama memakai stamp
verifikasi di penyimpanan privat; isi 17 MB tidak di-hash ulang setiap kali.
Ini adalah cache berdasarkan metadata, bukan pemeriksaan kriptografi ulang jika
isi sengaja diubah sambil mempertahankan metadata. Save tidak dihapus.

Perubahan ini menghilangkan sumber latar putih di wrapper dan pekerjaan hashing
berulang. Durasi boot engine, splash OEM dan startup sebenarnya masih perlu
diukur pada ponsel; belum ada bukti waktu pembukaan test8.

## Layar dan ABI

Lebar/tinggi canvas logis dipilih dari rasio surface pertama: layar lebar
memperluas lebar dari dasar 400×240, sedangkan rasio lebih sempit dapat memperluas
tinggi. Contoh 2620×1280 menjadi 492×240, 2340×1080 menjadi 520×240, dan 1024×768
menjadi 400×300. Skala seragam menutup keempat tepi dan input mengikuti viewport.
Pembulatan dapat membuat overscan beberapa piksel.

Orientasi `sensorLandscape` mengizinkan kedua arah landscape. Canvas dipertahankan
sepanjang sesi agar buffer game aktif tidak diubah ukurannya secara mendadak.
Perubahan ukuran jendela di tengah sesi memakai viewport cover dan dapat
memotong sebagian area; UI portrait, lipatan dan semua HUD belum diuji fisik.
Hasil aritmetika untuk banyak resolusi bukan bukti bahwa setiap adegan game
mendukung semua rasio tanpa masalah.

APK menyertakan host `arm64-v8a` dan `armeabi-v7a`, minimum Android 8/API 26,
target SDK 36. Keduanya tetap menjalankan engine ARM32 target melalui Unicorn.
Nama library historis `libhl5_arm64_bridge.so` dipertahankan pada kedua direktori
ABI, tetapi header ELF masing-masing benar-benar AArch64/64-bit dan ARM/32-bit.
Tidak ada klaim dukungan x86, Android di bawah 8 atau semua smartphone.

Dependency ARM32 dibuat dari source resmi Unicorn 2.1.2, dengan SHA ZIP dipin di
tool dan hash library dipin di profil. Perubahan source dependency hanya mengganti
pembuatan alias `.o` melalui symlink dengan salinan identik agar build Windows
tidak membutuhkan hak symlink. Gunakan NDK lengkap, CMake, Ninja dan Git for
Windows yang menyediakan `sh.exe`, `false.exe` serta utilitas POSIX:

```powershell
python -B tools/build_arm32_dependency.py --ndk <ndk-r28c> --cmake <cmake.exe> --ninja <ninja.exe> --shell-directory <git-usr-bin> --record-profile
python -B tools/prepare_android_runner.py --reference <zip-acuan> --out work/runner-baru
python -B tools/build_android_test.py --runner work/runner-baru/app/src/main --ndk <ndk-r28c> --jdk <jdk17> --build-tools <build-tools36> --android-jar <android36.jar>
```

`--record-profile` hanya untuk hasil dependency lokal yang telah ditinjau; hash
input APK dan guest tidak diganti. Staging harus baru. Dependency dibangun dengan
perintah konfigurasi yang sama pada sesi ini; wrapper reproduksi belum dijalankan
dari lingkungan kosong. Tool menolak ZIP sumber yang hash-nya tidak cocok.

## Bukti dan batas

- **Statis/build:** kedua ABI berhasil dikompilasi dan dipaketkan; delapan export
  JNI per ABI, alignment ELF/ZIP 16 KB dan signature diperiksa. Guest SO, VFS dan
  konfigurasi touch identik dengan baseline. APK 20.296.816 byte; tambahan terhadap
  test7 terutama library host ARM32. Laporan: `work/android-build-report.json`.
- **Regresi/model:** 50 tes lolos pada staging test8 aktif. Allocator C++ sebenarnya dijalankan sebagai kode ARM32,
  termasuk 600 alokasi/pelepasan berukuran 1 MiB, churn acak, alignment, coalescing,
  overflow, resize dan perlindungan alokasi yang masih hidup. Model JVM memeriksa
  invalidasi cache dan urutan startup asynchronous. Aritmetika cover diuji pada
  11 resolusi ponsel/tablet termasuk layar persegi. Tes raster diferensial test7
  tetap dijalankan terhadap instruksi engine asli.
- **Model engine target:** menu dan state game baru tercapai menggunakan SO/VFS
  asli serta allocator C++ yang dikompilasi. Setelah 200 siklus resource buatan
  dan 25 pasangan callback pause/resume asli, heap kembali ke 2.479.544 byte,
  puncak 3.528.120 byte; metadata serta pointer/state game tetap valid. Ini memakai
  JNI/libc/GLES model Python, bukan runner Android terkompilasi, dan **bukan tes
  melintasi portal sebenarnya**. Laporan: `work/test8-heap-model-report.json`.
- **Perangkat:** test8 belum dijalankan pada ponsel yang terhubung ke workspace.
  ARM32, FPS, audio, save, startup dan stabilitas portal masih memerlukan tes fisik.
  Alignment statis juga belum membuktikan runtime JIT pada perangkat halaman 16 KB.

Hasil: `dist/hl5-01.01.00-test8-stability.apk`, SHA-256
`771bdf92dac23f763f6cef48009fc5e24d6c866ac4bc5bc71cd092bfa954a31d`.
Pasang sebagai update runner test7 dengan signer lokal yang sama agar data runner
tetap tersimpan. Bandingkan waktu membuka ulang aplikasi dan scene yang sama,
lalu ulangi perpindahan portal yang sebelumnya memicu crash. Jika masih gagal,
stack trace/logcat dari percobaan itu diperlukan untuk membedakan heap, import
guest, renderer dan driver. Jangan menyatakan semua crash selesai dari model ini.
