# Sửa Ethernet Magicsee N5 Max S905X3 trên Armbian

[English](README.md) · [Triển khai chi tiết](docs/DEPLOYMENT.md) · [Phân tích](docs/TECHNICAL_ANALYSIS.md) · [Kết quả test](docs/VALIDATION.md)

**Đã chạy trên một N5 Max S905X3: PHY nội, RMII, Ethernet 100 Mbps Full Duplex, carrier 1 và DHCP.** Bản sửa giữ DTB nền đang boot tốt, chỉ thay sáu property Ethernet. Kernel vẫn là **6.12.111-ophub**.

Dự án cộng đồng này dành cho bản LAN 100 Mbps đã test. N5 Max có nhiều revision; chưa xác nhận bản S905X2, Gigabit hoặc kernel khác. PCB revision của máy test chưa được ghi nhận.

## Cấu hình đã kiểm chứng

| Hạng mục | Giá trị |
|---|---|
| Box / SoC | Magicsee N5 Max / Amlogic S905X3 (SM1) |
| RAM | Loại 4 GB; Linux nhận khoảng 3,24 GiB usable |
| OS | ophub Armbian v26.11.0, Ubuntu Noble |
| Kernel | 6.12.111-ophub |
| DTB rescue | meson-sm1-x96-max-plus-100m.dtb |
| PHY sau patch | Meson G12A Internal PHY, mux branch 1, address 8 |
| Mode MAC–PHY | RMII |
| Link | 100 Mbps / Full Duplex / autoneg on |
| Regression trong snapshot | SD/root mount, eMMC nhận diện, USB như cũ, Wi-Fi kết nối |

## Vấn đề và cách sửa

DTB tên `100m` vẫn chọn **external PHY@0 / RGMII**; `max-speed=100` chỉ giới hạn tốc độ, không chuyển sang PHY nội. Endpoint ngoài báo ID 0 và không có capability tốc độ hợp lệ:

```text
validation of rgmii ... 00006280 failed: -EINVAL
__stmmac_open: Cannot attach to PHY (error: -22)
```

Bản sửa chọn PHY nội có sẵn ở mux branch 1 / address 8, chuyển RMII, bỏ pinctrl ngoài và delay RGMII, disable external MDIO branch. Sau reboot:

```text
PHY [mdio_mux-0.1:08] driver [Meson G12A Internal PHY]
configuring for phy/rmii link mode
Link is Up - 100Mbps/Full - flow control rx/tx
```

Giữ đủ **542 node**, **2.300 property có cùng bytes**, chỉ thay sáu property tại hai node Ethernet. CPU/RAM, storage, USB, Wi-Fi, clocks và regulators giữ nguyên. Không copy DTB vendor/CoreELEC sang kernel mainline.

## Cài nhanh bằng MobaXterm

Máy cần đã boot ổn bằng đúng DTB rescue và kernel trong bảng. Giải nén ZIP, upload **cả thư mục** `magicsee-n5-max-ethernet` vào home trên Armbian qua SFTP của MobaXterm. Tại SSH:

```bash
cd ~/magicsee-n5-max-ethernet
sha256sum -c SHA256SUMS
python3 scripts/verify.py
sudo python3 scripts/install.py --dry-run
sudo python3 scripts/install.py --apply
grep '^FDT=' /boot/uEnv.txt
sudo sync
sudo reboot
```

FDT phải thành:

```text
FDT=/dtb/amlogic/meson-sm1-magicsee-n5-max.dtb
```

Installer tạo backup `/boot/uEnv.txt.n5max-backup`, ghi DTB theo tên mới và chỉ đổi giá trị FDT. Rescue không bị ghi đè. Không tự reboot; cắm LAN trước khi khởi động lại.

Nếu máy đã chạy đúng bản DTB này và hoạt động tốt, **không cần cài lại**. Script nhận trạng thái already-installed rồi kết thúc.

Installer dừng khi kernel/checksum nền khác, có extlinux.conf thật, nhiều dòng FDT hoặc backup/candidate xung đột. Không bypass guard. [DEPLOYMENT](docs/DEPLOYMENT.md) giải thích yêu cầu và xử lý từng trường hợp.

## Test sau reboot

