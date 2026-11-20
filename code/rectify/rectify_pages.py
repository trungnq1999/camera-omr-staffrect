#!/usr/bin/env python3
"""
rectify_pages.py - Nắn trang giấy trong ảnh chụp bản nhạc bằng điện thoại.

Mỗi bước có thể bật/tắt riêng để làm thí nghiệm bỏ từng bước (ablation):
  rect   : tìm tứ giác trang giấy -> biến đổi phối cảnh về khổ A4 (ảnh màu)
  norm   : thêm chuẩn hoá ánh sáng (chia cho nền làm mờ) -> ảnh xám nền trắng đều
  bin    : thêm nhị phân hoá thích nghi Sauvola trên ảnh 'norm' (dành cho Audiveris)
  bbox   : chỉ cắt theo hình chữ nhật bao trang, không nắn (giống biến thể 'cropped' trong bài AMI)

Ví dụ:
  python rectify_pages.py --in real_photos2/photos --out real_photos2/pre --steps rect norm bin bbox
  python rectify_pages.py --in anh.jpg --out thu --steps rect --debug

Kết quả:
  <out>/<bước>/<tên ảnh>.jpg     ảnh sau xử lý (bin: .png), đặt cùng tên gốc để chấm bằng omr_eval như ảnh thường
  <out>/debug/<tên ảnh>.jpg      ảnh gốc thu nhỏ, vẽ tứ giác tìm được (khi có --debug)
  <out>/report.csv               mỗi ảnh: cách tìm trang, tỷ lệ diện tích, độ nghiêng, cảnh báo

Chỉ cần: opencv-python, numpy, pillow  (python -m pip install opencv-python numpy pillow)
"""
import argparse
import csv
import glob
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageOps

A4 = 2 ** 0.5                       # tỷ lệ cạnh dài / cạnh ngắn của khổ A4
JPG = [cv2.IMWRITE_JPEG_QUALITY, 95]   # ảnh nắn/chuẩn hoá/cắt khung lưu JPEG 95 (nhỏ hơn PNG 4-6 lần); ảnh nhị phân giữ PNG
EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".heic")


# ------------------------------------------------------------------ đọc ảnh
def load(path):
    """Đọc ảnh và xoay theo EXIF (ảnh điện thoại thường lưu ngang kèm cờ xoay)."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


# ------------------------------------------------------------------ tìm trang giấy
def order_quad(pts):
    """Sắp 4 điểm theo thứ tự: trên-trái, trên-phải, dưới-phải, dưới-trái."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def paper_mask(small):
    """
    Mặt nạ vùng giấy: giấy sáng và gần như không màu. Kết hợp Otsu trên kênh sáng (L)
    với ngưỡng độ bão hoà, rồi đóng lỗ (nốt nhạc, khuông nhạc) bằng phép đóng hình thái.
    """
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    L = cv2.GaussianBlur(lab[:, :, 0], (0, 0), 3)
    _, bright = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    sat = cv2.GaussianBlur(hsv[:, :, 1], (0, 0), 3)
    low_sat = (sat < max(60, np.percentile(sat, 60))).astype(np.uint8) * 255
    mask = cv2.bitwise_and(bright, low_sat)
    k = max(5, small.shape[1] // 60) | 1
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)), iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    return mask


