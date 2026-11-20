#!/usr/bin/env python3
"""
rename_photos.py - Nhận trang và điều kiện chụp cho ảnh điện thoại (tên tự động IMG_xxxx), rồi đổi tên
theo quy ước <mã trang>__<điều kiện>_<máy>.jpg và đổi HEIC sang JPG.

Hai bước, KHÔNG đổi tên ngay:
  1) scan : đọc ảnh, nhận TRANG (so khớp đặc trưng ORB với 32 trang in gốc), đoán ĐIỀU KIỆN và MÁY,
            ghi đề xuất ra plan.csv và một tờ ảnh thu nhỏ để kiểm tra.
     python rename_photos.py scan --in anh_tai_ve --plan plan.csv
  2) Mở plan.csv (Excel), xem các dòng status khác OK, sửa cột page_id / condition nếu sai.
  3) apply: đổi định dạng + đặt tên theo plan.csv vào thư mục đích (ảnh gốc không bị sửa).
     python rename_photos.py apply --plan plan.csv --dst real_photos2

Điều kiện chụp:
  - Nếu ảnh nằm trong thư mục con mang tên điều kiện (sang/, den_ban/, nghieng/, bong/, nen_roi/), dùng tên
    thư mục: CHẮC CHẮN đúng. Nên làm cách này.
  - Nếu không, script ĐOÁN từ ảnh (độ nghiêng trang, độ sáng/màu ánh sáng, bóng, diện tích trang, ISO, giờ chụp)
    và đánh dấu status=CHECK để thầy xác nhận. Không dùng kết quả đoán mà không xem lại.
Máy: đọc từ EXIF (iPhone 14 Pro Max -> ip14pm, iPhone 8 -> ip8, SM-G991B -> s21; máy khác: --phone-code).

Cần: python -m pip install opencv-python numpy pillow pillow-heif pymupdf
"""
import argparse
import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

HERE = os.path.dirname(os.path.abspath(__file__))
CONDS = ["sang", "den_ban", "nghieng", "bong", "nen_roi", "scan_app"]
PHONES = {"iphone 14 pro max": "ip14pm", "iphone 8": "ip8", "sm-g991b": "s21", "galaxy s21": "s21",
          "iphone 12": "ip12"}
EXTS = (".jpg", ".jpeg", ".heic", ".heif", ".png")


# ------------------------------------------------------------------ đọc ảnh
def load_pil(path):
    if path.lower().endswith((".heic", ".heif")) and pillow_heif is None:
        sys.exit("Ảnh HEIC: cần  python -m pip install pillow-heif")
    im = Image.open(path)
    exif = im.getexif()
    return ImageOps.exif_transpose(im).convert("RGB"), exif


def exif_info(exif):
    model = str(exif.get(0x0110, "") or "").strip()
    dt = str(exif.get(0x0132, "") or "")
    sub = exif.get_ifd(0x8769) if hasattr(exif, "get_ifd") else {}
    iso = sub.get(0x8827)
    if isinstance(iso, (tuple, list)):
        iso = iso[0]
    dto = str(sub.get(0x9003, "") or dt)
    hour = int(dto[11:13]) if re.match(r"\d{4}:\d\d:\d\d \d\d", dto) else None
    return model, dto, (int(iso) if iso else None), hour


def norm_name(t):
    """'Đèn bàn' -> 'den_ban', 'Nền rối' -> 'nen_roi', '1. Sáng' -> '1_sang'."""
    import unicodedata
    t = t.replace("đ", "d").replace("Đ", "D")
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


FOLDER_ALIASES = {"sang": "sang", "ban_ngay": "sang",
                  "den_ban": "den_ban", "denban": "den_ban", "den": "den_ban",
                  "nghieng": "nghieng", "bong": "bong", "co_bong": "bong",
                  "nen_roi": "nen_roi", "nenroi": "nen_roi", "lon_xon": "nen_roi",
                  "scan_app": "scan_app", "scan": "scan_app", "quet": "scan_app"}


