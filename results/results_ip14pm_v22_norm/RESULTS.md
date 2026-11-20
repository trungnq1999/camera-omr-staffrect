# Kết quả tiền xử lý: `/mnt/g/doan/minh/v22_ip14pm/norm`

Thời điểm: 2026-11-18 03:46. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 13.6 [10.6–17.2] | 1 | 44/9/47 | 12.2 |
| audiveris | raw | 192 | 41.7 [37.5–46.1] | 6 | 32/7/61 | 20.5 |
| smt | raw | 192 | 35.9 [31.7–40.3] | 0 | 40/33/28 | 90.5 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 8.5 | 10.5 | 12.7 | 37.5 | 5.3 | 7.1 |
| audiveris | raw | 29.5 | 33.3 | 56.5 | 71.5 | 16.1 | 43.1 |
| smt | raw | 28.6 | 27.8 | 37.8 | 58.5 | 29.7 | 32.9 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
