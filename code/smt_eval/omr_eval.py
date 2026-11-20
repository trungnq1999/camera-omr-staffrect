#!/usr/bin/env python3
"""
omr_eval.py - Thực nghiệm đánh giá các engine OMR của Score Studio (homr, Audiveris,
mô hình riêng) trên tập test Camera-GrandStaff, phục vụ bài báo AMI2026 (hướng 2).

Các lệnh con:
  inspect   Kiểm tra cấu trúc tập dữ liệu, ghép ảnh-nhãn, thử chuyển nhãn sang dạng chuẩn.
  run       Chạy từng engine trên một mẫu ảnh test, lưu kết quả và thời gian xử lý.
  score     Chuyển nhãn gốc và kết quả về cùng một dạng token, tính SER, xuất bảng cho bài báo.
  logtimes  Tổng hợp thời gian xử lý thực tế từ museparse.log của backend.

Ví dụ:
  python omr_eval.py inspect  --data /mnt/g/doan/minh/camera-grandstaff/dataset/test
  python omr_eval.py run      --data .../test --engines engines.json --out results --limit 500 --seed 42
  python omr_eval.py score    --data .../test --out results
  python omr_eval.py logtimes --log /mnt/g/doan/minh/Muse-Parse/museparse.log

Phụ thuộc: music21 (bắt buộc cho score/inspect); rapidfuzz (tùy chọn, tính nhanh hơn);
Pillow (tùy chọn, chỉ khi dùng --upscale).
"""
import argparse
import csv
import glob
import json
import math
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fractions import Fraction

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
LABEL_EXT = {".txt", ".krn", ".kern", ".ekrn", ".bekrn", ".ekern", ".bekern", ".musicxml", ".mxl"}


# =============================================================== dữ liệu
def find_pairs(data_dir):
    """Ghép ảnh với file nhãn có cùng tên (stem) trong cây thư mục của split."""
    images, labels = {}, {}
    for dp, _, files in os.walk(data_dir):
        for f in files:
            stem, ext = os.path.splitext(f)
            ext = ext.lower()
            p = os.path.join(dp, f)
            if ext in IMG_EXT:
                images.setdefault(stem, p)
            elif ext in LABEL_EXT:
                # ưu tiên nhãn nằm trong thư mục tên 'label(s)/gt/kern'
                if stem not in labels or re.search(r"label|gt|kern|annot", dp, re.I):
                    labels[stem] = p
    pairs = {}
    for s, img in images.items():
        key = s
        # nhiều ảnh chụp dùng chung một nhãn: <tên-nhãn>__<mô tả ảnh>, ví dụ bai03_p1__iphone_den
        while key not in labels and "__" in key:
            key = key.rsplit("__", 1)[0]
        if key in labels:
            pairs[s] = (img, labels[key])
    return images, labels, pairs


def label_to_kern(text):
    """
    Chuyển nhãn (kern / ekern / bekern / chuỗi token kiểu SMT) về **kern chuẩn để music21 đọc.
    Nếu tập dữ liệu dùng quy ước khác, chỉ cần sửa hàm này; lệnh 'inspect' cho biết tỷ lệ đọc được.
    """
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # chuỗi token kiểu SMT: <b> = xuống dòng, <t> = tab, <s> = dấu cách
    if "<b>" in t or "<t>" in t:
        t = t.replace("<b>", "\n").replace("<t>", "\t").replace("<s>", " ")
        t = re.sub(r"<bos>|<eos>|<pad>", "", t, flags=re.I)
    # nhãn bị gộp trên một dòng, các dòng ngăn bởi ' | '
    if t.count("\n") <= 1 and " | " in t:
        t = t.replace(" | ", "\n")
    t = re.sub(r"\*\*(e|be)?kern(_[\d.]+)?", "**kern", t)
    t = t.replace("@", "").replace("·", "")
    lines = [l.rstrip() for l in t.split("\n") if l.strip()]
    # nếu không có tab, thử tách cột theo số spine ở dòng header
    if lines and "\t" not in lines[0]:
        n = len(lines[0].split())
        fixed = []
        for l in lines:
            parts = l.split()
            fixed.append("\t".join(parts) if len(parts) == n else l)
        lines = fixed
    if lines and not lines[-1].startswith("*-"):
        n = len(lines[0].split("\t"))
        lines.append("\t".join(["*-"] * n))
    return "\n".join(lines) + "\n"


