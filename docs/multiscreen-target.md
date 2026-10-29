# Sasaran multiscreen dan investigasi layar hitam

Sasaran pengguna adalah memperluas area dunia/map yang terlihat sambil menjaga
proporsi objek. Source HL5 acuan menjadi bahan referensi; engine dan resource
APK target tetap menjadi dasar. Mode FULL yang hanya meregangkan framebuffer
400x240 tidak memenuhi sasaran tersebut. Tombol rasio/FULL dihapus dari test3.

## Layar hitam pada test2

Pengguna mengonfirmasi layar tetap hitam setelah ditunggu. Screenshot menunjukkan
Activity beserta tombol Java terbuka. Screenshot tersebut belum menunjukkan
apakah CPU guest gagal boot, GLES tidak tersedia, upload tekstur gagal, atau
frame game tidak diserahkan ke driver. Tidak ada log perangkat terhubung di workspace.

Kode test2 menyembunyikan overlay setelah 180 callback frame, termasuk saat
inisialisasi gagal. Nomor callback Java terus bertambah meskipun engine belum
siap. Karena itu panel yang hilang dan penghitung frame bukan bukti game berjalan.

Test3 adalah paket diagnostik, bukan penyelesaian layar hitam atau multiscreen:

- Status boot dari JNI, kernel, display, VFS, audio dan start app tetap terlihat.
- Kegagalan inisialisasi GLES menghentikan boot dengan pesan yang jelas.
- Kode error driver dicatat setelah upload tekstur dan pengiriman draw call.
- Eksekusi guest dihentikan setelah exception frame, agar state parsial tidak
  terus dieksekusi seolah-olah frame berhasil.
- Tombol `Salin status` menyalin informasi terakhir untuk diagnosis berikutnya.
- Import `memmove` target kini memakai hook salin dengan buffer sementara yang
  mendukung rentang tumpang tindih. Sebelumnya runner mengembalikan nol tanpa
  menyalin data. Perbaikan ini diuji pada model pemuatan data, bukan perangkat.

## Penelitian resolusi logis target

Disassembly binary target memperlihatkan ukuran dan titik tengah pada objek
`Graphic`: GetWidth di +0x54, GetHeight di +0x58, GetHalfWidth di +0x4c dan
GetHalfHeight di +0x50. `Graphic::ChangeFrameBuff` mengambil ukuran dari
descriptor framebuffer dan `ResetClip` membaca ukuran tersebut.

Eksperimen memanggil nativeInitDisplay dengan resolusi logis 400x240 dan 520x240
pada engine target yang sama. Kedua ukuran dikenali oleh Graphic dan descriptor
framebuffer. Tangkapan framebuffer CPU menunjukkan menu/loading pada canvas
yang berbeda lebar; ini belum membuktikan jangkauan map atau penambahan objek.

Pada eksperimen lebih panjang, kedua ukuran gagal di lokasi yang sama:
PC guest `0x40070914`, LR `0x40070a84`, R0 `0x14`, saat membaca memori yang tidak
dipetakan. Lokasi target adalah `FrameExtra::GetFrame`, dipanggil oleh
`ExtraData::GetHitAttkProperty`. Ini merupakan kegagalan model Python/JNI/libc,
belum dapat disamakan dengan penyebab layar hitam di perangkat. Pelebaran canvas
sendiri belum menyelesaikan pemuatan data game. Pemeriksaan berikutnya menemukan
import `memmove` belum diimplementasikan. Dengan operasi tersebut aktif, model
400x240 dan 520x240 melewati 80 tick awal dan mencapai layar intro bertanda Skip. Pengujian
ini tetap belum membuktikan gameplay atau luas map yang terlihat.

Pembacaan gambar model juga diperbaiki: field pertama Graphic menunjuk ke
descriptor framebuffer, sedangkan pointer pixel dibaca dari descriptor +0x10.
Pemeriksaan lama atas 84 warna membaca wilayah descriptor; angka tersebut
ditarik sebagai bukti rendering. Ekstraksi pixel yang benar pada enam tick awal
menunjukkan layar loading. Setelah memmove diaktifkan, 80 tick menghasilkan layar
intro bertanda Skip dengan 32 warna unik. Bukti masuk state game tidak
sama dengan gameplay yang telah tervalidasi.

## Kriteria penerimaan multiscreen

1. Boot dan render APK target stabil pada perangkat sebelum kamera diubah.
2. Lebar logis mengikuti aspek area layar yang tersedia, dengan skala X/Y sama.
3. Kamera, framebuffer, clipping dan batas penggambaran tile/objek mendukung
   lebar tambahan; penyesuaian didasarkan pada binary target.
4. Pada posisi karakter dan map yang sama, mode lebar memperlihatkan rentang
   koordinat dunia dan objek tambahan dengan ukuran sprite tetap proporsional.
5. HUD, dialog dan koordinat input tetap tepat; collision, script dan save tidak
   berubah sebagai efek samping penyesuaian tampilan.

Test4 telah berjalan di perangkat berdasarkan video/screenshot pengguna.
Test5 mengimplementasikan canvas logis dinamis melalui nativeInitDisplay asli:
pada surface 2620x1280 menjadi 492x240, dengan proyeksi GLES, viewport dan sentuhan
mengikuti canvas tersebut. Ukuran sprite tetap memakai skala yang sama di X/Y.
Lebar dipertahankan selama sesi ketika surface dibuat ulang; ukuran dihitung
kembali saat sesi baru agar framebuffer/game state tidak dialokasikan ulang
di tengah permainan. Test5 memakai letterbox pada rasio lebih sempit dari canvas.
Test6 mengganti aturan ini dengan viewport yang menutup semua tepi, skala seragam
dan overscan; padding cutout juga dihapus. Lihat [catatan fullscreen dan performa](test6-fullscreen-performance.md).

Model 492x240 melewati 300 tick termasuk callback pause/resume asli dan menghasilkan
framebuffer adegan map/dialog dengan 1125 warna. Dibandingkan model 400x240
pada tick yang sama, seluruh 36750 pixel pada area dunia x=145..389, y=20..169
cocok persis setelah translasi horizontal 46 pixel pada canvas lebar. Ukuran
objek tidak berubah; canvas menambahkan 92 pixel lebar dunia. Bukti ini berlaku
untuk satu adegan model, belum untuk seluruh map/perangkat. Intro dilewati melalui metode
EventSkipStart yang diekspor; ini bukan pengujian input pengguna atau APK Android.
Eksperimen/gambar berada di `work/viewport-*`. Validasi tambahan jangkauan dunia,
HUD dan sentuhan seluruh adegan pada perangkat tetap diperlukan.
Lihat [perubahan dan uji test5](test5-wide-lifecycle.md).
