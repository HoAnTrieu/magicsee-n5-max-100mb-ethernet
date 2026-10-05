# Triển khai trên Armbian đang boot từ SD

[README](../README.vi.md) · [Rollback](ROLLBACK.md) · [Troubleshooting](TROUBLESHOOTING.md)

## Điều kiện đã kiểm chứng

Dự án sửa Ethernet cho một N5 Max **S905X3/SM1**, RAM loại 4 GB, kernel **6.12.111-ophub**, Armbian ophub v26.11.0 / Ubuntu Noble. Máy đã boot tốt từ SD bằng rescue `meson-sm1-x96-max-plus-100m.dtb`. Đây là bản LAN 100 Mbps; các revision Gigabit cần phân tích riêng.

Đây là triển khai patch trên hệ thống đã chạy, không phải hướng dẫn flash image Armbian lên box mới. Bộ dự án không kèm OS image, bootloader hoặc công cụ cài OS lên eMMC. Script không khóa eMMC cho các chương trình khác; chức năng bảo vệ eMMC thuộc một nhiệm vụ riêng.

Installer yêu cầu Python 3.10+ (Noble có Python 3.12), `findmnt`, boot partition đã mount tại `/boot` và layout `/boot/uEnv.txt`. Không cần cài dtc để dùng DTB có sẵn. Cần `ethtool` để test link:

```bash
sudo apt-get update
sudo apt-get install python3 ethtool
```

Xác nhận thông tin trước khi ghi:

```bash
uname -r
findmnt /
findmnt /boot
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
grep '^FDT=' /boot/uEnv.txt
sha256sum /boot/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb
```

Checksum rescue phải là:

```text
386cdd6714f2e507db8b443c263c1a7d5fb7facc24bce9c8b2208d8bfe5c67eb
```

Nếu khác, không bypass guard. Tên file trùng không chứng minh nội dung trùng. Phân tích lại cây nền và boot trước khi mở rộng phạm vi hỗ trợ.

## Windows → MobaXterm → Armbian

1. Giải nén ZIP. Bên trong có thư mục `magicsee-n5-max-ethernet`.
2. Mở kết nối SSH bằng MobaXterm. Qua panel SFTP, upload cả thư mục vào home user Armbian. Ví dụ thư mục đích `~/magicsee-n5-max-ethernet`.
3. Cắm dây LAN vào router/switch. Giữ khả năng SSH qua Wi-Fi hoặc console và tháo SD để phục hồi.
4. Chạy từ thư mục gốc dự án:

```bash
cd ~/magicsee-n5-max-ethernet
sha256sum -c SHA256SUMS
python3 scripts/verify.py
sudo python3 scripts/install.py --dry-run
```

Dry-run không ghi boot file. Nếu tất cả kiểm tra pass:

```bash
sudo python3 scripts/install.py --apply
grep '^FDT=' /boot/uEnv.txt
sudo cmp dist/meson-sm1-magicsee-n5-max.dtb /boot/dtb/amlogic/meson-sm1-magicsee-n5-max.dtb
sudo sync
sudo reboot
```

FDT cần chọn:

```text
FDT=/dtb/amlogic/meson-sm1-magicsee-n5-max.dtb
```

`cmp` thành công không in gì. Nếu script hoặc `cmp` báo lỗi, xử lý trước khi reboot. Thư mục `reference/` chỉ dùng kiểm chứng, không copy vào `/boot`.

## Những gì installer làm

| Bước | Hành vi |
|---|---|
| Kiểm tra release | SHA256SUMS, binary, semantic delta đúng sáu property |
| Kiểm tra máy | Kernel, checksum rescue, một dòng FDT đúng nền, boot partition mount |
| Kiểm tra xung đột | Dừng khi có extlinux.conf thật, symlink đích, hardlink tới rescue, candidate/backup khác |
| Backup | Tạo `uEnv.txt.n5max-backup` nếu chưa có; không ghi đè backup khác |
| Ghi DTB | Tên mới; file tạm → flush/fsync → rename; kiểm tra byte |
| Chọn DTB | Thay đúng giá trị dòng FDT active; giữ bytes khác và CRLF nếu có |
| Kết thúc | Sync; kiểm lại checksum rescue; không tự reboot |

Lock file tránh hai lần cài chạy đồng thời. Đây không phải cam kết chống mọi tình huống mất nguồn hoặc chương trình root khác sửa boot cùng lúc. Rescue và khả năng sửa SD bằng PC vẫn là đường phục hồi.

Nếu FDT đã chọn đúng DTB release và binary trùng, script báo `Already installed` rồi kết thúc. Trường hợp này không tạo backup mới; nếu backup cũ thiếu, rollback bằng cách đổi riêng FDT về rescue.

## Khi installer dừng

| Thông báo | Cách xử lý |
|---|---|
| Untested kernel / rescue checksum differs | Giữ máy nguyên trạng; gửi reduced report và cây nền cho phân tích riêng |
| /boot must be mounted | Kiểm tra mount; không ghi vào thư mục boot rỗng trên rootfs |
| Actual extlinux.conf exists | Xác định loader thực sự dùng uEnv hay extlinux; script không tự sửa loader |
| Existing backup differs | Đọc backup và uEnv hiện tại; giữ bản cũ dưới tên khác nếu xác định cần backup mới |
| Existing candidate differs | Giữ candidate cũ để đối chiếu; không ghi đè file chưa rõ nguồn |
| Multiple FDT / current FDT differs | Xác định cấu hình active đúng; không dùng replace hàng loạt |
| Checksum mismatch | Lấy lại gói nguyên vẹn; không sửa checksum để bỏ qua lỗi |

Sau reboot làm theo [TESTING](TESTING.md). Trước khi cập nhật kernel/Armbian sau này, giữ bản boot hoạt động và rescue; kiểm tra FDT và checksum lại sau cập nhật. Bản này chưa được test trên kernel khác.
