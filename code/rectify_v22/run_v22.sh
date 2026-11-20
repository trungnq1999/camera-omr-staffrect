#!/bin/bash
# Chạy v2.2 trên cả hai máy: nắn + đo hình học/khung cắt + 3 engine.
set -x
cd /mnt/g/doan/minh
export TMPDIR=/mnt/g/tmp HF_HOME=/mnt/g/tmp/hf XDG_CONFIG_HOME=/mnt/g/tmp/config XDG_DATA_HOME=/mnt/g/tmp/data XDG_CACHE_HOME=/mnt/g/tmp/cache
PY=.venv/bin/python
P=pp_study/pipeline/run_pipeline.py
sha256sum -c frozen/FROZEN.sha256 frozen/FROZEN_V22.sha256 || exit 1
for M in x12sp:real_photos3:results_x12sp_v1 ip14pm:real_photos2:results_real; do
  code=${M%%:*}; rest=${M#*:}; photos=${rest%%:*}; diag=${rest#*:}/diag.csv
  $PY pp_study/rectify_v22/rectify_v2.py --photos $photos --out v22_$code
  $PY pp_study/tools/eval_v2_geometry.py --diag $diag --report v22_$code/report_v2.csv --out v22_$code/geometry.csv
  $PY pp_study/rectify_v22/crop_eval.py $diag v22_$code/report_v2.csv v22_$code v22_$code/crop_eval.csv
  $PY $P --photos v22_$code/raw  --out results_${code}_v22_raw  --variants raw --smt-variants raw
  $PY $P --photos v22_$code/norm --out results_${code}_v22_norm --variants raw --smt-variants raw
  $PY $P --photos v22_$code/bin  --out results_${code}_v22_bin  --variants raw --engines audiveris
done
echo "XONG TẤT CẢ"
