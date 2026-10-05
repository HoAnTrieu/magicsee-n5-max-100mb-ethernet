# Dữ liệu report công khai

Bộ release chỉ chứa source DTB nền, patch, log Ethernet đã chọn lọc và summary kiểm chứng. Không đóng raw tar.gz debug, live DTS, uEnv riêng của máy, route/IP đầy đủ, MAC thật, root UUID hoặc SSID vào bản public.

`collect.py` chỉ đọc thông tin kernel, ethtool, counters eth0, Ethernet dmesg, lsblk không có UUID, mounts không có options, USB và một số Ethernet DT property. Nó không thu `/proc/cmdline`, toàn cây runtime DT hoặc file boot riêng.

Report được redact UUID chuẩn, MAC và địa chỉ IP theo pattern. Điều này không bao phủ mọi chuỗi tùy biến; có thể còn USB serial, hostname hoặc dữ liệu riêng trong driver log. Mở các file sau khi giải nén rồi đọc lại trước khi đăng issue. Không upload file nằm trong home hoặc debug archive gốc để thay cho reduced report.

Kernel release và PHY ID phải giữ vì cần cho chẩn đoán. Public evidence ghi rõ dữ liệu gốc bị lược để tránh nhầm bản reduced với một dump đầy đủ.
