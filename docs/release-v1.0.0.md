# Heroes Lore 5 English Multiscreen v1.0.0

The first public release at `hisyam28/heroes-lore-5-en-multiscreen` uses the app
name **Heroes Lore 5 English**, versionName **1.0.0**, versionCode **1010100**,
and the same runner package as earlier builds. The launcher label, version, and
APK filename no longer include the word test. Android's `debuggable` flag is
disabled, and the update signer is retained to preserve the existing update path.

## Older-save quest description fix

The user's screenshot showed an English `Returning Home` title, category, and
location, while the description remained Korean. Target binary instructions
show that `QuestMgr::DrawQuestString` passes the description buffer at `this+28`
to `BFont::DrawTextLine`, unlike the title path that was already covered. This
call occurs at target address `0xce3e8`. Both function fingerprints were added
to the profile that must match the target APK.

The display bridge now handles `DrawTextLine`: text is argument 6 and width is
argument 4. An exact dictionary match is copied to scratch memory before the
original function calculates line breaks and selects the scrolled page. The
quest buffer, status/progress, save files, and save format are unchanged. This
path applies to the modern API21+ runner; API9–20 retains the original native
engine implementation.

The regression executes the original ARM quest and pagination instructions,
stubbing only libc and the final pixel draw. Two scroll positions produce
different English text slices while the entire QuestMgr buffer stays identical.
This catches the description path missed by the earlier title-lookup test.

## Package contents and compatibility limits

- Minimum manifest Android 2.3/API9; target SDK36/Android16.
- Original native ARM engine on API9–20; ARM32/ARM64 runner on API21+.
- Multiscreen, touch/fullscreen adjustments, lifecycle handling, heap/raster/
  palette/font optimizations, and the older-text bridge apply to the modern path.
- English assets cover 13,825 Hangul fields and 72 existing English label
  corrections. Script opcodes, gameplay metadata, input, fonts, audio/artwork,
  and the original engine library are retained.
- API14/API19 emulator installation was checked on earlier builds. Android2.3
  and all legacy gameplay have not been verified on physical devices.
- Legacy rating artwork remains Korean. Old online services are not claimed
  to have been restored.
- The user accepted the general results of the previous build except for
  older-save descriptions. The final fix has static and ARM execution evidence;
  final APK testing on phones, FPS, audio, and long sessions remain separate.

See the [README](../README.md) for specifications, features, and update instructions.

## Local build

Prepare inputs and dependencies locally using the fingerprints in the
[target profile](../config/target-profile.json). Do not replace the target with
reference binaries. The recorded toolchain uses JDK17, NDK r28c, Android SDK36,
Build Tools36, and the official API9 android.jar for the legacy launcher.

1. Compile assets with `tools/translate_assets.py --reference <reference-zip>
   --out work/english-release`.
2. Create a new stage with `tools/prepare_android_runner.py --reference
   <reference-zip> --out work/runner-release --localization-vfs
   work/english-release/data.vfs.mp3`.
3. Run the builder with your local toolchain paths:

   ```powershell
   python -B tools/build_android_test.py --runner work/runner-release/app/src/main --ndk <ndk> --jdk <jdk17> --build-tools <build-tools> --android-jar <android36.jar> --include-legacy --legacy-android-jar <android9.jar> --english-vfs work/english-release/data.vfs.mp3 --version-code 1010100 --version-name 1.0.0 --application-label "Heroes Lore 5 English" --release --out dist/heroes-lore-5-english-multiscreen-v1.0.0.apk
   python -B tools/check_workspace.py
   python -B -m unittest discover -s tests -v
   ```

`build_android_test.py` is the historical tooling name, not the release APK label.
The builder checks stage hashes, baseline identity, dictionary/VFS consistency,
DEX separation, resource/input/engine preservation, ABIs, signatures, and
alignment. Build outputs and signing keys stay local. The final APK is uploaded
as a Release asset rather than force-added to Git, as explicitly requested by
the project owner.

Release metadata and checksums are in [config/release.json](../config/release.json).
All **78 local tests passed** against the final package, including the release
name/version, disabled debug flag, quest hook in both host libraries, and
unchanged APK payloads except for the manifest and the two intentionally updated
host libraries. The final certificate matches the previous update signer.

## Credits

The main technical and English translation reference is
**[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)**.
Additional acknowledgments and upstream component notices are in
[CREDITS.md](../CREDITS.md).
