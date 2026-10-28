# Thư viện kiểu chữ

Mỗi mục trong `moments` có `"style"` (preset) và `"lines"`. Preset quy định font, cỡ, màu, vị trí và việc chữ có nằm sau người hay không.
Mọi giá trị đều ghi đè được, ở cấp khoảnh khắc (`y`, `x`, `behind`, `drift`…) hoặc cấp từng dòng (`font`, `w`, `fs`, `color`…).
`w` là bề ngang dòng tính theo tỉ lệ khung (engine tự tính cỡ chữ). `fs` là cỡ cố định.

> **Màu mặc định = VÀNG SÁNG + `halo: "dark"`** (phong cách cố định của kênh, 2026-09-30). Cột "Dòng" bên dưới ghi màu của MẪU GỐC
> tiếng Anh để tham khảo; engine hiện đặt: chữ khóa `gold` / `gold_grad` / `gold_soft`, `neon` = neon vàng, `thin_silver` dòng 2 = vàng phẳng (không âm bản).

> **MẪU CHUẨN (2026-10-07):** dùng thường xuyên chỉ `caps_title`, `caps_big`, `serif_hook`, `thin_silver`, `serif_top_pair`,
> `serif_pair`, `neon`, `strike`, `pills`, `flash`. Các kiểu còn lại chỉ dùng khi người dùng yêu cầu riêng (xem SKILL.md M3).

## Tầng TRÊN: trên đầu / chìm một phần sau đầu (`behind: true`, y ~0.18–0.28, giữa khung — mép trên an toàn 0.15)
| Style | Dòng | Dùng khi | Ví dụ mẫu |
|---|---|---|---|
| `serif_hook` | 1 dòng serif in hoa, tím `violet`, w 0.62 | hook mở đầu, lời mời gọi | LET ME |
| `caps_title` | 1 dòng Inter ExtraBold in hoa `plum`, w 0.78, bật lên (pop) | chủ đề, danh từ chính | YOUR PROPERTY |
| `neon` | ExtraBold in hoa, gradient hồng → xanh + quầng sáng, tắt chậm | con số, thành tích | TOP 1% |
| `strike` | ExtraBold trắng + **vạch đỏ quét** trái → phải, rút đi cuối cảnh | phủ định, "không phải", "đừng" | IS NOT |
| `caps_big` | 1 từ ExtraBold trắng rất to, pop | từ nối gây bước ngoặt: NHƯNG, VÌ, VẬY | BUT |
| `thin_silver` | Light nhỏ + ExtraBold in hoa **bạc kim loại** (gradient dọc) | khái niệm nặng ký | and that / INVESTMENT |
| `serif_top_pair` | serif trắng + italic `lilac_grad` | câu cảm xúc, lời cảm ơn | I would be / honored |
| `serif_dark` | italic `ink` (đen), không bóng | nền phía sau đầu là **tường sáng** | than what's |
| `caps_invert` | Inter Black in hoa **âm bản** cảnh phía sau, pop | tiêu đề trên nền rối/sáng (lá, trời): chữ tự tương phản | INVESTMENT |

**Hiệu ứng trong chữ** gắn cho từng dòng bằng `"fill"`:
- `"invert"`: âm bản cảnh phía sau, chạy theo hình. Có sẵn trong `thin_silver` (dòng 2) và `caps_invert`.
- `"liquid"`: vân nước/kim loại chảy trên nền màu của dòng. Có sẵn trong `serif_pair`, `thin_caps`, `gradient_serif`, `caps_italic`,
  `serif_color`, `serif_top_pair` (dòng khóa). Muốn tắt thì đặt `"fill": null`. Chỉnh tần số/tốc độ/độ tương phản trong `LIQUID` của engine.
- Chữ in hoa dùng font `black` (Inter Black 900). Mọi dòng có bóng gọn mặc định (`SHADOW_OFF`, `SHADOW_BLUR`, `SHADOW_ALPHA`).

