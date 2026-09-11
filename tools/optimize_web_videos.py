#!/usr/bin/env python3
"""Build smaller 30 fps H.264 web copies; leave all source videos unchanged."""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'camera':'ori_vedio/画图/camera.mp4','local':'ori_vedio/画图/local.mp4','global':'ori_vedio/同一时刻/global.mp4',
 'dynamic01-ours':'ori_vedio/画图/dynamic01-our1.mp4','dynamic01-fastlio2':'ori_vedio/画图/dynamic01-lio2.mp4',
 'dynamic03-ours':'ori_vedio/画图/dynamic03-our.mp4','dynamic03-fastlio2':'ori_vedio/画图/dynamic03-fastlio2.mp4',
 **{x:f'ori_vedio/{x}.mp4' for x in ['a2','dog','omnicar','longhu','gazebo']}}

def main():
 out=ROOT/'videos/optimized';out.mkdir(exist_ok=True)
 rows=[]
 for name,rel in SOURCES.items():
  src=ROOT/rel;dst=out/(name+'.mp4')
  # Keep original frame cadence/timestamps; CRF encoding is lossy and display-only.
  cmd=['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-i',str(src),'-map','0:v:0','-vf',"scale=w='min(1280,iw)':h=-2",'-filter_threads','1','-c:v','libx264','-threads','2','-preset','fast','-crf','23','-maxrate','2500k','-bufsize','5000k','-pix_fmt','yuv420p','-g','30','-keyint_min','30','-sc_threshold','0','-an','-movflags','+faststart','-y',str(dst)]
  subprocess.run(cmd,check=True)
  row={'source':rel,'output':str(dst.relative_to(ROOT)),'source_bytes':src.stat().st_size,'web_bytes':dst.stat().st_size};rows.append(row)
  print(name,round(row['source_bytes']/1e6,2),'->',round(row['web_bytes']/1e6,2),'MB',flush=True)
 (ROOT/'data/web-video-optimization.json').write_text(json.dumps({'encoding':'H.264 CRF 23, max 1280 px width, max 2.5 Mbit/s, 1-second keyframes, original frame cadence, no audio, faststart. Lossy display copies; originals retained.','videos':rows},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