# =============================================================== chuẩn hoá thành token
def _dur(ql):
    return str(Fraction(ql).limit_denominator(96))


def stream_to_tokens(score):
    """
    Biểu diễn chung cho mọi nguồn (kern hoặc MusicXML):
    mỗi khuông -> chuỗi token theo thời gian: khoá, hoá biểu, nhịp, nốt (mỗi cao độ một token
    'E-4_1/2' = Mi giáng 4, móc đơn), dấu lặng ('r_1'), vạch nhịp '|'. Khuông được sắp theo cao độ trung bình (trên trước).
    Bỏ qua: nốt hoa mỹ (grace), dấu lặng ẩn, dynamics, articulation, luyến, dấu nối.
    Trả về dict: full, pitch, rhythm, struct (list token).
    """
    from music21 import stream
    parts = list(score.parts) if getattr(score, "parts", None) and len(score.parts) else [score]
    staves = []
    for p in parts:
        measures = list(p.getElementsByClass(stream.Measure)) or [p]
        full, pitch, rhythm, struct, ps_all = [], [], [], [], []
        first_clef = None
        for mi, m in enumerate(measures):
            if mi > 0:
                full.append("|")
            items = []
            for el in m.flatten().getElementsByClass(
                    ["Clef", "KeySignature", "TimeSignature", "Note", "Rest", "Chord"]):
                off = float(el.offset)
                cls = el.classes
                if "Clef" in cls:
                    if first_clef is None:
                        first_clef = el.sign
                    oc = getattr(el, "octaveChange", 0) or 0
                    items.append((off, 0, 0, f"clef:{el.sign}{el.line}{'' if not oc else oc}", "s"))
                elif "KeySignature" in cls:
                    items.append((off, 1, 0, f"key:{el.sharps}", "s"))
                elif "TimeSignature" in cls:
                    items.append((off, 2, 0, f"time:{el.ratioString}", "s"))
                else:
                    if el.duration.isGrace or el.quarterLength == 0:
                        continue
                    d = _dur(el.quarterLength)
                    if "Rest" in cls:
                        if getattr(el.style, "hideObjectOnPrint", False):
                            continue
                        items.append((off, 3, -1.0, f"r_{d}", "r"))
                    else:
                        pits = el.pitches if "Chord" in cls else [el.pitch]
                        for pt in pits:
                            ps_all.append(pt.ps)
                            items.append((off, 3, pt.ps, f"{pt.nameWithOctave}_{d}", "n"))
            items.sort(key=lambda x: (x[0], x[1], x[2]))
            for _, _, _, tok, kind in items:
                full.append(tok)
                if kind == "s":
                    struct.append(tok)
                elif kind == "r":
                    rhythm.append(tok)
                else:
                    name, d = tok.split("_", 1)
                    pitch.append(name)
                    rhythm.append("n_" + d)
        mean_ps = statistics.mean(ps_all) if ps_all else -1e9
        clef_rank = {"G": 0, "C": 1, "F": 2}.get(first_clef, 1)
        staves.append(((clef_rank, -mean_ps), full, pitch, rhythm, struct))
    # khuông trên trước: khóa Sol < khóa Đô < khóa Fa, cùng khóa thì cao độ trung bình cao hơn trước
    staves.sort(key=lambda s: s[0])
    out = {"full": [], "pitch": [], "rhythm": [], "struct": []}
    for i, (_, full, pitch, rhythm, struct) in enumerate(staves):
        sep = [f"<staff{i}>"]
        out["full"] += sep + full
        out["pitch"] += sep + pitch
        out["rhythm"] += sep + rhythm
        out["struct"] += sep + struct
    return out


