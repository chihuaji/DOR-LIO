#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p videos/synchronized
for view in local camera global; do
  ffmpeg -hide_banner -loglevel error -i "ori_vedio/同一时刻/$view.mp4" \
    -map 0:v:0 -c:v copy -an -movflags +faststart -y "videos/synchronized/$view.mp4"
done
