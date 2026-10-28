# Bộ Skill `edit-video-bvc` — Thiết Kế Web DC

Phát triển bởi **Bùi Viết Cường** (Thiết Kế Web DC), dựa trên nền tảng skill HMT của Hồ Mạnh Thắng. Chạy trong **Claude Code**, xử lý video ngay trên máy bạn.

| Skill | Làm gì | Gọi bằng |
|---|---|---|
| `edit-video-bvc-tu-a-z` | Edit từ A–Z: cắt ghép, phủ chữ khối, minh họa, SFX, cắt short, b-roll, chữ chìm sau người, ảnh bìa/thumbnail | `/edit-video-bvc-tu-a-z` |
| `edit-video-bvc-chia-se` | Phủ chữ + hiệu ứng lên video đã cắt | `/edit-video-bvc-chia-se` |
| `edit-video-bvc-sub-editorial` | Sub kiểu tạp chí | `/edit-video-bvc-sub-editorial` |
| `edit-video-bvc-animation` | Video đồ họa phẳng từ file voice | `/edit-video-bvc-animation` |
| `edit-video-bvc-nguoi-que` | Hoạt hình người que từ file voice | `/edit-video-bvc-nguoi-que` |

## Cài đặt (macOS)
```bash
git clone https://github.com/thietkewebdc/skill-edit-video-bvc.git
cd skill-edit-video-bvc && ./install.sh
```
Cần: Claude Code, ffmpeg (có libass), Python 3.10+, `pip install numpy faster-whisper opencv-python` (thêm `onnxruntime` cho chữ chìm sau người; mô hình RVM tải từ https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx, đặt cạnh `matte.py` trong `scripts/text3d/`).

Video cần có lời nói rõ; quay dọc từ 1080p cho hình đẹp. Chỉ kiểm tra trên macOS. Giấy phép: [LICENSE.txt](LICENSE.txt).