def quad_from_contour(cnt):
    """Xấp xỉ đường viền bằng tứ giác: thử nhiều epsilon, nếu không được thì dùng bao lồi + minAreaRect."""
    hull = cv2.convexHull(cnt)
    peri = cv2.arcLength(hull, True)
    for eps in (0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return order_quad(approx), "quad"
    return order_quad(cv2.boxPoints(cv2.minAreaRect(hull))), "minrect"


def quad_skew(q):
    """Độ lệch góc lớn nhất giữa hai cặp cạnh đối diện (độ); tứ giác méo vô lý có giá trị lớn."""
    def ang(p, r):
        return np.degrees(np.arctan2(r[1] - p[1], r[0] - p[0]))
    return max(abs(ang(q[0], q[1]) - ang(q[3], q[2])), abs(ang(q[0], q[3]) - ang(q[1], q[2])))


def edge_support(q, grad, n=60):
    """
    Tỷ lệ điểm trên từng cạnh tứ giác nằm trên biên ảnh rõ (gradient mạnh).
    Trả về (trung bình 4 cạnh, số cạnh có ít nhất một nửa điểm nằm trên biên).
    Dùng trung bình thay vì cạnh yếu nhất vì mép trang cong hoặc dính vào giấy cùng màu có thể làm yếu một cạnh.
    """
    h, w = grad.shape
    sides = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        t = np.linspace(0.05, 0.95, n)[:, None]
        pts = a + (b - a) * t
        x = np.clip(pts[:, 0].round().astype(int), 0, w - 1)
        y = np.clip(pts[:, 1].round().astype(int), 0, h - 1)
        sides.append(float((grad[y, x] > 0).mean()))
    return float(np.mean(sides)), sum(v >= 0.5 for v in sides)


def candidates(small):
    """Sinh tứ giác ứng viên từ nhiều nguồn: mặt nạ giấy, cạnh Canny (nhiều ngưỡng), kể cả đường viền lồng bên trong."""
    cands = []
    mask = paper_mask(small)
    cnts, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:6]:
        cands.append(quad_from_contour(c) + ("mask",))
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    for lo, hi in ((10, 30), (30, 90), (60, 160)):
        edges = cv2.Canny(gray, lo, hi)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)  # nối nét, không phình biên
        cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:8]:
            cands.append(quad_from_contour(c) + ("edge",))
    return cands, gray


def _intersect(l1, l2):
    """Giao điểm hai đường thẳng cho bởi 2 điểm mỗi đường; None nếu gần song song."""
    (x1, y1, x2, y2), (x3, y3, x4, y4) = l1, l2
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(d) < 1e-6:
        return None
    a, b = x1 * y2 - y1 * x2, x3 * y4 - y3 * x4
    return ((a * (x3 - x4) - (x1 - x2) * b) / d, (a * (y3 - y4) - (y1 - y2) * b) / d)


def line_candidates(gray, top=12):
    """
    Ứng viên từ đường thẳng dài (Hough): ghép 2 đường gần ngang x 2 đường gần dọc thành tứ giác.
    Bổ sung cho cách tìm theo đường viền khi mép trang chạm vào giấy, sách vở cùng màu
    (đường viền bị nối liền với vật bên cạnh nhưng mép trang vẫn là một đường thẳng dài).
    """
    h, w = gray.shape
    edges = cv2.Canny(gray, 20, 60)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=60,
                            minLineLength=int(0.22 * min(h, w)), maxLineGap=int(0.02 * max(h, w)))
    if lines is None:
        return []
    L = []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):   # OpenCV 4: (N,1,4); OpenCV 5: (N,4)
        ang = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
        L.append(((float(x1), float(y1), float(x2), float(y2)), ang, np.hypot(x2 - x1, y2 - y1)))
    L.sort(key=lambda t: -t[2])
    hor = [l for l in L if min(l[1], 180 - l[1]) < 35][:top]
    ver = [l for l in L if abs(l[1] - 90) < 35][:top]
    out = []
    for i in range(len(hor)):
        for j in range(i + 1, len(hor)):
            for k in range(len(ver)):
                for m in range(k + 1, len(ver)):
                    pts = [_intersect(a[0], b[0]) for a, b in ((hor[i], ver[k]), (hor[i], ver[m]),
                                                               (hor[j], ver[m]), (hor[j], ver[k]))]
                    if any(p is None for p in pts):
                        continue
                    q = np.array(pts, dtype=np.float32)
                    if (q[:, 0] < -0.02 * w).any() or (q[:, 0] > 1.02 * w).any() or \
                       (q[:, 1] < -0.02 * h).any() or (q[:, 1] > 1.02 * h).any():
                        continue
                    if not cv2.isContourConvex(q.reshape(-1, 1, 2)):
                        continue
                    out.append((order_quad(q), "quad", "line"))
    return out


