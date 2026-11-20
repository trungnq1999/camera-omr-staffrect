# Quy trình đánh giá tiền xử lý: chạy với ảnh mô phỏng, rồi thay bằng ảnh thật

Một lệnh `run_pipeline.py` làm cả ba bước: tiền xử lý, chạy engine, tổng hợp. Lệnh giống hệt nhau cho ảnh mô phỏng và ảnh thật; chỉ đổi `--photos` và `--out`.

```
/mnt/g/doan/minh/
  pp_study/                     bộ in, nhãn, rectify, sim, pipeline (gói này)
  smt_eval/                     bản mới (thêm --pages cho smt_batch.py)
  omr_eval/engines.json         cấu hình homr + Audiveris (giữ nguyên)
  sim_photos2/                  ảnh MÔ PHỎNG  -> results_sim/
  real_photos2/                 ảnh CHỤP THẬT -> results_real/
```

## 0. Chuẩn bị (một lần)

```bash
cd /mnt/g/doan/minh
unzip -o pp_study.zip && unzip -o smt_eval.zip
export TMPDIR=/mnt/g/tmp HF_HOME=/mnt/g/tmp/hf XDG_CONFIG_HOME=/mnt/g/tmp/config XDG_DATA_HOME=/mnt/g/tmp/data XDG_CACHE_HOME=/mnt/g/tmp/cache
source .venv/bin/activate                 # venv có homr
python -m pip install opencv-python numpy pillow pymupdf
which python                              # đường dẫn này dùng cho --py-homr nếu khác mặc định
```

`run_pipeline.py` mặc định dùng:
- `/mnt/g/doan/minh/.venv/bin/python` cho homr, Audiveris và tiền xử lý;
- `/mnt/g/doan/minh/.venv-smt/bin/python` cho SMT++.

Nếu venv của thầy nằm chỗ khác, truyền thêm `--py-homr ...` và `--py-smt ...`.

## 1. Tạo ảnh mô phỏng (256 ảnh)

`make_photo_dataset.py` trong `pp_study/sim/` là bản của thầy, chỉ thêm cột `corners` (toạ độ thật 4 góc trang) vào manifest để đo sai số bước tìm trang.

```bash
mkdir -p sim_src && cp pp_study/print_set2/out_set2/print/*.pdf sim_src/ && rm sim_src/ALL_PAGES.pdf
python pp_study/sim/make_photo_dataset.py all --dir sim_src --out sim_photos2 --jobs 4
```

Mỗi PDF của từng bản tạo ra mã trang `<bản>_p<k>`, khớp đúng tên nhãn trong `out_set2/gt/`.

## 2. Chạy thử toàn bộ quy trình trên ảnh mô phỏng

homr và Audiveris chạy đủ 256 ảnh. SMT++ chỉ chạy 4 trang đại diện (32 ảnh) cho nhanh:

```bash
python pp_study/pipeline/run_pipeline.py --photos sim_photos2 --out results_sim \
    --smt-pages bach_inv07_p1,haydn_xvi22_1_p1,brahms_118_2_p3,schoenberg_19_2_p1
```

- Bị ngắt thì chạy lại đúng lệnh; phần đã xong được bỏ qua.
- Chỉ muốn tổng hợp lại bảng: thêm `--steps report`.
- Chỉ tiền xử lý: thêm `--steps pre`.
- Kết quả xem ở `results_sim/RESULTS.md`, gồm:
  1. SER theo engine × biến thể;
  2. SER theo điều kiện chụp;
  3. hiệu quả từng biến thể so với ảnh gốc (ghép cặp, có khoảng tin cậy);
  4. ảnh hưởng của điện thoại;
  5. kết quả bước tìm trang, kèm sai số góc trên ảnh mô phỏng.
- Ảnh kiểm tra bước tìm trang nằm ở `results_sim/pre/debug/`.

**Chốt tham số trên ảnh mô phỏng.** Nếu cần chỉnh (ngưỡng tìm trang, cửa sổ Sauvola, `--smt-width`), chỉnh ở bước này. Sau đó **không sửa code hay tham số nữa**. File `pipeline_args.json` ghi lại cấu hình đã chạy.

## 3. Ảnh thật: cùng lệnh, đổi thư mục

Ảnh đặt tên `<mã trang>__<điều kiện>_<máy>.jpg`, ví dụ `brahms_118_2_p3__nghieng_s21.jpg`, vào `real_photos2/`.

```bash
python pp_study/pipeline/run_pipeline.py --photos real_photos2 --out results_real
```

Không có `--smt-pages` nên SMT++ chạy đủ 256 ảnh. Ước tính khoảng 25 giờ trên RTX 3090; có thể ngắt rồi chạy tiếp.

## Ghi chú

- Báo cáo tự đánh dấu **DỮ LIỆU MÔ PHỎNG** khi ảnh có chữ `SIMULATED` trong EXIF, nên không lẫn với kết quả ảnh thật.
- Biến thể `bin` (Sauvola) chỉ chạy cho homr và Audiveris; SMT++ chạy `raw rect norm bbox`. Muốn đổi: `--smt-variants raw rect`.
- Ảnh `scan_app` được nhận là trang đã quét (`already_page`) nên không bị nắn lại. Các biến thể của nó trùng với ảnh gốc, đúng ý đồ: đây là đối chứng ngoài.
