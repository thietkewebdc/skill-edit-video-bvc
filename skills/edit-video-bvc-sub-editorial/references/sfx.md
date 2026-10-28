# SFX

Mẫu gốc **không có nhạc nền**. Giọng nói chiếm trọn, SFX nằm dưới giọng, chỉ vừa đủ cảm thấy. Master mặc định **-9 dB**.
Chỉnh to/nhỏ cả video bằng `"sfx_volume"` trong plan (1.0 = mặc định).

| kind | Âm | Engine tự gắn khi |
|---|---|---|
| `boom` | sub-bass ~44 Hz nở dần 2.4s | khoảnh khắc chữ đầu tiên (hook), tắt bằng `"hook_boom": false` |
| `whoosh_soft` | whoosh hơi, 0.55s | mọi chữ ở tầng trên (đặt sớm 0.12s) |
| `air` | whoosh rất ngắn, mỏng | dòng khóa của `serif_pair` / `thin_caps` / `gradient_serif` |
| `swipe` | tiếng quét 0.3s | vạch gạch `strike` |
| `shimmer` | chuông cao lấp lánh | `neon` |
| `pop_soft` | pop nhẹ | mỗi badge `pills`, mỗi từ `scatter` |
| `pop` | pop rõ hơn | `image`, `bubble` |
| `boom_soft` | thump trầm ngắn | `bubble` |
| `riser` + `hit` | riser 0.8s dồn vào hit | `flash` |
| `tick` | tick nhỏ | chỉ dùng qua `sfx_add` |

Sub thường **không có SFX**.

## Dùng âm riêng
Thả file **WAV 16-bit** vào `sfx/` của skill, đặt tên đúng theo kind (`boom.wav`, `swipe.wav`, `pop_soft.wav`…).
Engine sẽ dùng file đó thay cho âm tự tạo. Gain theo từng kind vẫn giữ như trên.
