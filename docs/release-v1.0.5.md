# Heroes Lore 5 v1.0.5

This release brings the accepted English intro/title artwork and the local
performance improvements to the public build. The application is named
**Heroes Lore 5**, without an English or Test suffix. The home-screen wordmark
is **HEROES LORE**, retaining the original Roman **V**, with **COVENANT OF
DARKNESS** directly below it in gold with a dark outline.

[Download Heroes Lore 5 v1.0.5](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/download/v1.0.5/heroes-lore-5-v1.0.5.apk)

## Changes since the public v1.0.0 release

- English opening captions and selected rating/trial bitmap labels, checked
  against the original target assets. The supplied launcher icon is included.
- Gold title lettering with bronze edging and ivory highlights; the original
  V and crescent emblem are retained. The full subtitle has a one-pixel dark
  underlay outline, keeping it readable over the background emblem.
- Subtitle animation pieces retain their sequence, alpha and timing. Only
  the verified subtitle coordinates and scoped artwork were adjusted.
- Native DES round acceleration on the modern runner uses the original live
  key and target tables. Save encryption and the file format are unchanged.
- Dirty save files are synchronized once before close, instead of after every
  write. Failed synchronization is reported, and descriptors still close.
- Native RGB565 sprite blending preserves transparency, mirroring, lookup
  tables and the original alpha rounding.
- **New in 1.0.5:** normal-orientation sprites partially clipped by the screen
  or clip rectangle can use the accelerated path. This reduces interpreter
  work during camera movement. Mirrored edge cases, rotations and unsupported
  effects retain the original target implementation.

Existing multiscreen, fullscreen/touch mapping, pause/resume, Exit handling,
guest-memory reuse, English dialogue wrapping and older-save quest text fixes
remain included. No gameplay script, input configuration, save progress or
original guest engine library was replaced.

## Specifications

| Item | Value |
|---|---|
| App / package | Heroes Lore 5 / `co.kr.eamobile.hl5.runner` |
| Version / versionCode | 1.0.5 / 1010105 |
| Package minimum | Android 2.3 Gingerbread / API9 |
| Legacy path | Original ARM engine on API9-20, including Android 4 |
| Modern path | ARM32/ARM64 runner on Android 5.0+ / API21+ |
| Target SDK | 36 / Android 16 |
| Graphics | OpenGL ES 1.1 or compatible GLES1 provider |
| Modern display | Adaptive landscape viewport with proportional objects |
| Modern host alignment | 16 KB ELF and ZIP alignment |
| APK size | 22,860,967 bytes |

The manifest minimum is not certification for every device. Android 2.3 has
not been tested on physical hardware, and minimum RAM/CPU requirements have
not been established. The legacy path retains its original display behavior.
No x86 host is included, and old online services are not claimed to be restored.

## Validation and remaining performance limits

All **89 local tests passed**, including 96 original-ARM edge-rendering
comparisons, 224 sprite-blend cases, 48 forward/reverse-key DES comparisons,
subtitle/target-loader checks, older-save quest rendering, heap/viewport guards,
and checks of the final release package. Signatures, the existing update signer,
resource-table storage/alignment and both host architectures were verified.
Workspace and Git whitespace checks passed before publication.

The owner accepted the 1.0.4 presentation but reported residual slow/stuttering
movement in the opening cutscene of a new game. Version 1.0.5 addresses an
additional verified renderer slow path. **It has not yet been timed on the
Galaxy A24/Helio G99 or Dimensity 9400+ phones.** No FPS increase or complete
elimination of cutscene stutter is claimed. The modern runner interprets the
original ARM32 engine, so old native-device performance does not predict its
speed on Android 16. Early sparse-frame model counts are not treated as full
moving-cutscene benchmarks.

## Update and checksum

Install as an update **without uninstalling** to retain existing app data.
The package and update signer are unchanged from previous runner builds.

```text
288dbddf95fff05dabde571e7081a7eab190a251f784861c3e6267369543affd  heroes-lore-5-v1.0.5.apk
```

The Release also provides a checksum file. Metadata is recorded in
[config/release.json](../config/release.json); the old release metadata remains
in [config/release-v1.0.0.json](../config/release-v1.0.0.json).

## Build and preservation boundaries

The immutable input APK is 01.01.00, identified by the
[target profile](../config/target-profile.json). The intro asset builder uses
the pinned public v1.0.0 APK and locally supplied artwork. The native overlay is
prepared from the fingerprinted reference ZIP and the audited runner patch.
It is compiled for both host ABIs, then repacked into the art APK with
`tools/build_performance_preview.py`. The artwork and runtime stages are separate.

Compared with accepted local 1.0.4, this release changes only the manifest
version and the two host libraries. Its VFS, icon, DEX, original engine, input,
audio and gameplay scripts are byte-identical to that accepted preview.
Reproducing the artwork stage requires the local wordmark and supplied icon;
the repository alone is not a complete game or a self-contained game build.
Inputs, signing keys, reference snapshots, dependencies and outputs remain
excluded from Git. Only the final APK and checksum are uploaded as Release assets.

## Credits

The main technical and English translation reference is
**[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)**.
Additional credits: [hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en),
[Unicorn Engine](https://github.com/unicorn-engine/unicorn), QEMU and the
original game's rights holders. Full acknowledgments and component notices
are in [CREDITS.md](../CREDITS.md).
