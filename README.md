# Heroes Lore 5 English Multiscreen

Heroes Lore 5 versi Inggris dengan tampilan multiscreen dan adaptasi Android ARM32/ARM64. APK asli **01.01.00** menjadi baseline game. Source **[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)** digunakan sebagai referensi teknis dan bahasa, dengan penyesuaian terhadap binary target.

**Rilis: v1.0.0** · Nama aplikasi: **Heroes Lore 5 English**

[Unduh APK v1.0.0](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/download/v1.0.0/heroes-lore-5-english-multiscreen-v1.0.0.apk) · [Halaman rilis](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest) · [Kredit](CREDITS.md)

## Spesifikasi dan kompatibilitas

| Komponen | Keterangan |
|---|---|
| Minimum paket | Android **2.3 Gingerbread / API9**, termasuk Android 4 |
| Jalur Android lama | Android 2.3–4.4 / API9–20: engine ARM asli |
| Jalur Android modern | Android 5.0+ / API21+: runner ARM32 atau ARM64 |
| Arsitektur | `armeabi` untuk engine legacy; `armeabi-v7a` dan `arm64-v8a` untuk perangkat yang sesuai |
| Target SDK | **36**, Android **16** |
| Grafis | OpenGL ES **1.1** / provider GLES1 yang kompatibel |
| Orientasi | Landscape |
| Layar modern | Canvas mengikuti rasio layar dengan proporsi objek tetap |
| Alignment host modern | ELF dan ZIP **16 KB** |
| Package | `co.kr.eamobile.hl5.runner` |
| Versi / versionCode | **1.0.0** / **1010100** |
| Baseline game | **01.01.00** |
| APK | Universal ARM, **22.787.239 byte** (sekitar 23 MB) |

Minimum paket adalah batas instalasi yang dikonfigurasi, bukan sertifikasi semua perangkat. Android 2.3 belum diuji fisik. Instalasi emulator ARM32 Android 4.0.2 dan 4.4 sudah diperiksa; ini belum membuktikan seluruh gameplay legacy. Tidak tersedia library host x86/x86_64. Batas RAM dan kecepatan CPU minimum belum ditetapkan melalui benchmark perangkat.

## Fitur APK

- **Multiscreen pada runner modern.** Area pandang dunia diperluas mengikuti rasio layar, bukan meregangkan objek dari rasio 5:3. Viewport dan koordinat sentuhan mengikuti canvas. Fullscreen memakai area cutout yang tersedia dan menyembunyikan system bar. Perluasan viewport berlaku pada jalur Android 5+; jalur native lama mempertahankan perilaku layar engine asli.
- **Terjemahan Inggris.** Sebanyak **13.825 field Hangul** diterjemahkan pada **57 tabel DAT dan 258 script SCN** yang diperiksa. Sebanyak **72 label Inggris bawaan** diringkas agar sesuai panel. Menu utama memakai kapitalisasi konsisten, stat memakai label ringkas, dan dialog modern mengikuti lebar kotak yang tersedia.
- **Quest dari save lama.** Pada runner modern, judul, kategori dan deskripsi Korea yang cocok dengan kamus sumber diganti saat ditampilkan. Deskripsi diterjemahkan sebelum pemenggalan dan scrolling. File save dan status/progres quest tidak ditulis ulang; tidak perlu memulai permainan baru untuk perbaikan tampilan ini.
- **Lifecycle dan Exit.** Fullscreen dipasang setelah view siap. Kembali dari Home memakai pause/resume, dan menu Exit diteruskan untuk menutup task pada runner modern.
- **Optimasi runtime.** Memori guest yang dilepas dapat dipakai ulang; persiapan aset berjalan di background dan cache memakai fingerprint. Salin framebuffer, raster RGB565, efek palet dan metrik font dioptimalkan dengan fallback ke fungsi asli untuk kasus yang tidak didukung.
- **Tampilan bersih.** Overlay hijau dan tombol salin status tidak muncul pada peluncuran normal. APK rilis tidak memakai flag Android `debuggable`.
- **Data game dipertahankan.** Guest SO, metadata gameplay, opcode script, format save, input, audio dan artwork tidak diganti dengan versi source acuan. Perubahan teks dan adaptasi host dicatat terpisah.

Artwork rating pada jalur Android lama masih Korea. Cakupan field teks di atas tidak berarti seluruh bitmap sudah diterjemahkan. Bridge perbaikan tampilan save lama berlaku pada runner modern; jalur legacy tidak memakai bridge tersebut. Layanan online lama tidak dinyatakan pulih.

## Instalasi dan update

1. Unduh APK dari [GitHub Releases](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest).
2. Izinkan instalasi dari aplikasi pengunduh/file manager jika Android memintanya.
3. Untuk build runner sebelumnya, **pasang sebagai update tanpa uninstall** agar data aplikasi tetap tersimpan. Package dan signer update dipertahankan.
4. Lanjutkan save dan periksa panel quest lama. Penggantian tampilan tidak mengubah progres permainan.

