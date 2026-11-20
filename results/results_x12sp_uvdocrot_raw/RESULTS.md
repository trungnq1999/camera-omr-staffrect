# Kết quả tiền xử lý: `/mnt/g/doan/minh/uvdocrot_x12sp/raw`

Thời điểm: 2026-11-19 17:46. Ảnh chụp thật.

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 192 | 40.3 [35.2–45.8] | 5 | 40/10/50 | 12.0 |
| audiveris | raw | 192 | 94.1 [92.1–96.1] | 67 | 5/1/94 | 12.0 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 10.3 | 63.7 | 53.4 | 72.6 | 34.1 | 7.9 |
| audiveris | raw | 88.5 | 99.9 | 100.0 | 99.6 | 98.5 | 78.0 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
