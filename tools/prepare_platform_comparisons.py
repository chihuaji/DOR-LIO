"""Build labeled browser videos from the reviewed 2026-09-21 source selection."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('human', ROOT / 'videos/human/dorlio_reference_topdown_axes_stride10.mp4', Path('/home/hyd/dynamic_ws/a2_dor_yflio_work/methods/fastlio2_requested_20260921/videos/fastlio2_dynamic_red.mp4'), False),
    ('stairs', Path('/home/hyd/dynamic_ws/stairs_compare_work/previews/user_side_v1/videos/seq01_3to2/dor_height.mp4'), Path('/home/hyd/dynamic_ws/stairs_compare_work/previews/requested_fastlio2_ws/videos/seq01_3to2/fast_dor_dynamic_red.mp4'), True),
    ('omni', Path('/home/hyd/dynamic_ws/omni_compare_work/videos/test2/dor_height.mp4'), Path('/home/hyd/dynamic_ws/omni_compare_work/videos/test2_requested_red/fast_dor_dynamic_red.mp4'), True),
]
OUT = ROOT / 'videos/comparisons'
OUT.mkdir(exist_ok=True)
manifest = []
for name, dor, fast, synchronized in SOURCES:
    records = []
    for source in (dor, fast):
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(source)]))
        records.append({'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'duration': float(probe['format']['duration'])})
    duration = max(r['duration'] for r in records)
    # Keep native recording speed; hold the shorter recording's last frame.
    filters = []
    for i, label in enumerate(('DOR-LIO (Ours)', 'FAST-LIO2')):
        filters.append(f"[{i}:v]setpts=PTS-STARTPTS,scale=800:530,setsar=1,tpad=stop_mode=clone:stop_duration=5,pad=800:900:0:190:black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{label}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=132[v{i}]")
    filters.append('[v0][v1]hstack=inputs=2[out]')
    dest = OUT / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2', '-i', str(dor), '-threads', '2', '-i', str(fast), '-filter_complex_threads', '1', '-filter_complex', ';'.join(filters), '-map', '[out]', '-t', str(duration), '-r', '30', '-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dest)], check=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(duration * .7), '-i', str(dest), '-frames:v', '1', '-q:v', '2', str(OUT / f'{name}.jpg')], check=True)
    manifest.append({'scene': name, 'inputs': records, 'red_points': 'DOR posterior DYNAMIC=2 labels on FAST-LIO2 output; not FAST-LIO2 detection or ground truth.', 'common_sensor_interval': synchronized, 'timing': 'Original playback speed preserved. Shorter recording holds its final frame; Human screen recordings are not sensor-synchronized.' if not synchronized else 'Common sensor interval, 2x playback.', 'output': dest.name, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
    print(name, dest.stat().st_size, flush=True)
(OUT / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')