APK lain dengan package atau signer berbeda belum tentu bisa diperbarui melalui jalur yang sama. Jangan menghapus aplikasi yang berisi save hanya untuk mencoba pemasangan.

SHA-256 APK v1.0.0:

```text
dfc424bbabc19a45512857250153af175143a130fcd429131aed8053357618ed
```

## Bukti pengujian

**78 tes lokal lulus** untuk rilis ini, termasuk regresi deskripsi quest save lama
dan pemeriksaan APK final. Pemeriksaan workspace dan whitespace Git juga lulus.

Pengguna telah mencoba seri build sebelumnya di Android 16 pada Dimensity 9400+ dan Samsung Galaxy A24/Helio G99 serta melaporkan peningkatan tampilan/performa. Pada review terakhir, bagian lain dinilai cukup baik, dengan deskripsi quest save lama sebagai masalah tersisa. Rilis 1.0.0 menambahkan perbaikan jalur deskripsi tersebut; APK final belum diuji langsung pada ponsel pengguna.

- Tes lokal melindungi format VFS, metadata/opcode, placeholder/kontrol warna, input, DEX legacy/modern, heap, viewport dan aset yang tidak diubah.
- Regresi menjalankan ARM **QuestMgr → DrawTextLine → DrawText**, memakai deskripsi Korea asli dan beberapa posisi scroll, lalu memastikan byte data quest tetap sama.
- Helper font dibandingkan pada **900 kasus** dan helper palet pada **384 kombinasi** terhadap fungsi ARM target.
- Pada sampel intro tiga frame, helper palet mengurangi instruksi guest dari **1.388.879 menjadi 561.635 (59,56%)**, dengan framebuffer identik. Sampel menu/map tidak mendapat pengurangan dari helper palet ini. **Ini bukan persentase kenaikan FPS Android.**
- Signature v1/v2/v3, signer update, resource table STORED/alignment 4 byte, alignment host 16 KB, nama dan versi paket diperiksa saat build.

Tidak ada klaim semua ponsel atau seluruh adegan pasti lancar. Audio, sesi panjang, portal berulang, save dan variasi UI masih memerlukan pemeriksaan perangkat. Rincian ada di [catatan v1.0.0](docs/release-v1.0.0.md).

## Source dan build lokal

Repositori memuat tooling, profil target, katalog/override terjemahan, tes, dokumentasi dan patch runner. **APK input, SO game, dependency binary, snapshot acuan, kunci dan hasil build tidak dimasukkan ke Git.** APK final tersedia sebagai aset GitHub Release.

Build lokal memerlukan APK baseline dan ZIP referensi dengan hash sesuai profil, Python 3.10+, JDK17, Android SDK API36/API9, Build Tools dan NDK yang tercatat. Tes ARM tambahan memakai Python Unicorn. Toolchain, input dan stage tetap lokal. Lihat [petunjuk rilis](docs/release-v1.0.0.md) dan [profil target](config/target-profile.json).

```powershell
python -B tools/check_workspace.py
python -B -m unittest discover -s tests -v
```

| Direktori | Isi |
|---|---|
| `config/` | Profil target, lokalisasi dan metadata rilis |
| `tools/` | Parser, validator, compiler teks, staging/overlay dan builder APK |
| `translations/` | Katalog, glossary dan override berdasarkan sumber/konteks |
| `tests/` | Pengujian tooling, model dan perbandingan ARM target |
| `docs/` | Referensi, workflow, diagnosis, bukti dan batas uji |
| `inputs/`, `work/`, `dist/`, `.local/` | Data dan hasil lokal yang diabaikan Git |

Riwayat: [referensi](docs/reference-study.md), [Android](docs/android-port.md), [multiscreen](docs/multiscreen-target.md), [stabilitas](docs/test8-stability-startup.md), [legacy](docs/test9-legacy-android.md), [packaging](docs/test10-install-packaging.md), [terjemahan](docs/english-assets.md), [layout/performa](docs/test12-layout-performance.md).

## Kredit

- **[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)** — referensi utama reverse engineering, runner dan terjemahan Inggris HL5.
- **[hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en)** — pengalaman lokalisasi HL3.
- **[Unicorn Engine](https://github.com/unicorn-engine/unicorn)** dan kontributor QEMU — fondasi eksekusi ARM guest.
- Heroes Lore 5 dan materi game tetap merupakan karya pemegang hak masing-masing; proyek ini tidak mengklaim kepemilikan atau afiliasi resmi.

Penyesuaian target, multiscreen dan rilis ini dikelola di **hisyam28/heroes-lore-5-en-multiscreen**. Rincian atribusi dan komponen pihak ketiga terdapat di [CREDITS.md](CREDITS.md).
