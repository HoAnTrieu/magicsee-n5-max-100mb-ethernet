# Release verification — 2026-10-05

These checks run locally before packaging; GitHub CI has not run because the repository has not been published.

| Check | Result |
|---|---|
| Tested binary SHA-256 | Unchanged: 03c8877650e9b7d7feda656db775dcd591ba20f6528665c2367537c8888fbffd |
| Real dtc rebuild | DTC 1.7.0; baseline and patched compile successfully |
| Full-tree semantic comparison | 542 node paths preserved; six allowed Ethernet property changes |
| Inherited warnings | 285 baseline / 285 patched; no new normalized warnings |
| Installation/report tests | 12 pass; disposable boot fixtures only |
| Patch reproduction | Applying supplied patch reproduces src DTS byte for byte |
| Local Markdown links | All resolve |
| Public content | Known private network identifiers and local workspace paths absent |
| ZIP | CRC valid, one source root, no caches/build/raw debug tarballs; tested DTB hash retained |

Installer tests cover rescue preservation, backup conflicts, wrong kernel/baseline, multiple FDT lines, extlinux, target symlink/hardlink, changed config, failed DTB writes, CRLF and commented FDT examples. These software checks do not replace the hardware evidence in VALIDATION.md.

Not run: dtbs_check against the exact ophub source, physical tests on other boards/kernels, long-term stress or a fresh physical install of the final Python installer. The DTB itself was tested by the project owner with the earlier installer; the final Python installer was verified using filesystem fixtures.
