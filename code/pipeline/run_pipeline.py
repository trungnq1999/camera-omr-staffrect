#!/usr/bin/env python3
"""
run_pipeline.py - Chạy TOÀN BỘ quy trình đánh giá tiền xử lý trên một thư mục ảnh:
    tiền xử lý (rectify_pages.py) -> chạy engine trên từng biến thể -> chấm điểm -> bảng tổng hợp.

Cùng một lệnh dùng cho ảnh mô phỏng và ảnh thật; chỉ đổi --photos và --out:
    python run_pipeline.py --photos sim_photos2  --gt pp_study/print_set2/out_set2/gt --out results_sim
    python run_pipeline.py --photos real_photos2 --gt pp_study/print_set2/out_set2/gt --out results_real

Biến thể ảnh đưa vào engine:
    raw   ảnh như chụp          rect  nắn phối cảnh về A4      norm  rect + chuẩn hoá ánh sáng
    bin   norm + Sauvola        bbox  chỉ cắt khung trang (không nắn)

Có thể chạy lại bất cứ lúc nào: ảnh/engine đã xong sẽ được bỏ qua (runs.csv của từng thư mục).
Chỉ dùng thư viện chuẩn của Python; mỗi bước gọi đúng python của từng môi trường (--py-homr, --py-smt).

Kết quả trong --out:
    data/<biến thể>/{gt,photos}         liên kết tới nhãn và ảnh của biến thể (để omr_eval tìm cặp)
    pre/                                 ảnh sau tiền xử lý + pre/report.csv
    runs/<biến thể>/<omr|smt>/           runs.csv, per_sample.csv, summary.md của omr_eval
    all_samples.csv                      mọi mẫu, mọi engine, mọi biến thể (một dòng một lượt chạy)
    RESULTS.md                           các bảng tổng hợp cho bài báo
"""
import argparse
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ALL_VARIANTS = ["raw", "rect", "norm", "bin", "bbox"]
DEFAULT_ENGINE_VARIANTS = {          # biến thể nào chạy engine nào
    "homr": ["raw", "rect", "norm", "bbox"],          # bin: làm homr kém đi rõ trên ảnh mô phỏng (+18,7 điểm), đã loại
    "audiveris": ["raw", "rect", "norm", "bin", "bbox"],
    "smt": ["raw", "rect", "norm", "bbox"],
}


