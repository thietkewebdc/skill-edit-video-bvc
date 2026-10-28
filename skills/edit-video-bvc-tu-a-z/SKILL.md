---
name: edit-video-bvc-tu-a-z
description: Edit video TỪ A–Z theo phong cách chữ khối vàng/xanh — GIAI ĐOẠN A cắt ghép (bỏ đoạn dư thừa, nói vấp, lặp lại, vô nghĩa; khoảng lặng > 0.6s; mối nối còn 0.2s; đoạn giữ lại ≥ 2s; nội dung trùng giữ lần nói sau; đoạn lẻ 100% – đoạn chẵn zoom 150% căn khung điện ảnh bám theo nhân vật; xuất cả ngang 16:9 và dọc 9:16), rồi GIAI ĐOẠN B phủ tiêu đề hook, sub karaoke, chữ nhấn, minh họa, hiệu ứng 3D và SFX. Dùng khi người dùng nói "edit từ A đến Z", "cắt ghép và phủ chữ", "cắt bỏ đoạn thừa rồi phủ chữ", "dựng hoàn chỉnh video", hoặc gọi /edit-video-bvc-tu-a-z. Có chế độ CHỮ CHÌM SAU NHÂN VẬT (3D) — "chữ phía sau nhân vật", "chữ chìm sau người", "chữ 3D sau người" (scripts/text3d). Có chế độ CHÈN FOOTAGE B-ROLL toàn màn hình khớp lời nói, mép chuẩn theo frame (scripts/broll.py) — "chèn footage", "đưa cảnh minh họa vào", "file footage". Có chế độ CẮT 1 VIDEO DÀI THÀNH NHIỀU SHORT dọc 60–90s ("cắt thành short", "cắt ra nhiều video ngắn"), VIDEO NGANG DÀI ĐÃ CẮT SẴN ("không cần cắt ghép, tôi đã cắt rồi" — chỉ chuẩn âm + phủ chữ nhịp thưa), và THÊM NHẠC NỀN ("thêm nhạc", "ghép nhạc nền"). Chỉ phủ chữ mà KHÔNG cắt → dùng skill edit-video-bvc-chia-se. Có chế độ KHỬ ỒN / giảm tạp âm (RNNoise, `enhance.py --denoise`) — "khử ồn", "giảm tạp âm", "nền bị ồn", "tiếng quán cà phê".
---

# Skill: Edit từ A đến Z (cắt ghép + phủ chữ khối vàng/xanh)

Ba giai đoạn (A cắt ghép, B phủ chữ, C ảnh bìa), chạy nối tiếp trên cùng thư mục làm việc `<tên video>__edit/` cạnh video:

- **A. Cắt ghép** — `scripts/cut_edit.py`: bỏ phần thừa, nối mối cắt 0.2s, zoom xen kẽ 100% / 150%, căn khung theo mặt nhân vật (OpenCV), xuất `cut_16x9.mp4` + `cut_9x16.mp4` + `words.json` đã dời mốc.
- **C. Ảnh bìa / thumbnail** — `scripts/thumb.py` (chuẩn TikTok 9:16, kèm 16:9 và 1:1; xem mục Giai đoạn C).
- **B. Phủ chữ + hiệu ứng** — `scripts/sm_overlay.py` (giống skill edit-video-bvc-chia-se, thêm hỗ trợ khung ngang 16:9) chạy trên từng video đã cắt với **cùng một `plan.json`**.

Gọi script bằng đường dẫn tuyệt đối.

## Quy tắc cắt ghép (giai đoạn A — chủ kênh chốt)

| # | Quy tắc |
|---|---|
| A1 | **Bỏ**: đoạn dư thừa, nói vấp, lặp lại, vô nghĩa, và mọi **chỗ ngừng > 0.6s** — kể cả chỗ ngừng bị tiếng ồn xe/quạt/hơi thở "lấp" (engine đo khoảng cách giữa 2 chữ có tiếng RÕ, không chỉ khoảng im lặng). Không bỏ nội dung có ý. Tiếng ồn/vỗ tay sau câu cuối → cắt ngay sau câu cuối. |
| A2 | **Mối nối**: tổng khoảng lặng còn lại ở mỗi mối cắt = **0.2s** (0.1s cuối đoạn trước + 0.1s đầu đoạn sau). Mối cắt giữa câu (không có khoảng lặng) bám điểm âm thấp nhất ±0.15s, không lẹm chữ. |
| A3 | **Nội dung trùng** (nói lại một ý / một câu): đoạn TRƯỚC là lỗi hoặc vấp → **giữ đoạn SAU**, bỏ đoạn trước. |
| A4 | **Mỗi đoạn giữ lại ≥ 2s.** Câu ngắn hơn 2s → KHÔNG cắt khoảng lặng quanh nó, gộp với đoạn kề liền mạch (engine tự gộp; `plan` cảnh báo nếu không gộp được). |
| A5 | **Zoom xen kẽ**: đoạn 1, 3, 5… **100%** (khung gốc); đoạn 2, 4, 6… **150%**. Đoạn 150% căn khung theo chuẩn điện ảnh: mặt nhân vật **giữa khung theo chiều ngang**, **mắt nằm trên đường 1/3 từ trên xuống**, đủ khoảng trống trên đầu, không mất đầu. Khung bám nhân vật mượt (camera lia nhẹ khi nhân vật di chuyển). |
| A6 | **Xuất 2 bản** khi video gốc quay ngang: **16:9** (đoạn 100% giữ nguyên khung gốc) và **9:16** (khung dọc bám theo nhân vật; 150% cắt tiếp từ khung dọc). Gốc quay dọc → chỉ bản 9:16. |
| A7 | Không đổi thứ tự nội dung, không chèn cảnh khác. |
| A8 | **Đuôi video** (chủ kênh chốt 2026-09-29): sau chữ cuối cùng **giữ thêm 0.5s** — không cắt sát, không dừng đột ngột. Chỉ cắt sớm hơn khi trong 0.5s đó có **tiếng mới lẹm vào** (chữ kế, ồn, vỗ tay) hoặc **đổi cảnh** → cắt ngay trước chỗ đó. Engine tự làm; `plan` in dòng `⏹ đuôi …s` + lý do. Muốn khác cho 1 video → `"end_tail": 0.8` trong `cut.json`. Mối nối GIỮA video vẫn 0.2s (A2). |

