# Sources and research boundaries

Research and hardware test date: **2026-10-05**. Rechecked during release packaging where noted. Primary source links are provided for maintainers; historical forum findings are not a substitute for the supplied board logs.

## Primary references

| Source | What it supports | Access / limitation |
|---|---|---|
| [ophub issue #2564](https://github.com/ophub/amlogic-s9xxx-armbian/issues/2564) | Another N5 Max S905X3 report with capability mask 6280, attach -22 and boot failures from changing entire DTBs | Rechecked in packaging; issue body accessible, no confirmed fix shown in retrieved page |
| [CoreELEC legacy DT table](https://coreelec.org/legacy/dtb/) | N5 Max / S905X3 / 4G maps to sm1_s905x3_4g | Rechecked; mapping does not reveal GPIO/PHY topology for this board |
| [Amlogic G12A MDIO mux binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/amlogic,g12a-mdio-mux.yaml) | Mux between embedded 10/100 PHY and external MDIO, branch/address example | Rechecked upstream document; not asserted to be the exact ophub build's schema |
| [Amlogic DWMAC binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/amlogic,meson-dwmac.yaml) | MAC clock roles and RGMII delay semantics; TX delay is ignored in RMII | Rechecked upstream document; exact ophub source commit unavailable |
| [Ethernet PHY binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/ethernet-phy.yaml) | Generic PHY properties | Reference retained from earlier analysis |
| [Synopsys DWMAC binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/snps,dwmac.yaml) | Generic MAC properties | Reference retained from earlier analysis |
| [SEI610 Linux DTS](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/amlogic/meson-sm1-sei610.dts) | SM1 internal PHY/RMII topology as a hardware pattern | Earlier analysis reference; v6.12 retrieval blocked during packaging; no binary copied |
| [MDIO mux implementation](https://codebrowser.dev/linux/linux/drivers/net/mdio/mdio-mux.c.html) | Available child enumeration behavior | Earlier reference displayed v6.19-rc8, not the exact 6.12.111-ophub code |
| [ophub distribution repository](https://github.com/ophub/amlogic-s9xxx-armbian) | Distribution context and maintenance entry point | Does not uniquely identify the original binary's source commit |

## Direct device-owner reports

| Source | Finding from earlier analysis | Limitation |
|---|---|---|
| [CoreELEC N5 Max S905X3 thread](https://discourse.coreelec.org/t/magicsee-n5-max-s905x3-no-wifi-no-bluetooth/12576) | A 4/32 LAN100M box used the mapped DT and reported Ethernet traffic | Not this PCB; no PHY register/stock DTS dump |
| [CoreELEC N5 Plus recovery](https://discourse.coreelec.org/t/magicsee-n5-plus-4-64-recovery-mode/15547) | sm1_ac213_4g reported on N5 Plus | Does not confirm this ID on N5 Max |
| [CoreELEC N5 Max 2019 thread](https://discourse.coreelec.org/t/magicsee-n5-max-ethernet-not-working/6569) | Opening post concerns g12a/S905X2 | Do not transfer its RTL8211F inference to the tested S905X3 |

## Russian sources, paraphrased in Vietnamese

The earlier research read search-retrieved 4PDA text because direct pages returned 403. These findings were retained with their access limits; PCB images and stock firmware bytes were not verified. See [technical analysis](TECHNICAL_ANALYSIS.md) for the translations.

| Source | Retained technical paraphrase | Confidence boundary |
|---|---|---|
| [4PDA topic 973352, st=240](https://4pda.to/forum/index.php?showtopic=973352&st=240) | Posts #242–243, 2020-01-19 discuss PM44-11BP magnetics and a 100 Mbps port | PM44-11BP is not the PHY model; photo not examined |
| [4PDA st=580](https://4pda.to/forum/index.php?showtopic=973352&st=580) | Post #596, 2020-02-19 reports different boot behavior between 1000M and stock firmware | User report; no GPIO/clock values extracted |
| [4PDA st=620](https://4pda.to/forum/index.php?showtopic=973352&st=620) | Post #640, 2020-02-22 names a 20191107 LAN100M firmware | Filename clue only; no downloadable matching bytes obtained |

No CoreELEC/vendor DTB was decompiled in this project because matching bytes were not obtained. The comparison table leaves unknown fields unknown. The strongest evidence for the actual board is the before/after runtime and real 100/full link, not a forum naming convention.
