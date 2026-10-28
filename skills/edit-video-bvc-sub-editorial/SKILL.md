---
name: edit-video-bvc-sub-editorial
description: Phủ SUB KIỂU EDITORIAL (tạp chí sang trọng) lên video nói chuyện 9:16/16:9 theo MẪU CHUẨN của kênh "Short Hook Demo_editorial_vang" — gọn, dễ xem. Mỗi câu nói chỉ 1 điểm nhấn - 1 CHỮ KHÓA to màu VÀNG SÁNG (Inter Black in hoa hoặc serif Playfair) đặt GIỮA KHUNG, ngay trên đầu / chìm một phần sau đầu, giữ suốt câu; bên dưới là SUB NHỎ 2–4 TỪ Inter Light trắng cố định ở ngực, viết thường, không in đậm, không hiệu ứng, KHÔNG lặp lại chữ đang nhấn. Cụm serif 2 dòng ở ngực (câu chốt) và điểm đặc biệt (neon, vạch gạch đỏ, badge viên thuốc) đứng một mình, sub tự ẩn. Chữ tự né mọi khuôn mặt, dò mặt thật bằng OpenCV, soát lại sau render; quầng tối mềm + bóng gọn; flash trắng ở bước ngoặt; SFX rất nhẹ, không nhạc, chuẩn −14 LUFS. KHÔNG cắt ghép. Dùng khi người dùng nói "sub kiểu editorial", "sub sang trọng kiểu tạp chí", "sub như video bất động sản / video mẫu Your home", "chữ serif + chữ mảnh", "sub kiểu luxury", "sub giống Short Hook Demo", hoặc gọi /edit-video-bvc-sub-editorial. Muốn kiểu chữ khối Montserrat vàng/xanh → dùng skill edit-video-bvc-chia-se (Phủ chữ & Hiệu ứng Video chia sẻ).
---

# Skill: Sub kiểu EDITORIAL (tạp chí)

*Phát triển bởi Bùi Viết Cường · Nền tảng gốc: Hồ Mạnh Thắng (kênh HMT)*

Skill chỉ phủ **lớp chữ + đồ họa nhẹ + SFX** lên video đã dựng. Không cắt, không zoom hình.
Engine: `scripts/ed_overlay.py` (Python + ffmpeg/libass), font trong `fonts/`, tách người `scripts/text3d/matte.py`, soát mặt `scripts/face_qa.py`.
Gọi script bằng **đường dẫn tuyệt đối**.

## MẪU CHUẨN — làm giống video này (chủ kênh chốt 2026-10-07)
`Short Hook Demo_editorial_vang.mp4` (bản demo nội bộ, không kèm gói) · plan: `plan_vang.json` cùng thư mục.
Chủ kênh: *"sub tùm lum quá, hơi rối"* → mọi video làm theo đúng 6 điều sau. **Khi luật cũ bên dưới mâu thuẫn, MẪU CHUẨN thắng.**

| # | Điều | Cụ thể |
|---|---|---|
| M1 | **Mỗi lúc chỉ 1 điểm nhấn** | 1 chữ khóa (1–2 từ, ≤ 12 ký tự) cho mỗi câu nói, giữ suốt câu (3–5s). Câu không có từ đắt → **chỉ sub**, không cố nhấn. Nhịp ~1 điểm nhấn / 2.5–3s. |
| M2 | **Chữ khóa to, giữa khung, trên đầu** | Đặt ở y ~0.18–0.28, **giữa khung theo chiều ngang**, ngay trên đỉnh đầu hoặc chìm một phần sau đầu (đầu che ≤ 1/2 một chữ cái, ≤ 2 chữ cái). Engine ưu tiên **dời lên** trên đầu, giữ cỡ ≥ ×0.8, không dạt ngang. Mép trên an toàn 0.15 (chừa thanh TikTok). |
| M3 | **Ít kiểu chữ, một tông vàng** | Chỉ dùng: `caps_title` / `caps_big` (Inter Black in hoa vàng) cho phần lớn chữ khóa · `serif_hook` (serif vàng) mở đầu · `thin_silver` (dòng đệm nhỏ + chữ khóa vàng: "chuyện gì / XẢY RA?", "quy tắc / 90/10") · `serif_top_pair` (2 dòng serif vàng trên đầu) · `serif_pair` (cụm ở ngực) · `neon` · `strike` · `pills` · `flash`. **Không** dùng chữ trắng mảnh ở tầng trên (trông như sub), không serif vàng nhạt trên nền tối, không đổi kiểu liên tục. |
| M4 | **Sub nhỏ 2–4 từ, cố định** | Inter Light 70, trắng, **mỗi cụm 2–4 từ**, ở **ngực (y 0.52)**, viết thường (tên riêng viết hoa), **không in đậm, không hiệu ứng**. Chỉ dời xuống dưới cằm khi đè mặt. |
| M5 | **Sub không lặp chữ nhấn** | Từ đang hiện ở chữ khóa được **bỏ khỏi sub** (không có "7 THÁNG 10" + sub "ngày 7 tháng"). |
| M6 | **Khi nào ẩn sub** | ① chữ khóa trên đầu → sub vẫn chạy bên dưới · ② cụm serif 2 dòng ở ngực (câu chốt) → **ẩn sub** · ③ `neon`, `strike`, `pills` → **ẩn sub**. Engine tự làm; plan ghi `"hide_subs": true/false` để ép. |

