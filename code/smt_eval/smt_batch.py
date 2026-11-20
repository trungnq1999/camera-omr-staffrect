#!/usr/bin/env python3
"""
smt_batch.py - Chạy Sheet Music Transformer (bản toàn trang, SMT++) trên một thư mục ảnh,
ghi kết quả theo định dạng của omr_eval.py để chấm cùng giao thức với homr và Audiveris.

Mô hình được nạp MỘT lần cho cả thư mục (khác homr/Audiveris gọi CLI từng ảnh).
Kết quả:  <out>/<engine>/pred/<stem>.krn   (chuỗi **kern/bekern do mô hình sinh ra)
          <out>/<engine>/raw/<stem>.txt     (chuỗi token gốc, để kiểm tra)
          <out>/runs.csv                    (nối thêm dòng; omr_eval.py score đọc file này)

Ví dụ:
  python smt_batch.py --smt-repo /mnt/g/tools/SMT --data /mnt/g/doan/minh/real_photos \
      --out /mnt/g/doan/minh/results_smt_try --limit 4 --width 1000      # chạy thử
  python smt_batch.py ... --out /mnt/g/doan/minh/results_smt --engine smt --width 1000   # chạy đủ
  python smt_batch.py ... --engine smt_crop --crop-page --width 1000       # biến thể cắt trang giấy
"""
import argparse
import csv
import json
import os
import sys
import time
import traceback

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omr_eval import find_pairs  # noqa: E402
from kern_fix import sanitize  # noqa: E402

CANDIDATE_MODELS = [
    # (repo, subfolder) - thử lần lượt nếu không chỉ định --model
    ("antoniorv6/smt-fp-grandstaff", None),
    ("PRAIG/smt-fp-grandstaff", None),
    ("AEmotionStudio/smt-omr-models", "grandstaff"),
]


# ------------------------------------------------------------------ mô hình
def load_model(smt_repo, model_id, subfolder, device):
    if smt_repo:
        sys.path.insert(0, os.path.abspath(smt_repo))
    from smt_model import SMTModelForCausalLM  # từ mã nguồn SMT (MIT)
    tried = []
    cands = [(model_id, subfolder)] if model_id else CANDIDATE_MODELS
    for mid, sub in cands:
        try:
            kw = {"subfolder": sub} if sub else {}
            m = SMTModelForCausalLM.from_pretrained(mid, **kw).to(device)
            m.eval()
            return m, f"{mid}" + (f"/{sub}" if sub else "")
        except Exception as e:  # thử ứng viên tiếp theo
            tried.append(f"{mid}{'/' + sub if sub else ''}: {str(e)[:160]}")
    sys.exit("Không nạp được mô hình SMT. Đã thử:\n  " + "\n  ".join(tried) +
             "\nHãy chỉ định --model <repo> [--subfolder <thư mục>] theo trang HuggingFace của PRAIG.")


def model_limits(model):
    cfg = getattr(model, "config", None)
    get = lambda *names: next((getattr(cfg, n) for n in names if cfg is not None and hasattr(cfg, n)), None)
    return {"maxh": get("maxh", "max_height"), "maxw": get("maxw", "max_width"),
            "maxlen": get("maxlen", "max_len"), "in_channels": get("in_channels") or 1}


