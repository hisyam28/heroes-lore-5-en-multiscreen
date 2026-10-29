# Terjemahan aset Inggris test11

Catatan ini mendokumentasikan build awal test11. Pengguna kemudian mengirim
screenshot game yang berjalan dan menunjukkan masalah layout serta quest Korea.
Katalog aktif sekarang milik test12; perubahan dan batas bukti terbaru ada di
[perbaikan test12](test12-layout-performance.md).

Pengguna mengonfirmasi test10 dapat dipasang, lalu meminta tahap terjemahan.
Baseline runtime ialah APK test10 dengan SHA-256
`45243f4268f50dd30478d0439ea7345ecb7b9528a5e333fa11e8672fe7804e79`.
APK target asli tetap menjadi sumber aset Korea dan tidak dimodifikasi.

## Cakupan perubahan

- 15.235 slot diperiksa pada 57 DAT dan 258 SCN target.
- 13.825 slot yang mengandung Hangul diterjemahkan; 1.410 slot lain dipertahankan
  byte demi byte, termasuk teks Inggris yang sudah ada dan slot kosong.
- 299 dari 2.205 entri VFS berubah. Sebanyak 1.906 entri lain, termasuk font,
  gambar, audio, data map, manifest VFS dan 16 aset tambahan target, tetap identik.
- Semua header dan bytecode SCN, jumlah/index string, tipe panjang asli, serta
  fragmen nonteks DAT tetap identik. Hanya panjang record/field yang memang
  menyimpan teks diperbarui; tidak ada upgrade format string SCN.
- APK akhir hanya berbeda pada `assets/data.vfs.mp3`, hash VFS di
  `assets/target-assets.json`, serta versionCode/versionName untuk update.
  Seluruh DEX, library native modern/legacy, input dan resource Android sama.
  Label launcher test10 dipertahankan; versi paket Inggris adalah test11.

Tidak ada penggantian SO/VFS referensi secara utuh. Lima scene referensi memiliki
bytecode berbeda (`00048`, `00049`, `00051`, `00095`, `00171`); bytecode itu tidak
diimpor. Target juga mempunyai 351 baris common_text, bukan 355 seperti referensi.
Parser VFS baru menemukan manifest melalui validasi semua nama/hash, tanpa
mengunci jumlah 2.189 entri milik referensi.

## Bahasa dan proteksi data

Katalog dipindahkan berdasarkan kecocokan teks sumber, file dan field konteks;
nomor baris saja tidak dipakai sebagai bukti transfer. Katalog target menyimpan
SHA teks sumber dan metadata/sibling context. Fingerprint APK/ZIP referensi
diperiksa sebelum proses. Tiga sumber campuran/rusak yang tidak cocok persis
ditangani dengan override yang ditinjau: dua label stat dan satu dialog 00151.

Nama karakter mengikuti referensi. Bahasa dipersingkat pada label yang terlalu
panjang, misalnya `Restore Tome (5)`, `Rebirth Amulet (5)` dan `Retaliation Crest`.
Sebanyak 34 slot mempunyai override editorial untuk sumber rusak, koreksi kode
warna, kalimat yang lebih sederhana atau judul yang terlalu panjang. Pemendekan
empat pola nama lain diterapkan hanya di field nama. Teks tidak dipotong otomatis
pada batas byte. Placeholder `#nn`, format `%d/%s`, prefix tampilan dan terminator
NUL diperiksa; seluruh kode warna asli harus tetap berjumlah sama.

Referensi mengubah tabel escape font agar apostrof dapat dicetak. Patch tersebut
**tidak digunakan**: engine target memperlakukan apostrof ASCII sebagai warna.
Kontraksi Inggris dieja penuh dan nama majemuk diringkas; warna kuning referensi
dikembalikan ke kode asli. Ukuran font dan jarak karakter tidak diubah.

`translations/catalog.json` menyimpan hasil target, sedangkan
`translations/slot-overrides.json` menjadi tempat koreksi editorial. Mengedit
katalog hasil saja tidak cukup; kompilasi ulang membangunnya dari input yang
dipin dan override. `translations/glossary.json` mencatat istilah terpilih.

## Font dan layout

