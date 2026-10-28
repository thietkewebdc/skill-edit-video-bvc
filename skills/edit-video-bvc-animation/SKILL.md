---
name: edit-video-bvc-animation
description: Tạo VIDEO ANIMATION ĐỒ HỌA PHẲNG (motion graphics, không có người) từ một file VOICE OVER, theo phong cách kênh Hồ Mạnh Thắng (mẫu "Tôi không lười, tôi chỉ tiêu xài quá sớm cuộc đời mình") — không logo. Nền màu đặc đổi liên tục (than, xanh rêu, đỏ cam, vàng mù tạt, kem, bạc hà) có vòng tròn mờ trôi; chữ đậm hiện TỪNG TỪ đúng lúc nói, cụm nhấn đổi màu + gạch chân kéo; đổi màn 2–3s bằng panel nghiêng/rèm/vòng tròn/tách đôi; minh họa bằng emoji và widget: đồng hồ vòng đếm, điện thoại lướt feed + ngón tay, thẻ "thời gian sử dụng" đếm số + thanh, danh sách ✓/✗ bật theo lời, pin cạn, VS chia đôi, màn chương 01/02, trích dẫn, polaroid, vòng lặp, dòng thời gian, biểu đồ tăng, thông báo, chat, ≠ gạch ngang, nút CHẠM bung icon, bản đồ xe chạy, lưới vỡ, confetti, sổ tay tự viết, cây mọc/héo + rễ, màn hình 240p/4K + dấu SPOILER, biển hoàng hôn; thanh tiến độ + nhãn phần góc phải; SFX tự tổng hợp, −14 LUFS; dọc 9:16 (ngang 16:9 được). Dùng khi người dùng nói "làm video animation", "video đồ họa từ voice", "motion graphics", "video kiểu Hồ Mạnh Thắng", "video kiểu Tôi không lười", "animation chữ + emoji", hoặc gọi /edit-video-bvc-animation. Người que nét chì → edit-video-bvc-nguoi-que.
---

# Skill: VIDEO ANIMATION ĐỒ HỌA PHẲNG từ voice over

Người dùng đưa **voice over** (mp3/wav/m4a, hoặc video lấy tiếng) → skill ra **video animation hoàn chỉnh**. Không có người, không logo, không chữ "bản test".

Engine: `scripts/anim.py` (CLI) + `runtime/engine.js` (hình vẽ bằng HTML/CSS, Chrome headless chụp từng khung → ffmpeg NVENC). Font Inter trong `fonts/`, emoji dùng font màu của máy (Segoe UI Emoji).
Gọi bằng **đường dẫn tuyệt đối**: `python "$HOME/.claude/skills/edit-video-bvc-animation/scripts/anim.py" …`
Cần: Python 3.10+, `pip install playwright faster-whisper numpy`, Chrome hoặc Edge đã cài, ffmpeg trên PATH.

Đọc trước khi viết plan:
- [references/phan-tich-video-mau.md](references/phan-tich-video-mau.md) — phong cách mẫu, bảng màu, ý nào → thành phần nào.
- [references/plan-schema.md](references/plan-schema.md) — mọi khóa của `plan.json` và 29 thành phần.
- [examples/plan-mau.json](examples/plan-mau.json) — plan 45 màn chạy thật trên voice mẫu (có đủ mọi thành phần).

## Luật của kiểu này
| # | Luật |
|---|---|
| 1 | **Đổi màn dày: 2–4s/màn** (mẫu ~2.5s). 1 màn = 1 ý / 1 vế câu. Không để màn đứng > 8s (`check` báo). |
| 2 | **Chữ trên màn là bản RÚT GỌN của lời** (≤ 3 dòng, ≤ ~12 từ), viết đúng chính tả dù whisper nghe sai. Từng từ hiện đúng lúc nói (engine tự dò trong lời). |
| 3 | **Nhấn 1 cụm/màn** bằng `*…*` (đổi màu + gạch chân) — từ đắt, số liệu, vế đối lập. Mọi số liệu đều nhấn / minh họa. |
| 4 | **Cứ 1–2 màn chữ thì 1 màn có hình**: emoji to (đĩa tròn), widget (đồng hồ, pin, điện thoại, thẻ số…). Hình minh họa ẨN DỤ của ý, không chép chữ. Liệt kê → `list` bật từng dòng theo lời. So sánh → `vs`. Lặp lại/nghiện → `cycle`. Tiến bộ dần → `chart`/`timeline`. |
| 5 | **Màu nền đổi gần như mỗi màn**, xoay vòng dark/red/yellow/cream/green/mint; giữ cùng nền khi chữ chỉ đổi tiếp ý (tự fade). Màn chương luôn `red` hoặc `dark` + sọc. |
| 6 | **Chia phần**: video > 90s → 3–6 màn `chapter` ("01 · …") ở chỗ đổi ý lớn; nhãn phần tự hiện góc phải; thêm `"chapters": [{"say": …, "label": "Kết"}]` cho đoạn kết. |
| 7 | **Không logo** (`brand` để trống) trừ khi người dùng đưa tên kênh của họ. |
| 8 | **Âm**: voice + SFX nhẹ (whoosh chuyển màn, pop, tick danh sách) `sfx_volume` 0.5; video > 3 phút dùng 0.35. Nhạc nền chỉ khi người dùng đưa file. Tự chuẩn −14 LUFS, đuôi 0.5s. |
| 9 | Luôn gửi **bảng đề xuất màn** (mốc · lời · chữ trên màn · hình) cho người dùng duyệt trước khi render bản cuối nếu video > 2 phút; video ngắn thì làm luôn rồi gửi nháp. |

