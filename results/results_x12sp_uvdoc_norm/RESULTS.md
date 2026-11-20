# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdoc_x12sp/norm`

Thời điểm: 2026-11-19 04:05. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 78.5 [73.5–83.1] | 28 | 44/5/51 | 10.4 |
| audiveris | raw | 192 | 97.5 [95.9–98.9] | 85 | 3/0/97 | 13.3 |
| smt | raw | 192 | 97.2 [93.7–100.8] | 0 | 36/8/56 | 182.6 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 95.1 | 87.9 | 90.4 | 69.7 | 75.7 | 52.5 |
| audiveris | raw | 99.8 | 100.0 | 100.0 | 99.9 | 100.0 | 85.2 |
| smt | raw | 102.7 | 98.7 | 103.8 | 107.6 | 101.9 | 68.7 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