## Quy tắc phủ chữ (giai đoạn B — như skill cũ)

| # | Quy tắc |
|---|---|
| 1 | **Mẫu chữ khối** (chỉ cho TIÊU ĐỀ và CHỮ NHẤN): Montserrat Black IN HOA, dòng trắng + dòng màu **bản to**, 2 dòng tự cân bằng bề rộng, **không viền, bóng đen đổ sát chữ**, không hộp nền, 2 dòng sát nhau. **Mỗi chữ 1 lớp**, **không mờ dần vào/ra**. Chi tiết: [references/mau-chu-khoi.md](references/mau-chu-khoi.md). |
| 2 | **Cặp màu theo video**: `"accent": "yellow"` (`#F4C80F`) hoặc `"cyan"` (`#00FFFF`). Nền nhiều mảng vàng (mái lá, tre, nắng) → `cyan`. |
| 3 | **Tiêu đề**: hook **2–6 từ**, hiện **ngay frame 0**, dài **5–10s**, đứng yên sắc nét, **không sub** trong lúc hiện. Hook mạnh = câu hỏi chạm nỗi đau + dòng màu 1–2 từ phản bác/khẳng định bản to (VD `LÀM VIDEO MẤT THỜI GIAN?|{BIỆN MINH!}`). Dòng màu dài 3+ từ → chữ nhỏ, kém nổi. |
| 3b | **Tiêu đề LUÔN 1 dòng trắng + 1 dòng màu**: trắng trên – màu dưới, hoặc màu trên – trắng dưới (`"{GOFI PHARMA}|TỔNG GIÁM ĐỐC"`). Dòng trắng đè nền sáng → đảo; vẫn chìm (áo trắng) → thêm `"dim": 0.2–0.25`. |
| 3c | **Màu tiêu đề = màu cả video** (chữ nhấn, từ đang nói trong sub, minh họa). |
| 4 | **Sub**: 2–3 từ (tối đa 18 ký tự/dòng), trắng ngà, từ đang nói theo màu tiêu đề, viền mỏng + bóng nhẹ. **Cỡ chữ (chủ kênh chốt)**: dọc 9:16 = **60** (60 px Full HD / **120 px 4K**, ~3.1% chiều cao, ở 66% chiều cao); ngang 16:9 = **50** (50 px Full HD / **100 px 4K**, ở 87%). Engine tự nhân theo độ phân giải — 4K luôn gấp đôi Full HD. **Tên riêng** viết hoa (thêm vào `proper_nouns`). |
| 5 | **Nhịp hiệu ứng 8–10s**, chữ nhấn ↔ minh họa xen kẽ, không trống quá 10s (≥ 6s giữa 2 hiệu ứng). |
| 6 | Chữ không đè mặt — kiểm tra cả đoạn 100% và đoạn 150% (mặt to hơn, cằm thấp hơn). |
| 6b | ~30% chữ nhấn 3D (`flip3d`/`swing3d`/`tilt3d`), không 2 hiệu ứng 3D liền nhau; có `cube`. |
| 7 | Mỗi hiệu ứng có SFX, tổng -7 dB, không nhạc nền. |
| 7b | Minh họa nét mảnh, gradient trên màu chính, icon trong huy hiệu vòng đôi. |

## Quy trình

**Giai đoạn A — cắt ghép**
1. `transcribe` video GỐC → `<work>/src_words.json`; **sửa chính tả** (chỉ sửa `w`; xóa từ thừa thì gộp thời gian vào từ trước). Hỏi người dùng tên riêng nghe không rõ (công ty, họ tên).
2. `cut_edit.py analyze` → `chunks.txt` (câu tách theo khoảng lặng > 0.6s đo từ âm thanh thật), `envelope.npy`, `face.json`.
   **Video quay đi quay lại nhiều lần** (mốc từ lệch, chữ dồn vào câu sai) → chạy thêm `cut_edit.py retext <work>`: nhận giọng LẠI từng câu (model `medium`, CPU) → `chunks.txt` + `src_words.json` chính xác. Câu chỉ có tiếng ồn hay ra chữ ảo kiểu "Hãy subscribe cho kênh…" → bỏ câu đó và xóa chữ ảo khỏi sub.
