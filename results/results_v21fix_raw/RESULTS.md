# Kết quả tiền xử lý: `/mnt/g/doan/minh/v2_ip14pm_fix/raw`

Thời điểm: 2026-11-13 00:25. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 9 | 36.1 [4.0–69.7] | 11 | 38/9/53 | 9.6 |
| audiveris | raw | 9 | 80.9 [73.5–90.8] | 22 | 30/6/64 | 16.5 |
| smt | raw | 9 | 45.3 [16.3–76.9] | 0 | 41/22/37 | 33.1 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | den_ban | nen_roi | nghieng | scan_app |
| --- | --- | --- | --- | --- | --- |
| homr | raw | 101.6 | 29.4 | 22.1 | 0.0 |
| audiveris | raw | 86.8 | 79.4 | 77.8 | 91.3 |
| smt | raw | 109.0 | 35.9 | 37.1 | 1.3 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