def folder_condition(rel):
    """Điều kiện lấy từ tên thư mục con gần ảnh nhất (bỏ dấu, không phân biệt hoa thường, chấp nhận tiền tố số)."""
    for part in reversed(rel.replace("\\", "/").split("/")[:-1]):
        n = norm_name(part)
        if n in FOLDER_ALIASES:
            return FOLDER_ALIASES[n]
        for key in sorted(FOLDER_ALIASES, key=len, reverse=True):     # '1_sang', 'anh_den_ban', 'sang_ip14'
            if re.search(r"(^|_)" + key + r"($|_)", n):
                return FOLDER_ALIASES[key]
    return None


def phone_code(model, override):
    if override:
        return override
    m = model.lower()
    for k, v in PHONES.items():
        if k in m:
            return v
    return re.sub(r"[^a-z0-9]", "", m)[:10] or "unknown"


# ------------------------------------------------------------------ trang tham chiếu
def load_refs(pdf, manifest, width=900):
    import pymupdf
    order = [r["page_id"] for r in csv.DictReader(open(manifest, encoding="utf-8"))]
    doc = pymupdf.open(pdf)
    if len(doc) != len(order):
        sys.exit(f"PDF có {len(doc)} trang nhưng manifest có {len(order)} trang")
    orb = cv2.ORB_create(nfeatures=4000)
    refs = []
    for pid, page in zip(order, doc):
        zoom = width / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
        g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
        kp, des = orb.detectAndCompute(g, None)
        small = cv2.resize(g, (120, 170), interpolation=cv2.INTER_AREA)
        refs.append(dict(page_id=pid, kp=kp, des=des, shape=g.shape, small=small))
    return refs


