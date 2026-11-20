# Kết quả tiền xử lý: `/mnt/g/doan/minh/v22_ip14pm/raw`

Thời điểm: 2026-11-17 21:59. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 13.5 [10.5–17.0] | 2 | 40/9/51 | 12.2 |
| audiveris | raw | 192 | 51.8 [48.8–55.5] | 6 | 30/8/62 | 17.7 |
| smt | raw | 192 | 35.0 [30.8–39.1] | 0 | 40/29/31 | 86.4 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 5.2 | 16.2 | 12.7 | 33.2 | 6.9 | 7.0 |
| audiveris | raw | 48.3 | 45.3 | 55.7 | 71.7 | 38.4 | 51.5 |
| smt | raw | 28.0 | 28.0 | 38.3 | 56.5 | 27.2 | 32.1 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
