# Test5: canvas lebar, diagnostik dan lifecycle

Test4 telah menjalankan game di perangkat pengguna, Android 16 dengan Dimensity
9400+. Video/screenshot menampilkan gameplay dan cutscene, sementara telemetry
memperlihatkan draw call dan sentuhan berhasil. Tiga masalah yang dilaporkan
menjadi lingkup test5. Engine SO, VFS Korea dan konfigurasi mtouchdevice dari APK
asli tetap identik byte demi byte; tidak ada transfer resource acuan atau perubahan
format save.

## Tampilan dan input

Runner menunggu ukuran surface tersedia sebelum memanggil nativeInitDisplay.
Tinggi logis tetap 240 dan lebar adalah pembulatan genap ke atas dari
240 × lebar surface / tinggi surface, minimum 400. Untuk 2620x1280 hasilnya
492x240, sekitar 23% lebih lebar. Engine membuat framebuffer lebih lebar;
proyeksi asli diteruskan tanpa pemaksaan 800x480. Viewport dipasang dengan
skala seragam dan sentuhan dipetakan ke canvas yang sama.

Disassembly target menunjukkan Graphic::GetWidth/GetHalfWidth membaca ukuran
runtime dan createTextures memakai ukuran display/framebuffer. Tidak ada offset
source acuan yang dipakai untuk memperluas map. Lebar sesi dipertahankan ketika
surface berubah agar state dan buffer yang sedang dipakai tetap konsisten.

Overlay hijau dan tombol Salin status tersembunyi pada peluncuran biasa.
Pesan kegagalan tetap tampil. Diagnostik dapat diaktifkan oleh pengembang:

```powershell
adb shell am force-stop co.kr.eamobile.hl5.runner
adb shell am start -n co.kr.eamobile.hl5.runner/.MainActivity --ez debug true
```

Perintah force-stop hanya untuk peluncuran diagnostik baru, bukan prosedur
pengujian Home/resume. Log native tetap tersedia melalui logcat.

## Home, pemulihan grafis dan Exit

Sebelumnya setiap onSurfaceCreated mereset CPU dan menjalankan nativeStartApp.
Test5 mempertahankan guest yang sudah siap. Pause menjalankan nativePauseApp
target: pause game, hapus texture GL dan deinit layar. Resume menjalankan
nativeResumeApp: init layar, buat ulang texture dan resume game. Eksekusinya
berada di GL thread; resume ditunda sampai frame memiliki konteks GL yang aktif.
onSurfaceChanged tidak lagi menimpa ukuran guest dengan 800x480.

Android dapat menghilangkan konteks EGL meskipun preserve diminta. Resource GL
perlu dibuat kembali; lihat [dokumentasi Renderer Android](https://developer.android.com/reference/android/opengl/GLSurfaceView.Renderer).
Pemulihan RAM ini berlaku selama proses aplikasi masih hidup. Setelah Android
menghentikan proses, kelanjutan bergantung pada save game yang tersimpan.

AndroidService::exitApp target memanggil CletEntry.exitApp()V. Sebelumnya callback
ini tidak ditangani runner. Test5 menandai permintaan tersebut dan, setelah
eksekusi guest kembali, meminta Activity menjalankan finishAndRemoveTask sekali.
CPU tidak ditutup secara reentrant dari hook guest. Penutupan Activity yang
benar-benar finishing melepaskan runtime; rekreasi Activity tidak menutup CPU.

## Bukti dan pengujian berikutnya

- Statis/build: nativeInitDisplay, pause/resume, createTextures dan exitApp
  dicocokkan dengan symbol/hash fungsi target. Signature v2/v3 dan alignment
  ELF/ZIP 16 KB diperiksa; baseline assets identik.
- Otomatis: 28 tes lolos, termasuk aritmetika native display/touch yang dikompilasi
  dan dieksekusi ARM32, model JVM untuk diagnostik/Exit, serta regresi sebelumnya.
- Simulasi engine target: 492x240 melewati 300 tick, menggambar map/dialog dan
  mempertahankan pointer/state sebelum/sesudah pause/resume asli. JNI/libc/GLES
  model memiliki stub. New game dan skip dipanggil melalui metode ekspor;
  ini tidak membuktikan jalur input lengkap, driver Android atau stabilitas sesi.
  Perbandingan dengan 400x240 pada tick yang sama menunjukkan 36750 pixel area
  dunia cocok 100% setelah translasi 46 pixel, dengan skala objek tetap 1:1 dan
  tambahan lebar canvas 92 pixel. Laporan lokal: `work/multiscreen-comparison.json`.
- Perangkat: test4 berhasil render/input berdasarkan bukti pengguna. Test5 belum
  diuji di perangkat. Bandingkan map yang sama, ukuran sprite, dialog/HUD dan
  tombol di sisi kanan; uji Home/Recents berulang dan Exit dari menu game.

APK lokal: `dist/hl5-01.01.00-arm64-test5-wide.apk`. Instal sebagai update test4
agar sandbox/save runner dipertahankan. Audio, performa sesi panjang, seluruh
jenis map/menu dan save setelah proses dimatikan masih perlu diuji.
