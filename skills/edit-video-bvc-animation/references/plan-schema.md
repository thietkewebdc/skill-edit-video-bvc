# plan.json — cấu trúc đầy đủ

```json
{
  "audio": "voice.mp3",            // voice over (mp3/wav/m4a hoặc video lấy tiếng) — tương đối theo thư mục plan
  "words": "words.json",           // từ lệnh transcribe
  "size": [1080, 1920],            // 9:16 mặc định; [1920,1080] cho ngang
  "fps": 30,
  "tail": 0.5,                     // giữ thêm sau chữ cuối (luật đuôi 0.5s)
  "intro_label": "Mở đầu",         // nhãn phần trước chương 01 ("" = ẩn)
  "chapters": [ { "say": "Tôi không viết những dòng này", "label": "Kết" } ],  // nhãn phần thêm (ngoài màn chapter)
  "chapter_pill": true,            // false = ẩn nhãn phần góc phải
  "progress": true,                // thanh tiến độ vàng mép trên
  "brand": null,                   // chữ pill góc trái trên — MẶC ĐỊNH KHÔNG CÓ (đã bỏ logo)
  "sfx": true, "sfx_volume": 0.5,
  "music": null, "music_db": -24,  // nhạc nền tùy chọn, tự hạ khi có giọng
  "scenes": [ ... ]
}
```

## Màn (scene)
| Khóa | Ý nghĩa |
|---|---|
| `say` | cụm lời mở màn (màn bắt đầu ở từ đầu tiên − 0.12s). Bỏ trống → dùng chữ của `text` đầu tiên. |
| `at` | ép mốc giây tuyệt đối (thay cho `say`) |
| `lead` | lùi sớm hơn lời (mặc định 0.12) |
| `bg` | `dark` `green` `red` `yellow` `cream` `white` `mint` `crimson` `sunset` |
| `deco` | `circles` (mặc định) · `stripes` (mặc định màn chương) · `lines` · `dots` · `sunset` · `none` — chuỗi hoặc mảng |
| `trans` | `tilt` `blinds` `circle` `split` `slide` `wipe` `zoom` `fade` `cut` — bỏ trống = tự chọn (cùng nền → fade) |
| `td` | thời lượng chuyển (0.45 / fade 0.25) |
| `valign` | `center` (mặc định) · `top` · `bottom` |
| `gap`, `top`, `bottom` | khoảng cách giữa mục (56), lề trên (200), lề dưới (160) — px ở khung 1080 |
| `text` | tắt nhanh: thêm 1 mục `text` đứng đầu; `size`, `textSay` đi kèm |
| `items` | danh sách mục, xếp dọc theo thứ tự |

Màn kết thúc khi màn sau bắt đầu → **không có khoảng trống**.

## Khóa chung cho mọi mục
| Khóa | Ý nghĩa |
|---|---|
| `say` / `at` | lúc mục bật (cụm lời trong màn / giây tính từ đầu màn). Mặc định: vào màn là bật. |
| `in` | `pop` `up` `drop` `left` `right` `tilt` `zoom` `fade` `none` |
| `idle` | `bob` `float` `sway` `shake` `pulse` `spin` `wobble` |
| `move` | `{ "to": [dx, dy], "say"/"at", "dur": 0.6, "rot": 0 }` dịch chuyển sau khi bật |
| `out` | `{ "say"/"at" }` mờ đi |
| `dx`, `dy`, `mt` | xê dịch / lề trên thêm |
| `sfx` | ghi đè tiếng (`pop` `tick` `ding` `whoosh` `swipe` `thud` `boom` `burst`) hoặc `null` |

## Thành phần
**text** — `text` (bọc `*…*` để nhấn màu + gạch chân, `\n` xuống dòng), `size` (`xs` 40 · `s` 54 · `m` 72 · `l` 92 · `xl` 130 · `xxl` 180 hoặc số), `say` (cụm lời để khớp từng từ; mặc định = chính chữ), `color`, `acc`, `ul`, `underline:false`, `align`, `w`, `instant`. Màn chỉ có chữ → mặc định `l`.

**emoji** — `e`, `size` (200), `disc` (màu đĩa tròn phía sau: `yellow` `cream` `white`…), `swap: [{e, say}]` đổi hình đúng lời.

**list** — `items: [{t, say, icon}]`, `icon` chung: `check` `x` `ok` `dash` `dot` `num` hoặc emoji (`⏳`); `style` `light`/`dark`; `w`, `fs`.

**timer** — `from`, `to` ("mm:ss" hoặc số), `ring: [đầu, cuối]` (0–1), `emoji` (⏱️ / 🎧 / false), `color` vòng, `run: {say}`, `dur`, `fmt: "num"`.

**usage** — `title`, `from`, `to` (số lẻ được: 1.8), `unit`, `suffix` ("+"), `note`, `rows: [{label, v, fill, color}]`, `color` số lớn, `barColor`, `run: {say}`.

**battery** — `from`, `to`, `drain: {say}`, `dur`.

**vs** (chiếm cả màn) — `top`/`bottom`: `{cap, e, t, bg, say}`.

**phone** — `feed: [{e, cap, bg, likes}]`, `header`, `every` (giây/lần vuốt), `hand`, `tilt`, `run: {say}`.

**chapter** — `num`, `label` (mặc định "PHẦN 01"), `title` (có `*…*`), `chap` (nhãn góc phải). Tự thêm nhãn phần "01 · …".

**quote** — `text`, `say`, `by`, `size`, `mark` (màu dấu “).

**polaroid** — `e` hoặc `src` (ảnh), `cap`, `bg`, `rot`, `w`.

**cycle** — `nodes: [...]`, `center` (emoji), `per` (giây/nút), `spin`.

**timeline** — `steps: [{when, t, say}]`.

**chart** — `points` (0–1), `xl`, `xr`, `color`, `run`, `dur`.

**notify** — `items: [{e, t, sub, say}]`.

**chat** — `title`, `msgs: [{t, me, say}]`, `w` (780), `h` (560), `fs` (30 — cỡ chữ tin; tiêu đề = 0.8×).

**neq** — `items: [{a, b, say, strike:{say}}]` → "a ≠ ~~b~~".

**radial** — `center` ("CHẠM"), `around: [emoji…]`, `burst: {say}`.

**map** — `from`, `car`, `tags: [{t, say, pos, bg}]`, `path` (SVG d, tùy chọn), `run`, `dur`.

**grid** — `rows`, `cols`, `cell`, `label`, `break: {say}` (vỡ vụn).

**confetti** (cả màn) — `n`, `colors`, `y`, `say`/`at`.

**notebook** — `lines`, `dur`, `run`.

**plant** — `e` (🌱/🌷/🌳), `swap: [{e, say}]`, `roots` (true), `tool` (🪏), `rootsAt`.

**pill** — `t`, `bg` (`green` `red` `yellow` `dark`…), `caps`, `rot`, `fs`.

**screen** — `e: [emoji…]`, `badge` ("240p"/"4K"), `blur`, `stamps: [{t, say}]`, `bg`.

**ghost** (nền) — `t`, `size`, `y` (0–1), `color`.

**image** — `src` (tương đối thư mục plan), `w`, `h`, `radius`, `fit`.

**row** — `items: [...]` xếp ngang, `shelf: true` (kệ dưới), `gap`, `align`.

**spacer** — `h`.
