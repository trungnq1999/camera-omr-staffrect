# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_x12sp/raw`

Thời điểm: 2026-11-15 21:18. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 43.9 [38.2–49.5] | 11 | 35/5/60 | 11.2 |
| audiveris | raw | 192 | 66.7 [61.5–72.0] | 27 | 16/3/82 | 16.0 |
| smt | raw | 192 | 59.9 [54.5–65.4] | 0 | 45/15/40 | 95.3 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 9.8 | 53.0 | 64.5 | 67.0 | 54.5 | 14.5 |
| audiveris | raw | 28.1 | 93.9 | 87.6 | 86.5 | 72.1 | 31.7 |
| smt | raw | 36.4 | 60.1 | 80.9 | 65.0 | 86.2 | 30.5 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
