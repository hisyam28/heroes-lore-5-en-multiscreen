# Heroes Lore 5

An English localization of Heroes Lore 5 with multiscreen support and Android ARM32/ARM64 runtime adaptations. The original **01.01.00** APK remains the game baseline. **[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)** provides the technical and translation reference, with changes verified against the target binary.

**Release: v1.0.5** | App name: **Heroes Lore 5** | Covenant of Darkness

[Download APK v1.0.5](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/download/v1.0.5/heroes-lore-5-v1.0.5.apk) | [Releases](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest) | [Credits](CREDITS.md)

## Specifications and compatibility

| Component | Details |
|---|---|
| Package minimum | Android **2.3 Gingerbread / API9**, including Android 4 |
| Legacy Android path | Android 2.3–4.4 / API9–20: original native ARM engine |
| Modern Android path | Android 5.0+ / API21+: ARM32 or ARM64 runner |
| Architectures | `armeabi` for the legacy engine; `armeabi-v7a` and `arm64-v8a` on compatible devices |
| Target SDK | **36**, Android **16** |
| Graphics | OpenGL ES **1.1** / a compatible GLES1 provider |
| Orientation | Landscape |
| Modern display | Canvas adapts to the screen aspect ratio while preserving object proportions |
| Modern host alignment | **16 KB** ELF and ZIP alignment |
| Package | `co.kr.eamobile.hl5.runner` |
| Version / versionCode | **1.0.5** / **1010105** |
| Game baseline | **01.01.00** |
| APK | Universal ARM, **22,860,967 bytes** (about 23 MB) |

The package minimum is the configured installation threshold, not certification for every device. Android 2.3 has not been tested on physical hardware. Installation has been checked on ARM32 Android 4.0.2 and 4.4 emulators; this does not verify all legacy gameplay. No x86/x86_64 host libraries are included. Minimum RAM and CPU requirements have not been established through device benchmarks.

## APK features

- **Multiscreen on the modern runner.** The visible world area expands with the screen aspect ratio while preserving object proportions. Viewport and touch coordinates follow the canvas. Fullscreen uses the available display cutout area and hides system bars. The expanded viewport applies to Android 5+; the legacy native path retains the original engine's display behavior.
- **English localization.** **13,825 Hangul text fields** have been translated across **57 DAT tables and 258 SCN scripts** that were inspected. **72 existing English labels** have been shortened to fit their panels. Main menu capitalization is consistent, stat labels are compact, and modern dialogue follows the available text box width.
- **Quests from older saves.** On the modern runner, Korean titles, categories, and descriptions that exactly match the source dictionary are replaced when displayed. Descriptions are translated before line splitting and scrolling. Save files and quest status/progress are not rewritten; starting a new game is not required for this display fix.
- **Lifecycle and Exit handling.** Fullscreen is applied after the view is ready. Returning from Home uses pause/resume, and the in-game Exit action closes the task on the modern runner.
- **Runtime optimizations.** Guest memory can be reused; asset preparation and cache fingerprints avoid unnecessary work. Native helpers accelerate framebuffer/raster operations, sprite blending, normal-orientation edge clipping, palette effects, font metrics and original DES save rounds. Saves synchronize once before close. Unsupported cases retain the original implementation.
- **English intro and title artwork.** Opening captions and selected rating/trial bitmap labels are translated. The gold HEROES LORE wordmark retains the original Roman V and crescent emblem. COVENANT OF DARKNESS sits directly below the lettering with a dark outline. The supplied launcher icon is included.
- **Clean presentation.** The green diagnostic overlay and copy-status button are hidden during normal launch. The release APK does not enable Android's `debuggable` flag.
- **Preserved game data.** The original engine library, gameplay metadata, script opcodes, save format, input configuration, and audio are retained. Selected intro/title/rating artwork changes are explicitly scoped; reference-version game assets are not substituted. Text changes and host adaptations are tracked separately.

Selected intro/rating artwork now includes English text, but text-field coverage does not certify every bitmap or every legacy UI screen. The display bridge for older saves applies to the modern runner; the legacy path does not use that bridge. Old online services are not claimed to have been restored.

## Installation and updates

