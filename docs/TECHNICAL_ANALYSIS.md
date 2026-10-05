# Phân tích Ethernet và Device Tree

[README tiếng Việt](../README.vi.md) · [Sources](SOURCES.md)

Ngày: 2026-10-05. Bản này dành cho cấu hình đã test trên một máy, không bao quát mọi revision N5 Max.

## 1. Kết luận từ dữ liệu mới

Cấu hình đang chạy chọn **external MDIO branch 0, PHY address 0, RGMII**. Tuy tên file có `100m`, nó chỉ đặt `max-speed = <100>` trên external PHY. Giới hạn tốc độ không chuyển MAC sang PHY nội.

`mdio-sysfs.txt` trong gói `n5max-phy.KCSZMLhk.tar.gz` cho thấy:

| Endpoint | PHY ID trong sysfs | Driver thực sự bind | Nhận xét |
|---|---|---|---|
| `mdio_mux-0.0:00` | `0x00000000` | Không có symlink driver hoặc `DRIVER=` trong uevent | Endpoint ngoài mà DT chọn không có nhận dạng/capability hữu ích |
| `mdio_mux-0.1:08` | `0x01803301` | `Meson G12A Internal PHY` | Driver PHY nội đã bind; MAC chưa dùng endpoint này |
| `fixed-0:1f` | Không phải PHY LAN đang chọn | Không liên quan | Không dùng làm bằng chứng Ethernet |

Các dòng `DRIVER=/sys/.../driver` do script in từ `readlink -f` không tự chứng minh symlink tồn tại. Đã đối chiếu với listing và uevent: chỉ endpoint nội có symlink driver thật. `eth0/phydev` hiện cũng chưa có symlink thật.

**Giới hạn của dữ liệu trước patch:** ID `0180.3301` đã khai báo trong DT nên ID sysfs/bind driver riêng lẻ không chứng minh PHYID registers hoặc routing RJ45. Gói sau reboot nay cung cấp bằng chứng độc lập: eth0 attach PHY nội, autoneg100/full, carrier 1 và DHCP IPv4. Đường PHY nội/RMII hoạt động tới LAN trên revision này đã được xác nhận. Sysfs vẫn ghi `phy_interface=internal`; dùng DT runtime và dmesg `phy/rmii` để xác nhận mode MAC, không ép field sysfs phải là rmii.

Log `validation of rgmii ... 00006280 failed: -EINVAL` có capability mask chỉ gồm TP, MII, Pause, AsymPause; thiếu các bit tốc độ và autoneg. Vì vậy không xử lý lỗi này bằng DHCP, route hay thêm RGMII delay. External PHY ID bằng 0 cùng capability rỗng phù hợp nhất với việc cấu hình X96 đang chọn sai endpoint. Trước test, ngoại vi chưa cấp nguồn/reset đúng vẫn là khả năng khác. Sau test, việc giữ nguyên kernel và chuyển đúng sáu property đã đưa đường PHY nội lên link, xác nhận cấu hình Ethernet nền không phù hợp với đường LAN đang dùng trên máy này. Không khẳng định PCB không thể có linh kiện khác khi chưa xem ảnh/dump.

RGMII vẫn có thể mang link 100 Mbps. Bằng chứng LAN 100M riêng lẻ không đủ để chọn RMII. Quyết định patch dựa trên tổng hợp: endpoint external không hợp lệ, endpoint internal đã bind, tham chiếu N5 Max LAN 100M, và topology internal ePHY/RMII trong mainline SM1.

Kernel config và builtin metadata xác nhận `STMMAC_ETH`, `DWMAC_MESON`, `PHYLINK`, `PHYLIB`, `MESON_GXL_PHY`, `MDIO_BUS_MUX`, `MDIO_BUS_MUX_MESON_G12A`, `REALTEK_PHY`, `ICPLUS_PHY` đều được build-in (`=y`). Thiếu module không phải hướng sửa cho các driver này. Không cần đổi kernel hoặc modprobe thêm driver.

## 2. Đầu vào và đối chiếu semantic

