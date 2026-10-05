# eMMC Guard for Armbian TV Box
## Bộ "Ổ & Chìa" bảo vệ eMMC

Tài liệu này đi kèm 2 script:

- `lock-emmc.sh` — **Ổ khóa**: bảo vệ eMMC khỏi bị ghi nhầm hoặc bị cài Armbian lên ngoài ý muốn.
- `unlock-emmc.sh` — **Chìa khóa**: gỡ toàn bộ lớp bảo vệ software và trả eMMC về trạng thái ghi bình thường.

Thiết kế này ưu tiên 3 mục tiêu:

1. **Không làm mất dữ liệu eMMC.**
2. **Không dùng permanent hardware write-protect.**
3. **Có thể đảo ngược hoàn toàn khi cần.**

> Đây là khóa bằng software. Người có quyền `root` và cố tình gỡ khóa vẫn có thể vô hiệu hóa nó. Mục tiêu chính là chống thao tác nhầm, script cài đặt ngoài ý muốn, hoặc người khác không biết cấu hình máy.

---

# 1. Môi trường đang áp dụng

Máy hiện tại:

- Armbian Ubuntu
- Amlogic S905X3 / SM1
- Hệ điều hành chạy từ SD card
- SD card:
  - `/dev/mmcblk1`
  - `/boot` trên `mmcblk1p1`
  - `/` trên `mmcblk1p2`
- eMMC trong TV box:
  - `/dev/mmcblk2`
  - dung lượng khoảng 29 GB

**Không được áp dụng file này một cách mù quáng cho máy khác nếu eMMC không phải `/dev/mmcblk2`.**

Kiểm tra trước:

```bash
lsblk -o NAME,SIZE,RO,TYPE,FSTYPE,MOUNTPOINTS
```

Kiểm tra loại thiết bị:

```bash
cat /sys/block/mmcblk2/device/type
```

Kết quả mong muốn:

```text
MMC
```

Kiểm tra eMMC có vùng boot phần cứng:

```bash
ls -l /dev/mmcblk2boot0 /dev/mmcblk2boot1
```

Nếu cả hai tồn tại thì đây là dấu hiệu rất mạnh rằng `/dev/mmcblk2` là eMMC thật.

---

# 2. File Ổ khóa — `lock-emmc.sh`

## Mục đích

Script bảo vệ eMMC bằng nhiều lớp:

1. Kiểm tra target có thật sự giống eMMC.
2. Từ chối chạy nếu `/` hoặc `/boot` đang nằm trên eMMC.
3. Từ chối chạy nếu eMMC đang được mount.
4. Từ chối chạy nếu swap đang nằm trên eMMC.
5. Đưa eMMC về chế độ read-only bằng `blockdev`.
6. Tạo `systemd service` để tự áp lại sau mỗi lần boot.
7. Tạo `udev rule` để tự áp lại khi block device xuất hiện.
8. Chặn lệnh `armbian-install` thông thường.
9. Tạo cảnh báo khi đăng nhập shell.
10. Lưu thông tin target vào `/etc/emmc-guard/config`.

Script **không** bật permanent hardware write-protect.

---

## Cài file vào máy

Ví dụ copy từ Windows:

```powershell
scp .\lock-emmc.sh admin@192.168.1.28:/home/admin/
```

SSH vào máy:

```bash
ssh admin@192.168.1.28
```

Cho quyền thực thi:

```bash
chmod +x ~/lock-emmc.sh
```

---

## Chạy khóa

```bash
sudo ~/lock-emmc.sh --apply
```

Script sẽ kiểm tra hệ thống trước.

Nếu an toàn, nó sẽ hiển thị đại loại:

```text
=== SAFETY CHECK PASSED ===
Target eMMC : /dev/mmcblk2
Type        : MMC
Size        : 29.1G
Root source : /dev/mmcblk1p2
Boot source : /dev/mmcblk1p1
boot0/boot1 : present
```

Sau đó yêu cầu xác nhận:

```text
Type exactly 'LOCK mmcblk2' to continue:
```

Nhập:

```text
LOCK mmcblk2
```

Nếu không nhập chính xác, script sẽ thoát và không thay đổi gì.

---

# 3. Kiểm tra sau khi khóa

Kiểm tra trạng thái read-only:

```bash
sudo blockdev --getro /dev/mmcblk2
```

Kết quả đúng:

```text
1
```

Kiểm tra bằng `lsblk`:

```bash
lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS
```

Mong muốn:

