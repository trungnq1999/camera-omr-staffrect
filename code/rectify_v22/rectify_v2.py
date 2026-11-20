#!/usr/bin/env python3
"""
rectify_v2.py - Tiền xử lý v2 cho ảnh chụp bản nhạc: tự xác định hướng ảnh + nắn trang theo KHUÔNG NHẠC
(không cần thấy mép giấy). Phát triển trên tập ảnh iPhone 14 Pro Max (tập phát triển); khoá trước khi chạy
trên ảnh máy thứ hai (tập kiểm tra).

Các bước cho mỗi ảnh:
  1. Hướng ngang/dọc: so sánh bằng chứng dòng kẻ khuông theo hai trục (profile theo ô + bộ lọc "lược 5 dòng").
  2. Đoạn thẳng LSD -> giữ đoạn có đoạn song song cách ~1 khoảng dòng kẻ (cấu trúc khuông) -> vùng nhạc.
  3. Điểm tụ ngang (dòng kẻ khuông) và điểm tụ dọc (thân nốt, vạch nhịp, mép trang trong vùng nhạc), RANSAC.
  4. Ước lượng tiêu cự từ hai điểm tụ (hoặc dùng giá trị mặc định), xoay camera ảo cho mặt giấy song song
     mặt ảnh -> ảnh nắn; cắt quanh vùng nhạc + lề 7% bề rộng.
  5. Đúng chiều / lộn ngược: mật độ nét ở hai đầu khuông + so khớp hình khoá nhạc ở đầu và cuối khuông;
     v2.2: lật khi điểm < 0 (bỏ ngưỡng -0.2 của v2.1).
  v2.2 (17/11/2026, sau khi xem kết quả máy Xiaomi): (a) nâng độ phân giải xử lý khi khoảng dòng kẻ < 7 px;
     (b) đoạn khuông phải nằm trên nền giấy (không phải vân gỗ màu cam đậm); (c) vùng nhạc = mọi vùng khuông
     đủ lớn (>=15% vùng lớn nhất), không chỉ vùng lớn nhất.
  Thất bại ở bước 2-4 -> trả về ảnh gốc đã xoay đúng hướng (ghi 'fallback').

Đầu ra: <out>/raw/ (ảnh v2), <out>/norm/ (v2 + chuẩn hoá ánh sáng), <out>/bin/ (v2 + Sauvola),
dùng đúng hàm normalize_light và sauvola của rectify_pages.py (bản đã khoá, chỉ import), và report_v2.csv.

  python pp_study/rectify_v2/rectify_v22/rectify_v2.py --photos real_photos2 --out v22_ip14pm
"""
import argparse
import csv
import glob
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "rectify"))
from rv2 import rectify, side_score  # noqa: E402
from updown import updown  # noqa: E402

VERSION = "v2.2"
FLIP_MARGIN = 0.0   # v2.2: bỏ ngưỡng lật học từ iPhone (v2.1 dùng 0.2)


def process(img_bgr, out_w=2480):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    t = time.time()
    try:
        o = rectify(gray, out_w=1600, bgr=img_bgr)
    except Exception as e:  # noqa: BLE001
        o = dict(ok=False, why="EXC " + str(e)[:60])
    if o.get("ok"):
        small = cv2.warpPerspective(gray, o["H"], o["size"], flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
        ud, cues = updown(small)
        k = out_w / o["size"][0]
        S = np.diag([k, k, 1.0])
        H = S @ o["H"]
        W, Hh = out_w, int(round(o["size"][1] * k))
        if ud < -FLIP_MARGIN:
            H = np.array([[-1, 0, W - 1], [0, -1, Hh - 1], [0, 0, 1.0]]) @ H
        out = cv2.warpPerspective(img_bgr, H, (W, Hh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        info = dict(method="staff", updown=round(ud, 4), flipped=int(ud < -FLIP_MARGIN), side=round(o["info"]["side"], 3),
                    f_rel=round(o["info"].get("f", 0), 3), v2=o["info"].get("v2", "vp"),
                    H=";".join(f"{v:.6g}" for v in H.ravel()))
    else:
        side = side_score(gray)
        rot = img_bgr if side >= 0 else cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        g2 = cv2.cvtColor(rot, cv2.COLOR_BGR2GRAY)
        s = 1600 / g2.shape[1]
        ud, cues = updown(cv2.resize(g2, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        out = rot if ud >= -FLIP_MARGIN else cv2.rotate(rot, cv2.ROTATE_180)
        info = dict(method="fallback:" + str(o.get("why")), updown=round(ud, 4), flipped=int(ud < -FLIP_MARGIN),
                    side=round(side, 3), f_rel="", v2="", H="")
    info["seconds"] = round(time.time() - t, 2)
    info.update({k: round(v, 4) for k, v in cues.items()})
    return out, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="chỉ xử lý ảnh có chuỗi này trong tên (chạy thử)")
    a = ap.parse_args()
    from rectify_pages import normalize_light, sauvola  # bản đã khoá, chỉ dùng lại hàm
    for v in ("raw", "norm", "bin"):
        os.makedirs(os.path.join(a.out, v), exist_ok=True)
    rep = os.path.join(a.out, "report_v2.csv")
    done = set()
    if os.path.exists(rep):
        done = {r["file"] for r in csv.DictReader(open(rep, encoding="utf-8"))}
    files = sorted(glob.glob(os.path.join(a.photos, "*.jpg")))
    if a.only:
        files = [f for f in files if a.only in f]
    fields = None
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        if name in done:
            continue
        img = cv2.imread(f)
        out, info = process(img)
        cv2.imwrite(os.path.join(a.out, "raw", name), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
        nl = normalize_light(out)
        cv2.imwrite(os.path.join(a.out, "norm", name), nl, [cv2.IMWRITE_JPEG_QUALITY, 95])
        bn = sauvola(nl)
        cv2.imwrite(os.path.join(a.out, "bin", name[:-4] + ".png"), bn)
        row = dict(file=name, version=VERSION, **info)
        new = not os.path.exists(rep)
        with open(rep, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row.keys()))
            if new:
                w.writeheader()
            w.writerow(row)
        print(f"{i}/{len(files)} {name}: {info['method']} lật={info['flipped']} ({info['seconds']} s)", flush=True)


if __name__ == "__main__":
    main()