# ------------------------------------------------------------------ tiện ích
def sh(cmd, env_bin=None, log=None):
    """Chạy lệnh, in ra màn hình và ghi log. env_bin: thư mục bin của venv đưa lên đầu PATH."""
    env = dict(os.environ)
    if env_bin:
        env["PATH"] = env_bin + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = os.path.dirname(env_bin)
    print("\n$ " + " ".join(str(c) for c in cmd), flush=True)
    t0 = time.time()
    with open(log, "a", encoding="utf-8") if log else open(os.devnull, "w") as lf:
        lf.write("\n$ " + " ".join(str(c) for c in cmd) + "\n")
        p = subprocess.Popen([str(c) for c in cmd], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        for line in p.stdout:
            if "Warning" in line or "warn(" in line:
                lf.write(line)
                continue
            sys.stdout.write(line)
            lf.write(line)
        p.wait()
    print(f"  ({time.time() - t0:.0f} s, mã thoát {p.returncode})", flush=True)
    return p.returncode


def link_or_copy(src, dst):
    if os.path.lexists(dst):
        return
    try:
        os.symlink(os.path.abspath(src), dst)
    except OSError:
        shutil.copy2(src, dst)


def make_data_dir(root, gt_dir, img_dir, exts=(".jpg", ".jpeg", ".png")):
    """data/<v>/gt và data/<v>/photos là THƯ MỤC THẬT chứa liên kết tới từng file (os.walk không đi vào thư mục symlink)."""
    for sub in ("gt", "photos"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    for f in os.listdir(gt_dir):
        link_or_copy(os.path.join(gt_dir, f), os.path.join(root, "gt", f))
    n = 0
    for f in sorted(os.listdir(img_dir)):
        if f.lower().endswith(exts) and "__" in f:
            link_or_copy(os.path.join(img_dir, f), os.path.join(root, "photos", f))
            n += 1
    return n


def parse_stem(stem):
    """<mã trang>__<điều kiện>_<máy>  ->  (mã trang, điều kiện, máy)."""
    page, _, rest = stem.partition("__")
    cond, _, phone = rest.rpartition("_")
    if not cond:
        cond, phone = rest, ""
    piece = page.rsplit("_p", 1)[0]
    return page, piece, cond, phone


def micro(rows):
    L = sum(int(r["len_full"]) for r in rows)
    return 100.0 * sum(int(r["ed_full"]) for r in rows) / max(1, L)


def boot_ci(rows, iters=1000, seed=0):
    if not rows:
        return float("nan"), float("nan")
    rnd = random.Random(seed)
    ed = [int(r["ed_full"]) for r in rows]
    ln = [int(r["len_full"]) for r in rows]
    n, vals = len(rows), []
    for _ in range(iters):
        idx = [rnd.randrange(n) for _ in range(n)]
        vals.append(100.0 * sum(ed[i] for i in idx) / max(1, sum(ln[i] for i in idx)))
    vals.sort()
    return vals[int(0.025 * iters)], vals[int(0.975 * iters) - 1]


def boot_diff(a, b, iters=1000, seed=1):
    """a, b: danh sách mẫu ghép cặp cùng thứ tự. Trả về (chênh lệch, CI thấp, CI cao, % mẫu a tốt hơn)."""
    rnd = random.Random(seed)
    ea = [int(r["ed_full"]) for r in a]
    eb = [int(r["ed_full"]) for r in b]
    ln = [int(r["len_full"]) for r in a]
    n = len(a)
    d0 = 100.0 * (sum(ea) - sum(eb)) / max(1, sum(ln))
    vals = []
    for _ in range(iters):
        idx = [rnd.randrange(n) for _ in range(n)]
        L = max(1, sum(ln[i] for i in idx))
        vals.append(100.0 * (sum(ea[i] for i in idx) - sum(eb[i] for i in idx)) / L)
    vals.sort()
    better = 100.0 * sum(1 for x, y in zip(a, b) if float(x["ser_full"]) < float(y["ser_full"])) / max(1, n)
    return d0, vals[int(0.025 * iters)], vals[int(0.975 * iters) - 1], better


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ các bước
def step_preprocess(a, log):
    pre = os.path.join(a.out, "pre")
    steps = [v for v in a.variants if v != "raw"]
    if not steps:
        return pre
    # chỉ chạy lại khi còn ảnh chưa xử lý
    imgs = [f for f in os.listdir(a.photos) if f.lower().endswith((".jpg", ".jpeg", ".png")) and "__" in f]
    missing = [f for f in imgs for v in steps
               if not any(os.path.exists(os.path.join(pre, v, os.path.splitext(f)[0] + e)) for e in (".jpg", ".png"))]
    if missing or not os.path.exists(os.path.join(pre, "report.csv")):
        sh([a.py_homr, os.path.join(a.pp_root, "rectify", "rectify_pages.py"), "--in", a.photos, "--out", pre,
            "--steps", *steps, "--debug"], log=log)
    else:
        print("[tiền xử lý] đã có đủ, bỏ qua")
    return pre


def step_engines(a, pre, log):
    eng_bin_homr = os.path.dirname(os.path.abspath(a.py_homr))
    for v in a.variants:
        img_dir = a.photos if v == "raw" else os.path.join(pre, v)
        data = os.path.join(a.out, "data", v)
        n = make_data_dir(data, a.gt, img_dir)
        print(f"\n===== biến thể {v}: {n} ảnh =====")
        omr_engines = [e for e in ("homr", "audiveris") if e in a.engines and v in a.engine_variants[e]]
        if omr_engines:
            out = os.path.join(a.out, "runs", v, "omr")
            sh([a.py_homr, a.omr_eval, "run", "--data", data, "--engines", a.engines_json, "--out", out,
                "--limit", "0", "--only", ",".join(omr_engines)], env_bin=eng_bin_homr, log=log)
            sh([a.py_homr, a.omr_eval, "score", "--data", data, "--out", out], env_bin=eng_bin_homr, log=log)
        if "smt" in a.engines and v in a.engine_variants["smt"]:
            out = os.path.join(a.out, "runs", v, "smt")
            cmd = [a.py_smt, a.smt_batch, "--smt-repo", a.smt_repo, "--model", a.smt_model, "--data", data,
                   "--out", out, "--engine", "smt", "--width", str(a.smt_width)]
            if a.smt_pages:
                cmd += ["--pages", a.smt_pages]
            sh(cmd, env_bin=os.path.dirname(os.path.abspath(a.py_smt)), log=log)
            sh([a.py_smt, a.smt_omr_eval, "score", "--data", data, "--out", out],
               env_bin=os.path.dirname(os.path.abspath(a.py_smt)), log=log)


def is_simulated(photos):
    """Ảnh do make_photo_dataset.py tạo có chữ SIMULATED trong EXIF: đọc vài ảnh đầu để đánh dấu báo cáo."""
    files = sorted(f for f in os.listdir(photos) if f.lower().endswith((".jpg", ".jpeg")))[:5]
    for f in files:
        with open(os.path.join(photos, f), "rb") as fh:
            if b"SIMULATED" in fh.read(65536):
                return True
    return False


def load_manifest(photos):
    mp = os.path.join(photos, "manifest.csv")
    if not os.path.exists(mp):
        return {}
    with open(mp, encoding="utf-8-sig") as f:
        return {os.path.splitext(r["file"])[0]: r for r in csv.DictReader(f)}


def corner_errors(pre, manifest):
    """Nếu manifest có toạ độ góc trang thật (ảnh mô phỏng), đo sai số góc của bước tìm trang."""
    rp = os.path.join(pre, "report.csv")
    if not os.path.exists(rp) or not manifest or "corners" not in next(iter(manifest.values())):
        return None
    out = []
    with open(rp, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            stem = os.path.splitext(r["file"])[0]
            m = manifest.get(stem)
            if not m or not m.get("corners"):
                continue
            t = [tuple(map(float, p.split(","))) for p in m["corners"].split(";")]
            q = [tuple(map(float, p.split(","))) for p in r["quad"].split(";")]
            err = max(max(abs(x1 - x2), abs(y1 - y2)) for (x1, y1), (x2, y2) in zip(q, t))
            diag = (float(m["width"]) ** 2 + float(m["height"]) ** 2) ** 0.5
            out.append({"stem": stem, "cond": parse_stem(stem)[2], "method": r["method"],
                        "err_px": err, "err_pct": 100 * err / diag})
    return out


def step_report(a, pre):
    rows = []
    for v in a.variants:
        for kind in ("omr", "smt"):
            ps = os.path.join(a.out, "runs", v, kind, "per_sample.csv")
            if not os.path.exists(ps):
                continue
            with open(ps, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    page, piece, cond, phone = parse_stem(r["stem"])
                    r.update(variant=v, page=page, piece=piece, cond=cond, phone=phone)
                    rows.append(r)
    if not rows:
        print("Chưa có per_sample.csv nào để tổng hợp.")
        return
    fields = ["engine", "variant", "stem", "page", "piece", "cond", "phone", "status", "parsed", "seconds",
              "ed_full", "len_full", "ser_full", "sub", "ins", "dele", "ser_pitch", "ser_rhythm", "ser_struct"]
    with open(os.path.join(a.out, "all_samples.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    by = defaultdict(list)
    for r in rows:
        by[(r["engine"], r["variant"])].append(r)
    engines = [e for e in ("homr", "audiveris", "smt") if any(k[0] == e for k in by)]
    conds = sorted({r["cond"] for r in rows})
    manifest = load_manifest(a.photos)
    synthetic = is_simulated(a.photos)
    L = [f"# Kết quả tiền xử lý: `{os.path.abspath(a.photos)}`\n",
         f"Thời điểm: {time.strftime('%Y-%m-%d %H:%M')}. "
         + ("**DỮ LIỆU MÔ PHỎNG — chỉ dùng để kiểm tra quy trình và chọn tham số, không phải kết quả ảnh thật.**\n"
            if synthetic else "Ảnh chụp thật.\n"),
         "SER (%) micro-average; khoảng tin cậy 95% bootstrap 1.000 lần. Mẫu engine không trả kết quả tính SER = 100%.\n"]

    # Bảng 1: engine x biến thể
    L.append("\n## 1. SER theo engine và biến thể tiền xử lý\n")
    head = ["Engine", "Biến thể", "n", "SER [95% CI]", "Thất bại (%)", "Thay/Chèn/Xoá (%)", "Thời gian TB (s)"]
    t = []
    for e in engines:
        for v in a.variants:
            R = by.get((e, v))
            if not R:
                continue
            lo, hi = boot_ci(R)
            fail = 100.0 * sum(1 for r in R if r["parsed"] in ("0", "")) / len(R)
            s, i, d = (sum(int(r[k] or 0) for r in R) for k in ("sub", "ins", "dele"))
            tot = max(1, s + i + d)
            sec = sum(float(r["seconds"] or 0) for r in R) / len(R)
            t.append([e, v, len(R), f"{micro(R):.1f} [{lo:.1f}–{hi:.1f}]", f"{fail:.0f}",
                      f"{100*s/tot:.0f}/{100*i/tot:.0f}/{100*d/tot:.0f}", f"{sec:.1f}"])
    L.append(md_table(head, t))

    # Bảng 2: engine x biến thể x điều kiện
    L.append("\n## 2. SER theo điều kiện chụp\n")
    head = ["Engine", "Biến thể"] + conds
    t = []
    for e in engines:
        for v in a.variants:
            R = by.get((e, v))
            if not R:
                continue
            row = [e, v]
            for c in conds:
                Rc = [r for r in R if r["cond"] == c]
                row.append(f"{micro(Rc):.1f}" if Rc else "–")
            t.append(row)
    L.append(md_table(head, t))

    # Bảng 3: chênh lệch so với ảnh gốc (ghép cặp)
    L.append("\n## 3. Hiệu quả từng biến thể so với ảnh như chụp (raw), ghép cặp trên cùng ảnh\n")
    L.append("Âm = biến thể tốt hơn raw. Cột cuối: % ảnh biến thể có SER thấp hơn raw.\n\n")
    head = ["Engine", "Biến thể", "n cặp", "Chênh SER (điểm %)", "95% CI", "Tốt hơn raw (% ảnh)"]
    t = []
    for e in engines:
        base = {r["stem"]: r for r in by.get((e, "raw"), [])}
        for v in a.variants:
            if v == "raw" or (e, v) not in by:
                continue
            pairs = [(r, base[r["stem"]]) for r in by[(e, v)] if r["stem"] in base]
            if not pairs:
                continue
            d, lo, hi, better = boot_diff([p[0] for p in pairs], [p[1] for p in pairs])
            t.append([e, v, len(pairs), f"{d:+.1f}", f"[{lo:+.1f}, {hi:+.1f}]", f"{better:.0f}"])
    L.append(md_table(head, t))

    # Bảng 4: điện thoại (chỉ các điều kiện có cả hai máy)
    phones = sorted({r["phone"] for r in rows if r["phone"]})
    if len(phones) > 1:
        L.append("\n## 4. Ảnh hưởng của điện thoại (chỉ các điều kiện chụp bằng cả hai máy)\n")
        both = [c for c in conds if len({r["phone"] for r in rows if r["cond"] == c}) > 1]
        head = ["Engine", "Biến thể", "Điều kiện"] + phones
        t = []
        for e in engines:
            for v in a.variants:
                for c in both:
                    R = [r for r in by.get((e, v), []) if r["cond"] == c]
                    if R:
                        t.append([e, v, c] + [f"{micro([r for r in R if r['phone'] == p]):.1f}"
                                              if any(r["phone"] == p for r in R) else "–" for p in phones])
        L.append(md_table(head, t))

    # Bảng 5: bước tìm trang
    rp = os.path.join(pre, "report.csv")
    if os.path.exists(rp):
        L.append("\n## 5. Bước tìm trang (rectify_pages.py)\n")
        with open(rp, encoding="utf-8") as f:
            rep = list(csv.DictReader(f))
        cnt = defaultdict(lambda: defaultdict(int))
        for r in rep:
            cnt[parse_stem(os.path.splitext(r["file"])[0])[2]][r["method"].split("/")[0]] += 1
        methods = sorted({m for c in cnt.values() for m in c})
        L.append(md_table(["Điều kiện"] + methods, [[c] + [cnt[c].get(m, 0) for m in methods] for c in sorted(cnt)]))
        ce = corner_errors(pre, manifest)
        if ce:
            L.append("\nSai số góc trang so với toạ độ thật của ảnh mô phỏng (% đường chéo ảnh):\n\n")
            g = defaultdict(list)
            for r in ce:
                g[r["cond"]].append(r["err_pct"])
            L.append(md_table(["Điều kiện", "n", "Trung bình", "Lớn nhất", "Ảnh sai > 2%"],
                              [[c, len(x), f"{sum(x)/len(x):.2f}", f"{max(x):.2f}", sum(1 for e in x if e > 2)]
                               for c, x in sorted(g.items())]))
    with open(os.path.join(a.out, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nĐã ghi {os.path.join(a.out, 'RESULTS.md')} và all_samples.csv ({len(rows)} dòng)")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = "/mnt/g/doan/minh"
    ap.add_argument("--photos", required=True, help="thư mục ảnh (tên <mã trang>__<điều kiện>_<máy>.jpg)")
    ap.add_argument("--gt", default=f"{root}/pp_study/print_set2/out_set2/gt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", nargs="+", default=ALL_VARIANTS, choices=ALL_VARIANTS)
    ap.add_argument("--engines", default="homr,audiveris,smt")
    ap.add_argument("--smt-variants", nargs="+", help="ghi đè biến thể chạy SMT++ (mặc định raw rect norm bbox)")
    ap.add_argument("--smt-pages", help="chỉ chạy SMT++ trên các trang này (để chạy thử nhanh), vd bach_inv07_p1,brahms_118_2_p3")
    ap.add_argument("--steps", nargs="+", default=["pre", "run", "report"], choices=["pre", "run", "report"])
    ap.add_argument("--pp-root", default=f"{root}/pp_study")
    ap.add_argument("--py-homr", default=f"{root}/.venv/bin/python", help="python của venv có homr + opencv")
    ap.add_argument("--py-smt", default=f"{root}/.venv-smt/bin/python")
    ap.add_argument("--omr-eval", default=f"{root}/smt_eval/omr_eval.py")
    ap.add_argument("--smt-omr-eval", default=f"{root}/smt_eval/omr_eval.py")
    ap.add_argument("--engines-json", default=f"{root}/omr_eval/engines.json")
    ap.add_argument("--smt-batch", default=f"{root}/smt_eval/smt_batch.py")
    ap.add_argument("--smt-repo", default="/mnt/g/tools/SMT")
    ap.add_argument("--smt-model", default="PRAIG/smt-fp-grandstaff")
    ap.add_argument("--smt-width", type=int, default=2100)
    a = ap.parse_args()
    a.engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    a.engine_variants = dict(DEFAULT_ENGINE_VARIANTS)
    if a.smt_variants:
        a.engine_variants["smt"] = a.smt_variants
    a.photos, a.gt, a.out = (os.path.abspath(p) for p in (a.photos, a.gt, a.out))
    os.makedirs(a.out, exist_ok=True)
    log = os.path.join(a.out, "pipeline.log")
    json.dump({k: v for k, v in vars(a).items()}, open(os.path.join(a.out, "pipeline_args.json"), "w",
              encoding="utf-8"), indent=2, ensure_ascii=False)

    pre = os.path.join(a.out, "pre")
    if "pre" in a.steps:
        pre = step_preprocess(a, log)
    if "run" in a.steps:
        step_engines(a, pre, log)
    if "report" in a.steps:
        step_report(a, pre)


if __name__ == "__main__":
    main()
