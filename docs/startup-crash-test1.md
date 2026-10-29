# Diagnosis crash startup test1

Pengguna melaporkan APK test1 gagal dibuka pada Android 16 dengan MediaTek
Dimensity 9400+. Lima screenshot yang diberikan memperlihatkan bagian berbeda
dari stack trace dengan penyebab yang sama, bukan lima kegagalan terpisah.

## Baseline

APK yang ditunjuk ulang cocok dengan salinan baseline di `inputs/` berdasarkan
SHA-256 penuh:

`5fcddd17f1a4e3c48957c142aa2cf7738ef1b35775b48eecde43eb43d383403e`

Build test2 menerima file yang ditunjuk pengguna secara langsung melalui `--apk`.
SO guest, VFS dan konfigurasi touch tetap dibandingkan terhadap APK itu.

## Urutan kegagalan yang terbukti

1. Android membuka `co.kr.eamobile.hl5.runner.MainActivity`.
2. `onCreate()` test1, baris 64, memanggil `hideSystemUI()` sebelum `setContentView()`.
3. `hideSystemUI()`, baris 371, memanggil `getWindow().getInsetsController()`.
4. Stack trace menunjukkan `PhoneWindow.getInsetsController()` mencoba memakai
   `DecorView` yang masih null. Exception terjadi di dalam pemanggilan tersebut,
   sebelum pemeriksaan `if (controller != null)` milik aplikasi dapat dijalankan.
5. Android melaporkan `Unable to start activity` dengan penyebab
   `java.lang.NullPointerException`.

Pemanggilan tersebut berada sebelum persiapan aset, pembuatan GLSurfaceView dan
callback inisialisasi engine game. Bukti ini menetapkan kegagalan startup Java;
ia belum menguji emulasi guest, gambar game, audio, input atau save pada ponsel.
Kesalahan berasal dari perubahan wrapper UI yang ditambahkan pada test1.

## Perbaikan test2

- Pemanggilan awal sebelum `setContentView()` dihapus.
- Penyembunyian system bars dijadwalkan melalui `layout.post()` setelah content
  dipasang; callback fokus/resume tetap dapat meminta ulang mode immersive.
- `hideSystemUI()` memeriksa window, `peekDecorView()` dan status attachment
  sebelum mengakses controller dari view yang sudah terpasang.
- API 30+ memakai controller view; API lama mempertahankan flag system UI lama.
- `versionCode` naik dari 1010001 menjadi 1010002 dan label menyebut `Test 2`.
  Package dan kunci signing sama sehingga test2 dapat dipasang sebagai update.

`peekDecorView()` memang dapat mengembalikan null jika decor belum dibuat,
sebagaimana dijelaskan dalam [referensi Window Android](https://developer.android.com/reference/android/view/Window#peekDecorView()).

## Verifikasi dan batas bukti

Tes JVM mengambil metode `hideSystemUI()` aktual dari staging, lalu menjalankannya
dengan model Window/View. Kode test1 mereproduksi NullPointerException saat decor
belum dibuat. Perbaikan lulus untuk keadaan sebelum decor dibuat, window null,
view belum terpasang, controller null, jalur API 36 dan jalur API 26. Model ini
tidak menjalankan framework Android dan tidak menggantikan pengujian perangkat.

Tes profil, hash baseline, parser ELF dan keamanan path staging tetap dijalankan.
Build memeriksa signature, alignment ELF/ZIP 16 KB, serta kesamaan SO/VFS/touch
dengan baseline. Bukti test1 disimpan lokal di `work/failures/test1/`.

Hasil test2: `dist/hl5-01.01.00-arm64-test2.apk`. Pengujian pada ponsel pengguna
masih diperlukan untuk memastikan Activity berhasil dibuka dan mengetahui apakah
ada masalah berikutnya setelah inisialisasi game dimulai. Keberhasilan model UI
tidak membuktikan stabilitas gameplay maupun kompatibilitas runtime 16 KB.
