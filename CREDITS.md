# Kredit dan asal referensi

Proyek ini disiapkan berdasarkan kajian ZIP source HL5 yang diberikan pemilik
workspace serta pengalaman pengerjaan proyek HL3.
Katalog Inggris rilis ini memakai teks sumber dan terjemahan referensi HL5 melalui
pencocokan konteks target, dengan koreksi kontrol, ejaan dan pemendekan lokal.
Resource Inggris, opcode dan library dari snapshot referensi tidak disalin
menggantikan runtime game target.

- Referensi HL5: [sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en).
  Kredit utama untuk kajian reverse engineering, implementasi runner, parser
  resource dan translation memory Inggris. Referensi tidak diklaim sebagai karya
  baru proyek ini. Penyesuaian binary 01.01.00, multiscreen, kestabilan,
  optimasi, layout dan bridge deskripsi save lama didokumentasikan terpisah.
- Referensi HL3: [hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en).

ZIP acuan tidak memiliki metadata Git, sehingga commit upstream persisnya
belum ditetapkan. Hash bahan dan salinan sumber lengkap disimpan lokal.
Source runner acuan memakai [Unicorn](https://github.com/unicorn-engine/unicorn)
sebagai engine CPU. Library ARM64 berasal dari ZIP acuan yang dipin hash-nya.
Dependency ARM32 test8 dibangun dari source resmi Unicorn 2.1.2; URL, fingerprint
dan langkah build dicatat dalam `tools/build_arm32_dependency.py` serta profil
target. Source, berkas lisensi upstream dan hasil kompilasi tetap disimpan lokal.
Unicorn 2.1.2 menyatakan lisensi GPL; beberapa file API memuat pemberitahuan
LGPL2 dan bagian QEMU/GLib memiliki pemberitahuan masing-masing. Salinan lisensi
utama tersedia di [GPL2](docs/licenses/UNICORN-COPYING.txt),
[LGPL2](docs/licenses/UNICORN-COPYING.LGPL2.txt) dan
[GLib](docs/licenses/UNICORN-COPYING_GLIB.txt). Source upstream tersedia di
[tag 2.1.2](https://github.com/unicorn-engine/unicorn/tree/2.1.2).
Pemberitahuan dan lisensi komponen upstream tetap berlaku saat distribusi.

Snapshot acuan, binary game dan library pihak ketiga tidak dimasukkan dalam
Git. APK final disediakan melalui Release sesuai permintaan pemilik proyek;
kunci, APK input, snapshot sumber dan dependency binary tetap lokal.
Tidak ada lisensi baru yang diterapkan atas karya pihak lain. Heroes Lore 5,
audio, grafik dan materi game tetap milik pemegang hak masing-masing.