3. Đọc `chunks.txt` + `src_words.txt`, viết **`cut.json`** (xem [references/cut-schema.md](references/cut-schema.md)): `drop_chunks` (bỏ cả câu), `drop_ranges` (bỏ khúc giữa câu — lấy mốc từ đầu từ bị bỏ tới đầu từ được giữ), `trim` (bó đầu/cuối câu), ghi lý do vào `_notes`. Áp A1–A3.
4. `cut_edit.py plan` → duyệt danh sách đoạn: không đoạn nào < 2s, zoom xen kẽ đúng, không sót chữ lẻ ở mép (VD "nhưng" còn sót → dời mốc cắt).
4b. **DUYỆT LẦN 2 — BẮT BUỘC, TRƯỚC MỌI LẦN RENDER 4K** (không để cắt thiếu, cắt sót, còn đoạn thừa / lặp):
   - Chạy `cut_edit.py review <work>/cut.json` → `review.txt` liệt kê: **NGỪNG** (chỗ ngừng > 0.6s còn sót trong đoạn, kể cả bị tiếng ồn lấp), **TRÙNG CỤM** (cụm ≥ 5 từ lặp trong 60s → quay lại/nhắc ý), **VẤP/LẶP TỪ** ("có thể có thể"), **TỪ ĐỆM** (ờ, à, ừm…), **CHỮ VẮT MÉP** (chữ bị lẹm ở mối cắt), **MẨU THỪA** (mẩu tiếng ngắn + khoảng lặng ngay đầu/cuối đoạn = đuôi chữ vấp còn sót, VD "…mà… những cái kinh nghiệm").
   - Mốc `drop_ranges` khi bỏ một lần nói vấp: đặt ĐẦU phần giữ vào khoảng lặng NGAY TRƯỚC chữ đầu của lần nói lại (không đặt ở mốc máy nhận giọng — hay dính đuôi chữ kéo dài của lần vấp).
   - Đọc thêm toàn bộ lời các đoạn giữ lại (`newtl`/`plan`) như người xem: ý nào nói 2 lần (kể cả nhắc lại ý vừa nói, "câu chốt" lặp câu giữa bài) → bỏ lần TRƯỚC.
   - Sửa `cut.json` từng mục: NGỪNG do mẩu < 2s bị gộp → thay bằng lần nói trôi chảy khác của cùng câu, hoặc bỏ mẩu ngắn nếu câu vẫn liền mạch; TRÙNG/VẤP → bỏ lần trước; TỪ ĐỆM → `drop_ranges`; CHỮ VẮT MÉP → dời mốc.
   - **Lặp `review` → sửa cho tới khi sạch.** Mục nào giữ lại có chủ đích (ngừng không cắt được vì luật 2s, chủ đề nhắc lại cách xa, "người, người ta" tự nhiên) → ghi lý do vào `cut.json._notes` và báo người dùng.
   Đổi `analyze` (VD luật dò mới) làm số thứ tự câu thay đổi → dùng `keep_ranges` (mốc thời gian) thay cho `drop_chunks`. Sửa sub sau khi cắt: sửa `src_words.json` rồi chạy `cut_edit.py words <cut.json>` (không cần render lại).
4c. **KIỂM DUYỆT BẰNG ÂM THANH THẬT — BẮT BUỘC, TRƯỚC RENDER 4K** (`scripts/cut_qa.py`; chủ kênh chốt 2026-09-26 sau khi bắt lỗi: short dính âm thừa ở đầu, cụt chữ ở mối nối, "336 triệu" thành "36 triệu"). `review` chỉ đọc mốc chữ của máy nhận giọng — KHÔNG bắt được các lỗi này:
   - **Mép cắt theo CHỮ, không theo giây**: `cut_qa.py medwords <video> <work>` (mốc chữ bằng model medium) → trong `cut.json` ghi `keep_words` / `drop_words` / `pause_words` ("giữ từ chữ *cái* đến chữ *thu*") → `cut_qa.py wordsnap <work>` đặt mép vào **khoảng lặng thật** (năng lượng âm) ngay TRƯỚC chữ đầu / ngay SAU chữ cuối. Mốc whisper small lệch 0.1–0.3s → cắt theo nó là dính đuôi chữ trước hoặc lẹm chữ đầu.
   - **Không có khoảng lặng thì KHÔNG cắt giữa tiếng**: vấp/lặp dính liền ("video video", "họ sẽ họ sẽ", "nhỏ nhỏ nhỏ") → GIỮ NGUYÊN (cụt tiếng tệ hơn vấp nhẹ); ghi `_notes` + báo người dùng. `wordsnap` in `!!` cho mép không có lặng → bắt buộc nghe thử.
   - **Tiếng bị analyze bỏ sót**: cụm nói ngắn kẹp giữa 2 chỗ ngừng ("ba trăm … ba mươi sáu") bị coi là ồn lẻ, không vào câu nào → mất khi ghép. Sau `render --preview`: `cut_qa.py lost <work>` → có quãng `MẤT TIẾNG` → `lost --fix` (nới `trim` câu kề) → render lại → `lost` phải "sạch".
   - **Nghe lại video đã cắt**: `cut_qa.py listen <work>` (medium, **không VAD**, đệm 0.6s lặng — VAD làm mất chữ đầu, mẩu âm < 3s gây chữ ảo "Hãy subscribe cho kênh…") → `joints.txt`: lời quanh MỖI mối nối (‖) + dòng **SỐ LIỆU nghe được**. Đọc từng mối như người xem: dư chữ lẻ ("là", "thì", "cao"), mất chữ ("mất ‖" thiếu "thời gian"), câu cụt. **Số nghe lệch so với lời gốc (36 ≠ 336, 2007 ≠ 2027) = MẤT TIẾNG, không được coi là máy nghe nhầm.**
   - Mép nghi ngờ → `cut_qa.py try <video> t1,t2,t3` (nghe 2.2s từ nhiều điểm trên nguồn) → chọn điểm sạch, ghi thẳng số giây vào `keep_words` (VD `[478.58, 478.58, "hơn", 491.2]`).
   - `cut_qa.py edges <work>`: liệt kê mép đang nằm giữa dòng tiếng — mỗi mép phải đã được xác nhận bằng `listen`/`try`.
   - **Lặp tới khi `lost` sạch và mọi mối nối trong `joints.txt` đúng chữ** — rồi mới render 4K.