# ------------------------------------------------------------------ tiền xử lý
def crop_page(img):
    """Cắt theo hình chữ nhật bao trang giấy (vùng sáng lớn nhất). Không nắn phối cảnh."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (0, 0), 5)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return img
    x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    if w * h < 0.2 * img.shape[0] * img.shape[1]:
        return img
    return img[y:y + h, x:x + w]


def prepare(path, width, limits, crop):
    img = cv2.imread(path)
    if img is None:
        raise ValueError("không đọc được ảnh")
    if crop:
        img = crop_page(img)
    h, w = img.shape[:2]
    scale = width / w
    if limits["maxh"] and h * scale > limits["maxh"]:
        scale = limits["maxh"] / h
    if limits["maxw"] and w * scale > limits["maxw"]:
        scale = limits["maxw"] / w
    img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    if limits["in_channels"] == 1:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def to_tensor(img):
    import torch
    try:
        from data_augmentation.data_augmentation import convert_img_to_tensor
        return convert_img_to_tensor(img)
    except Exception:
        arr = img.astype(np.float32) / 255.0
        if arr.ndim == 2:
            arr = arr[None]
        else:
            arr = arr.transpose(2, 0, 1)
        return torch.from_numpy(arr)


def decode(pred):
    if isinstance(pred, (tuple, list)) and pred and not isinstance(pred[0], str):
        pred = pred[0]
    if isinstance(pred, (tuple, list)):
        pred = "".join(pred)
    return str(pred).replace("<b>", "\n").replace("<s>", " ").replace("<t>", "\t") \
        .replace("<bos>", "").replace("<eos>", "")


# ------------------------------------------------------------------ chạy
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smt-repo", help="thư mục mã nguồn SMT (git clone github.com/antoniorv6/SMT)")
    ap.add_argument("--model", help="tên mô hình HuggingFace; bỏ trống để thử các ứng viên mặc định")
    ap.add_argument("--subfolder")
    ap.add_argument("--engine", default="smt", help="tên engine trong báo cáo (vd. smt, smt_crop, smt_w1500)")
    ap.add_argument("--width", type=int, default=1000, help="chiều rộng ảnh đưa vào mô hình (px)")
    ap.add_argument("--crop-page", action="store_true", help="cắt theo khung trang giấy trước khi thu nhỏ")
    ap.add_argument("--limit", type=int, default=0, help="chỉ chạy N ảnh đầu (để thử)")
    ap.add_argument("--pages", help="chỉ chạy ảnh của các trang này (mã trang cách nhau dấu phẩy, phần trước '__')")
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()

    import torch
    device = "cpu" if a.cpu or not torch.cuda.is_available() else "cuda"
    model, model_name = load_model(a.smt_repo, a.model, a.subfolder, device)
    limits = model_limits(model)
    print(f"Mô hình: {model_name} | thiết bị: {device} | giới hạn: {limits}")

    _, _, pairs = find_pairs(a.data)
    stems = sorted(pairs)
    if a.pages:
        keep = {x.strip() for x in a.pages.split(",") if x.strip()}
        stems = [s for s in stems if s.split("__")[0] in keep]
    if a.limit:
        # chạy thử: lấy đều các điều kiện chụp
        by_cond = {}
        for s in stems:
            by_cond.setdefault(s.split("__")[-1], []).append(s)
        stems = [v[0] for v in by_cond.values()][:a.limit] or stems[:a.limit]

    pred_dir = os.path.join(os.path.abspath(a.out), a.engine, "pred")
    raw_dir = os.path.join(os.path.abspath(a.out), a.engine, "raw")
    os.makedirs(pred_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    runs_path = os.path.join(a.out, "runs.csv")
    done = set()
    if os.path.exists(runs_path):
        with open(runs_path, encoding="utf-8") as f:
            done = {r["stem"] for r in csv.DictReader(f) if r["engine"] == a.engine and r["status"] == "ok"}
    fields = ["engine", "stem", "status", "returncode", "seconds", "pred", "stderr_tail"]
    new = not os.path.exists(runs_path)

    with open(runs_path, "a", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=fields)
        if new:
            w.writeheader()
        todo = [s for s in stems if s not in done]
        print(f"[{a.engine}] {len(todo)} ảnh cần chạy ({len(stems) - len(todo)} đã có)")
        for i, s in enumerate(todo, 1):
            t0 = time.perf_counter()
            row = {"engine": a.engine, "stem": s, "status": "ok", "returncode": 0, "pred": "", "stderr_tail": ""}
            try:
                img = prepare(pairs[s][0], a.width, limits, a.crop_page)
                x = to_tensor(img).unsqueeze(0).to(device)
                with torch.no_grad():
                    out = model.predict(x, convert_to_str=True)
                text = decode(out)
                with open(os.path.join(raw_dir, s + ".txt"), "w", encoding="utf-8") as f:
                    f.write(str(out[0] if isinstance(out, tuple) else out))
                if not text.strip():
                    row["status"] = "no_output"
                else:
                    dec_dir = os.path.join(os.path.dirname(pred_dir), "decoded")
                    os.makedirs(dec_dir, exist_ok=True)
                    with open(os.path.join(dec_dir, s + ".krn"), "w", encoding="utf-8") as f:
                        f.write(text)                       # chuỗi giải mã gốc
                    clean, dropped, _ = sanitize(text)      # thêm **kern / *-, bỏ dòng sai cột
                    pp = os.path.join(pred_dir, s + ".krn")
                    with open(pp, "w", encoding="utf-8") as f:
                        f.write(clean)
                    row["pred"] = pp
                row["stderr_tail"] = f"input {img.shape[1]}x{img.shape[0]}" + (f" | {text.count(chr(10))} dòng, bỏ {dropped}" if row["pred"] else "")
            except Exception as e:
                row["status"], row["returncode"] = "error", 1
                row["stderr_tail"] = (str(e) + " | " + traceback.format_exc(limit=1))[-400:].replace("\n", " ")
                if device == "cuda":
                    torch.cuda.empty_cache()
            row["seconds"] = round(time.perf_counter() - t0, 3)
            w.writerow(row)
            fcsv.flush()
            print(f"  {i}/{len(todo)} {s}: {row['status']} {row['seconds']} s {row['stderr_tail'][:80]}")

    # ghi định dạng engine vào env.json để omr_eval score đọc đúng kern
    env_path = os.path.join(a.out, "env.json")
    try:
        env = json.load(open(env_path, encoding="utf-8")) if os.path.exists(env_path) else {}
        env.setdefault("engines", {})[a.engine] = {"format": "kern", "model": model_name, "width": a.width,
                                                    "crop_page": a.crop_page, "device": device,
                                                    "torch": torch.__version__}
        json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    except Exception as e:
        print("Không cập nhật được env.json:", e)
    print("Xong. Chấm điểm: python omr_eval.py score --data", a.data, "--out", a.out)


if __name__ == "__main__":
    main()
