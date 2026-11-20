# Kết quả tiền xử lý: `/mnt/g/doan/minh/oracle_x12sp_rect`

Thời điểm: 2026-11-16 15:34. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 15.6 [11.3–20.2] | 2 | 37/7/55 | 12.8 |
| homr | norm | 192 | 15.9 [11.6–20.4] | 1 | 37/7/56 | 12.6 |
| audiveris | raw | 192 | 62.4 [57.1–67.9] | 18 | 21/4/76 | 15.7 |
| audiveris | norm | 192 | 42.0 [37.1–47.3] | 8 | 35/9/56 | 19.1 |
| audiveris | bin | 192 | 44.0 [39.2–49.3] | 7 | 40/9/51 | 15.2 |
| smt | raw | 192 | 37.3 [32.3–42.0] | 0 | 34/15/51 | 84.2 |
| smt | norm | 192 | 35.2 [30.7–39.5] | 0 | 38/20/42 | 96.3 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 5.3 | 6.1 | 5.6 | 16.9 | 6.0 | 53.5 |
| homr | norm | 5.4 | 5.1 | 5.2 | 21.5 | 5.6 | 52.5 |
| audiveris | raw | 27.2 | 90.5 | 82.3 | 76.2 | 37.0 | 61.4 |
| audiveris | norm | 16.5 | 44.4 | 45.4 | 63.4 | 20.4 | 61.6 |
| audiveris | bin | 18.4 | 48.3 | 49.3 | 66.6 | 18.6 | 62.7 |
| smt | raw | 35.6 | 26.1 | 30.4 | 41.4 | 25.7 | 64.3 |
| smt | norm | 26.6 | 27.7 | 29.4 | 36.8 | 26.3 | 64.5 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | norm | 192 | +0.3 | [-0.9, +1.9] | 28 |
| audiveris | norm | 192 | -20.5 | [-25.5, -15.9] | 67 |
| audiveris | bin | 192 | -18.4 | [-23.1, -14.1] | 72 |
| smt | norm | 192 | -2.0 | [-4.6, -0.0] | 41 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page |
| --- | --- |
| bong | 32 |
| den_ban | 32 |
| nen_roi | 32 |
| nghieng | 32 |
| sang | 32 |
| scan_app | 32 |
