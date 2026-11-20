import cv2, numpy as np
from rv2 import segs, seg_geom, music_filter
from staff import ink_map, interline_gray

TW, TH = 45, 100   # template size at il=10: 4.5 il wide, 10 il high (staff 4 il + 3 il above/below)

def find_staves_rect(g):
    """On a rectified (staff lines ~horizontal) gray image: list of (x0, x1, ytop, il)."""
    ink = ink_map(g); sp, th = interline_gray(ink)
    if not sp: return [], None
    il = sp + th
    L = segs(g); ln, ang, mid = seg_geom(L)
    da = np.abs((ang + 90) % 180 - 90)
    m = (ln > 2 * il) & (da < 3)
    L = L[m]
    if len(L) < 10: return [], il
    k = music_filter(L, il); L = L[k]
    if len(L) < 10: return [], il
    h, w = g.shape
    cov = np.zeros(h)
    for x0, y0, x1, y1 in L:
        y = int(round((y0 + y1) / 2))
        if 0 <= y < h: cov[y] += abs(x1 - x0)
    cov = np.convolve(cov, np.ones(3), 'same')
    # line rows: local maxima with coverage > 15% of width
    rows = [y for y in range(1, h - 1) if cov[y] >= cov[y - 1] and cov[y] > cov[y + 1] and cov[y] > 0.15 * w]
    # merge rows closer than il/2
    lines = []
    for y in rows:
        if lines and y - lines[-1] < 0.5 * il: 
            if cov[y] > cov[lines[-1]]: lines[-1] = y
        else: lines.append(y)
    # group into staves of 5 with spacing ~ il
    st = []; i = 0
    while i + 4 < len(lines):
        gaps = np.diff(lines[i:i + 5])
        if np.all(np.abs(gaps - il) < 0.35 * il):
            yt, yb = lines[i], lines[i + 4]
            sel = [(x0, x1) for x0, y0, x1, y1 in L if yt - 0.5 * il <= (y0 + y1) / 2 <= yb + 0.5 * il]
            xs0 = np.array([min(a, b) for a, b in sel]); xs1 = np.array([max(a, b) for a, b in sel])
            st.append((float(np.percentile(xs0, 2)), float(np.percentile(xs1, 98)), float(yt), float(np.mean(gaps))))
            i += 5
        else:
            i += 1
    return st, il

def crop_end(ink, x, yt, il, side):
    """side='L': window starting at staff start; 'R': window ending at staff end, rotated 180."""
    s = 10.0 / il
    w = int(round(4.5 * il)); hh = int(round(10 * il))
    y0 = int(round(yt - 3 * il))
    if side == 'L': x0 = int(round(x - 0.3 * il))
    else: x0 = int(round(x - 4.5 * il + 0.3 * il))
    H, W = ink.shape
    pad = cv2.copyMakeBorder(ink, hh, hh, w, w, cv2.BORDER_CONSTANT, value=0)
    c = pad[y0 + hh:y0 + 2 * hh, x0 + w:x0 + 2 * w]
    c = cv2.resize(c, (TW, TH), interpolation=cv2.INTER_AREA).astype(np.float32)
    if side == 'R': c = c[::-1, ::-1]
    return c

def ncc(a, B):
    """a: (h,w); B: (n,h,w) -> max normalised cross-correlation (no shift)."""
    a = (a - a.mean()) / (a.std() + 1e-6)
    Bn = (B - B.mean((1, 2), keepdims=True)) / (B.std((1, 2), keepdims=True) + 1e-6)
    return float(((Bn * a).mean((1, 2))).max())

def ncc_shift(a, B, sh=3):
    best = -1
    for dx in range(-sh, sh + 1, 1):
        for dy in range(-sh, sh + 1, 2):
            aa = np.roll(np.roll(a, dx, 1), dy, 0)
            best = max(best, ncc(aa, B))
    return best

def refine_ends(ink, x0, x1, yt, il):
    H, W = ink.shape
    rows = [int(round(yt + k * il)) for k in range(5)]
    P = np.zeros(W)
    for y in rows:
        if 1 <= y < H - 1:
            P += (ink[y - 1:y + 2].max(0) > 60)
    P = np.convolve(P, np.ones(3) / 3, 'same')
    ok = P >= 3.5
    xs = int(np.clip(x0, 0, W - 1)); xe = int(np.clip(x1, 0, W - 1))
    gap = int(il)
    a = xs
    while a > 0 and ok[max(0, a - gap):a].any():
        a -= 1
        while a > 0 and ok[a - 1]: a -= 1
        if not ok[max(0, a - gap):a].any(): break
    b = xe
    while b < W - 1 and ok[b + 1:min(W, b + 1 + gap)].any():
        b += 1
        while b < W - 1 and ok[b + 1]: b += 1
        if not ok[b + 1:min(W, b + 1 + gap)].any(): break
    return float(a), float(b)

def find_staves_profile(g):
    ink = ink_map(g); sp, th = interline_gray(ink)
    if not sp: return [], None, ink
    il = sp + th
    H, W = ink.shape
    out = []
    # profile per vertical band (3 bands) to tolerate slight rotation/curl; take centre band for detection
    xa, xb = int(0.3 * W), int(0.7 * W)
    P = ink[:, xa:xb].astype(np.float32).mean(1)
    best = None
    for f in np.linspace(0.85, 1.15, 13):
        l = il * f
        idx = np.arange(H)
        on = np.min(np.stack([P[np.clip((idx + k * l).round().astype(int), 0, H - 1)] for k in range(5)]), 0)
        off = np.mean(np.stack([P[np.clip((idx + k * l + l / 2).round().astype(int), 0, H - 1)] for k in range(4)]), 0)
        c = on - off
        if best is None: best, bl = c, np.full(H, l)
        else:
            m = c > best; best[m] = c[m]; bl[m] = l
    thr = 0.35 * np.percentile(best, 99.5)
    win = int(3 * il)
    mx = cv2.dilate(best.reshape(-1, 1), np.ones((2 * win + 1, 1))).ravel()
    ys = np.where((best >= mx) & (best > thr))[0]
    for y in ys:
        l = bl[y]
        a, b = refine_ends(ink, W / 2, W / 2, y, l)
        if b - a > 0.25 * W:
            out.append((a, b, float(y), float(l)))
    return out, il, ink
