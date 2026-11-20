#!/usr/bin/env python3
"""
make_oracle.py - Tạo hai bộ ảnh "chuẩn" (oracle) từ ảnh chụp thật + diag.csv của real_diag.py,
để đo TRẦN hiệu quả của tiền xử lý (phân tích, không phải phương pháp):

  <out>_rot/   : ảnh gốc, chỉ xoay bội số 90° cho trang đứng thẳng (sửa hướng ảnh, không nắn)
  <out>_rect/  : nắn trang bằng 4 góc TỜ GIẤY chuẩn (từ so khớp với trang in gốc), về khổ A4 đứng thẳng
                 = kết quả tốt nhất mà một bộ tìm mép trang hoàn hảo có thể đạt

Tờ giấy lớn hơn vùng trang PDF (máy in thu nhỏ khi in). Tỉ lệ + lề in được ước lượng tự động từ các ảnh
scan_app (ứng dụng quét cắt đúng mép giấy), rồi áp cho mọi ảnh.

  python pp_study/tools/make_oracle.py --photos real_photos2 --diag results_real/diag.csv --out oracle
"""
import argparse
import csv
import os
import shutil

import cv2
import numpy as np

A4 = 297 / 210


def P(s):
    return np.array([[float(v) for v in c.split(",")] for c in s.split(";")], np.float32)


def print_box(rows):
    """Vùng trang PDF trên tờ giấy (toạ độ chuẩn hoá 0..1), trung vị trên các ảnh scan_app."""
    b = []
    for r in rows:
        if r["cond"] != "scan_app" or not r.get("oracle_quad"):
            continue
        q = P(r["oracle_quad"])
        W, H = float(r["W"]), float(r["H"])
        b.append([q[:, 0].min() / W, q[:, 1].min() / H, q[:, 0].max() / W, q[:, 1].max() / H])
    if len(b) < 5:
        raise SystemExit("Cần ít nhất 5 ảnh scan_app trong diag.csv để ước lượng lề in")
    b = np.median(np.array(b), 0)
    return b


def paper_quad(q, box):
    u0, v0, u1, v1 = box
    src = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])
    Hm = cv2.getPerspectiveTransform(src, q.astype(np.float32))
    a0, a1 = -u0 / (u1 - u0), (1 - u0) / (u1 - u0)
    b0, b1 = -v0 / (v1 - v0), (1 - v0) / (v1 - v0)
    c = np.float32([[a0, b0], [a1, b0], [a1, b1], [a0, b1]]).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(c, Hm).reshape(4, 2)


ROT = {90: cv2.ROTATE_90_COUNTERCLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_CLOCKWISE}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", required=True)
    ap.add_argument("--diag", required=True)
    ap.add_argument("--out", default="oracle")
    ap.add_argument("--width", type=int, default=2480)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.diag, encoding="utf-8")))
    box = print_box(rows)
    print("Vùng in trên tờ giấy (x0,y0,x1,y1):", np.round(box, 4))
    d_rot, d_rect = a.out + "_rot", a.out + "_rect"
    os.makedirs(d_rot, exist_ok=True)
    os.makedirs(d_rect, exist_ok=True)
    W, H = a.width, int(round(a.width * A4))
    dst = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
    log = []
    for r in rows:
        src = os.path.join(a.photos, r["file"])
        if not r.get("oracle_quad"):
            print("Bỏ qua (không so khớp được):", r["file"])
            continue
        rot = int(r["rot_class"])
        img = cv2.imread(src)
        # 1) chỉ sửa hướng
        if rot == 0:
            shutil.copy2(src, os.path.join(d_rot, r["file"]))
        else:
            cv2.imwrite(os.path.join(d_rot, r["file"]), cv2.rotate(img, ROT[rot]), [cv2.IMWRITE_JPEG_QUALITY, 95])
        # 2) nắn bằng 4 góc tờ giấy chuẩn (thứ tự góc theo trang -> tự đứng thẳng)
        if r["cond"] == "scan_app":
            shutil.copy2(src, os.path.join(d_rect, r["file"]))        # ảnh quét: đã là trang
        else:
            pq = paper_quad(P(r["oracle_quad"]), box)
            M = cv2.getPerspectiveTransform(pq.astype(np.float32), dst)
            out = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            cv2.imwrite(os.path.join(d_rect, r["file"]), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log.append(dict(file=r["file"], rot=rot))
    print(f"Đã ghi {len(log)} ảnh vào {d_rot}/ và {d_rect}/")


if __name__ == "__main__":
    main()
