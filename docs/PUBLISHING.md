# Đăng dự án lên GitHub

Tên repo gợi ý: **magicsee-n5-max-ethernet**.

Description:

```text
Verified internal PHY/RMII Ethernet fix for one Magicsee N5 Max S905X3 Fast Ethernet board on ophub Armbian 6.12.111, with safe deployment and rollback.
```

Topics: `amlogic`, `s905x3`, `magicsee`, `n5-max`, `armbian`, `device-tree`, `ethernet`, `rmii`, `linux`.

## Cách 1: Web GitHub

1. Tạo repo mới, chọn Public nếu muốn công khai. Không tự tạo README/LICENSE khác vì ZIP đã có.
2. Giải nén ZIP, mở thư mục `magicsee-n5-max-ethernet`.
3. Upload **nội dung bên trong** thư mục vào gốc repo để README.md nằm ngay root; không upload nguyên ZIP như source duy nhất.
4. Upload hoặc commit cả `.github/`, `.gitignore`, `.gitattributes`. Các file này cần được giữ để CI chạy và đảm bảo line endings.
5. Kiểm tra README hiển thị, liên kết tài liệu mở được và workflow Verify pass.
6. Tạo release tag `v1.0.0`, dùng nội dung `docs/RELEASE_NOTES.md`, đính kèm ZIP và file checksum ZIP nếu muốn.

## Cách 2: Git trên Windows

Mở PowerShell trong thư mục source đã giải nén. Thay OWNER bằng tài khoản của bạn:

```powershell
git init
git add .
git commit -m "Release verified N5 Max S905X3 Ethernet fix"
git branch -M main
git remote add origin https://github.com/OWNER/magicsee-n5-max-ethernet.git
git push -u origin main
git tag v1.0.0
git push origin v1.0.0
```

Phải tạo repo rỗng trên GitHub trước khi push. Lệnh yêu cầu Git và xác thực tài khoản của bạn. Không có tài khoản/token hoặc URL repo cá nhân được đóng trong release.

## Tái đóng gói từ Linux

Sau khi sửa source/doc, cập nhật checksum và tạo archive:

```bash
bash scripts/build.sh
python3 scripts/package.py
```

Script dùng allowlist thư mục public, bỏ cache/build/report và chạy verifier/tests trước khi tạo ZIP trong `release/`. Nếu sửa DTS/DTB thì phải cập nhật project.json và kiểm chứng trên máy trước khi phát hành; không tự đổi hash để gọi binary mới là hardware-tested.

## Trước lần phát hành sau

Ghi rõ kernel, checksum và revision mới đã test. Giữ nguồn tham chiếu, patch, license/NOTICE và giới hạn kiểm chứng. Với upstream Linux/ophub, nên chuyển patch từ DTS decompile sang source có labels/includes và kiểm tra bindings đúng source commit. Một issue closed không chứng minh patch này là fix chính thức.

Dự án và release chưa được đăng tự động. Chủ dự án chủ động chọn tên repo, thông tin tác giả và phạm vi public khi đăng.
