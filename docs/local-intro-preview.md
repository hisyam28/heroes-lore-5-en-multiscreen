# Intro and performance development notes (1.0.1-1.0.4)

The final local-only preview was `dist/heroes-lore-5-v1.0.4.apk` (versionCode 1010104).
It adds a one-pixel dark outline behind the existing gold subtitle, using the
original inverse subtitle sprite as an underlay. Dilating that underlay keeps
the stroke visible beneath the additive gold animated pieces. Subtitle spelling,
position, dimensions, palettes and animation data remain identical to 1.0.3.

The pinned 1.0.3 APK is the baseline for this update. Only its manifest version,
VFS and VFS cache digest change; within the VFS, only title sprite 19's pixels
change. All ARM32/ARM64 performance libraries, DEX, icon, scripts and saves remain
unchanged. Seven relevant asset/APK/target-ARM-loader checks pass. Native-model
title previews are `work/intro-audit/native-title-outline-20.png` and adjacent
animation frames. This is model evidence, not a new physical-device test.
Build evidence: `work/intro-outline-build-report.json`; test log:
`work/v104-intro-tests.txt`. The earlier 88-test result below belongs to 1.0.3.

## Preserved 1.0.3 baseline

These previews were kept local at the owner's request. On 2026-10-29 the owner
authorized publication of the follow-up 1.0.5 release; see its [release notes](release-v1.0.5.md).

The combined APK is `dist/heroes-lore-5-v1.0.3.apk`, app label **Heroes Lore 5**,
versionName **1.0.3**, versionCode **1010103**, signed with the existing update key.
It retains minSdk9, targetSdk36, ARM32 and ARM64 hosts, and 16 KB library/ZIP
alignment. Android 2.3-4.4 continues through the original legacy ARM engine;
the new performance helpers apply to the modern API21+ runner.

## Title, subtitle and captions

- `HEROES LORE` now has warm gold faces, bronze edging and ivory highlights,
  matching the original gold crescent and Roman **V**. Those two original
  emblem sprites remain byte-identical. No additional Arabic 5 is drawn.
- `COVENANT OF DARKNESS` uses a readable single line centered directly under
  the wordmark. The owner explicitly preferred this closer placement, with
  some overlap over the background emblem. Its letters do not overlap the
  main wordmark. Five animated pieces and the complete subtitle remain present.
- Title sprite dimensions/palettes change only in the specifically allowed
  wordmark/subtitle slots. The title CIF changes only subtitle x/y coordinates;
  record counts, frame order, alpha, scaling, effects and animation timing stay intact.
  Coordinates were checked against this target's `LoadSprData` and `DrawSprite`.
- Opening captions retain their original indexed palettes and follow the
  original Hangul's row brightness instead of using a flat brightest stroke.
  The concluding oval caption retains its orange palette and background.
- The supplied launcher icon remains 192x192 without cropping, at the original
  drawable path and resource ID. The resource table is unchanged.
- Earlier English rating labels, `KR` keyboard indicator, trial label, and
  source/context-verified opening DAT translations remain included.

The gold wordmark uses the built-in imagegen tool. Its saved local input is
`work/intro-audit/heroes-lore-wordmark-gold.png`. Final prompt: preserve the exact
 two-line HEROES / LORE shapes and spelling; change only the material to warm
 gold, ivory-gold highlights, bronze bevels and a dark brown outline matching
 the original emblem; transparent background; no subtitle, number or objects.

## Separate performance overlay

`tools/build_intro_preview.py` first builds an art-only preview from the pinned
v1.0.0 APK. `tools/build_performance_preview.py` then compiles an isolated native
stage and replaces only the ARM32/ARM64 host libraries in that art preview.
All DEX, the original guest library, legacy libraries, input, save format,
gameplay scripts, audio, and translation dictionary remain byte-identical.

The modern runner adds three bounded optimizations:

1. Run the target's DES rounds as native code using its live original key,
   expansion/permutation tables and S-boxes. The encrypted save algorithm and
   file layout remain identical. Unsupported bit arrays use the original path.
2. Run verified RGB565 sprite blend loops as native code, preserving the
   target's lookup tables, transparency key, mirroring and distinct alpha
   rounding. Edge/clipping cases and gray-palette side effects keep the original path.
3. Commit dirty save descriptors once before closing each completed file,
   replacing the prior durability fence after every write. A failed fence is
   reported as an error; the descriptor still closes. Non-save descriptors and
   tracker exhaustion preserve immediate synchronization.

## Evidence and limits

All **88 local tests passed**. These include 48 random forward/reverse-key DES
comparisons with the actual target ARM routine, 224 transparent-sprite blend
comparisons, durability-fence/error/reuse checks, 34 original/revised sprite
loads through the target ARM loader, subtitle reconstruction and coordinate
checks, APK payload guards, and existing runtime/save/translation regressions.
The workspace check passes. Signature, update signer, manifest and alignment
checks also pass. An additional two-frame model comparison preserved framebuffer
bytes in both menu and early intro. The early-intro frame is mostly black with
the Skip prompt, so its instruction reduction is not used as evidence for
full cutscene performance. These counts also exclude native helper work.

The original target rendered the revised title at several animation frames
in a Python/Unicorn model. This demonstrates target sprite loading and drawing;
it does not run the compiled Android host, Android GLES or physical-phone timing.
The APK also installs as an update on the available API19 ARM32 emulator.
This does not test the new API21+ performance path.

Physical testing of **this version** on Galaxy A24/Android16 and Dimensity
9400+ remains pending. No FPS or freeze-elimination claim is made from static
checks or instruction counts. Install as an update without uninstalling to keep
the existing app data, then compare the same load/save and dialogue scenes.

Local evidence: `work/v103-full-tests.txt`,
`work/intro-english-assets/intro-translation-report.json`,
`work/intro-preview-build-report.json`, `work/performance-preview-build-report.json`,
`work/v103-cutscene-phases.json`,
and `work/intro-audit/native-title-20.png`. Inputs, key, images, generated assets,
builds and full reports remain local and ignored by Git.
