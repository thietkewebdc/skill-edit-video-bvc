---
name: edit-video-bvc-chia-se
description: PHỦ CHỮ & HIỆU ỨNG VIDEO CHIA SẺ — phủ sub, tiêu đề hook, chữ nhấn, minh họa, hiệu ứng động và SFX lên video dọc 9:16 hoặc ngang 16:9 (engine tự đổi bố cục theo khung) theo phong cách chữ khối vàng/xanh — KHÔNG cắt ghép video. Tiêu đề và chữ nhấn dùng mẫu chữ khối Montserrat Black 2 dòng (dòng trắng nhỏ + dòng màu lớn vàng hoặc xanh cyan), bóng đen đặc đổ chéo, dòng sát nhau, ở giữa khung; tiêu đề 5–10s từ frame đầu và ẩn sub; sub 2–3 từ karaoke giữ kiểu riêng; cứ 8–10s có một hiệu ứng (chữ nhấn slam/zoom/stagger/wipe/type hoặc minh họa) kèm SFX. Có chế độ CHỮ CHÌM SAU NHÂN VẬT (3D) — tách người khỏi nền, chữ nằm sau đầu/vai, không che mặt (scripts/text3d). Dùng khi người dùng nói "phủ chữ & hiệu ứng video chia sẻ", "phủ chữ khối vàng/xanh", "làm sub chuyên gia", "phủ chữ cho video", "thêm tiêu đề + sub + hiệu ứng", "làm sub giống video mẫu", "chữ phía sau nhân vật", "chữ chìm sau người", "chữ 3D sau người". Có tiện ích KHỬ ỒN (`scripts/denoise.py`) — "khử ồn", "giảm tạp âm".
---

# Skill: Phủ chữ & Hiệu ứng Video chia sẻ

*Phát triển bởi Bùi Viết Cường · Nền tảng gốc: Hồ Mạnh Thắng (kênh HMT)*

Skill **chỉ phủ lớp chữ + minh họa + hiệu ứng + âm thanh** lên video đã dựng. Không cắt, không ghép, không đổi thứ tự. Hiệu ứng duy nhất đụng vào hình là **zoom punch** (phóng nhẹ 5–10% lúc chữ nhấn đập vào).

Engine: `scripts/sm_overlay.py` (Python + ffmpeg/libass; font Montserrat trong `fonts/`). Gọi bằng đường dẫn tuyệt đối.

## Quy tắc đã chốt với chủ kênh

