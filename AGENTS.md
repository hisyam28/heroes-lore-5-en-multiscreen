# Petunjuk kerja

- Baca `config/project.json`, `config/target-profile.json` dan `docs/workflow.md`
  sebelum mengubah pipeline.
- APK target belum tersedia pada tahap awal. Jangan menyebut build, port,
  terjemahan, atau kompatibilitas perangkat sudah selesai tanpa bukti.
- APK target adalah baseline. Simpan input tetap utuh dan tulis output ke
  `work/` atau `dist/`.
- Perubahan terjemahan harus menjaga metadata, opcode script, format save,
  placeholder dan kode kontrol yang tidak dimaksudkan untuk diubah.
- Jangan memakai offset, batas buffer atau struktur dari source acuan tanpa
  memverifikasinya terhadap binary target. Tolak profil yang tidak cocok.
- Pindahkan terjemahan berdasarkan teks sumber beserta konteks. Indeks baris
  atau slot pada versi lama tidak cukup sebagai bukti kecocokan.
- Pisahkan perubahan UI/input/runtime dari penggantian teks agar masing-masing
  dapat dibandingkan dan diuji. Pertahankan konfigurasi input bila lingkupnya
  hanya terjemahan.
- Jalankan `python -B tools/check_workspace.py` dan pengujian yang relevan.
  Bedakan bukti statis, simulasi, dan pengujian perangkat dalam laporan.
- Input APK, binary game, snapshot acuan, kunci dan hasil build tetap lokal.
  Jangan menambahkan direktori yang diabaikan Git secara paksa.
