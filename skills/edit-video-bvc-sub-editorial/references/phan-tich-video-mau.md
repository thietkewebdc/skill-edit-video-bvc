# Phân tích video mẫu — "Your home deserves an agent who invests in it…"

Video dọc 1080×1920, 30 fps, dài 44 s. Một người nói tiếng Anh trước ống kính, quay ở 5 góc trong một căn nhà mẫu.
Không có nhạc nền. Phân tích từng khung ở 10 fps, đo màu bằng giá trị điểm ảnh, đo âm bằng phổ tần số.

## 1. Tinh thần chung
- **Kiểu tạp chí thời trang / bất động sản cao cấp.** Không viền chữ, không hộp nền, không chữ khối. Chữ nhìn như được in lên cảnh.
- **Hai họ chữ đặt cạnh nhau:** serif cao gầy (kiểu Didone, nét thanh nét đậm) và sans kiểu Helvetica (mảnh hoặc rất đậm).
  Một cụm luôn có **chữ đệm mảnh/nhỏ** đi với **chữ khóa to/đậm/màu**.
- **Mật độ dày:** 23 điểm nhấn trong 44 s, tức khoảng **1 điểm nhấn mỗi 1.9–2.2 s**. Chỉ có 4 quãng ngắn (2.5–5 s) là sub trơn.
- **Chữ hiện từng từ đúng lúc nói**, bằng blur-in (mờ → nét, khoảng 4–6 khung).
- **Chữ ở tầng trên nằm SAU người:** đầu và tóc che một phần chữ, tạo chiều sâu 3D. Đây là dấu ấn mạnh nhất của mẫu.

## 2. Ba tầng vị trí
| Tầng | Vị trí dọc | Nội dung | Ví dụ |
|---|---|---|---|
| **Trên (sau đầu)** | 20–31% chiều cao | tiêu đề to, chữ khóa, luôn nằm SAU người | LET ME, YOUR PROPERTY, TOP 1%, IS NOT, INVESTMENT, BUT, I would be / honored |
| **Giữa (ngực)** | 47–53% | sub từng cụm + cụm nhấn serif/italic | stand by, deserves the / investment, something / I take lightly, visible. |
| **Tự do (quanh tay)** | 40–55%, lệch trái/phải | chữ rải theo cử chỉ tay, logo, badge | retargeting · ads · maximum · exposure, Zillow, Homes.com, Character / Integrity / HOW |

Tầng trên và tầng giữa thường **hiện cùng lúc** (VD: `YOUR PROPERTY` ở trên + `deserves the / investment` ở giữa) → câu được "dàn trang" như bìa tạp chí.

## 3. Font chữ (nhận dạng + font thay thế đã đóng gói)
| Vai trò trong mẫu | Font mẫu (ước đoán) | Font trong skill (OFL, có tiếng Việt) |
|---|---|---|
| Serif đứng cao gầy (LET ME, deserves the, I would be) | Didone condensed, kiểu Editorial New / Instrument Serif | **Playfair Display Regular**, ép ngang 82% |
| Serif nghiêng (investment, goes far beyond, visible., honored) | Didone italic | **Playfair Display Italic**, ép 86% |
| Serif nghiêng đậm vừa (something) | Didone medium italic | **Playfair Display Medium Italic** |
| Sans mảnh (sub, "and that", "from your") | Helvetica Neue Light | **Inter Light** |
| Sans đậm (to say, far more, one,) | Helvetica Neue Bold | **Inter Bold** |
| Sans rất đậm in hoa (YOUR PROPERTY, IS NOT, BUT, TOP 1%, AGENT.) | Helvetica Neue Heavy | **Inter ExtraBold** |
| Badge + CTA | SF Pro / Inter | **Inter Bold / Inter Light** |

## 4. Bảng màu (đo từ điểm ảnh)
| Tên trong skill | Mã | Dùng ở |
|---|---|---|
| `violet` | #7B51AF → #68297A | LET ME |
| `plum` | #662676 | YOUR PROPERTY |
| `purple_grad` | #5A2A90 → #A57DD8 | TRANSPARENCY. |
| `lilac_grad` | #8A56B6 → #C39BEB | honored, you |
| `teal_grad` | #2E8FB0 → #6CC3D6 | investment (italic) |
| `teal_deep` (dọc) | #7CC4D2 → #0B5577 | AGENT., CAN SEE. |
| `sky_grad` | #2299C4 → #6CC9EA | visible. |
| `slate_grad` | #3C4652 → #7EBAD0 | something |
| `silver` (dọc) | #F6F6F6 → #8D939A | INVESTMENT |
| `neon` + phát sáng | #FF7BFF → #A8FEFF | TOP 1% |
| `ink` | #1E1A1A | than what's (chữ tối trên nền tường sáng) |
| `red` | #FA2000 | vạch gạch IS NOT |
| `yellow` | #FFE82A | viền badge |
| trắng | #FFFFFF | sub + chữ đệm |