Đã đọc các file liên quan trong ba archive (baseline, trước patch và sau patch): cấu hình boot, toàn bộ cây DT, Ethernet/MDIO sysfs, kernel config/support, full dmesg, ethtool, GPIO debug, mount/storage, USB, network và nhiệt độ.

- DTB rescue: 77.050 byte; SHA-256 `386cdd6714f2e507db8b443c263c1a7d5fb7facc24bce9c8b2208d8bfe5c67eb`.
- DTB rescue và DTS decompile được cung cấp: cùng 542 node, 2.305 property; giá trị từng property trùng nhau.
- Hai bản `magicsee-live.dts`: trùng nhau theo node/property.
- Nền so với runtime: đúng 6 khác biệt — bootargs, hai địa chỉ initrd, RAM reg, local MAC address và MAC address. Ethernet topology không bị bootloader sửa.
- `boot-passed.fdt` so với runtime: runtime thêm `mac-address`; các giá trị còn lại trùng nhau. Các boot fixup vẫn cần được bootloader thực hiện mỗi lần khởi động.

Vì vậy bản sửa lấy **DTS của DTB rescue** làm nền, không lấy live DTS để cố định initramfs/RAM/MAC. Runtime RAM là `0xd8000000` (3.456 MiB); giữ nguyên khai báo nền để bootloader tiếp tục xử lý như trước.

Máy hiện boot từ SD: `/boot` trên `/dev/mmcblk1p1` (vfat), `/` trên `/dev/mmcblk1p2` (ext4). eMMC `/dev/mmcblk2` khoảng 29,1 GiB vẫn được nhận diện. Wi-Fi QCA6174 qua SDIO/ath10k đang hoạt động. Nhiệt độ trước patch: CPU 42,5°C, DDR 43,8°C. Đây là mốc regression, không phải đo sau patch.

## 3. Research và bản dịch nguồn Nga

