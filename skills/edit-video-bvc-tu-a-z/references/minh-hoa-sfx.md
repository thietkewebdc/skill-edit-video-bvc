# Minh họa + SFX

Minh họa vẽ nét **theo màu nhấn của video** (vàng hoặc xanh), có quầng sáng, bóng và hạt sáng. Nhãn dùng Montserrat Black IN HOA màu trắng.
Minh họa và chữ nhấn **xen kẽ**: cứ 8–10s một hiệu ứng, không chồng nhau. Minh họa dài 2.5–4s. Sub vẫn hiện (minh họa nằm phía trên sub).

| `type` | Hình | Hợp với câu nói về | Trường thêm | SFX tự động |
|---|---|---|---|---|
| `counter` | con số đếm nhảy 0 → giá trị, tia sáng quét, hạt | %, số tiền, số năm, số người | `value`, `prefix`, `suffix`, `decimals`, `label` | tick liên tục + impact nhẹ |
| `clock` | đồng hồ nét, kim quay | thời gian, deadline | `label` | tick |
| `scale` | cán cân nghiêng rồi cân bằng | lựa chọn, cân bằng | `left_label`, `right_label` | chime |
| `split` | vạch dọc chia đôi + 2 chữ khối trượt ra | A vs B | `left_label`, `right_label` | swish |
| `quote` | dấu “ lớn phóng vào + câu trích | lời dạy, câu đáng nhớ | `label` (`|` xuống dòng, `{..}` tô màu) | shimmer |
| `checklist` | 2–3 dòng tick lần lượt | bước, quy tắc | `items` | pop mỗi dòng |
| `growth` | biểu đồ tăng + nhãn phóng vào | kết quả, tăng trưởng | `label` | riser |
| `frame` | 4 góc khung co vào quanh người nói | chốt, kết video | — | shimmer |
| `cube` | **khối lập phương 3D** nét màu nhấn, xoay trong không gian (phối cảnh thật) | nền tảng, hệ thống, sản phẩm, sự nghiệp, xây dựng | `label` (hiện phía trên khối), `size` | shimmer |
| `icon:home` `icon:heart` `icon:briefcase` `icon:star` `icon:target` `icon:bulb` | icon nét + hạt sáng | gia đình / yêu thương / công việc / thành công / mục tiêu / ý tưởng | `label` | chime + sparkle |

Icon (`icon:*`) mặc định: **nét mảnh bo tròn, trong huy hiệu vòng đôi + 4 điểm kim cương**, tô **gradient** trên màu chính, **xoay 3D** khi xuất hiện. Tắt huy hiệu `"emblem": false`, tắt xoay `"spin3d": false`.
Mọi hình minh họa (đồng hồ, cán cân, khối 3D, biểu đồ…) đều tô gradient trên màu chính.

Tùy chọn chung: `x`, `y` (0–1; mặc định 0.5 / 0.535; giữ `y` trong 0.44–0.62), `size`, `sfx` (`"none"` hoặc tên khác), `hide_subs`.
`checklist` nhận `x` (vị trí cột dấu tick, mặc định 0.25) và `y` (tâm danh sách, mặc định 0.50 — hạ/nâng khi đè mặt); `quote` nhận `y` (vị trí dấu “, mặc định 0.49). `split` và `frame` cố định vị trí.

## Thư viện SFX (tạo bằng code, có vang)
| Tên | Âm thanh |
|---|---|
| `whoosh` | gió lướt dày 0.8s, quét trái→phải, có vang |
| `whoosh_soft` | whoosh nhỏ |
| `swish` | lướt ngắn 0.4s |
| `impact` | cú đập trầm (sub-boom + tiếng nổ nhỏ + vang dài) |
| `impact_soft` | impact nhẹ |
| `riser` | âm dâng 0.8s dẫn vào cao trào |
| `sparkle` | lấp lánh nhiều nốt cao |
| `pop` | pop ngắn |
| `tick` | tick đồng hồ |
| `chime` | chuông pha lê |
| `shimmer` | chuỗi nốt cao ngân |

Âm lượng: engine đã giảm tổng **-7 dB**; chỉnh thêm từng video bằng `"sfx_volume"` (mặc định 1.0).
Thay bằng âm thanh riêng: thả `sfx/<tên>.wav` (WAV 16-bit) vào thư mục skill.
