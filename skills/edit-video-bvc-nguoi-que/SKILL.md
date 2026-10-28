---
name: edit-video-bvc-nguoi-que
description: Tạo VIDEO HOẠT HÌNH NGƯỜI QUE NÉT CHÌ trên giấy sepia từ một file VOICE OVER (mẫu "Gia đình hạnh phúc nhất…"). Người dùng chỉ đưa voice (mp3/wav/m4a/mp4) — skill tự nghe (whisper), chia 1 câu = 1 cảnh, rồi Claude tự nghĩ hình ẩn dụ cho từng câu và VẼ BẰNG CODE (skia, miễn phí, không cần API): người que đầu tròn tóc lởm chởm, biểu cảm, tư thế, nắm tay/chỉ tay/ôm (IK), đám đông, đạo cụ (trái tim vỡ + băng dán, dao, nhà tranh ấm, biệt thự lạnh, cây lớn, mầm cây mọc, cửa sáng, bình vỡ, khung ảnh kỷ niệm, bóng thoại…), nền (chòi tranh, phòng, sảnh lạnh, đường làng, khung cửa tối), tông warm/golden/cold/dark, ánh sáng, vòng sáng, chia đôi màn hình, zoom chậm, chuyển cảnh mờ; tiêu đề hook 2 dòng ở đầu; âm −14 LUFS; dọc 9:16 hoặc ngang 16:9. Có KIỂU SOFT mượt 30 hình/s (người áo dài tô chì có khối, tai, mũi, nền vệt sáng xiên) khi người dùng muốn "chuyển động mượt như video AI". Dùng khi người dùng nói "làm video người que", "hoạt hình người que", "stick figure", "video hoạt hình từ voice", "vẽ minh họa cho voice over", "video kiểu Gia đình hạnh phúc nhất", hoặc gọi /edit-video-bvc-nguoi-que.
---

# Skill: Hoạt hình NGƯỜI QUE NÉT CHÌ từ voice over

Người dùng đưa **voice over** → skill ra **video hoàn chỉnh** (hình + voice). Hình do code vẽ (skia), không dùng AI tạo ảnh, không chữ ký, không nhạc (trừ khi người dùng yêu cầu).

Engine: `scripts/stick.py` (CLI) + `scripts/stickdraw.py` (thư viện vẽ). Gọi bằng **đường dẫn tuyệt đối**:
`python "$HOME/.claude/skills/edit-video-bvc-nguoi-que/scripts/stick.py" …`
Cần: `pip install skia-python faster-whisper opencv-python numpy`, ffmpeg. Whisper chạy GPU (tự nạp cuBLAS như các skill khác, lỗi thì tự về CPU; `--cpu` để ép).

Tài liệu đầy đủ định dạng cảnh (tư thế, biểu cảm, đạo cụ, nền, fx, hoạt ảnh): **[references/scene-format.md](references/scene-format.md)** — đọc trước khi viết cảnh.
Ví dụ hoàn chỉnh 23 cảnh (voice "Gia đình hạnh phúc nhất"): [examples/gia-dinh.scenes.json](examples/gia-dinh.scenes.json).

## Phong cách (phân tích từ video mẫu)
- Người que **đầu tròn to** (≈¼ chiều cao), tóc vài nét lởm chởm, mắt chấm, tay chân 1 nét, bàn tay/chân bầu dục; bóng đổ gạch chì dưới chân.
- Giấy kem/sepia có vân, góc tối dần; chỉ tông nâu–kem–than chì; **vàng ấm chỉ dùng cho ánh sáng** (đèn, cửa sổ, hào quang, cảnh hạnh phúc).
- **1 câu voice = 1 cảnh** (3–10s). Cảnh vẽ đúng **ẩn dụ** của câu, không minh họa chữ. Tâm trạng câu quyết định tông: tích cực → `warm/golden` + glow; tiêu cực → `neutral/cold/dark`, người `slump`, `dark` (bóng đen).
- Mỗi cảnh có chuyển động nhẹ: zoom chậm 1.0→1.06–1.12, nhân vật thở/nói/run, và **1 thay đổi chính khớp với từ khóa** trong câu (biểu cảm đổi, trái tim vỡ/lành, người hóa đen, tường biến mất, mầm cây lớn…).
- Tiêu đề hook 2 dòng, **dài 5s** (chủ kênh chốt 2026-10-01), kiểu `"style": "pro"` mặc định: dải nâu trong mờ mép nhòe · dòng 1 Montserrat Black màu kem, to · vạch mảnh vàng + hình thoi · dòng 2 Montserrat Bold vàng ấm, giãn chữ. Khoảng dòng đo theo đỉnh/đáy thật của chữ (cả dấu chồng Ề, Ổ) → **không bao giờ đè nhau**. Hiện lần lượt: nền → dòng 1 trồi lên → vạch kéo ra → dòng 2; ra mờ 0.4s. Đặt `y` vào vùng trống (trời), tránh mặt trời/mặt người. Kiểu cũ (chữ trắng viền nâu): `"style": "classic"`. Sau đó không có sub.
- Đuôi video: 0.5s sau chữ cuối (plan tự đặt).

