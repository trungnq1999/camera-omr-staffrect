#!/usr/bin/env python3
"""
eval_v2_geometry.py - Đo độ đúng HÌNH HỌC của tiền xử lý v2 bằng 4 góc tờ giấy chuẩn (từ real_diag.py):
  - orient_ok : trang ra đứng thẳng (sai số góc < 45°)
  - geo_err   : sai lệch còn lại so với một hình chữ nhật A4 (khớp đồng dạng), chia cho đường chéo trang
  - geo_ok    : geo_err < 2%
Lề in (vùng trang PDF trên tờ giấy) ước lượng từ ảnh scan_app trong diag.csv, như make_oracle.py.

  python pp_study/tools/eval_v2_geometry.py --diag results_real/diag.csv --report v2_ip14pm/report_v2.csv
"""
import argparse
import csv
import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_oracle import P, print_box, paper_quad  # noqa: E402

A4 = 297 / 210


def sim_fit(q):
    R = np.array([[0, 0], [1, 0], [1, A4], [0, A4]], float)
    X = q - q.mean(0); Y = R - R.mean(0)
    xc = X[:, 0] + 1j * X[:, 1]; yc = Y[:, 0] + 1j * Y[:, 1]
    a = (np.conj(yc) @ xc) / (np.conj(yc) @ yc)
    res = xc - a * yc
    return float(np.sqrt(np.mean(np.abs(res) ** 2)) / abs(a) / np.hypot(1, A4)), float(np.degrees(np.angle(a)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diag", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--input-long", type=int, default=0,
                    help="nếu ảnh đưa vào v2 đã thu nhỏ: cạnh dài của ảnh đó (vd 2000); mặc định ảnh gốc")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.diag, encoding="utf-8")))
    box = print_box(rows)
    diag = {r["file"]: r for r in rows}
    out = []
    for r in csv.DictReader(open(a.report, encoding="utf-8")):
        d = diag.get(r["file"])
        if d is None or not d.get("oracle_quad"):
            continue
        cond = r["file"].split("__")[1].rsplit("_", 1)[0]
        s = a.input_long / max(float(d["W"]), float(d["H"])) if a.input_long else 1.0
        pq = paper_quad(P(d["oracle_quad"]), box).astype(np.float64) * s
        row = dict(file=r["file"], cond=cond, rot_in=d["rot_class"], method=r["method"].split(":")[0])
        if r["H"]:
            H = np.array([float(v) for v in r["H"].split(";")]).reshape(3, 3)
            q = cv2.perspectiveTransform(pq.reshape(-1, 1, 2), H).reshape(4, 2)
            e, rot = sim_fit(q)
            row.update(geo_err=round(e, 4), rot_out=round(rot, 1), orient_ok=int(abs(rot) < 45), geo_ok=int(e < 0.02))
        else:
            # fallback: chỉ xoay bội số 90 -> hướng đúng nếu tổng góc = 0
            k = int(d["rot_class"])
            k = (k - (90 if float(r["side"]) < 0 else 0) - (180 if int(r["flipped"]) else 0)) % 360
            row.update(geo_err="", rot_out=k, orient_ok=int(k == 0), geo_ok=0)
        out.append(row)
    import collections
    by = collections.defaultdict(list)
    for x in out:
        by[x["cond"]].append(x)
    print(f"{'Điều kiện':10s} {'n':>3s} {'đúng hướng':>10s} {'nắn đúng (<2%)':>15s} {'sai số TV':>10s}")
    for c in sorted(by):
        xs = by[c]
        errs = [x["geo_err"] for x in xs if x["geo_err"] != ""]
        print(f"{c:10s} {len(xs):3d} {sum(x['orient_ok'] for x in xs):10d} {sum(x['geo_ok'] for x in xs):15d} "
              f"{(np.median(errs) * 100 if errs else float('nan')):9.2f}%")
    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader(); w.writerows(out)


if __name__ == "__main__":
    main()
