#!/usr/bin/env python3
"""
real_diag.py - Chẩn đoán ảnh chụp thật bằng "trang chuẩn" (oracle): so khớp ORB + RANSAC ảnh chụp với
đúng trang in gốc của nó, chiếu 4 góc trang gốc về ảnh. Từ đó có, cho TỪNG ảnh:
  - rot_deg   : trang trong ảnh bị xoay bao nhiêu (0 = đứng thẳng, 180 = lộn ngược, 90/270 = nằm ngang)
  - cut_frac  : tỉ lệ diện tích trang nằm NGOÀI khung ảnh (chụp mất mép trang)
  - page_area : diện tích trang / diện tích ảnh
  - tilt      : độ phối cảnh (cạnh dài / cạnh ngắn đối diện)
  - rect_iou, rect_err : bước tìm trang (rectify_pages.py, report.csv) so với 4 góc chuẩn
Không sửa gì trong ảnh hay trong cấu hình đã khoá; chỉ đọc và ghi diag.csv + DIAG.md.

  python pp_study/tools/real_diag.py --photos real_photos2 --results results_real
"""
import argparse
import csv
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rename_photos import load_refs  # noqa: E402

ROOT = "/mnt/g/doan/minh/pp_study/print_set2/out_set2"


def oracle_quad(gray, ref, orb, bf):
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or ref["des"] is None:
        return None, 0
    m = bf.knnMatch(des, ref["des"], k=2)
    good = [a for a, b in (x for x in m if len(x) == 2) if a.distance < 0.78 * b.distance]
    if len(good) < 12:
        return None, len(good)
    src = np.float32([kp[g.queryIdx].pt for g in good])
    dst = np.float32([ref["kp"][g.trainIdx].pt for g in good])
    H, mask = cv2.findHomography(dst, src, cv2.RANSAC, 5.0)      # trang gốc -> ảnh
    if H is None:
        return None, 0
    h, w = ref["shape"]
    c = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(c, H).reshape(4, 2), int(mask.sum())


def rotation(q):
    """Góc của hướng 'đầu trang -> chân trang' trong ảnh; 0 = đứng thẳng."""
    top = (q[0] + q[1]) / 2
    bot = (q[2] + q[3]) / 2
    d = bot - top
    return float(np.degrees(np.arctan2(-d[0], d[1])) % 360)


def poly_mask(q, shape, s):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.asarray(q) * s).astype(np.int32)], 1)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--pdf", default=f"{ROOT}/print/ALL_PAGES.pdf")
    ap.add_argument("--manifest", default=f"{ROOT}/manifest.csv")
    a = ap.parse_args()

    refs = {r["page_id"]: r for r in load_refs(a.pdf, a.manifest, width=1200)}
    rep = {r["file"]: r for r in csv.DictReader(open(os.path.join(a.results, "pre", "report.csv"), encoding="utf-8"))}
    ser = {}
    p = os.path.join(a.results, "all_samples.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            ser[(r["engine"], r["variant"], r["stem"])] = float(r["ser_full"])

    orb = cv2.ORB_create(nfeatures=8000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    files = sorted(glob.glob(os.path.join(a.photos, "*.jpg")))
    rows = []
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        stem = name[:-4]
        page, rest = stem.split("__")
        cond = rest.rsplit("_", 1)[0]
        img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        H0, W0 = img.shape
        s = 2000 / max(H0, W0)
        g = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        q, inl = oracle_quad(g, refs[page], orb, bf)
        row = dict(file=name, page=page, cond=cond, inliers=inl, W=W0, H=H0)
        if q is not None:
            q = q / s                                                   # về toạ độ ảnh gốc
            rot = rotation(q)
            ms = 400 / max(H0, W0)
            big = (int(H0 * ms) * 3, int(W0 * ms) * 3)                  # khung rộng để tính phần trang ra ngoài ảnh
            off = np.array([W0, H0]) * ms
            mq = poly_mask((q * ms + off), big, 1)
            frame = np.zeros(big, np.uint8)
            frame[int(off[1]):int(off[1]) + int(H0 * ms), int(off[0]):int(off[0]) + int(W0 * ms)] = 1
            page_px = mq.sum()
            cut = 1 - (mq & frame).sum() / max(1, page_px)
            e = [np.linalg.norm(q[(k + 1) % 4] - q[k]) for k in range(4)]
            tilt = max(max(e[0], e[2]) / max(1e-6, min(e[0], e[2])), max(e[1], e[3]) / max(1e-6, min(e[1], e[3])))
            row.update(rot_deg=round(rot, 1), rot_class=int(round(rot / 90) % 4 * 90),
                       cut_frac=round(float(cut), 3),
                       page_area=round(float((mq & frame).sum() / max(1, frame.sum())), 3),
                       tilt=round(float(tilt), 3),
                       oracle_quad=";".join(f"{x:.0f},{y:.0f}" for x, y in q))
            r = rep.get(name)
            if r:
                row["rect_method"] = r["method"]
                if r["method"].startswith("quad"):
                    rq = np.array([[float(v) for v in c.split(",")] for c in r["quad"].split(";")])
                    a1 = poly_mask(q * ms + off, big, 1)
                    a2 = poly_mask(rq * ms + off, big, 1)
                    iou = (a1 & a2).sum() / max(1, (a1 | a2).sum())
                    # sai số góc: ghép góc gần nhất (không phụ thuộc thứ tự góc), chia đường chéo trang
                    diag = np.linalg.norm(q[0] - q[2])
                    err = np.mean([min(np.linalg.norm(rq - c, axis=1)) for c in q]) / diag
                    row.update(rect_iou=round(float(iou), 3), rect_err=round(float(err), 3))
        for eng, var in [("homr", "raw"), ("homr", "rect"), ("audiveris", "raw"), ("audiveris", "bin"),
                         ("smt", "raw"), ("smt", "rect")]:
            v = ser.get((eng, var, stem))
            if v is not None:
                row[f"ser_{eng}_{var}"] = round(v, 3)
        rows.append(row)
        print(f"{i}/{len(files)} {name}: inliers={inl} rot={row.get('rot_deg')} cut={row.get('cut_frac')} "
              f"rect={row.get('rect_method')} iou={row.get('rect_iou', '-')}", flush=True)

    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    out = os.path.join(a.results, "diag.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("Đã ghi", out)


if __name__ == "__main__":
    main()
