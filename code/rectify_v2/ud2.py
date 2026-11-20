import cv2, numpy as np
from orient import binarize, interline, deskew_angle, rot_img

def prep(gray):
    s = 2000 / max(gray.shape[:2])
    g = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    b = binarize(g)
    a = deskew_angle(b)
    return rot_img(b, a)

def staff_lines(b):
    h, w = b.shape
    sp, th = interline(b)
    if not sp: return None, None, None
    hm = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, 4 * sp), 1)))
    return hm, sp, th

def find_staves(b, hm, sp, th):
    h, w = b.shape
    il = sp + th
    sm = cv2.morphologyEx(hm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (8 * il, 1)))
    band = cv2.morphologyEx(sm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(1.5 * il))))
    band = cv2.morphologyEx(band, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (4 * il, int(2.5 * il))))
    n, lab, st, _ = cv2.connectedComponentsWithStats(band)
    out = []
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        if ww > 0.25 * w and 3.0 * il < hh < 6.5 * il and a > 0.5 * ww * 3 * il:
            out.append((x, y, ww, hh))
    return out

def end_score(b, dbg=False):
    hm, sp, th = staff_lines(b)
    if hm is None: return 0.0, 0
    h, w = b.shape
    ink = cv2.subtract(b, hm)
    # group staff line pixels into staves: close vertically by ~1.5 sp
    sc = []
    k = 3 * (sp + th)
    for x, y, ww, hh in find_staves(b, hm, sp, th):
        x0, x1 = x, x + ww - 1
        y0, y1 = max(0, y - 2 * sp), min(h, y + hh + 2 * sp)
        Lo = float(ink[y0:y1, max(0, x0 - k):x0].sum()); Ro = float(ink[y0:y1, x1 + 1:min(w, x1 + 1 + k)].sum())
        Li = float(ink[y0:y1, x0:x0 + k].sum()); Ri = float(ink[y0:y1, max(0, x1 - k):x1].sum())
        L, R = Lo + Li, Ro + Ri
        if L + R > 0: sc.append((L - R) / (L + R))
    return (float(np.median(sc)) if sc else 0.0), len(sc)
