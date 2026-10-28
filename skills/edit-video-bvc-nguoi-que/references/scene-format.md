# Định dạng `scenes.json`

```jsonc
{
 "voice": "D:/…/voice.mp3", "words": "words.json",
 "size": [1080, 1920],          // [1920,1080] cho ngang
 "fps": 30, "anim_fps": 15, "boil_fps": 6, "seed": 1,
 "rough": 1.0,                  // độ run nét chì (kiểu soft: 0.45; anim_fps 30, boil_fps 0)
 "trans": "fade",               // chuyển cảnh mặc định: fade | cut | dip | wipe
 "title": {"lines": ["GIA ĐÌNH", "HẠNH PHÚC NHẤT"], "dur": 5.0, "y": 0.24, "width": 0.8,
           "style": "pro",            // "pro" (mặc định: dải nâu + kem/vàng + vạch thoi) | "classic" (trắng viền nâu)
           "band_a": 0.55, "color": [250,242,222], "color2": [242,196,104], "tracking2": 0.16},
 "cast": {"dad": {"kind": "man", "h": 0.62}, "mom": {"kind": "woman", "h": 0.58, "dress": true}},
 "scenes": [
  {"i": 1, "start": 0.0, "end": 5.11, "text": "…",
   "bg": "path" | {"type": "path", "horizon": 0.55, …},
   "tone": "warm",
   "cam": {"zoom": [1.0, 1.08]} | {"from": [z, cx, cy], "to": [z, cx, cy]} | "none",
   "trans": "fade", "trans_d": 0.45,       // cách CẢNH NÀY xuất hiện
   "fx": [ … ],
   "items": [ … ]                          // hoặc "panels": [ … ] (chia màn hình)
  }
 ]
}
```

## Thời gian & hoạt ảnh
- Mọi thời gian tính **từ đầu cảnh** (giây) hoặc là **cụm từ trong câu**: `"t": "đổ lỗi"`, `"t": "đổ lỗi+0.5"`, `"t": "cùng nhau-0.3"` (khớp theo words.json; không tìm thấy → 0s và in cảnh báo).
- `keys`: danh sách `{ "t": …, "d": 0.6, <thuộc tính>: <giá trị> }`. Số (x, y, h, s, opacity, dark, glow, crack, broken, mend, grow, open, light, face, leaves…) **chuyển mượt** trong `d` giây; `pose` **hòa trộn góc** trong `d`; còn lại (expr, do, content…) đổi ngay.
- `appear` / `vanish`: thời điểm hiện dần / mờ dần (0.35s). Dùng cho phần tử đổi giữa câu.
- Phần tử vẽ theo **thứ tự trong `items`** (sau đè trước). Đám đông tự xếp sau→trước.

## Người que — `{"type": "fig", …}` (type mặc định)
| trường | ý nghĩa |
|---|---|
| `id` | tên, kế thừa `cast[id]`; dùng cho `hold`/`reach`/`at` |
| `kind` | `man` · `woman` (tóc dài) · `boy` · `girl` (bím, váy) · `old` (tóc thưa) · `oldwoman` (búi) · `plain` (trọc) · `baby` |
| `x, y, h` | chân ở (x,y); cao h × cạnh ngắn |
| `pose` | xem bảng dưới; hoặc dict tùy biến `{"base":"stand","a2":[96,0],"lean":5}` |
| `expr` | `happy` `smile` `joy` `calm` `neutral` `sad` `worried` `cry` `angry` `shout` `surprised` `scared` `hurt` |
| `face` | −1…1 hướng mặt; `flip` lật tư thế |
| `do` | danh sách: `breathe` `talk` `walk` (tự đổi hướng theo x) `shake` `bounce` `sob` `wave` `nod` `headshake` `sway` `cheer` `jab` `tremble` |
| `hold` | `"mom"` hoặc `["dad","son"]` — nắm tay người bên cạnh |
| `reach` | `{"arm":"R"|"L","to":"mom.shoulder"|[x,y],"off":[dx,dy]}` hoặc danh sách |
| `reach_w` 0..1 | độ "với tới" — đặt 0 rồi keys `{"t":2.8,"reach_w":1,"d":1}` → tay đưa ra dần, `0` → rút tay về (không giật) |
| `style` | `"soft"` = thân áo dài có khối, tai, mũi, tóc dày (xem SKILL.md) |
| `hold_prop` | đạo cụ trên tay: `{"name":"cane","arm":"L","s":0.3}` (briefcase, flower, phone, heart…) |
| `dark` 0..1 | hóa bóng đen (mặt vẫn thấy nét sáng) |
| `glow` 0..1 | hào quang vàng |
| `crack` 0..1 | vết nứt trên ngực |
| `tears` | nước mắt (tự có với `cry`) |
| `dress` `shirt` `sweater` | trang phục đơn giản |
| `rot` | xoay cả người quanh chân (nằm/ngã: 90) |
| `opacity` `weight` `shadow:false` `walk_in_place` `cadence` | |

