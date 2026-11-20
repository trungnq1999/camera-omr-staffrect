# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_ip14pm_fix/norm`

Thời điểm: 2026-11-13 00:39. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 9 | 35.6 [3.7–68.9] | 11 | 42/7/51 | 9.0 |
| audiveris | raw | 9 | 79.3 [67.7–91.7] | 22 | 40/9/51 | 14.6 |
| smt | raw | 9 | 46.2 [13.2–81.0] | 0 | 73/24/3 | 75.0 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | den_ban | nen_roi | nghieng | scan_app |
| --- | --- | --- | --- | --- | --- |
| homr | raw | 100.6 | 28.5 | 22.1 | 0.0 |
| audiveris | raw | 94.2 | 81.1 | 79.8 | 36.2 |
| smt | raw | 112.2 | 38.9 | 34.8 | 1.3 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