def paper_fill(q, mask, n=15):
    """Tỷ lệ điểm bên trong tứ giác thuộc vùng giấy (lấy mẫu lưới n x n theo toạ độ song tuyến)."""
    h, w = mask.shape
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    top = q[0][None, None, :] * (1 - U[..., None]) + q[1][None, None, :] * U[..., None]
    bot = q[3][None, None, :] * (1 - U[..., None]) + q[2][None, None, :] * U[..., None]
    P = top * (1 - V[..., None]) + bot * V[..., None]
    x = np.clip(P[..., 0].round().astype(int), 0, w - 1)
    y = np.clip(P[..., 1].round().astype(int), 0, h - 1)
    return float((mask[y, x] > 0).mean())


def outside_nonpaper(q, mask, n=40, off=0.015):
    """
    Với mỗi cạnh, lấy mẫu một dải ngay BÊN NGOÀI tứ giác; trả về tỷ lệ điểm KHÔNG phải giấy của từng cạnh.
    Mép trang thật có nền khác màu ở ít nhất vài phía; tứ giác dựng từ khuông nhạc bên trong trang thì không.
    """
    h, w = mask.shape
    c = q.mean(0)
    d = off * float(np.hypot(h, w))
    out = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        t = np.linspace(0.1, 0.9, n)[:, None]
        pts = a + (b - a) * t
        nrm = np.array([-(b - a)[1], (b - a)[0]], dtype=np.float32)
        nrm /= max(1e-6, float(np.linalg.norm(nrm)))
        if np.dot((a + b) / 2 - c, nrm) < 0:
            nrm = -nrm
        pts = pts + nrm * d
        x, y = pts[:, 0].round().astype(int), pts[:, 1].round().astype(int)
        ok = (x >= 0) & (x < w) & (y >= 0) & (y < h)
        if ok.sum() < n // 3:
            out.append(1.0)                              # ngoài khung ảnh: coi như nền
            continue
        out.append(float((mask[y[ok], x[ok]] == 0).mean()))
    return out


def find_page(img, work=1000):
    """
    Tìm tứ giác trang giấy. Trả về (4 điểm ở toạ độ ảnh gốc, cách tìm, tỷ lệ diện tích) hoặc None.
    Mỗi ứng viên được chấm theo: (1) cả 4 cạnh phải nằm trên biên ảnh rõ, (2) tỷ lệ gần A4,
    (3) không chạm mép ảnh (trang thường nằm trọn trong khung), (4) diện tích lớn (ưu tiên nhẹ).
    Chấm theo cạnh thay vì theo diện tích giúp tránh dính vào giấy, sách vở xung quanh.
    """
    h, w = img.shape[:2]
    scale = work / max(h, w)
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    area_img = sh * sw
    # ảnh đã là trang giấy (ứng dụng quét, ảnh scan): viền ảnh gần như toàn giấy -> không nắn
    mask = paper_mask(small)
    b = max(3, int(0.02 * min(sh, sw)))
    border = np.concatenate([mask[:b].ravel(), mask[-b:].ravel(), mask[:, :b].ravel(), mask[:, -b:].ravel()])
    border_is_paper = (border > 0).mean() > 0.9
    # ảnh có đúng tỷ lệ A4 (ảnh điện thoại là 3:4) gần như chắc chắn là trang đã quét/cắt sẵn
    if abs(max(h, w) / min(h, w) - A4) < 0.03:
        border_is_paper = True
    cands, gray = candidates(small)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    thr = max(8.0, 0.25 * float(np.percentile(mag, 99)))
    strong = cv2.dilate((mag > thr).astype(np.uint8), np.ones((7, 7), np.uint8))   # dung sai ~3 px

    margin = 0.012 * max(sh, sw)

    def pick(cands, strict_outside):
        best, best_score = None, -1e9
        for q, kind, src in cands:
            ratio = cv2.contourArea(q) / area_img
            if ratio < 0.2 or ratio > 0.97:
                continue
            wq = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
            hq = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
            aspect = max(wq, hq) / max(1e-6, min(wq, hq))
            aspect_pen = abs(np.log(aspect / A4))        # 0 khi đúng tỷ lệ A4
            if aspect_pen > 0.45:                        # lệch xa tỷ lệ A4 kể cả khi nghiêng mạnh
                continue
            support, good_sides = edge_support(q, strong)
            if good_sides < 3:
                continue
            fill = paper_fill(q, mask)                   # bên trong phải gần như toàn giấy
            if fill < 0.6:
                continue
            extra = 0.0
            if strict_outside:
                # ứng viên từ đường thẳng: tránh tứ giác dựng từ khuông nhạc bên trong trang
                outs = outside_nonpaper(q, mask)
                if sum(o >= 0.6 for o in outs) < 2:
                    continue
                extra = 0.6 * float(np.mean(outs))
            near = sum(1 for x, y in q if x < margin or y < margin or x > sw - margin or y > sh - margin)
            score = 2.0 * support - 0.8 * aspect_pen + 0.4 * ratio + 0.8 * fill + extra - 0.3 * near \
                - (0.15 if kind == "minrect" else 0)
            if score > best_score:
                best, best_score = (q / scale, f"{kind}/{src}", ratio, support), score
        return best

    best = pick(cands, False)
    if (best is None or best[3] < 0.5 or best[2] < 0.25) and not border_is_paper:
        # dự phòng: mép trang dính vào giấy/sách cùng màu -> ghép tứ giác từ các đường thẳng dài
        alt = pick(line_candidates(gray), True)
        if alt is not None:
            best = alt
    if border_is_paper:
        # viền ảnh toàn màu giấy: hoặc ảnh đã là trang (app quét), hoặc trang nằm trên nền sáng gần màu giấy.
        # Chỉ nhận tứ giác khi nó rõ ràng nhỏ hơn khung và có biên mạnh; nếu không thì coi ảnh đã là trang.
        if best is None or not 0.4 <= best[2] <= 0.8 or best[3] < 0.6 or quad_skew(best[0]) > 20:
            return "page"
    if best is None or best[3] < 0.5:                    # không có tứ giác nào có đủ 4 cạnh rõ
        return None
    return best[:3]


