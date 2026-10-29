# Test12: layout Inggris dan optimasi palet

Screenshot test11 dari pengguna membuktikan game berjalan dengan teks Inggris,
tetapi label stat bertumpuk, lokasi quest bertabrakan dengan kategori, beberapa
quest masih Korea, dan dialog berhenti terlalu dini pada layar lebar. Pengguna
juga meminta optimasi lanjutan. Test12 menangani tampilan dan performa secara
terpisah dari penggantian aset. APK asli dan test10/test11 tetap menjadi pembanding.

## Aset terjemahan

- Seluruh 13.825 field Hangul yang dikenali pada 57 DAT dan 258 SCN diterjemahkan.
  Sebanyak 72 label Inggris bawaan yang terlalu panjang juga dikoreksi dengan
  override yang memverifikasi teks sumber dan SHA-256 field target.
- Kolom stat memakai label pendek: `P.DEF` = physical defense, `M.DEF` = magic
  defense, `ATK SPD` = attack speed, `EVA` = evasion, `HIT` = accuracy,
  `CRIT` = critical, `C.RES` = critical resistance. Angka stat tidak berubah.
- Lokasi pada popup quest dibatasi satu baris, maksimum 84 piksel logis.
  Kategori memakai `MAIN`, `SIDE`, atau `HIDDEN`, sesuai makna sumber.
- Tombol utama konsisten: `GAME START`, `EXPERT`, `STORAGE`, `UPDATE`, `OPTIONS`,
  `RECORDS`, `HELP`, `SUPPORT`, `EXIT`. Label panjang memakai istilah ringkas.
- Hard wrap dialog 360 piksel dihapus; paragraf eksplisit tetap dipertahankan.
  Target menghitung lebar dialog dari `Graphic::GetWidth() - 16`, sehingga dialog
  mengikuti lebar canvas yang sudah ada. Artwork, ukuran bitmap font, advance
  karakter, parameter tinggi baris, input, opcode scene dan data gameplay tetap.

Kompilasi memverifikasi semua struktur SCN dan fragmen DAT nonteks. Semua 1.906
entri VFS di luar 299 aset teks tetap identik. Teks keyboard Hangul pada engine
merupakan tabel input, sehingga tidak diganti. Satu pesan autentikasi hardcoded
yang terverifikasi mendapat penggantian tampilan saja; proses autentikasi tetap.
Audit tabel teks bukan bukti OCR lengkap seluruh artwork.

## Teks quest lama dan wrapping saat render

VFS Inggris baru sudah berisi `Returning Home`, termasuk judul dan deskripsinya
pada ketiga tabel quest. Foto saja tidak dapat membuktikan apakah tampilan Korea
berasal dari save lama atau cache. Tidak ada save yang dihapus atau dikonversi.

Kamus render berisi 3.620 pasangan teks sumber persis, termasuk Korea asli dan
label Inggris test11 yang diperbaiki. Tidak ada pasangan ambigu yang diterapkan.
Kamus hanya dipakai pada fungsi tampilan font. String asli, buffer save dan
status quest tidak ditulis; argumen tampilan diarahkan ke salinan sementara.
Kamus statis memakai pencarian hash terurut, tanpa membangun tabel heap saat boot.

Untuk field teks dengan lebar yang tersedia, wrapper hanya mengganti spasi
terpilih menjadi pemisah baris. Panjang byte dan indeks pagination tetap sama.
Lebar font dan kode warna diambil dari objek font target; tidak ada penggantian
font global. Helper metrik font dibandingkan dengan instruksi ARM target,
termasuk offset awal, warna, spasi, Hangul dan beberapa ukuran font.

Jalur native Android API9–20 memakai engine asli dan aset Inggris yang sama.
Bridge render serta optimasi native host berlaku pada runner API21+; perbaikan
teks tersimpan lama pada perangkat legacy belum dibuktikan di perangkat.

## Optimasi dan batas bukti