## Hai kiểu vẽ
| | **Kiểu nét (mặc định)** | **Kiểu SOFT — mượt, có khối** |
|---|---|---|
| Mẫu | "Gia đình hạnh phúc nhất" (người que 1 nét) | clip AI "bình vỡ" (người áo dài tô chì) |
| Nhân vật | tay chân + thân 1 nét, đầu tròn | thân **áo dài tô gạch chì + đổ bóng**, đầu tô khối, **tai, mũi tròn**, tóc chùm dày, vai tách 2 bên, bàn tay/chân to |
| Chuyển động | 15 hình/s + rung nét 6 lần/s (kiểu vẽ tay) | **30 hình/s, không rung nét**, chuyển động mềm |
| Bật | — | mỗi nhân vật `"style": "soft"` (để trong `cast`); plan: `"anim_fps": 30, "boil_fps": 0, "rough": 0.45` |
| Nền hợp | mọi nền | `studio` (góc tối gạch chì + vệt sáng xiên + sàn tối dần), `room`, `floor` |
Người dùng nói "mượt", "như video AI", "có khối", "kiểu bình vỡ" → dùng kiểu SOFT. Ví dụ: [examples/binh-vo.soft.scenes.json](examples/binh-vo.soft.scenes.json) (8s, 16:9: 5 người đi vào, cúi/quỳ nhặt bình vỡ, đứng dậy cười).
Giới hạn thật (nói rõ với người dùng nếu họ so với video AI): thân là khối 2D, không xoay người 3D; tay là nét gập khuỷu; nét sạch kiểu đồ họa, không nhòe như chì thật.

## Quy trình
1. **Lập kế hoạch từ voice** (dọc mặc định; `--horizontal` cho 16:9):
   ```
   python ".../stick.py" plan "VOICE" -o "DỰ_ÁN"
   ```
   → `DỰ_ÁN/words.json` + `DỰ_ÁN/scenes.json` (khung sẵn: mỗi cảnh có start/end/text, items rỗng) và in danh sách câu. Dự án đặt cạnh file voice (vd `…/ten-video_nguoique/`) trừ khi người dùng nói khác.
2. **Viết hình cho từng cảnh** trong `scenes.json` (Claude tự làm, không hỏi từng cảnh):
   - Điền `title.lines` = câu hook ngắn nhất, 2 dòng (dòng 1 ngắn–to, dòng 2 dài hơn). Ý hook chọn theo công thức trong [references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt).
   - Khai báo `cast` (dàn nhân vật dùng lại xuyên video: bố/mẹ/con… hoặc nhân vật A/B) để hình dáng nhất quán.
   - Mỗi cảnh: chọn `bg`, `tone`, `cam`, `items` (người/đạo cụ/đám đông/chữ), `fx`. Dùng `keys` với `"t": "cụm từ trong câu"` để thay đổi **đúng lúc voice nói tới** (luật nhớ: nói đến đâu hiện đến đó).
   - Bảng gợi ý ẩn dụ ở cuối file này. Tránh lặp cùng 1 bố cục quá 2 cảnh liền.
   - Với dự án dài, nên viết 1 script Python nhỏ (như `examples/build_demo.py`) sinh `scenes.json` — dễ tái dùng hàm/cảnh.
3. **Duyệt hình trước khi render** (bắt buộc — Claude tự Read ảnh):
   ```
   python ".../stick.py" sheet "DỰ_ÁN/scenes.json" -o "DỰ_ÁN/sheet.png"            # mọi cảnh ở 60% thời lượng
   python ".../stick.py" sheet ... --scenes 5-10 --cols 3 --scale 0.45 --at 0.3    # soi kỹ, đổi thời điểm
   python ".../stick.py" still "DỰ_ÁN/scenes.json" --scene 7 --at 0.9 -o a.png     # 1 cảnh full-res
   ```
   Kiểm: người không bị cắt khỏi khung, không đè nhau vô lý, tay IK không duỗi quá dài, đạo cụ đúng cỡ, chữ tiêu đề không che mặt. Xem thêm ở `--at 0.1` và `--at 0.95` với cảnh có keys để thấy trước/sau thay đổi.
