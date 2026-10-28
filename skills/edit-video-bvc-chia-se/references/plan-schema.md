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

Cú pháp chữ: `{...}` = dòng/cụm màu nhấn · `|` = xuống dòng · không dùng `\`.
Chữ nhấn/tiêu đề luôn IN HOA (engine tự đổi).
`words.json` do `transcribe` tạo: `{"words": [{"w": "Mình", "s": 0.0, "e": 0.22}, ...]}`.
