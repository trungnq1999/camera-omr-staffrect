"""Staff-guided rectification (v2 prototype)."""
import cv2, numpy as np
from comb import strength
from orient import binarize, h_vs_v, resize
from staff import ink_map, interline_gray

LSD = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)

def segs(g):
    L = LSD.detect(g)[0]
    if L is None: return np.zeros((0, 4), np.float32)
    return L.reshape(-1, 4)

def seg_geom(L):
    d = L[:, 2:] - L[:, :2]
    ln = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180
    mid = (L[:, :2] + L[:, 2:]) / 2
    return ln, ang, mid

def hline(L):
    p = np.c_[L[:, :2], np.ones(len(L))]; q = np.c_[L[:, 2:], np.ones(len(L))]
    l = np.cross(p, q)
    return l / np.linalg.norm(l[:, :2], axis=1, keepdims=True)

def vp_ransac(L, w, iters=400, tol_deg=0.6, rng=np.random.default_rng(0)):
    """Vanishing point (homogeneous) of segment set; returns vp, inlier mask."""
    n = len(L)
    if n < 5: return None, np.zeros(n, bool)
    lines = hline(L)
    ln, ang, mid = seg_geom(L)
    best, bm = None, None
    for _ in range(iters):
        i, j = rng.choice(n, 2, replace=False, p=w / w.sum())
        v = np.cross(lines[i], lines[j])
        if np.linalg.norm(v) < 1e-12: continue
        # angle between segment direction and direction from mid to vp
        if abs(v[2]) > 1e-9 * np.linalg.norm(v[:2]):
            vx, vy = v[0] / v[2], v[1] / v[2]
            dirs = np.c_[vx - mid[:, 0], vy - mid[:, 1]]
        else:
            dirs = np.tile(v[:2], (n, 1))
        a2 = np.degrees(np.arctan2(dirs[:, 1], dirs[:, 0])) % 180
        err = np.abs((a2 - ang + 90) % 180 - 90)
        m = err < tol_deg
        score = (w * m).sum()
        if best is None or score > best: best, bm = score, m
    if bm is None or bm.sum() < 3: return None, np.zeros(n, bool)
    # refine: least squares on inliers, weighted by length
    A = lines[bm] * np.sqrt(w[bm])[:, None]
    _, _, vt = np.linalg.svd(A)
    v = vt[-1]
    return v, bm

def music_filter(L, il):
    """Keep segments with a near-parallel partner at about il, 2il (staff structure)."""
    ln, ang, mid = seg_geom(L)
    keep = np.zeros(len(L), bool)
    if len(L) == 0: return keep
    from scipy.spatial import cKDTree
    t = cKDTree(mid)
    for i in range(len(L)):
        nb = t.query_ball_point(mid[i], r=max(ln[i] / 2, 2.5 * il))
        n = np.array([-np.sin(np.radians(ang[i])), np.cos(np.radians(ang[i]))])
        c = 0
        for j in nb:
            if j == i: continue
            da = abs((ang[j] - ang[i] + 90) % 180 - 90)
            if da > 3: continue
            dist = abs(np.dot(mid[j] - mid[i], n))
            r = dist / il
            if 0.75 < r < 1.3 or 1.75 < r < 2.3: c += 1
        keep[i] = c >= 2
    return keep

def dom_dir(L, w):
    ln, ang, mid = seg_geom(L)
    h = np.zeros(180)
    np.add.at(h, ang.astype(int) % 180, w)
    h = np.convolve(np.r_[h[-5:], h, h[:5]], np.ones(5), 'same')[5:-5]
    return float(np.argmax(h))

def music_region(mid, il, shape):
    """Mask of dense staff-segment area (closed, largest component), plus margin."""
    h, w = shape
    m = np.zeros(shape, np.uint8)
    for x, y in mid.astype(int):
        if 0 <= x < w and 0 <= y < h: m[y, x] = 255
    k = int(6 * il) | 1
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3 * k, 3 * k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2: return m
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return ((lab == i) * 255).astype(np.uint8)

def to_inh(v):
    return v / v[2] if abs(v[2]) > 1e-9 else None

def rectify_H(shape, v1, v2, f):
    """Homography that maps image -> fronto-parallel view, x along v1 direction, y along v2."""
    h, w = shape
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
    Ki = np.linalg.inv(K)
    d1 = Ki @ v1; d1 /= np.linalg.norm(d1)
    d2 = Ki @ v2; d2 /= np.linalg.norm(d2)
    # orthogonalise symmetric
    d2 = d2 - d1 * np.dot(d1, d2); d2 /= np.linalg.norm(d2)
    d3 = np.cross(d1, d2)
    if d3[2] < 0: d3 = -d3; d2 = -d2   # keep plane facing camera
    R = np.stack([d1, d2, d3], 1)       # columns: plane axes in camera coords
    return K @ R.T @ Ki                 # rotate camera to face plane

def orient_sign(L, v):
    """Make vanishing direction point consistently (+x for v1, +y for v2) wrt segment directions."""
    return v

def estimate_f(v1, v2, shape):
    h, w = shape
    p1, p2 = to_inh(v1), to_inh(v2)
    if p1 is None or p2 is None: return None
    c = np.array([w / 2, h / 2])
    f2 = -np.dot(p1[:2] - c, p2[:2] - c)
    return np.sqrt(f2) if f2 > 0 else None

