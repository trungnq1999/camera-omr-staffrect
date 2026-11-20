# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdoc_ip14pm/raw`

Thời điểm: 2026-11-19 10:47. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 30.1 [24.2–36.1] | 11 | 37/9/54 | 12.2 |
| audiveris | raw | 192 | 77.0 [73.6–80.6] | 26 | 18/1/81 | 15.1 |
| smt | raw | 192 | 53.8 [48.1–59.1] | 0 | 41/11/47 | 104.9 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 37.5 | 40.7 | 10.2 | 42.0 | 40.2 | 10.0 |
| audiveris | raw | 70.9 | 69.5 | 86.1 | 98.0 | 67.0 | 70.4 |
| smt | raw | 58.0 | 55.6 | 64.0 | 64.3 | 54.5 | 26.5 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