Điểm neo cho `reach.to` / `at`: `head` `top` `chin` `mouth` `eyeL` `eyeR` `headL` `headR` `shoulder` `chest` `belly` `hip` `hipL` `hipR` `hand` `hand1` `hand2` `knee`.

### Tư thế
Đứng: `stand` `relaxed` `arms_open` `cheer` `wave` `point` `angry_point` `hips` `shrug` `think` `hand_chest` `hands_chest` `cover_face` `hands_head` `hug` `reach` `push` `defend` `carry` `slump` `bow` `lean_back` `cane` `walk` `run` `jump` `fall`
Mới: `clasp` (chắp tay trước bụng), `peek` (chắp tay, nghiêng người nhìn xuống), `bend` (cúi gập người với xuống đất — dùng với `reach`)
Ngồi/quỳ: `sit` (duỗi chân) `sit_knees` (ôm gối) `sit_cross` (xếp bằng) `sit_chair` `kneel` (1 gối) `kneel2` (2 gối) `crouch`

## Đạo cụ — `{"type": "prop", "name": …, "x", "y", "s", …}`
(x,y) thường là **đáy** vật (nhà, cây, cửa, người…) hoặc **tâm** (trái tim, mặt trời, bóng thoại, khung ảnh, đồng hồ).
| name | tham số |
|---|---|
| `heart` | `broken` 0..1, `crack`, `mend` 0..1 (băng dán), `beat`, `glow`, `dark` |
| `knife` | `rot` |
| `house` (nhà tranh ấm) | `light` 0..1 |
| `mansion` (biệt thự) | |
| `tree` (cây lớn) | `leaves` 0..1, `grow` 0..1, `glow`, `seed`, `depth` |
| `sapling` (mầm cây) | `grow` 0..1 |
| `sun` `cloud` (`rain`, `dark`) `mountain` `rock` `flower` | |
| `door` (s = cao cửa) | `open` 0..1, `light` 0..1 |
| `vase` | `broken` 1 = nằm vỡ + mảnh |
| `pot` (bình gốm hoa văn, tô khối) | `broken` 0..1 = miệng vỡ răng cưa |
| `shards` (mảnh gốm có độ dày + bụi vụn) | `n`, `spread`, `seed` |
| `bubble` | `content`: `scribble` `angry` `heart` `!` `?` `...` `text:Chữ`; `spiky`; `tail`:[dx,dy] |
| `lamp` `candle` | lửa lung linh + quầng sáng |
| `frame` (khung ảnh) | `oval`, `rot` |
| `coins` (`n`) `moneybag` `briefcase` `phone` (`glow`) `table` `chair` `book` `gift` `clock` (`speed`) | |
| `wall` (s = cao) | `width` |
| `bridge` `stairs` (`n`) `chain` (`n`) `tape` `cane` | |
| `arrow` | `to`:[x,y], `bend`, `draw` 0..1 |
| `lightning` `sparkle` (`n`) `mark` (`text`) | |
| `boat` (thuyền gỗ; (x,y) = tâm mép nước, s = chiều dài) | `bob` 0..1 (nhấp nhô, mặc định 0.6), `phase`, `flip` (mũi sang trái), `oar` 0..1 (mái chèo), `ripple` 0..1 (gợn nước), `dark`. Người trong thuyền: đặt fig **trước** thuyền trong `items`, `h` ≈ 0.36, chân ở `y` thuyền − 0.012 (ngồi `sit_cross`) / − 0.006 (đứng) → thân thuyền che chân |
| `waves` (sóng gợn trôi; (x,y) tâm vùng, s = bề ngang) | `depth` (bề dày vùng sóng), `n` hàng, `speed`, `seed` — dùng với nền `river` |
Đặt đạo cụ bám người: `"at": "dad.hand2", "off": [0, -0.05]`.