def parse_any(path=None, text=None, fmt=None):
    from music21 import converter
    if text is not None:
        return converter.parse(text, format=fmt or "humdrum")
    return converter.parse(path)


def tokens_from_label(path):
    if os.path.splitext(path)[1].lower() in (".musicxml", ".mxl", ".xml"):
        return stream_to_tokens(parse_any(path=path))
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    return stream_to_tokens(parse_any(text=label_to_kern(raw), fmt="humdrum"))


def tokens_from_prediction(path, fmt):
    if fmt == "kern":
        with open(path, encoding="utf-8", errors="ignore") as f:
            return stream_to_tokens(parse_any(text=label_to_kern(f.read()), fmt="humdrum"))
    try:
        return stream_to_tokens(parse_any(path=path))
    except ZeroDivisionError:
        # MusicXML không hợp lệ (vd. Audiveris ghi <divisions>0</divisions> khi không nhận ra nốt nào):
        # coi là kết quả rỗng
        return {"full": [], "pitch": [], "rhythm": [], "struct": []}


# =============================================================== khoảng cách chỉnh sửa
def _encode(a, b):
    vocab = {}
    def enc(seq):
        return "".join(chr(0x4E00 + vocab.setdefault(t, len(vocab))) for t in seq)
    return enc(a), enc(b)