5. `cut_edit.py render --preview` → trích 1 khung giữa mỗi đoạn (cả 2 khung hình) → **xem thật**: đoạn 150% không mất đầu, mắt ở đường 1/3, mặt giữa khung.
6. `cut_edit.py render` (4K) → `cut_16x9.mp4`, `cut_9x16.mp4`, `words.json` (đã dời mốc), `segments.json`. Gốc quay dọc → engine tự chỉ xuất `cut_9x16.mp4`.
   ⚠ Mỗi lần `render` GHI ĐÈ `words.json` → sửa sub sau khi cắt thì lưu sang `words_final.json` và trỏ `plan.json` → `"words_file": "words_final.json"`.
   ⚠ `words.json` của engine BỎ MẤT chữ có mốc lọt vào khoảng lặng vừa cắt ("doanh nghiệp" → "nghiệp", "quảng cáo" → "cáo") → luôn dùng `cut_qa.py subs <work>` (ghép chữ mồ côi vào chữ sau) → `words_final.json`.

6b. **Âm lượng chuẩn (mặc định bật)** — `enhance.py` trên bản cắt → `cut_<khung>_enh.mp4` (hình copy nguyên, ~1 phút), dùng file này cho giai đoạn B:
   chỉ `loudnorm` về **-14 LUFS** (TikTok/YouTube/Facebook), LRA 7, đỉnh -1.5 dBTP → không quá to, không quá nhỏ, các đoạn đều nhau. Làm TRƯỚC khi thêm nhạc (nhạc đặt theo giọng đã chuẩn).
   **Khử ồn (tùy chọn, thêm 15/10/2026)**: mặc định KHÔNG khử (giữ tiếng tự nhiên). Khi nền ồn (quán cà phê, quạt, xe, người nói chuyện nền) hoặc người dùng nói "ồn / tạp âm / khử ồn":
   - Đo trước: `python "$S/denoise.py" "<video>" --check` → in độ chênh giọng–nền, **chênh < 20 dB = khuyên khử**.
   - Khử + chuẩn âm một lệnh: `python "$S/enhance.py" "<cut.mp4>" -o "<cut_enh.mp4>" --denoise` (RNNoise, `--denoise 0.85`).
   - **Mức 0.85 (85% tiếng khử ồn + 15% tiếng gốc) là mức khuyên dùng.** Đừng đặt 1.0: nền sạch hơn nhưng giọng méo (đo trên video quán cà phê: nghe lại chỉ khớp 46% chữ so với 87% ở mức 0.85, gốc 90%). Kết quả mẫu: nền −34 → −49 dB, giọng −1.7 dB.
   - Giới hạn: tiếng ồn ĐÚNG LÚC đang nói vẫn còn một phần (mô hình không tách hết, nhất là tiếng người nền cùng dải với giọng) → báo người dùng; muốn sạch hẳn phải quay lại bằng micro cài áo / chỗ yên.
   - Lần đầu tự cài môi trường RNNoise vào `~/.claude/hmt-denoise/venv` (~200 MB, cần mạng); không cài được → tự dùng ffmpeg `afftdn` (yếu, chỉ hợp ồn đều như quạt). Bộ lọc ffmpeg đơn thuần (`afftdn`, `anlmdn`, gate) KHÔNG giảm được ồn quán cà phê — đã thử, SNR chỉ +0.6 dB.
   Skill KHÔNG làm mịn da / trắng răng (chủ kênh đã bỏ).
   Máy có GPU NVIDIA → `cut_edit render` và `sm_overlay render` tự dùng **NVENC** (nhanh gấp nhiều lần libx264).

**Giai đoạn B — phủ chữ** (trên video đã cắt, 1 `plan.json` dùng chung cho cả 2 khung)
7. Chọn `accent`, tiêu đề (3b–3c), lên lịch hiệu ứng theo `words.json` đã dời mốc; viết `plan.json` theo [references/plan-schema.md](references/plan-schema.md).
8. `check` + `snap` trên **cả 2 video cắt** (0s + mỗi hiệu ứng, có cả đoạn 150%) → xem thật theo [references/checklist-qa.md](references/checklist-qa.md).
9. `render --preview` gửi người dùng, rồi **tự render bản cuối 4K luôn** (không cần hỏi) cho cả 2 khung.
10. **Nhạc nền (khi người dùng đưa file nhạc)**: `add_music.py` trên bản đã phủ chữ → `<tên>_<khung>_final_nhac.mp4`. Mặc định: san đều các đoạn trong bài, nhạc **thấp hơn giọng 17 dB** (riu riu, không lấn tiếng), hết bài tự lặp (crossfade 3s), mở 1.5s đầu, **nhỏ dần 4s cuối**. Hình copy nguyên, không encode lại. Người dùng muốn to/nhỏ hơn → `--rel -14` / `--rel -20`.

