# Chữ chìm SAU nhân vật (hiệu ứng 3D)

Kỹ thuật: tách người khỏi nền → render lớp chữ lên video → đè lại lớp NGƯỜI (lấy từ video gốc) lên trên chữ.
Chữ nằm sau đầu/vai → có chiều sâu, và **không bao giờ che mặt**. Làm lần đầu cho Trailer "Nút bạc" (2026-09-26), chủ kênh khen "Quá tốt".

Kích hoạt khi người dùng nói: "chữ phía sau nhân vật", "chữ chìm sau người", "chữ 3D sau người", "tách nhân vật ra chồng lớp chữ".

## Luật chủ kênh (đã chốt)
| # | Luật |
|---|---|
| 1 | Mỗi **chữ cái** bị người che **tối đa 1/2**; **tối đa 2 chữ cái** bị chạm → không che hết từ, luôn đọc được. |
| 2 | Các dòng **rộng bằng nhau** — đổi cỡ chữ từng dòng (`"tw"`), không dùng giới hạn 85% của engine. |
| 3 | Chữ **càng to càng tốt** trong giới hạn luật 1; mỗi khối nên có 1 chữ cái chìm một phần (chiều sâu). |
| 4 | Không che mặt (tự đúng vì người nằm trên chữ). |
| 5 | Cảnh **không có người ngồi** (cảnh chèn, quay màn hình, tay cầm đồ) → tắt mask (`--no-mask`), chữ nằm trên hình như bình thường. |
| 6 | Số liệu vẫn hiện theo lời nói (fx `sync` + `"at"`); tiêu đề = khối `sync` có `"static": true` từ 0s. |
| 7 | Lớp chữ render **không zoom punch** (`"punch": false`) — zoom làm lệch lớp chữ với lớp người. |

**Đánh đổi phải báo người dùng:** người ngồi giữa khung → khối chữ phải dạt 1 bên và hẹp lại (~0.36–0.44 bề ngang) để giữ luật 1 → chữ nhỏ hơn bản chữ nổi. Tiêu đề muốn thật to → đề xuất tách 3 dòng ngắn đặt 1 bên, hoặc riêng tiêu đề nổi trước người.

## Quy trình
```
T="<skill>/scripts/text3d"
python "$T/matte.py"    "<video>" -o "<work>/mask.mp4"                                  # tách người (~40s / 17s video 4K)
# viết <work>/plan_3d_base.json (mẫu dưới) — mục cần tự đặt vị trí có "auto_place": true
python "$T/place.py"    "<video>" "<work>/mask.mp4" "<work>/plan_3d_base.json" -o "<work>/plan_3d.json"
python "$T/engine3d.py" snap   "<video>" "<work>/plan_3d.json" --at 1,5,9 -o "<work>/qa3d"   # xem lớp chữ
python "$T/engine3d.py" render "<video>" "<work>/plan_3d.json" -o "<work>/text_layer.mp4" --preview
python "$T/compose.py"  "<work>/text_layer.mp4" "<video>" "<work>/mask.mp4" -o "<work>/preview_3d.mp4" --no-mask 13.2-17.5
# duyệt ảnh trích từ preview_3d.mp4 (mỗi khối ở lúc chữ cuối vừa hiện) → render bản cuối (bỏ --preview) → compose
```
- `place.py` in từng khối: `tw` (độ rộng), `x`, `y`, % che nhiều nhất 1 chữ cái, số chữ cái bị chạm. `!! KHÔNG ĐẠT` → rút chữ, tách dòng, hoặc để khối đó nổi trước người (bỏ khỏi mask bằng `--no-mask`).
- Xem mask trước: trích vài khung `mask.mp4` — người trắng, nền đen, viền tóc/tay rõ. Cảnh mask lác đác (không có người) → đưa vào `--no-mask`.
- Video đã cắt (skill A–Z): chạy trên `cut_9x16_enh.mp4` / `cut_16x9_enh.mp4` (video gốc của bước compose = chính file cắt đó).

## Mẫu plan_3d_base.json
```jsonc
{
 "accent": "cyan",
 "emphasis": [
  {"start": 0, "end": 3.62, "fx": "sync", "static": true, "auto_place": true, "punch": false,
   "text": "NÚT BẠC YOUTUBE|{KIẾM BAO NHIÊU $}"},                          // tiêu đề: đứng yên từ frame 0
  {"start": 7.18, "end": 10.6, "fx": "sync", "auto_place": true, "punch": false,
   "text": "KÊNH YOUTUBE NÀY|{3 TỶ · 5 TỶ · 10 TỶ}",
   "at": [7.18, 7.42, 7.60, 9.02, 9.34, 9.54, 9.54, 9.68, 9.90, 9.90, 10.04]},  // 1 mốc / chữ (kể cả "·")
  {"start": 15.34, "end": 17.4, "fx": "sync", "tw": 0.84, "y": 0.5, "punch": false,   // cảnh không người: tự đặt tay
   "text": "NÚT BẠC NHỎ|{NHƯNG RẤT ĐẸP}", "at": [15.34, 15.50, 15.84, 16.16, 16.68, 17.00]}
 ]
}
```
Không dùng `"title"` của engine cho bản 3D (tiêu đề engine không dịch vị trí được) → dùng khối `sync` + `"static": true`.

## Cần có
- `scripts/text3d/rvm_mobilenetv3_fp32.onnx` (~14 MB, Robust Video Matting). Thiếu → **xin phép người dùng** rồi tải từ
  `https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx`.
- `pip install onnxruntime numpy` (CPU là đủ).