1. Download the APK from [GitHub Releases](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest).
2. Allow installation from your downloader or file manager if Android requests it.
3. If you use an earlier runner build, **install this as an update without uninstalling** to retain app data. The package and update signer are unchanged.
4. Continue your save and check its existing quest panels. Display substitutions do not change game progress.

APKs with a different package or signer may not support the same update path. Do not remove an app containing your saves just to try an installation.

APK v1.0.5 SHA-256:

```text
288dbddf95fff05dabde571e7081a7eab190a251f784861c3e6267369543affd
```

## Validation

**89 local tests passed** for this release, including final APK payload/version checks. Workspace and Git whitespace checks also passed.

- The original ARM renderer and optimized helpers produced identical pixels in **96 edge-clipping cases** and **224 sprite-blending cases**. Original DES output matched **48 forward/reverse-key cases**. Subtitle geometry, animation and sprite loading were also checked against the target.
- Existing tests protect metadata/opcodes, placeholders/color controls, input, older-save quest rendering, legacy/modern DEX separation, heap behavior and viewport geometry. Font and palette helpers retain their earlier target-ARM comparisons.
- Build checks cover v1/v2/v3 signatures, the unchanged update signer, a STORED and aligned resource table, and 16 KB alignment for both modern host ABIs.

The owner accepted the 1.0.4 presentation but still reported slight slowness/stutter in the new-game opening cutscene. Version 1.0.5 adds verified acceleration for partially clipped sprites during camera movement. **The final 1.0.5 APK has not yet been benchmarked on Galaxy A24/Helio G99 or Dimensity 9400+ hardware.** No complete stutter fix or FPS increase is claimed. The modern runner executes the original ARM32 engine through Unicorn; the game's smoothness on old native Android devices does not establish its performance on the modern path.

Android 4.0.2/4.4 emulator installation and earlier Android 16 phone feedback are distinct from final-build gameplay validation. Audio, long sessions, repeated portal transitions and all scene variations still need device testing. See the [v1.0.5 release notes](docs/release-v1.0.5.md) for changes and limits.

## Source and local builds

This repository contains tooling, target profiles, translation catalogs/overrides, tests, documentation, and the runner patch. **Input APKs, game libraries, dependency binaries, reference snapshots, signing keys, and build outputs are excluded from Git.** The final APK is distributed as a GitHub Release asset.

Local builds require the baseline APK and reference ZIP matching the profile hashes, Python 3.10+, JDK17, Android SDK API36/API9, and the recorded Build Tools and NDK versions. Additional ARM execution tests use Python Unicorn. Toolchains, inputs, and staging directories remain local. See the [release build notes](docs/release-v1.0.5.md) and [target profile](config/target-profile.json).

```powershell
python -B tools/check_workspace.py
python -B -m unittest discover -s tests -v
```

| Directory | Contents |
|---|---|
| `config/` | Target, localization, and release metadata |
| `tools/` | Parsers, validators, text compiler, staging/overlay, and APK builder |
| `translations/` | Catalog, glossary, and source/context-based overrides |
| `tests/` | Tooling tests, models, and target ARM comparisons |
| `docs/` | References, workflow, diagnoses, evidence, and validation limits |
| `inputs/`, `work/`, `dist/`, `.local/` | Local data and outputs excluded from Git |

Development history: [reference study](docs/reference-study.md), [Android](docs/android-port.md), [multiscreen](docs/multiscreen-target.md), [stability](docs/test8-stability-startup.md), [legacy support](docs/test9-legacy-android.md), [packaging](docs/test10-install-packaging.md), [translation](docs/english-assets.md), and [layout/performance](docs/test12-layout-performance.md).

## Credits

- **[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)** — the main reference for HL5 reverse engineering, the runner, and English translations.
- **[hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en)** — HL3 localization experience.
- **[Unicorn Engine](https://github.com/unicorn-engine/unicorn)** and QEMU contributors — the foundation for ARM guest execution.
- Heroes Lore 5 and its game materials remain the work of their respective rights holders. This project claims no ownership or official affiliation.

Target adaptations, multiscreen work, and this release are maintained at **hisyam28/heroes-lore-5-en-multiscreen**. See [CREDITS.md](CREDITS.md) for attribution and third-party component details.
