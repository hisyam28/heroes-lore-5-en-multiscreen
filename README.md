# Heroes Lore 5 — English Localization

Workspace terjemahan Heroes Lore 5 dari APK target yang akan diberikan.
Proyek ini memakai kajian source HL5 dan pengalaman proyek HL3 sebagai acuan.

**Status: menunggu APK target.** Belum ada APK hasil terjemahan atau build siap rilis.
Parser, alamat patch, dan kompatibilitas runtime akan ditentukan dari APK target.

## Mulai bekerja

Gunakan Python 3.10 atau lebih baru. Tool pemeriksaan awal hanya membutuhkan
standard library Python.

1. Simpan APK target di direktori `inputs/`.
2. Buat inventaris tanpa mengekstrak atau mengubah APK:

   ```powershell
   python -B tools/inspect_apk.py inputs/game.apk --out work/target-inventory.json
   ```

3. Cocokkan hasil inventaris dengan [profil target](config/target-profile.json)
   sebelum membuat parser, katalog, dan patch untuk versi tersebut.

Pemeriksaan workspace dan pengujian tooling:

```powershell
python -B tools/check_workspace.py
python -B -m unittest discover -s tests -v
```

## Struktur

| Direktori | Isi |
|---|---|
| `config/` | Status proyek dan profil APK yang telah diverifikasi |
| `tools/` | Inventaris APK dan pemeriksaan workspace |
| `translations/` | Katalog baru, glossary dan override per konteks |
| `docs/` | Kajian acuan, alur kerja dan catatan keputusan |
| `tests/` | Pengujian tooling yang dapat dijalankan tanpa APK game |
| `inputs/` | APK sumber lokal; diabaikan Git |
| `work/` | Inventaris lengkap, ekstraksi dan eksperimen lokal; diabaikan Git |
| `dist/` | APK hasil build lokal; diabaikan Git |
| `.local/` | Source acuan lengkap dan hasil kajian privat; diabaikan Git |

Source acuan HL5 yang disertakan dalam bahan kajian memiliki runner ARM32-on-ARM64
dan resource VFS yang sudah berbahasa Inggris. Katalog tersebut menjadi
translation memory setelah pencocokan teks sumber dan konteks, bukan pengganti
resource APK target. Lihat [kajian acuan](docs/reference-study.md) dan
[alur kerja](docs/workflow.md).

## Kredit referensi

- [sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en):
  acuan kajian tooling, format resource dan katalog terjemahan HL5.
- [hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en):
  pengalaman lokalisasi, penataan UI, perlindungan data gameplay dan validasi APK.

Nama game dan merek terkait dimiliki pemilik masing-masing. Ini adalah proyek
komunitas independen. Detail asal bahan dan komponen ada di [CREDITS.md](CREDITS.md).