Profil model menunjukkan intro banyak memakai `Graphic::ChangeBlendingPal`.
Jalur RGB565/mode 0–15 dijalankan pada host dengan tabel lookup target yang sama.
Kasus grayscale, format lain, atau buffer yang tidak memenuhi syarat tetap
memakai fungsi asli. Backup palet, transparansi, alpha, penanda perubahan dan
nilai balik dipertahankan. SO guest dan library engine legacy tetap identik.

Uji diferensial mencakup 384 kombinasi mode, alpha, flag dan ukuran palet terhadap
fungsi ARM asli; palet hasil dan penanda objek harus identik. Uji font mencakup
900 perbandingan width/line, pencarian quest Korea tanpa mengubah sumber, serta
wrapping pada lebar 220/384/476/504. Tes aset memeriksa kolom stat, lokasi satu
baris, kapitalisasi menu, metadata/opcode dan DEX/input/artwork yang tidak berubah.

Laporan lokal: `work/test12-palette-phases.json`, `work/test12-font-phases.json`,
`work/test12-full-tests.txt`, `work/android-build-report.json`. Profil ini memakai
model Python, stub JNI/GLES dan helper C++ terkompilasi; pengurangan instruksi
guest bukan pengukuran FPS Android atau bukti seluruh adegan lancar.

Hasil model pada masing-masing tiga frame, dengan framebuffer identik:

| Sampel | Sebelum helper palet | Sesudah helper palet | Pengurangan instruksi guest |
|---|---:|---:|---:|
| Menu utama | 1.997.163 | 1.997.163 | 0% |
| Intro | 1.388.879 | 561.635 | 59,56% |
| Map/dialog | 2.592.599 | 2.592.599 | 0% |

Helper metrik font, diuji terpisah, mengurangi instruksi guest sekitar 0,9% pada
menu dan 1,5% pada map/dialog. Pengukuran ini tidak menghitung seluruh biaya host,
bridge teks, GPU, I/O atau audio; tidak ada klaim kenaikan FPS dengan persentase itu.

Signature v1/v2/v3, signer update yang sama, zipalign 16 KB, ABI ARM32/ARM64,
DEX legacy terpisah, dan resource table STORED/alignment 4 diperiksa saat build.
Test12 belum diuji fisik: update tanpa uninstall, kelanjutan save lama, quest,
seluruh panel/menu, perpindahan portal, audio dan FPS masih memerlukan perangkat.

Seluruh 75 tes lokal lulus. APK terpasang di emulator ARM32 Android 4.0.2/API14
dan 4.4/API19. Pada API19 launcher mencapai activity native Midas dan menampilkan
layar rating; ini bukan bukti gameplay legacy atau performa di ponsel. Bitmap
rating Korea asli yang terlihat pada jalur legacy tetap dipertahankan dan belum
termasuk cakupan terjemahan field teks. Karena itu jangan menyebut seluruh artwork
sudah berbahasa Inggris.

APK: `dist/hl5-01.01.00-test12-layout.apk`, 22.787.239 byte, SHA-256
`beef8ea8fd70d40f0cad0ab62c0826b68c072db9e710f72cac6cd616857cacfb`.
Ringkasan bukti lokal ada di `work/test12-validation-report.json`. Stage test10
diarsipkan di `work/history/test10/runner`; runner aktif merupakan stage test12.

## Build ulang lokal

1. Jalankan `tools/translate_assets.py` dengan ZIP acuan yang dipin dan output
   `work/test12-english-assets`.
2. Jalankan `tools/prepare_android_runner.py` dengan `--localization-vfs`
   mengarah ke VFS Inggris tersebut dan stage baru di `work/`.
3. Jalankan `tools/build_android_test.py` dengan stage, toolchain lokal,
   `--include-legacy`, API9 android.jar, `--english-vfs`,
   `--version-code 1010012`, `--version-name 01.01.00-test12`, dan output
   `dist/hl5-01.01.00-test12-layout.apk`.
4. Jalankan `python -B tools/check_workspace.py` dan seluruh tes di `tests/`.

Kunci, binary, laporan penuh, source acuan dan APK hasil tetap lokal.
