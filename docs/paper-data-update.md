# Manuscript data update — 2026-09-10

Source: `DOR_LIO__ICRA_/root.tex` (explicitly selected by the author).
`data/paper-results.json` records the source SHA-256 and numerical table snapshot.
This is a transcription of manuscript results, not a rerun of the experiments.

Updated website content:

- `tab:ape_comparison`: eight sequences, nine methods, translation APE RMSE in meters; no legacy RMSE/mean pairs.
- `tab:datasets`: sixteen sequence entries, with original sensor labels and missing values preserved.
- `tab:helimos_compare`: four sensors, SA/DA/HA percentages, ground-truth poses. Do not combine these point-wise scores with Gazebo voxel scores.
- `tab:gazebo_comparison`: six methods in each of Slow/Medium/Fast; PR/RR/F1 percentages and CD/map RMSE in meters. Displayed in one grouped table directly below the Gazebo video; all values are unchanged.
- `tab:selfcollected_eval`: six methods, Mall 01/Mall 02/School 01 drift and MME; all School 01 entries remain `--`.
- Runtime: 24.54 ms mean, 16.00–30.80 ms reported range, 2–5 ms DOR/map update. The average-time figure does not establish tail latency or end-to-end throughput.
- Current manuscript figures copied into `images/paper/`: framework, residual examples, map clearing, Gazebo, platforms, mall, and module timings.

Editorial handling:

- Preserve numerical precision, `--`, and `×` from source tables.
- Determine best values numerically, ignoring LaTeX color annotations. In particular, LIMOT is the minimum on P1 and P2 (1.30 and 0.18 m).
- Do not recompute HA from aggregate SA/DA; preserve the manuscript's reported aggregates.
- The initial Aeva DA row had an extra value. The source was corrected during the update, and the final six-method row is imported in full: 79.98, 79.33, 44.56, 64.78, 77.77, 90.49.
- Retain the paper's citation/provenance distinction for reported BTSA baselines. Its HeLiMOS table note does not specify the ERASOR result source; the website notes this rather than assigning provenance.
- The dataset inventory enumerates five self-collected sequences while the prose mentions eight, and the results table also reserves School 01. The website avoids asserting a complete eight-sequence inventory.
- Preserve the four-platform video selector and recorded Gazebo/M3DGR videos. The supplied Gazebo video has no verified speed label, so it is not assigned to Slow/Medium/Fast.

## Synchronized keyframe tour

- Reference interaction: https://wuyi2121.github.io/UrbanAgent/ (key-moment thumbnails that seek the video).
- Local and Camera appear above the larger Global view. All share one clock, timeline, pause/play control, and loop. Muted autoplay starts when the player enters view; offscreen/hidden playback pauses.
- Source videos in `ori_vedio/同一时刻/` are all 77.184 s, 854×480, 30 fps. Web copies in `videos/synchronized/` use stream-copy video with `+faststart` and omit audio; no video re-encoding. Rebuild with `bash tools/prepare_sync_videos.sh`.
- `data/keyframes.json` records ten timestamps and source montage IDs. Timestamps were located by SIFT matching the supplied montage against Camera at 0.25 s intervals, so they are approximate visual matches, not manually supplied timestamps. Cards use actual Camera frames at those timestamps and are displayed chronologically.
- To adjust a keyframe, update its `data-keyframe-time` in `index.html`, its JSON entry, and corresponding thumbnail. One keyframe seeks all three views.
- Local preview now uses `python3 tools/serve.py --port 8899`, providing MP4 `Accept-Ranges`/206 responses. This is required to seek into partially downloaded fast-start videos; Python's default static server did not provide seekable ranges in the browser check.

## Page order (2026-09-11)

Contributions → Inside a Dynamic Scene → Interactive Point Cloud Explorer →
Mall 01 Point Cloud Comparison → Cross-Platform video → public dataset video and
metrics → Gazebo video and one three-speed metric table → self-collected results →
Method Overview → Citation. The dataset inventory follows the public metric tables.

## Replacement views and paired public benchmarks (2026-09-11)

The replacement Local and Camera clips come from `ori_vedio/画图/`, both 640×480
and 77.184 s. Global remains from `ori_vedio/同一时刻/`. Camera keyframe thumbnails
and both posters have been regenerated at the existing timestamps.

The public dataset video is now a paired comparison with Dynamic01 and Dynamic03
tabs. Each tab loads DOR-LIO on the left and FAST-LIO2 on the right. Four source
files map to `videos/benchmarks/{dynamic01,dynamic03}-{ours,fastlio2}.mp4`:
`dynamic01-our1`, `dynamic01-lio2`, `dynamic03-our`, and `dynamic03-fastlio2`.
All source clips are 14.838 s. They use lossless video stream-copy with fast-start
indexing and omit audio. The source videos are retained. A shared control bar
keeps paired playback, seeking, looping and pause synchronized. The old single
M3DGR video is no longer embedded; all quantitative tables are unchanged.

## HeLiMOS qualitative figure (2026-09-11)

Added the user-selected `/home/hyd/Downloads/compare_helimos.png` unchanged as
`images/paper/compare_helimos.png`, immediately before the HeLiMOS table.
It compares Raw Map, BTSA, DUFOMap, ERASOR2, and Ours; no numerical values
or color semantics have been inferred from this figure.
