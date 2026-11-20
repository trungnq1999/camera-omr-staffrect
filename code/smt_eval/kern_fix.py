#!/usr/bin/env python3
"""
kern_fix.py - Làm sạch chuỗi **kern do SMT++ sinh ra để music21 đọc được.

SMT++ sinh phần thân của file kern nhưng KHÔNG có dòng header '**kern', không có dòng kết thúc '*-',
và khi mô hình lỗi có thể sinh dòng sai số cột. Hàm sanitize():
  - thêm header '**kern' và dòng kết thúc '*-' theo đúng số spine;
  - theo dõi tách/gộp spine (*^, *v) như Humdrum;
  - khi mô hình quên dòng *^ / *v (dòng dữ liệu có số cột khác số spine hiện tại), tự chèn dòng
    tách/gộp còn thiếu; chỉ bỏ dòng khi không thể khớp (đếm lại, in ra để báo cáo).
Không sửa nội dung nốt: lỗi nhận dạng của mô hình vẫn được tính đầy đủ khi chấm.

Sửa lại các dự đoán đã chạy (không cần chạy lại mô hình):
  python kern_fix.py /mnt/g/doan/minh/results_smt_try
  -> bản gốc được giữ ở <engine>/decoded/<stem>.krn, bản đã làm sạch ghi đè <engine>/pred/<stem>.krn
"""
import glob
import os
import re
import shutil
import sys


def _is_interp(fields):
    return all(f.startswith("*") for f in fields)


def _apply_manip(fields, staff):
    """Áp một dòng tách/gộp spine lên danh sách staff-id của từng cột. Trả về staff mới hoặc None nếu vô lý."""
    out, i = [], 0
    while i < len(fields):
        f = fields[i]
        if f == "*^":
            out += [staff[i], staff[i]]
        elif f == "*v":
            j = i
            while j + 1 < len(fields) and fields[j + 1] == "*v":
                j += 1
            if j == i or len(set(staff[i:j + 1])) != 1:   # *v đơn lẻ, hoặc gộp hai khuông khác nhau
                return None
            out.append(staff[i])
            i = j
        else:
            out.append(staff[i])
        i += 1
    return out


def _resync(staff, k):
    """
    Dòng dữ liệu có k cột nhưng hiện có len(staff) spine (mô hình quên dòng *^ hoặc *v).
    Sinh các dòng tách/gộp còn thiếu: tách cột phải nhất (khuông trên), gộp cặp cột kề nhau
    phải nhất cùng khuông. Trả về (các dòng chèn, staff mới) hoặc (None, staff) nếu không được.
    """
    lines, st = [], list(staff)
    while len(st) < k:
        if len(st) >= 6:
            return None, staff
        lines.append("\t".join(["*"] * (len(st) - 1) + ["*^"]))
        st = st + [st[-1]]
    while len(st) > k:
        j = next((j for j in range(len(st) - 2, -1, -1) if st[j] == st[j + 1]), None)
        if j is None:
            return None, staff
        f = ["*"] * len(st)
        f[j] = f[j + 1] = "*v"
        lines.append("\t".join(f))
        st = st[:j + 1] + st[j + 2:]
    return lines, st


def sanitize(text):
    """
    Trả về (kern_text, số_dòng_bị_bỏ, số_spine_ban_đầu).
    SMT++ hay sinh dòng 3 cột mà quên dòng '*^' trước đó, hoặc sinh '*^' rồi lại quay về 2 cột.
    Thay vì bỏ các dòng đó, hàm tự chèn dòng tách/gộp spine cho khớp số cột của dòng dữ liệu.
    """
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("<b>", "\n").replace("<t>", "\t").replace("<s>", " ")
    t = re.sub(r"<bos>|<eos>|<pad>", "", t, flags=re.I)
    t = t.replace("@", "").replace("·", "")
    lines = [l.rstrip("\n").rstrip(" ") for l in t.split("\n")]
    lines = [l for l in lines if l.strip() and not l.startswith("!")]
    lines = [l for l in lines if not l.lstrip().startswith("**")]          # header cũ (nếu có) -> dựng lại
    if not lines:
        return "", 0, 0

    def split(l):
        return [f.strip() for f in (l.split("\t") if "\t" in l else l.split())]

    n0 = len(split(lines[0]))
    staff = list(range(n0))           # staff-id của từng cột (0 = khuông dưới/trái)
    out, dropped = [], 0
    for l in lines:
        fields = split(l)
        if any(f == "" for f in fields):
            dropped += 1
            continue
        if _is_interp(fields):
            if "*-" in fields:                       # kết thúc giữa chừng: bỏ, sẽ kết thúc ở cuối
                dropped += 1
                continue
            manip = any(f in ("*^", "*v") for f in fields)
            if len(fields) != len(staff):
                dropped += 1                         # vd. '*\t*v\t*v' khi chỉ có 2 spine
                continue
            if manip:
                new = _apply_manip(fields, staff)
                if new is None or not 1 <= len(new) <= 8:
                    dropped += 1
                    continue
                staff = new
            out.append("\t".join(fields))
            continue
        if any(f.startswith("*") for f in fields):
            # dòng lẫn nốt và lệnh spine (vd. '8\t*-', '8\t*v\t*'): music21 hiểu '*-' là đóng spine giữa
            # dòng dữ liệu rồi báo lỗi 'Could not determine spineType' -> bỏ dòng hỏng này
            dropped += 1
            continue
        if len(fields) != len(staff):
            ins, st = _resync(staff, len(fields))
            if ins is None:
                dropped += 1
                continue
            out += ins
            staff = st
        out.append("\t".join(fields))
    body = ["\t".join(["**kern"] * n0)] + out + ["\t".join(["*-"] * len(staff))]
    return "\n".join(body) + "\n", dropped, n0


def fix_dir(root):
    total = 0
    for pp in sorted(glob.glob(os.path.join(root, "*", "pred", "*.krn"))):
        eng_dir = os.path.dirname(os.path.dirname(pp))
        bak_dir = os.path.join(eng_dir, "decoded")
        os.makedirs(bak_dir, exist_ok=True)
        bak = os.path.join(bak_dir, os.path.basename(pp))
        if not os.path.exists(bak):                      # chỉ sao lưu lần đầu
            shutil.copy2(pp, bak)
        text, dropped, n0 = sanitize(open(bak, encoding="utf-8", errors="ignore").read())
        with open(pp, "w", encoding="utf-8") as f:
            f.write(text)
        total += 1
        print(f"{os.path.relpath(pp, root)}: {n0} spine, bỏ {dropped} dòng không khớp, còn {text.count(chr(10))} dòng")
    print(f"Đã làm sạch {total} file.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fix_dir(sys.argv[1])
