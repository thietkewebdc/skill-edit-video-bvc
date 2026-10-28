# Phân tích video mẫu "Tôi không lười, tôi chỉ tiêu xài quá sớm cuộc đời mình"

Nguồn: FDown.vn_Tai_video_Facebook_1080p_253f.mp4 — 1080×1920, 30fps, 320s. Phong cách áp dụng cho kênh Hồ Mạnh Thắng.
**Đã bỏ khỏi skill:** logo kênh gốc góc trái trên + màn chớp đỏ thẫm có lá 🌿 (brand sting). `brand` mặc định tắt.

## Bản chất
- **100% đồ họa, không có người**. Voice over đọc liên tục (~4.3 từ/s), không nhạc nổi, SFX nhẹ khi chuyển màn. Âm ~−14 LUFS.
- **Đổi màn rất dày: ~2–3s/màn** (≈130 màn / 320s). Mỗi màn = 1 ý của câu đang đọc.
- Chữ trên màn là **bản rút gọn** của lời (không chép nguyên câu), hiện **từng từ đúng lúc nói**.
- Video chia **phần**: Mở đầu → màn chương "01 · Mọi thứ đến quá sớm" … "05 · Đủ thời gian để chín" → Kết. Nhãn phần nằm góc phải trên suốt video.
- Thanh tiến độ vàng mảnh chạy trên mép trên cùng.

## Bảng màu nền (mỗi màn 1 màu đặc, đổi liên tục)
| Nền | Màu | Chữ | Chữ nhấn | Gạch chân |
|---|---|---|---|---|
| dark | #1B1B1B | trắng | vàng #F2C14E | đỏ |
| green | #1F4630 | trắng | vàng | đỏ |
| red | #DD5840 | kem | vàng | đỏ thẫm |
| yellow | #ECC24E | mực #1E2A22 | đỏ #C8321F | vàng nhạt |
| cream | #F2EDE1 | mực | đỏ #D9503F | vàng |
| mint | #D5EBDD | xanh rêu | xanh lá | vàng |
Trang trí nền: 2–3 **hình tròn lớn mờ** trôi chậm, đôi khi 1 vòng viền mảnh; màn chương có **sọc chéo**; màn "tốc độ" có **vệt ngang**; cảnh biển hoàng hôn cho ý thư thái.

## Chữ
- Sans đậm bo tròn (skill dùng Inter ExtraBold), căn giữa, 1–3 dòng, cỡ 64–92px (khung 1080), chữ lớn một mình tới 130px.
- Mỗi từ hiện: mờ → rõ, trồi lên nhẹ, bớt nhòe (~0.3s). Cụm quan trọng **đổi màu nhấn + gạch chân dày** kéo từ trái sang sau khi từ hiện.
- Câu trích dẫn: dấu “ lớn màu đỏ/vàng, chữ căn trái, dòng ký tên "— …".

## Thư viện hình minh họa trong mẫu → thành phần skill
| Trong mẫu | Thành phần |
|---|---|
| Đồng hồ vòng 05:53 → 07:12, tai nghe 19:51 → 00:02 | `timer` |
| Laptop – bàn tay – điện thoại trên kệ | `row` + `emoji` (`shelf`, `move`) |
| 😣 + "Bứt rứt / Khó chịu / Muốn thoát ra" | nhiều `text` + `emoji` idle `shake` |
| Điện thoại lướt feed "Dành cho bạn" + ngón tay vuốt | `phone` |
| Thẻ "Thời gian sử dụng 43 phút" + thanh TikTok/Facebook | `usage` |
| Danh sách ✓ "Tôi từng…", ✗ "Bước ngoặt không đến từ", – "Ở Nha Trang" | `list` (icon check/x/dash/hour) |
| Não 🧠 + pin 100% → 14% | `emoji` + `battery` |
| Con lười trong đĩa vàng | `emoji` `disc` |
| Màn chương "01 / PHẦN 01 / Mọi thứ đến quá sớm" | `chapter` |
| Hoa tulip → héo, rễ trong đất; cây lớn + xẻng | `plant` (`swap`, `tool`) |
| Bao lì xì → khóa, "Giữ đến khi lớn" | `emoji` `swap` + `pill` |
| Đồng hồ cát trong đĩa | `emoji` `disc` |
| Ảnh polaroid "Ngày xưa" (máy game, băng video) | `polaroid` |
| Nút CHẠM + icon bung ra quanh | `radial` |
| "Chiến thắng / Kích thích / Trốn tránh" + nhãn ⚡ RẤT NHANH | `text` + `pill` |
| Mới ngoài 20 VS Nói như ông cụ 80 (chia đôi trên/dưới) | `vs` |
| Màn hình 240p mờ + dấu SPOILER / 4K | `screen` (`blur`, `stamps`, `badge`) |
| Lưới ô "SỰ CHÚ Ý" vỡ vụn | `grid` (`break`) + `confetti` |
| Refresh… lượt xem/bình luận | `usage` biến thể / `notify` |
| Thông báo "3 tin nhắn mới…" + số mờ 23:47 phía sau | `notify` + `ghost` |
| Não đã quen: Nhanh, ngắn VS Chậm, sâu | `vs` |
| Vòng lặp Áp lực → Lướt → Nhẹ đầu → Rỗng hơn | `cycle` |
| Cà phê trên biển hoàng hôn, "≈ 1 tiếng" | nền `sunset` + `pill` + `list` |
| Cửa sổ chat "Danh bạ" — "Dạo này sao rồi?" / Đã xem | `chat` |
| Vài tuần / Vài tháng / Quan trọng hơn (dòng thời gian) | `timeline` |
| Biểu đồ "Từng chút → Tự tới" tăng dần | `chart` |
| Bản đồ Hà Nội → Nha Trang, xe chạy, nhãn Nhịp nhanh/Chậm lại | `map` |
| Làm chậm lại ≠ ~~thụt lùi~~ | `neq` |
| Sổ tay tự viết + bút chì | `notebook` |
| Dấu "?" to | `emoji` ❓ hoặc `text` cỡ xxl |

## Chuyển màn
Panel nghiêng trượt vào (tilt), rèm dọc (blinds), vòng tròn mở (circle), tách đôi (split), trượt lên (slide), quét ngang (wipe). Màn cùng màu nền → chỉ mờ chồng (fade). Skill tự xoay vòng các kiểu khi màu nền đổi.

## Nhịp
- Màn mở: đúng từ đầu tiên của câu (lùi 0.12s).
- Mục minh họa bật ngay khi vào màn, hoặc đúng từ khóa (`say`).
- Liệt kê: mỗi dòng bật đúng lúc nói dòng đó + tiếng "tick".
