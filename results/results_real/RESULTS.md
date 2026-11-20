# Kết quả tiền xử lý: `/mnt/g/doan/minh/real_photos2`

Thời điểm: 2026-11-09 22:58. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 40.9 [34.9–47.4] | 9 | 36/9/54 | 12.3 |
| homr | rect | 192 | 42.8 [36.6–48.8] | 8 | 31/8/61 | 11.8 |
| homr | norm | 192 | 42.4 [36.0–48.3] | 7 | 33/9/59 | 11.8 |
| homr | bbox | 192 | 44.7 [38.9–51.0] | 8 | 33/8/58 | 11.8 |
| audiveris | raw | 192 | 77.9 [74.1–82.0] | 42 | 18/2/80 | 18.1 |
| audiveris | rect | 192 | 70.2 [66.3–74.3] | 25 | 21/3/76 | 16.5 |
| audiveris | norm | 192 | 68.5 [63.5–73.0] | 29 | 21/5/75 | 19.7 |
| audiveris | bin | 192 | 66.8 [61.7–71.9] | 30 | 23/3/74 | 15.7 |
| audiveris | bbox | 192 | 81.0 [77.3–84.6] | 44 | 15/2/83 | 17.0 |
| smt | raw | 192 | 75.7 [71.1–80.0] | 0 | 21/4/76 | 48.3 |
| smt | rect | 192 | 65.7 [60.4–70.7] | 0 | 29/5/66 | 66.6 |
| smt | norm | 192 | 66.9 [61.5–72.3] | 0 | 29/8/63 | 75.0 |
| smt | bbox | 192 | 70.4 [65.2–75.5] | 0 | 28/7/66 | 67.4 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 40.8 | 40.3 | 34.9 | 75.4 | 48.3 | 5.7 |
| homr | rect | 68.9 | 41.0 | 29.2 | 67.0 | 44.6 | 6.3 |
| homr | norm | 70.3 | 41.2 | 23.9 | 68.8 | 39.7 | 10.2 |
| homr | bbox | 61.1 | 43.4 | 34.8 | 75.4 | 44.5 | 9.0 |
| audiveris | raw | 60.7 | 78.2 | 72.2 | 98.8 | 57.6 | 100.0 |
| audiveris | rect | 74.6 | 67.4 | 74.5 | 97.0 | 55.7 | 51.7 |
| audiveris | norm | 76.3 | 65.3 | 80.4 | 97.8 | 49.4 | 42.1 |
| audiveris | bin | 74.6 | 53.6 | 78.2 | 97.7 | 45.3 | 51.4 |
| audiveris | bbox | 76.4 | 78.5 | 75.1 | 98.7 | 57.5 | 100.0 |
| smt | raw | 73.8 | 84.1 | 93.6 | 97.2 | 75.5 | 29.8 |
| smt | rect | 69.8 | 57.4 | 91.9 | 97.6 | 47.6 | 29.9 |
| smt | norm | 71.0 | 61.1 | 92.8 | 98.3 | 51.1 | 27.1 |
| smt | bbox | 70.5 | 78.0 | 93.7 | 94.8 | 55.3 | 30.0 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | rect | 192 | +1.9 | [-2.1, +6.0] | 43 |
| homr | norm | 192 | +1.5 | [-3.3, +6.2] | 42 |
| homr | bbox | 192 | +3.8 | [+1.1, +6.5] | 27 |
| audiveris | rect | 192 | -7.8 | [-11.8, -4.4] | 46 |
| audiveris | norm | 192 | -9.4 | [-14.1, -5.0] | 50 |
| audiveris | bin | 192 | -11.1 | [-15.5, -7.0] | 51 |
| audiveris | bbox | 192 | +3.1 | [+1.5, +5.0] | 15 |
| smt | rect | 192 | -10.0 | [-13.7, -6.3] | 56 |
| smt | norm | 192 | -8.8 | [-12.9, -4.6] | 54 |
| smt | bbox | 192 | -5.3 | [-8.7, -2.1] | 41 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page | none | quad |
| --- | --- | --- | --- |
| bong | 0 | 8 | 24 |
| den_ban | 0 | 3 | 29 |
| nen_roi | 0 | 32 | 0 |
| nghieng | 0 | 19 | 13 |
| sang | 0 | 1 | 31 |
| scan_app | 32 | 0 | 0 |
