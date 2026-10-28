# Checklist trước khi giao

1. `check` sạch cảnh báo: mọi `say` tìm thấy, không màn < 0.7s hoặc > 9s, không mục tràn khung, chữ ≤ 3 dòng.
2. `snap --sheet` (vị trí 0.85 mỗi màn) — mở ảnh xem thật:
   - Chữ đủ, không lệch, không đè hình; cụm nhấn đúng từ quan trọng (≤ 1 cụm/dòng).
   - Màu nền không lặp 2 màn liền nhau quá 3 lần (trừ khi cố ý giữ nền để chữ đổi mượt).
   - Hình minh họa đúng ý câu, không chỉ chép chữ; mỗi 3–4 màn có ít nhất 1 màn hình minh họa lớn.
3. Soi vài màn động ở nhiều thời điểm (`snap --at`): danh sách bật đúng lời, đồng hồ/số đếm chạy đúng hướng, emoji `swap` đúng lúc.
4. Không có logo, chữ ký hay chữ "bản test/demo" (trừ khi người dùng yêu cầu `brand`).
5. Đuôi 0.5s sau chữ cuối; âm −14 LUFS (render tự chuẩn).
6. Render xong: tách tờ khung `ffmpeg -ss X -t 4 -i out.mp4 -vf fps=6,scale=216:384,tile=12x2 m.png` ở 2–3 đoạn để chắc chuyển động mượt, không khung trắng/đen.
