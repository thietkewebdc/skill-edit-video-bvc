# Cấu trúc cut.json + cách chọn đoạn cắt

```jsonc
{
  "words": "src_words.json",          // sub của video GỐC (đã sửa chính tả), tương đối so với cut.json
  "drop_chunks": [5],                  // bỏ cả câu (số # trong chunks.txt)
  "drop_ranges": [                     // bỏ khúc giữa câu, thời gian NGUỒN (giây)
    [14.94, 16.64],                    //   từ ĐẦU từ bị bỏ đầu tiên → ĐẦU từ được giữ tiếp theo
    [26.22, 37.12]
  ],
  "trim": {"7": [170.18, 206.55]},     // bó câu #7 còn [s, e] (VD bỏ vỗ tay cuối video)
  "keep_ranges": [[36.2, 126.75]],     // tùy chọn: CHỈ giữ phần nằm trong các vùng này (mốc nguồn) — bền khi
                                       //   chạy lại analyze làm đổi số thứ tự câu; dùng thay drop_chunks
  "_notes": {"14.94-16.64": "nói vấp → giữ lần sau"}   // lý do từng chỗ cắt (để người dùng duyệt)
}
```

## Mép cắt theo CHỮ (khuyến nghị — `cut_qa.py wordsnap` ghi ra keep_ranges / drop_ranges)
```jsonc
{
  "keep_words":  [["cái", 193.4, "thu", 235.8],      // giữ từ TRƯỚC chữ "cái"@~193.4 đến SAU chữ "thu"@~235.8
                  [478.58, 478.58, "hơn", 491.2]],   // số = mốc đã nghe thử bằng `try`, dùng thẳng
  "drop_words":  [["và", 282.38, "20", 284.52]],     // bỏ từ trước "và" đến trước "20"
  "pause_words": [["80.000", 371.4, "90.000", 372.8]], // bỏ chỗ ngừng giữa 2 chữ
  "trim": {"18": [303.82, 310.42]}                   // do `cut_qa.py lost --fix` ghi: nới câu để nhập tiếng bị bỏ sót
}
```
- Mốc giây chỉ để tìm đúng lần xuất hiện của chữ; mép thật do năng lượng âm quyết định (khoảng lặng sát chữ, mốc chữ từ `med_words.json`).
- `wordsnap` báo `!!` = không có khoảng lặng → nghe thử bằng `cut_qa.py try` trước khi dùng.
- Bỏ vấp mà 2 lần nói dính liền (không lặng) → KHÔNG ghi `drop_words` (sẽ cụt tiếng); giữ nguyên, ghi `_notes`.

## Engine tự làm
- Câu = đoạn nói giữa 2 khoảng lặng > 0.6s (đo năng lượng âm thanh, ngưỡng thích nghi từng video).
- Mọi khoảng lặng giữa 2 câu giữ lại → cắt, còn 0.1s + 0.1s = **0.2s**.
- Mốc `drop_ranges` tự bám điểm âm thấp nhất ±0.15s; phần lặng dính ở mép cắt được bó lại, mép chỉ đệm bằng phần lặng vừa bỏ (không lẹm chữ bị cắt).
- Đoạn < 2s → gộp với đoạn kề liền mạch (giữ nguyên khoảng lặng giữa chúng).
- Đoạn lẻ 100%, đoạn chẵn 150% (đếm sau khi gộp).
- Sub `words.json` cho video đã cắt được dời mốc tự động.

## Chọn đoạn cắt (người biên tập quyết)
| Loại | Dấu hiệu trong transcript | Làm gì |
|---|---|---|
| Nói vấp | "có những kiến thức, học tập có học tập được những kiến thức" | bỏ khúc đầu, giữ lần nói trọn |
| Lặp ý / nói lại câu | 2 câu cùng mở đầu "lúc đầu tôi chỉ nhận ra một điều…" | bỏ lần TRƯỚC, giữ lần SAU |
| Cụm vô nghĩa / không nghe ra | "và đều có ráng thị trắng" | bỏ |
| Ý nhắc lại xa nhau | cùng kết luận ở 47s và 83s | bỏ lần trước nếu câu vẫn nối mạch |
| Ồn, vỗ tay, im lặng cuối | năng lượng cao sau câu chào cuối | `trim` câu cuối |

Không cắt từ đệm nhỏ ("thì", "tôi mình") nếu mỗi mối cắt tạo đoạn < 2s hoặc làm câu giật — ưu tiên mạch nói tự nhiên.

Sau `plan`: kiểm tra chữ ĐẦU và CUỐI mỗi đoạn trong `words.json` mới — thấy từ lẻ (VD "nhưng" ở cuối đoạn) → dời mốc `drop_ranges`.