## Quy trình
1. **Thư mục làm việc** `<tên voice>__anim/` cạnh file voice.
2. **Nghe voice**: `transcribe VOICE -o WORK/words.json` → `words.json` + `words.txt` (large-v3, GPU). Đọc `words.txt` để hiểu nội dung. KHÔNG cần sửa chính tả words.json — chỉ cần chép `say` giống cách whisper viết (engine dò mờ, bỏ dấu, sai 1 ký tự vẫn khớp).
3. **Lên màn**: chia lời thành màn 2–4s; mỗi màn chọn `bg`, chữ rút gọn, hình. Mở màn bằng `say` = 3–5 từ đầu của vế câu đó, chép từ `words.txt`. Video dài → viết script Python nhỏ sinh `plan.json` cũng được. Màn mở đầu (hook) có thể đặt theo công thức trong [references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt).
4. `check WORK/plan.json` → sửa hết cảnh báo (lời không thấy, màn quá ngắn/dài, tràn khung, chữ > 3 dòng).
5. `snap WORK/plan.json --sheet --cols 8` → **mở `qa/sheet.png` xem thật** (checklist: [references/checklist-qa.md](references/checklist-qa.md)). Soi thêm màn động bằng `snap --at 12.3,12.8`.
6. `render WORK/plan.json -o WORK/<tên>_anim.mp4` (nháp: `--preview`, một đoạn: `--from 30 --to 60`).
7. Tách tờ khung vài đoạn để kiểm chuyển động, rồi giao file + tóm tắt số màn/phần.

```
S="$HOME/.claude/skills/edit-video-bvc-animation/scripts/anim.py"
python "$S" transcribe "voice.mp3" -o "WORK/words.json"
python "$S" check  "WORK/plan.json"
python "$S" snap   "WORK/plan.json" --sheet --cols 8            # mọi màn, ảnh ở qa/
python "$S" snap   "WORK/plan.json" --scenes 10-20 --pos 0.5
python "$S" render "WORK/plan.json" -o "WORK/video_anim.mp4"
```
Tốc độ đo được: 60s video 1080×1920 → 22s (4 luồng Chrome + NVENC, ~90 khung/s). `--cpu` ép libx264, `--workers N` đổi số luồng.

## Plan tối thiểu
```json
{
  "audio": "voice.mp3", "words": "words.json",
  "scenes": [
    { "bg": "dark", "text": "Tôi *không lười.*", "size": "xl" },
    { "bg": "red", "say": "tôi chỉ tiêu xài", "text": "Tôi chỉ *tiêu xài quá sớm*\ncuộc đời của mình." },
    { "bg": "yellow", "say": "Có một giai đoạn", "items": [
      { "type": "timer", "from": "00:00", "to": "07:12" },
      { "type": "text", "text": "Không làm nổi việc gì\nquá *30 phút*", "say": "không thể làm được một việc gì quá 30 phút" } ] }
  ]
}
```

## Lưu ý kỹ thuật
- Màn bắt đầu ở từ đầu của `say` (lùi 0.12s) và kéo tới màn sau → không khoảng trống. Màn 1 luôn từ 0s.
- `text` tự dò `say` = chính chữ của nó; khi chữ rút gọn khác xa lời, **ghi `say` là cụm lời thật** để từng từ hiện đúng nhịp.
- Mục con (dòng list, tin chat, mốc timeline, dấu stamp, swap emoji…) đều nhận `say`/`at` riêng.
- Kích thước tính theo khung 1080 (dọc) — khung ngang 1920×1080 dùng cùng số, `valign`/`gap` chỉnh bố cục.
- Emoji hiển thị theo font máy (Windows 10: Segoe UI Emoji viền đen). Muốn giống mẫu hơn (emoji Noto bóng mịn) → hỏi người dùng cho tải Noto Color Emoji vào `fonts/` rồi thêm `@font-face` trong `runtime/style.css`.
- Thêm thành phần mới: viết hàm `C.ten = (it, ctx) => ({ el, upd(t) })` trong `engine.js` (mọi chuyển động là hàm của `t`), ghi vào `plan-schema.md`.
