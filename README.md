# Heroes Lore 5 English Multiscreen

An English localization of Heroes Lore 5 with multiscreen support and Android ARM32/ARM64 runtime adaptations. The original **01.01.00** APK remains the game baseline. **[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en)** provides the technical and translation reference, with changes verified against the target binary.

**Release: v1.0.0** | App name: **Heroes Lore 5 English**

[Download APK v1.0.0](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/download/v1.0.0/heroes-lore-5-english-multiscreen-v1.0.0.apk) | [Releases](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest) | [Credits](CREDITS.md)

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
| Version / versionCode | **1.0.0** / **1010100** |
| Game baseline | **01.01.00** |
| APK | Universal ARM, **22,787,239 bytes** (about 23 MB) |

The package minimum is the configured installation threshold, not certification for every device. Android 2.3 has not been tested on physical hardware. Installation has been checked on ARM32 Android 4.0.2 and 4.4 emulators; this does not verify all legacy gameplay. No x86/x86_64 host libraries are included. Minimum RAM and CPU requirements have not been established through device benchmarks.

## APK features

- **Multiscreen on the modern runner.** The visible world area expands with the screen aspect ratio while preserving object proportions. Viewport and touch coordinates follow the canvas. Fullscreen uses the available display cutout area and hides system bars. The expanded viewport applies to Android 5+; the legacy native path retains the original engine's display behavior.
- **English localization.** **13,825 Hangul text fields** have been translated across **57 DAT tables and 258 SCN scripts** that were inspected. **72 existing English labels** have been shortened to fit their panels. Main menu capitalization is consistent, stat labels are compact, and modern dialogue follows the available text box width.
- **Quests from older saves.** On the modern runner, Korean titles, categories, and descriptions that exactly match the source dictionary are replaced when displayed. Descriptions are translated before line splitting and scrolling. Save files and quest status/progress are not rewritten; starting a new game is not required for this display fix.
- **Lifecycle and Exit handling.** Fullscreen is applied after the view is ready. Returning from Home uses pause/resume, and the in-game Exit action closes the task on the modern runner.
- **Runtime optimizations.** Freed guest memory can be reused. Asset preparation runs in the background, and the cache uses fingerprints. Framebuffer copying, RGB565 raster operations, palette effects, and font metrics are accelerated, with the original functions handling unsupported cases.
- **Clean presentation.** The green diagnostic overlay and copy-status button are hidden during normal launch. The release APK does not enable Android's `debuggable` flag.
- **Preserved game data.** The original engine library, gameplay metadata, script opcodes, save format, input configuration, audio, and artwork are retained rather than replaced with reference-version assets. Text changes and host adaptations are tracked separately.

Rating artwork on the legacy Android path remains in Korean. The text-field coverage above does not mean every bitmap has been translated. The display bridge for older saves applies to the modern runner; the legacy path does not use that bridge. Old online services are not claimed to have been restored.

## Installation and updates

1. Download the APK from [GitHub Releases](https://github.com/hisyam28/heroes-lore-5-en-multiscreen/releases/latest).
2. Allow installation from your downloader or file manager if Android requests it.
3. If you use an earlier runner build, **install this as an update without uninstalling** to retain app data. The package and update signer are unchanged.
4. Continue your save and check its existing quest panels. Display substitutions do not change game progress.

APKs with a different package or signer may not support the same update path. Do not remove an app containing your saves just to try an installation.

APK v1.0.0 SHA-256:

```text
dfc424bbabc19a45512857250153af175143a130fcd429131aed8053357618ed
```

## Validation

**78 local tests passed** for this release, including the older-save quest description regression and final APK checks. Workspace and Git whitespace checks also passed.

Earlier builds received device testing and feedback on Android 16 with Dimensity 9400+ and Samsung Galaxy A24/Helio G99 hardware, with reported display and performance improvements. The last review accepted the general results while identifying Korean descriptions in older saves as the remaining issue. Release 1.0.0 adds that description-path fix; its final APK had not yet been tested directly on those phones when published.

- Local tests protect VFS structure, metadata/opcodes, placeholders/color controls, input, legacy/modern DEX separation, heap behavior, viewport geometry, and unchanged assets.
- The regression executes the original ARM **QuestMgr → DrawTextLine → DrawText** path with a Korean description and multiple scroll positions, then checks that quest data bytes remain unchanged.
- Font helpers were compared against the target ARM functions in **900 cases**, and palette helpers in **384 combinations**.
- In a three-frame intro sample, the palette helper reduced guest instructions from **1,388,879 to 561,635 (59.56%)**, with an identical framebuffer. The sampled menu/map phases showed no instruction reduction from this palette helper. **This is not an Android FPS improvement percentage.**
- Build checks cover v1/v2/v3 signatures, the update signer, a STORED resource table with 4-byte alignment, 16 KB host alignment, and package name/version information.

Smooth performance on every phone or in every scene is not guaranteed. Audio, long sessions, repeated portal transitions, saves, and UI variations still require device validation. See the [v1.0.0 release notes](docs/release-v1.0.0.md) for details.

## Source and local builds

This repository contains tooling, target profiles, translation catalogs/overrides, tests, documentation, and the runner patch. **Input APKs, game libraries, dependency binaries, reference snapshots, signing keys, and build outputs are excluded from Git.** The final APK is distributed as a GitHub Release asset.

Local builds require the baseline APK and reference ZIP matching the profile hashes, Python 3.10+, JDK17, Android SDK API36/API9, and the recorded Build Tools and NDK versions. Additional ARM execution tests use Python Unicorn. Toolchains, inputs, and staging directories remain local. See the [release build instructions](docs/release-v1.0.0.md) and [target profile](config/target-profile.json).

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