```
S="<skill>/scripts"
python "$S/sm_overlay.py" transcribe "<video>" -o "<work>/src_words.json"
python "$S/cut_edit.py"   analyze "<video>" "<work>/src_words.json" -o "<work>"
python "$S/cut_edit.py"   retext  "<work>"                                     # tùy chọn: video nhiều lần quay lại
python "$S/cut_edit.py"   plan    "<work>/cut.json"
python "$S/cut_edit.py"   review  "<work>/cut.json"                            # DUYỆT LẦN 2 — lặp tới khi sạch
python "$S/cut_qa.py"     medwords "<video>" "<work>"                          # 4c: mốc chữ chính xác (medium)
python "$S/cut_qa.py"     wordsnap "<work>"                                    # 4c: keep_words/drop_words → mép trong khoảng lặng thật
python "$S/cut_edit.py"   render  "<video>" "<work>/cut.json" --preview        # QA khung
python "$S/cut_qa.py"     lost    "<work>" --fix                               # 4c: nhập lại tiếng bị bỏ sót → render lại
python "$S/cut_qa.py"     listen  "<work>"                                     # 4c: NGHE LẠI mọi mối nối + số liệu → joints.txt
python "$S/cut_qa.py"     try     "<video>" 478.48,478.56,478.62               # 4c: nghe thử điểm bắt đầu nghi ngờ
python "$S/cut_qa.py"     subs    "<work>"                                     # sub không mất chữ → words_final.json
python "$S/cut_edit.py"   render  "<video>" "<work>/cut.json"                  # 4K: cut_16x9.mp4 + cut_9x16.mp4
python "$S/enhance.py"    "<work>/cut_9x16.mp4" -o "<work>/cut_9x16_enh.mp4"    # âm lượng chuẩn -14 LUFS (thêm --denoise nếu nền ồn)
python "$S/sm_overlay.py" check  "<work>/cut_9x16_enh.mp4" "<work>/plan.json"
python "$S/sm_overlay.py" snap   "<work>/cut_16x9.mp4" "<work>/plan.json" --at 0,20.9 -o "<work>/qa16"
python "$S/sm_overlay.py" render "<work>/cut_9x16.mp4" "<work>/plan.json" -o "<work>/<tên>_9x16_final.mp4"
python "$S/sm_overlay.py" render "<work>/cut_16x9.mp4" "<work>/plan.json" -o "<work>/<tên>_16x9_final.mp4"
python "$S/enhance.py"    "<work>/<tên>_9x16_final.mp4" -o "<work>/<tên>_9x16_final_chuan.mp4"   # SFX đẩy lên ~−13 LUFS / đỉnh −0.4 → chuẩn lại (hình copy)
python "$S/add_music.py"  "<work>/<tên>_16x9_final.mp4" "<nhạc.mp3>" -o "<work>/<tên>_16x9_final_nhac.mp4"   # tùy chọn
```

## Giai đoạn C — Ảnh bìa / THUMBNAIL (chuẩn TikTok, thêm 26/10/2026 theo ảnh mẫu của anh Bùi Viết Cường)
Làm SAU giai đoạn B (hook đã chốt), dùng chính hook của video để bìa và video đồng bộ nhận diện kênh. Công cụ: `scripts/thumb.py` + `scripts/cover_v2.py`.

| # | Quy tắc bìa 9:16 (1080×1920) |
|---|---|
| C1 | **Vùng an toàn TikTok**: 0–10% trên cùng để TRỐNG (thanh tìm kiếm); không đặt chữ ở cột icon bên phải (từ ~50% xuống ~80%, rộng ~16%); ~20% dưới cùng dành cho caption/giao diện. |
| C2 | **Người nói**: mặt ở ≈ 27–34% chiều cao, thấy vai và ngực; nền thật của căn phòng, không che mặt. Chọn khung mắt mở, mặt nét, biểu cảm mạnh (`thumb.py frames` xếp hạng sẵn). |
| C3 | **Logo tròn** góc trên trái (tâm ≈ 17% × 16.5%, đường kính ≈ 172 px), viền vàng `#F4C80F` phát sáng. Mặc định dùng `assets/avatar-giang-vien.png` của skill Dạng 1/2. |
| C4 | **Thẻ tên dạng tab** gắn góc trên trái ô tiêu đề: `#Bùi Viết Cường` (đổi bằng `--tag`). |
| C5 | **Ô tiêu đề** navy `#0A1F5A→#08164A` bo góc, ≈ 55–74% chiều cao, rộng ≈ 77% khung, viền xanh mảnh + **viền vàng phát sáng ở cạnh dưới và cạnh phải**. Không bao giờ vượt quá 74% chiều cao. |
| C6 | **Hook 3 dòng IN HOA, mỗi dòng ≤ 22 ký tự.** Kiểu **A**: 2 dòng trắng + dòng cuối VÀNG to hơn. Kiểu **B**: chữ số/con số màu vàng, mặt zoom gần hơn. Luôn ra cả A và B để chọn. |
| C7 | **Công thức hook**: *con số thật + nghịch lý + câu hỏi* (VD "LƯƠNG 120 TRIỆU / VẪN VỠ NỢ / VÌ 600 TRIỆU?"). Chỉ dùng con số CÓ trong lời nói; không bịa số, không cam kết. Công thức khác: nỗi đau, so sánh A/B, "vì sao…?" — xem `references/100-tieu-de-thu-hut.txt`. |
| C8 | **Hoa văn mờ theo chủ đề** sau chữ (`--icon auto`): $ (tiền, lương, nợ, doanh thu), đồng hồ (thời gian), biểu đồ (tăng, %); không khớp thì không vẽ. |
| C9 | **Dải navy** đậm dần từ ~64% xuống đáy (chỗ để caption). |
| C10 | Xuất đủ **9:16 (TikTok/Reels)**, **16:9 1280×720 (YouTube: chữ bên trái, người bên phải)**, **1:1 (Facebook)**. Luôn kèm `_check.jpg`: thu nhỏ 160 px + lớp tô đỏ vùng cần tránh; chữ phải còn đọc được ở 160 px. |

