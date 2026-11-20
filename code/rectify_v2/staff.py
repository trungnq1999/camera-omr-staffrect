import cv2, numpy as np

def ink_map(gray):
    """Ink strength: background (max filter, smoothed) minus gray, normalised to 0..255."""
    bg = cv2.dilate(gray, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    bg = cv2.GaussianBlur(bg, (0, 0), 8)
    d = cv2.subtract(bg, gray).astype(np.float32)
    d = d / max(1.0, np.percentile(d, 99.5)) * 255
    return np.clip(d, 0, 255).astype(np.uint8)

def interline_gray(ink):
    b = (ink > 60).astype(np.uint8)
    h, w = b.shape
    cols = b[:, ::max(1, w // 300)]
    whites, blacks = [], []
    for c in cols.T:
        d = np.diff(np.concatenate([[0], c.astype(np.int8), [0]]))
        s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
        if len(s) < 3: continue
        blacks += list(e - s); whites += list(s[1:] - e[:-1])
    if not whites: return None, None
    wb = np.bincount(np.clip(whites, 0, 300)); wb[:2] = 0
    bb = np.bincount(np.clip(blacks, 0, 300))
    return int(np.argmax(wb)), int(max(1, np.argmax(bb)))

def line_mask(ink, il):
    """Horizontal staff-line pixels: long horizontal mean stays dark, and darker than il/2 above & below."""
    L = max(9, int(3 * il)) | 1
    hmean = cv2.blur(ink.astype(np.float32), (L, 1))
    k = max(2, int(round(il / 2)))
    up = np.roll(hmean, k, 0); dn = np.roll(hmean, -k, 0)
    ridge = hmean - np.maximum(up, dn)
    m = (ridge > 25) & (hmean > 50)
    return (m * 255).astype(np.uint8)

def staves(lm, il, w_frac=0.25):
    h, w = lm.shape
    sm = cv2.morphologyEx(lm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (6 * il, 1)))
    band = cv2.morphologyEx(sm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(1.6 * il))))
    band = cv2.morphologyEx(band, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (4 * il, int(2.5 * il))))
    n, lab, st, _ = cv2.connectedComponentsWithStats(band)
    out = []
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        if ww > w_frac * w and 3.0 * il < hh < 6.5 * il:
            out.append((x, y, ww, hh, i))
    return out, lab
