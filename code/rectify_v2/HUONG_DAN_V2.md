# Tiền xử lý v2: xác định hướng ảnh + nắn trang theo khuông nhạc

Phát triển trên tập ảnh iPhone 14 Pro Max (tập phát triển). Kết quả hình học trên tập này,
đo bằng 4 góc tờ giấy chuẩn (`eval_v2_geometry.py`), chạy trên ảnh thu nhỏ còn 2000 px:

| Điều kiện | Đúng hướng | Nắn đúng (sai số < 2%) | Trung vị sai số |
|---|---|---|---|
| sang | 32/32 | 32/32 | 0,36% |
| den_ban | 32/32 | 31/32 | 0,38% |
| bong | 32/32 | 32/32 | 0,39% |
| nen_roi | 32/32 | 28/32 | 0,78% |
| nghieng | 29/32 | 18/32 | 1,38% |
| scan_app | 31/32 | 32/32 | 1,12% |

Để so sánh, quy trình v1 (đã khoá) trên cùng tập ảnh:
- đúng hướng 156/192, vì không có bước xoay;
- tìm đúng trang 64/192 (sang 31, den_ban 26, bong 7, nen_roi 0, nghieng 0).

## Chạy trên ảnh iPhone 14 Pro Max (tập phát triển)

```bash
cd /mnt/g/doan/minh
.venv/bin/python -m pip install scipy          # nếu venv chưa có
.venv/bin/python pp_study/rectify_v2/rectify_v2.py --photos real_photos2 --out v2_ip14pm
.venv/bin/python pp_study/tools/eval_v2_geometry.py --diag results_real/diag.csv \
    --report v2_ip14pm/report_v2.csv --out v2_ip14pm/geometry.csv
```

Bước nắn tạo 3 thư mục ảnh: `v2_ip14pm/raw`, `v2_ip14pm/norm` và `v2_ip14pm/bin`. Hai thư mục sau dùng đúng hàm chuẩn hoá ánh sáng và Sauvola của bản đã khoá.

Sau đó chạy các engine bằng quy trình cũ, mỗi thư mục chỉ chạy biến thể `raw`:

```bash
P=pp_study/pipeline/run_pipeline.py
.venv/bin/python $P --photos v2_ip14pm/raw  --out results_v2_raw  --variants raw --smt-variants raw
.venv/bin/python $P --photos v2_ip14pm/norm --out results_v2_norm --variants raw --smt-variants raw
.venv/bin/python $P --photos v2_ip14pm/bin  --out results_v2_bin  --variants raw --engines audiveris
```

## Khoá và chạy máy thứ hai (tập kiểm tra)

Khi đã chốt v2 trên tập phát triển, khoá cấu hình bằng `sha256sum pp_study/rectify_v2/* > frozen/FROZEN_V2.sha256`. Sau đó KHÔNG sửa gì nữa. Ảnh máy thứ hai đặt trong `real_photos3/` và chạy theo thứ tự sau:
1. `real_diag.py`: lấy 4 góc chuẩn;
2. `rectify_v2.py`;
3. `eval_v2_geometry.py`;
4. 3 lệnh `run_pipeline` như trên.

Ngoài ra chạy `run_pipeline` một lần trên `real_photos3` (quy trình v1) để có đường cơ sở.
