# Provenance and attribution

## Inherited Device Tree

The reference DTS/DTB was supplied from the tested ophub Armbian installation under the filename `meson-sm1-x96-max-plus-100m.dtb`. Its SHA-256 is recorded in `project.json`. The patched source is derived from that exact decompiled baseline; the six changed Ethernet properties and modification date (2026-10-05) are documented in `patches/ethernet-only.patch` and `docs/TECHNICAL_ANALYSIS.md`.

The underlying Amlogic Linux Device Tree work originates from upstream Linux and the ophub distribution ecosystem. Decompilation does not preserve source comments, include topology or copyright/SPDX headers. The exact ophub source commit, preferred upstream source hierarchy and every inherited copyright notice could not be recovered from the debug archive. This project does not claim authorship of the inherited board/SoC definitions, or claim that the decompiled standalone DTS is the canonical upstream source.

Inherited content retains its original terms. Linux DTS files commonly permit GPL-2.0 or MIT, but the exact inherited file's license identifier is not asserted without its source. The supplied LICENSE is GNU GPL v2; it is the license selected for new scripts, tests, documentation and Ethernet changes in this project. It does not replace any applicable inherited notice. Source and build instructions accompany the distributed DTB.

Before proposing upstream inclusion, recover the matching ophub source hierarchy, preserve its notices, and express the change with labels/includes under its existing license. Provenance limitations are explicit here so future maintainers can resolve them rather than invent attribution.

## References and hardware evidence

CoreELEC, upstream Linux, ophub and forum reports informed the analysis. No vendor/CoreELEC DTB or kernel binary is distributed or copied into the fix. Forum findings are paraphrased with source links; no forum images are bundled. [Sources](docs/SOURCES.md) distinguishes accessible primary references from historical research with access limitations.

Hardware logs were supplied by the project owner on 2026-10-05. The public excerpts remove network and storage identifiers. The release does not contain the owner's original debug archives.
