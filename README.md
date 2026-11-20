# Staff-guided rectification of phone photographs for optical music recognition

Code, benchmark references, true page geometry and per-photograph results for the paper

> N. Q. Trung, *Staff-Guided Rectification of Phone Photographs for Optical Music Recognition:
> A Cross-Device Study with Oracle Error Decomposition*, submitted to Vietnam Journal of Computer Science.

## Contents
| Folder | What |
|---|---|
| `benchmark/prints` | the 32 printed A4 pages (PDF) |
| `benchmark/references_musicxml` | symbol-level reference of every page |
| `benchmark/pages.csv` | page list (piece, composer, source, licence) |
| `benchmark/true_geometry` | per photograph: true orientation, paper corners (ORB+RANSAC against the print), page area, tilt |
| `code/rectify` | v1: page-boundary rectification tuned on simulation (frozen) |
| `code/rectify_v2` | v2.1: staff-guided rectification (frozen on the iPhone before the held-out test) |
| `code/rectify_v22` | v2.2: revised after the held-out test |
| `code/baselines` | UVDoc baseline wrapper |
| `code/pipeline`, `code/smt_eval` | engine runner and SER scoring (music21 tokens, bootstrap CIs) |
| `code/tools` | true-geometry diagnosis, oracle pipelines, geometric evaluation, photo renaming |
| `results` | per-photograph SER of every engine, variant and pipeline; `all_results.csv` is the consolidated table used in the paper |
| `frozen` | SHA-256 hashes and dates of every frozen configuration |

The photographs (2 phones x 192) are archived separately on Zenodo (link in the paper). Backgrounds outside the page are blurred
in photographs that showed other documents, and location metadata were removed.

## Reproduce
```bash
python -m venv .venv && . .venv/bin/activate
pip install opencv-python numpy scipy pillow pymupdf music21 pandas
python code/rectify_v22/rectify_v2.py --photos photos/ip14pm --out v22_ip14pm
python code/tools/eval_v2_geometry.py --diag benchmark/true_geometry/ip14pm.csv --report v22_ip14pm/report_v2.csv
```
Engines (homr, Audiveris, SMT++) are installed separately; see `code/pipeline/HUONG_DAN_PIPELINE.md` and `code/omr_eval/engines.json`.
Some helper documents are in Vietnamese.

## Licences
* Code: MIT (see LICENSE).
* References and prints are derived from KernScores and ASAP encodings (CC BY-NC-SA 4.0) and the music21 corpus; they are distributed
  under CC BY-NC-SA 4.0. The musical works are in the public domain.
* Clef templates in `code/rectify_v2*/clef_tpl_f.npy` are cut from renderings of other public-domain pieces.