```text
mmcblk1       59.5G  0 disk
├─mmcblk1p1    511M  0 part /boot
└─mmcblk1p2     59G  0 part /

mmcblk2       29.1G  1 disk
```

`RO = 1` nghĩa là block device đang read-only.

---

## Kiểm tra lệnh `armbian-install`

```bash
command -v armbian-install
```

Sau khi khóa, nó nên ưu tiên:

```text
/usr/local/sbin/armbian-install
```

Thử chạy:

```bash
sudo armbian-install
```

Nó phải từ chối và hiện thông báo dạng:

```text
BLOCKED: armbian-install is intentionally disabled on this machine.
The internal eMMC is protected...
```

---

# 4. Reboot test

Sau khi cài guard, reboot một lần:

```bash
sudo reboot
```

Khi máy lên lại:

```bash
sudo blockdev --getro /dev/mmcblk2
```

Vẫn phải là:

```text
1
```

Kiểm tra service:

```bash
systemctl status emmc-guard.service
```

Kiểm tra rule:

```bash
cat /etc/udev/rules.d/99-emmc-readonly.rules
```

Kiểm tra config:

```bash
cat /etc/emmc-guard/config
```

---

# 5. File Chìa khóa — `unlock-emmc.sh`

## Mục đích

Script này đảo ngược đúng phần mà `lock-emmc.sh` tạo ra.

Nó sẽ:

- dừng và disable `emmc-guard.service`
- xóa systemd service
- xóa udev rule
- xóa wrapper chặn `armbian-install`
- xóa login warning
- xóa executable guard
- đưa `/dev/mmcblk2` về read-write
- cuối cùng mới xóa `/etc/emmc-guard/config`

Script **không sửa permanent write-protect bit** của eMMC.

---

## Copy chìa khóa lên máy

Từ Windows:

```powershell
scp .\unlock-emmc.sh admin@192.168.1.28:/home/admin/
```

Cho quyền:

```bash
chmod +x ~/unlock-emmc.sh
```

---

## Gỡ khóa

```bash
sudo ~/unlock-emmc.sh --remove
```

Script đọc target từ:

```text
/etc/emmc-guard/config
```

Nó **không tự đoán ổ**.

Sau đó yêu cầu:

```text
Type exactly 'UNLOCK mmcblk2' to continue:
```

Nhập:

```text
UNLOCK mmcblk2
```

---

# 6. Kiểm tra sau khi mở khóa

```bash
sudo blockdev --getro /dev/mmcblk2
```

Kết quả mong muốn:

```text
0
```

`0` nghĩa là read-write bình thường.

Kiểm tra:

```bash
lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS
```

`mmcblk2` phải có:

```text
RO = 0
```

Kiểm tra lại lệnh Armbian:

```bash
command -v armbian-install
```

Wrapper `/usr/local/sbin/armbian-install` do guard tạo ra phải biến mất.

Reboot:

```bash
sudo reboot
```

Sau đó kiểm tra lại:

```bash
sudo blockdev --getro /dev/mmcblk2
```

Vẫn phải là:

```text
0
```

---

# 7. Những file mà Guard tạo ra

Khi khóa đang hoạt động, các file chính gồm:

```text
/etc/emmc-guard/config
/usr/local/sbin/emmc-guard
/usr/local/sbin/armbian-install
/usr/local/bin/armbian-install
/etc/udev/rules.d/99-emmc-readonly.rules
/etc/systemd/system/emmc-guard.service
/etc/profile.d/99-emmc-protected.sh
```

Không nên chỉnh từng file bằng tay nếu vẫn còn `unlock-emmc.sh`.

---

# 8. Cách hoạt động

Luồng khóa:

```text
Boot
  ↓
Linux thấy /dev/mmcblk2
  ↓
udev rule gọi emmc-guard
  ↓
blockdev --setro /dev/mmcblk2
  ↓
systemd chạy lại guard
  ↓
eMMC = READ-ONLY
```

Ngoài ra:

```text
Người dùng chạy:
sudo armbian-install
        ↓
/usr/local/sbin/armbian-install
        ↓
BLOCKED
```

Nên kể cả người sau không biết cấu hình máy, khả năng vô tình cài Armbian lên eMMC sẽ giảm rất nhiều.

---

# 9. Điều Guard KHÔNG làm

Guard không:

- format eMMC
- xóa partition
- xóa firmware Android cũ
- ghi vào boot0/boot1 theo kiểu permanent
- bật permanent write-protect
- fuse OTP
- sửa bootloader
- thay đổi U-Boot
- thay đổi dữ liệu eMMC
- ngăn một người có quyền root và chủ động phá khóa