def rectify(gray, work_long=2000, prior_f=0.67, margin=0.07, out_w=2480):
    """Returns dict(H=full-res homography to output, size=(W,H), ok, info...)"""
    s = work_long / max(gray.shape[:2])
    g = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    info = {}
    side = side_score(g); info['side'] = side
    R90 = np.eye(3)
    if side < 0:   # staff lines vertical: work on image rotated 90 deg counter-clockwise
        hh, ww = g.shape
        g = cv2.rotate(g, cv2.ROTATE_90_COUNTERCLOCKWISE)
        R90 = np.array([[0, 1, 0], [-1, 0, ww - 1], [0, 0, 1.0]])   # (x,y) -> (y, W-1-x)
    h, w = g.shape
    ink = ink_map(g); sp, th = interline_gray(ink)
    if not sp: return dict(ok=False, why='no_interline')
    il = sp + th
    L = segs(g)
    ln, ang, mid = seg_geom(L)
    L = L[ln > 2.5 * il]
    keep = music_filter(L, il)
    Ls = L[keep]
    if len(Ls) < 20: return dict(ok=False, why='few_staff_segs', n=len(Ls))
    ln, ang, mid = seg_geom(Ls)
    a0 = dom_dir(Ls, ln)
    info['dom'] = a0
    # staff segments: within 20 deg of dominant
    da = np.abs((ang - a0 + 90) % 180 - 90)
    st = da < 20
    Ls = Ls[st]
    ln, ang, mid = seg_geom(Ls)
    region = music_region(mid, il, (h, w))
    inr = region[np.clip(mid[:, 1].astype(int), 0, h - 1), np.clip(mid[:, 0].astype(int), 0, w - 1)] > 0
    Ls = Ls[inr]; ln = ln[inr]
    v1, m1 = vp_ransac(Ls, ln)
    if v1 is None: return dict(ok=False, why='no_vp1')
    info['n1'] = int(len(Ls)); info['in1'] = float(m1.mean())
    # perpendicular segments inside region
    L2 = L
    ln2, ang2, mid2 = seg_geom(L2)
    da2 = np.abs((ang2 - (a0 + 90) + 90) % 180 - 90)
    inr2 = region[np.clip(mid2[:, 1].astype(int), 0, h - 1), np.clip(mid2[:, 0].astype(int), 0, w - 1)] > 0
    sel = (da2 < 35) & inr2 & (ln2 > 2.5 * il)
    L2 = L2[sel]; ln2 = ln2[sel]
    v2 = None
    if len(L2) >= 8:
        v2, m2 = vp_ransac(L2, ln2, tol_deg=1.0)
        if v2 is not None: info['in2'] = float(m2.mean())
    info['n2'] = int(len(L2))
    if v2 is None:   # weak perspective: perpendicular direction at infinity
        v2 = np.array([-np.sin(np.radians(a0)), np.cos(np.radians(a0)), 0.0])
        info['v2'] = 'affine'
    f = estimate_f(v1, v2, (h, w)); info['f_est'] = None if f is None else f / max(h, w)
    fp = prior_f * max(h, w)
    if f is None or not (0.5 * fp < f < 2.0 * fp): f = fp
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]]); Ki = np.linalg.inv(K)
    d1 = Ki @ v1; d1 /= np.linalg.norm(d1)
    d2 = Ki @ v2; d2 /= np.linalg.norm(d2)
    # staff direction in image: dominant angle a0 -> choose sign of d1 so it points along +x of the
    # dominant orientation (with a0 in [0,180): vector (cos,sin)); d2 perpendicular "down" (rotated +90)
    u = np.array([np.cos(np.radians(a0)), np.sin(np.radians(a0))])
    if u[0] < 0: u = -u          # staff direction pointing right: upright input stays upright
    if d1[0] * u[0] + d1[1] * u[1] < 0: d1 = -d1
    un = np.array([-u[1], u[0]])
    if d2[0] * un[0] + d2[1] * un[1] < 0: d2 = -d2
    # symmetric orthogonalisation
    M = np.stack([d1, d2], 1)
    U, _, Vt = np.linalg.svd(M, full_matrices=False)
    M = U @ Vt
    d1, d2 = M[:, 0], M[:, 1]
    d3 = np.cross(d1, d2)
    R = np.stack([d1, d2, d3], 0)
    Hw = K @ R @ Ki
    # bbox of region in rectified coords
    cnts, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pts = np.vstack([c.reshape(-1, 2) for c in cnts]).astype(np.float32)
    pr = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), Hw).reshape(-1, 2)
    x0, y0 = pr.min(0); x1, y1 = pr.max(0)
    bw, bh = x1 - x0, y1 - y0
    mx = margin * bw; my = margin * bw
    x0, x1, y0, y1 = x0 - mx, x1 + mx, y0 - my, y1 + my
    sc = out_w / (x1 - x0)
    T = np.array([[sc, 0, -x0 * sc], [0, sc, -y0 * sc], [0, 0, 1]])
    Hfull = T @ Hw @ R90 @ np.diag([s, s, 1.0])
    size = (out_w, int(round((y1 - y0) * sc)))
    if not (0.2 < size[1] / size[0] < 3.0): return dict(ok=False, why='bad_size', size=size)
    info.update(il=il, f=f / max(h, w))
    return dict(ok=True, H=Hfull, size=size, info=info, s=s)


def side_score(g):
    """>0: staff lines horizontal; <0: vertical. Tile projection profiles + staff comb (dev: 0/192 errors)."""
    g14, _ = resize(g, 1400)
    st, _ = h_vs_v(binarize(g14))
    a = strength(g); b = strength(np.ascontiguousarray(g.T))
    return float(st + 0.25 * np.log((a + 1e-3) / (b + 1e-3)))
