# Rollback và khôi phục boot

[Triển khai](DEPLOYMENT.md)

Rescue luôn là `meson-sm1-x96-max-plus-100m.dtb`. Bản này giúp máy boot như trước patch; Ethernet có thể trở lại lỗi cũ sau rollback.

## Máy còn boot hoặc SSH được

Đọc backup trước khi restore:

```bash
sudo grep '^FDT=' /boot/uEnv.txt.n5max-backup
```

Nếu backup đúng cấu hình nền:

```bash
sudo cp /boot/uEnv.txt.n5max-backup /boot/uEnv.txt
grep '^FDT=' /boot/uEnv.txt
sudo sync
sudo reboot
```

Nếu backup thiếu hoặc không phải cấu hình cần khôi phục, mở `/boot/uEnv.txt` bằng editor và chỉ đổi FDT về:

```text
FDT=/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb
```

Không chép `reference/` đè lên file rescue của máy. Không chỉnh LINUX, INITRD, APPEND, root UUID hoặc kernel để rollback Ethernet.

## Máy không boot, rơi initramfs / BusyBox

1. Tắt nguồn, tháo SD khỏi box.
2. Cắm SD vào PC. Mở phân vùng FAT nhãn **BOOT**. Nếu Windows đề nghị format phân vùng Linux khác, hủy đề nghị đó.
3. `uEnv.txt` nằm ở gốc BOOT. Mở bằng editor text, đổi riêng dòng FDT về rescue như trên. Nếu backup đúng, có thể copy nội dung backup về uEnv.
4. Kiểm tra tên file vẫn là `uEnv.txt`, không thành `uEnv.txt.txt`; giữ nguyên các dòng khác.
5. Eject SD, cắm lại box và bật nguồn.

Không cần mount ROOTFS hoặc flash lại toàn bộ OS để đổi FDT.

## Gỡ patch

Sau khi boot lại rescue, DTB mới có thể để nguyên vì loader không chọn nó. Muốn dọn file, chỉ xóa `meson-sm1-magicsee-n5-max.dtb` sau khi xác nhận FDT đã chọn rescue. Giữ backup và rescue. Thư mục source không cần nằm trên box sau khi cài, nhưng nên giữ bản ZIP để tái lập.
