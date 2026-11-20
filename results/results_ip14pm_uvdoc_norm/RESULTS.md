# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdoc_ip14pm/norm`

Thời điểm: 2026-11-19 16:42. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 31.5 [25.8–37.3] | 10 | 37/9/54 | 12.2 |
| audiveris | raw | 192 | 75.4 [71.3–79.4] | 28 | 16/3/81 | 17.7 |
| smt | raw | 192 | 52.7 [47.5–58.0] | 0 | 39/10/51 | 93.9 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 37.7 | 39.5 | 14.5 | 43.3 | 41.0 | 12.9 |
| audiveris | raw | 67.8 | 68.0 | 88.9 | 98.5 | 58.3 | 70.8 |
| smt | raw | 57.2 | 57.3 | 67.0 | 57.6 | 50.5 | 26.5 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
