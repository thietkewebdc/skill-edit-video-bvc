# Checklist trước khi giao

## Chuẩn bị
- [ ] `words.json` đã sửa chính tả (video ngắn: nhận giọng lại bằng `large-v3` để đối chiếu). Tên riêng viết hoa đúng. Các mảnh bị tách đã gộp (`1` + `%`). Từ nghe không rõ → hỏi người dùng.
- [ ] Có `mask.mp4` cho MỌI video có người (dùng cho chữ sau người VÀ để né mặt). Trích vài khung mask để xem: người trắng, nền đen, tóc/tay rõ.
      Cảnh không có người → khoảnh khắc đó đặt `"behind": false`.
- [ ] Thiếu `scripts/text3d/rvm_mobilenetv3_fp32.onnx` → **xin phép người dùng** rồi tải (~14 MB) từ
      `https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx`.
- [ ] Đã lập BẢNG câu → khuôn theo MẪU CHUẨN (SKILL.md M1–M6): mỗi câu tối đa 1 điểm nhấn · ① chữ khóa trên đầu + sub ~60–70% · ② cụm ngực ~15% · ③ neon/strike/badge ~15% · câu thường chỉ sub.

## `check`
- [ ] Không còn CẢNH BÁO: không "RỐI MẮT" (chữ sau đầu + cụm giữa cùng lúc), không "KHÔNG ĐẠT" (che chữ / che mặt), không chữ chồng chữ cùng tầng.
- [ ] Mỗi chữ nhấn giữ suốt câu (3–5s), mật độ ~2.5s/điểm nhấn. Không có quãng sub trơn > 6.5s.

## Mở ảnh `snap` xem thật (mỗi câu, lúc từ khóa vừa hiện + 0.3s)
- [ ] So với MẪU CHUẨN (`Short Hook Demo_editorial_vang.mp4`): mỗi khung chỉ 1 điểm nhìn chính — 1 chữ khóa to GIỮA KHUNG trên đầu + 1 dòng sub nhỏ 2–4 từ ở ngực, HOẶC 1 cụm ngực (không sub), HOẶC 1 điểm đặc biệt (không sub). Chữ khóa không bị thu nhỏ/dạt góc; không có chữ trắng mảnh ở tầng trên trông như sub.
- [ ] Không chữ nào che mặt (cảnh cận: sub nằm dưới cằm). Chữ tầng trên: đầu/tóc che ≤ 1/2 chữ cái, ≤ 2 chữ cái, đọc được cả từ.
- [ ] Sub KHÔNG lặp chữ đang hiện ở chữ nhấn / badge (VD "không viết." chỉ 1 lần). Sub nhỏ 2–4 từ, không in đậm, cố định ở ngực, hiện thẳng, không mờ vào/ra.
- [ ] Bản NGANG: sub là 1 dòng 8–12 từ ở đáy, đủ câu (không khuyết từ), không đuôi mồ côi 1–2 từ, đọc rõ trên nền sáng.
      Chữ sau đầu khuôn ① có `"hide_subs": false` (sub chạy bên dưới như bản dọc đã duyệt).
- [ ] Chữ không tràn mép (chừa ≥ 3% mỗi bên). Hai dòng trong một cụm không dính vào nhau khó đọc.
- [ ] Nền sáng (trời, đồi nắng, tường/xe trắng): chữ đọc rõ — không âm bản/bạc/teal/slate trên nền sáng; chữ khóa vàng sáng + halo tối (mặc định), dòng đệm tối thì ink + halo.
- [ ] Phong cách kênh: chữ khóa VÀNG SÁNG phẳng + quầng tối, không khối 3D, không tím/xanh (trừ khi người dùng xin riêng cho video đó); có 1–2 flash ở bước ngoặt.
- [ ] Gradient nhìn rõ 2 tông, không bị tối đen ở một đầu.
- [ ] Badge, chữ rải, logo không che mặt và tay đang làm động tác chính.
- [ ] Dấu tiếng Việt đầy đủ, không bị cắt ở đỉnh dòng.

## Preview + bản cuối
- [ ] Nghe: SFX nằm dưới giọng, không át lời; badge có tiếng "bloop" nghe rõ. Không có nhạc nền.
- [ ] Từng từ khóa hiện khớp lời nói (lệch ≤ 2–3 khung).
- [ ] Flash trắng rơi đúng mối cắt cảnh.
- [ ] Đo âm bản cuối: ~−14 LUFS, đỉnh ≤ −1.5 dBTP (`ffmpeg -i out.mp4 -af loudnorm=print_format=summary -f null -`).