```
S="~/.claude/skills/edit-video-bvc-tu-a-z/scripts"
python "$S/thumb.py" frames "<video đã cắt>" "<work>/khung" --n 12            # 12 khung đẹp nhất → chọn 1
python "$S/thumb.py" make --photo "<video hoặc ảnh>" --at 12.5 \
   --hook "LƯƠNG 120 TRIỆU|VẪN VỠ NỢ|VÌ 600 TRIỆU?" --out "<work>/bia" \
   [--sizes 9x16,16x9,1x1] [--variants A,B] [--tag "#Bùi Viết Cường"] [--avatar <png>] [--icon auto|dollar|clock|chart|none]
```
- Lấy khung từ **video gốc 4K** (`--photo <video> --at <giây>`) để ảnh nét, không lấy từ ảnh đã nén.
- Nguồn quay ngang hoặc thấp hơn 1080p: bìa dọc sẽ mờ/phóng to, báo anh trước.
- Nguồn quay NGANG: thumbnail 9:16 phóng rất to và mờ (video 848×464 cho ra ảnh vỡ); ưu tiên bản 16:9, hoặc quay dọc ≥ 1080p. Bìa trong video Dạng 1/2 với nguồn ngang xem mục "Nguồn quay NGANG" của skill `edit-kieu-toan-khung-chuyen-nghiep`.
- **Bìa nằm trong video** (2,4s đầu của Dạng 1/Dạng 2) dùng cùng thiết kế: `cover_style` trong cfg (mặc định `"v2"`; `"v1"` = bìa Snaptik cũ), `cover_mode` `"A"|"B"`, `cover_icon`.
- Ghi kèm tiêu đề YouTube + caption TikTok có hook; lên lịch DC Post như skill Dạng 1/2.

## Video ngang DÀI đã cắt sẵn (YouTube nói chuyện, 10–40 phút) — chủ kênh chốt 2026-09-27
Người dùng nói "không cần cắt ghép, tôi đã cắt rồi" → **bỏ giai đoạn A**, chỉ: `enhance.py` (−14 LUFS) → [chèn footage nếu có] → giai đoạn B.
- **Hỏi trước khi làm**: kiểu chèn footage, màu nhấn (bối cảnh mới), nhạc/tiếng footage, tên riêng nghe không rõ (tên thầy/khách, dự án, đường).
- **Hook**: đọc hết lời thoại, đưa **3 câu hook mạnh nhất** theo file "100 tiêu đề thu hút" ([references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt), ghi số công thức), mỗi câu gồm tiêu đề YouTube + bản 2 dòng trên màn hình → người dùng chọn 1.
- **Nhận giọng video dài bằng `--model large-v3`** (GPU): bản `medium` sai nhiều thuật ngữ và BỎ SÓT câu ngắn ("Quá hay", "Đúng rồi", "Thì chúng ta cùng đi giải mã"). Sau đó ĐỌC HẾT từng câu, sửa bằng luật thay cụm từ (xem `fix_words2.py` của dự án phong thủy trên Desktop làm mẫu) — chủ kênh bắt lỗi còn sót như "chất hợp" → "kết hợp". Chỗ không nghe được → sửa theo nghĩa và BÁO người dùng mốc giờ để nghe lại.
  Engine tự viết thường mọi từ rồi viết hoa lại theo `proper_nouns` (so khớp cụm) → thêm đủ cụm tên riêng; KHÔNG thêm từ đơn trùng từ thường ("Thủy" sẽ biến "phong thủy" → "phong Thủy") — dùng cụm ("Thủy sinh", "phương Đông", "tiếng Việt").
  Đổi bản nhận giọng sau khi đã có plan → `python "$S/remap_plan.py" plan.json words_cũ.json words_mới.json` (dóng hàng từ, dời mọi mốc).
- **Nhịp thưa ~30s/hiệu ứng** (cảnh báo "khoảng trống" của `check` là luật video ngắn → bỏ qua); chỉ nhấn ý đắt + MỌI số liệu; `"punch": false` cả plan (zoompan 4K cả video rất chậm); `sfx_volume` 0.6.
- **Cỡ chữ nhấn khung ngang 4K**: `"fs": 240` (120 quá nhỏ). Biến thể `chapter` ra chữ nhỏ và lệch bề ngang → thay bằng khối 2 dòng thường, VD `ĐIỀU 01: ÁNH SÁNG|{THIÊN KHÍ}`.
- **Dùng `scripts/sm_sync.py` thay `sm_overlay.py`** (cùng lệnh check/snap/render):
  - số liệu / liệt kê: `"fx": "sync", "at": [mốc từng từ]` — mỗi từ hiện đúng lúc nói (đếm cả "·", "=", "–" là 1 từ; số mốc = số từ);
  - tiêu đề 2 dòng rộng bằng nhau: bỏ `"title"`, thêm chữ nhấn đầu `{"start": 0, "end": 7.5, "text": "CĂN HỘ SINH TÀI?|{3 ĐIỀU}", "fx": "sync", "static": true, "tw": 0.38, "at": [0,0,…]}`.
- **Chữ nhấn nội dung trang nghiêm** (bàn thờ, tâm linh) không hiện đè footage WC/bếp.
- **"Chỉ giữ tiêu đề và chữ nhấn, bỏ sub"** → copy plan, xóa `"words_file"`, render ra file MỚI `<tên>_khong_sub.mp4` (giữ bản có sub).