Đây là **reversible software protection**.

---

# 10. Khi nào KHÔNG được chạy `lock-emmc.sh`

Không chạy nếu:

- OS đã chuyển sang chạy từ eMMC
- `/boot` nằm trên eMMC
- `/` nằm trên eMMC
- eMMC đang được dùng làm swap
- `/dev/mmcblk2` không còn là eMMC
- đang làm recovery/cài đặt firmware có chủ đích
- chưa xác định rõ thiết bị nào là SD và thiết bị nào là eMMC

Script có safety check để từ chối nhiều trường hợp trên, nhưng vẫn nên kiểm tra bằng mắt trước.

---

# 11. Kiểm tra nhanh trạng thái máy

## Đang khóa hay chưa?

```bash
sudo blockdev --getro /dev/mmcblk2
```

- `1` = khóa read-only
- `0` = read-write

## Service còn hoạt động không?

```bash
systemctl is-enabled emmc-guard.service
systemctl is-active emmc-guard.service
```

Khi khóa:

```text
enabled
active
```

## Wrapper `armbian-install` còn không?

```bash
command -v armbian-install
```

Khi khóa:

```text
/usr/local/sbin/armbian-install
```

## Xem toàn bộ nhanh

```bash
echo "=== eMMC ==="
lsblk -o NAME,SIZE,RO,TYPE,MOUNTPOINTS

echo
echo "=== Guard ==="
systemctl is-enabled emmc-guard.service 2>/dev/null || true
systemctl is-active emmc-guard.service 2>/dev/null || true

echo
echo "=== armbian-install ==="
command -v armbian-install || true

echo
echo "=== Saved config ==="
cat /etc/emmc-guard/config 2>/dev/null || echo "Guard config not found"
```

---

# 12. Trường hợp mất file `unlock-emmc.sh`

Không hoảng.

Miễn là:

```text
/etc/emmc-guard/config
```

còn tồn tại, vẫn biết eMMC nào đang được guard bảo vệ.

Có thể lấy lại `unlock-emmc.sh` từ bộ tài liệu gốc và chạy:

```bash
sudo ./unlock-emmc.sh --remove
```

Không cần reinstall Armbian.

---

# 13. Khuyến nghị lưu bộ file

Nên lưu chung 3 file:

```text
emmc-guard/
├── README-eMMC-GUARD.md
├── lock-emmc.sh
└── unlock-emmc.sh
```

Có thể backup bộ này ở:

- máy Windows cá nhân
- Google Drive / Git private
- USB recovery
- thư mục tài liệu dự án

**Không chỉ lưu duy nhất trên N5 Max.**

Nếu một ngày SD card chết thì README nằm trên chính cái máy chết cũng không giúp được nhiều. Công nghệ đôi khi có khiếu hài hước khá tàn nhẫn.

---

# 14. Quy tắc bàn giao

Nếu giao máy cho đồng nghiệp, có thể ghi ngắn:

> **CẢNH BÁO: eMMC bên trong TV box được khóa read-only có chủ đích.**
>
> Hệ điều hành Armbian hiện tại chạy từ SD card.
>
> Không cài Armbian vào eMMC.
>
> Không chạy các công cụ cài OS xuống internal storage.
>
> Khi thực sự cần mở eMMC, phải dùng `unlock-emmc.sh` và đọc README trước.

---

# 15. Cheat Sheet

### Khóa

```bash
chmod +x lock-emmc.sh
sudo ./lock-emmc.sh --apply
```

Nhập:

```text
LOCK mmcblk2
```

Kiểm tra:

```bash
sudo blockdev --getro /dev/mmcblk2
```

Phải là:

```text
1
```

---

### Mở khóa

```bash
chmod +x unlock-emmc.sh
sudo ./unlock-emmc.sh --remove
```

Nhập:

```text
UNLOCK mmcblk2
```

Kiểm tra:

```bash
sudo blockdev --getro /dev/mmcblk2
```

Phải là:

```text
0
```

---

# 16. Ghi chú cuối

Mục tiêu của bộ này không phải "bất khả xâm phạm".

Mục tiêu là:

> **Biến việc ghi vào eMMC từ một thao tác dễ làm nhầm thành một hành động phải được thực hiện có chủ ý.**

Đối với máy chạy Armbian từ SD card và cần giữ nguyên eMMC để recovery, đây là mức bảo vệ hợp lý: đủ khó để tránh tai nạn, nhưng vẫn có chìa khóa để chủ máy mở lại khi thực sự cần.
