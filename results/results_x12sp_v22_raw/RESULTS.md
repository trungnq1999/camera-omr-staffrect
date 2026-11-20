# Kết quả tiền xử lý: `/mnt/g/doan/minh/v22_x12sp/raw`

Thời điểm: 2026-11-17 10:20. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 13.8 [10.8–17.0] | 1 | 49/10/41 | 12.5 |
| audiveris | raw | 192 | 57.7 [52.0–62.8] | 17 | 19/4/77 | 17.9 |
| smt | raw | 192 | 49.1 [44.4–54.4] | 0 | 31/19/49 | 88.7 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 7.8 | 16.3 | 10.6 | 27.6 | 9.3 | 11.3 |
| audiveris | raw | 26.2 | 90.6 | 77.6 | 75.3 | 45.7 | 30.5 |
| smt | raw | 34.4 | 69.7 | 33.9 | 53.3 | 72.9 | 30.6 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
