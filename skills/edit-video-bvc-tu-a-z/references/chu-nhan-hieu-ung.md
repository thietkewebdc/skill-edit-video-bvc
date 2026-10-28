# Chữ nhấn + hiệu ứng động

Chữ nhấn dùng đúng **mẫu chữ khối** (xem mau-chu-khoi.md). Nhịp chung với minh họa: **một hiệu ứng mỗi 8–10s, xen kẽ**.

## Chọn câu
- Bám **đúng lúc người nói nói ra cụm đó** (lấy `s` của từ đầu trong `words.json`, trừ 0.1–0.2s). Dài 1.4–2.6s.
- Chọn: kết luận, con số, cảm xúc mạnh, 2 vế đối lập, câu hỏi tu từ. Không chọn câu dẫn.
- 2–6 từ, dòng màu 1–3 từ.

## Kiểu vào (`fx`)
| fx | Diễn biến | SFX tự động | Dùng khi |
|---|---|---|---|
| `slam` (mặc định) | dòng trắng rơi xuống; dòng màu đập vào từ 165% → 96% → 100% + nhòe→nét; chớp sáng nhẹ, **sóng lan**, **hạt sáng bắn ra**, **zoom punch 7%** | whoosh + impact | câu đinh, kết luận |
| `zoom` | dòng màu phóng từ 30% → 108% → 100%; sóng lan, hạt, zoom punch | riser (trước 0.7s) + impact | con số, cao trào |
| `stagger` | từng từ trượt lên theo nhịp 0.11s | swish + pop mỗi từ | liệt kê, câu có nhịp |
| `wipe` | từng dòng lộ trái→phải | whoosh + sparkle | tên khái niệm, tiêu đề phần |
| `type` | gõ từng ký tự | tick | câu hỏi, suy nghĩ |
| `rise` | nở nhẹ 88% → 100% | whoosh nhỏ | câu nhẹ, nội tâm |
| `flip3d` | **3D** — lật thẻ quanh trục ngang, phối cảnh thật; sóng lan, hạt, zoom punch | swish + impact nhẹ | câu đinh, kết luận, bước ngoặt |
| `swing3d` | **3D** — xoay vào như cánh cửa quanh trục dọc | whoosh + pop | so sánh, chuyển ý, hành động |
| `tilt3d` | **3D** — nghiêng sâu rồi dựng lại, giữ chút chiều sâu khi đứng | whoosh + impact nhẹ | câu hỏi lớn, suy ngẫm, cao trào |

Tùy chọn mỗi chữ nhấn: `"punch": false` (tắt zoom) hoặc số (VD `1.1`), `"flash": false`, `"particles": false`, `"sfx": "none"`.

## Biến thể (`variant`)
| variant | Cỡ tối đa | Nền | fx mặc định |
|---|---|---|---|
| `impact` | 330 | tối 22% | slam |
| `whisper` | 190 | không tối | rise (không zoom punch, whoosh nhỏ) |
| `chapter` | 250 | tối 45% | wipe (dùng `"kicker": "CHƯƠNG 01"` làm dòng trắng) |

## Phối để không nhàm
- ~40% `slam`, **~30% hiệu ứng 3D** (`flip3d` / `swing3d` / `tilt3d`), còn lại `zoom` / `stagger` / `wipe` / `type`.
- Không đặt 2 hiệu ứng 3D liền nhau; 3D hợp nhất với câu 2–4 từ.
- Không dùng cùng fx 3 lần liên tiếp.
- `zoom` dành cho con số và 1–2 cao trào mỗi video.
- Zoom punch không quá 1 lần / 8s.
