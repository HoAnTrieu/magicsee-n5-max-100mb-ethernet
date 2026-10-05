# Xử lý lỗi theo tầng

| Triệu chứng | Kiểm tra tiếp | Hành động |
|---|---|---|
| Boot fail/initramfs | FDT, rescue, uEnv trên BOOT | [Rollback](ROLLBACK.md) bằng SD; không thử DTB ngẫu nhiên |
| Runtime còn rgmii | uEnv và runtime phy-mode, checksum DTB | Xác định loader có nạp file mới; không chỉnh DHCP |
| Attach -22 còn xuất hiện | Kernel, phydev, MDIO endpoint, runtime cây | Thu reduced report; baseline/revision có thể khác |
| PHY attach nhưng carrier 0 | Cáp, switch, autoneg, port partner | Thử dây/port đã biết tốt; không đoán GPIO reset |
| Link 10 Mbps | ethtool partner và cáp | Xác định partner/cáp; chưa đạt mục tiêu 100 Mbps |
| Link yes nhưng chưa IPv4 | NetworkManager và DHCP | Kiểm tra profile/lease sau khi PHY đã hoạt động |
| Ping chạy nhưng không chắc LAN | Route, ping -I eth0, counters | Bind interface; Wi-Fi cùng subnet có thể che kết quả |
| Throughput thấp | CPU, counters, route, sender/receiver, storage | Đo iperf3 hai chiều có binding; không ép Gigabit |
| Installer STOP | Nội dung lỗi | [DEPLOYMENT](DEPLOYMENT.md); giữ guard, không sửa manifest để bypass |
| Model vẫn X96 | Runtime Ethernet topology | Bình thường; model giữ từ nền, không dùng nó để kết luận patch chưa nạp |

Đổi cả DTB sang một board khác từng làm máy mất boot. Giữ rescue làm nền và chỉ mở rộng patch khi có bằng chứng cụ thể. Linux 6.12 không thể dùng nguyên bindings/clock IDs/DTB từ vendor kernel hoặc CoreELEC cũ.