| Nguồn | Thông tin kiểm chứng được | Giới hạn khi áp dụng |
|---|---|---|
| [CoreELEC legacy DTB table](https://coreelec.org/legacy/dtb/) | Chính thức ánh xạ Magicsee N5 Max / S905X3 / 4G → `sm1_s905x3_4g` | Xác nhận manh mối thứ nhất; không xác nhận PCB revision hoặc bindings 6.12 |
| [CoreELEC, N5 Max S905X3](https://discourse.coreelec.org/t/magicsee-n5-max-s905x3-no-wifi-no-bluetooth/12576) | Chủ máy ghi bản 4/32, LAN 100M, CE 9.2.4.2 và DTB trên; eth0 UP/RUNNING có IPv4 và traffic | Chứng minh tồn tại bản LAN 100M hoạt động; không có PHY ID/reset GPIO |
| [ophub issue #2564](https://github.com/ophub/amlogic-s9xxx-armbian/issues/2564) | N5 Max S905X3/kernel 6.6.50 có đúng validation mask `6280`, attach `-22`, đổi DTB khác làm lỗi boot | Issue đóng nhưng trang truy xuất không có patch đã được xác nhận |
| [4PDA topic 973352, st=240](https://4pda.to/forum/index.php?showtopic=973352&st=240), #242–243, 19/01/2020 | Dịch kỹ thuật: người dùng nói linh kiện biến áp/cách ly `PM44-11BP` chỉ phục vụ 100 Mbps, bài sau xác nhận cổng 100 Mbps | PM44-11BP là magnetics, **không phải PHY**; chưa xem được ảnh PCB |
| [4PDA st=580](https://4pda.to/forum/index.php?showtopic=973352&st=580), #596, 19/02/2020 | Dịch: firmware 1000M bị kẹt logo trên box của người viết; firmware stock 07/11/2019 boot và Ethernet hoạt động, Wi-Fi gặp lỗi | Không chuyển lời kể đó thành GPIO/PHY model của máy này |
| [4PDA st=620](https://4pda.to/forum/index.php?showtopic=973352&st=620), #640, 22/02/2020 | Có tên firmware N5MAX S905X3 LAN 100M Android9.0 20191107, phản ánh link nhà cung cấp không tải được | Là đầu mối firmware; chưa có bytes dump để phân tích |
| [CoreELEC N5 Plus recovery](https://discourse.coreelec.org/t/magicsee-n5-plus-4-64-recovery-mode/15547) | Chủ máy đọc `sm1_ac213_4g` từ `amlogic-dt-id` trên **N5 Plus** | Xác nhận DT ID trong family; chưa xác nhận trên N5 Max này |
| [CoreELEC N5 Max Ethernet 2019](https://discourse.coreelec.org/t/magicsee-n5-max-ethernet-not-working/6569) | Bài mở đầu dùng `g12a_s905x2...` | Thảo luận RTL8211F của S905X2 không xác định PHY cho S905X3 |

4PDA trực tiếp trả 403. Phần tiếng Nga nêu trên được đọc từ nội dung trang mà kết quả tìm kiếm trả về và dịch sang tiếng Việt; chưa kiểm chứng ảnh đính kèm. Không bỏ qua nguồn Nga, cũng không coi phần ảnh chưa xem là bằng chứng.

Chưa lấy được stock Android `boot.img`/`dtb.img`/`dtbo.img`, DTS khớp revision, schematic hoặc ảnh PCB đủ rõ để xác định chip/reset/routing. Chưa có bytes của CoreELEC `sm1_s905x3_4g.dtb` để decompile. Do đó các ô vendor chưa biết dưới đây được giữ là chưa biết; không suy diễn nội dung node từ tên DTB.

## 4. So sánh Ethernet A/B/C/D/E

| Hạng mục | A: rescue / B: runtime | C: CoreELEC `sm1_s905x3_4g` | D: Android `sm1_ac213_4g` | E: mainline SM1 internal PHY / bản sửa |
|---|---|---|---|---|
| MAC | `amlogic,meson-g12a-dwmac`, ff3f0000; hai vùng MMIO | Chưa đọc node | Chưa đọc node | Giữ nguyên controller của nền |
| PHY topology | External mux branch 0 được MAC chọn | Mapping đúng N5 Max S905X3 confirmed; topology chưa đọc | DT ID có trên N5 Plus; chưa đọc topology | SEI610 dùng internal ePHY; bản sửa chọn branch 1 |
| `phy-handle` | `0x09` → external PHY@0 | Chưa biết | Chưa biết | `0xe7` → internal PHY@8 có sẵn trong nền |
| Interface | RGMII | Chưa biết node | Chưa biết node | RMII |
| MDIO address | External 0; internal 8 chưa được MAC chọn | Chưa biết | Chưa biết | Internal 8, giữ nguyên |
| PHY ID/model | External đọc 0; internal khai báo 0180.3301 | Chưa xác định chip | Chưa xác định chip | Meson G12A integrated 10/100 ePHY đã attach và lên link trên máy này |
| External reset | GPIOZ_15, flags 7; assert 30ms, deassert 80ms | Chưa biết | Chưa biết | External branch disabled; không thêm GPIO reset cho internal |
| External IRQ | Parent 0x16, line 26, flags 8 | Chưa biết | Chưa biết | Giữ trong node không được enumerate; internal SPI9 giữ nguyên |
| Pinctrl | MAC tham chiếu `eth` + `eth-rgmii` | Chưa biết | Chưa biết | Bỏ hai tham chiếu ở MAC; giữ nguyên các node pinctrl |
| Clock | MAC: stmmaceth/clkin0/clkin1/timing-adjustment; mux: pclk/clkin0/clkin1 | Vendor binding/IDs chưa đọc | Vendor binding/IDs chưa đọc | Không thay clock source/IDs/rates của nền |
| Delay | MAC TX delay 2ns | Chưa biết | Chưa biết | Bỏ property RGMII khi chuyển RMII |
| Power/regulator | Không có sửa nguồn Ethernet trong bản này | Chưa biết | Chưa biết | Không thêm regulator dựa trên phỏng đoán |
| Speed | External `max-speed=100`; internal cũng 100 | Chủ máy khác xác nhận LAN 100M | Chưa xác nhận bản N5 Max này | Giữ internal `max-speed=100`, autoneg do PHY xử lý |

Ý nghĩa phần cứng: `phy-handle` chọn endpoint quản lý/link; `phy-mode` chọn đường dữ liệu MAC–PHY. Cần đổi cả hai. Nhánh mux 1 dùng ePHY trong SoC, không cần pinmux RGMII ra GPIOZ. `max-speed` chỉ giới hạn quảng bá/capability, không sửa lựa chọn nhánh. Không ánh xạ clock ID hay GPIO số vendor trực tiếp sang mainline.

## 5. Patch chính xác và mức độ tin cậy

Chỉ thay đúng sáu property tại hai node. Không xóa node hoặc đổi phandle/symbol.

| Node/property | Thay đổi | Lý do | Mức độ |
|---|---|---|---|
| MAC `phy-handle` | `0x09` → `0xe7` | Chọn internal PHY@8 đã có driver thay cho endpoint ngoài ID0/capability rỗng | **confirmed** cấu hình hoạt động; phandle đích tồn tại; chưa đo routing PCB trực tiếp |
| MAC `phy-mode` | `rgmii` → `rmii` | Đường dữ liệu phù hợp integrated 10/100 ePHY trong mainline | **confirmed** RMII hoạt động trong cấu hình sau boot |
| MAC `pinctrl-0` | Xóa `<0x07 0x08>` | Ngừng mux chân external Ethernet/RGMII cho đường nội | **confirmed** trong cấu hình tổng thể; chưa thử riêng property |
| MAC `pinctrl-names` | Xóa `default` | Đi cùng việc bỏ state pinctrl ngoài | **confirmed** trong cấu hình tổng thể; chưa thử riêng property |
| MAC `amlogic,tx-delay-ns` | Xóa giá trị 2 | Binding quy định delay RGMII bị bỏ qua trong RMII; không cần cho cấu hình mới | **confirmed** về ngữ nghĩa upstream; không phải timing tuning đã đo trên PCB |
| Mux `mdio@0/status` | Thêm `disabled` | Bỏ enumeration toàn nhánh external, tránh claim reset/IRQ GPIO thừa hưởng X96 | **confirmed** endpoint ngoài không enumerate sau boot; chưa thử độc lập |

**Cập nhật sau test: confirmed working PHY/link 100M cho cấu hình tổng thể trên chính máy này.** Bảng trên cập nhật bằng chứng sau test; sau reboot đã xác nhận đường kết nối chức năng internal/RMII, attach, carrier 1 và DHCP. Chưa kiểm tra mức độ cần thiết riêng lẻ của từng property hoặc độ ổn định dài hạn. Không cần thử thêm PHY model/DTB.

Node external vẫn chứa reset/IRQ cũ để giữ nguyên cây/symbol, nhưng parent `mdio@0` disabled nên driver mux không enumerate nó. `debug-gpio.txt` trước patch ghi GPIO527 (GPIOZ_15) là PHY reset active-low, output-low sau attach fail. Trạng thái đó chưa chứng minh GPIO này là reset đúng của PCB; patch ngừng dùng nhánh thừa hưởng thay vì đoán timing mới.

Giữ nguyên: internal PHY compatible `0180.3301`, address 8, IRQ SPI9, max-speed 100; MAC/mux clocks, reg, IRQ, FIFO, DMA properties, nvmem MAC; toàn bộ memory, CPU/cpufreq, SD/eMMC/SDIO/Wi-Fi, USB/UART, power domains, regulators, pinctrl definitions, `/chosen`, `__symbols__`. Root `model` vẫn mang tên AMedia X96 của nền có chủ ý để không thêm thay đổi ngoài Ethernet; tên file mới xác định bản dành cho N5 Max. Root compatible không được tự đổi sang một board binding chưa có.

Không thêm `assigned-clocks`, `assigned-clock-rates`, GPIO reset mới, `snps,reset-*`, `rx-internal-delay-ps`, `tx-internal-delay-ps`, regulator hoặc vendor property.

## 6. Bindings, compile và validation

Tham chiếu source/binding primary:

- [Amlogic MAC binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/amlogic,meson-dwmac.yaml): MAC clocks và ngữ nghĩa TX delay RGMII/RMII.
- [G12A MDIO mux binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/amlogic,g12a-mdio-mux.yaml): external/internal 10/100, mux branch 0/1, internal PHY@8 và compatible 0180.3301.
- [Generic PHY binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/ethernet-phy.yaml) và [Synopsys binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/net/snps,dwmac.yaml): không tự thêm reset legacy/delay.
- [SEI610 mainline DTS](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/amlogic/meson-sm1-sei610.dts): mẫu internal ePHY/RMII; không lấy cả board DT làm nền.
- [MDIO mux source](https://codebrowser.dev/linux/linux/drivers/net/mdio/mdio-mux.c.html): enumerate `for_each_available_child_of_node`; bản hiển thị v6.19-rc8, dùng tham chiếu hành vi, không giả là source build ophub 6.12.

**Không có source commit/bindings chính xác của build `6.12.111-ophub`.** Máy chỉ có headers, gói thu thập không có binding/source; các lần truy xuất source theo tag/branch không lấy được nội dung. Vì vậy chưa chạy `dtbs_check` đúng kernel này. Tài liệu upstream không được gọi là binding đã xác minh theo build. Patch chỉ dùng `phy-handle`, `phy-mode`, `status` mainline và node internal đang có/đã bind; không thêm property reset/timing có nguy cơ khác phiên bản. Đây vẫn là giới hạn validation cần nêu rõ.

Đã dùng **dtc 1.7.0 thật**, cùng phiên bản ghi trên máy của bạn, để compile cả baseline và bản sửa, không dùng trình đóng gói FDT tự viết thay compiler:

```bash
dtc -I dts -O dtb \
  -o meson-sm1-magicsee-n5-max.dtb \
  meson-sm1-magicsee-n5-max.dts
```

| Kiểm tra | Kết quả |
|---|---|
| Compile baseline / patched | Exit 0 / Exit 0; không error |
| Warning baseline / patched | 285 / 285; không warning mới sau chuẩn hóa file/line |
| Nguồn warning | 280 warning numeric phandle của DTS decompile; 5 warning cấu trúc có sẵn trong nền |
| Recompile baseline vs DTB gốc | Tất cả node/property trùng nhau |
| DTB mới | 76.998 byte; SHA-256 `03c8877650e9b7d7feda656db775dcd591ba20f6528665c2367537c8888fbffd` |
| Semantic diff toàn cây | Đúng 6 property nêu trên, chỉ ở hai node Ethernet |
| Node paths / symbols | Giữ đủ 542 node và toàn bộ symbol table |
| Property nền giữ nguyên | 2.300 property có cùng bytes; 2 đổi giá trị, 3 xóa, 1 thêm |
| Memory reservation / boot CPU header | Giữ nguyên |
| Storage/CPU/Wi-Fi/USB/RAM/regulator | Không có thay đổi DT property |
| Boot/link/regression thực tế | Boot/attach/link 100/full/DHCP đã xác nhận; SD/eMMC/USB/Wi-Fi không thấy regression trong snapshot. Throughput/stress dài hạn chưa đo |

Warning `cell ... is not a phandle reference` xuất hiện vì source decompile dùng số như `<0x02 ...>` thay `&label`; dtc không có metadata reference trong source, dù phandle nhị phân vẫn trỏ node hợp lệ. Không sửa toàn cây hoặc tắt warning để làm log trông sạch. `dtc-baseline.log`, `dtc-patched.log` và `validation.json` kèm đầy đủ bằng chứng. Compile thành công không xác nhận dây LAN/routing PHY.


## Đọc patch và tái tạo source

Từ gốc dự án:

```bash
mkdir -p build
patch -o build/from-patch.dts reference/meson-sm1-x96-max-plus-100m.dts < patches/ethernet-only.patch
cmp build/from-patch.dts src/meson-sm1-magicsee-n5-max.dts
bash scripts/build.sh
```

Giá trị phandle `0xe7` chỉ có ý nghĩa trong cây nền này. Khi port sang cây mới, dùng label và binding của cây mới, không copy số phandle. Không thay binary `dist/` bằng kết quả build khác trước khi kiểm chứng trên phần cứng.
