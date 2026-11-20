#!/usr/bin/env python3
"""
uvdoc_batch.py - Đường cơ sở: nắn tài liệu bằng mô hình học sâu UVDoc (Magne et al., SIGGRAPH Asia 2023,
giấy phép MIT, trọng số có sẵn trong repo) cho cả thư mục ảnh, dùng đúng như tác giả công bố (không huấn luyện lại).

Đầu ra cùng cấu trúc với rectify_v2.py để chạy engine bằng run_pipeline.py:
  <out>/raw/  ảnh UVDoc (khổ A4 dọc 2480x3508)
  <out>/norm/ + chuẩn hoá ánh sáng   <out>/bin/ + Sauvola   (dùng hàm của rectify_pages.py đã khoá)
  <out>/report_uvdoc.csv

  git clone --depth 1 https://github.com/tanguymagne/UVDoc.git /mnt/g/tools/UVDoc
  .venv-smt/bin/python pp_study/baselines/uvdoc_batch.py --uvdoc /mnt/g/tools/UVDoc --photos real_photos2 --out uvdoc_ip14pm
"""
import argparse, csv, glob, os, sys, time
import cv2
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uvdoc", required=True, help="thư mục repo UVDoc (chứa model/best_model.pkl)")
    ap.add_argument("--photos", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="2480x3508", help="kích thước ảnh ra WxH (A4 dọc)")
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, a.uvdoc)
    from model import UVDocnet
    from utils import IMG_SIZE, bilinear_unwarping
    sys.path.insert(0, os.path.join(HERE, "..", "rectify"))
    from rectify_pages import normalize_light, sauvola   # bản đã khoá, chỉ dùng lại hàm

    dev = torch.device("cpu" if a.cpu or not torch.cuda.is_available() else "cuda")
    model = UVDocnet(num_filter=32, kernel_size=5)
    ck = torch.load(os.path.join(a.uvdoc, "model", "best_model.pkl"), map_location="cpu", weights_only=False)
    model.load_state_dict(ck["model_state"]); model.to(dev).eval()
    W, H = map(int, a.size.lower().split("x"))
    for v in ("raw", "norm", "bin"):
        os.makedirs(os.path.join(a.out, v), exist_ok=True)
    rep = os.path.join(a.out, "report_uvdoc.csv")
    done = {r["file"] for r in csv.DictReader(open(rep, encoding="utf-8"))} if os.path.exists(rep) else set()
    files = sorted(glob.glob(os.path.join(a.photos, "*.jpg")))
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        if name in done: continue
        t = time.time()
        bgr = cv2.imread(f)
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        with torch.no_grad():
            inp = torch.from_numpy(cv2.resize(img, tuple(IMG_SIZE)).transpose(2, 0, 1)).unsqueeze(0).to(dev)
            pts, _ = model(inp)
            out = bilinear_unwarping(torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).to(dev), pts, (W, H))
        out = (out[0].cpu().numpy().transpose(1, 2, 0) * 255).clip(0, 255).astype(np.uint8)
        out = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
        cv2.imwrite(os.path.join(a.out, "raw", name), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
        nl = normalize_light(out)
        cv2.imwrite(os.path.join(a.out, "norm", name), nl, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(a.out, "bin", name[:-4] + ".png"), sauvola(nl))
        sec = round(time.time() - t, 2)
        new = not os.path.exists(rep)
        with open(rep, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new: w.writerow(["file", "seconds", "device"])
            w.writerow([name, sec, dev.type])
        print(f"{i}/{len(files)} {name} ({sec} s)", flush=True)

if __name__ == "__main__":
    main()
