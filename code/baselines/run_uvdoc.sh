#!/bin/bash
# Đường cơ sở UVDoc trên cả hai máy.
#  A. UVDoc trên ảnh như chụp (so sánh trực tiếp với v1, v2.1, v2.2): đủ 3 engine
#  B. UVDoc trên ảnh đã xoay đúng hướng bằng góc chuẩn (oracle_rot): tách riêng chất lượng nắn của UVDoc
set -x
cd /mnt/g/doan/minh
export TMPDIR=/mnt/g/tmp HF_HOME=/mnt/g/tmp/hf XDG_CONFIG_HOME=/mnt/g/tmp/config XDG_DATA_HOME=/mnt/g/tmp/data XDG_CACHE_HOME=/mnt/g/tmp/cache
PY=.venv/bin/python
P=pp_study/pipeline/run_pipeline.py
UV=/mnt/g/tools/UVDoc
sha256sum -c frozen/FROZEN.sha256 || exit 1
[ -d $UV ] || git clone --depth 1 https://github.com/tanguymagne/UVDoc.git $UV
for M in x12sp:real_photos3 ip14pm:real_photos2; do
  code=${M%%:*}; photos=${M#*:}
  .venv-smt/bin/python pp_study/baselines/uvdoc_batch.py --uvdoc $UV --photos $photos --out uvdoc_$code
  $PY $P --photos uvdoc_$code/raw  --out results_${code}_uvdoc_raw  --variants raw --smt-variants raw
  $PY $P --photos uvdoc_$code/norm --out results_${code}_uvdoc_norm --variants raw --smt-variants raw
  $PY $P --photos uvdoc_$code/bin  --out results_${code}_uvdoc_bin  --variants raw --engines audiveris
done
for M in x12sp:oracle_x12sp_rot ip14pm:oracle_rot; do
  code=${M%%:*}; photos=${M#*:}
  .venv-smt/bin/python pp_study/baselines/uvdoc_batch.py --uvdoc $UV --photos $photos --out uvdocrot_$code
  $PY $P --photos uvdocrot_$code/raw --out results_${code}_uvdocrot_raw --variants raw --engines homr,audiveris
  $PY $P --photos uvdocrot_$code/bin --out results_${code}_uvdocrot_bin --variants raw --engines audiveris
done
echo "XONG TẤT CẢ"
