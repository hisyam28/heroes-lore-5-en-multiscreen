# Kajian acuan

Kajian awal dilakukan pada 27 Oktober 2026. Detail lengkap disimpan pada
`.local/reference/hl5-source-study.md` bersama hasil verifikasi JSON dan source
acuan lengkap. Bahan tersebut dipakai untuk analisis lokal.

## HL5

Source acuan berisi tooling Python serta runner Android dengan engine guest
`libHeroesLore5.so` ARM32, CPU bridge Unicorn pada host ARM64, dan resource VFS.
Engine game asli masih berupa binary; ZIP tersebut bukan source penuh engine.
Ini berbeda dari format WIPI LGT `binary.mod` pada proyek HL3.

Hasil pemeriksaan bahan acuan:

- 2.189 entri VFS dan manifest 2.188 nama; parse/repack tanpa perubahan identik.
- 57 tabel DAT dan 258 script SCN berhasil round-trip secara identik.
- Katalog memiliki 15.241 slot, termasuk 449 source kosong.
- Validator mencatat nol error dan sembilan warning lebar kata.
- Resource yang disertakan sudah berbahasa Inggris dan patch apostrof sudah
  terpasang. APK target baru tetap perlu diekstrak ulang.
- Belum ada pengujian perangkat atau benchmark FPS dalam kajian ini.

Parser VFS menetapkan jumlah entri dan posisi manifest versi acuan secara
tetap. Runner memakai alamat pointer, vtable dan offset objek tertentu.
Batas buffer, kode warna dan metrik font juga perlu diverifikasi ulang.
Mode FULL runner mengisi layar dengan stretch dari ruang game 400x240;
ini belum memperluas kamera atau jumlah map yang terlihat.

## Pengalaman HL3 yang dipakai kembali

- Inventaris dan hash baseline sebelum modifikasi.
- Lindungi metadata, opcode, format save dan placeholder.
- Kurasi teks menurut konteks, batas byte dan ruang panel aktual.
- Periksa perubahan kode/font terhadap pengenal binary yang cocok.
- Bandingkan isi APK dan resource untuk membuktikan cakupan perubahan.
- Pisahkan bukti uji statis/simulasi dari pengujian fisik.
- Periksa signature, signer dan alignment pada APK akhir.

## Hal yang ditentukan setelah APK target tersedia

Identitas versi, ABI, format arsip, struktur tabel/script, metrik font dan
runtime baru ditetapkan dari APK target. Katalog lama menjadi translation
memory setelah source/context matching. Jika target berbasis WIPI LGT atau
engine lain, parser dan runner acuan tidak dianggap kompatibel secara otomatis.