def edit_ops(ref, hyp):
    """Trả về (distance, substitutions, insertions, deletions)."""
    try:
        from rapidfuzz.distance import Levenshtein
        r, h = _encode(ref, hyp)
        ops = Levenshtein.editops(r, h)
        s = sum(1 for o in ops if o.tag == "replace")
        i = sum(1 for o in ops if o.tag == "insert")
        d = sum(1 for o in ops if o.tag == "delete")
        return s + i + d, s, i, d
    except ImportError:
        pass
    n, m = len(ref), len(hyp)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1,
                          D[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, s, ins, dele = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            s += ref[i - 1] != hyp[j - 1]
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            dele += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return D[n][m], s, ins, dele


def edit_distance(ref, hyp):
    try:
        from rapidfuzz.distance import Levenshtein
        r, h = _encode(ref, hyp)
        return Levenshtein.distance(r, h)
    except ImportError:
        return edit_ops(ref, hyp)[0]


# =============================================================== môi trường
def collect_env():
    import importlib.metadata as md
    env = {"time": datetime.now().isoformat(timespec="seconds"),
           "os": f"{platform.system()} {platform.release()}",
           "python": platform.python_version(), "cpu": platform.processor(),
           "cpu_count": os.cpu_count(), "packages": {}}
    try:
        with open("/proc/cpuinfo") as f:
            for l in f:
                if l.startswith("model name"):
                    env["cpu"] = l.split(":", 1)[1].strip()
                    break
        with open("/proc/meminfo") as f:
            env["ram_gb"] = round(int(f.readline().split()[1]) / 1024 ** 2, 1)
    except OSError:
        pass
    for p in ["homr", "music21", "torch", "onnxruntime", "onnxruntime-gpu", "rapidfuzz", "numpy",
              "opencv-python", "opencv-python-headless"]:
        try:
            env["packages"][p] = md.version(p)
        except md.PackageNotFoundError:
            pass
    if shutil.which("nvidia-smi"):
        try:
            env["gpu"] = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            pass
    return env


# =============================================================== inspect
def cmd_inspect(a):
    images, labels, pairs = find_pairs(a.data)
    print(f"Ảnh: {len(images)} | Nhãn: {len(labels)} | Ghép được: {len(pairs)}")
    if not pairs:
        print("Không ghép được ảnh với nhãn. Ví dụ tên ảnh:", list(images)[:3], "nhãn:", list(labels)[:3])
        return
    stems = sorted(pairs)
    random.Random(0).shuffle(stems)
    first = pairs[stems[0]][1]
    with open(first, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    if os.path.splitext(first)[1].lower() in (".musicxml", ".mxl", ".xml"):
        print(f"\n--- Nhãn mẫu (MusicXML): {first}")
    else:
        print(f"\n--- Nhãn mẫu: {first}\n{raw[:600]}\n--- Sau khi chuyển sang **kern:\n{label_to_kern(raw)[:600]}")
    ok, lens, errs = 0, [], []
    for s in stems[:a.n]:
        try:
            t = tokens_from_label(pairs[s][1])
            if len(t["pitch"]) <= 2:
                raise ValueError("không có nốt nào")
            ok += 1
            lens.append(len(t["full"]))
        except Exception as e:
            errs.append((s, str(e)[:150]))
    n = min(a.n, len(stems))
    print(f"\nĐọc được {ok}/{n} nhãn ({100 * ok / n:.1f}%).", end=" ")
    if lens:
        print(f"Token/hệ thống: TB {statistics.mean(lens):.0f}, min {min(lens)}, max {max(lens)}")
    for s, e in errs[:8]:
        print(f"  Lỗi {s}: {e}")
    if ok:
        t = tokens_from_label(pairs[stems[0]][1])
        print("\nToken mẫu:", " ".join(t["full"][:60]))
    if ok < 0.9 * n:
        print("\n!! Tỷ lệ đọc nhãn thấp: cần chỉnh hàm label_to_kern() theo định dạng nhãn ở trên.")


# =============================================================== run
def _upscale(src, dst, factor):
    from PIL import Image
    im = Image.open(src)
    im = im.resize((int(im.width * factor), int(im.height * factor)), Image.LANCZOS)
    im.save(dst)


def _to_win(path):
    """/mnt/g/a/b -> G:\\a\\b (dùng wslpath nếu có). Không ở trong WSL thì trả nguyên."""
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", path)
    if m:
        return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")
    if shutil.which("wslpath"):
        try:
            return subprocess.run(["wslpath", "-w", path], capture_output=True, text=True,
                                  timeout=10).stdout.strip() or path
        except Exception:
            pass
    return path


def run_one(engine, cfg, stem, img, out_dir, upscale, keep_work):
    out_dir = os.path.abspath(out_dir)
    work = os.path.join(out_dir, engine, "work", stem)
    pred_dir = os.path.join(out_dir, engine, "pred")
    os.makedirs(work, exist_ok=True)
    os.makedirs(pred_dir, exist_ok=True)
    ext = os.path.splitext(img)[1]
    inp = os.path.join(work, stem + (".png" if upscale != 1 else ext))
    if upscale != 1:
        _upscale(img, inp, upscale)
    else:
        shutil.copy(img, inp)
    subs = {"input": os.path.abspath(inp), "workdir": os.path.abspath(work), "stem": stem}
    # đường dẫn kiểu Windows, dùng khi gọi chương trình .exe của Windows từ WSL
    subs["input_win"] = _to_win(subs["input"])
    subs["workdir_win"] = _to_win(subs["workdir"])
    cmd = [c.format(**subs) for c in cfg["cmd"]]
    env = dict(os.environ, **cfg.get("env", {}))
    t0 = time.perf_counter()
    status, rc, err = "ok", None, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           timeout=cfg.get("timeout", 600), cwd=cfg.get("cwd") or work)
        rc = r.returncode
        err = (r.stderr or "")[-400:].replace("\n", " ")
    except subprocess.TimeoutExpired:
        status = "timeout"
    except Exception as e:
        status, err = "error", str(e)[:400]
    elapsed = time.perf_counter() - t0
    pattern = cfg["output_glob"].format(**subs)
    found = sorted(glob.glob(pattern, recursive=True))
    pred = ""
    if found:
        src = found[0]
        pred = os.path.join(pred_dir, stem + os.path.splitext(src)[1])
        shutil.copy(src, pred)
    elif status == "ok":
        status = "no_output"
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return {"engine": engine, "stem": stem, "status": status, "returncode": rc,
            "seconds": round(elapsed, 3), "pred": pred, "stderr_tail": err}


def cmd_run(a):
    with open(a.engines, encoding="utf-8") as f:
        engines = {k: v for k, v in json.load(f).items()
                   if not k.startswith("_") and v.get("enabled", True)}
    if a.only:
        engines = {k: v for k, v in engines.items() if k in a.only.split(",")}
    _, _, pairs = find_pairs(a.data)
    stems = sorted(pairs)
    random.Random(a.seed).shuffle(stems)
    if a.limit:
        stems = stems[:a.limit]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "sample.txt"), "w") as f:
        f.write("\n".join(stems) + "\n")
    with open(os.path.join(a.out, "env.json"), "w", encoding="utf-8") as f:
        json.dump({"env": collect_env(), "engines": engines, "data": os.path.abspath(a.data),
                   "limit": a.limit, "seed": a.seed, "upscale": a.upscale}, f, indent=2, ensure_ascii=False)
    runs_path = os.path.join(a.out, "runs.csv")
    done = set()
    if os.path.exists(runs_path):
        with open(runs_path, encoding="utf-8") as f:
            done = {(r["engine"], r["stem"]) for r in csv.DictReader(f)
                    if r["status"] in ("ok", "no_output")}
    fields = ["engine", "stem", "status", "returncode", "seconds", "pred", "stderr_tail"]
    new = not os.path.exists(runs_path)
    with open(runs_path, "a", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=fields)
        if new:
            w.writeheader()
        for eng, cfg in engines.items():
            todo = [s for s in stems if (eng, s) not in done]
            jobs = int(cfg.get("jobs", 1))
            print(f"[{eng}] {len(todo)} ảnh cần chạy ({len(stems) - len(todo)} đã có), {jobs} luồng")
            t_start = time.time()
            with ThreadPoolExecutor(max_workers=jobs) as ex:
                futs = [ex.submit(run_one, eng, cfg, s, pairs[s][0], a.out, a.upscale, a.keep_work)
                        for s in todo]
                for i, fu in enumerate(as_completed(futs), 1):
                    r = fu.result()
                    w.writerow(r)
                    fcsv.flush()
                    if i % 10 == 0 or i == len(todo):
                        rate = (time.time() - t_start) / i
                        print(f"  {i}/{len(todo)}  ~{rate:.1f} s/ảnh, còn ~{rate * (len(todo) - i) / 60:.0f} phút")
    print(f"Xong. Kết quả: {runs_path}")


