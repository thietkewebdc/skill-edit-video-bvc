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

## Cắt ghép + zoom (skill từ A–Z)
- [ ] `cut_edit.py plan`: không đoạn nào < 2s, zoom xen kẽ 100% / 150% bắt đầu từ 100%.
- [ ] Chữ đầu/cuối mỗi đoạn trong `words.json` mới không có từ lẻ sót lại (VD "nhưng").
- [ ] Đuôi video: `plan` in `⏹ đuôi 0.50s` — ngắn hơn chỉ khi có lý do (lẹm tiếng / đổi cảnh). Nghe 2s cuối: không dừng cụt, không dính tiếng câu sau.
- [ ] Footage B-roll: `check` không còn `!! rung`; xem thử 2s đầu mỗi footage — không giật, không rung tay.
- [ ] Khung giữa mỗi đoạn (cả 16:9 và 9:16): đoạn 150% không mất đầu, mặt giữa khung, mắt ~ đường 1/3.
- [ ] Minh họa trong đoạn 150% (mặt to, cằm thấp): đặt `"y": 0.60` + `"hide_subs": true` để không chạm cằm và không đè sub. Một `plan.json` dùng cho cả 2 khung — khung ngang tự cộng thêm độ dời.
- [ ] Hiệu ứng `tilt3d` với dòng màu dài dễ tràn mép khung dọc → đổi `swing3d`/`flip3d`.

## Mối cắt — nghe bằng âm thanh thật (`cut_qa.py`, bắt buộc trước render 4K)
- [ ] `lost`: "sạch" — không quãng tiếng nào trong vùng giữ bị bỏ (cụm ngắn giữa 2 chỗ ngừng như "ba trăm").
- [ ] `listen` → `joints.txt`: MỌI mối nối (kể cả ĐẦU và CUỐI video) vào đúng chữ, không chữ lẻ thừa ("là", "thì", "mình", "cao"), không mất chữ, câu trọn nghĩa.
- [ ] Dòng "SỐ LIỆU nghe được" khớp từng con số trong lời gốc (336 triệu, 2027, 43.000…). Số lệch = mất tiếng → sửa, KHÔNG bỏ qua.
- [ ] `edges`: mép nào nằm giữa dòng tiếng đều đã nghe xác nhận (`listen`/`try`).
- [ ] Không có lệnh cắt nào giữa 2 chữ dính liền (vấp giữ nguyên, ghi `_notes`, báo người dùng).
- [ ] Sub dùng `words_final.json` từ `cut_qa.py subs` (không mất chữ quanh mối cắt).
- [ ] Chữ nhấn số liệu dạng "sync": mốc neo chữ số không bị bắt nhầm sang số khác gần đó (VD "MỘT VIDEO" neo nhầm số "1" của "1 đô" → khối trước bị cắt ngang). Snap từng khối để xác nhận.

## Nhịp
- [ ] 8–10s một hiệu ứng, xen kẽ chữ nhấn ↔ minh họa, không trống quá 10s.
- [ ] fx đa dạng, không 3 lần liên tiếp cùng kiểu.

## Sub
- [ ] Chính tả đúng (đã rà `words.json`), từ vàng chạy khớp giọng.
- [ ] Tên người, địa danh, thương hiệu viết hoa chữ cái đầu (thêm vào `proper_nouns` nếu thiếu).
- [ ] Sub cỡ 60 (dọc) / 50 (ngang) — dễ đọc trên điện thoại, không tràn mép, không chạm nhãn minh họa; viền đen thật mỏng + bóng nhẹ khép sát, từ đang nói theo màu tiêu đề — vàng #F4C80F hoặc xanh #00FFFF (không phải mẫu chữ khối).
- [ ] Thư mục xuất KHÔNG có file `.ass` cạnh video.

## Âm thanh
- [ ] Whoosh/impact rõ nhưng không át giọng. To quá thì `"sfx_volume": 0.7`.

## Video nguồn đã có chữ cháy sẵn
Skill không xóa được chữ cũ → xin người dùng file gốc chưa có chữ.
