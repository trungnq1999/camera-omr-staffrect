#!/usr/bin/env python3
"""
make_print_set2.py - Tạo bộ bản nhạc MỚI để in và chụp cho nghiên cứu tiền xử lý ảnh (không trùng tập AMI2026).

Chạy:  SRC=<thư mục nguồn> python make_print_set2.py out_set2

Với mỗi bản nhạc nguồn (kern hoặc MusicXML):
  1. Verovio dàn trang khổ A4 -> mỗi trang một SVG/PDF để in.
  2. Đếm ô nhịp trên từng trang, cắt đúng các ô nhịp đó từ bản nguồn bằng music21
     -> nhãn gt/<id>_p<k>.musicxml (khoá, hoá biểu, nhịp được mang sang đầu trang).
  3. Kiểm tra: ghép token nhãn các trang phải khớp token cả bản.

Kết quả: out/print/<id>.pdf, out/print/ALL_PAGES.pdf, out/gt/*.musicxml, out/preview/*.png, out/manifest.csv
"""
import csv
import io
import os
import re
import sys

import cairosvg
import verovio
from music21 import converter
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, os.environ.get("OMR_EVAL", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "omr_eval")))
from omr_eval import stream_to_tokens  # noqa: E402

SRC = os.environ.get("SRC", "/mnt/g/doan/minh/src_scores")
# id, nguồn, tác giả, tên bản, giấy phép mã hoá, các trang in (None = tất cả)
PIECES = [
    ("haydn_xvi12_1", f"{SRC}/haydn-piano-sonatas/kern/sonata12-1.krn", "J. Haydn", "Sonata in A major, Hob. XVI:12, I. Andante", "KernScores, C. Sapp (CC BY-NC-SA 4.0)", None),
    ("haydn_xvi12_2", f"{SRC}/haydn-piano-sonatas/kern/sonata12-2.krn", "J. Haydn", "Sonata in A major, Hob. XVI:12, II. Menuetto", "KernScores, C. Sapp (CC BY-NC-SA 4.0)", None),
    ("haydn_xvi14_2", f"{SRC}/haydn-piano-sonatas/kern/sonata16-2.krn", "J. Haydn", "Sonata in D major, Hob. XVI:14, II. Menuetto", "KernScores, C. Sapp (CC BY-NC-SA 4.0)", None),
    ("haydn_xvi22_1", f"{SRC}/haydn-piano-sonatas/kern/sonata37-1.krn", "J. Haydn", "Sonata in E major, Hob. XVI:22, I. Allegro moderato", "KernScores, C. Sapp (CC BY-NC-SA 4.0)", [1, 2, 3, 4]),
    ("haydn_xvi30_3", f"{SRC}/haydn-piano-sonatas/kern/sonata45-3a.krn", "J. Haydn", "Sonata in A major, Hob. XVI:30, III. Tema (Tempo di Menuetto)", "KernScores, C. Sapp (CC BY-NC-SA 4.0)", None),
    ("bach_inv07", f"{SRC}/inventions/kern/inven07.krn", "J.S. Bach", "Invention No. 7, BWV 778", "KernScores (Humdrum tools)", None),
    ("bach_inv09", f"{SRC}/inventions/kern/inven09.krn", "J.S. Bach", "Invention No. 9, BWV 780", "KernScores (Humdrum tools)", None),
    ("bach_inv11", f"{SRC}/inventions/kern/inven11.krn", "J.S. Bach", "Invention No. 11, BWV 782", "KernScores (Humdrum tools)", None),
    ("bach_inv12", f"{SRC}/inventions/kern/inven12.krn", "J.S. Bach", "Invention No. 12, BWV 783", "KernScores (Humdrum tools)", None),
    ("brahms_118_2", f"{SRC}/asap-dataset/Brahms/Six_Pieces_op_118/2/xml_score.musicxml", "J. Brahms", "Intermezzo Op. 118 No. 2", "ASAP (CC BY-NC-SA 4.0)", None),
    ("schumann_arabeske", f"{SRC}/asap-dataset/Schumann/Arabeske/xml_score.musicxml", "R. Schumann", "Arabeske Op. 18", "ASAP (CC BY-NC-SA 4.0)", [1, 2, 3, 4]),
    ("schoenberg_19_2", "corpus:schoenberg/opus19/movement2.mxl", "A. Schoenberg", "Sechs kleine Klavierstücke Op. 19, No. 2", "music21 corpus", None),
    ("schoenberg_19_6", "corpus:schoenberg/opus19/movement6.mxl", "A. Schoenberg", "Sechs kleine Klavierstücke Op. 19, No. 6", "music21 corpus", None),
]

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
OPTIONS = {
    "pageWidth": 2100, "pageHeight": 2970,          # A4, đơn vị 0,1 mm
    "pageMarginTop": 150, "pageMarginBottom": 150, "pageMarginLeft": 150, "pageMarginRight": 150,
    "scale": 40,                                      # khoảng cách dòng kẻ ~1,8 mm, gần bản in giáo trình
    "breaks": "auto", "adjustPageHeight": False, "footer": "none", "header": "auto",
    "mmOutput": True, "svgViewBox": True,
}


def clean_score(score, title, composer):
    """Bỏ chỉ số metronome sinh tự động, tên bè và thông tin xuất bản rườm rà; giữ tên bản và tác giả."""
    from music21 import instrument, metadata, tempo
    from music21 import text
    for tb in list(score.getElementsByClass(text.TextBox)):
        score.remove(tb)
    for el in list(score.recurse().getElementsByClass([tempo.MetronomeMark])):
        if el.activeSite is not None:
            el.activeSite.remove(el)
    for part in score.parts:
        part.partName = ""
        part.partAbbreviation = ""
        for ins in part.recurse().getElementsByClass(instrument.Instrument):
            ins.partName = ""
            ins.partAbbreviation = ""
            ins.instrumentName = ""
            ins.instrumentAbbreviation = ""
    md = metadata.Metadata()
    md.title = title
    md.composer = composer
    score.metadata = md


