# Alur kerja APK target baru

Current release: **Heroes Lore 5 v1.0.5**. On 2026-10-29 the owner accepted
1.0.4's presentation, reported residual new-game intro stutter, and explicitly
authorized Git commit/push and a new public GitHub Release. The earlier
local-only restriction is superseded for this release.

The update includes English intro/rating artwork, the supplied icon, a gold
HEROES LORE wordmark, and a readable outlined Covenant of Darkness subtitle.
Save DES and sprite blending were accelerated in the preceding local previews.
Version 1.0.5 additionally accelerates verified normal-orientation edge clipping,
with 96 target-ARM comparisons. Original guest, save format, input and gameplay
scripts remain unchanged. Physical 1.0.5 cutscene timing remains unverified.
See [release notes](release-v1.0.5.md) and [development notes](local-intro-preview.md).

Prioritas rilis: pengguna meminta perbaikan deskripsi quest dari save lama dan
publikasi ke `hisyam28/heroes-lore-5-en-multiscreen`. Perbaikan menambahkan jalur
`BFont::DrawTextLine` yang terverifikasi, tanpa menulis save. APK v1.0.0 memakai
label Heroes Lore 5 English, signer update yang sama dan debug nonaktif.
Publikasi **APK final sebagai aset GitHub Release** diminta eksplisit; APK input,
kunci, snapshot acuan, dependency binary dan hasil eksperimen tetap lokal serta
tidak ditambahkan paksa ke Git. Lihat [catatan rilis](release-v1.0.0.md).

Prioritas aktif: koreksi layout/quest Inggris dan optimasi yang diminta pengguna
setelah screenshot test11. Perubahan aset, bridge tampilan, dan optimasi runtime
dicatat dan diuji terpisah dalam [catatan test12](test12-layout-performance.md).
Save, opcode, metadata gameplay, input, artwork dan guest SO tetap dipertahankan.

Tahap test11: terjemahan aset Korea ke Inggris setelah pengguna mengonfirmasi
test10 dapat dipasang dan secara eksplisit meminta tahap terjemahan. Runtime
test10 dibekukan; perubahan dibatasi pada field teks VFS dan metadata update
yang diperlukan. Keberhasilan instalasi tidak berarti semua FPS/save/gameplay
telah diverifikasi. Panduan dan bukti ada di [terjemahan aset](english-assets.md).
Permintaan berikutnya menambahkan dukungan Android 4 dan jalur lama hingga
Gingerbread. Test9 memakai engine native baseline pada API9–20 dan runtime modern
pada API21+, dengan DEX terpisah; rincian dan batas uji ada di
[catatan kompatibilitas lama](test9-legacy-android.md).
Test9 kemudian ditolak installer pada ponsel modern. Test10 memperbaiki kompresi
`resources.arsc`; pemeriksaan install-time tersebut sekarang wajib dilakukan
sebelum dan sesudah signing, selain zipalign dan pemeriksaan signature.

1. **Penerimaan baseline.** Simpan APK asli di `inputs/`. Jalankan inventaris,
   catat SHA-256, identitas package/version melalui pemeriksa manifest Android,
   ABI, library dan arsip resource. Tool inventaris awal hanya mengidentifikasi
   kandidat struktur; ia belum menyatakan APK kompatibel.
2. **Pengenalan format.** Cocokkan target dengan kajian acuan. Tentukan profil
   berdasarkan hash dan struktur yang terbukti. Jangan menyalin alamat patch
   atau batas buffer dari versi lain tanpa verifikasi.
3. **Repack baseline.** Buktikan parser dan compiler mampu menghasilkan kembali
   byte asli tanpa perubahan. Tolak file terpotong, struktur tidak dikenal,
   path ekstraksi keluar workspace dan indeks yang tidak sesuai.
4. **Katalog baru.** Ekstrak teks dari APK target. Simpan file, konteks, source,
   slot target dan batas field yang terverifikasi. Pindahkan translation memory
   dari acuan hanya setelah teks sumber dan konteks cocok.
5. **Terjemahan dan UI.** Jaga placeholder, kode warna dan pemisah baris.
   Uji encoding, kapasitas buffer, lebar/tinggi panel dan font target. Gunakan
   override untuk teks identik dengan konteks berbeda. Jangan memotong makna
   secara otomatis agar lolos batas.
6. **Build terisolasi.** Gunakan baseline dan overlay untuk menghasilkan output
   baru. Jangan menimpa input. Build pipeline nyata ditambahkan setelah format
   target terverifikasi; workspace awal belum menyediakan build game.
7. **Verifikasi cakupan.** Bandingkan metadata, bytecode, save, library, audio
   dan konfigurasi input dengan baseline. Setiap perubahan di luar terjemahan
   dicatat dan diuji sesuai tujuan.
8. **Pengujian akhir.** Periksa signature, signer, alignment ELF dan ZIP 16 KB
   sesuai ABI target. Uji instalasi/update, pembaruan assets, kelanjutan save,
   dialog/menu, input dan gameplay di perangkat. Simpan hasil serta batas uji.

Terjemahan pada APK yang sudah berfungsi sebaiknya mempertahankan runtime APK
tersebut lebih dahulu. Port runner ARM64, perluasan viewport, pengaturan input
atau perubahan gameplay adalah pekerjaan terpisah sesuai kebutuhan target.

File inventaris lengkap tetap di `work/` agar nama input, path lokal dan rincian
binary tidak otomatis ikut ke source publik. Laporan publik dibuat sebagai
ringkasan yang telah diperiksa.
