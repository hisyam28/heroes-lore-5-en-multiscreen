# Test6: fullscreen dan pengurangan beban emulasi

Pengguna mengonfirmasi test5 mulai memperlebar pandangan. Screenshot masih
menunjukkan strip abu-abu/kosong di tepi; Galaxy A24/Helio G99 juga mengalami lag
berat. Kedua perangkat uji memakai Android 16. Pengguna menyatakan game dahulu
lancar sebelum pembaruan Android; ketersediaan proses ARM32 pada firmware kini
belum diperiksa. Tidak ada perangkat ADB terhubung ke workspace.

## Jendela dan viewport

Test5 memasang padding systemBars/displayCutout pada seluruh layout game.
Test6 menghapus padding itu, mengatur decorFitsSystemWindows=false pada API 30+,
serta cutout ALWAYS pada API 30+ atau SHORT_EDGES pada API 28–29. Latar jendela
game berwarna hitam dan fullscreen diatur sebelum surface dibuat. Implementasi
mengikuti [panduan cutout Android](https://developer.android.com/develop/ui/views/layout/display-cutout).

Lebar canvas tetap berasal dari aspek layar dan tinggi logis 240. Viewport kini
memakai skala seragam yang menutup seluruh surface. Pembulatan genap lebar logis
dapat menyebabkan overscan tipis, bukan letterbox. Pada 2620x1280, canvas 492x240
memakai viewport 2624x1280 dengan x=-2: dua pixel fisik terpotong pada masing-masing
sisi, tanpa perubahan proporsi sprite. Pemetaan sentuhan memakai viewport yang sama.
Saat aspek surface berubah jauh di tengah sesi, canvas sesi dipertahankan dan
viewport menutup surface dengan crop yang sesuai; sesi baru menghitung canvas baru.
Area fisik kamera dan sudut panel yang tidak memiliki pixel tetap tidak bisa digambar.

## Hotspot yang diukur dan akselerasi

Profil blok pada model engine target, tiga tick adegan map/dialog yang sama:

| Pengukuran model | Sebelum | Sesudah |
|---|---:|---:|
| Estimasi instruksi ARM guest | 33.665.646 | 4.950.402 |
| Instruksi fungsi copy framebuffer | 28.715.724 | Digantikan jalur host pada kasus yang cocok |
| Framebuffer pada tick 300 | Acuan | Identik seluruh pixel |

Fungsi `_Z26internalGrpCopyFrameBufferiiiiiiiiP14_MC_GrpContexth` menyumbang sekitar
85% instruksi sampel. Runner menangkap entry fungsi yang dicocokkan berdasarkan
symbol dan SHA-256 target, kemudian menjalankan salin baris melalui host pada
kasus opaque 16/32 bit dengan format sama, clipping valid dan buffer terpisah.
Alpha blending, transparansi, pixel operator, koordinat negatif, buffer overlap
dan format/batas yang tidak didukung kembali ke instruksi guest asli.

Layout framebuffer 20 byte dan context 64 byte diperiksa terhadap DWARF serta
instruksi binary target. Tidak ada struktur acuan yang diasumsikan cocok.
Uji diferensial menjalankan fungsi ARM asli dan rencana native terkompilasi pada
48 kombinasi buffer, stride, format dan clipping. Hasil tujuan termasuk padding
cocok persis. Model 300 tick berikutnya memakai rencana C++ terkompilasi melalui
hook Python: 1077 copy dipercepat, tidak ada fallback dalam sampel, dan framebuffer
akhir identik dengan model tanpa optimasi.

Angka instruksi ini tidak menghitung biaya host copy dan bukan FPS ponsel.
Model JNI/libc/GLES memiliki stub dan tidak menjalankan APK Android hasil build.
Performa A24 serta adegan/map lain tetap perlu diuji pada perangkat.

Upload tekstur juga diperbaiki: RGB565 disalin dua byte per pixel, bukan asumsi
empat byte; row alignment GLES tetap dijaga. Buffer upload dipakai ulang,
glGetError per draw/upload hanya aktif pada diagnostik, status JNI tidak lagi
dibuat setiap frame normal, trace save guest bersifat opt-in, dan pembacaan
register trampoline memakai batch. Timer/game speed tidak diubah atau dipaksa.

## Ukuran APK dan batas kompatibilitas

| Komponen | Test5 | Test6 |
|---|---:|---:|
| Seluruh APK | 33.821.724 byte | 19.084.316 byte |
| Host ARM64 terkemas | 15.414.368 byte | 1.710.704 byte |

Library sebelumnya membawa hampir 12 MB section debug. Test6 menyimpan binary
host lengkap untuk diagnosis di direktori build lokal dan mengemas salinan yang
telah di-strip. Symbol internal disembunyikan, kode tak terpakai dibuang, dan
entry JNI tetap diekspor. Guest SO dikompresi di dalam ZIP, tetapi byte hasil
ekstraksinya tetap identik. VFS tetap tersimpan tanpa kompresi untuk akses audio.
Guest SO, VFS dan mtouchdevice tidak berubah; tidak ada pengurangan aset atau
perubahan format save. APK asli juga tidak diubah.

Build tetap mengeksekusi ARM32 melalui runner ARM64. Ini memerlukan biaya lebih
besar daripada eksekusi ARM32 langsung; usia game atau ukuran file tidak
menentukan biaya emulasi. Dukungan eksekusi langsung pada firmware A24 belum
dibuktikan. Tidak ada klaim lancar pada semua perangkat.

## Validasi dan pemasangan

34 tes otomatis lolos, termasuk fullscreen model API 26/28/29/30/36, viewport
menutup empat tepi, proporsi, touch, RGB565, copy diferensial dan regresi sebelumnya.
Signature v2/v3, signer yang sama dan alignment ELF/ZIP 16 KB diverifikasi.
Hasil uji perangkat test6 masih menunggu; kelanjutan Exit/Home test5 belum dilaporkan.

Instal `dist/hl5-01.01.00-arm64-test6-fullscreen.apk` sebagai update test5 tanpa
uninstall. Uji kedua perangkat: periksa empat tepi, input dekat tepi, map/dialog,
performa bergerak/bertarung, Home/Recents dan Exit. Diagnostik opsional memakai
intent `--ez debug true` sebagaimana [catatan test5](test5-wide-lifecycle.md).
Laporan lokal berada di `work/target-frame-profile.json`,
`work/fast-copy-model-report.json` dan `work/android-build-report.json`.