# ------------------------------------------------------------------ nắn và tăng cường
def warp_a4(img, quad, out_w=2480):
    """Biến đổi phối cảnh tứ giác về hình chữ nhật tỷ lệ A4 (dọc hoặc ngang theo tứ giác)."""
    wq = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
    hq = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
    if hq >= wq:
        W, H = out_w, int(round(out_w * A4))
    else:
        W, H = int(round(out_w * A4)), out_w
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    return cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def bbox_crop(img, quad, pad=0.01):
    x0, y0 = quad.min(0)
    x1, y1 = quad.max(0)
    h, w = img.shape[:2]
    px, py = pad * w, pad * h
    x0, y0 = int(max(0, x0 - px)), int(max(0, y0 - py))
    x1, y1 = int(min(w, x1 + px)), int(min(h, y1 + py))
    return img[y0:y1, x0:x1]


def normalize_light(img):
    """Chia ảnh xám cho nền (ảnh đã xoá nét nhạc bằng phép đóng và làm mờ) -> nền trắng đều, bỏ bóng đổ."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    k = max(15, img.shape[1] // 60) | 1
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 2)
    out = np.clip(gray / np.maximum(bg, 1) * 255.0, 0, 255)
    # kéo giãn tương phản: điểm tối 1% -> 0, nền -> 255
    lo = np.percentile(out, 1)
    out = np.clip((out - lo) * 255.0 / max(1, 250 - lo), 0, 255)
    return out.astype(np.uint8)


def sauvola(gray, window=None, k=0.2, R=128):
    """Nhị phân hoá Sauvola bằng ảnh tích phân (không cần scikit-image)."""
    if window is None:
        window = max(15, gray.shape[1] // 80) | 1
    g = gray.astype(np.float64)
    mean = cv2.boxFilter(g, -1, (window, window), borderType=cv2.BORDER_REFLECT)
    sq = cv2.boxFilter(g * g, -1, (window, window), borderType=cv2.BORDER_REFLECT)
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    thr = mean * (1 + k * (std / R - 1))
    return np.where(g > thr, 255, 0).astype(np.uint8)


# ------------------------------------------------------------------ chạy
def collect(inputs):
    files = []
    for p in inputs:
        if os.path.isdir(p):
            files += [f for f in sorted(glob.glob(os.path.join(p, "*"))) if f.lower().endswith(EXTS)]
        elif os.path.isfile(p):
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inputs", nargs="+", required=True, help="ảnh hoặc thư mục ảnh")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", nargs="+", default=["rect", "norm", "bin", "bbox"],
                    choices=["rect", "norm", "bin", "bbox"])
    ap.add_argument("--width", type=int, default=2480, help="chiều rộng ảnh nắn (2480 px = A4 ở 300 dpi)")
    ap.add_argument("--debug", action="store_true", help="lưu ảnh có vẽ tứ giác tìm được")
    ap.add_argument("--min-ratio", type=float, default=0.25,
                    help="tứ giác chiếm ít hơn tỷ lệ này của ảnh thì coi là không tìm được trang")
    a = ap.parse_args()

    files = collect(a.inputs)
    if not files:
        sys.exit("Không tìm thấy ảnh.")
    for s in a.steps + (["debug"] if a.debug else []):
        os.makedirs(os.path.join(a.out, s), exist_ok=True)
    rows = []
    for i, f in enumerate(files, 1):
        stem = os.path.splitext(os.path.basename(f))[0]
        t0 = time.perf_counter()
        img = load(f)
        found = find_page(img)
        warn = ""
        if isinstance(found, str):                      # ảnh đã là trang giấy
            h, w = img.shape[:2]
            quad = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
            method, ratio = "already_page", 1.0
        elif found is None or found[2] < a.min_ratio:
            # không tìm được trang: giữ nguyên ảnh để engine vẫn có đầu vào, ghi cảnh báo
            h, w = img.shape[:2]
            quad = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
            method, ratio, warn = "none", 1.0, "không tìm được trang, dùng cả ảnh"
        else:
            quad, method, ratio = found
        # độ lệch góc lớn nhất giữa các cạnh đối diện: đo mức méo phối cảnh
        def ang(p, q):
            return np.degrees(np.arctan2(q[1] - p[1], q[0] - p[0]))
        skew = max(abs(ang(quad[0], quad[1]) - ang(quad[3], quad[2])),
                   abs(ang(quad[0], quad[3]) - ang(quad[1], quad[2])))
        rect = warp_a4(img, quad, a.width) if any(s in a.steps for s in ("rect", "norm", "bin")) else None
        if "rect" in a.steps:
            cv2.imwrite(os.path.join(a.out, "rect", stem + ".jpg"), rect, JPG)
        if "norm" in a.steps or "bin" in a.steps:
            norm = normalize_light(rect)
            if "norm" in a.steps:
                cv2.imwrite(os.path.join(a.out, "norm", stem + ".jpg"), norm, JPG)
            if "bin" in a.steps:
                cv2.imwrite(os.path.join(a.out, "bin", stem + ".png"), sauvola(norm))
        if "bbox" in a.steps:
            cv2.imwrite(os.path.join(a.out, "bbox", stem + ".jpg"), bbox_crop(img, quad), JPG)
        if a.debug:
            sc = 1200 / max(img.shape[:2])
            dbg = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            cv2.polylines(dbg, [(quad * sc).astype(np.int32)], True, (0, 0, 255) if warn else (0, 200, 0), 4)
            cv2.putText(dbg, f"{method} {ratio:.2f}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            cv2.imwrite(os.path.join(a.out, "debug", stem + ".jpg"), dbg, [cv2.IMWRITE_JPEG_QUALITY, 85])
        sec = time.perf_counter() - t0
        rows.append({"file": os.path.basename(f), "method": method, "area_ratio": round(ratio, 3),
                     "skew_deg": round(float(skew), 1), "seconds": round(sec, 2), "warning": warn,
                     "quad": ";".join(f"{x:.0f},{y:.0f}" for x, y in quad)})
        print(f"{i}/{len(files)} {stem}: {method} diện tích {ratio:.2f} lệch {skew:.1f}° {sec:.1f}s {warn}")
    with open(os.path.join(a.out, "report.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n_bad = sum(1 for r in rows if r["warning"])
    print(f"Xong {len(rows)} ảnh; {n_bad} ảnh không tìm được trang. Báo cáo: {os.path.join(a.out, 'report.csv')}")


if __name__ == "__main__":
    main()
