#!/bin/bash
# make_release.sh - Build a clean GitHub project + photo archives for the paper
#   "Staff-Guided Rectification of Phone Photographs for Optical Music Recognition".
# Usage (from /mnt/g/doan/minh):
#   bash pp_study/release/make_release.sh <github_user> [out_dir]
# Produces:
#   <out_dir>/camera-omr-staffrect/   git repository ready to push (code, references, geometry, results)
#   <out_dir>/zenodo/photos_ip14pm.zip, photos_x12sp.zip   redacted photographs for Zenodo (too large for GitHub)
set -e
GHUSER=${1:?usage: make_release.sh <github_user> [out_dir]}
OUT=${2:-/mnt/g/doan/release}
SRC=/mnt/g/doan/minh
REPO=$OUT/camera-omr-staffrect
NAME="Nguyen Quang Trung"
EMAIL="trungnq1999@gmail.com"
cd $SRC
sha256sum -c frozen/FROZEN.sha256 frozen/FROZEN_V2.sha256 frozen/FROZEN_V22.sha256 >/dev/null || { echo "Frozen files changed - stop."; exit 1; }
rm -rf $REPO && mkdir -p $REPO/{code,benchmark,results,frozen}

# ---------- code ----------
for d in rectify rectify_v2 rectify_v22 pipeline tools sim baselines release; do
  [ -d pp_study/$d ] && cp -r pp_study/$d $REPO/code/
