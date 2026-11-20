#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_photo_dataset.py - Mo phong anh chup trang nhac (in laser A4 -> chup bang dien thoai).

Ke hoach (32 trang):
    ip12 (may chinh, vi du iPhone 12): sang, den_ban, nghieng, bong, nen_roi, scan_app  -> 32 x 6 = 192
    s21  (may phu,   vi du Galaxy S21): sang, nghieng                                   -> 32 x 2 =  64
    Tong: 256 anh

Ten file ra:  <ma trang>__<dieu kien>_<may>.jpg      vi du: brahms_118_2_p3__nghieng_s21.jpg
<ma trang> = ten file anh dau vao (bo duoi). Neu dau vao la PDF thi la <ten pdf>_p<so trang>.

Cach dung:
    python make_photo_dataset.py all --dir ./pages            # quet ca thu muc anh, ra thu muc moi
    python make_photo_dataset.py ./pages/brahms_118_2_p3.png  # chi mot anh
    python make_photo_dataset.py all --dir ./pages --out ./sim_out --jobs 4
    python make_photo_dataset.py all --dir ./pages --only sang,nghieng --phones s21
    python make_photo_dataset.py all --dir ./pages --scale 0.4 --limit 2     # chay thu nhanh

Thu vien: pip install numpy opencv-python pillow   (them pymupdf neu dau vao la PDF)
Moi anh ra deu co EXIF Software = "SIMULATED ..." de khong lan voi anh chup that.
Co file manifest.csv ghi: may, dieu kien, HDR, ty le trang trong khung, chuc nang quet...
"""
import argparse
import csv
import datetime as dt
import os
import shutil
import sys
import tempfile
import traceback
import zlib
from concurrent.futures import ProcessPoolExecutor, as_completed

import cv2
import numpy as np
from PIL import Image, ImageOps

PAGE_W, PAGE_H = 2480, 3508          # A4 @ 300 dpi
SCAN_W, SCAN_H = 1654, 2339          # A4 @ 200 dpi (kich thuoc ban quet cua app)
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

# ------------------------------------------------------------------ may anh
PHONES = {
    "ip12": dict(
        make="Apple", model="iPhone 12", size=(3024, 4032),
        wb=(1.01, 1.00, 0.985), contrast=1.04, sat=1.00, sharpen=0.35,
        blur=0.90, noise=1.0, jpeg=92, hdr=0.6,
        conds=["sang", "den_ban", "nghieng", "bong", "nen_roi", "scan_app"],
    ),
    "s21": dict(
        make="samsung", model="SM-G991B (Galaxy S21)", size=(3000, 4000),
        wb=(0.98, 1.00, 1.04), contrast=1.14, sat=1.15, sharpen=0.85,
        blur=0.85, noise=0.9, jpeg=91, hdr=0.5,
        conds=["sang", "nghieng"],
    ),
}

# ------------------------------------------------------------------ tinh huong
# area: ty le dien tich trang / khung hinh;  offset: do lech tam trang (ty le khung)
SCENES = {
    "sang": dict(
        bg=["wood_light", "laminate"], pitch=(-1.5, 1.5), yaw=(-1.5, 1.5), roll=(-2.5, 2.5),
        curl=(0.0, 0.10), area=(0.64, 0.78), light=["window_left"], target=0.84,
        cast=(1.02, 1.00, 0.97), blur_mul=1.0, motion=0, noise=0.006, vignette=0.20,
        depth_blur=0.0, shadow=(8, 16, 0.40)),
    "den_ban": dict(
        bg=["wood_dark"], pitch=(-2.5, 2.5), yaw=(-3, 3), roll=(-3, 3),
        curl=(0.15, 0.35), area=(0.62, 0.76), light=["desk_lamp"], target=0.60,
        cast=(1.10, 0.98, 0.78), blur_mul=1.35, motion=7, noise=0.024, vignette=0.45,
        depth_blur=0.0, shadow=(14, 26, 0.55)),
    "nghieng": dict(
        # theo kịch bản chụp: giấy PHẲNG, máy nghiêng 30-40 độ (trang cong để dành cho điều kiện riêng sau này)
        bg=["stand"], pitch=(30, 40), yaw=(-4, 4), roll=(-3, 3),
        curl=(0.0, 0.15), area=(0.64, 0.78), light=["stand"], target=0.72,
        cast=(1.04, 1.00, 0.92), blur_mul=1.05, motion=0, noise=0.012, vignette=0.30,
        depth_blur=0.9, shadow=(18, 30, 0.50)),
    "bong": dict(
        bg=["wood_light", "laminate"], pitch=(-3, 3), yaw=(-3, 3), roll=(-4, 4),
        curl=(0.0, 0.2), area=(0.64, 0.78), light=["window_left", "even"], target=0.84,
        cast=(1.02, 1.00, 0.97), blur_mul=1.0, motion=0, noise=0.007, vignette=0.22,
        depth_blur=0.0, shadow=(8, 16, 0.40), occluder=True),
    "nen_roi": dict(
        bg=["busy"], pitch=(-4, 4), yaw=(-4, 4), roll=(-10, 10),
        curl=(0.0, 0.25), area=(0.36, 0.52), light=["even", "window_left"], target=0.82,
        cast=(1.03, 1.00, 0.95), blur_mul=1.0, motion=0, noise=0.009, vignette=0.25,
        depth_blur=0.0, shadow=(10, 18, 0.45), offset=0.15),
    "scan_app": dict(   # anh chup dau vao cua app quet; sau do duoc nan phang + lam trang
        bg=["wood_light", "laminate", "wood_dark"], pitch=(-5, 5), yaw=(-5, 5), roll=(-7, 7),
        curl=(0.1, 0.4), area=(0.55, 0.74), light=["window_left", "even", "desk_lamp"],
        target=0.80, cast=(1.04, 1.00, 0.94), blur_mul=1.0, motion=0, noise=0.008,
        vignette=0.25, depth_blur=0.0, shadow=(10, 18, 0.45)),
}

SCAN_FUNCTIONS = {
    "color": "Mo phong iOS Ghi chu > Quet tai lieu (bo loc Mau)",
    "gray": "Mo phong iOS Ghi chu > Quet tai lieu (bo loc Xam)",
    "bw": "Mo phong iOS Ghi chu > Quet tai lieu (bo loc Den trang)",
}


# ================================================================== tien ich
def lin(x):
    return np.power(np.clip(x, 0, 1), 2.2)


def enc(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def lowfreq(rng, w, h, gw=6, gh=8):
    a = rng.random((gh, gw)).astype(np.float32)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def gauss2d(W, H, cx, cy, sx, sy):
    x = (np.arange(W, dtype=np.float32) - cx) / sx
    y = (np.arange(H, dtype=np.float32) - cy) / sy
    return np.exp(-0.5 * (y[:, None] ** 2 + x[None, :] ** 2)).astype(np.float32)


def rot_pts(c, w, h, ang):
    a = np.radians(ang)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return (pts @ R.T + np.array(c, dtype=np.float64)).astype(np.int32)


def local_pt(c, ang, x, y):
    a = np.radians(ang)
    return (int(c[0] + x * np.cos(a) - y * np.sin(a)), int(c[1] + x * np.sin(a) + y * np.cos(a)))


# ================================================================== in an
def simulate_print(gray, rng):
    """gray: HxW float 0..1 (1 = trang) -> HxWx3 phan xa tuyen tinh (giay + muc toner)."""
    h, w = gray.shape
    ink = 1.0 - gray
    ink = cv2.GaussianBlur(ink, (0, 0), 0.8)
    ink = np.clip(ink * 1.05, 0, 1)
    refl = 0.90 - ink * (0.90 - 0.055)
    tex = cv2.GaussianBlur(rng.standard_normal((h, w), dtype=np.float32), (0, 0), 1.3)
    refl *= 1.0 + 0.010 * tex / (tex.std() + 1e-6)
    refl *= 1.0 + 0.025 * (lowfreq(rng, w, h, 4, 5) - 0.5)
    tint = np.array([1.00, 0.985, 0.95], np.float32)
    return (refl[..., None] * tint[None, None, :]).astype(np.float32)


def curl_shading(page, curl):
    if curl <= 0.02:
        return page
    h, w = page.shape[:2]
    un = np.linspace(-1, 1, w, dtype=np.float32)
    vn = np.linspace(-1, 1, h, dtype=np.float32)
    shade = 1 - 0.20 * curl * un - 0.12 * curl * un ** 2
    shade = shade[None, :] * (1 - 0.05 * curl * vn[:, None] ** 2)
    return page * shade[..., None]


# ================================================================== hinh hoc
def project_grid(sc, W, H, rng, nx, ny, curl):
    us = np.linspace(-PAGE_W / 2, PAGE_W / 2, nx + 1)
    vs = np.linspace(-PAGE_H / 2, PAGE_H / 2, ny + 1)
    U, V = np.meshgrid(us, vs)
    z = -curl * PAGE_W * 0.045 * (1 - (2 * U / PAGE_W) ** 2)
    z += -curl * PAGE_H * 0.012 * (1 - (2 * V / PAGE_H) ** 2)

    roll = np.radians(rng.uniform(*sc["roll"]))
    pitch = np.radians(rng.uniform(*sc["pitch"]))
    yaw = np.radians(rng.uniform(*sc["yaw"]))
    x = U * np.cos(roll) - V * np.sin(roll)
    y = U * np.sin(roll) + V * np.cos(roll)
    y2 = y * np.cos(pitch) + z * np.sin(pitch)
    z2 = -y * np.sin(pitch) + z * np.cos(pitch)
    x3 = x * np.cos(yaw) + z2 * np.sin(yaw)
    z3 = -x * np.sin(yaw) + z2 * np.cos(yaw)

    D = 2.6 * max(PAGE_W, PAGE_H)
    zc = z3 + D
    px, py = x3 / zc, y2 / zc

    # dien tich da giac bien -> chon ti le de dat dung ty le trang/khung
    bx = np.concatenate([px[0, :], px[1:, -1], px[-1, -2::-1], px[-2:0:-1, 0]])
    by = np.concatenate([py[0, :], py[1:, -1], py[-1, -2::-1], py[-2:0:-1, 0]])
    area0 = 0.5 * abs(np.dot(bx, np.roll(by, -1)) - np.dot(by, np.roll(bx, -1)))
    bw, bh = px.max() - px.min(), py.max() - py.min()
    s = min(np.sqrt(rng.uniform(*sc["area"]) * W * H / area0), 0.96 * W / bw, 0.96 * H / bh)
    cx, cy = (px.max() + px.min()) / 2, (py.max() + py.min()) / 2
    mx = max(0.0, W / 2 - s * bw / 2 - 0.02 * W)
    my = max(0.0, H / 2 - s * bh / 2 - 0.02 * H)
    off = sc.get("offset", 0.03)
    jx = rng.uniform(-1, 1) * min(mx, off * W)
    jy = rng.uniform(-1, 1) * min(my, off * H)
    X = (px - cx) * s + W / 2 + jx
    Y = (py - cy) * s + H / 2 + jy
    SX, SY = U + PAGE_W / 2, V + PAGE_H / 2
    corners = np.array([[X[0, 0], Y[0, 0]], [X[0, -1], Y[0, -1]],
                        [X[-1, -1], Y[-1, -1]], [X[-1, 0], Y[-1, 0]]], np.float32)  # TL TR BR BL
    return SX, SY, X, Y, corners


def render_mesh(page, SX, SY, X, Y, W, H):
    canvas = np.zeros((H, W, 3), np.float32)
    mask = np.zeros((H, W), np.uint8)
    ny, nx = X.shape[0] - 1, X.shape[1] - 1
    for j in range(ny):
        for i in range(nx):
            s = np.float32([[SX[j, i], SY[j, i]], [SX[j, i + 1], SY[j, i + 1]],
                            [SX[j + 1, i + 1], SY[j + 1, i + 1]], [SX[j + 1, i], SY[j + 1, i]]])
            d = np.float32([[X[j, i], Y[j, i]], [X[j, i + 1], Y[j, i + 1]],
                            [X[j + 1, i + 1], Y[j + 1, i + 1]], [X[j + 1, i], Y[j + 1, i]]])
            x0 = max(int(np.floor(d[:, 0].min())) - 2, 0)
            y0 = max(int(np.floor(d[:, 1].min())) - 2, 0)
            x1 = min(int(np.ceil(d[:, 0].max())) + 3, W)
            y1 = min(int(np.ceil(d[:, 1].max())) + 3, H)
            if x1 <= x0 or y1 <= y0:
                continue
            dl = d - np.float32([x0, y0])
            M = cv2.getPerspectiveTransform(s, dl)
            patch = cv2.warpPerspective(page, M, (x1 - x0, y1 - y0), flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
            m = np.zeros((y1 - y0, x1 - x0), np.uint8)
            cv2.fillConvexPoly(m, np.round(dl).astype(np.int32), 255)
            m = cv2.dilate(m, np.ones((3, 3), np.uint8))
            sel = m > 0
            canvas[y0:y1, x0:x1][sel] = patch[sel]
            mask[y0:y1, x0:x1][sel] = 255
    return canvas, mask


# ================================================================== nen
def make_bg(kind, W, H, rng):
    """Tra ve nen sRGB float32 0..1."""
    sw, sh = max(8, W // 8), max(8, H // 8)
    low = cv2.resize(rng.random((9, 7)).astype(np.float32), (sw, sh), interpolation=cv2.INTER_CUBIC)
    g = rng.random((sh, sw)).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), sigmaX=45, sigmaY=2.2)
    g = (g - g.mean()) / (g.std() + 1e-6)
    base, lf, gr = {
        "wood_light": ((0.66, 0.52, 0.38), 0.14, 0.035),
        "wood_dark": ((0.36, 0.25, 0.17), 0.16, 0.04),
        "laminate": ((0.80, 0.80, 0.77), 0.05, 0.015),
        "stand": ((0.11, 0.11, 0.12), 0.10, 0.02),
    }[kind]
    f = 1.0 - lf / 2 + lf * (low - low.min()) / (np.ptp(low) + 1e-6) + gr * g
    f = cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC)
    return np.clip(f[..., None] * np.array(base, np.float32)[None, None, :], 0, 1).astype(np.float32)


PALETTE = [(200, 60, 50), (40, 90, 170), (230, 230, 225), (60, 150, 90),
           (220, 170, 40), (30, 30, 35), (150, 60, 140)]


def _col(rng):
    return tuple(int(v) for v in PALETTE[int(rng.integers(len(PALETTE)))])


def _plaid(w, h, rng):
    x = np.arange(w, dtype=np.float32)[None, :]
    y = np.arange(h, dtype=np.float32)[:, None]
    ang = rng.uniform(0, np.pi)
    xr = x * np.cos(ang) + y * np.sin(ang)
    yr = -x * np.sin(ang) + y * np.cos(ang)
    a = 0.5 + 0.5 * np.sin(2 * np.pi * xr / rng.uniform(60, 140))
    b = 0.5 + 0.5 * np.sin(2 * np.pi * yr / rng.uniform(40, 110))
    c1, c2, c3 = (rng.random(3).astype(np.float32) * 0.6 + 0.2 for _ in range(3))
    img = c1[None, None, :] + (c2 - c1)[None, None, :] * (a ** 4)[..., None] * 0.8 \
        + (c3 - c1)[None, None, :] * (b ** 4)[..., None] * 0.8
    img *= 1 + 0.08 * rng.standard_normal((h, w, 1), dtype=np.float32)
    return np.clip(img, 0, 1).astype(np.float32)


def _news(w, h, rng, cm):
    D = int(np.hypot(w, h)) + 4
    cv = np.full((D, D, 3), (222, 219, 208), np.uint8)
    lh = max(3, int(0.38 * cm))
    colw = max(20, int(6.5 * cm))
    gap = max(4, int(0.8 * cm))
    x = 0
    while x < D:
        y = 0
        while y < D:
            r = rng.random()
            if r < 0.07:
                hh = int(rng.uniform(1.2, 2.4) * cm)
                cv2.rectangle(cv, (x, y), (x + colw, y + hh), (35, 35, 38), -1)
                y += hh + lh
            elif r < 0.12:
                hh = int(rng.uniform(3, 5) * cm)
                gv = int(rng.integers(90, 170))
                cv2.rectangle(cv, (x, y), (x + colw, y + hh), (gv, gv, gv), -1)
                y += hh + lh
            else:
                ln = int(colw * rng.uniform(0.6, 1.0))
                cv2.line(cv, (x, y), (x + ln, y), (60, 60, 66), max(1, int(lh * 0.28)), cv2.LINE_AA)
                y += lh
        x += colw + gap
    M = cv2.getRotationMatrix2D((D / 2, D / 2), float(rng.uniform(0, 360)), 1.0)
    M[:, 2] += (w / 2 - D / 2, h / 2 - D / 2)
    out = cv2.warpAffine(cv, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out.astype(np.float32) / 255


# ---- vat the tren ban (ve tren lop uint8 RGB `L` va mat na `M`)
def obj_mug(L, M, c, cm, rng):
    r = int(rng.uniform(3.2, 4.2) * cm)
    col = _col(rng)
    a = rng.uniform(0, 2 * np.pi)
    hc = (int(c[0] + np.cos(a) * r), int(c[1] + np.sin(a) * r))
    for img, cc in ((L, col), (M, 255)):
        cv2.ellipse(img, hc, (int(r * 0.55), int(r * 0.42)), float(np.degrees(a)), -90, 90, cc,
                    max(2, int(0.8 * cm)), cv2.LINE_AA)
        cv2.circle(img, c, r, cc, -1, cv2.LINE_AA)
    cv2.circle(L, c, int(r * 0.84), (int(70 + rng.integers(40)), int(40 + rng.integers(20)), 25), -1, cv2.LINE_AA)
    cv2.circle(L, (c[0] - r // 3, c[1] - r // 3), max(2, int(r * 0.18)), (140, 100, 70), -1, cv2.LINE_AA)


def obj_pen(L, M, c, cm, rng):
    length = rng.uniform(12, 15) * cm
    a = rng.uniform(0, np.pi)
    d = np.array([np.cos(a), np.sin(a)])
    n = np.array([-d[1], d[0]])
    p0 = np.array(c, np.float64) - d * length / 2
    p1 = np.array(c, np.float64) + d * length / 2
    th = max(3, int(0.9 * cm))
    col = _col(rng)
    P = lambda p: (int(p[0]), int(p[1]))
    for img, cc in ((L, col), (M, 255)):
        cv2.line(img, P(p0), P(p1), cc, th, cv2.LINE_AA)
    cv2.line(L, P(p1 - d * 0.28 * length), P(p1), (25, 25, 28), th, cv2.LINE_AA)
    tip = np.array([p0 + n * th / 2, p0 - n * th / 2, p0 - d * th * 1.4]).astype(np.int32)
    cv2.fillConvexPoly(L, tip, (215, 185, 140))
    cv2.fillConvexPoly(M, tip, 255)


def obj_keys(L, M, c, cm, rng):
    cols, rows = int(rng.integers(7, 10)), int(rng.integers(3, 5))
    pitch = 1.9 * cm
    a = rng.uniform(-30, 30)
    base = rot_pts(c, cols * pitch + 0.8 * cm, rows * pitch + 0.8 * cm, a)
    cv2.fillConvexPoly(L, base, (38, 38, 42))
    cv2.fillConvexPoly(M, base, 255)
    kc = (205, 205, 208) if rng.random() < 0.5 else (75, 75, 82)
    for i in range(cols):
        for j in range(rows):
            lx, ly = (i - (cols - 1) / 2) * pitch, (j - (rows - 1) / 2) * pitch
            kp = rot_pts(local_pt(c, a, lx, ly), pitch * 0.86, pitch * 0.86, a)
            cv2.fillConvexPoly(L, kp, kc)


def obj_sticky(L, M, c, cm, rng):
    s = rng.uniform(6, 8) * cm
    a = rng.uniform(-35, 35)
    pts = rot_pts(c, s, s, a)
    col = [(250, 225, 90), (245, 150, 190), (150, 220, 150)][int(rng.integers(3))]
    cv2.fillConvexPoly(L, pts, col)
    cv2.fillConvexPoly(M, pts, 255)
    for k in range(4):
        y = (-0.3 + 0.2 * k) * s
        cv2.line(L, local_pt(c, a, -0.35 * s, y), local_pt(c, a, rng.uniform(0.05, 0.35) * s, y),
                 (90, 80, 60), 1, cv2.LINE_AA)


def obj_cable(L, M, c, cm, rng):
    P = np.array([(c[0] + rng.uniform(-9, 9) * cm, c[1] + rng.uniform(-9, 9) * cm) for _ in range(4)])
    t = np.linspace(0, 1, 80)[:, None]
    B = ((1 - t) ** 3) * P[0] + 3 * ((1 - t) ** 2) * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
    col = [(235, 235, 235), (25, 25, 25), (90, 90, 95)][int(rng.integers(3))]
    for img, cc in ((L, col), (M, 255)):
        cv2.polylines(img, [B.astype(np.int32)], False, cc, max(2, int(0.45 * cm)), cv2.LINE_AA)


def obj_book(L, M, c, cm, rng):
    w, h, a = rng.uniform(15, 19) * cm, rng.uniform(21, 26) * cm, rng.uniform(0, 180)
    col = _col(rng)
    pts = rot_pts(c, w, h, a)
    cv2.fillConvexPoly(L, pts, col)
    cv2.fillConvexPoly(M, pts, 255)
    cv2.fillConvexPoly(L, rot_pts(c, w * 0.6, h * 0.22, a), (235, 230, 215))


def obj_sheet(L, M, c, cm, rng):
    w, h, a = 21 * cm, 29.7 * cm, rng.uniform(-40, 40)
    pts = rot_pts(c, w, h, a)
    cv2.fillConvexPoly(L, pts, (235, 235, 230))
    cv2.fillConvexPoly(M, pts, 255)
    for k in range(16):
        y = (-0.42 + k * 0.055) * h
        x0 = -0.40 * w
        cv2.line(L, local_pt(c, a, x0, y), local_pt(c, a, x0 + rng.uniform(0.5, 0.8) * w, y),
                 (70, 70, 80), 1, cv2.LINE_AA)


def obj_coins(L, M, c, cm, rng):
    for _ in range(3):
        p = (int(c[0] + rng.uniform(-2, 2) * cm), int(c[1] + rng.uniform(-2, 2) * cm))
        r = max(3, int(rng.uniform(1.0, 1.3) * cm))
        cv2.circle(L, p, r, (190, 175, 120), -1, cv2.LINE_AA)
        cv2.circle(L, p, int(r * 0.7), (215, 200, 150), 1, cv2.LINE_AA)
        cv2.circle(M, p, r, 255, -1, cv2.LINE_AA)


OBJECTS = [obj_mug, obj_pen, obj_pen, obj_keys, obj_sticky, obj_cable, obj_cable, obj_book, obj_sheet, obj_coins]


def make_busy_bg(W, H, rng, quad, ppcm):
    """Nen roi: vai ca ro / bao / go + nhieu vat dung quanh trang. Tra ve sRGB float32."""
    ds = 2
    w, h = W // ds, H // ds
    cm = ppcm / ds
    style = ["plaid", "news", "wood"][int(rng.integers(3))]
    if style == "plaid":
        canvas = _plaid(w, h, rng)
    elif style == "news":
        canvas = _news(w, h, rng, cm)
    else:
        canvas = np.clip((make_bg("wood_light", w, h, rng) - 0.5) * 1.5 + 0.5, 0, 1)
    poly = quad.astype(np.float32).reshape(-1, 1, 2)
    n, placed, tries = int(rng.integers(8, 13)), 0, 0
    while placed < n and tries < 300:
        tries += 1
        cx, cy = rng.uniform(-0.03 * w, 1.03 * w), rng.uniform(-0.03 * h, 1.03 * h)
        if cv2.pointPolygonTest(poly, (float(cx * ds), float(cy * ds)), True) > -2.0 * ppcm:
            continue   # giu tam vat the cach mep trang >= 2 cm
        L = np.zeros((h, w, 3), np.uint8)
        M = np.zeros((h, w), np.uint8)
        OBJECTS[int(rng.integers(len(OBJECTS)))](L, M, (int(cx), int(cy)), cm, rng)
        mf = M.astype(np.float32) / 255
        sh = np.roll(np.roll(mf, int(0.5 * cm), axis=0), int(0.35 * cm), axis=1)
        sh = cv2.GaussianBlur(sh, (0, 0), max(1.0, 0.5 * cm))
        canvas = canvas * (1 - 0.5 * sh)[..., None]
        mb = cv2.GaussianBlur(mf, (0, 0), 0.8)[..., None]
        canvas = canvas * (1 - mb) + (L.astype(np.float32) / 255) * mb
        placed += 1
    canvas = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_CUBIC)
    canvas = cv2.GaussianBlur(canvas, (0, 0), 1.0)
    canvas += 0.015 * rng.standard_normal((H, W, 1), dtype=np.float32)
    return np.clip(canvas, 0, 1).astype(np.float32)


# ================================================================== anh sang
def illumination(kind, W, H, rng):
    x = np.arange(W, dtype=np.float32)[None, :] / W
    y = np.arange(H, dtype=np.float32)[:, None] / H
    lf = cv2.resize(rng.random((5, 4)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    if kind == "window_left":
        L = 0.78 + 0.26 * (1 - x) + 0.04 * y + 0.05 * (lf - 0.5)
    elif kind == "desk_lamp":
        hot = gauss2d(W, H, rng.uniform(0.2, 0.4) * W, rng.uniform(0.2, 0.4) * H, 0.50 * W, 0.45 * H)
        L = 0.22 + 1.00 * hot + 0.05 * (lf - 0.5)
        sh = np.zeros((H, W), np.float32)
        poly = np.array([[0.52 * W, -0.05 * H], [1.05 * W, -0.05 * H], [1.05 * W, 0.42 * H],
                         [0.86 * W, 0.34 * H], [0.66 * W, 0.16 * H]], np.int32)
        cv2.fillPoly(sh, [poly], 1.0)
        sh = cv2.GaussianBlur(sh, (0, 0), 0.05 * W)
        L = L * (1 - 0.55 * sh)
    elif kind == "even":
        L = 0.94 + 0.08 * gauss2d(W, H, 0.5 * W, 0.4 * H, 0.8 * W, 0.8 * H) + 0.03 * (lf - 0.5)
    elif kind == "stand":
        L = (0.55 + 0.42 * (1 - 0.5 * x)) * (0.62 + 0.38 * y) \
            + 0.15 * gauss2d(W, H, 0.4 * W, 0.7 * H, 0.5 * W, 0.4 * H) + 0.04 * (lf - 0.5)
    else:
        L = np.ones((H, W), np.float32)
    return L.astype(np.float32)


def occluder(W, H, rng):
    """Bong do cua dien thoai / ban tay / canh tay len trang. Tra ve (mat na 0..1, do toi)."""
    w4, h4 = max(8, W // 4), max(8, H // 4)
    sh = np.zeros((h4, w4), np.uint8)
    mode = ["phone", "arm", "both"][int(rng.integers(3))]
    if mode in ("phone", "both"):
        w, h = rng.uniform(0.30, 0.45) * w4, rng.uniform(0.40, 0.62) * h4
        c = (rng.uniform(0.2, 0.8) * w4, rng.uniform(0.1, 0.5) * h4)
        cv2.fillConvexPoly(sh, rot_pts(c, w, h, rng.uniform(-25, 25)), 255)
    if mode in ("arm", "both"):
        side = int(rng.integers(3))
        p0 = [(-0.05 * w4, rng.uniform(0.1, 0.9) * h4), (1.05 * w4, rng.uniform(0.1, 0.9) * h4),
              (rng.uniform(0.1, 0.9) * w4, -0.05 * h4)][side]
        p1 = (rng.uniform(0.3, 0.7) * w4, rng.uniform(0.3, 0.7) * h4)
        cv2.line(sh, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 255, int(0.17 * w4))
        cv2.circle(sh, (int(p1[0]), int(p1[1])), int(0.10 * w4), 255, -1)
    f = cv2.GaussianBlur(sh.astype(np.float32) / 255, (0, 0), rng.uniform(0.012, 0.04) * w4)
    return cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC), float(rng.uniform(0.60, 0.78))


def motion_kernel(length, angle):
    k = np.zeros((length, length), np.float32)
    c = length // 2
    dx, dy = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    cv2.line(k, (int(c - dx * c), int(c - dy * c)), (int(c + dx * c), int(c + dy * c)), 1.0, 1)
    return k / k.sum()


def apply_hdr(out, amt):
    """HDR nhe: nang vung toi, nen vung sang (kieu Smart HDR / Auto HDR)."""
    if amt <= 0:
        return out
    H, W = out.shape[:2]
    lum = out.mean(axis=2)
    small = cv2.resize(lum, (max(8, W // 16), max(8, H // 16)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 3)
    low = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
    lift = 1 + amt * 0.45 * np.clip(1 - low, 0, 1) ** 2
    out = np.clip(out * lift[..., None], 0, 1)
    return out - amt * 0.10 * np.clip(out - 0.85, 0, 1)


# ================================================================== render anh chup
def render_photo(page_gray, cond, phone, seed, hdr_on, scale):
    sc, ph = SCENES[cond], PHONES[phone]
    rng = np.random.default_rng(seed)
    W, H = (int(round(v * scale)) for v in ph["size"])
    bgk = str(rng.choice(sc["bg"]))
    light = str(rng.choice(sc["light"]))
    curl = float(rng.uniform(*sc["curl"]))

    page = curl_shading(simulate_print(page_gray, rng), curl)
    nx, ny = (20, 28) if curl > 0.05 else (4, 6)
    SX, SY, X, Y, corners = project_grid(sc, W, H, rng, nx, ny, curl)
    canvas, mask = render_mesh(page, SX, SY, X, Y, W, H)
    mf = (mask > 0).astype(np.float32)
    area = float(mf.mean())

    if bgk == "busy":
        ppcm = float(np.linalg.norm(corners[1] - corners[0])) / 21.0
        bg = make_busy_bg(W, H, rng, corners, ppcm)
    else:
        bg = make_bg(bgk, W, H, rng)
    bg = lin(bg)

    # bong do to giay len mat ban
    dx, dy, st = sc["shadow"]
    dx, dy = max(1, int(dx * scale)), max(1, int(dy * scale))
    sh = np.roll(np.roll(mf, dy, axis=0), dx, axis=1)
    sh = cv2.GaussianBlur(sh, (0, 0), dy * 1.2)
    bg = bg * (1 - st * sh)[..., None]
    m = cv2.GaussianBlur(mf, (0, 0), 1.1 * scale + 0.3)[..., None]
    scene = bg * (1 - m) + canvas * m

    # anh sang, bong vat can, can bang trang
    L = illumination(light, W, H, rng)
    if sc.get("occluder"):
        f, d = occluder(W, H, rng)
        L = L * (1 - d * f)
    cast = np.array(sc["cast"], np.float32) * np.array(ph["wb"], np.float32)
    scene = scene * L[..., None] * cast[None, None, :]

    # phoi sang theo vung giay (may do sang tren phan giay duoc chieu)
    k = max(3, int(25 * scale)) | 1
    inner = cv2.erode((mask > 0).astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    if inner.sum() < 100:
        inner = mask > 0
    scene *= sc["target"] / np.percentile(scene.mean(axis=2)[inner], 98)

    # quang hoc
    sig = max(0.3, ph["blur"] * sc["blur_mul"] * scale)
    if sc["depth_blur"] > 0:
        sharp = cv2.GaussianBlur(scene, (0, 0), sig)
        soft = cv2.GaussianBlur(scene, (0, 0), 3.6 * scale + 0.5)
        yy = np.arange(H, dtype=np.float32)[:, None] / H
        wgt = np.clip((0.58 - yy) / 0.58, 0, 1) ** 1.1 * sc["depth_blur"]
        wgt = np.broadcast_to(wgt, (H, W))[..., None]
        scene = sharp * (1 - wgt) + soft * wgt
    else:
        scene = cv2.GaussianBlur(scene, (0, 0), sig)
    mk = int(sc["motion"] * scale)
    if mk >= 3:
        scene = cv2.filter2D(scene, -1, motion_kernel(mk, rng.uniform(0, 180)))

    xs = (np.arange(W, dtype=np.float32) - W / 2) / (W / 2)
    ys = (np.arange(H, dtype=np.float32) - H / 2) / (H / 2)
    scene *= (1 - sc["vignette"] * (ys[:, None] ** 2 + xs[None, :] ** 2) / 2)[..., None]

    # tone map, bao hoa
    out = enc(scene)
    out = np.clip(0.5 + (out - 0.5) * ph["contrast"], 0, 1)
    gray = out.mean(axis=2, keepdims=True)
    out = np.clip(gray + (out - gray) * ph["sat"], 0, 1)
    out = apply_hdr(out, ph["hdr"] if hdr_on else 0.0)

    # nhieu cam bien (toi hon -> nhieu hon)
    n = sc["noise"] * ph["noise"]
    lum_n = cv2.GaussianBlur(rng.standard_normal((H, W), dtype=np.float32), (0, 0), 0.8)
    lum_n /= lum_n.std() + 1e-6
    chroma = cv2.resize(cv2.GaussianBlur(rng.standard_normal((H // 2, W // 2, 3), dtype=np.float32), (0, 0), 1.0),
                        (W, H), interpolation=cv2.INTER_LINEAR)
    chroma /= chroma.std() + 1e-6
    dark = 1.35 - out.mean(axis=2, keepdims=True)
    out = out + (n * lum_n[..., None] + 0.5 * n * chroma) * dark

    # lam net cua phan mem camera
    if ph["sharpen"] > 0:
        out = out + ph["sharpen"] * (out - cv2.GaussianBlur(out, (0, 0), 1.6 * max(scale, 0.5)))

    img = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img, dict(area=area, corners=corners, w=W, h=H, jpeg=ph["jpeg"])


# ================================================================== quet bang app
def make_scan(img, corners, rng, mode):
    """Mo phong app quet (Ghi chu / Tep cua iPhone): tu nhan goc -> nan phang -> lam trang."""
    c = corners.astype(np.float32).copy()
    ctr = c.mean(0)
    dims = np.array([np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[3] - c[0])])
    c = ctr + (c - ctr) * (1 + rng.uniform(-0.004, 0.008))      # khung quet hoi rong / hoi hep
    c += rng.normal(0, 0.0025, (4, 2)).astype(np.float32) * dims.mean()   # sai so nhan goc
    sc_pre = min(1.0, 1.25 * SCAN_W / dims[0])
    small = cv2.resize(img, None, fx=sc_pre, fy=sc_pre, interpolation=cv2.INTER_AREA)
    dst = np.float32([[0, 0], [SCAN_W - 1, 0], [SCAN_W - 1, SCAN_H - 1], [0, SCAN_H - 1]])
    Mx = cv2.getPerspectiveTransform(c * sc_pre, dst)
    w = cv2.warpPerspective(small, Mx, (SCAN_W, SCAN_H), flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE)

    f = w.astype(np.float32) / 255
    # uoc luong mau giay tung kenh (dong - dan no lam mat net nhac), chia de lam trang
    sm = cv2.resize(f, (SCAN_W // 4, SCAN_H // 4), interpolation=cv2.INTER_AREA)
    bgl = cv2.dilate(sm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    bgl = cv2.GaussianBlur(bgl, (0, 0), 12)
    bg = cv2.resize(bgl, (SCAN_W, SCAN_H), interpolation=cv2.INTER_CUBIC)
    norm = f / np.maximum(bg, 0.05)
    resid = bg.mean(axis=2) / max(float(np.percentile(bg.mean(axis=2), 95)), 1e-3)
    norm *= (0.88 + 0.12 * np.clip(resid, 0, 1.1))[..., None]        # con sot lai chut bong
    out = np.clip((norm - 0.10) / (0.97 - 0.10), 0, 1) ** 1.15
    if mode in ("gray", "bw"):
        out = np.repeat(out.mean(axis=2, keepdims=True), 3, axis=2)
    if mode == "bw":
        g8 = (out[..., 0] * 255).astype(np.uint8)
        bw = cv2.adaptiveThreshold(g8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 12)
        out = np.repeat((bw.astype(np.float32) / 255)[..., None], 3, axis=2)
    out = out + 0.006 * rng.standard_normal(out.shape, dtype=np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


# ================================================================== vao / ra
def load_page(path):
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("L")
    w, h = im.size
    s = min(PAGE_W / w, PAGE_H / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (PAGE_W, PAGE_H), 255)
    canvas.paste(im, ((PAGE_W - nw) // 2, (PAGE_H - nh) // 2))
    return np.asarray(canvas, np.float32) / 255.0


def make_exif(ph, cond, phone, hdr_on):
    ex = Image.Exif()
    ex[0x010F] = ph["make"]
    ex[0x0110] = ph["model"]
    ex[0x0131] = "SIMULATED by make_photo_dataset.py (khong phai anh chup that)"
    ex[0x0132] = dt.datetime.now().strftime("%Y:%m:%d %H:%M:%S")
    ex[0x010E] = "SIMULATED | cond=%s | phone=%s | hdr=%s" % (cond, phone, "on" if hdr_on else "off")
    return ex.tobytes()


def _init_worker():
    cv2.setNumThreads(1)


def process(task):
    page_id, path, phone, cond, out_dir, opt = task
    name = "%s__%s_%s" % (page_id, cond, phone)
    fp = os.path.join(out_dir, name + ".jpg")
    try:
        if opt["resume"] and os.path.exists(fp):
            return dict(status="skip", file=name + ".jpg")
        seed = (zlib.crc32(name.encode("utf-8")) ^ opt["seed"]) & 0xFFFFFFFF
        img, meta = render_photo(load_page(path), cond, phone, seed, opt["hdr"], opt["scale"])
        q = meta["jpeg"]
        area_pct = round(meta["area"] * 100, 1)
        scan_fn = ""
        if cond == "scan_app":
            img = make_scan(img, meta["corners"], np.random.default_rng(seed + 1), opt["scan_mode"])
            q, area_pct = 82, ""
            scan_fn = SCAN_FUNCTIONS[opt["scan_mode"]]
        ph = PHONES[phone]
        Image.fromarray(img).save(fp, quality=q, exif=make_exif(ph, cond, phone, opt["hdr"]))
        return dict(status="ok", file=name + ".jpg", page=page_id, condition=cond, phone=phone,
                    phone_model=ph["model"], width=img.shape[1], height=img.shape[0],
                    hdr="on" if opt["hdr"] else "off", page_area_pct=area_pct,
                    scan_function=scan_fn, seed=seed,
                    # toạ độ thật 4 góc trang (TL TR BR BL) trong ảnh ra: để đo sai số bước tìm trang
                    corners="" if cond == "scan_app" else ";".join("%.1f,%.1f" % (x, y) for x, y in meta["corners"]))
    except Exception:
        return dict(status="error", file=name + ".jpg", error=traceback.format_exc(limit=3))


def rasterize_pdf(pdf, tmp, stem):
    try:
        import fitz
    except ImportError:
        raise SystemExit("Dau vao la PDF: can  pip install pymupdf")
    out = []
    doc = fitz.open(pdf)
    for i, page in enumerate(doc):
        r = page.rect
        pix = page.get_pixmap(matrix=fitz.Matrix(PAGE_W / r.width, PAGE_H / r.height),
                              colorspace=fitz.csGRAY, alpha=False)
        fp = os.path.join(tmp, "%s_p%d.png" % (stem, i + 1))
        pix.save(fp)
        out.append(("%s_p%d" % (stem, i + 1), fp))
    doc.close()
    return out


def collect_inputs(args, out_dir, tmp):
    pages = []
    target = args.input
    if target.lower() == "all":
        folder = args.dir
    elif os.path.isdir(target):
        folder = target
    else:
        folder = None
    if folder is None:
        p = target if os.path.isfile(target) else os.path.join(args.dir, target)
        if not os.path.isfile(p):
            raise SystemExit("Khong tim thay anh dau vao: %s" % target)
        files = [p]
    else:
        files = []
        for root, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs
                       if os.path.abspath(os.path.join(root, d)) != os.path.abspath(out_dir)]
            for n in names:
                files.append(os.path.join(root, n))
            if not args.recursive:
                break
        files.sort()
    skipped = 0
    for p in files:
        stem, ext = os.path.splitext(os.path.basename(p))
        ext = ext.lower()
        if ext == ".pdf":
            pages += rasterize_pdf(p, tmp, stem)
        elif ext in IMG_EXT:
            if "__" in stem:        # co the la anh da mo phong
                skipped += 1
                continue
            pages.append((stem, p))
    if skipped:
        print("Bo qua %d file co '__' trong ten (co the la anh da mo phong)." % skipped)
    return pages


def unique_dir(path):
    if os.path.isdir(path) and os.listdir(path):
        path = path + "_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return path


def main():
    ap = argparse.ArgumentParser(description="Mo phong anh chup trang nhac theo 2 may, nhieu dieu kien.")
    ap.add_argument("input", help="'all' = quet ca thu muc (--dir), hoac duong dan 1 anh / 1 thu muc / 1 PDF")
    ap.add_argument("--dir", default=".", help="thu muc anh dau vao khi input = all (mac dinh: thu muc hien tai)")
    ap.add_argument("--out", help="thu muc anh ra (mac dinh: <ten thu muc>_sim); neu da co du lieu se them hau to thoi gian")
    ap.add_argument("--phones", default="ip12,s21", help="may can tao: ip12,s21")
    ap.add_argument("--only", help="chi mot so dieu kien, vi du sang,nghieng")
    ap.add_argument("--hdr", choices=["on", "off"], default="on", help="gia lap HDR bat/tat (mac dinh on)")
    ap.add_argument("--scan-mode", choices=["color", "gray", "bw"], default="color", help="bo loc cua app quet")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1), help="so tien trinh song song")
    ap.add_argument("--scale", type=float, default=1.0, help="ty le do phan giai anh ra (<1 de chay thu nhanh)")
    ap.add_argument("--limit", type=int, default=0, help="chi lay N trang dau (de chay thu)")
    ap.add_argument("--seed", type=int, default=0, help="doi seed de ra bo anh khac")
    ap.add_argument("--recursive", action="store_true", help="quet ca thu muc con")
    ap.add_argument("--resume", action="store_true", help="dung lai thu muc --out da co, bo qua anh da tao")
    args = ap.parse_args()

    base = args.dir if args.input.lower() == "all" else (
        args.input if os.path.isdir(args.input) else os.path.dirname(os.path.abspath(args.input)))
    default_out = os.path.join(os.getcwd(), os.path.basename(os.path.abspath(base)) + "_sim")
    out_dir = os.path.abspath(args.out or default_out)
    if not args.resume:
        out_dir = unique_dir(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    phones = [p.strip() for p in args.phones.split(",") if p.strip()]
    for p in phones:
        if p not in PHONES:
            raise SystemExit("May khong hop le: %s (chon: %s)" % (p, ", ".join(PHONES)))
    only = set(args.only.split(",")) if args.only else None

    tmp = tempfile.mkdtemp(prefix="pdfpages_")
    try:
        pages = collect_inputs(args, out_dir, tmp)
        if args.limit:
            pages = pages[:args.limit]
        if not pages:
            raise SystemExit("Khong co anh dau vao nao (dinh dang: %s)." % ", ".join(sorted(IMG_EXT)))

        opt = dict(hdr=args.hdr == "on", scale=args.scale, scan_mode=args.scan_mode,
                   seed=args.seed, resume=args.resume)
        tasks = [(pid, path, ph, cond, out_dir, opt)
                 for pid, path in pages for ph in phones for cond in PHONES[ph]["conds"]
                 if not only or cond in only]
        print("%d trang -> %d anh  (%s)  ->  %s" % (len(pages), len(tasks), ", ".join(phones), out_dir))

        rows, errors, done = [], [], 0
        if args.jobs <= 1:
            results = (process(t) for t in tasks)
            pool = None
        else:
            pool = ProcessPoolExecutor(max_workers=args.jobs, initializer=_init_worker)
            futs = [pool.submit(process, t) for t in tasks]
            results = (f.result() for f in as_completed(futs))
        for r in results:
            done += 1
            if r["status"] == "error":
                errors.append(r)
                print("[%d/%d] LOI %s" % (done, len(tasks), r["file"]))
            else:
                if r["status"] == "ok":
                    rows.append(r)
                print("[%d/%d] %s %s" % (done, len(tasks), r["status"], r["file"]))
        if pool:
            pool.shutdown()

        if rows:
            fields = ["file", "page", "condition", "phone", "phone_model", "width", "height", "hdr",
                      "page_area_pct", "scan_function", "seed", "corners"]
            mp = os.path.join(out_dir, "manifest.csv")
            exists = args.resume and os.path.exists(mp)
            with open(mp, "a" if exists else "w", newline="", encoding="utf-8-sig") as fh:
                wtr = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                if not exists:
                    wtr.writeheader()
                for r in sorted(rows, key=lambda r: r["file"]):
                    wtr.writerow(r)
        print("Xong: %d anh, %d loi. Thu muc: %s" % (len(rows), len(errors), out_dir))
        for e in errors:
            print("---", e["file"], "\n", e["error"])
        if errors:
            sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