## Tầng GIỮA: ngực (y 0.47–0.53, ẩn sub)
| Style | Dòng | Dùng khi | Ví dụ mẫu |
|---|---|---|---|
| `serif_pair` | serif trắng + italic `teal_grad` to hơn, 2 dòng chồng nhẹ | câu có 1 danh từ đắt giá ở cuối | deserves the / investment |
| `thin_caps` | Light nhỏ + ExtraBold in hoa `teal_deep` (gradient dọc) | kết câu bằng 1–2 từ khóa | real estate / AGENT. |
| `thin_bold` | Light + Bold trắng, sát nhau | nhấn nhẹ, câu nói nhanh | be the first / to say, |
| `thin_bold` + `swap` | dòng trên đứng yên, dòng dưới đổi từ theo lời | liệt kê nhanh trong 1 câu | because / far more → goes → into → this, |
| `gradient_serif` | Medium Italic `slate_grad` + italic trắng | câu tự sự, suy ngẫm | something / I take lightly. |
| `serif_italic` | 1 dòng italic trắng | vế câu chuyển tiếp | goes far beyond, |
| `caps_italic` | italic in hoa gradient tím. Có thể thêm từ nhỏ lệch trái (`"dx": -0.27`) | giá trị cốt lõi, 1 từ | IS / TRANSPARENCY. |
| `serif_color` | italic `sky_grad` | từ kết câu, đi kèm `serif_dark` ở tầng trên | visible. |

## Loại đặc biệt (`"type"`)
| type | Mô tả | Dùng khi |
|---|---|---|
| `pills` | chấm tròn bật → kéo dài thành viên thuốc (nền xám đậm, viền vàng `#FFE82A`, chữ Inter Bold trắng), **cộng dồn** tới hết khoảnh khắc. Sub tự ẩn (đứng một mình). | 2–4 giá trị, tiêu chí, phẩm chất |
| `scatter` | từng từ italic nhỏ hiện **cạnh tay đang cử động**, từ sau thay từ trước, mỗi từ có pop nhẹ. Thay cho sub. | liệt kê kênh, dịch vụ, công cụ |
| `image` | logo PNG (nền trong suốt) mờ vào, trôi lên nhẹ, đặt cạnh tay | nhắc tên thương hiệu, nền tảng |
| `flash` | lóe trắng toàn khung 0.45s + riser + hit | cắt cảnh lớn, sau một câu chốt |
| `bubble` | bong bóng chat kính mờ + avatar tròn (PNG tròn hoặc chữ cái) | CTA cuối video |

## Bố cục 3 khuôn (kênh HMT — bắt buộc, xem SKILL.md luật 3)
- Tầng TRÊN = khuôn ① (kèm sub nhỏ bên dưới). Tầng GIỮA = khuôn ② (thay sub). `pills` `neon` `strike` `scatter` = khuôn ③ (đứng một mình).
- Không bao giờ dùng 1 style tầng trên và 1 style tầng giữa cùng lúc — "Gợi ý nhịp" bên dưới là của MẪU GỐC tiếng Anh, chỉ tham khảo thứ tự kiểu chữ.
- Ví dụ đã duyệt: `plan.json` (bản demo nội bộ, không kèm gói) (9 câu hook, 41.6s, 16 điểm nhấn).

## Gợi ý nhịp (video 45s — mẫu gốc, có chồng 2 tầng: KHÔNG áp nguyên cho kênh HMT)
Hook tầng trên + cụm tầng giữa (0–5s) → sub trơn 3–4s → `caps_italic` → `flash` → `neon` → `strike` + `gradient_serif`
→ sub trơn → `thin_silver` + `serif_italic` → `thin_caps` → `image`/`scatter` (liệt kê) → `caps_big` → sub → `thin_bold`+`swap`
→ `serif_dark` + `serif_color` → `pills` → sub → `serif_top_pair` → `bubble`.

## Mẹo chọn chữ khóa (tiếng Việt)
- Chữ khóa ngắn (1–2 từ) thì mới to và đẹp: "SỰ ĐẦU TƯ", "MINH BẠCH", "TOP 1%", "KHÔNG PHẢI".
- Dòng mảnh/đệm giữ nguyên chữ thường: "và khoản", "những gì bạn".
- Tầng trên nên ≤ 12 ký tự để chữ đủ to mà vẫn đúng luật che (người thường ngồi giữa khung).
- Màu: cả video 1 tông VÀNG SÁNG (gold phẳng cho chữ in hoa, gold_grad/gold_soft cho serif italic, neon vàng cho thành tích). Màu khác chỉ khi người dùng yêu cầu riêng.