def drop_carried_time_signature(score, lab, start):
    """
    Trang 2 trở đi chỉ in khoá và hoá biểu ở đầu hệ thống, không in lại số chỉ nhịp
    (trừ khi bản nhạc đổi nhịp đúng ô đó). music21 luôn ghi số chỉ nhịp vào ô đầu của đoạn
    trích, nên xoá thẻ <time> của ô đầu trong file MusicXML để nhãn khớp với trang in.
    """
    import xml.etree.ElementTree as ET
    from music21 import meter
    src_meas = score.parts[0].getElementsByClass("Measure")
    if start < len(src_meas) and src_meas[start].getElementsByClass(meter.TimeSignature):
        return  # đổi nhịp đúng ô đầu trang: có in, giữ nguyên
    with open(lab, encoding="utf-8") as f:
        head = f.read().split("<score-partwise", 1)[0]
    tree = ET.parse(lab)
    for part in tree.getroot().iter("part"):
        first = part.find("measure")
        if first is None:
            continue
        for attrs in first.findall("attributes"):
            for t in attrs.findall("time"):
                attrs.remove(t)
    body = ET.tostring(tree.getroot(), encoding="unicode")
    with open(lab, "w", encoding="utf-8") as f:
        f.write(head + body)


def resolve(path):
    if path.startswith("corpus:"):
        from music21 import corpus
        return str(corpus.getWork(path[7:]))
    return path


def main():
    for d in ("print", "gt", "preview", "svg"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    tk = verovio.toolkit()
    tk.setOptions(OPTIONS)
    all_pdf = PdfWriter()
    rows = []
    for pid, src, composer, title, lic, keep in PIECES:
        # chuẩn hoá: mọi nguồn -> MusicXML qua music21; dùng chung file này để dàn trang và cắt nhãn
        try:
            score = converter.parse(resolve(src))
        except Exception as e:
            print(f"[{pid}] music21 không đọc được nguồn: {e}")
            continue
        clean_score(score, title, composer)
        os.makedirs(os.path.join(OUT, "source"), exist_ok=True)
        path = os.path.join(OUT, "source", f"{pid}.musicxml")
        score.write("musicxml", fp=path)
        score = converter.parse(path)
        if not tk.loadFile(path):
            print(f"[{pid}] Verovio không đọc được {path}")
            continue
        n_pages = tk.getPageCount()
        n_meas = len(score.parts[0].getElementsByClass("Measure"))
        per_page = []
        piece_pdf = PdfWriter()
        for p in range(1, n_pages + 1):
            svg = tk.renderToSVG(p)
            per_page.append(len(re.findall(r'class="measure[" ]', svg)))
            with open(os.path.join(OUT, "svg", f"{pid}_p{p}.svg"), "w") as f:
                f.write(svg)
            pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode())
            if keep is None or p in keep:
                for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
                    piece_pdf.add_page(page)
                    all_pdf.add_page(page)
            cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT, "preview", f"{pid}_p{p}.png"),
                             output_width=1240, background_color="white")
        with open(os.path.join(OUT, "print", f"{pid}.pdf"), "wb") as f:
            piece_pdf.write(f)
        status = "ok" if sum(per_page) == n_meas else f"lệch: verovio {sum(per_page)} / music21 {n_meas} ô nhịp"
        # cắt nhãn theo trang
        start = 0
        page_tokens = []
        for p, k in enumerate(per_page, 1):
            lab = os.path.join(OUT, "gt", f"{pid}_p{p}.musicxml")
            if keep is not None and p not in keep:
                start += k
                continue
            if status == "ok":
                ex = score.measures(start, start + k, indicesNotNumbers=True)  # chỉ số từ 0, không gồm cuối
                try:
                    ex.write("musicxml", fp=lab)
                except Exception as e:                   # vd. trường độ liên ba bị cắt ngang
                    print(f"[{pid}] trang {p}: không ghi được nhãn ({str(e)[:80]})")
                    status = "lỗi nhãn"
                    page_tokens.append([])
                    rows.append({"page_id": f"{pid}_p{p}", "piece": pid, "composer": composer, "title": title,
                                 "page": p, "pages": n_pages, "first_measure_idx": start + 1, "measures": k,
                                 "tokens": "", "printed_of": f"{p}/{n_pages}", "source": src,
                                 "encoding_license": lic, "status": status})
                    start += k
                    continue
                if p > 1:
                    drop_carried_time_signature(score, lab, start)
                t = stream_to_tokens(converter.parse(lab))
                page_tokens.append(t["full"])
            rows.append({"page_id": f"{pid}_p{p}", "piece": pid, "composer": composer, "title": title,
                         "page": p, "pages": n_pages, "first_measure_idx": start + 1, "measures": k,
                         "tokens": len(page_tokens[-1]) if status == "ok" else "", "printed_of": f"{p}/{n_pages}", "source": src,
                         "encoding_license": lic, "status": status})
            start += k
        print(f"[{pid}] {n_pages} trang, ô nhịp/trang {per_page}, {status}")
    with open(os.path.join(OUT, "print", "ALL_PAGES.pdf"), "wb") as f:
        all_pdf.write(f)
    with open(os.path.join(OUT, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\nTổng: {len(rows)} trang, {len(ok)} trang có nhãn hợp lệ.")


if __name__ == "__main__":
    main()
