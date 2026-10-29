# Test9: jalur Android lama dan modern

**Catatan lanjutan:** pengguna melaporkan test9 ditolak saat update pada ponsel
modern. Resource table-nya ternyata masih dikompresi, yang dilarang untuk target
SDK36. Gunakan test10; [diagnosis packaging](test10-install-packaging.md) menjelaskan
perbaikan serta batas bukti. Pemeriksaan awal di bawah belum mencakup syarat ini.

Permintaan pengguna adalah minimum Android 4; pengguna juga mengingat game
berjalan pada Gingerbread. Test9 menambahkan jalur native lama dalam satu APK
dengan minimum SDK 9/Android 2.3. Ini adalah hasil build yang siap diuji, bukan
pernyataan bahwa semua versi Android sudah terbukti menjalankan gameplay.

## Pemilihan runtime

| Perangkat | Runtime dalam test9 |
|---|---|
| Android 2.3–4.4/API9–20, ARM | Kelas Java asli dan `libHeroesLore5.so` baseline, langsung tanpa Unicorn |
| Android 5+/API21+, ARMv7 atau ARM64 | Runner modern dengan perbaikan heap, startup dan raster test8 |
| ARM `armeabi` tanpa ARMv7 | Jalur native asli |

Library asli memiliki atribut CPU ARMv5TE. APK menyediakan library tersebut di
`armeabi` dan `armeabi-v7a`, identik byte demi byte dengan baseline. Host modern
ARM32/ARM64 kini dilink terhadap API21; library host hanya dimuat oleh jalur modern.
Ini menangani kasus Android 5–7 ARM64: proses 64-bit tetap mendapat host 64-bit,
tanpa mencoba memuat engine native 32-bit ke proses tersebut.

Launcher kecil `CompatibilityActivity` dikompilasi terhadap SDK **API9 resmi**,
yang hash `android.jar`-nya diperiksa tool. Ia memilih nama Activity melalui
string sehingga tidak memiliki referensi tipe ke kelas runner modern.
Kode launcher dan semua 29 kelas Java baseline berada dalam `classes.dex`
format DEX035. Runner modern berada dalam `classes2.dex`; Android sebelum 5
tidak membutuhkannya. Pemisahan ini mengikuti batas [dukungan multidex native
Android 5+](https://developer.android.com/build/multidex).

Java baseline dienkode ulang oleh D8 untuk digabung dengan launcher. Semua
definisi kelas asli diperiksa keberadaannya; byte DEX gabungan tidak diklaim
identik dengan DEX input. SO, VFS, touch, `resources.arsc` dan semua berkas `res/`
asli dipertahankan persis, termasuk ID resource yang dirujuk kode lama. Tidak
ada offset atau instruksi game baru yang ditambal pada jalur legacy.

Jalur lama mempertahankan UI, input, audio, pengelolaan memori dan perilaku
lifecycle baseline. Perluasan canvas dan perbaikan wrapper modern test8 tidak
otomatis diterapkan pada jalur tersebut. Proporsi, HUD dan resolusi Android lama
masih perlu diuji di perangkat; belum ada klaim multiscreen setiap rasio.

## Manifest dan paket

Manifest universal menambahkan launcher serta Activity asli yang dibutuhkan;
Activity game tidak diekspor. Izin legacy mengikuti manifest baseline, ditambah
izin baca telepon/storage yang dahulu diimplikasikan target SDK sangat lama.
Izin khusus jalur lama dibatasi sampai SDK20. Theme memakai theme hitam bawaan
yang tersedia pada SDK lama, tanpa referensi ke Theme.Material di primary DEX.

Library native diekstrak saat instalasi untuk kompatibilitas loader lama.
Library host modern tetap memiliki segment ELF 16 KB dan APK di-zipalign 16 KB;
library legacy asli mempertahankan alignment 4 KB dan tidak dimuat jalur modern.
Jangan menyimpulkan seluruh `.so` native dalam APK ini mempunyai alignment 16 KB.

Signing v1 untuk Android lama serta v2/v3 telah diverifikasi pada APK akhir.
[Dokumentasi Android](https://source.android.com/docs/security/features/apksigning/v2)
menjelaskan perlunya JAR signing untuk versi sebelum Android 7. Package dan signer
runner tetap sama dengan test8 sehingga APK dapat dipasang sebagai update runner.
Ini bukan update dengan signer yang sama seperti APK game asli. Tool tidak
menghapus save; kompatibilitas/persistensi save tetap membutuhkan tes perangkat.

## Build ulang

Toolchain test8 masih digunakan. Sediakan pula SDK API9 dari arsip resmi Google
`android-2.3.1_r02.zip`; SHA-1 metadata SDK
`209f8a7a8b2cb093fce858b8b55fed3ba5206773`, SHA-256 arsip
`b2ab4896d0a4857e4f688f69eb08b0e1a8074709d4445a92a83ece7ec7cd198c`,
SHA-256 `android.jar`
`99bddc4363e5be6cc2fe9e243465cd9856c64b2c8238e1e1023acae59bb88469`.
Arsip, jar dan provenance rinci tetap lokal di `work/`.

```powershell
python -B tools/build_android_test.py --include-legacy --legacy-android-jar <api9-android.jar> --ndk <ndk-r28c> --jdk <jdk17> --build-tools <build-tools36> --android-jar <android36.jar>
python -B tools/check_workspace.py
python -B -m unittest discover -s tests -v
```

Staging modern tetap dihasilkan dari overlay yang sama seperti test8. Source
launcher dan manifest universal berada di `tools/compatibility/`; hash keduanya
dicatat terpisah dalam laporan build. Tanpa `--include-legacy`, builder tetap
menghasilkan varian test8 dengan minimum SDK26. Test8 tidak ditimpa oleh test9.

## Bukti dan pengujian berikutnya

- **Statis/build:** host ARM32/ARM64 berhasil dilink API21; launcher berhasil
  dikompilasi memakai API9; kedua DEX lolos pemeriksaan checksum/format/kelas,
  semua resource baseline dan native legacy identik; signature v1/v2/v3 serta
  alignment host modern dan ZIP lolos. Minimum SDK9, target36, launcher dan
  ABI juga diperiksa dari manifest APK akhir memakai `aapt2`.
- **Regresi/model:** 55 tes lolos, termasuk pilihan jalur pada API9/10/14–20 dan
  API21–36, pemisahan DEX APK akhir, heap, raster serta model startup test8.
  JVM routing bukan eksekusi Activity Android dan bukan tes GPU/native legacy.
- **Perangkat:** `adb devices` kosong. Android 2.3/4, Android 5–7, serta test9
  pada Android16 belum diuji fisik. FPS, audio, input, save, lama startup dan
  perpindahan portal belum dinyatakan selesai. Tidak ada dukungan x86 dalam APK.

Hasil lokal `dist/hl5-01.01.00-test9-legacy.apk`, 22.115.495 byte, SHA-256
`bd1868082330c58baecd5d078f89c1a441cfff3e6a37193fe5501cc1db8b4e97`.
Laporan build test9 di `work/test9-build-report.json`, laporan test8 disimpan
di `work/test8-build-report.json`, hasil regresi di `work/test9-regressions.txt`.
Pada perangkat lama, periksa pembukaan, mulai/load save, audio, sentuhan, Home/
resume dan portal. Pada kedua perangkat Android16, bandingkan perilaku test8
untuk memastikan pemilihan jalur modern tetap benar. Terjemahan tetap ditunda.
