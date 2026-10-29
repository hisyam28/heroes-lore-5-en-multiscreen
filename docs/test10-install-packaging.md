# Test10: memperbaiki APK yang ditolak installer

Pengguna melaporkan test9 tidak dapat dipasang sebagai update pada ponsel biasa
untuk testing Android baru. Kedua screenshot hanya menampilkan “Aplikasi tidak
terinstal”; tidak ada kode PackageManager atau logcat. Karena itu, kode error
perangkat tidak boleh diklaim sudah diperoleh.

## Cacat yang ditemukan

Test9 menyalin `ZipInfo` resource table dari APK baseline agar resource ID dan
isinya tetap utuh. Ini juga menyalin metode DEFLATE untuk `resources.arsc`.
Baseline memakai target SDK lama sehingga aturan penyimpanan ini berbeda,
sedangkan APK runner menargetkan SDK36.

[Dokumentasi Android](https://developer.android.com/about/versions/11/behavior-changes-11#app-packaging)
menyatakan aplikasi target SDK30+ tidak dapat diinstal bila `resources.arsc`
terkompresi atau tidak sejajar 4 byte. [Parser AOSP](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/com/android/internal/pm/pkg/parsing/ParsingPackageUtils.java)
melaporkan kategori `INSTALL_PARSE_FAILED_RESOURCES_ARSC_COMPRESSED` untuk
kondisi tersebut. Ini cacat konkret pada APK lokal test9 yang cukup menyebabkan
penolakan Android modern, bukan kode error yang disalin dari ponsel pengguna.

| APK | Kompresi resource table | Offset data | Sejajar 4 byte | Target SDK |
|---|---|---:|---|---:|
| test8 | STORED | 36580 | Ya | 36 |
| test9 | DEFLATE | 59520 | Ya | 36 |
| test10 | STORED | 59524 | Ya | 36 |

`zipalign -c` tidak menolak tabel yang dikompresi. Signature yang valid juga tidak
membuktikan seluruh aturan installer terpenuhi. Pemeriksaan test9 sebelumnya
melewatkan syarat ini; saran bahwa update siap dipasang belum cukup didukung
bukti packaging yang lengkap.

## Perbaikan dan verifikasi

Builder sekarang menyimpan byte `resources.arsc` baseline dengan metode STORED,
kemudian menjalankan zipalign. `tools/apk_packaging.py` memeriksa metode kompresi
dan offset local ZIP header sebelum serta setelah signing. Build target SDK30+
ditolak jika tabel hilang, duplikat, dikompresi atau tidak sejajar 4 byte.

Test10 menaikkan versionCode menjadi 1010010. Package tetap
`co.kr.eamobile.hl5.runner`; certificate test8, test9 dan test10 cocok. Signature
v1/v2/v3 dan alignment ZIP/ELF host modern diperiksa kembali. Support lama tetap
berupa jalur API9–20 native dan API21+ runner ARM32/ARM64; belum diuji fisik.

Perbandingan seluruh entry test9/test10 di luar `META-INF/` membuktikan hanya
**isi manifest** yang berubah, untuk versi dan label test10. Isi kedua DEX,
library modern/legacy, VFS, touch dan resource table identik. Perubahan kompresi
ZIP tabel tidak mengubah byte resource yang dibaca game, format save atau engine.

Sebelas tes relevan lolos tanpa skip: reproduksi kegagalan test9, penolakan tabel
unaligned/hilang/duplikat, penerimaan test10, validasi DEX dan routing yang
dikompilasi terhadap SDK9. Tes raster/heap sebelumnya tidak diulang karena semua
payload runtime test10 identik dengan test9. `python -B tools/check_workspace.py`
dan `git diff --check` dijalankan. Ini pemeriksaan statis/build serta model JVM,
bukan tes instalasi/update di Android. Tidak ada perangkat pada `adb devices`.

Hasil lokal: `dist/hl5-01.01.00-test10-install.apk`, 22.115.495 byte, SHA-256
`45243f4268f50dd30478d0439ea7345ecb7b9528a5e333fa11e8672fe7804e79`.
Laporan terakhir berada di `work/android-build-report.json`; laporan test9
dipertahankan di `work/test9-build-report.json`. Hasil pengujian ada di
`work/test10-install-tests.txt`.

Pasang test10 sebagai update tanpa uninstall untuk mempertahankan data runner.
Keberhasilan instalasi di ponsel pengguna masih perlu dikonfirmasi; screenshot
generik tidak cukup menyingkirkan penyebab lain jika paket yang sudah diperbaiki
tetap ditolak.
