# Kết quả phần cứng và giới hạn kiểm chứng

Ngày: **2026-10-05**. Test ID: `N5MAX-SM1-100M-01`. Số máy: **1**. PCB revision chưa ghi nhận. Dữ liệu public nằm tại [evidence](../evidence/hardware-validation.json).

## Trước và sau patch

| Hạng mục | Trước | Sau |
|---|---|---|
| Kernel | 6.12.111-ophub | Giữ nguyên |
| Endpoint MAC chọn | External mux branch 0 / address 0 | Internal branch 1 / address 8 |
| PHY attach | -22, capability thiếu tốc độ | Thành công |
| PHY driver của eth0 | Chưa attach | Meson G12A Internal PHY |
| Interface MAC | RGMII | RMII |
| Link / speed / duplex | No / Unknown | Yes / 100 Mbps / Full |
| Carrier | Không có link hợp lệ | 1 |
| Autonegotiation | Không có link | On; đọc được link partner |
| Ethernet DHCP | Chưa có | Có IPv4 |
| Route IPv4 | Chưa có eth0 | eth0 metric 100; wlan0 metric 600 |
| Lỗi attach trong captured dmesg | Có | Không |
| External MDIO endpoint | Có, ID 0 | Không enumerate |

Bằng chứng trực tiếp sau reboot:

```text
PHY [mdio_mux-0.1:08] driver [Meson G12A Internal PHY] (irq=25)
configuring for phy/rmii link mode
Link is Up - 100Mbps/Full - flow control rx/tx
```

PHY ID `0x01803301` đã được khai báo qua compatible trong DT; chưa có phép đọc PHYID register độc lập. Link partner, carrier, autoneg và DHCP là bằng chứng đường LAN hoạt động độc lập với ID khai báo. Sysfs có thể ghi interface `internal`; mode của MAC được xác nhận bằng DT runtime và log `phy/rmii`.

Runtime trước/sau chỉ khác sáu property Ethernet. DTB release so với runtime có các boot fixup RAM, bootargs/initrd và MAC như nền; không đóng cứng runtime DTS vào source.

## Regression quan sát

| Hạng mục | Sau reboot |
|---|---|
| Root / boot | SD ext4 / vfat mount bình thường |
| SD và eMMC | lsblk trùng trước; eMMC khoảng 29,1 GiB được nhận diện |
| USB | Danh sách enumeration trùng trước |
| Wi-Fi | QCA6174/ath10k SDIO vẫn kết nối, có IPv4 |
| CPU / DDR | 43,1°C / 44,1°C trong snapshot |
| Kernel config | Trùng trước patch |

Đây là kiểm tra boot, mount, enumeration và Wi-Fi; chưa phải stress I/O hoặc test mọi chức năng USB.

## Throughput chủ máy đã báo

Chủ máy sau đó báo test Windows → N5 Max truyền 1 GiB bằng netcat/pv: Windows tính **87,3 Mbps / 10,9 MB/s / 98,40 s**; phía N5 Max hiển thị **9,22 MiB/s**. Các con số được giữ theo nguồn, không gộp thành phép đo đồng bộ.

Đây là **kết quả tự báo qua hội thoại**, chưa có log đầy đủ kèm binding interface hoặc kết quả chiều ngược đủ dữ liệu trong bộ evidence này. Không gọi đó là benchmark iperf3 hoặc chứng minh packet loss bằng 0. Hai đầu có thể đo khoảng thời gian khác nhau; MB và MiB cũng khác đơn vị. Xem [TESTING](TESTING.md) để đo lại có ràng buộc Ethernet.

## Mức độ đã đạt

- Confirmed: bản patch tổng thể boot, attach PHY nội, RMII, link 100/full, carrier 1, DHCP trên máy đã test.
- Confirmed trong snapshot: storage mount/enumeration, USB enumeration, Wi-Fi còn hoạt động.
- Chưa test: độ bền dài hạn, nhiều cold boot, throughput có binding eth0 hai chiều, packet loss kéo dài, PCB revision khác, kernel khác, dtbs_check đúng source ophub.

Không thử riêng từng property để chứng minh mọi property đều bắt buộc. Kết quả xác nhận sáu thay đổi như một cấu hình tổng thể. DTB trong `dist/` vẫn giữ nguyên checksum của bản đã test.
