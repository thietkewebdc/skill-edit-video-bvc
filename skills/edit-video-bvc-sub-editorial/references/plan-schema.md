# plan.json

```jsonc
{
  "words_file": "words.json",          // từ transcribe (đã sửa chính tả); sub nhỏ KHÔNG in đậm (MẪU CHUẨN) — "b" bỏ qua
  "mask": "mask.mp4",                  // từ text3d/matte.py — cần cho chữ "behind"
  "theme": "vang",                     // bộ màu: "vang" (mặc định) | "tim" (tím sáng, mẫu Short Hook Demo bản tím)
  "palette": {"accent_x": "#C08A3E"},  // (tùy chọn) thêm/ghi đè màu trong bảng PAL
  "sub": {"y": 0.52, "fs": 70, "max_words": 4, "min_words": 2, "max_chars": 24},   // (tùy chọn) — video DỌC, mặc định = MẪU CHUẨN (2–4 từ)
  // video NGANG tự dùng: {"y": 0.86, "fs": 54, "font": "semi", "max_words": 12, "min_words": 8, "max_chars": 64,
  //                      "halo": true, "keep_shown": true}  → 1 dòng 8–12 từ, giữ nguyên câu (SKILL.md luật 8b)
  // "sub": {"join": ["đảo síp", "minthis spa"]} → từ ghép/tên riêng riêng của video, không bao giờ bị ngắt giữa (luật 8c)
  "sub_zones": [{"start": 9.3, "end": 22.5, "y": 0.86, "halo": true}],  // (tùy chọn) dời sub trong đoạn đó — VD đoạn quay
                                       // màn hình / B-roll có chữ cháy sẵn ở giữa khung; cụm sub CHỒNG lên vùng là dời, bỏ qua né mặt
  "proper_nouns": ["Phước", "Hồ Mạnh Thắng"],  // tên riêng của video (ngoài danh sách sẵn: YouTube, Claude, ChatGPT, Việt Nam…)
                                       // sub nhỏ VIẾT THƯỜNG hết, chỉ tên riêng/thương hiệu + chữ có hoa giữa (AI, TikTok) giữ hoa
  "subs": true,                        // false = tắt sub thường
  "hook_boom": true,                   // boom trầm ở khoảnh khắc chữ đầu tiên
  "sfx_volume": 1.0,
  "moments": [ ... ]
}
```

## Khoảnh khắc chữ (`type` mặc định `"text"`)
```jsonc
{"style": "serif_pair", "start": 2.34, "end": 3.3,
 "lines": ["deserves the", "investment"]}
```
| Khóa | Ý nghĩa |
|---|---|
| `style` | preset trong [kieu-chu.md](kieu-chu.md) |
| `start`, `end` | giây. Chữ chỉ hiện trong khoảng này |
| `lines` | danh sách dòng: chuỗi, hoặc object để ghi đè thuộc tính dòng |
| `y`, `x` | tâm khối (tỉ lệ khung) |
| `behind` | true = nằm sau người (cần `mask`) |
| `auto_place` | false = không tự dời khi vi phạm luật che (chỉ báo) |
| `enter` | `blur` (mặc định) · `pop` (bật từ 84%) · `rise` (trồi lên) · `none` |
| `exit_s` | thời gian blur-out (mặc định 0.2) |
| `drift` | độ phóng chậm trong lúc giữ (0.03 = 3%) |
| `gap` | khoảng dòng (hệ số theo em, âm = chồng lên nhau) |
| `sync` | true (mặc định): mỗi từ hiện theo mốc nói trong words.json |
| `hide_subs` | ép ẩn/hiện sub (mặc định: tầng giữa ẩn, tầng trên chỉ ẩn lúc đang nói từ đó) |
| `sfx` | danh sách SFX thay mặc định, `[]` = im lặng |
| `sfx_add` | thêm `[[giây, "kind"], ...]` |

Thuộc tính **dòng**: `text`, `font` (`serif` `serif_i` `serif_mi` `light` `semi` `bold` `xbold`), `w` hoặc `fs`, `color`
(tên trong PAL, `"#hex"`, list = gradient ngang, `{"stops": [...], "dir": "v"}` = gradient dọc), `caps`, `glow`, `shadow`,
`halo` (`true` = quầng trắng mềm sau chữ TỐI trên nền rối · `"dark"` = quầng tối mềm sau chữ SÁNG nét mảnh — vàng/kem — trên trời trắng),
`dx` (lệch ngang, tỉ lệ khung), `at` (list giây cho từng từ), `t` (giây dòng hiện nếu không đồng bộ),
`swap` (`[{"text": "goes", "t": 30.84}, ...]`), `strike` (`{}` hoặc `{"t": 13.4, "color": "red"}`), `end`.

## Loại đặc biệt
```jsonc
{"type": "pills", "start": 33.0, "end": 35.8, "fs": 48, "items": [
   {"text": "Nhân cách", "t": 33.04, "x": 0.22, "y": 0.41},
   {"text": "Chính trực", "t": 33.84, "x": 0.50, "y": 0.535}]}

{"type": "scatter", "start": 23.4, "end": 25.4, "fs": 64, "items": [
   {"text": "quảng cáo", "t": 23.44, "x": 0.30, "y": 0.44},
   {"text": "tiếp cận tối đa,", "t": 24.7, "x": 0.66, "y": 0.52}]}

{"type": "image", "file": "logo_zillow.png", "start": 21.2, "end": 22.3, "x": 0.22, "y": 0.44, "w": 0.28}

{"type": "flash", "t": 10.78, "riser": true}

{"type": "bubble", "start": 42.76, "end": 44.0, "text": "Bấm link ở tiểu sử nhé.",
 "avatar": "avatar_tron.png", "x": 0.56, "y": 0.50}          // không có avatar → "avatar_text": "H"
```
Ảnh logo và avatar: PNG nền trong suốt (avatar đã cắt tròn sẵn). Đường dẫn tương đối tính theo thư mục chứa plan.json.
