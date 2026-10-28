# Bộ Skill `edit-video-bvc` — Thiết Kế Web DC

Phát triển bởi **Bùi Viết Cường** (Thiết Kế Web DC). Nền tảng gốc: bộ skill chuyên gia **HMT của Hồ Mạnh Thắng**; bản này đổi tên, chỉnh sửa và bổ sung (ví dụ giai đoạn C: ảnh bìa/thumbnail chuẩn TikTok). Các skill chạy trong **Claude Code**, xử lý video ngay trên máy bạn.

| Skill | Làm gì | Gọi bằng |
|---|---|---|
| `edit-video-bvc-tu-a-z` | Edit từ A–Z: cắt ghép (bỏ ngừng, vấp, lặp), zoom xen kẽ, phủ chữ khối vàng/xanh, minh họa động, SFX, cắt nhiều short, chèn b-roll, chữ chìm sau người, **ảnh bìa/thumbnail** | `/edit-video-bvc-tu-a-z` |
| `edit-video-bvc-chia-se` | Chỉ phủ chữ + hiệu ứng lên video đã cắt (engine `sm_overlay`) | `/edit-video-bvc-chia-se` |
| `edit-video-bvc-sub-editorial` | Sub kiểu tạp chí sang trọng: 1 chữ khóa vàng + sub nhỏ, tự né mặt | `/edit-video-bvc-sub-editorial` |
| `edit-video-bvc-animation` | Video đồ họa phẳng (motion graphics) từ file voice over | `/edit-video-bvc-animation` |
| `edit-video-bvc-nguoi-que` | Hoạt hình người que nét chì từ file voice over | `/edit-video-bvc-nguoi-que` |

## Cài đặt (macOS)
```bash
git clone https://github.com/thietkewebdc/skill-edit-video-bvc.git
cd skill-edit-video-bvc && ./install.sh
```
Cần: Claude Code, ffmpeg (có libass), Python 3.10+, `pip install numpy faster-whisper opencv-python` (thêm `onnxruntime` cho chữ chìm sau người). Mô hình RVM tách người: tải về từ https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx rồi đặt cạnh `matte.py` trong `scripts/text3d/`.
Mỗi skill có `SKILL.md` ghi rất chi tiết quy tắc và quy trình.

## Lưu ý
- Video phải có **lời nói rõ**; video chỉ có nhạc/tiếng nhỏ làm Whisper bịa câu "Hãy subscribe…".
- Quay dọc ≥ 1080p cho hình đẹp. Máy 8GB: Whisper dùng `int8`, mỗi lần 1 video.
- Chỉ kiểm tra trên macOS (Apple Silicon). Windows/Linux chưa thử.
- Giấy phép: [LICENSE.txt](LICENSE.txt).
