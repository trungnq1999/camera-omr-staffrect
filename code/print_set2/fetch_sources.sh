#!/usr/bin/env bash
# fetch_sources.sh - Tải mã hoá các bản nhạc nguồn cho tập test mới (chỉ cần chạy một lần).
# Dùng:  bash fetch_sources.sh /mnt/g/doan/minh/src_scores
set -e
SRC="${1:-/mnt/g/doan/minh/src_scores}"
mkdir -p "$SRC" && cd "$SRC"
[ -d inventions ] || git clone --depth 1 https://github.com/humdrum-tools/inventions
[ -d haydn-piano-sonatas ] || git clone --depth 1 https://github.com/craigsapp/haydn-piano-sonatas
if [ ! -d asap-dataset ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/fosfrancesco/asap-dataset
  (cd asap-dataset && git sparse-checkout set Brahms/Six_Pieces_op_118/2 Schumann/Arabeske)
fi
echo "Đã có nguồn trong $SRC"
