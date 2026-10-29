# Kegagalan pemuatan ELF pada test3

Pada 28 Oktober 2026 pengguna mengirim status perangkat:

```text
GLES Provider: libGLESv1_CM.so
State: -1.-1 (Pop: -1)
DrawArrays: 0 | TexBinds: 0
Status: FAIL ELF: target guest load/relocation failed
```

Kode test3 mencapai tahap ini setelah inisialisasi driver/context GLES dan CPU
Unicorn mengembalikan sukses. Loader ELF berhenti sebelum pemanggilan kernel,
display dan start app guest. Penghitung Frame #1140 menghitung callback Java;
ia tidak menunjukkan 1140 frame game yang berhasil dijalankan. Menunggu lebih
lama tidak melanjutkan boot yang telah gagal.

## Kondisi penolakan yang ditemukan

Binary target dengan fingerprint pada profil memiliki dua relokasi ABS32 untuk
simbol yang belum didefinisikan dan bertipe weak:

| Offset target | Symbol | Binding | Addend |
|---|---|---|---|
| `0x14fcb4` | `__cxa_call_unexpected` | STB_WEAK / SHN_UNDEF | 0 |
| `0x14fdec` | `__gnu_Unwind_Find_exidx` | STB_WEAK / SHN_UNDEF | 0 |

Penanganan ABS32 yang ditambahkan pada loader sebelumnya mengembalikan false
untuk setiap SHN_UNDEF. Kondisi tersebut menolak kedua weak reference yang sah
ini dan cocok dengan kegagalan pada tahap ELF yang dilaporkan perangkat.

ABI ARM mengizinkan weak reference tidak teresolusi; nilainya nol untuk relokasi
absolut. ABS32 menggunakan operasi `(S + A) | T`. Dengan addend nol, dua lokasi
target ini harus tetap bernilai nol tanpa penambahan load bias.
Lihat [ABI ELF ARM, weak references dan relocation](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst#5511-weak-references).

## Perbaikan test4

- Weak reference yang belum tersedia diselesaikan sebagai nol.
- Symbol terdefinisi menggunakan load bias; SHN_ABS tidak ditambah bias.
- Import kuat yang memiliki hook menggunakan alamat trampoline yang tersedia.
  Import kuat ABS32 yang tidak tersedia tetap ditolak dengan nama dan offset.
- Symbol nol, addend, arithmetic ARM32 dan penanda Thumb ditangani tersendiri.
- Pesan kesalahan membedakan file tidak terbuka, header, pemetaan memory,
  addend dan resolusi symbol; status perangkat menampilkan alasan loader itu.
- Engine SO, VFS dan konfigurasi touch tetap identik dengan APK baseline.

Implementasi aritmetika berada di `tools/runtime/arm32_relocations.h` dan disalin
oleh tahap persiapan runner. Ini merupakan kode loader host, bukan patch terhadap
binary engine game.

## Bukti pengujian

Tujuh tes mengompilasi helper C++ yang sama menjadi ARM32, lalu menjalankannya
dalam Unicorn. Cakupan meliputi kedua weak import aktual, addend nonnol, symbol
terdefinisi/absolut, hook host, penolakan import kuat, symbol nol, Thumb dan
overflow 32-bit. Seluruh 22 tes workspace lulus melalui virtual environment lokal.

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

Tes relokasi opsional memerlukan Android NDK lokal dan paket Python `unicorn`.
Tanpa keduanya tes tersebut dilewati; pemeriksaan workspace tetap hanya memakai
standard library. Pengujian ini tidak menjalankan Activity Android atau seluruh
loader di ponsel.

Hasil berikutnya: `dist/hl5-01.01.00-arm64-test4-elf-fix.apk`, versionCode
1010004, label `Heroes Lore 5 Target Test 4`. Package dan kunci uji sama untuk
update dari test3. Keberhasilan melewati loader dan boot di perangkat masih perlu
dikonfirmasi. Perubahan kamera/multiscreen belum diterapkan dalam perbaikan ini.
