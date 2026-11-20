# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdoc_x12sp/raw`

Thời điểm: 2026-11-18 17:35. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 79.6 [74.6–83.8] | 28 | 43/5/52 | 10.2 |
| audiveris | raw | 192 | 97.0 [95.3–98.4] | 80 | 4/0/96 | 10.1 |
| smt | raw | 192 | 97.0 [93.3–100.5] | 0 | 36/7/57 | 191.3 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 95.6 | 91.2 | 89.1 | 71.8 | 77.4 | 52.2 |
| audiveris | raw | 99.2 | 99.9 | 99.8 | 99.6 | 99.0 | 84.4 |
| smt | raw | 105.4 | 100.9 | 105.6 | 103.9 | 97.7 | 68.4 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
