# Kết quả tiền xử lý: `/mnt/g/doan/minh/oracle_rot`

Thời điểm: 2026-11-11 13:08. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 23.7 [19.1–28.6] | 3 | 34/14/52 | 13.4 |
| homr | rect | 192 | 30.0 [25.2–34.8] | 3 | 29/11/60 | 12.5 |
| homr | norm | 192 | 29.4 [24.4–34.5] | 3 | 30/12/57 | 12.5 |
| audiveris | raw | 192 | 69.8 [65.7–74.2] | 32 | 19/4/77 | 19.5 |
| audiveris | rect | 192 | 61.7 [57.8–65.7] | 14 | 23/4/73 | 17.8 |
| audiveris | norm | 192 | 57.2 [52.2–62.3] | 18 | 22/6/72 | 21.3 |
| audiveris | bin | 192 | 54.7 [49.6–60.0] | 19 | 24/4/71 | 17.0 |
| smt | raw | 192 | 71.4 [66.5–75.9] | 0 | 17/4/79 | 46.9 |
| smt | rect | 192 | 57.1 [51.5–62.2] | 0 | 26/9/65 | 73.2 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 10.5 | 6.3 | 31.4 | 75.4 | 13.0 | 5.7 |
| homr | rect | 55.3 | 14.4 | 25.7 | 67.0 | 11.5 | 6.3 |
| homr | norm | 56.7 | 14.4 | 20.8 | 68.8 | 5.6 | 10.2 |
| audiveris | raw | 41.5 | 69.5 | 70.3 | 98.8 | 38.4 | 100.0 |
| audiveris | rect | 62.1 | 51.7 | 73.0 | 97.0 | 34.9 | 51.7 |
| audiveris | norm | 60.4 | 42.9 | 80.5 | 97.8 | 19.7 | 42.1 |
| audiveris | bin | 57.1 | 31.2 | 76.5 | 97.7 | 14.5 | 51.4 |
| smt | raw | 60.1 | 79.2 | 93.0 | 97.2 | 68.8 | 29.8 |
| smt | rect | 59.7 | 38.0 | 91.3 | 97.6 | 26.4 | 29.9 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | rect | 192 | +6.3 | [+1.8, +11.3] | 41 |
| homr | norm | 192 | +5.7 | [+0.4, +11.0] | 38 |
| audiveris | rect | 192 | -8.0 | [-12.4, -4.3] | 54 |
| audiveris | norm | 192 | -12.5 | [-17.8, -7.8] | 62 |
| audiveris | bin | 192 | -15.0 | [-19.9, -10.4] | 62 |
| smt | rect | 192 | -14.2 | [-19.0, -9.8] | 62 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page | none | quad |
| --- | --- | --- | --- |
| bong | 0 | 8 | 24 |
| den_ban | 0 | 3 | 29 |
| nen_roi | 0 | 32 | 0 |
| nghieng | 0 | 19 | 13 |
| sang | 0 | 0 | 32 |
| scan_app | 32 | 0 | 0 |