Aset asli `c/font/eng.fnt` memakai HNF dengan 95 bitmap karakter ASCII 8×11;
glyph aktif Inggris berukuran 5×11 dengan advance 6 piksel. Instruksi target
`BFont::GetByteLenPrintable` dan konstruktor diverifikasi, lalu dibandingkan
melalui eksekusi ARM asli. Model juga memakai advance Hangul 10 piksel dan
escape dari tabel target. Fingerprint ada di `config/localization-profile.json`.

Lebar wrapping konservatif dipakai sesuai konteks: deskripsi/help 126, quest 138,
popup 156, episode 220 dan dialog 360 piksel logis. Nama pendek dibatasi 19 byte
dan 114 piksel; judul panjang tertentu dipersingkat. Font, line spacing dan
mekanisme pagination tetap dari runtime asli. Daftar Related Traits mempertahankan
awal baris tiap item. Kata sangat panjang tetap mengikuti soft-wrap native.
Substitusi angka/placeholder serta semua tinggi panel nyata belum diuji fisik;
metrik yang lolos bukan bukti setiap adegan sudah bebas clipping.

`tools/preview_english.py` menghasilkan `work/english-font-layout.png` dengan bitmap
font asli. Ini contact sheet layout, bukan screenshot gameplay. Sampel ditinjau
untuk popup, episode, skill, quest, nama item dan help. Artwork bertulisan Korea
yang bukan field teks tidak di-OCR atau diubah; jangan mengklaim semua bitmap
atau teks hardcoded engine telah diterjemahkan dari cakupan tabel ini.

## Bukti pengujian

- Delapan tes terjemahan lolos. Tes memeriksa seluruh format target round-trip,
  nol Hangul tersisa pada field yang dikenali, hanya field Korea yang berubah,
  metadata/opcode, konten APK, batas byte/label dan layout per baris.
- Uji diferensial mencakup 216 kasus pemenggalan baris, termasuk Hangul, ASCII,
  warna dan semicolon, pada enam lebar melawan fungsi font ARM target.
- Perubahan buatan pada font, header scene dan field Inggris ditolak. String
  yang memerlukan perubahan format panjang juga ditolak.
- Model Python memakai SO target serta VFS Inggris untuk mencapai menu dan
  state game baru. Ia memakai sejumlah stub JNI/libc/GLES; bukan APK Android
  terkompilasi. Perbandingan model Korea/Inggris pada 80 tick menampilkan frame
  hitam bertanda Skip, sehingga model ini tidak dipakai sebagai bukti kualitas
  dialog atau render gameplay. Bukti layout datang dari font/sample; pemeriksaan
  seluruh adegan tetap memerlukan perangkat.
- Signature v1/v2/v3, signer yang sama, zipalign 16 KB dan resource table STORED
  beralignment 4 byte diperiksa. Metadata manifest dibandingkan secara semantik:
  hanya versi berbeda. `python -B tools/check_workspace.py` dan `git diff --check`
  dijalankan. Test11 belum diuji di ponsel; hasil pemasangan test10 tidak dipakai
  sebagai bukti gameplay/terjemahan test11.

## Build dan review

```powershell
python -B tools/translate_assets.py --reference <zip-acuan>
python -B tools/build_english_apk.py --jdk <jdk17> --build-tools <build-tools36> --android-jar <android36.jar>
python -B tools/preview_english.py
python -B tools/check_workspace.py
```

Hasil `dist/hl5-01.01.00-test11-en.apk`, 22.176.935 byte, SHA-256
`2265b7250e75d5a7511e137d7a8d480fbe753a3585df3a9ab9f5af644e864f91`.
VFS Inggris SHA-256
`9638c53dd2d9cea9f81955c4cf87dcbe340a91cee0f8821089de0a409e36725a`.
Laporan lokal: `work/english-assets/translation-report.json`,
`work/english-build-report.json`, `work/english-translation-tests.txt` dan
`work/english-layout-preview.json`. Test10 Korea tetap tersedia untuk pembanding.

Pasang sebagai update tanpa uninstall. Periksa intro/dialog, pergantian halaman,
menu, nama/deskripsi item dan skill, quest, help serta save lama. Jika muncul
teks yang terpotong atau istilah membingungkan, catat screenshot dan lokasinya
agar koreksi dilakukan pada field teks terkait, tanpa mengubah runtime.
