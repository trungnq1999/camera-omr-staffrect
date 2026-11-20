# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_x12sp/norm`

Thời điểm: 2026-11-16 03:36. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 44.0 [38.3–49.5] | 11 | 35/7/58 | 11.1 |
| audiveris | raw | 192 | 58.1 [52.5–63.6] | 20 | 26/5/69 | 18.8 |
| smt | raw | 192 | 60.3 [54.7–65.8] | 0 | 41/17/42 | 101.6 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 12.2 | 56.2 | 63.9 | 65.7 | 55.5 | 10.4 |
| audiveris | raw | 21.1 | 68.2 | 73.6 | 78.8 | 76.0 | 31.2 |
| smt | raw | 34.5 | 59.6 | 81.8 | 67.7 | 87.6 | 30.5 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
