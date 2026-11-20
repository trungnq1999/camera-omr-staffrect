#!/usr/bin/env python3
"""
redact_photos.py - Prepare the photographs for public release.
  * removes GPS and other location/owner EXIF fields (keeps Make/Model/DateTime/exposure);
  * blurs everything outside the (slightly enlarged) true paper outline in photographs whose background
    contains other documents (condition nen_roi by default; --all for every camera photo), so that
    names or personal data printed on surrounding papers are not published.
The true paper outline comes from diag.csv (real_diag.py) and the print box estimated from the scans,
exactly as in make_oracle.py.

  python pp_study/release/redact_photos.py --photos real_photos2 --diag results_real/diag.csv --out release_photos/ip14pm
"""
import argparse, csv, os, sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from make_oracle import P, print_box, paper_quad  # noqa: E402

KEEP_TAGS = {0x010F, 0x0110, 0x0132, 0x0112, 0x011A, 0x011B, 0x0128}   # make, model, datetime, orientation, resolution


def clean_exif(src_im):
    ex = src_im.getexif()
    out = Image.Exif()
    for k in KEEP_TAGS:
        if k in ex:
            out[k] = ex[k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", required=True)
    ap.add_argument("--diag", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conds", default="nen_roi", help="comma list of conditions to blur outside the page")
    ap.add_argument("--all", action="store_true", help="blur outside the page in every camera photograph")
    ap.add_argument("--margin", type=float, default=0.01, help="page outline enlargement, fraction of diagonal")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.diag, encoding="utf-8")))
    box = print_box(rows)
    conds = set(a.conds.split(","))
    os.makedirs(a.out, exist_ok=True)
    n_blur = 0
    for r in rows:
        f = os.path.join(a.photos, r["file"])
        im = Image.open(f)
        exif = clean_exif(im)
        bgr = cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)
        cond = r["cond"]
        if cond != "scan_app" and (a.all or cond in conds) and r.get("oracle_quad"):
            q = paper_quad(P(r["oracle_quad"]), box)
            c = q.mean(0); d = np.linalg.norm(q[0] - q[2])
            q = c + (q - c) * (1 + a.margin * d / max(1.0, np.linalg.norm(q - c, axis=1).mean()))
            mask = np.zeros(bgr.shape[:2], np.uint8)
            cv2.fillPoly(mask, [np.round(q).astype(np.int32)], 255)
            k = max(bgr.shape[:2]) // 40
            small = cv2.resize(bgr, None, fx=1 / k, fy=1 / k, interpolation=cv2.INTER_AREA)   # pixelate
            blur = cv2.resize(small, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_NEAREST)
            blur = cv2.GaussianBlur(blur, (0, 0), k / 2)
            bgr = np.where(mask[..., None] > 0, bgr, blur)
            n_blur += 1
        out = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        out.save(os.path.join(a.out, r["file"]), quality=95, exif=exif.tobytes())
    print(f"{len(rows)} photographs written to {a.out}; background blurred in {n_blur}; GPS/owner EXIF removed in all.")
    print("CHECK BY EYE before publishing: open the blurred ones and any other photo whose background shows documents or faces.")


if __name__ == "__main__":
    main()