done
mkdir -p $REPO/code/print_set2 $REPO/code/smt_eval $REPO/code/omr_eval
cp pp_study/print_set2/*.py pp_study/print_set2/*.sh $REPO/code/print_set2/ 2>/dev/null || true
cp smt_eval/*.py $REPO/code/smt_eval/
cp omr_eval/engines.json $REPO/code/omr_eval/
rm -f $REPO/code/release/all_results.csv $REPO/code/release/stats.json
find $REPO/code -name "__pycache__" -prune -exec rm -rf {} + ; find $REPO/code -name "*.pyc" -delete
find $REPO/code -name "*.v1031" -delete

# ---------- benchmark (references, prints, true geometry) ----------
cp -r pp_study/print_set2/out_set2/gt $REPO/benchmark/references_musicxml
cp pp_study/print_set2/out_set2/manifest.csv $REPO/benchmark/pages.csv
mkdir -p $REPO/benchmark/prints && cp pp_study/print_set2/out_set2/print/*.pdf $REPO/benchmark/prints/
mkdir -p $REPO/benchmark/true_geometry
cp results_real/diag.csv $REPO/benchmark/true_geometry/ip14pm.csv
cp results_x12sp_v1/diag.csv $REPO/benchmark/true_geometry/x12sp.csv

# ---------- results ----------
cp pp_study/release/all_results.csv pp_study/release/stats.json $REPO/results/
for d in results_real results_oracle_rot results_oracle_rect results_v2_raw results_v2_norm results_v2_bin \
         results_v21fix_raw results_v21fix_norm results_v21fix_bin results_ip14pm_v22_* results_x12sp_* \
         results_ip14pm_uvdoc* results_sim; do
  for x in $d; do
    [ -d "$x" ] || continue
    mkdir -p $REPO/results/$x
    for f in RESULTS.md all_samples.csv pipeline_args.json pre/report.csv diag.csv; do
      [ -f "$x/$f" ] && cp "$x/$f" "$REPO/results/$x/$(echo $f | tr / _)"
    done
  done
done
for x in v2_ip14pm v2_x12sp v22_ip14pm v22_x12sp uvdoc_ip14pm uvdoc_x12sp uvdocrot_ip14pm uvdocrot_x12sp; do
  [ -d $x ] || continue; mkdir -p $REPO/results/$x
  cp $x/*.csv $REPO/results/$x/ 2>/dev/null || true
done
cp frozen/*.sha256 frozen/*DATE*.txt frozen/FROZEN_NOTE.txt $REPO/frozen/ 2>/dev/null || true

# ---------- top-level files ----------
cat > $REPO/README.md <<MD
# Staff-guided rectification of phone photographs for optical music recognition

Code, benchmark references, true page geometry and per-photograph results for the paper

> N. Q. Trung, *Staff-Guided Rectification of Phone Photographs for Optical Music Recognition:
> A Cross-Device Study with Oracle Error Decomposition*, submitted to Vietnam Journal of Computer Science.

## Contents
| Folder | What |
|---|---|
| \`benchmark/prints\` | the 32 printed A4 pages (PDF) |
| \`benchmark/references_musicxml\` | symbol-level reference of every page |
| \`benchmark/pages.csv\` | page list (piece, composer, source, licence) |
| \`benchmark/true_geometry\` | per photograph: true orientation, paper corners (ORB+RANSAC against the print), page area, tilt |
| \`code/rectify\` | v1: page-boundary rectification tuned on simulation (frozen) |
| \`code/rectify_v2\` | v2.1: staff-guided rectification (frozen on the iPhone before the held-out test) |
| \`code/rectify_v22\` | v2.2: revised after the held-out test |
| \`code/baselines\` | UVDoc baseline wrapper |
| \`code/pipeline\`, \`code/smt_eval\` | engine runner and SER scoring (music21 tokens, bootstrap CIs) |
| \`code/tools\` | true-geometry diagnosis, oracle pipelines, geometric evaluation, photo renaming |
| \`results\` | per-photograph SER of every engine, variant and pipeline; \`all_results.csv\` is the consolidated table used in the paper |
| \`frozen\` | SHA-256 hashes and dates of every frozen configuration |

The photographs (2 phones x 192) are archived separately on Zenodo (link in the paper). Backgrounds outside the page are blurred
in photographs that showed other documents, and location metadata were removed.

## Reproduce
\`\`\`bash
python -m venv .venv && . .venv/bin/activate
pip install opencv-python numpy scipy pillow pymupdf music21 pandas
python code/rectify_v22/rectify_v2.py --photos photos/ip14pm --out v22_ip14pm
python code/tools/eval_v2_geometry.py --diag benchmark/true_geometry/ip14pm.csv --report v22_ip14pm/report_v2.csv
\`\`\`
Engines (homr, Audiveris, SMT++) are installed separately; see \`code/pipeline/HUONG_DAN_PIPELINE.md\` and \`code/omr_eval/engines.json\`.
Some helper documents are in Vietnamese.

## Licences
* Code: MIT (see LICENSE).
* References and prints are derived from KernScores and ASAP encodings (CC BY-NC-SA 4.0) and the music21 corpus; they are distributed
  under CC BY-NC-SA 4.0. The musical works are in the public domain.
* Clef templates in \`code/rectify_v2*/clef_tpl_f.npy\` are cut from renderings of other public-domain pieces.
MD
cat > $REPO/LICENSE <<LIC
MIT License

Copyright (c) 2026 $NAME

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
LIC
cat > $REPO/CITATION.cff <<CFF
cff-version: 1.2.0
message: "If you use this code or benchmark, please cite the paper."
title: "Staff-guided rectification of phone photographs for optical music recognition"
authors:
  - family-names: Nguyen
    given-names: Quang Trung
    affiliation: "Vietnam Youth Academy"
license: MIT
repository-code: "https://github.com/$GHUSER/camera-omr-staffrect"
CFF
cat > $REPO/.gitignore <<GI
__pycache__/
*.pyc
.venv/
photos/
GI

# ---------- git ----------
cd $REPO
git init -q -b main
git config user.name "$NAME"
git config user.email "$EMAIL"
git add .
git commit -q -m "Code, benchmark references, true geometry and results for the staff-guided rectification paper"
echo "Repository: $REPO  ($(du -sh $REPO | cut -f1))"
find $REPO -type f -size +50M -exec echo "WARNING >50MB (GitHub limit 100MB):" {} \;

# ---------- photographs for Zenodo ----------
cd $SRC
mkdir -p $OUT/zenodo
.venv/bin/python pp_study/release/redact_photos.py --photos real_photos2 --diag results_real/diag.csv --out $OUT/zenodo/ip14pm
.venv/bin/python pp_study/release/redact_photos.py --photos real_photos3 --diag results_x12sp_v1/diag.csv --out $OUT/zenodo/x12sp
(cd $OUT/zenodo && rm -f photos_ip14pm.zip photos_x12sp.zip && zip -q -r photos_ip14pm.zip ip14pm && zip -q -r photos_x12sp.zip x12sp)
echo
echo "NEXT STEPS"
echo " 1. Open the blurred photos in $OUT/zenodo/*/ (cluttered condition) and check that no name or personal data is readable."
echo " 2. Create an EMPTY public repository named camera-omr-staffrect on https://github.com/new (account $GHUSER)."
echo " 3. cd $REPO && git remote add origin https://github.com/$GHUSER/camera-omr-staffrect.git && git push -u origin main"
echo "    (GitHub asks for a Personal Access Token instead of the password: Settings > Developer settings > Tokens)"
echo " 4. Upload $OUT/zenodo/photos_*.zip to https://zenodo.org (log in with GitHub), licence CC BY 4.0, and copy the DOI into the paper."