| # | Quy tắc |
|---|---|
| 1 | **Mẫu chữ khối** (chỉ cho TIÊU ĐỀ và CHỮ NHẤN): Montserrat Black IN HOA, dòng trắng + dòng màu **bản to**, **2 dòng tự đổi cỡ để luôn cân bằng bề rộng** (khối chữ vuông như mẫu), **không viền, bóng đen đổ sát chữ** (lệch 1.6% cỡ chữ, chéo phải-dưới, mép sắc), không hộp nền, 2 dòng gần nhau như mẫu. **Mỗi chữ chỉ 1 lớp** (bóng nằm trong chính lớp chữ), **không mờ dần vào/ra** — chữ vào bằng chuyển động, ra bằng cắt gọn. Chi tiết: [references/mau-chu-khoi.md](references/mau-chu-khoi.md). |
| 2 | **Cặp màu theo video**: `"accent": "yellow"` (trắng–vàng `#F4C80F`) hoặc `"cyan"` (trắng–xanh `#00FFFF`). Chọn theo nội dung/tông hình (xem mau-chu-khoi.md). Minh họa dùng cùng màu nhấn. |
| 3 | **Tiêu đề**: hook rút gọn **2–6 từ**, hiện **ngay frame 0**, dài **5–10s**, hợp ý đoạn mở đầu, **đứng yên sắc nét — không hiệu ứng ánh sáng đầu video**. **Không có sub** trong lúc tiêu đề hiện. Dòng màu nên 1–2 từ ngắn để chữ to như mẫu. |
| 3b | **Tiêu đề LUÔN là 1 dòng trắng + 1 dòng màu** (màu = xanh cyan hoặc vàng, theo `accent`). Hai cách, chọn theo nền: **trắng trên – màu dưới** `"DẤU HIỆU|{THÀNH CÔNG}"` hoặc **màu trên – trắng dưới** `"{3 PHONG THỦY}|QUÝ GIÁ"`. Không bao giờ 2 dòng cùng màu hay xanh + vàng. Dòng trắng mà đè lên nền sáng (trời, áo trắng) → đảo cho dòng đó thành dòng màu. Kiểm tra bằng snap 0s. |
| 3c | **Màu tiêu đề quyết định màu cả video**: tiêu đề xanh → chữ nhấn, từ đang nói trong sub, minh họa đều xanh; tiêu đề vàng → tất cả vàng. Engine tự làm theo `accent`. |
| 4 | **Sub KHÔNG dùng mẫu chữ khối**: 2–3 từ (tối đa 18 ký tự/dòng), **cỡ 60 = 60 px Full HD / 120 px 4K** (~3.1% chiều cao, ở 66% chiều cao; engine tự nhân theo độ phân giải — chủ kênh chốt), trắng ngà, từ đang nói **theo màu tiêu đề** (vàng `#F4C80F` hoặc xanh `#00FFFF`), **viền đen thật mỏng + bóng nhẹ khép sát** (cùng kiểu với tiêu đề). **Tên riêng** (người, địa danh, thương hiệu) viết hoa chữ cái đầu. |
| 5 | **Nhịp hiệu ứng: 8–10s một lần**, chữ nhấn và minh họa **xen kẽ**, không bao giờ trống quá 10s. |
| 6 | Mọi chữ trong dải giữa khung (44–72% chiều cao), không đè mặt, không xuống vùng UI đáy. |
| 6b | **Có hiệu ứng 3D**: ~30% chữ nhấn dùng `flip3d` / `swing3d` / `tilt3d`; icon xoay 3D khi hiện; có minh họa `cube` (khối 3D xoay). Chữ 3D vẫn là 1 lớp. |
| 7 | **Mỗi hiệu ứng có SFX**: whoosh + impact cho chữ nhấn, SFX riêng cho minh họa (xem bảng). Âm lượng tổng hiệu ứng **-7 dB** (`SFX_MASTER_DB`). Không nhạc nền. |
| 7b | **Minh họa sang trọng**: nét mảnh bo tròn, **gradient trên màu chính** (vàng nhạt→#F4C80F→vàng đồng / xanh nhạt→cyan→xanh biển sâu); icon đặt trong **huy hiệu vòng đôi + điểm kim cương**. |
| 8 | **Không cắt ghép.** Người dùng muốn cắt → báo skill không làm việc đó. |
| 9 | **Khung NGANG 16:9** (engine tự nhận khi video rộng hơn cao — cùng bộ engine với skill edit-video-bvc-tu-a-z): canvas 1920×1080, chữ khối thu nhỏ (×0.56, rộng tối đa 62% khung) và hạ xuống y 0.68 cho khỏi đè cằm, minh họa dời xuống 12%, **sub cỡ 50 = 50 px Full HD / 100 px 4K ở 87% chiều cao** (đáy khung). Bản `--preview` ra 1920 ngang. Luật 6 (dải 44–72%) chỉ áp cho khung dọc. Video ngang dài: xem thêm nhịp thưa ~30s/hiệu ứng nếu chủ kênh yêu cầu; luôn `snap` kiểm cỡ chữ trước khi render (4K có lúc cần `"fs"` riêng). |

## Chế độ CHỮ CHÌM SAU NHÂN VẬT (3D)
Khi người dùng nói "chữ phía sau nhân vật", "chữ chìm sau người", "chữ 3D sau người", "tách nhân vật ra chồng lớp chữ" → làm theo [references/chu-3d-sau-nguoi.md](references/chu-3d-sau-nguoi.md), công cụ trong `scripts/text3d/`:
`matte.py` (tách người, Robust Video Matting) → `place.py` (tự đặt khối chữ) → `engine3d.py render` (lớp chữ, không zoom punch) → `compose.py` (đè lớp người lên chữ).
Luật chốt: mỗi chữ cái bị che **tối đa 1/2**, **≤ 2 chữ cái** bị chạm; các dòng **rộng bằng nhau** (`"tw"`); cảnh không có người → `--no-mask` (chữ nằm trên). Báo người dùng đánh đổi: người ngồi giữa khung → khối chữ dạt 1 bên, nhỏ hơn bản thường.
## Quy trình

1. **Video**: đường dẫn file. Thư mục làm việc `<tên video>__edit/` cạnh video.
1b. **(Tùy chọn) Khử ồn** khi nền ồn (quán cà phê, quạt, xe…) hoặc người dùng nói "ồn/tạp âm": `python "<skill>/scripts/denoise.py" "<video>" --check` (chênh giọng–nền < 20 dB = khuyên khử) rồi `python "<skill>/scripts/denoise.py" "<video>" -o "<work>/video_dn.mp4" --mix 0.85` và dùng file này cho các bước sau. Mức 0.85 (85% khử + 15% gốc) là mức khuyên dùng — 1.0 làm méo giọng. Tiếng ồn đúng lúc đang nói vẫn còn một phần. Lần đầu tự cài RNNoise vào `~/.claude/hmt-denoise/venv` (~200 MB, cần mạng).
2. **Nhận giọng nói**: `python sm_overlay.py transcribe "<video>" -o "<work>/words.json"` → có thêm `words.txt` để đọc.
3. **Sửa chính tả `words.json`** (bắt buộc; chỉ sửa `w`, không đổi thời gian). Có kịch bản gốc thì đối chiếu.
   Liệt kê **tên riêng** xuất hiện trong lời nói (tên người, địa danh, thương hiệu, sản phẩm) vào `"proper_nouns"` của plan — engine tự viết hoa chữ cái đầu trong sub (đã có sẵn danh sách phổ biến: Facebook, YouTube, TikTok, Zalo, Việt Nam, Hà Nội, Sài Gòn…).
4. **Chọn cặp màu** (`accent`) theo nội dung + tông hình. Không chắc → hỏi người dùng hoặc snap cả 2 cho xem.
5. **Tiêu đề** (quy tắc 3b–3c): đọc 5–10s đầu → đề xuất 3 hook 2–6 từ theo mẫu `DÒNG TRẮNG|{DÒNG MÀU}` (VD `QUY TẮC|{90/10}`, `GẶP NHAU TẠI|{CYPRUS}`) cho người dùng chọn nếu họ chưa đưa. Đặt `end` = hết câu mở đầu, trong 5–10s. Ý hook chọn theo công thức trong [references/100-tieu-de-thu-hut.txt](references/100-tieu-de-thu-hut.txt) (ghi số công thức), rồi rút gọn còn 2–6 từ.
6. **Lên lịch hiệu ứng 8–10s/lần** — xen kẽ chữ nhấn ↔ minh họa, bám đúng lúc người nói nói ý đó. Xem [references/chu-nhan-hieu-ung.md](references/chu-nhan-hieu-ung.md) và [references/minh-hoa-sfx.md](references/minh-hoa-sfx.md).
7. **Viết `plan.json`** theo [references/plan-schema.md](references/plan-schema.md).
8. `check` → sửa hết cảnh báo.
9. `snap` tại 0s, giữa tiêu đề, mỗi hiệu ứng (≈ start + 0.8s) → **mở ảnh xem thật** theo [references/checklist-qa.md](references/checklist-qa.md).
10. `render --preview` (1080p nhanh) → gửi người dùng → `render` bản cuối (độ phân giải gốc, CRF 17).
11. Sửa theo góp ý: chỉ chỉnh `plan.json`/`words.json` rồi render lại.

```
python "<skill>/scripts/sm_overlay.py" transcribe "<video>" -o "<work>/words.json"
python "<skill>/scripts/sm_overlay.py" check  "<video>" "<work>/plan.json"
python "<skill>/scripts/sm_overlay.py" snap   "<video>" "<work>/plan.json" --at 0,4,16.2 -o "<work>/qa"
python "<skill>/scripts/sm_overlay.py" render "<video>" "<work>/plan.json" -o "<work>/preview.mp4" --preview
python "<skill>/scripts/sm_overlay.py" render "<video>" "<work>/plan.json" -o "<work>/<tên>_final.mp4"
```

## Tham chiếu
- [references/mau-chu-khoi.md](references/mau-chu-khoi.md) — phân tích mẫu tiêu đề/chữ nhấn, thông số, chọn màu.
- [references/chu-nhan-hieu-ung.md](references/chu-nhan-hieu-ung.md) — các kiểu hiệu ứng chữ nhấn + lớp phụ + SFX.
- [references/minh-hoa-sfx.md](references/minh-hoa-sfx.md) — thư viện minh họa và SFX.
- [references/plan-schema.md](references/plan-schema.md) — cấu trúc plan.json.
- [references/checklist-qa.md](references/checklist-qa.md) — kiểm tra trước khi giao.
- [references/chu-3d-sau-nguoi.md](references/chu-3d-sau-nguoi.md) — chữ chìm sau nhân vật (3D): tách người, luật che chữ, quy trình.
- [examples/plan-mau.json](examples/plan-mau.json) — plan hoàn chỉnh cho video mẫu.

## SFX riêng (tùy chọn)
Thả file **WAV 16-bit** vào `sfx/` của skill, đặt tên theo SFX muốn thay: `whoosh.wav`, `impact.wav`, `riser.wav`, `sparkle.wav`, `pop.wav`, `swish.wav`, `tick.wav`, `chime.wav`, `shimmer.wav`, `whoosh_soft.wav`, `impact_soft.wav`. Engine tự dùng file đó thay âm tạo bằng code.

Yêu cầu máy: Python 3.10+, ffmpeg/ffprobe (có libass) trên PATH, `pip install numpy faster-whisper` (+ `onnxruntime` cho chế độ chữ 3D — `text3d/matte.py`).

**GPU NVIDIA (tự dùng khi có):** `render` nén bằng `h264_nvenc` (nhanh ~2×, CQ 18 bản cuối / 23 preview), không chạy được thì tự về libx264; ép CPU bằng `--cpu`. `transcribe` chạy whisper trên CUDA (nhanh ~3.4×) — cần `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"`, engine tự nạp DLL; thiếu thì tự về CPU.