## Chèn footage B-roll (người dùng đưa file footage minh họa) — `scripts/broll.py`
Chủ kênh chốt (2026-09-27, video phong thủy 18 phút + 30 footage):
- Footage **toàn màn hình**, cắt thẳng, **tắt tiếng footage**, tiếng nói gốc chạy liên tục bên dưới; sub + chữ nhấn vẫn chạy trên footage.
- Mỗi cảnh **4–8s**; dùng **đủ** các footage; chèn khi **lời nói khớp cảnh**, hoặc tối đa **20–30s** một lần — điều kiện nào đến trước. Footage dài có thể dùng lại đoạn khác.
- **Không để mảnh hình ngắn**: đoạn nói giữa 2 khối footage ≥ 6.5s; không mảnh nào (nói hoặc footage) < 8 frame.
- Không để chữ nhấn "trang nghiêm" (bàn thờ, tâm linh) hiện đè cảnh WC/bếp — dời footage.
- **Lấy khúc ÍT RUNG nhất của mỗi footage** (chủ kênh chốt 2026-09-29): giây đầu/cuối clip hay rung (lúc bấm/tắt máy — đo thật: rung gấp 5–15 lần khúc giữa). Trong `sched` ghi `"auto"` ở cột "vào từ giây" → engine bỏ 0.5s đầu/cuối clip, chọn khúc rung ít nhất (lia máy đều không tính là rung), footage dùng lại thì lấy khúc khác không trùng. Ghi số giây bằng tay chỉ khi cần đúng một khoảnh khắc; `check` báo `!! rung` nếu khúc đó rung gấp ≥ 1.5 lần khúc tốt nhất.

Quy trình (chạy TRƯỚC giai đoạn B; plan chữ dùng `words` của video chính vì tiếng không đổi):
```
python "$S/broll.py" split  "<work>"     # dò cắt cảnh footage → broll_clips.json + qa/broll_index.jpg (đếm lại với số người dùng nói)
                                         #   + đo độ rung → qa/broll_shake.txt (rung đầu · giữa · cuối, khúc ổn định nhất)
python "$S/broll.py" stable "<work>"     # (chạy lại bảng độ rung sau khi sửa broll_clips.json bằng tay)
python "$S/broll.py" cuts   "<work>"     # dò điểm đổi góc máy của video chính → main_scenes.txt
#   viết <work>/broll.json: {"main": "main_enh.mp4", "footage": "...", "sched": [[mốc, footage#, "auto", dài, "lý do"], ...]}
python "$S/broll.py" check  "<work>"     # lặp tới khi OK
python "$S/broll.py" render "<work>" --to 100   # thử, trích frame quanh mỗi mép
python "$S/broll.py" render "<work>"     # → base_16x9.mp4 → đưa vào sm_overlay render
```
⚠ **Lỗi lọt 1 frame (chủ kênh bắt 2026-09-27)**: video chính đã tự cắt nhiều góc máy. Đặt mép footage theo GIÂY làm tròn (158.267 trong khi frame đổi góc là 158.2667) + `enable='between(t,…)'` → lọt 1 frame góc khác, nhìn như giật hình. Cách sửa (có sẵn trong `broll.py`):
1. Dò điểm đổi góc bằng `scene` (ngưỡng 0.06, lấy điểm ≥ 0.2) → đổi ra **số frame**.
2. Mép mỗi khối footage đổi sang frame; mép nào cách điểm đổi góc ≤ 6 frame → **bám đúng frame đó** (đổi góc được giấu dưới lúc chuyển footage).
3. Footage nối liền dùng **chung 1 mép frame**; overlay `enable='between(n,F0,F1-1)'` theo **số frame n**; footage `setpts=N/(fps*TB)+F0/(fps*TB)`, lấy dư 3 frame.
4. **Frame đầu tiên sau khi tua (`-ss`) file footage bị giải mã lệch** (đo được: nhảy 0.07–0.14 so với frame sau — nhìn như giật 1 frame ở MỌI đầu footage). → tua sớm 10 frame rồi `trim=start_frame=10` (hằng `PRE`).
5. File footage ghép sẵn có **vi cắt** 1–2 frame sát chỗ chuyển clip (VD 176.467 cắt thật + 176.533 vi cắt) → điểm vào footage cách mọi cắt/vi cắt ≥ 6 frame (`FOOT_MARGIN`); điểm thấp giữa cảnh (xe chạy, người đi) không phải vi cắt.
6. `check` báo mọi mảnh < 8 frame, footage chứa điểm cắt cảnh bên trong, footage thiếu frame → sửa lịch.
7. Sau render bản nền: `python "$S/broll_verify.py" "<work>"` → quanh MỖI mép, điểm khác biệt từng frame chỉ được có 1 cú nhảy lớn; mép nào báo `!!` → trích ~12 frame quanh đó xem tận mắt (chuyển động thật trong cảnh thì bỏ qua). Frame NGAY SAU cú cắt luôn bị bộ đo `scene` đội điểm 0.05–0.15 (báo nhầm, script đã bỏ qua). Nghi ngờ thật → so MSE từng frame bản ghép với frame nguồn footage: phải khớp liên tiếp +0, +1, +2… Lưu ý khi trích frame: `-ss` + `trim=start_frame` (không có `fps` trước) trả về 1 frame lặp lại — dùng `select=gte(n\,K)` + `-fps_mode passthrough`.

