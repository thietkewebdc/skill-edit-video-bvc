# Checklist QA trước khi giao

`check` phải sạch cảnh báo (hoặc có lý do rõ). Rồi `snap` tại: 0s, giữa tiêu đề, mỗi hiệu ứng ở (start + 0.8s), 2s cuối. **Mở ảnh xem thật.**

## Tiêu đề
- [ ] Ảnh 0s có tiêu đề đầy đủ (đây là thumbnail).
- [ ] Đúng mẫu: dòng trắng + dòng màu bản to, 1 lớp bóng đen đặc chéo sắc nét, không tràn mép.
- [ ] Đúng 1 dòng trắng + 1 dòng màu. Dòng trắng đè nền sáng (trời, áo trắng) → đảo: màu trên – trắng dưới.
- [ ] Sub (từ đang nói), chữ nhấn, minh họa cùng màu với tiêu đề (xanh hoặc vàng).
- [ ] Không có hiệu ứng ánh sáng nào trong lúc tiêu đề hiện.
- [ ] Snap cả khung **đang vào / sắp ra** của tiêu đề và chữ nhấn: không được thấy chữ chồng đôi hay bóng lộ qua chữ.
- [ ] 2–6 từ, hợp ý đoạn mở đầu, dài 5–10s, không có sub trong lúc hiện.

## Chữ nhấn
- [ ] Đúng cặp màu của video (không lẫn vàng/xanh).
- [ ] Không đè mặt (xem cả góc rộng và góc cận).
- [ ] Dấu tiếng Việt của dòng dưới không dính vào dòng trên.

## Nhịp
- [ ] 8–10s một hiệu ứng, xen kẽ chữ nhấn ↔ minh họa, không trống quá 10s.
- [ ] fx đa dạng, không 3 lần liên tiếp cùng kiểu.

## Sub
- [ ] Chính tả đúng (đã rà `words.json`), từ vàng chạy khớp giọng.
- [ ] Tên người, địa danh, thương hiệu viết hoa chữ cái đầu (thêm vào `proper_nouns` nếu thiếu).
- [ ] Sub cỡ 60 — dễ đọc trên điện thoại, không tràn mép, không chạm nhãn minh họa; viền đen thật mỏng + bóng nhẹ khép sát, từ đang nói theo màu tiêu đề — vàng #F4C80F hoặc xanh #00FFFF (không phải mẫu chữ khối).
- [ ] Thư mục xuất KHÔNG có file `.ass` cạnh video.

## Âm thanh
- [ ] Whoosh/impact rõ nhưng không át giọng. To quá thì `"sfx_volume": 0.7`.

## Video nguồn đã có chữ cháy sẵn
Skill không xóa được chữ cũ → xin người dùng file gốc chưa có chữ.
