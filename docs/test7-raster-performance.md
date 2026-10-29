# Test7: performa intro, menu dan adegan

Pengguna mengonfirmasi test6 meningkatkan performa Galaxy A24/Helio G99 pada
Android 16, tetapi intro, home/menu dan adegan masih lag. Terjemahan ditunda
secara eksplisit sampai performa diterima. Test7 hanya mengubah wrapper runtime;
engine ARM32, VFS Korea, touch asset, timer/game speed dan format save dipertahankan.

## Hotspot dan jalur native

Profil terpisah diperlukan karena sampel map pada test6 tidak mewakili intro
atau menu. Intro didominasi ChangeFrameBufferBlending565, sedangkan menu memiliki
biaya besar pada MC_grpFillRect dan FillRectBlending. Test7 menambah lima jalur:

- FillRectAlpha RGB565, mempertahankan pembulatan /256 dan inverse 255-alpha.
- Sprite indexed 4/8 bit untuk rectangle yang seluruhnya berada di clip, termasuk
  mirror X/Y, anchor dan SKIP_COLOR dinamis. Edge clipping tetap di fungsi asli.
- Efek warna seluruh framebuffer berdasarkan tabel lookup asli milik Graphic.
- Efek warna rectangle berdasarkan tabel yang sama, termasuk threshold alpha 248
  dan kuantisasi alpha/green asli.
- MC_grpFillRect opaque RGB565 dengan normalisasi ukuran negatif, batas framebuffer
  dan clip context. Alpha atau pixel operator kembali ke fungsi asli.

Symbol dan hash fungsi target diperiksa sebelum staging. Layout dibuktikan dari
instruksi target: Graphic RGB type +0x5c, clip +0x40e0..+0x40ec, tabel lookup
+0x6d+mode*1024; GbmImage type/width/height/palette/pixels +0/+2/+4/+8/+12.
FrameBufferInfo menghitung bytes per pixel melalui stride/width; fast path
memvalidasi syarat tersebut. Mode/format di luar cakupan tidak dipaksakan.

Native membaca sumber sebelum commit. Jika commit gagal setelah sebagian hasil
ditulis, eksekusi dihentikan agar alpha tidak diterapkan dua kali melalui fallback.
Buffer kerja dipakai ulang dan ukuran dibatasi terhadap heap guest. Jalur fullscreen,
input dan pause/resume dari test6 tidak diubah.

## Bukti

Uji diferensial menjalankan instruksi ARM target dan helper C++ terkompilasi pada
592 kombinasi alpha, efek 16 mode, warna, palette 4/8 bit, mirror, anchor, stride,
clipping dan ukuran negatif. Seluruh pixel tujuan dan padding cocok. Seluruh
40 tes regresi lolos; angka ini tidak berarti 40 perangkat diuji.

Model mengambil snapshot RAM, register, heap cursor dan waktu simulasi. Pada
masing-masing adegan, tiga tick yang sama dijalankan dengan jalur test6 lalu
diulang dengan helper raster terkompilasi. Snapshot dipulihkan di antaranya.
Hasil model yang terverifikasi:

| Sampel | Instruksi guest test6 | Instruksi guest test7 | Penurunan |
|---|---:|---:|---:|
| Menu utama | 5.337.801 | 2.154.105 | 59,6% |
| Intro | 9.554.033 | 1.388.879 | 85,5% |
| Map/dialog | 4.950.402 | 2.326.186 | 53,0% |

Framebuffer ketiga sampel identik seluruh pixel. Angka instruksi mengecualikan biaya helper host;
bukan rasio FPS atau pengukuran pada A24. Model memakai sejumlah stub JNI/libc/GLES,
serta memulai game dan skip melalui metode ekspor. Ia tidak menjalankan APK Android.

APK `dist/hl5-01.01.00-arm64-test7-raster.apk` berukuran 19.092.508 byte. Signature
v2/v3, delapan entry JNI, signer yang sama, hash baseline dan alignment ELF/ZIP 16 KB
diperiksa. Laporan lokal: `work/test7-raster-phases.json`, `work/test7-regressions.txt`
dan `work/android-build-report.json`. Source dan laporan test6 disimpan di history.

## Uji perangkat berikutnya

Instal sebagai update test6 tanpa uninstall. Bandingkan durasi/kelancaran intro,
menu utama, jalan dan bertarung pada map yang sama. Periksa fade, warna efek,
transparansi sprite, tombol, save, Home/Recents dan Exit. Tidak ada perangkat ADB
terhubung saat pengerjaan; performa dan stabilitas test7 belum dinyatakan selesai.
Terjemahan belum dimulai dan tetap menunggu penerimaan performa pengguna.
