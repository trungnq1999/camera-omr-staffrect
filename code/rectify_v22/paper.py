import cv2, numpy as np

def bg_stats(bgr, ink, mid, il):
    """Median V and S of non-ink pixels around each segment midpoint (box +-1.5 il)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    V = hsv[:, :, 2].astype(np.float32); S = hsv[:, :, 1].astype(np.float32); Hh = hsv[:, :, 0].astype(np.float32)
    V = np.where(ink < 40, V, np.nan); S = np.where(ink < 40, S, np.nan); Hh = np.where(ink < 40, Hh, np.nan)
    h, w = V.shape; r = max(3, int(1.5 * il))
    out = np.zeros((len(mid), 3), np.float32)
    for i, (x, y) in enumerate(mid.astype(int)):
        y0, y1 = max(0, y - r), min(h, y + r + 1); x0, x1 = max(0, x - r), min(w, x + r + 1)
        v = V[y0:y1, x0:x1]; s_ = S[y0:y1, x0:x1]; hh_ = Hh[y0:y1, x0:x1]
        ok = np.isfinite(v).any()
        out[i] = (np.nanmedian(v) if ok else 0, np.nanmedian(s_) if ok else 255, np.nanmedian(hh_) if ok else 0)
    return out

def paper_mask_seg(bgr, ink, mid, il):
    st = bg_stats(bgr, ink, mid, il)
    V, S, Hh = st[:, 0], st[:, 1], st[:, 2]
    p = V - 1.5 * S
    ref = np.percentile(p, 90) if len(p) else 0
    bright_white = p > ref - 60                       # bright and unsaturated: paper in normal light
    orange = (Hh >= 5) & (Hh <= 35) & (S > np.percentile(S, 10) + 8)
    dark = V < 0.35 * np.percentile(V, 90)
    # paper in a (bluish) shadow: not orange-ish and not dark. Wood: orange-ish and fails the bright-white test.
    return bright_white | (~orange & ~dark), p
