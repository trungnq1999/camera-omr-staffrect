# Kết quả tiền xử lý: `/mnt/g/doan/minh/sim_photos2`

Thời điểm: 2026-11-01 02:26. **DỮ LIỆU MÔ PHỎNG — chỉ dùng để kiểm tra quy trình và chọn tham số, không phải kết quả ảnh thật.**

SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.


## 1. SER theo engine và biến thể tiền xử lý

| Engine | Biến thể | n | SER [95% CI] | Thất bại (%) | Thay/Chèn/Xoá (%) | Thời gian TB (s) |
| --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 256 | 11.5 [9.2–13.8] | 2 | 28/18/54 | 19.8 |
| homr | rect | 256 | 9.4 [7.0–12.1] | 2 | 28/7/65 | 14.1 |
| homr | norm | 256 | 10.2 [7.6–12.8] | 2 | 30/8/62 | 14.0 |
| homr | bbox | 256 | 12.1 [9.2–15.2] | 3 | 26/11/63 | 13.9 |
| audiveris | raw | 256 | 60.3 [54.9–65.5] | 44 | 10/2/88 | 14.1 |
| audiveris | rect | 256 | 46.3 [41.3–51.0] | 20 | 17/3/80 | 15.8 |
| audiveris | norm | 256 | 32.9 [28.8–36.9] | 12 | 28/5/67 | 16.5 |
| audiveris | bin | 256 | 35.2 [31.3–39.1] | 12 | 34/6/60 | 16.1 |
| audiveris | bbox | 256 | 59.8 [54.5–65.1] | 40 | 11/2/87 | 15.0 |
| smt | raw | 32 | 67.0 [56.5–76.9] | 0 | 14/4/82 | 43.0 |
| smt | rect | 32 | 21.4 [17.0–26.4] | 0 | 30/34/36 | 90.8 |
| smt | norm | 32 | 20.7 [16.7–25.1] | 0 | 30/31/40 | 110.8 |
| smt | bbox | 32 | 39.6 [31.2–49.1] | 0 | 24/14/63 | 135.1 |


## 2. SER theo điều kiện chụp

| Engine | Biến thể | bong | den_ban | nen_roi | nghieng | sang | scan_app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| homr | raw | 8.7 | 12.0 | 17.8 | 11.2 | 9.9 | 11.1 |
| homr | rect | 9.8 | 9.3 | 19.2 | 7.4 | 6.7 | 8.4 |
| homr | norm | 13.8 | 9.7 | 15.9 | 9.6 | 8.6 | 6.0 |
| homr | bbox | 11.6 | 12.2 | 13.1 | 18.1 | 6.2 | 11.1 |
| audiveris | raw | 43.5 | 100.0 | 88.8 | 100.0 | 16.5 | 17.1 |
| audiveris | rect | 13.8 | 99.9 | 80.0 | 67.8 | 12.7 | 15.3 |
| audiveris | norm | 15.5 | 92.2 | 28.1 | 40.7 | 15.2 | 15.7 |
| audiveris | bin | 14.6 | 94.1 | 41.9 | 38.0 | 15.0 | 25.1 |
| audiveris | bbox | 42.6 | 100.0 | 88.4 | 98.6 | 16.5 | 17.1 |
| smt | raw | 50.7 | 78.5 | 91.3 | 78.5 | 64.2 | 30.3 |
| smt | rect | 16.6 | 21.0 | 16.6 | 21.0 | 22.7 | 29.8 |
| smt | norm | 15.8 | 23.5 | 17.9 | 22.1 | 19.8 | 24.5 |
| smt | bbox | 22.8 | 36.5 | 43.2 | 65.7 | 26.3 | 30.3 |


## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh

Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.


| Engine | Biến thể | n cặp | Chênh SER (điểm %) | 95% CI | Tốt hơn raw (% ảnh) |
| --- | --- | --- | --- | --- | --- |
| homr | rect | 256 | -2.1 | [-4.7, +0.8] | 41 |
| homr | norm | 256 | -1.3 | [-4.5, +2.0] | 40 |
| homr | bbox | 256 | +0.6 | [-2.3, +3.4] | 34 |
| audiveris | rect | 256 | -14.0 | [-17.2, -11.0] | 59 |
| audiveris | norm | 256 | -27.4 | [-31.9, -22.9] | 65 |
| audiveris | bin | 256 | -25.1 | [-29.5, -20.7] | 60 |
| audiveris | bbox | 256 | -0.5 | [-1.1, +0.1] | 6 |
| smt | rect | 32 | -45.6 | [-56.0, -34.9] | 94 |
| smt | norm | 32 | -46.3 | [-55.7, -36.7] | 88 |
| smt | bbox | 32 | -27.4 | [-37.1, -17.7] | 84 |


## 4. Ảnh hưởng của điện thoại (chỉ các điều kiện chụp bằng cả hai máy)

| Engine | Biến thể | Điều kiện | ip12 | s21 |
| --- | --- | --- | --- | --- |
| homr | raw | nghieng | 12.2 | 10.2 |
| homr | raw | sang | 8.6 | 11.1 |
| homr | rect | nghieng | 9.2 | 5.6 |
| homr | rect | sang | 7.4 | 6.1 |
| homr | norm | nghieng | 8.9 | 10.2 |
| homr | norm | sang | 11.1 | 6.0 |
| homr | bbox | nghieng | 18.7 | 17.5 |
| homr | bbox | sang | 6.2 | 6.2 |
| audiveris | raw | nghieng | 100.0 | 100.0 |
| audiveris | raw | sang | 15.7 | 17.2 |
| audiveris | rect | nghieng | 78.2 | 57.5 |
| audiveris | rect | sang | 13.2 | 12.2 |
| audiveris | norm | nghieng | 49.8 | 31.6 |
| audiveris | norm | sang | 15.7 | 14.6 |
| audiveris | bin | nghieng | 44.3 | 31.6 |
| audiveris | bin | sang | 16.7 | 13.3 |
| audiveris | bbox | nghieng | 100.0 | 97.2 |
| audiveris | bbox | sang | 15.7 | 17.2 |
| smt | raw | nghieng | 81.6 | 75.3 |
| smt | raw | sang | 83.8 | 44.6 |
| smt | rect | nghieng | 20.3 | 21.8 |
| smt | rect | sang | 17.6 | 27.8 |
| smt | norm | nghieng | 21.0 | 23.2 |
| smt | norm | sang | 22.5 | 17.2 |
| smt | bbox | nghieng | 57.8 | 73.5 |
| smt | bbox | sang | 26.2 | 26.4 |


## 5. Bước tìm trang (rectify_pages.py)

| Điều kiện | already_page | none | quad |
| --- | --- | --- | --- |
| bong | 0 | 0 | 32 |
| den_ban | 0 | 0 | 32 |
| nen_roi | 0 | 3 | 29 |
| nghieng | 0 | 0 | 64 |
| sang | 0 | 0 | 64 |
| scan_app | 32 | 0 | 0 |


Sai số góc trang so với toạ độ thật của ảnh mô phỏng (% đường chéo ảnh):


| Điều kiện | n | Trung bình | Lớn nhất | Ảnh sai > 2% |
| --- | --- | --- | --- | --- |
| bong | 32 | 0.15 | 0.39 | 0 |
| den_ban | 32 | 0.08 | 0.20 | 0 |
| nen_roi | 32 | 4.51 | 26.45 | 7 |
| nghieng | 64 | 0.13 | 0.27 | 0 |
| sang | 64 | 0.14 | 0.34 | 0 |