Tỉ lệ trong mẫu (41.6s, 16 điểm nhấn): ~10 chữ khóa trên đầu (①), 2 cụm ngực (②), 3 điểm đặc biệt (③: neon VIRAL, vạch gạch KHÔNG VIẾT, badge Tự động / Chuyển khoản / Mua hàng), 2 flash.

## Luật kỹ thuật (giữ nguyên, áp trong khuôn khổ MẪU CHUẨN)
| # | Luật |
|---|---|
| 1 | **Không viền, không hộp nền.** Bóng gọn (lệch chéo ~4% em, nhòe ít, đen ~55%) + **quầng tối mềm `"halo": "dark"`** cho chữ vàng. Engine đặt sẵn — plan chỉ cần `style` + `lines`. |
| 2 | **Màu**: chữ khóa VÀNG SÁNG (`gold` #FFD60A · `gold_grad` · `gold_soft` · `neon` vàng), dòng đệm trắng, đỏ chỉ cho vạch gạch. Bộ tím (`"theme": "tim"`) chỉ khi người dùng nói "chữ tím". Màu khác cho riêng 1 video → ghi đè `"palette"`/`"color"`, không sửa mặc định. Nền tối → tránh `gold_soft`/serif mảnh (chìm), dùng `gold` đặc. |
| 3 | **Từng từ hiện đúng lúc nói** (blur-in 0.18s, engine dò mốc trong `words.json`), giữ bằng drift 2–6%, ra blur-out 0.2s. Không bay, không nảy. Chữ câu trước tắt hẳn rồi chữ câu sau mới vào. |
| 4 | **Chữ sau người** (`behind`, cần `mask.mp4`): mỗi chữ cái bị che ≤ 1/2, ≤ 2 chữ cái chạm; chữ lơ lửng được hạ tới khi đầu che 25–50% ở 1–2 chữ cái. Không có người → `"behind": false`. Engine tự dời, in kết quả khi `check`. |
| 5 | **Không che mặt — mọi khuôn mặt**: chữ phía trước người chạm mặt ≤ 3% (`FACE_MAX`); engine gộp khung mặt từ mask + mặt dò thật bằng OpenCV (`cv_faces`). Sau `render --preview` chạy `face_qa.py` → phải **SẠCH**. |
| 6 | **Vùng an toàn** (khung dọc): mọi chữ trong x 8–92%, **y 15–75%**. `check` in "VÙNG 3:4 → …"; báo KHÔNG ĐẠT → đổi khuôn câu đó (VD sang ② với `"behind": false`). Tắt riêng 1 video: `"safe": false`. |
| 7 | **Selfie cận, cằm thấp (y > 0.58)**: phóng khung 125% neo trên → `reframe.mp4` (`crop=iw*0.8:ih*0.8:iw*0.08:ih*0.184,scale=<gốc>`), cắt y hệt mask → `mask_reframe.mp4`; chữ khóa `"behind": false` dưới cằm (y ~0.66), sub `"sub": {"y": 0.735, "halo": true}`. Báo người dùng video này không có chữ chìm sau đầu. |
| 8 | **Selfie 2 người / mặt chiếm giữa khung**: cụm ngực đặt `"y": 0.68–0.72`; dấu dòng dưới (Ế, Ỷ) đâm dòng trên → nới `"gap"` 0.12–0.26. Sub dưới cằm trên áo sáng → `"sub": {"halo": true}`. |
| 9 | **Ngắt sub theo từ ghép** (`scripts/vi_tu_ghep.txt`): không tách "thương hiệu", "bất động sản", "con số 0"; không bỏ lửng "của/tại/những" cuối cụm; ưu tiên ngắt sau dấu phẩy, chỗ ngừng. Từ ghép mới → thêm vào file hoặc `"sub": {"join": [...]}`. |
| 10 | **Sub viết thường** — chỉ tên riêng/thương hiệu viết hoa (`PROPER_DEFAULT` + plan `"proper_nouns"`); `check` in "SUB VIẾT THƯỜNG" để soát tên bị hạ nhầm. |
| 11 | **Footage quay màn hình / B-roll đầy chữ**: không sub cả đoạn → `"sub_zones": [{"start","end","hide": true}]`. |
| 12 | **Bản ngang 16:9**: sub 1 dòng 8–12 từ ở đáy (y 0.86), Inter SemiBold 54 + quầng tối (engine tự bật `SUB_LAND`); chữ khóa vẫn theo M1–M3. |
| 13 | **SFX rất nhẹ, không nhạc** (master −9 dB): boom trầm hook đầu, whoosh nhẹ chữ trên đầu, swipe vạch gạch, "bloop" badge (viên sau cao hơn), riser + hit cho flash. Sub không có SFX. Tự chuẩn −14 LUFS / đỉnh −1.5 dBTP. |
| 14 | Tiếng Việt: Playfair và Inter đủ dấu; chữ in hoa có dấu cao hơn nên engine tự nới dòng. |

## Kiểu chữ (chi tiết: [references/kieu-chu.md](references/kieu-chu.md))
- **Dùng thường xuyên (MẪU CHUẨN):** `caps_title` · `caps_big` · `serif_hook` · `thin_silver` · `serif_top_pair` (trên đầu) · `serif_pair` (ngực) · `neon` · `strike` · `pills` · `flash`.
- **Chỉ khi người dùng yêu cầu riêng:** `serif_dark` · `thin_caps` · `thin_bold` (+`swap`) · `gradient_serif` · `serif_italic` · `caps_italic` · `serif_color` · `caps_invert` · `scatter` · `image` (logo) · `bubble` (CTA).

## Quy trình
1. **Thư mục làm việc** `<tên video>__editorial/` đặt cạnh video.
2. **Nhận giọng nói** `--model large-v3` (GPU): `transcribe` → `words.json` + `words.txt`. **Sửa chính tả** (chỉ sửa `w`, giữ thời gian), gộp mảnh tách (`1` + `%`). Whisper hay bịa câu cuối ("Hãy subscribe…") → xóa.
3. **Tách người**: `matte.py` → `mask.mp4`. Thiếu mô hình ONNX → xin phép người dùng rồi mới tải.
4. **Lên bảng theo câu** (mốc câu · khuôn ①/②/③ · chữ khóa): mỗi câu tối đa 1 điểm nhấn; ~60–70% ①, ~15% ②, ~15% ③; câu thường → chỉ sub. Mở đầu bằng ① (`serif_hook` hoặc `caps_title`), chọn hook theo [references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt) rồi rút còn 1–2 chữ khóa. Kết bằng ② (câu chốt) hoặc ① (con số).
5. **Viết `plan.json`** theo [references/plan-schema.md](references/plan-schema.md); plan mẫu chuẩn: `plan_vang.json` ở thư mục MẪU CHUẨN.
6. `check` → sửa hết cảnh báo (đọc phần CHỮ SAU NGƯỜI, VÙNG 3:4).
7. `snap` giữa mỗi điểm nhấn → **mở ảnh xem thật**, so với MẪU CHUẨN: 1 chữ khóa to giữa khung trên đầu + 1 dòng sub nhỏ ở ngực, không lặp chữ.
8. `render --preview` → `face_qa.py` phải SẠCH → gửi người dùng → `render` bản cuối.
9. Góp ý: chỉ sửa `plan.json` / `words.json` rồi render lại.

```
S="<skill>/scripts"
python "$S/ed_overlay.py" transcribe "<video>" -o "<work>/words.json" --lang vi --model large-v3
python "$S/text3d/matte.py" "<video>" -o "<work>/mask.mp4"
python "$S/ed_overlay.py" check  "<video>" "<work>/plan.json"
python "$S/ed_overlay.py" snap   "<video>" "<work>/plan.json" --at 1.2,3.1,13.9 -o "<work>/qa"
python "$S/ed_overlay.py" render "<video>" "<work>/plan.json" -o "<work>/preview.mp4" --preview
python "$S/face_qa.py" "<video>" "<work>/preview.mp4"
python "$S/ed_overlay.py" render "<video>" "<work>/plan.json" -o "<work>/<tên>_editorial.mp4"
# đổi bản nhận giọng sau khi đã có plan (VD small → large-v3): dời mọi mốc trong moments
python "$S/remap_plan.py" "<work>/plan.json" "<work>/words_cũ.json" "<work>/words.json"
```
Chữ nhấn khớp nhầm từ (từ lặp gần nhau) → ghi `"at"` mốc từng từ cho dòng đó. Câu lặp lại đúng từ được nhấn ngay trước/sau → kéo `start`/`end` qua từ lặp để sub không hiện lại từ đó.

## Tham chiếu
- [references/phan-tich-video-mau.md](references/phan-tich-video-mau.md): phân tích video mẫu tiếng Anh gốc (font, chuyển động, SFX).
- [references/kieu-chu.md](references/kieu-chu.md): thông số từng kiểu chữ.
- [references/plan-schema.md](references/plan-schema.md): cấu trúc `plan.json`.
- [references/sfx.md](references/sfx.md): bảng SFX, thay bằng file WAV riêng.
- [references/checklist-qa.md](references/checklist-qa.md): kiểm tra trước khi giao.

Yêu cầu máy: Python 3.10+, ffmpeg/ffprobe có libass trên PATH, `pip install numpy faster-whisper onnxruntime opencv-python`.