4. **Render**:
   ```
   python ".../stick.py" render "DỰ_ÁN/scenes.json" -o "DỰ_ÁN/ten_video.mp4"            # full HD, song song nhiều nhân, NVENC
   python ".../stick.py" render ... --preview --scenes 3-6 -o p.mp4                       # nháp nửa độ phân giải
   ```
   ~18–20 khung/s ở 1080×1920 (video 2 phút ≈ 4 phút). Âm: tăng gain + limiter, tự đo lại và bù cho tới −14 LUFS (±0.3), đỉnh ≤ −1 dBFS.
5. **QA sau render**: `ffprobe` độ dài = cảnh cuối; tách tờ khung (`ffmpeg -vf fps=2,scale=216:384,tile=5x2`) ở vài đoạn có chuyển động để chắc keys chạy đúng lúc. Rồi giao file + tóm tắt từng cảnh vẽ gì.

## Bảng ẩn dụ gợi ý
| Ý trong voice | Hình |
|---|---|
| hạnh phúc, đoàn tụ, bình yên | gia đình ôm nhau/nắm tay, `hut`/`field`, `golden`, `glow`, `lamp`, `rings` |
| đổ lỗi, cãi nhau, công kích | nhiều người `angry_point` + `reach` vào đầu nhau, `shake`, `talk`, `lightning` |
| lời nói cay độc | người `shout` + `bubble spiky angry`; người kia `lean_back`/`defend` |
| tổn thương, đau lòng | `crack` trên ngực, `hand_chest`, `hurt`; `heart` + `knife` cắm vào |
| rạn nứt, xa cách | `heart broken` tách dần; 2 người `slump` quay lưng; `wall`; tông `cold` |
| muốn thoát ra, ngột ngạt | bg `doorway`, người `dark` bước ra, cảnh cãi nhỏ phía sau |
| hàn gắn, bao dung | `heart` `broken`→0 + `mend` (băng dán), `tape`; người `kneel` an ủi, `reach` vai |
| cùng nhau giải quyết | `wall` biến mất, 2 người `walk` lại gần rồi `reach` bắt tay; `bridge` |
| trưởng thành, tự tin | `sapling` `grow` 0→1, trẻ ôm cây; `door` sáng + bắt tay, `briefcase` |
| ký ức, thời gian, người thân | `old` + `cane` dắt trẻ trên `path`, `frame` bay lên; `clock` |
| không có gì cả, mất mát | người chuyển `dark`, khung ảnh mờ dần (`opacity`→0), fx `darken` |
| giàu mà lạnh / nghèo mà ấm | chia đôi: `house` sáng + `rings` ↔ `hall` `cold` người đen đi xa nhau |
| lan tỏa, phát triển, cả cộng đồng | `crowd circle hold` quanh `tree` lớn, `rays`, cuối `cheer` |
| suy nghĩ, băn khoăn, lựa chọn | `think` + `worried` ở ngã rẽ `path`, `mark ?` |
| tiền bạc | `coins`, `moneybag`; công việc: `briefcase`, `phone`, `table` |
| sông nước, ngụ ngôn con thuyền, va chạm | bg `river` + `waves`, `boat` (có/không người, `flip`, keys `x` cho thuyền trôi tới), `lightning` lúc va |

## Lưu ý kỹ thuật
- Toạ độ `x,y` là tỉ lệ khung (hoặc panel); **`y` của người = mặt đất dưới chân**; `h` (người) và `s` (đạo cụ) là tỉ lệ **cạnh ngắn** của panel. Khung dọc: người lớn `h` 0.55–0.65, trẻ 0.34–0.42, mặt đất `y` 0.8–0.88.
- `face`: −1 (nhìn trái) … 0 (chính diện) … 1 (nhìn phải). Tư thế định nghĩa cho người nhìn phải; `face<0` tự lật. Muốn tư thế lật nhưng mặt nhìn thẳng: `"flip": true`.
- Tay nối người khác: `hold` (nắm tay ở ngang hông), `reach` (với tới `id.head/shoulder/chest/hand/...` hoặc `[x,y]`). Tự thân: tư thế `think`/`hand_chest`/`cover_face`/`hands_head` đã có IK sẵn.
- Nhân vật cùng `id` giữa các cảnh kế thừa `cast` → giữ nguyên hình dáng. Có thể ghi đè từng cảnh (vd con lớn lên: `"kind":"man","h":0.58`).
- Thiếu đạo cụ cần thiết: thêm hàm `@prop("ten")` trong `stickdraw.py` (vẽ bằng `pen.stroke/fill/hatch/glow`), ghi vào `references/scene-format.md`.
- Nền tĩnh được cache; chỉ nhân vật/đạo cụ "rung nét" (boil 6 lần/s) và chuyển động ở 15 hình/s như hoạt hình vẽ tay. `anim_fps`, `boil_fps` chỉnh trong plan (`boil_fps: 0` = tắt rung).
