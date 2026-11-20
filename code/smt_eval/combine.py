#!/usr/bin/env python3
"""
combine.py - Gộp kết quả SMT++ (thư mục mới) với kết quả homr/Audiveris đã có vào MỘT thư mục so sánh mới,
để chấm cả ba engine trên cùng tập ảnh. Thư mục kết quả cũ chỉ được ĐỌC, không bị sửa.

    python combine.py --src /mnt/g/doan/minh/results_real /mnt/g/doan/minh/results_smt \
                      --out /mnt/g/doan/minh/results_compare
    python omr_eval.py score --data /mnt/g/doan/minh/real_photos --out /mnt/g/doan/minh/results_compare
"""
import argparse
import csv
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", nargs="+", required=True, help="các thư mục kết quả cần gộp (chỉ đọc)")
    ap.add_argument("--out", required=True, help="thư mục so sánh mới (không được trùng thư mục nguồn)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if out in {os.path.abspath(s) for s in a.src}:
        raise SystemExit("--out phải là thư mục mới, khác các thư mục nguồn.")
    os.makedirs(out, exist_ok=True)

    rows, engines, env_main = {}, {}, None
    fields = ["engine", "stem", "status", "returncode", "seconds", "pred", "stderr_tail"]
    for src in a.src:
        src = os.path.abspath(src)
        with open(os.path.join(src, "runs.csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                p = r.get("pred", "")
                if p and not os.path.isabs(p):          # đường dẫn tương đối từ lần chạy cũ
                    cands = [os.path.join(os.path.dirname(src), p), os.path.join(src, p),
                             os.path.join(src, r["engine"], "pred", os.path.basename(p))]
                    p = next((c for c in cands if os.path.exists(c)), p)
                r["pred"] = p
                rows[(r["engine"], r["stem"])] = {k: r.get(k, "") for k in fields}   # bản ghi sau cùng thắng
        env_path = os.path.join(src, "env.json")
        if os.path.exists(env_path):
            env = json.load(open(env_path, encoding="utf-8"))
            engines.update(env.get("engines", {}))
            env_main = env_main or env

    with open(os.path.join(out, "runs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows.values())
    env = dict(env_main or {})
    env["engines"] = engines
    env["combined_from"] = [os.path.abspath(s) for s in a.src]
    json.dump(env, open(os.path.join(out, "env.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    per_engine = {}
    for (e, _), r in rows.items():
        per_engine[e] = per_engine.get(e, 0) + 1
    print("Đã gộp:", ", ".join(f"{e} {n}" for e, n in sorted(per_engine.items())), "->", out)


if __name__ == "__main__":
    main()
