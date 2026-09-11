#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p videos/benchmarks images/benchmarks
for pair in 'dynamic01-our1 dynamic01-ours' 'dynamic01-lio2 dynamic01-fastlio2' 'dynamic03-our dynamic03-ours' 'dynamic03-fastlio2 dynamic03-fastlio2'; do
  read -r source_name target_name <<< "$pair"
  ffmpeg -hide_banner -loglevel error -i "ori_vedio/画图/$source_name.mp4" \
    -map 0:v:0 -c:v copy -an -movflags +faststart -y "videos/benchmarks/$target_name.mp4"
  ffmpeg -hide_banner -loglevel error -ss 2 -i "ori_vedio/画图/$source_name.mp4" \
    -frames:v 1 -q:v 3 -y "images/benchmarks/$target_name.jpg"
done
