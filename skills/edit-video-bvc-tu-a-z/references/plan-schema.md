# Cấu trúc plan.json

```jsonc
{
  "words_file": "words.json",        // tương đối so với plan.json
  "accent": "yellow",                // "yellow" (trắng–vàng) | "cyan" (trắng–xanh)
  "sfx_volume": 1.0,                 // tùy chọn
  "punch": true,                     // false = tắt mọi zoom punch
  "proper_nouns": ["Suối Mơ", "Anh Tuấn", "Đà Lạt"],   // tên riêng viết hoa chữ cái đầu trong sub (ngoài danh sách có sẵn)
  "sub_zones": [{"start": 13.4, "end": 73.2, "y": 0.14}], // tùy chọn: dời sub lên/xuống trong khoảng đó (VD đoạn quay màn hình đã có sub sẵn ở 66%)

  "title": {
    "start": 0,                      // luôn 0
    "end": 7.5,                      // 5–10s
    "lines": ["GIA ĐÌNH", "{HAY SỰ NGHIỆP?}"],   // hoặc "GIA ĐÌNH|{HAY SỰ NGHIỆP?}"
                                     // luôn 1 dòng trắng + 1 dòng màu; đảo "{3 PHONG THỦY}|QUÝ GIÁ" khi dòng trên đè nền sáng
    "letterbox": false,              // true: thêm 2 dải đen điện ảnh (storytelling)
    "dim": 0                         // 0–0.4: làm tối nền sau tiêu đề
  },

  "emphasis": [
    {"start": 15.4, "end": 17.4, "text": "CON KHÓC {KHÔNG NÍN}"},
    {"start": 47.2, "end": 49.2, "text": "BA ĐANG {KHÔNG Ở ĐÂY}", "fx": "zoom"},
    {"start": 63.6, "end": 65.4, "text": "MÌNH ĐANG {XÂY GÌ?}", "variant": "whisper"},
    {"start": 11.4, "end": 13.4, "text": "{MỘT ĐÊM NỌ}", "kicker": "Chương 01", "variant": "chapter"}
  ],

  "illustrations": [
    {"start": 24.0, "end": 27.4, "type": "clock", "label": "Tiến độ"},
    {"start": 76.0, "end": 79.4, "type": "counter", "value": 90, "suffix": "%", "label": "Thời gian bên con"},
    {"start": 57.0, "end": 60.4, "type": "scale", "left_label": "Gia đình", "right_label": "Sự nghiệp"}
  ]
}
```

**Khung ngang 16:9** (engine tự nhận khi video rộng hơn cao): canvas 1920×1080, chữ khối 56% cỡ, khối chữ ở 68% chiều cao, sub cỡ 50 ở 87% (dọc: cỡ 60 ở 66%), minh họa tự dời xuống +0.12 (cộng cả vào `y` ghi trong plan) → 1 `plan.json` dùng chung cho bản dọc và bản ngang.

**Trường riêng của `sm_sync.py`** (video dài, số liệu hiện theo lời nói):
```jsonc
{"start": 40.1, "end": 44.0, "text": "336 {TRIỆU}", "fx": "sync", "at": [40.1, 40.9]},   // số mốc = số từ ("·", "=", "–" cũng là 1 từ)
{"start": 0, "end": 7.5, "text": "CĂN HỘ SINH TÀI?|{3 ĐIỀU}", "fx": "sync", "static": true, "tw": 0.38, "at": [0,0,0,0,0,0]}  // tiêu đề 2 dòng rộng bằng nhau
```
`"fs": 240` = cỡ chữ nhấn khung ngang 4K. Biến thể `"chapter"` KHÔNG dùng cho khung ngang (chữ nhỏ, lệch bề ngang).

Cú pháp chữ: `{...}` = dòng/cụm màu nhấn · `|` = xuống dòng · không dùng `\`.
Chữ nhấn/tiêu đề luôn IN HOA (engine tự đổi).
`words.json` do `transcribe` tạo: `{"words": [{"w": "Mình", "s": 0.0, "e": 0.22}, ...]}`.
