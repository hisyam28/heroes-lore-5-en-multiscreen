# Heroes Lore 5 English Multiscreen v1.0.0

Rilis publik pertama pada `hisyam28/heroes-lore-5-en-multiscreen` memakai nama
aplikasi **Heroes Lore 5 English**, versionName **1.0.0**, versionCode **1010100**
dan package runner yang sama seperti build sebelumnya. Label launcher, versi dan
nama APK tidak lagi memakai kata test. Flag Android `debuggable` dinonaktifkan;
penandatangan update tetap sama agar data aplikasi dapat dipertahankan.

## Perbaikan quest save lama

Screenshot pengguna menunjukkan judul `Returning Home`, kategori dan lokasi sudah
Inggris, tetapi deskripsi masih Korea. Instruksi binary target memperlihatkan
`QuestMgr::DrawQuestString` mengirim buffer deskripsi di `this+28` ke
`BFont::DrawTextLine`, berbeda dari jalur judul yang sudah tercakup sebelumnya.
Panggilan itu terjadi pada alamat target `0xce3e8`. Fingerprint kedua fungsi
ditambahkan ke profil yang wajib cocok dengan APK target.

Bridge tampilan kini menangani `DrawTextLine`: teks berada di argumen 6 dan lebar
di argumen 4. Teks sumber dicocokkan persis dengan kamus, disalin ke scratch, lalu
baru fungsi asli menghitung baris dan mengambil halaman scroll. Buffer quest,
status/progres, file dan format save tidak diubah. Jalur ini berlaku pada runner
modern API21+; engine legacy API9–20 tetap memakai implementasi native asli.

Regresi menjalankan instruksi ARM quest dan pagination asli, dengan stub hanya
pada libc dan draw piksel terakhir. Dua posisi scroll menampilkan potongan
Inggris yang berbeda, sedangkan seluruh buffer QuestMgr tetap identik. Tes ini
menangkap jalur yang belum dicakup oleh tes pencarian judul sebelumnya.

## Isi paket dan batas kompatibilitas

- Minimum manifest Android 2.3/API9, target SDK36/Android16.
- Engine native ARM asli untuk API9–20, runner ARM32/ARM64 untuk API21+.
- Multiscreen, penyesuaian sentuhan/fullscreen, lifecycle, optimasi heap/raster/
  palet/font dan bridge teks lama berlaku pada jalur modern.
- Aset Inggris: 13.825 field Hangul dan 72 koreksi label Inggris bawaan;
  opcode, metadata gameplay, input, font, audio/artwork dan guest SO dipertahankan.
- Instalasi emulator API14/API19 sudah diperiksa pada build sebelumnya.
  Android2.3 dan seluruh gameplay legacy belum dibuktikan pada perangkat fisik.
- Artwork rating legacy masih Korea. Layanan online lama tidak dinyatakan pulih.
- Pengguna menerima hasil umum build sebelumnya, kecuali deskripsi save lama.
  Perbaikan final diuji statis dan melalui eksekusi ARM; validasi APK final pada
  ponsel, FPS, audio dan sesi panjang tetap berbeda dari bukti tersebut.

Spesifikasi, fitur dan cara update tersedia pada [README](../README.md).

## Build lokal

Input dan dependency harus disiapkan lokal sesuai fingerprint
[profil target](../config/target-profile.json). Jangan mengganti target dengan
binary referensi. Versi toolchain yang dipakai: JDK17, NDK r28c, Android SDK36,
Build Tools36 serta android.jar API9 resmi untuk launcher legacy.

1. Kompilasi aset dengan `tools/translate_assets.py --reference <zip-acuan>
   --out work/english-release`.
2. Buat stage baru dengan `tools/prepare_android_runner.py --reference
   <zip-acuan> --out work/runner-release --localization-vfs
   work/english-release/data.vfs.mp3`.
3. Jalankan builder berikut dengan path toolchain lokal yang sesuai:

   ```powershell
   python -B tools/build_android_test.py --runner work/runner-release/app/src/main --ndk <ndk> --jdk <jdk17> --build-tools <build-tools> --android-jar <android36.jar> --include-legacy --legacy-android-jar <android9.jar> --english-vfs work/english-release/data.vfs.mp3 --version-code 1010100 --version-name 1.0.0 --application-label "Heroes Lore 5 English" --release --out dist/heroes-lore-5-english-multiscreen-v1.0.0.apk
   python -B tools/check_workspace.py
   python -B -m unittest discover -s tests -v
   ```

`build_android_test.py` adalah nama tooling historis, bukan label APK rilis.
Builder memeriksa hash stage, identitas baseline, kecocokan kamus/VFS, pembagian
DEX, kesamaan resource/input/guest, ABI, signature dan alignment. Hasil serta
kunci tetap lokal; APK final diunggah sebagai aset Release, bukan ditambahkan
paksa ke Git. Publikasi APK final diminta secara eksplisit oleh pemilik proyek.

Metadata dan checksum rilis ada di [config/release.json](../config/release.json).
Seluruh **78 tes lokal lulus** pada APK final, termasuk nama/versi tanpa test,
flag debug nonaktif, kehadiran hook quest pada kedua library host, dan kesamaan
semua payload APK selain manifest serta dua library host yang memang berubah
dibanding build sebelumnya. Sertifikat final cocok dengan signer update lama.
Kredit utama: [sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en).
