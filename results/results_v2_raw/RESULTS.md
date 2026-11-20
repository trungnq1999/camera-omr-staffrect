# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_ip14pm/raw`

Thời điểm: 2026-11-12 08:40. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 12.1 [9.5–15.3] | 1 | 43/9/48 | 12.5 |
| audiveris | raw | 192 | 52.0 [48.8–55.6] | 7 | 29/7/64 | 18.1 |
| smt | raw | 192 | 40.8 [36.5–45.2] | 0 | 36/21/43 | 77.1 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 5.3 | 5.1 | 15.5 | 33.8 | 5.3 | 7.7 |
| audiveris | raw | 47.9 | 49.3 | 59.5 | 66.1 | 37.7 | 51.3 |
| smt | raw | 48.6 | 39.8 | 39.6 | 57.9 | 28.3 | 30.9 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
