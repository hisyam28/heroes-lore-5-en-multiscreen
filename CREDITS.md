# Credits and references

This project builds on the HL5 source ZIP supplied by the workspace owner and
experience from the HL3 localization project. Its English catalog uses source
text and translations from the HL5 reference, matched against the target context,
with local corrections to control codes, spelling, and label length. The reference
resource archive, script opcodes, and game library were not substituted for the
target game's runtime.

- **Main HL5 reference: [sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en).**
  Credit for reverse-engineering research, the runner implementation, resource
  parsers, and English translation memory. These contributions are not claimed
  as new work by this project. Adaptations for the 01.01.00 binary, multiscreen,
  stability, performance, layout, and older-save quest descriptions are
  documented separately.
- **HL3 reference: [hisyam28/heroes-lore-3-en](https://github.com/hisyam28/heroes-lore-3-en).**
  Reference experience for game localization and UI layout.

The supplied reference ZIP has no Git metadata, so its exact upstream commit has
not been established. Input hashes and the full reference snapshot are retained
locally.

## Unicorn and other upstream components

The reference runner uses [Unicorn Engine](https://github.com/unicorn-engine/unicorn)
for CPU execution. The ARM64 library comes from the fingerprinted reference ZIP.
The ARM32 dependency was built from official Unicorn 2.1.2 source; its URL,
fingerprint, and build steps are recorded in `tools/build_arm32_dependency.py`
and the target profile. The full source and compiled dependencies remain local.

Unicorn 2.1.2 declares the GPL license. Some API files carry LGPL2 notices, and
QEMU/GLib components retain their own notices. Copies of the principal license
texts are included here:

- [GPL2](docs/licenses/UNICORN-COPYING.txt)
- [LGPL2](docs/licenses/UNICORN-COPYING.LGPL2.txt)
- [GLib](docs/licenses/UNICORN-COPYING_GLIB.txt)

Upstream source is available at [Unicorn tag 2.1.2](https://github.com/unicorn-engine/unicorn/tree/2.1.2).
Upstream component notices and licenses continue to apply to distribution.

## Project maintenance and game ownership

Target adaptations, multiscreen work, and this release are maintained at
[hisyam28/heroes-lore-5-en-multiscreen](https://github.com/hisyam28/heroes-lore-5-en-multiscreen).

Reference snapshots, game binaries, and third-party libraries are excluded from
Git. The final APK is provided through GitHub Releases at the project owner's
request. Signing keys, input APKs, source snapshots, and dependency binaries
remain local.

No new license is imposed on third-party work. Heroes Lore 5, its audio,
graphics, and game materials remain the property of their respective rights
holders. This is an independent community project with no claimed official
affiliation.
