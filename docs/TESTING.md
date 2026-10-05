# Test PHY, link, mạng và regression

[Validation hiện có](VALIDATION.md) · [Xử lý lỗi](TROUBLESHOOTING.md)

## 1. Xác nhận patch được nạp

```bash
uname -r
grep '^FDT=' /boot/uEnv.txt
tr -d '\000' < /sys/firmware/devicetree/base/soc/ethernet@ff3f0000/phy-mode
readlink -f /sys/class/net/eth0/phydev
```

Kỳ vọng: kernel 6.12.111-ophub, FDT tên N5 Max, mode `rmii`, endpoint cuối `mdio_mux-0.1:08`. Root model vẫn là X96 do metadata nền được giữ nguyên.

## 2. PHY và link trước, IP sau

```bash
sudo ip link set dev eth0 up
sleep 3
sudo ethtool eth0
sudo ethtool -i eth0
cat /sys/class/net/eth0/carrier
cat /sys/class/net/eth0/speed
ip -br link
sudo dmesg | grep -Ei 'eth0|ethernet|dwmac|stmmac|phy|mdio|rgmii|rmii'
```

Cần link yes, 100 Mb/s, Full, autoneg on, carrier 1 và log attach PHY nội. Nếu chưa có carrier, chưa debug DHCP. Không ép speed/autoneg để che lỗi.

## 3. IPv4 và ping đi qua eth0

```bash
ip -4 -br addr show dev eth0
ip -4 route show default dev eth0
```

Nếu máy dùng NetworkManager và eth0 chưa có IP sau khi link đã lên:

```bash
nmcli device status
sudo nmcli device connect eth0
```

Thay `ETH_GATEWAY_IP` bằng gateway thực tế:

```bash
ping -I eth0 -c 100 ETH_GATEWAY_IP
ip -s link show dev eth0
```

Ghi lại sent/received/loss, min/avg/max RTT, counters trước/sau và dmesg. Ping hữu hạn không chứng minh không bao giờ mất gói.

Trên Windows có thể kiểm tra khả năng truy cập IP eth0 bằng PowerShell:

```powershell
ping.exe ETH0_IP
```

Đây là test truy cập địa chỉ; nếu box bật Wi-Fi cùng subnet, Linux có thể nhận traffic địa chỉ eth0 trên interface khác. Kiểm tra counters eth0 hoặc dùng phép đo được bind rõ ràng bên dưới.

## 4. Throughput ưu tiên iperf3

Trên một máy Linux LAN khác:

```bash
iperf3 -s
```

Trên N5 Max, thay `LAN_SERVER_IP` và `ETH0_IP` bằng IPv4 thật:

```bash
iperf3 -c LAN_SERVER_IP -B ETH0_IP --bind-dev eth0 -t 60
iperf3 -c LAN_SERVER_IP -B ETH0_IP --bind-dev eth0 -t 60 -R
```

`--bind-dev` cần phiên bản iperf3 hỗ trợ và có thể cần sudo. Nếu phiên bản không hỗ trợ, dùng `-B ETH0_IP` cùng route đến server rõ ràng qua eth0 và theo dõi counters. TCP Mbps của sender/receiver có thể khác; ghi cả hai, retransmits và thời gian. Link 100 Mbps là line rate, throughput TCP thấp hơn do overhead.

## 5. Windows không cài iperf3: HTTP estimate tùy chọn

Trên box, dùng file trong RAM để giảm ảnh hưởng tốc độ SD. Lệnh tạo 64 MiB; bảo đảm `/dev/shm` đủ chỗ:

```bash
mkdir -p /dev/shm/n5max-http-test
dd if=/dev/zero of=/dev/shm/n5max-http-test/test.bin bs=1M count=64 status=progress
python3 -m http.server 8000 --bind ETH0_IP --directory /dev/shm/n5max-http-test
```

Trong PowerShell Windows:

```powershell
curl.exe --output NUL --write-out "bytes=%{size_download} seconds=%{time_total} bytes_per_second=%{speed_download}\n" http://ETH0_IP:8000/test.bin
```

Tính Mbps = bytes_per_second × 8 / 1.000.000. MB/s dùng 1.000.000 byte; MiB/s dùng 1.048.576 byte. HTTP có overhead Python/server, không thay thế benchmark TCP. Bind server vào IP vẫn chưa cưỡng chế ingress interface trong mọi cấu hình Linux; đọc counters eth0 để xác nhận traffic. Dừng server bằng Ctrl+C, rồi dọn đúng file test:

```bash
rm /dev/shm/n5max-http-test/test.bin
rmdir /dev/shm/n5max-http-test
```

HTTP server này chỉ dùng tạm trong LAN tin cậy. Nếu firewall chặn, kiểm tra rule cổng 8000 theo cấu hình đang dùng; không vô hiệu hóa toàn bộ firewall.

## 6. Regression và theo dõi lâu hơn

```bash
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
findmnt /
findmnt /boot
lsusb
ip -br addr
ip -s link show dev eth0
sudo ethtool -S eth0
sudo dmesg | grep -Ei 'Link is|Cannot attach|reset|timeout'
```

Đọc các thermal_zone type/temp để theo dõi nhiệt độ. Theo dõi tải mạng lâu hơn, rút/cắm lại cáp và cold boot khi có khả năng phục hồi. Không chạy ghi thử lên eMMC để test patch Ethernet.

## 7. Report cho cộng đồng

```bash
sudo python3 scripts/collect.py
```

Script tạo `/tmp/n5max-public-report-*.tar.gz`, chỉ đọc boot/network và ghi archive mới. Đọc nội dung trước khi upload. Kèm exact kernel, PCB revision nếu biết, checksum nền, link, ping, throughput hai chiều và thời gian quan sát. Không gửi raw debug archive cũ. Xem [PRIVACY](PRIVACY.md).
