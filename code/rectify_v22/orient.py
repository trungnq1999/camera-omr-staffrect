import cv2, numpy as np

def binarize(gray):
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    b = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 6)
    return b

def line_masks(b, frac=25):
    h, w = b.shape
    L = max(w, h) // frac
    hm = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1)))
    vm = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, L)))
    return hm, vm

def resize(img, long=1600):
    s = long / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s

def rot_img(b, ang):
    h, w = b.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return cv2.warpAffine(b, M, (w, h), flags=cv2.INTER_NEAREST)

def profile_score(b, angles):
    best = 0
    for a in angles:
        r = rot_img(b, a)
        p = r.sum(1).astype(np.float64)
        if p.sum() == 0: continue
        dp = np.diff(p)
        best = max(best, (dp ** 2).sum() / (p.sum() ** 2 / len(p) + 1e-9))
    return best

def h_vs_v(b, tiles=4):
    """log ratio of horizontal-line evidence to vertical-line evidence, tile vote."""
    h, w = b.shape
    votes = []
    th, tw = h // tiles, w // tiles
    for i in range(tiles):
        for j in range(tiles):
            t = b[i*th:(i+1)*th, j*tw:(j+1)*tw]
            if t.mean() < 255*0.02: continue
            sh = profile_score(t, np.arange(-6, 6.1, 1.5))
            sv = profile_score(np.ascontiguousarray(t.T), np.arange(-6, 6.1, 1.5))
            votes.append(np.log((sh+1e-9)/(sv+1e-9)))
    return float(np.median(votes)) if votes else 0.0, len(votes)

def deskew_angle(b, rng=6, step=0.5):
    best, ba = -1, 0
    small = cv2.resize(b, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    for a in np.arange(-rng, rng + 1e-6, step):
        r = rot_img(small, a); p = r.sum(1).astype(np.float64); dp = np.diff(p)
        v = (dp ** 2).sum()
        if v > best: best, ba = v, a
    return ba

def staves(b):
    h, w = b.shape
    hm = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 30), 1)))
    band = cv2.dilate(hm, cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, w // 40), max(1, h // 120))))
    band = cv2.morphologyEx(band, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, w // 20), max(1, h // 60))))
    n, lab, st, _ = cv2.connectedComponentsWithStats(band)
    out = []
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        if ww > 0.3 * w and hh < 0.2 * h and hh > h / 150:
            out.append((x, y, ww, hh))
    return out, hm

def updown_score(b):
    ang = deskew_angle(b)
    r = rot_img(b, ang)
    sts, hm = staves(r)
    ink = cv2.subtract(r, hm)
    sc = []
    for x, y, ww, hh in sts:
        k = max(4, int(0.08 * ww))
        L = float(ink[y:y + hh, x:x + k].sum()); R = float(ink[y:y + hh, x + ww - k:x + ww].sum())
        if L + R > 0: sc.append((L - R) / (L + R))
    return (float(np.mean(sc)) if sc else 0.0), len(sts)

def interline(b):
    """Most common vertical white run between black runs (staff space) and black run (line thickness)."""
    h, w = b.shape
    cols = b[:, ::max(1, w // 300)] > 0
    whites, blacks = [], []
    for c in cols.T:
        d = np.diff(np.concatenate([[0], c.astype(np.int8), [0]]))
        s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
        if len(s) < 3: continue
        blacks += list(e - s)
        whites += list(s[1:] - e[:-1])
    if not whites: return None, None
    wb = np.bincount(np.clip(whites, 0, 200)); bb = np.bincount(np.clip(blacks, 0, 200))
    wb[:2] = 0
    return int(np.argmax(wb)), int(np.argmax(bb))
