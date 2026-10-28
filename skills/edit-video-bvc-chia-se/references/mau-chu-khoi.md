# Mẫu chữ khối (tiêu đề + chữ nhấn)

Phân tích từ 2 thumbnail mẫu của kênh: "QUY TẮC / 90/10" (trắng–vàng) và "GẶP NHAU TẠI / CYPRUS" (trắng–xanh).

```
        QUY TẮC           ← dòng trắng: nhỏ (~60% dòng màu), IN HOA
       90/10              ← dòng màu: to nhất khung, IN HOA
  (bóng đen đặc đổ chéo xuống phải; 2 dòng gần chạm nhau)
```

## Thông số (đã khóa trong engine)
| Thuộc tính | Giá trị |
|---|---|
| Font | Montserrat Black, IN HOA toàn bộ |
| Dòng màu | bản to: cỡ tối đa để rộng ≤ 84% khung (tiêu đề tối đa fs 350 ≈ chữ hoa cao 8% khung như mẫu, chữ nhấn 330) |
| Dòng trắng | **CÂN BẰNG**: tự co giãn cỡ chữ để **rộng bằng dòng màu** → khối chữ vuông như mẫu (QUY TẮC rộng = 90/10; GẶP NHAU TẠI rộng = CYPRUS). Không bao giờ to quá 85% cỡ dòng màu |
| Khoảng dòng | **sát**: hở ≈ 15% chiều cao chữ hoa dòng dưới (`LINE_GAP = 0.40`); tự cộng thêm vừa đủ khi dòng dưới có dấu phía trên (Ổ, Ấ, Ờ…) để dấu không chạm dòng trên |
| Viền | **tiêu đề / chữ nhấn / số đếm: KHÔNG viền**. Sub + nhãn nhỏ: viền đen thật mỏng 0.9% cỡ chữ |
| Bóng | tiêu đề / chữ nhấn: đen 85%, **đổ sát chữ** x = y ≈ 1.6% cỡ chữ. Sub + nhãn: đen 75%, lệch 2.2% |
| Hộp nền | không có |
| Số lớp | **1 lớp duy nhất** cho mỗi dòng chữ: viền + bóng render trong cùng event (`\bord \xshad \yshad`), không có lớp bóng/tia sáng riêng chồng lên |
| File phụ đề | **không bao giờ** xuất `.ass` cạnh video (trình phát sẽ tự mở và vẽ chữ lần 2 đè lên) |
| Mờ dần | **không dùng** (chữ bán trong suốt sẽ lộ bóng bên dưới → trông như chồng đôi). Vào: đập/phóng/trượt/lộ; ra: cắt gọn |
| Vị trí | tâm khối ở 58.5% chiều cao (khoảng 47–70% như mẫu) |
| Màu | trắng `#FFFFFF` + vàng `#F4C80F` **hoặc** trắng + xanh cyan `#00FFFF`. Tiêu đề **luôn 1 dòng trắng + 1 dòng màu**: trắng trên–màu dưới, hoặc màu trên–trắng dưới (`"{3 PHONG THỦY}|QUÝ GIÁ"`) khi dòng trên đè nền sáng. Không phối xanh + vàng. Sub (từ đang nói), chữ nhấn, minh họa theo cùng màu của tiêu đề. |

## Đo bề rộng
Engine đọc trực tiếp bảng độ rộng ký tự trong file Montserrat-Black.ttf (hệ số libass 1.562) nên cân bằng 2 dòng chính xác tới từng pixel.

## Viết chữ theo mẫu
- Cú pháp: `"DÒNG TRẮNG|{DÒNG MÀU}"`. Không có `|` thì engine tự tách theo ranh giới màu: `"CÓ MẶT {THỰC SỰ}"` → 2 dòng.
- Dòng màu là **từ khóa / con số / địa danh** — thứ người xem nhớ. Dòng trắng là ngữ cảnh ngắn.
- Tiêu đề: tổng **2–6 từ**. Dòng màu **1–2 từ ngắn** (≤ 10 ký tự) để chữ bản to như `90/10`, `CYPRUS`.
- Được đảo thứ tự (màu trên, trắng dưới) khi câu tự nhiên hơn: `"{90%}|THỜI GIAN BÊN CON"`.
- 1 dòng duy nhất cũng được (`"{KHÔNG!}"`) — toàn bộ là dòng màu.

## Chọn cặp màu cho từng video
| Chọn `yellow` (trắng–vàng) khi | Chọn `cyan` (trắng–xanh) khi |
|---|---|
| nội dung về tiền, quy tắc, thành công, bài học, cảm xúc ấm | du lịch, địa điểm, công nghệ, tương lai, sự kiện |
| hình tông xanh lá, xanh dương, tối | hình tông nóng (nắng vàng, đất, gạch cam, đá) |
| mặc định khi phân vân | khi nền có nhiều mảng vàng làm chữ vàng chìm |

Một video chỉ dùng **một** cặp màu từ đầu tới cuối (tiêu đề, chữ nhấn, minh họa đều theo).

## Tiêu đề
- Hiện **đầy đủ ngay frame 0** (cũng là thumbnail) → không có hiệu ứng vào.
- Trong lúc hiện: **đứng yên hoàn toàn** — không tia sáng, không vệt sáng, không phóng to. SFX: impact nhẹ ở 0s.
- Ra: cắt gọn đúng mốc `end`, kèm whoosh.
- Dài 5–10s, kết thúc đúng lúc hết câu mở đầu. Sub ẩn trong suốt thời gian này.
