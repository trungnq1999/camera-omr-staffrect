# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_ip14pm/norm`

Thời điểm: 2026-11-12 13:55. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 13.1 [10.3–16.2] | 1 | 45/10/45 | 13.1 |
| audiveris | raw | 192 | 42.3 [38.0–46.8] | 5 | 31/8/62 | 20.8 |
| smt | raw | 192 | 42.0 [37.7–46.6] | 0 | 35/23/42 | 79.6 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 9.0 | 8.5 | 13.4 | 34.7 | 4.9 | 8.0 |
| audiveris | raw | 31.6 | 32.5 | 55.5 | 66.9 | 19.0 | 48.0 |
| smt | raw | 49.4 | 40.7 | 38.6 | 62.1 | 29.1 | 32.4 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