## Cắt 1 video dài thành nhiều short dọc — `scripts/shorts.py`
Chủ kênh chốt (2026-09-26, đóng gói thành công cụ 2026-09-29):
- Short **60–90s**, dọc 9:16, có sub + chữ nhấn kiểu chữ khối vàng/xanh. Tiêu đề theo công thức file "100 tiêu đề thu hút" ([references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt)).
- **Hỏi trước khi cắt**: đọc hết lời, đưa BẢNG đề xuất (đoạn gốc mm:ss–mm:ss · thông điệp · tiêu đề 2 dòng + số công thức) → người dùng chọn/sửa → mới viết `shorts.json`.
- Mỗi short là 1 ý TRỌN: bắt đầu ở chữ mở ý, kết ở câu chốt; mép theo CHỮ (`keep_words`), bỏ vấp/ngừng bằng `drop_words`/`pause_words`.
- Làm đủ 4b + **4c cho TỪNG short** (`shorts.py qa` làm thay) trước khi render 4K.
- Bản dọc có đoạn zoom 150% (mặt to, cằm thấp): minh họa `"y": 0.60`, `"hide_subs": true`, icon size ~210, nhãn to ~1.6×; `checklist` chữ quá nhỏ trên điện thoại → thay bằng chữ nhấn.

Quy trình (cấu trúc `shorts.json` ở đầu `scripts/shorts.py`):
```
python "$S/sm_overlay.py" transcribe "<video>" -o "<work>/src_words.json"   # 1 lần cho video GỐC → SỬA CHÍNH TẢ ở đây
python "$S/cut_edit.py"   analyze "<video>" "<work>/src_words.json" -o "<work>"
#   đưa bảng đề xuất → người dùng chọn → viết <work>/shorts.json
python "$S/shorts.py" setup  "<work>"            # short_<id>/ (hardlink dữ liệu gốc) + cut.json + plan.json khởi đầu
python "$S/shorts.py" qa     "<work>" --fix      # medwords → wordsnap → review → preview → lost → listen → edges
#   đọc <work>/shorts_qa.txt: độ dài 60–90s, REVIEW, MỐI NỐI từng short (như người xem), số liệu khớp lời gốc
#   sửa shorts.json (keep/drop/pause_words, _notes) → setup → qa --only <id> … lặp tới khi mọi short sạch
#   viết chữ nhấn/minh họa vào short_<id>/plan.json theo short_<id>/words_final.json
python "$S/shorts.py" render "<work>" --preview  # phủ chữ lên bản preview → gửi người dùng duyệt
python "$S/shorts.py" render "<work>"            # 4K → subs → −14 LUFS → phủ chữ → chuẩn âm lần cuối → _SHORTS_FINAL/
python "$S/shorts.py" status "<work>"            # bảng tiến độ
```
- Sửa chính tả trên `<work>/src_words.json` (file GỐC): mọi short dùng chung qua hardlink → chạy lại `qa`/`render` là thấy.
- Mục `review` giữ lại có chủ đích (ngừng không cắt được vì luật 2s, cụm lặp tự nhiên) → ghi `_notes` trong shorts.json + báo người dùng.
- `render` bỏ qua short có `plan.json` chưa có chữ nhấn (thêm `--bare` nếu chỉ muốn tiêu đề + sub).

## Chế độ CHỮ CHÌM SAU NHÂN VẬT (3D)
Khi người dùng nói "chữ phía sau nhân vật", "chữ chìm sau người", "chữ 3D sau người" → sau giai đoạn A (đã cắt + chuẩn âm lượng), làm giai đoạn B theo [references/chu-3d-sau-nguoi.md](references/chu-3d-sau-nguoi.md) với công cụ `scripts/text3d/` — chạy trên **file đã cắt** (`cut_9x16_enh.mp4` / `cut_16x9_enh.mp4`), video gốc của bước `compose` = chính file cắt đó; mỗi khung (dọc/ngang) chạy `matte` + `place` riêng vì vị trí người khác nhau.
`matte.py` → `place.py` → `engine3d.py render` (không zoom punch) → `compose.py` (`--no-mask` cho cảnh chèn không có người).
Luật chốt: mỗi chữ cái bị che **tối đa 1/2**, **≤ 2 chữ cái** bị chạm; các dòng **rộng bằng nhau**; báo người dùng đánh đổi chữ nhỏ hơn khi người ngồi giữa khung. Sub vẫn phủ bình thường (plan_3d_base.json có `"words_file"`).

## Tham chiếu
- [references/cut-schema.md](references/cut-schema.md) — cấu trúc `cut.json` + cách chọn đoạn cắt.
- [references/mau-chu-khoi.md](references/mau-chu-khoi.md) — mẫu tiêu đề/chữ nhấn, chọn màu.
- [references/chu-nhan-hieu-ung.md](references/chu-nhan-hieu-ung.md) — hiệu ứng chữ nhấn + SFX.
- [references/minh-hoa-sfx.md](references/minh-hoa-sfx.md) — thư viện minh họa và SFX.
- [references/plan-schema.md](references/plan-schema.md) — cấu trúc `plan.json`.
- [references/checklist-qa.md](references/checklist-qa.md) — kiểm tra trước khi giao.
- [references/chu-3d-sau-nguoi.md](references/chu-3d-sau-nguoi.md) — chữ chìm sau nhân vật (3D).

## SFX riêng (tùy chọn)
Thả file **WAV 16-bit** vào `sfx/` (tên theo SFX: `whoosh.wav`, `impact.wav`, `riser.wav`, …) — engine tự dùng thay âm tạo bằng code.

Yêu cầu máy: Python 3.10+, ffmpeg/ffprobe (có libass) trên PATH (ffmpeg 6.0 cũng chạy được), `pip install numpy faster-whisper opencv-python` (+ `onnxruntime` cho chế độ chữ 3D — `text3d/matte.py`).
