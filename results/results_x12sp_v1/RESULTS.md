# Kết quả tiền xử lý: `/mnt/g/doan/minh/real_photos3`

Thời điểm: 2026-11-15 15:14. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 78.2 [73.1–82.8] | 18 | 44/6/51 | 11.6 |
| homr | rect | 192 | 79.4 [74.0–84.2] | 20 | 37/3/61 | 10.3 |
| homr | norm | 192 | 79.5 [74.0–84.4] | 19 | 39/3/58 | 10.4 |
| homr | bbox | 192 | 76.9 [71.6–81.9] | 18 | 44/4/52 | 11.0 |
| audiveris | raw | 192 | 91.6 [88.2–94.5] | 77 | 8/1/92 | 10.3 |
| audiveris | rect | 192 | 89.9 [86.5–93.0] | 60 | 14/1/85 | 11.7 |
| audiveris | norm | 192 | 87.6 [83.4–91.2] | 60 | 20/1/78 | 15.2 |
| audiveris | bin | 192 | 88.1 [84.1–91.4] | 57 | 22/1/77 | 10.5 |
| audiveris | bbox | 192 | 91.4 [88.0–94.2] | 76 | 10/1/89 | 8.8 |
| smt | raw | 192 | 96.3 [93.0–99.5] | 0 | 25/5/70 | 71.3 |
| smt | rect | 192 | 89.5 [84.9–93.7] | 0 | 33/6/61 | 90.7 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 94.2 | 83.6 | 91.2 | 69.5 | 77.3 | 53.5 |
| homr | rect | 97.5 | 79.0 | 93.4 | 81.3 | 73.3 | 51.9 |
| homr | norm | 97.0 | 78.0 | 94.7 | 81.4 | 73.4 | 52.5 |
| homr | bbox | 96.9 | 77.5 | 90.8 | 67.9 | 76.6 | 51.9 |
| audiveris | raw | 98.3 | 99.8 | 98.9 | 100.0 | 91.3 | 61.4 |
| audiveris | rect | 98.1 | 95.0 | 99.6 | 99.1 | 84.3 | 63.4 |
| audiveris | norm | 98.5 | 82.9 | 99.3 | 98.4 | 84.5 | 61.6 |
| audiveris | bin | 98.1 | 86.8 | 98.8 | 98.8 | 83.2 | 62.7 |
| audiveris | bbox | 97.3 | 99.8 | 99.0 | 100.0 | 92.1 | 60.5 |
| smt | raw | 102.1 | 102.6 | 102.7 | 98.5 | 107.6 | 64.3 |
| smt | rect | 105.9 | 84.3 | 100.8 | 97.1 | 84.3 | 64.8 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | rect | 192 | +1.2 | [-1.7, +4.1] | 44 |
| homr | norm | 192 | +1.3 | [-1.6, +4.1] | 38 |
| homr | bbox | 192 | -1.3 | [-3.6, +1.2] | 38 |
| audiveris | rect | 192 | -1.7 | [-3.5, +0.2] | 34 |
| audiveris | norm | 192 | -4.1 | [-6.8, -1.9] | 30 |
| audiveris | bin | 192 | -3.6 | [-6.1, -1.1] | 36 |
| audiveris | bbox | 192 | -0.2 | [-1.0, +0.7] | 11 |
| smt | rect | 192 | -6.8 | [-10.8, -2.9] | 44 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page | minrect | none | quad |
| --- | --- | --- | --- | --- |
| bong | 0 | 0 | 14 | 18 |
| den_ban | 0 | 0 | 1 | 31 |
| nen_roi | 0 | 1 | 19 | 12 |
| nghieng | 0 | 0 | 14 | 18 |
| sang | 0 | 0 | 4 | 28 |
| scan_app | 32 | 0 | 0 | 0 |
