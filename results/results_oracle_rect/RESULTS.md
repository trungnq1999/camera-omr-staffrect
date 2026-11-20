# Kết quả tiền xử lý: `/mnt/g/doan/minh/oracle_rect`

Thời điểm: 2026-11-12 00:42. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 7.1 [5.7–8.8] | 1 | 41/11/48 | 13.3 |
| homr | norm | 192 | 10.2 [7.5–13.3] | 3 | 36/12/51 | 13.1 |
| audiveris | raw | 192 | 55.3 [51.1–59.4] | 22 | 21/6/73 | 17.5 |
| audiveris | norm | 192 | 38.5 [34.7–42.3] | 5 | 33/10/58 | 23.9 |
| audiveris | bin | 192 | 34.9 [30.9–39.2] | 5 | 36/8/56 | 16.2 |
| smt | raw | 192 | 29.7 [25.8–33.3] | 0 | 35/17/47 | 87.2 |
| smt | norm | 192 | 28.6 [24.9–32.2] | 0 | 37/20/43 | 86.8 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 5.0 | 6.5 | 5.8 | 14.5 | 5.1 | 5.7 |
| homr | norm | 9.2 | 6.6 | 8.6 | 16.8 | 9.7 | 10.2 |
| audiveris | raw | 47.0 | 45.5 | 52.0 | 52.0 | 35.2 | 100.0 |
| audiveris | norm | 35.6 | 31.3 | 52.9 | 51.7 | 17.5 | 42.1 |
| audiveris | bin | 21.6 | 21.9 | 56.6 | 44.3 | 13.6 | 51.4 |
| smt | raw | 30.1 | 26.2 | 25.5 | 40.1 | 26.5 | 29.8 |
| smt | norm | 30.9 | 27.4 | 25.7 | 34.6 | 25.9 | 27.1 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | norm | 192 | +3.1 | [+0.9, +5.6] | 31 |
| audiveris | norm | 192 | -16.8 | [-21.4, -12.1] | 76 |
| audiveris | bin | 192 | -20.4 | [-24.5, -16.4] | 82 |
| smt | norm | 192 | -1.1 | [-2.6, +0.2] | 44 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page |
| --- | --- |
| bong | 32 |
| den_ban | 32 |
| nen_roi | 32 |
| nghieng | 32 |
| sang | 32 |
| scan_app | 32 |