Nguyên tắc: **1 cặp màu chủ đạo (tím + xanh ngọc)**, chữ trắng là nền. Gradient luôn nhẹ, 2 tông cùng họ màu. Đỏ và vàng chỉ dùng cho **đồ họa** (vạch gạch, viền badge), không dùng cho chữ.

## 5. Mười lăm kiểu chữ (theo mốc thời gian)
| # | Mốc | Kiểu | Mô tả |
|---|---|---|---|
| 1 | 0.0 | **serif_hook** | `LET` → `ME` hiện theo lời nói, serif tím cỡ rất to, sau đầu |
| 2 | 0.6 | **thin_bold** | `be the first` (mảnh) / `to say,` (đậm), 2 dòng sát nhau ở ngực |
| 3 | 1.7 | **caps_title** | `YOUR PROPERTY` in hoa đậm màu mận, bật từ nhỏ lên, sau đầu |
| 4 | 2.3 | **serif_pair** | `deserves the` (serif trắng) / `investment` (italic xanh ngọc) chồng nhẹ lên nhau |
| 5 | 3.3 | **thin_caps** | `real estate` (mảnh) / `AGENT.` (đậm, gradient xanh dọc) |
| 6 | 9.5 | **caps_italic** | `IS` nhỏ lệch trái + `TRANSPARENCY.` italic in hoa gradient tím |
| 7 | 10.8 | **flash** | lóe trắng toàn khung để chuyển cảnh (kèm riser + hit) |
| 8 | 11.3 | **neon** | `TOP 1%` hồng → xanh, có quầng sáng, sau đầu, tắt chậm |
| 9 | 13.0 | **strike** | `IS NOT` trắng đậm + **vạch đỏ quét trái → phải**, cuối cảnh vạch rút đi |
| 10 | 13.6 | **gradient_serif** | `something` (italic gradient xám-xanh) / `I take lightly.` (italic trắng) |
| 11 | 17.7 | **thin_silver** | `and that` (mảnh) / `INVESTMENT` (đậm, bạc kim loại) sau đầu |
| 12 | 21–25 | **image + scatter** | logo Zillow / Homes.com bật cạnh tay; `retargeting · ads · maximum · exposure,` italic nhỏ rải quanh 2 tay |
| 13 | 25.5 | **caps_big** | `BUT` trắng đậm rất to sau đầu, bật lên |
| 14 | 30.0 | **thin_bold + swap** | `because` giữ nguyên, dòng dưới đổi dần `far more → goes → into → this,` |
| 15 | 31.6 | **serif_dark + serif_color** | `than what's` (italic đen, tầng trên) + `visible.` (italic xanh, ngực) |
| 16 | 33–35 | **pills** | chấm tròn bật ra → kéo dài thành viên thuốc viền vàng: `Character`, `Integrity`, `HOW`, cộng dồn |
| 17 | 38.4 | **serif_top_pair** | `I would be` (serif trắng) / `honored` (italic tím) |
| 18 | 42.8 | **bubble** | bong bóng chat kính mờ + avatar tròn: "Click the link in my bio." |

## 6. Chuyển động
- **Vào:** blur-in khoảng 0.15–0.2 s, độ mờ ban đầu rất lớn; chữ in hoa đậm thì **bật từ ~85% lên 100%** (pop). Không trượt từ ngoài vào, không nảy.
- **Trong lúc giữ:** chữ **phóng to chậm 2–6%**, như trôi theo máy quay, nên không lúc nào đứng im hẳn.
- **Ra:** blur-out + mờ dần 0.2 s. `TOP 1%` tắt chậm khoảng 0.5 s. Không có hiệu ứng bay ra.
- **Theo từng từ:** mỗi từ hiện đúng mốc nói (LET 0.0 s → ME 0.36 s). Dòng đã hiện thì giữ nguyên chỗ, bố cục không nhảy.
- **Đổi từ (swap):** dòng trên giữ, dòng dưới blur-out/blur-in thay từ mới.
- **Badge:** chấm tròn 0 → 100% (0.15 s) → kéo ngang thành viên thuốc (0.15 s) → chữ blur-in.
- **Vạch gạch:** quét trái → phải khoảng 0.35 s, sau đó rút từ trái sang phải trước khi hết cảnh.
- **Sub:** mỗi lần 1–2 từ (tối đa ~14 ký tự), đổi cụm bằng blur nhanh khoảng 0.1 s.