# =============================================================== score
def bootstrap_ci(values_ed, values_len, iters=1000, seed=0):
    rnd = random.Random(seed)
    n = len(values_ed)
    stats = []
    for _ in range(iters):
        idx = [rnd.randrange(n) for _ in range(n)]
        stats.append(sum(values_ed[i] for i in idx) / max(1, sum(values_len[i] for i in idx)))
    stats.sort()
    return stats[int(0.025 * iters)], stats[int(0.975 * iters) - 1]


def bootstrap_diff(ed_a, ed_b, lens, iters=1000, seed=1):
    rnd = random.Random(seed)
    n = len(lens)
    diffs = []
    for _ in range(iters):
        idx = [rnd.randrange(n) for _ in range(n)]
        L = max(1, sum(lens[i] for i in idx))
        diffs.append((sum(ed_a[i] for i in idx) - sum(ed_b[i] for i in idx)) / L)
    diffs.sort()
    return diffs[int(0.025 * iters)], diffs[int(0.975 * iters) - 1]


def cmd_score(a):
    _, _, pairs = find_pairs(a.data)
    runs_path = os.path.join(a.out, "runs.csv")
    if not os.path.exists(runs_path):
        sys.exit("Chưa có runs.csv: hãy chạy lệnh 'run' trước.")
    runs = {}
    with open(runs_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            runs[(r["engine"], r["stem"])] = r      # bản ghi cuối cùng thắng
    engines = sorted({e for e, _ in runs})
    fmt = {}
    env_path = os.path.join(a.out, "env.json")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for k, v in json.load(f).get("engines", {}).items():
                fmt[k] = v.get("format", "musicxml")
    stems_all = sorted({s for _, s in runs})
    stems = [s for s in stems_all if s in pairs]
    if len(stems) < len(stems_all):
        print(f"Bỏ {len(stems_all) - len(stems)} ảnh đã chạy nhưng không còn nhãn trong --data")

    gt_cache, gt_fail = {}, []
    for s in stems:
        try:
            gt_cache[s] = tokens_from_label(pairs[s][1])
        except Exception as e:
            gt_fail.append((s, str(e)[:120]))
    print(f"Nhãn đọc được: {len(gt_cache)}/{len(stems)} (bỏ {len(gt_fail)} mẫu nhãn lỗi)")

    rows = []
    keys = ["full", "pitch", "rhythm", "struct"]
    for eng in engines:
        for s in stems:
            if s not in gt_cache or (eng, s) not in runs:
                continue
            r = runs[(eng, s)]
            gt = gt_cache[s]
            pred_ok, perr = False, ""
            hyp = {k: [] for k in keys}
            pp = r["pred"]
            if pp and not os.path.exists(pp):      # đường dẫn tương đối từ lần chạy cũ
                for base in (os.path.dirname(os.path.abspath(a.out)), os.path.abspath(a.out)):
                    cand = os.path.join(base, pp)
                    if os.path.exists(cand):
                        pp = cand
                        break
                else:
                    alt = os.path.join(a.out, eng, "pred", os.path.basename(pp))
                    pp = alt if os.path.exists(alt) else pp
            if pp and os.path.exists(pp):
                try:
                    f_eng = "kern" if pp.lower().endswith((".krn", ".kern", ".ekern", ".bekern")) else fmt.get(eng, "musicxml")
                    hyp = tokens_from_prediction(pp, f_eng)
                    pred_ok = len(hyp["full"]) > 0
                except Exception as e:
                    perr = str(e)[:150]
            row = {"engine": eng, "stem": s, "status": r["status"], "seconds": float(r["seconds"] or 0),
                   "parsed": int(pred_ok), "parse_error": perr}
            for k in keys:
                ref = gt[k]
                if k == "full":
                    d, sub, ins, dele = edit_ops(ref, hyp[k])
                    row.update(sub=sub, ins=ins, dele=dele)
                else:
                    d = edit_distance(ref, hyp[k])
                row[f"ed_{k}"] = d
                row[f"len_{k}"] = len(ref)
                row[f"ser_{k}"] = round(d / max(1, len(ref)), 4)
            rows.append(row)

    per_path = os.path.join(a.out, "per_sample.csv")
    with open(per_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- tổng hợp
    common = set.intersection(*[{r["stem"] for r in rows if r["engine"] == e} for e in engines])
    L = []
    L.append(f"# Kết quả đánh giá OMR: {os.path.basename(os.path.abspath(a.data).rstrip('/'))}\n")
    L.append(f"Thời điểm: {datetime.now():%Y-%m-%d %H:%M} · Dữ liệu: `{os.path.abspath(a.data)}`  ")
    L.append(f"Số mẫu chấm: {len(common)} mẫu chung cho mọi engine (bỏ {len(gt_fail)} mẫu có nhãn không đọc được).\n")
    L.append("SER = khoảng cách Levenshtein giữa chuỗi token dự đoán và nhãn, chia tổng độ dài nhãn "
             "(micro-average). Mẫu engine không trả kết quả được tính SER = 100%.\n")
    L.append("| Engine | n | Thất bại (%) | SER (%) [95% CI] | SER khi thành công (%) | Pitch SER (%) | "
             "Rhythm SER (%) | Struct SER (%) | Thay thế / Chèn / Xoá (%) | Thời gian TB (s) | Trung vị (s) | P90 (s) |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    by_eng = {}
    for eng in engines:
        R = [r for r in rows if r["engine"] == eng and r["stem"] in common]
        R.sort(key=lambda r: r["stem"])
        by_eng[eng] = R
        if not R:
            continue
        def micro(k, RR=R):
            return 100 * sum(r[f"ed_{k}"] for r in RR) / max(1, sum(r[f"len_{k}"] for r in RR))
        ok = [r for r in R if r["parsed"]]
        lo, hi = bootstrap_ci([r["ed_full"] for r in R], [r["len_full"] for r in R])
        tot_ed = max(1, sum(r["ed_full"] for r in R))
        secs = sorted(r["seconds"] for r in R if r["status"] == "ok")
        p90 = secs[int(0.9 * (len(secs) - 1))] if secs else float("nan")
        L.append(f"| {eng} | {len(R)} | {100 * (1 - len(ok) / len(R)):.1f} | {micro('full'):.1f} "
                 f"[{100 * lo:.1f}–{100 * hi:.1f}] | {micro('full', ok) if ok else float('nan'):.1f} | "
                 f"{micro('pitch'):.1f} | {micro('rhythm'):.1f} | {micro('struct'):.1f} | "
                 f"{100 * sum(r['sub'] for r in R) / tot_ed:.0f} / {100 * sum(r['ins'] for r in R) / tot_ed:.0f}"
                 f" / {100 * sum(r['dele'] for r in R) / tot_ed:.0f} | "
                 f"{statistics.mean(secs) if secs else float('nan'):.2f} | "
                 f"{statistics.median(secs) if secs else float('nan'):.2f} | {p90:.2f} |")

    L.append("\n## Phân bố SER theo từng mẫu\n")
    L.append("| Engine | Trung vị (%) | Q1 (%) | Q3 (%) | Mẫu SER ≤ 10% | Mẫu SER ≤ 25% | Mẫu SER ≥ 90% | Mẫu SER > 100% |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for eng in engines:
        x = sorted(r["ser_full"] for r in by_eng.get(eng, []))
        if not x:
            continue
        n = len(x)
        pc = lambda c: f"{c} ({100 * c / n:.0f}%)"
        L.append(f"| {eng} | {100 * statistics.median(x):.1f} | {100 * x[n // 4]:.1f} | {100 * x[(3 * n) // 4]:.1f} | "
                 f"{pc(sum(v <= 0.10 for v in x))} | {pc(sum(v <= 0.25 for v in x))} | "
                 f"{pc(sum(v >= 0.90 for v in x))} | {pc(sum(v > 1 for v in x))} |")

    if len(engines) >= 2:
        L.append("\n## So sánh từng cặp (chênh lệch SER, bootstrap 1.000 lần trên cùng các mẫu)\n")
        L.append("| A − B | Chênh SER (điểm %) | 95% CI | A tốt hơn ở (% mẫu) |")
        L.append("| --- | --- | --- | --- |")
        for i, ea in enumerate(engines):
            for eb in engines[i + 1:]:
                A, B = by_eng[ea], by_eng[eb]
                if not A or not B:
                    continue
                lens = [r["len_full"] for r in A]
                da = [r["ed_full"] for r in A]
                db = [r["ed_full"] for r in B]
                diff = 100 * (sum(da) - sum(db)) / max(1, sum(lens))
                lo, hi = bootstrap_diff(da, db, lens)
                better = 100 * sum(1 for x, y in zip(A, B) if x["ser_full"] < y["ser_full"]) / len(A)
                L.append(f"| {ea} − {eb} | {diff:+.1f} | [{100 * lo:+.1f}, {100 * hi:+.1f}] | {better:.0f} |")

    L.append("\n## Ví dụ cho hình phân tích lỗi (đường dẫn ảnh gốc)\n")
    for eng in engines:
        R = sorted([r for r in by_eng[eng] if r["parsed"]], key=lambda r: r["ser_full"])
        if not R:
            continue
        L.append(f"**{eng}**\n")
        picks = [("Tốt nhất", R[:3]), ("Trung vị", R[len(R) // 2 - 1: len(R) // 2 + 2]), ("Kém nhất", R[-3:])]
        for name, sel in picks:
            for r in sel:
                L.append(f"- {name}: `{pairs[r['stem']][0]}` — SER {100 * r['ser_full']:.1f}%")
        L.append("")
    fails = [r for r in rows if not r["parsed"]]
    if fails:
        L.append("## Thống kê thất bại\n")
        for eng in engines:
            c = {}
            for r in fails:
                if r["engine"] == eng:
                    key = r["status"] if r["status"] != "ok" else ("parse_error" if r["parse_error"] else "empty")
                    c[key] = c.get(key, 0) + 1
            if c:
                L.append(f"- {eng}: " + ", ".join(f"{k} {v}" for k, v in c.items()))
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            L.append("\n## Môi trường chạy\n\n```json\n" +
                     json.dumps(json.load(f).get("env", {}), indent=2, ensure_ascii=False) + "\n```")
    text = "\n".join(L)
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nĐã lưu: {per_path}, {os.path.join(a.out, 'summary.md')}")


# =============================================================== logtimes
def cmd_logtimes(a):
    seg_re = re.compile(r"^(\S+ \S+).*Segnet Inference time:\s*([\d.]+)")
    tr_re = re.compile(r"^(\S+ \S+).*Inference Time Tromr:\s*([\d.]+)")
    pages, cur = [], None
    with open(a.log, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = seg_re.search(line)
            if m:
                if cur:
                    pages.append(cur)
                cur = {"start": m.group(1), "segnet": float(m.group(2)), "staves": []}
                continue
            m = tr_re.search(line)
            if m and cur:
                cur["staves"].append(float(m.group(2)))
    if cur:
        pages.append(cur)
    if not pages:
        sys.exit("Không tìm thấy dòng 'Segnet Inference time' trong log.")
    seg = [p["segnet"] for p in pages]
    st = [s for p in pages for s in p["staves"]]
    tot = [p["segnet"] + sum(p["staves"]) for p in pages]
    nst = [len(p["staves"]) for p in pages]
    def d(x):
        return f"TB {statistics.mean(x):.2f} s, trung vị {statistics.median(x):.2f} s, min {min(x):.2f}, max {max(x):.2f}"
    print(f"Số trang trong log: {len(pages)} (từ {pages[0]['start']} đến {pages[-1]['start']})")
    print(f"Segnet (phân đoạn trang): {d(seg)}")
    if st:
        print(f"Transformer mỗi khuông: {d(st)}  (n = {len(st)} khuông)")
        print(f"Số khuông/trang: TB {statistics.mean(nst):.1f}, min {min(nst)}, max {max(nst)}")
    print(f"Tổng suy luận mỗi trang (Segnet + các khuông): {d(tot)}")
    print("Lưu ý: chưa gồm đọc ảnh, tiền xử lý, ghi MusicXML và chờ hàng đợi.")


# =============================================================== main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("inspect")
    p.add_argument("--data", required=True)
    p.add_argument("--n", type=int, default=50, help="số nhãn thử đọc")
    p = sp.add_parser("run")
    p.add_argument("--data", required=True)
    p.add_argument("--engines", default="engines.json")
    p.add_argument("--out", default="results")
    p.add_argument("--limit", type=int, default=500, help="số ảnh test lấy ngẫu nhiên (0 = tất cả)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--only", help="chỉ chạy các engine này, ví dụ homr,audiveris")
    p.add_argument("--upscale", type=float, default=1.0, help="phóng ảnh trước khi đưa vào engine")
    p.add_argument("--keep-work", action="store_true")
    p = sp.add_parser("score")
    p.add_argument("--data", required=True)
    p.add_argument("--out", default="results")
    p = sp.add_parser("logtimes")
    p.add_argument("--log", required=True)
    a = ap.parse_args()
    {"inspect": cmd_inspect, "run": cmd_run, "score": cmd_score, "logtimes": cmd_logtimes}[a.cmd](a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng. Chạy lại cùng lệnh để tiếp tục (các ảnh đã xong được bỏ qua).")