def match_page(gray, refs, orb, bf):
    """Trả về [(inliers, page_id, H), ...] sắp giảm dần: số cặp điểm khớp hình học (RANSAC) với từng trang."""
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 50:
        return []
    out = []
    for r in refs:
        if r["des"] is None:
            continue
        m = bf.knnMatch(des, r["des"], k=2)
        good = [a for a, b in (x for x in m if len(x) == 2) if a.distance < 0.78 * b.distance]
        if len(good) < 12:
            out.append((len(good) // 4, r["page_id"], None))
            continue
        src = np.float32([kp[g.queryIdx].pt for g in good])
        dst = np.float32([r["kp"][g.trainIdx].pt for g in good])
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
        out.append((int(mask.sum()) if mask is not None else 0, r["page_id"], H))
    out.sort(key=lambda t: -t[0])
    return out


# ------------------------------------------------------------------ đoán điều kiện
def page_quad(H, ref_shape, img_shape):
    """Chiếu 4 góc trang tham chiếu về ảnh chụp (nghịch đảo H) -> tứ giác trang trong ảnh."""
    if H is None:
        return None
    try:
        Hi = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return None
    h, w = ref_shape
    c = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(c, Hi).reshape(4, 2)


def guess_condition(img_small, quad, iso, hour):
    """
    Đoán điều kiện từ ảnh. Trả về (điều kiện, lý do). Chỉ là gợi ý để người xem lại.
    """
    h, w = img_small.shape[:2]
    reasons = []
    if quad is None:
        return "?", "không định vị được trang"
    area = cv2.contourArea(quad.astype(np.float32)) / (h * w)
    top = np.linalg.norm(quad[1] - quad[0]); bot = np.linalg.norm(quad[2] - quad[3])
    left = np.linalg.norm(quad[3] - quad[0]); right = np.linalg.norm(quad[2] - quad[1])
    persp = max(top, bot) / max(1e-6, min(top, bot)), max(left, right) / max(1e-6, min(left, right))
    tilt = max(persp)
    mask = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(mask, np.round(quad).astype(np.int32), 1)
    inner = cv2.erode(mask, np.ones((15, 15), np.uint8)) > 0
    lab = cv2.cvtColor(img_small, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, B = lab[:, :, 0], lab[:, :, 2]
    paper = inner & (L > np.percentile(L[inner], 40)) if inner.any() else inner
    Lp = L[paper] if paper.any() else L.ravel()
    bright, warm = float(np.median(Lp)), float(np.median(B[paper]) - 128) if paper.any() else 0.0
    # độ không đều sáng trên giấy: nền giấy làm mờ mạnh rồi đo chênh lệch
    bg = cv2.GaussianBlur(cv2.morphologyEx(L, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)), (0, 0), 15)
    uneven = float(np.percentile(bg[inner], 95) - np.percentile(bg[inner], 5)) if inner.any() else 0.0
    reasons.append(f"diện tích {area:.2f}, nghiêng {tilt:.2f}, sáng {bright:.0f}, ấm {warm:+.0f}, "
                   f"không đều {uneven:.0f}, ISO {iso}, giờ {hour}")
    if area > 0.95 and tilt < 1.04:
        return "scan_app", "; ".join(reasons)              # trang phủ kín ảnh, vuông vức: ảnh quét
    if tilt > 1.10:
        return "nghieng", "; ".join(reasons)
    if area < 0.52:
        return "nen_roi", "; ".join(reasons)
    night = (hour is not None and (hour >= 18 or hour < 6)) or (iso is not None and iso >= 400)
    if (warm > 12 and bright < 200) or (night and warm > 6):
        return "den_ban", "; ".join(reasons)
    if uneven > 45:
        return "bong", "; ".join(reasons)
    return "sang", "; ".join(reasons)


# ------------------------------------------------------------------ scan
def cmd_scan(a):
    files = [f for f in sorted(glob.glob(os.path.join(a.inp, "**", "*"), recursive=True))
             if f.lower().endswith(EXTS)]
    if not files:
        sys.exit("Không tìm thấy ảnh trong " + a.inp)
    print(f"{len(files)} ảnh. Đang dựng 32 trang tham chiếu...")
    refs = load_refs(a.pdf, a.manifest)
    orb = cv2.ORB_create(nfeatures=6000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    rows, thumbs = [], []
    for i, f in enumerate(files, 1):
        rel = os.path.relpath(f, a.inp)
        try:
            im, exif = load_pil(f)
        except Exception as e:
            rows.append(dict(file=rel, status="ERROR", note=str(e)[:80]))
            print(f"{i}/{len(files)} {rel}: LỖI {e}")
            continue
        model, dto, iso, hour = exif_info(exif)
        bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        s = 1600 / max(bgr.shape[:2])
        small = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        res = match_page(gray, refs, orb, bf)
        best = res[0] if res else (0, "?", None)
        second = res[1][0] if len(res) > 1 else 0
        page_id = best[1] if best[0] >= a.min_inliers else "?"
        ratio = best[0] / max(1, second)
        quad = page_quad(best[2], next((r["shape"] for r in refs if r["page_id"] == best[1]), (1, 1)), small.shape)
        # điều kiện: thư mục con nếu có, không thì đoán
        folder_cond = folder_condition(rel)
        if folder_cond:
            cond, cond_src, why = folder_cond, "thư mục", ""
        else:
            cond, why = guess_condition(small, quad, iso, hour)
            cond_src = "đoán"
        phone = phone_code(model, a.phone_code)
        status = []
        if page_id == "?":
            status.append("PAGE?")
        elif ratio < 1.5:
            status.append("PAGE_AMBIG")
        if cond_src == "đoán":
            status.append("COND_GUESS")
        if quad is not None:
            hq, wq = small.shape[:2]
            if (quad[:, 0] < 0.005 * wq).any() or (quad[:, 0] > 0.995 * wq).any() or \
               (quad[:, 1] < 0.005 * hq).any() or (quad[:, 1] > 0.995 * hq).any():
                status.append("CORNER_CUT")
        rows.append(dict(file=rel, path=os.path.abspath(f), page_id=page_id, inliers=best[0], second=second, ratio=round(ratio, 2),
                         condition=cond, cond_source=cond_src, phone=phone, model=model, datetime=dto, iso=iso,
                         status=" ".join(status) or "OK", note=why))
        print(f"{i}/{len(files)} {rel}: {page_id} ({best[0]}/{second}) {cond} [{cond_src}] {phone} {' '.join(status)}")
        th = cv2.resize(small, (240, int(240 * small.shape[0] / small.shape[1])))
        if quad is not None:
            cv2.polylines(th, [np.round(quad * 240 / small.shape[1]).astype(np.int32)], True, (0, 180, 0), 2)
        thumbs.append((th, f"{page_id}", f"{cond} {phone}", status))
    # trùng lặp
    cnt = Counter((r.get("page_id"), r.get("condition"), r.get("phone")) for r in rows if r.get("page_id") not in (None, "?"))
    for r in rows:
        if r.get("page_id") not in (None, "?") and cnt[(r["page_id"], r["condition"], r["phone"])] > 1:
            r["status"] = (r["status"].replace("OK", "") + " DUP").strip()
    for r in rows:
        if r.get("page_id") and r["page_id"] != "?":
            r["new_name"] = f"{r['page_id']}__{r['condition']}_{r['phone']}.jpg"
    fields = ["file", "path", "page_id", "condition", "phone", "new_name", "status", "inliers", "second", "ratio",
              "cond_source", "model", "datetime", "iso", "note"]
    with open(a.plan, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    sheet = os.path.splitext(a.plan)[0] + "_contact.jpg"
    make_sheet(thumbs, sheet)
    st = Counter(r["status"] for r in rows)
    print(f"\nĐã ghi {a.plan} và {sheet}. Trạng thái: {dict(st)}")
    order = [r["page_id"] for r in csv.DictReader(open(a.manifest, encoding="utf-8"))]
    by = defaultdict(set)
    for r in rows:
        if r.get("page_id") not in (None, "?"):
            by[(r["condition"], r["phone"])].add(r["page_id"])
    for k, v in sorted(by.items()):
        miss = [p for p in order if p not in v]
        print(f"  {k[0]}_{k[1]}: {len(v)}/{len(order)} trang" + (f", thiếu {len(miss)}: {miss[:6]}{' ...' if len(miss) > 6 else ''}" if miss else ""))


def make_sheet(thumbs, out, cols=8):
    if not thumbs:
        return
    W = 240
    H = max(t[0].shape[0] for t in thumbs) + 40
    rows = (len(thumbs) + cols - 1) // cols
    sheet = np.full((rows * H, cols * W, 3), 255, np.uint8)
    for i, (th, l1, l2, st) in enumerate(thumbs):
        y, x = (i // cols) * H, (i % cols) * W
        sheet[y:y + th.shape[0], x:x + W] = th[:, :W]
        col = (0, 0, 200) if st else (0, 0, 0)
        cv2.putText(sheet, l1[:28], (x + 3, y + th.shape[0] + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1)
        cv2.putText(sheet, l2[:28], (x + 3, y + th.shape[0] + 33), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1)
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])


# ------------------------------------------------------------------ apply
def cmd_apply(a):
    rows = list(csv.DictReader(open(a.plan, encoding="utf-8-sig")))
    bad = [r for r in rows if not r.get("page_id") or r["page_id"] == "?" or r["condition"] not in CONDS]
    names = Counter(f"{r['page_id']}__{r['condition']}_{r['phone']}.jpg" for r in rows if r not in bad)
    dups = [n for n, c in names.items() if c > 1]
    if bad or dups:
        for r in bad:
            print("Chưa có trang/điều kiện hợp lệ:", r["file"], r.get("page_id"), r.get("condition"))
        for n in dups:
            print("Trùng tên:", n)
        sys.exit("Sửa plan.csv rồi chạy lại apply.")
    os.makedirs(a.dst, exist_ok=True)
    src_root = a.inp or os.path.dirname(os.path.abspath(a.plan))
    n = 0
    for r in rows:
        name = f"{r['page_id']}__{r['condition']}_{r['phone']}.jpg"
        out = os.path.join(a.dst, name)
        if os.path.exists(out) and not a.overwrite:
            print("Đã có, bỏ qua:", name)
            continue
        src = r.get("path") or os.path.join(src_root, r["file"])
        im = Image.open(src)
        exif = im.getexif()
        exif[0x0112] = 1                                     # đã xoay theo EXIF -> đặt lại hướng chuẩn
        rgb = ImageOps.exif_transpose(im).convert("RGB")
        if src.lower().endswith((".jpg", ".jpeg")) and not a.reencode:
            import shutil
            shutil.copy2(src, out)                            # JPG gốc: chép nguyên, không nén lại
        else:
            rgb.save(out, quality=95, exif=exif.tobytes())
        n += 1
    print(f"Đã ghi {n} ảnh vào {a.dst}")


def main():
    root = "/mnt/g/doan/minh/pp_study/print_set2/out_set2"
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("scan")
    p.add_argument("--in", dest="inp", required=True, help="thư mục ảnh tải về (có thể chia thư mục con theo điều kiện)")
    p.add_argument("--plan", default="plan.csv")
    p.add_argument("--pdf", default=f"{root}/print/ALL_PAGES.pdf")
    p.add_argument("--manifest", default=f"{root}/manifest.csv")
    p.add_argument("--phone-code", help="ghi đè mã máy (mặc định đọc từ EXIF)")
    p.add_argument("--min-inliers", type=int, default=25)
    p = sp.add_parser("apply")
    p.add_argument("--plan", default="plan.csv")
    p.add_argument("--in", dest="inp", help="thư mục ảnh gốc (mặc định: lấy theo đường dẫn lúc scan)")
    p.add_argument("--dst", required=True)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--reencode", action="store_true", help="nén lại cả ảnh JPG gốc (mặc định chép nguyên)")
    p = sp.add_parser("run", help="scan rồi apply luôn nếu không có vấn đề (trang chắc chắn, điều kiện theo thư mục, không trùng)")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--dst", required=True)
    p.add_argument("--plan", default="plan.csv")
    p.add_argument("--pdf", default=f"{root}/print/ALL_PAGES.pdf")
    p.add_argument("--manifest", default=f"{root}/manifest.csv")
    p.add_argument("--phone-code")
    p.add_argument("--min-inliers", type=int, default=25)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--reencode", action="store_true")
    a = ap.parse_args()
    if a.cmd == "scan":
        cmd_scan(a)
    elif a.cmd == "apply":
        cmd_apply(a)
    else:
        cmd_scan(a)
        rows = list(csv.DictReader(open(a.plan, encoding="utf-8-sig")))
        block = [r for r in rows if any(t in r["status"] for t in ("PAGE?", "PAGE_AMBIG", "DUP", "COND_GUESS", "ERROR"))]
        cut = [r for r in rows if "CORNER_CUT" in r["status"]]
        if cut:
            print(f"\nLưu ý: {len(cut)} ảnh có trang chạm mép ảnh (CORNER_CUT), vẫn đổi tên nhưng nên xem lại:")
            for r in cut[:20]:
                print("   ", r["file"], "->", r.get("new_name"))
        if block:
            print(f"\nDỪNG, chưa đổi tên: {len(block)} ảnh cần xử lý tay trong {a.plan} (cột status):")
            for r in block[:40]:
                print(f"   {r['file']}: trang={r.get('page_id')} điều kiện={r.get('condition')} [{r['status']}]")
            print("Sửa plan.csv rồi chạy:  rename_photos.py apply --plan", a.plan, "--dst", a.dst)
            sys.exit(1)
        cmd_apply(a)


if __name__ == "__main__":
    main()