## 6b. Hiệu ứng trong chữ + bóng + độ mập (bổ sung 2026-09-29, chủ kênh chỉ ra)
- **Âm bản chạy trong chữ** (`fill: invert`): "INVESTMENT" hiển thị âm bản của chính cảnh phía sau. Phần chữ trên tủ hút mùi nâu tối thì
  sáng xanh nhạt, phần trên tường sáng thì xám đậm. Máy quay và người chuyển động nên phần âm bản trong chữ cũng chạy.
  Chữ luôn tự tương phản với nền, rất hợp với nền rối hoặc nền sáng.
- **Vân chảy trong chữ** (`fill: liquid`): "investment", "visible.", "CAN SEE.", "TRANSPARENCY.", "something" được lấp bằng
  vân nước/kim loại lỏng. Nền màu (xanh ngọc/tím) có các **vệt sáng mảnh, sắc, gợn sóng** dịch chuyển liên tục qua từng khung.
- **Bóng gọn:** "I take lightly.", "BUT", "IS": bóng đen lệch chéo phải-dưới khoảng 3–5% em, nhòe rất ít, đậm khoảng 55%.
  Bóng làm chữ nổi khối mà không lan ra.
- **Chữ mập:** in hoa dùng Helvetica Black (skill dùng Inter Black 900), bản rất to: BUT khoảng 45–60% khung, INVESTMENT khoảng 80%.

## 7. Sub thường
Inter/Helvetica Light, trắng, cỡ khoảng 62 (hệ 1080), ở 49% chiều cao (ngang ngực), **bóng đen rất mềm** (không viền). Từ quan trọng
(`one,` `but` `to say,` `you,`) chuyển sang **đậm**. Khi có cụm nhấn ở tầng giữa thì **ẩn sub**. Chữ ở tầng trên không làm ẩn sub.

## 8. Âm thanh (SFX)
Phổ tần cho thấy **không có nhạc nền**, giọng nói chiếm trọn. SFX rất nhỏ, gần như chỉ cảm thấy chứ không nghe rõ:
| Mốc | Âm | Gắn với |
|---|---|---|
| 1.6–4.2 s | **sub-boom** trầm (< 100 Hz) nở dần | hook mở đầu (YOUR PROPERTY / investment) |
| 2.9 · 4.3 s | **air**: whoosh hơi, rất ngắn | chữ khóa ở ngực (investment, AGENT.) |
| 8.3–10.8 s | **riser** có tiếng chuông cao 3.7/7 kHz | dồn vào flash trắng |
| 10.72 s | **hit** + lóe sáng | chuyển cảnh flash |
| 13.08 s | **swipe** (tiếng quét) | vạch gạch đỏ IS NOT |
| 21.2 · 22.2 s | **pop** | logo Zillow, Homes.com |
| 23.2–24.9 s | **pop nhẹ** từng cái | chữ rải quanh tay |
| 29.6 · 37.2 s | **shimmer/riser** ngắn | trước cắt cảnh |
| 40.7 · 42.7 s | **boom nhẹ + pop** | cảnh cuối, CTA bubble |
Sub thường **không có SFX**.

## 9. Công thức rút ra
1. Mỗi câu chọn **1 từ khóa** → cho nó serif italic màu, sans in hoa đậm, hoặc gradient. Các từ còn lại mảnh/nhỏ.
2. Tầng trên đặt **sau đầu**, cỡ lớn, để người che 1–2 chữ cái.
3. Cứ khoảng 2 s có 1 cụm trang trí. Đổi kiểu liên tục, không lặp một kiểu 2 lần liền.
4. Chữ hiện **đúng từng từ nói**, dùng blur-in, giữ bằng drift chậm, ra bằng blur-out.
5. Liệt kê (tên thương hiệu, dịch vụ) → logo và chữ rải quanh tay. Nhóm giá trị → badge viên thuốc cộng dồn. Phủ định → vạch gạch đỏ.
6. Chuyển cảnh lớn dùng flash trắng. Kết thúc bằng CTA bong bóng chat.
7. Âm thanh tối giản: không nhạc, SFX nhỏ, chỉ đặt ở chuyển cảnh và đồ họa.
