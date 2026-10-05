# Sửa Ethernet Magicsee N5 Max S905X3 trên Armbian

[English](README.md) · [Triển khai chi tiết](docs/DEPLOYMENT.md) · [Phân tích](docs/TECHNICAL_ANALYSIS.md) · [Kết quả test](docs/VALIDATION.md) · [Bonus: khóa eMMC](BONUS/README-eMMC-GUARD.md)

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

## Cài cho người mới: tải → chạy một script → reboot

Máy cần đã boot ổn với kernel **6.12.111-ophub** và đúng DTB rescue trong bảng. Script tự kiểm tra, backup uEnv, chép DTB theo tên mới và chỉ sửa dòng FDT. Không ghi đè rescue và không tự reboot.

### Clone từ GitHub

```bash
git clone https://github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet.git
cd magicsee-n5-max-100mb-ethernet
sudo bash install.sh
```

Nếu chưa có Git: `sudo apt-get update && sudo apt-get install git`.

### Dùng ZIP qua MobaXterm

Giải nén ZIP, upload cả thư mục `magicsee-n5-max-ethernet` vào home trên Armbian, rồi:

```bash
cd ~/magicsee-n5-max-ethernet
sudo bash install.sh
```

Chỉ khi script báo **HOÀN TẤT**, cắm LAN rồi reboot thủ công:

```bash
sudo reboot
```

Muốn chỉ kiểm tra trước, dùng `sudo bash install.sh --dry-run`.

Nếu bản DTB release đã được chọn và đúng checksum, script giữ nguyên boot file. Máy đang chạy tốt thì không cần cài lại. Khi kernel/checksum nền khác hoặc cấu hình xung đột, script dừng và chưa báo hoàn tất; xem [DEPLOYMENT](docs/DEPLOYMENT.md).

Script shell là cửa vào đơn giản; installer Python bên trong giữ toàn bộ kiểm tra rescue, backup, checksum và semantic delta. Người mới không cần chạy các file Python riêng.

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

## Bonus (tuỳ chọn): khóa eMMC read-only

`BONUS/` là phần quà thêm, **không liên quan tới bản sửa Ethernet**, dành cho máy boot Armbian từ SD và muốn giữ nguyên eMMC trong:

| File | Công dụng |
|---|---|
| `BONUS/lock-emmc.sh` | Đưa eMMC về read-only, tự áp lại sau mỗi boot bằng systemd service + udev rule, và chặn đường `armbian-install` mặc định |
| `BONUS/unlock-emmc.sh` | Gỡ đúng những gì script khóa đã tạo và trả eMMC về read-write |
| `BONUS/README-eMMC-GUARD.md` | Tài liệu đầy đủ (tiếng Việt): kiểm tra an toàn, xác minh sau reboot, cheat sheet và những điều guard **không** làm |
| `BONUS/LOG_OF_N5_MAX_BENCH.txt` | Log benchmark CPU/đĩa của máy test |

Dự án không cần bonus này và `install.sh` **không bao giờ** tự chạy nó. Đây chỉ là khóa phần mềm có thể đảo ngược, không phải hardware write-protect: không format, không sửa firmware hay bootloader, và từ chối chạy khi `/` hoặc `/boot` đang nằm trên eMMC. Đọc README trong `BONUS/` trước, rồi tự xác nhận tên ổ bằng `lsblk`:

```bash
lsblk -o NAME,SIZE,RO,TYPE,FSTYPE,MOUNTPOINTS
sudo ./BONUS/lock-emmc.sh --apply     # gõ đúng dòng xác nhận khi được yêu cầu
sudo blockdev --getro /dev/mmcblk2     # 1 = đang khóa
```

Muốn gỡ: `sudo ./BONUS/unlock-emmc.sh --remove`. Không chạy lệnh khóa trên máy đang boot từ eMMC.

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
| install.sh | Một lệnh cài cho người mới, báo reboot thủ công |
| BONUS/ | Bonus tuỳ chọn: script khóa/mở eMMC read-only kèm tài liệu |
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

`SHA256SUMS` bao phủ file public trong source, kể cả `BONUS/`. Hash kiểm tra tính nguyên vẹn, không phải chữ ký hoặc chứng nhận tương thích mọi board.

Dự án nằm tại [github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet](https://github.com/HoAnTrieu/magicsee-n5-max-100mb-ethernet). Cách tạo tag v1.0.1, nội dung release lấy từ [RELEASE_NOTES](docs/RELEASE_NOTES.md) và các bước trên web/Git nằm trong [PUBLISHING](docs/PUBLISHING.md). Chạy `python3 scripts/package.py` để tạo lại manifest và archive sau khi đã kiểm chứng.

Đọc [CONTRIBUTING](CONTRIBUTING.md) khi góp kết quả board khác; dùng [reduced collector](docs/PRIVACY.md) và đọc lại report trước khi đăng. Archive debug gốc, live DTS và thông tin mạng riêng không có trong bộ public.

Code/tài liệu mới chọn GPL-2.0-only; Device Tree kế thừa giữ điều khoản upstream. [NOTICE](NOTICE.md) ghi rõ giới hạn provenance và source commit chưa truy ra.