## Khác
- Chữ: `{"type":"text","text":"…","x","y","size":0.06,"color":[r,g,b],"font":"Montserrat-Black.ttf"}` (hạn chế dùng — phong cách mẫu gần như không có chữ).
- Đám đông: `{"type":"crowd","layout":"circle"|"rows"|"line","n":16,"h":0.27,"cx":0.5,"cy":0.74,"rx":0.44,"ry":0.1,"hold":true,"expr":"happy","exprs":[…],"kinds":[…],"pose":"stand","do":["breathe"],"dark":0,"glow":0}`; `rows` thêm `rows`,`y`,`w`,`depth_y`; keys đổi `pose`/`do` cho cả đám (vd `cheer`).

## Nền (`bg`)
`paper` (trơn) · `floor` (sàn gỗ phối cảnh) · `room` (sàn + cửa sổ nắng; `window`, `wx`) · `hall` (sảnh biệt thự lạnh: sàn caro, cửa sổ cao, đèn chùm) · `outdoor` (đồi, cỏ, cây xa; `trees`) · `path` (outdoor + đường làng; `road_x`, `road_end`) · `field` (chân trời phẳng) · `hut` (trong chòi tranh ấm) · `doorway` (tường tối, ô cửa sáng; `door_x`,`door_w`,`door_h`) · `night` (sao, trăng) · `studio` (góc trái-trên tối gạch chì, vệt sáng xiên, mép phải tối, sàn tối dần; `dark_w`, `dark_h`) · `river` (bờ xa có đồi + cây, mặt sông kẻ ngang dày dần; `trees`, `lines`, `bank`: `"left"|"right"` = bờ đất gần — thêm prop `waves` cho sóng động; ví dụ: dự án "Lý thuyết con thuyền trống" — dự án nội bộ, không kèm gói).
Chung: `horizon` (0..1), `sun: [x, y, s]`, `ground: true`.
Tông (`tone`): `warm` · `golden` · `neutral` · `cold` · `dark`.

## FX (`fx` của cảnh/panel) — `{"name": …, "front": false, "appear", "vanish"}`
`glow` (x,y,r,a,color,pulse) · `rays` (x,y,n,len,a,spin,width) · `rings` (x,y,r,a,n,speed,squash) · `dust` (n,a) · `rain` (n,a) · `darken` (a) · `vignette` (a) · `flash` (at,a) · `warm` (a).

## Chia màn hình (`panels`)
```json
"panels": [
 {"rect": [0, 0, 0.5, 1], "bg": "paper", "tone": "golden", "fx": [...], "items": [...]},
 {"rect": [0.5, 0, 0.5, 1], "bg": {"type": "hall"}, "tone": "cold", "enter": "slide_right", "enter_t": 0, "items": [...]}
]
```
Trong panel, x/y tính theo panel; U = cạnh ngắn panel (panel nửa khung dọc → người nhỏ lại, tăng `h`). `enter`: `slide_left|slide_right|slide_up`; `border: true` viền chì.

### Đạo cụ thêm (2026-10-03)
| `playbtn` | kỷ niệm chương nút Play YouTube (tâm; s = bề ngang) — `gold` (nút vàng, mặc định bạc), `glow`, `rot` |
| `screen` | khung video (tâm; s = cạnh dài) — `vertical` (dọc 9:16, mặc định ngang 16:9), `play` (nút ▶ đỏ, mặc định true), `dim` 0..1, `glow` |
