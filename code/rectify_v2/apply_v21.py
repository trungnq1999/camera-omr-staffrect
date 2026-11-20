#!/usr/bin/env python3
"""
apply_v21.py - Nâng kết quả v2.0 đã chạy lên v2.1 mà không phải nắn lại: v2.1 chỉ khác ở ngưỡng lật 180°
(lật khi điểm < -0.2 thay vì < 0). Ảnh v2.0 đã lật với điểm trong (-0.2, 0) được xoay lại 180° (raw/norm/bin),
report_v2.csv cập nhật, và các ảnh này được chép sang <out>_fix/ để chạy engine riêng.

  python pp_study/rectify_v2/apply_v21.py --out v2_ip14pm
"""
import argparse, csv, os, shutil
import cv2

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--margin", type=float, default=0.2)
a = ap.parse_args()
rep = os.path.join(a.out, "report_v2.csv")
rows = list(csv.DictReader(open(rep, encoding="utf-8")))
fix = a.out.rstrip("/") + "_fix"
changed = []
for r in rows:
    if r["version"] == "v2.0" and r["flipped"] == "1" and float(r["updown"]) > -a.margin:
        name = r["file"]
        for v, fn in (("raw", name), ("norm", name), ("bin", name[:-4] + ".png")):
            p = os.path.join(a.out, v, fn)
            im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            im = cv2.rotate(im, cv2.ROTATE_180)
            if fn.endswith(".png"): cv2.imwrite(p, im)
            else: cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
            os.makedirs(os.path.join(fix, v), exist_ok=True)
            shutil.copy2(p, os.path.join(fix, v, fn))
        if r["H"]:
            import numpy as np
            H = np.array([float(x) for x in r["H"].split(";")]).reshape(3, 3)
            im = cv2.imread(os.path.join(a.out, "raw", name)); h, w = im.shape[:2]
            H = np.array([[-1, 0, w - 1], [0, -1, h - 1], [0, 0, 1.0]]) @ H
            r["H"] = ";".join(f"{x:.6g}" for x in H.ravel())
        r["flipped"] = "0"
        changed.append(name)
    r["version"] = "v2.1"
with open(rep, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"Đã xoay lại {len(changed)} ảnh:", *changed, sep="\n  ")
print(f"Ảnh cần chạy lại engine: {fix}/raw, {fix}/norm, {fix}/bin")