```bash
sudo ip link set dev eth0 up
sleep 3
sudo ethtool eth0
sudo ethtool -i eth0
cat /sys/class/net/eth0/carrier
cat /sys/class/net/eth0/speed
ip -br addr
sudo dmesg | grep -Ei 'eth0|ethernet|dwmac|stmmac|phy|mdio|rgmii|rmii'
lsblk
findmnt /
lsusb
```

Mốc đạt: PHY@8 attach, runtime/log RMII, link yes, speed 100, duplex full, carrier 1. `model` vẫn ghi X96 do giữ metadata nền; dùng runtime Ethernet và dmesg để xác nhận patch.

Chỉ sau khi link lên, ping qua eth0 với gateway thật:

```bash
ip -4 route show default dev eth0
ping -I eth0 -c 100 IP_GATEWAY_ETH0
ip -s link show dev eth0
```

[TESTING](docs/TESTING.md) có throughput hai chiều bằng iperf3, Windows curl/HTTP estimate, counters và regression. [VALIDATION](docs/VALIDATION.md) phân biệt bằng chứng archive với kết quả truyền file do chủ máy báo. Chưa có benchmark hai chiều ràng buộc eth0 hoặc độ ổn định dài hạn trong evidence release.

## Rollback

Nếu vẫn boot được và backup đúng:

```bash
sudo cp /boot/uEnv.txt.n5max-backup /boot/uEnv.txt
sudo sync
sudo reboot
```

Nếu không boot: tắt nguồn, tháo SD, mở phân vùng FAT **BOOT** trên PC và đổi riêng FDT trong `uEnv.txt` về:

```text
FDT=/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb
```

Giữ nguyên LINUX, INITRD, APPEND và root UUID. Không cần flash lại OS để rollback. [ROLLBACK](docs/ROLLBACK.md) có hướng dẫn cụ thể.

## Build và kiểm chứng

```bash
sudo apt-get update
sudo apt-get install device-tree-compiler python3
bash scripts/build.sh
python3 -m unittest discover -s tests -v
```

Kết quả build nằm trong `build/`, không ghi đè binary đã test tại `dist/`. Dùng dtc thật; verifier đối chiếu full-tree bytes, phandle, reservations và boot CPU header.

DTC 1.7.0 compile baseline và bản sửa thành công; **285 warning ở mỗi bản, không warning mới**. Warning kế thừa từ DTS decompile được giữ trong `evidence/build/`, không che warning để gọi source sạch. Chưa chạy `dtbs_check` với source/bindings chính xác của build ophub; compile thành công không đồng nghĩa chứng nhận schema.

## Cấu trúc dự án

| Đường dẫn | Nội dung |
|---|---|
| src/ | DTS standalone hoàn chỉnh |
| dist/ | DTB đã test trên máy |
| reference/ | Exact rescue DTS/DTB để đối chiếu |
| patches/ | Diff Ethernet gồm hai hunk |
| scripts/ | Installer, verifier, build, reduced collector, packager |
| tests/ | Kiểm tra bằng fixture boot tạm; không chạm /boot thật |
| evidence/ | Log trước/sau và kết quả build đã lược dữ liệu riêng |
| docs/ | Triển khai, kỹ thuật, test, rollback, nguồn, phát hành |
| .github/ | CI và mẫu issue/report |

## Checksum và phát hành

| Artifact | SHA-256 |
|---|---|
| Rescue DTB | `386cdd6714f2e507db8b443c263c1a7d5fb7facc24bce9c8b2208d8bfe5c67eb` |
| DTB fix | `03c8877650e9b7d7feda656db775dcd591ba20f6528665c2367537c8888fbffd` |

`SHA256SUMS` bao phủ file public trong source. Hash kiểm tra tính nguyên vẹn, không phải chữ ký hoặc chứng nhận tương thích mọi board.

Đọc [PUBLISHING](docs/PUBLISHING.md) để đăng GitHub và tạo release v1.0.0. ZIP chứa đầy đủ source, license, notice và tài liệu; chưa đăng public tự động.

Đọc [CONTRIBUTING](CONTRIBUTING.md) khi góp kết quả board khác; dùng [reduced collector](docs/PRIVACY.md) và đọc lại report trước khi đăng. Archive debug gốc, live DTS và thông tin mạng riêng không có trong bộ public.

Code/tài liệu mới chọn GPL-2.0-only; Device Tree kế thừa giữ điều khoản upstream. [NOTICE](NOTICE.md) ghi rõ giới hạn provenance và source commit chưa truy ra.
