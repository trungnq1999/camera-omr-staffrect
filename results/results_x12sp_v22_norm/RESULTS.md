# Kết quả tiền xử lý: `/mnt/g/doan/minh/v22_x12sp/norm`

Thời điểm: 2026-11-17 16:02. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 14.3 [11.2–17.8] | 2 | 48/9/43 | 12.6 |
| audiveris | raw | 192 | 40.4 [35.6–45.3] | 7 | 36/9/55 | 21.4 |
| smt | raw | 192 | 47.8 [43.1–53.0] | 0 | 34/20/46 | 88.0 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 8.9 | 19.6 | 10.8 | 27.9 | 8.2 | 10.1 |
| audiveris | raw | 19.6 | 56.8 | 42.9 | 63.6 | 28.0 | 31.6 |
| smt | raw | 33.9 | 64.6 | 34.2 | 54.5 | 69.1 | 30.2 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
