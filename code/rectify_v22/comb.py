import cv2, numpy as np
from staff import ink_map, interline_gray

def strip_profiles(ink, sw):
    h, w = ink.shape
    xs = list(range(0, w - sw + 1, sw // 2))
    P = np.stack([ink[:, x:x + sw].mean(1) for x in xs], 1)  # h x nstrips
    return P, np.array(xs) + sw // 2

def comb_response(P, il):
    """C[y, s]: 5 equally spaced dark rows starting at y, contrasted with the 4 gaps between them."""
    h = P.shape[0]
    on = np.zeros_like(P); off = np.zeros_like(P)
    half = il / 2
    idx = np.arange(h)
    for k in range(5):
        on += P[np.clip((idx + k * il).round().astype(int), 0, h - 1)]
    for k in range(4):
        off += P[np.clip((idx + k * il + half).round().astype(int), 0, h - 1)]
    # min-on: all 5 lines must be present
    mn = np.min(np.stack([P[np.clip((idx + k * il).round().astype(int), 0, h - 1)] for k in range(5)]), 0)
    return np.minimum(on / 5 - off / 4, mn - off / 4)

def detect(gray, long=2000):
    s = long / max(gray.shape[:2])
    g = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ink = ink_map(g)
    sp, th = interline_gray(ink)
    if not sp: return None
    il0 = sp + th
    sw = max(8, int(2.5 * il0))
    P, xc = strip_profiles(ink, sw)
    best = None
    for f in (0.75, 0.85, 1.0, 1.15, 1.3):
        C = comb_response(P, il0 * f)
        best = C if best is None else np.maximum(best, C)
    return dict(g=g, ink=ink, il=il0, sp=sp, th=th, C=best, xc=xc, sw=sw, scale=s)

def strength(gray):
    """Overall staff evidence: mean of top-5% comb responses."""
    d = detect(gray)
    if d is None: return 0.0
    c = d['C']
    return float(np.mean(np.sort(c.ravel())[-max(1, c.size // 50):]))

def tracks(d, rel=0.35, min_frac=0.2):
    C, il, xc = d['C'], d['il'], d['xc']
    h, ns = C.shape
    top = np.sort(C.ravel())[-max(1, C.size // 50):].mean()
    T = rel * top
    peaks = []
    win = int(3 * il)
    for s in range(ns):
        c = C[:, s]
        mx = cv2.dilate(c.reshape(-1, 1), np.ones((2 * win + 1, 1))).ravel()
        ys = np.where((c >= mx) & (c > T))[0]
        peaks.append(list(ys))
    # link greedily left->right
    tr = []  # each: dict(s=[...], y=[...])
    active = []
    for s in range(ns):
        used = set()
        new_active = []
        for t in active:
            yl = t['y'][-1]
            cand = [y for y in peaks[s] if abs(y - yl) < 0.7 * il and y not in used]
            if cand:
                y = min(cand, key=lambda v: abs(v - yl)); used.add(y)
                t['s'].append(s); t['y'].append(y); t['gap'] = 0; new_active.append(t)
            elif t['gap'] < 3:  # allow small gaps
                t['gap'] += 1; new_active.append(t)
            else:
                tr.append(t)
        for y in peaks[s]:
            if y not in used:
                new_active.append(dict(s=[s], y=[y], gap=0))
        active = new_active
    tr += active
    W = d['g'].shape[1]
    out = []
    for t in tr:
        x0, x1 = xc[t['s'][0]], xc[t['s'][-1]]
        if x1 - x0 > min_frac * W and len(t['s']) > 0.5 * (t['s'][-1] - t['s'][0] + 1):
            out.append(dict(x=np.array([xc[s] for s in t['s']], float), y=np.array(t['y'], float), x0=x0, x1=x1))
    return out
