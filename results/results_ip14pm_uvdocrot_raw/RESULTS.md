# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdocrot_ip14pm/raw`

Thời điểm: 2026-11-19 19:01. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 12.5 [9.6–16.2] | 2 | 33/15/52 | 13.0 |
| audiveris | raw | 192 | 69.4 [65.7–73.3] | 16 | 20/2/78 | 16.2 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 4.9 | 6.1 | 6.8 | 42.0 | 4.9 | 10.0 |
| audiveris | raw | 60.6 | 53.4 | 86.1 | 98.0 | 47.8 | 70.4 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
