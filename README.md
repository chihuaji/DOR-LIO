# DOR-LIO Project Page

Source for the DOR-LIO website (`index.html` + assets), in the style of
[SE(2)-NavMesh](https://se2-navmesh.github.io/) / [Drive with Signs](https://drive-with-signs.netlify.app/).

Interactive components:

1. **Interactive Point Cloud Explorer** — drag to orbit, scroll/pinch to zoom,
   right-drag to pan, point-size slider, auto-spin.
2. **Paginated map comparison** — DOR-LIO vs FAST-LIO2, BTSA, and
   FAST-LIO2 + DUFOMap on Mall 01, using aligned display exports and shared
   height colors. Drag the wipe divider, orbit/zoom, and change pages with
   Previous/Next while retaining the viewpoint.
3. **Recorded Video Comparisons** — switch between four cross-platform videos,
   watch the M3DGR benchmark, and view recorded Gazebo results. The former
   Live Simulation Lab is disabled on the page; its backend sources are retained.

## Recorded comparison videos

The page now features Key Contributions, a four-button Cross-Platform Comparison
(single player), a recorded Gazebo comparison, and an M3DGR benchmark video.
Original MP4 files are served from `ori_vedio/`; posters live in `images/video-*.jpg`.
The selectors are defined in `index.html` and handled by `js/video-gallery.js`.
Videos load on demand and switching scenes pauses and resets the player.

The Live Simulation Lab is disabled on the public page: neither its controls nor
`js/simlab.js` are loaded. Backend sources remain available for later use.
No simulation jobs are launched by these video sections.

For the two future speed videos, add MP4s and posters, then reuse the
`data-video-gallery` / `data-src` button structure in the simulation section.
Label each speed only when its experimental setting is confirmed.

## Live Simulation Lab (archived; not enabled on the page)

### 快速开始

```bash
cd dor-web/simlab
python3 server.py --port 8900 --host 127.0.0.1
# 打开 http://127.0.0.1:8900/#simlab
```

后端同时提供网站静态文件与 REST API（`/api/health`、`/api/status`、
`POST /api/run`、`/api/runs`、`/runs/<id>/...`）。同一时刻只跑一个仿真任务。

### 一次实验做什么（全部后台无头，无 GUI）

`simlab/run_pipeline.py --room 12 --boxes 8 --people 10 --seed 42 --duration 60`：

1. **gen_world** — 生成动态/静态世界对（同种子 → 方块布局与行人路线一致）。
   行人是带贴图的 Gazebo actor（walk.dae 皮肤动画 + 幽灵碰撞体保证雷达可见 +
   随机 waypoint 轨迹，录制期间不循环）；机器人以 SDF 直接嵌入 world
   （避开 spawn 服务与 actor 的竞态崩溃）。
2. **record** — 无头 Gazebo + 随机巡游驾驶员（`random_driver.py`，
   随机 waypoints + 卡死倒车脱困）+ 动态标注器（PointCloud→PointCloud2），
   `rosbag record` 录 `/scan /scan_labeled_pc2 /imu/data /ground_truth/state`。
3. **replay_dorlio** — 同一 bag 回放进 DOR-LIO（`yifanLIO`，mid360_gazebo 配置），
   播完发 `/save_map` 话题触发 `static_map_point.pcd` 落盘。
4. **replay_raw** — 同一 bag 用真值位姿累积（`gt_accumulator.py`）→
   无滤除原始地图（行人鬼影完整保留）。
5. **convert** — `tools/pcd_to_ply.py`：clean 按高度染色；raw 以 clean 为参考
   diff 染色（离 clean 图 >0.25 m 的点标红 = 被 DOR-LIO 移除的动态点）。

产物在 `runs/<id>/`：`web/{raw,clean}.ply`（网页用）、`dorlio_out/static_map_point.pcd`、
`raw_map.pcd`、`gazebo.bag`、`log/`、`status.json`、`result.json`。

### 关键工程点（排障记录）

- 使用 `/home/hyd/icra-dor-ws/gazebo_sim/livox_sim_ws`（不是 dynamic_ws 那份）：
  其 URDF 带 `always_on` 传感器修复（否则无 GUI 时 /scan 静默无输出）、
  `gravity=false` IMU 修复和标定噪声模型。
- 环境链每一环都可能踩坑：`final_ws/devel` 会**重置** `ROS_PACKAGE_PATH` 和
  `GAZEBO_PLUGIN_PATH`（需显式补回，否则雷达插件加载失败）；
  world 内所有 `model://`、`package://` 一律写成绝对路径
  （否则 gazebo 联网查模型库会挂起、雷达 csv 读不到）。
- 每次运行使用随机 ROS master 端口（11330-11399），并全程持有
  `rosmaster -p <port>`（注意 rosmaster 不读 ROS_MASTER_URI 环境变量），
  与用户自己正在跑的仿真会话完全隔离。
- 地图保存是**话题触发**（`rostopic pub -1 /save_map std_msgs/Empty`），
  不是关停时保存。
- 已知问题：当前 `final_ws` 版本 LIO 在 gazebo 数据上有明显轨迹漂移
  （他们的旧 bag 用该版本回放同样漂移）。流程本身已验证正确
  （录制/回放/保存/转换全链路 + 真值累积正常），等算法侧修复后新任务即产出正常地图。

### 安全提示

`--host 0.0.0.0` 会把“在服务器上跑仿真”的能力开放给所有能访问该端口的人。
公网部署请放反代后并加鉴权（API 目前无鉴权、无速率限制，单任务排队）。

## Directory layout

```
dor-web/
├── index.html          # the page (all sections)
├── css/style.css       # design system
├── js/
│   ├── vendor/three.min.js   # three.js r128 (vendored, works offline)
│   ├── ply-loader.js         # binary PLY (xyz + rgb) parser
│   ├── orbit-controls.js     # custom z-up orbit/pan/zoom controls
│   ├── cloud-viewer.js       # Point Cloud Explorer component
│   ├── compare-viewer.js     # before/after wipe component
│   ├── simlab.js             # Live Simulation Lab frontend
│   ├── scenes.js             # <-- register your scenes here
│   └── main.js               # page bootstrap
├── data/               # point cloud PLYs served to the browser
├── images/             # paper figures (extracted from the PDF)
├── simlab/             # backend: server.py + pipeline scripts (see above)
├── runs/               # simulation results (served via /runs/)
└── tools/              # python helpers (see below)
```

## Local preview

```bash
cd dor-web
python3 tools/serve.py --port 8899
# open http://127.0.0.1:8899
```

(Opening `index.html` via `file://` also works in most browsers, but a local
server avoids any fetch/CORS quirks.)

## Deploying

- **GitHub Pages** — push this folder to the `DOR-LIO` repo (e.g. as `main`
  root or `/docs`), then Settings → Pages → enable. Rename to taste.
- **Netlify** (like drive-with-signs) — drag & drop the folder into a new
  site. No build step.

## Legacy demo point clouds and conversion examples

The archived campus demo uses a **real** DOR-LIO static map from
`final_ws/src/yifanLIO/PCD/static_map_point.pcd` (campus sequence). The
"raw" side of the wipe is that same map with **synthesized walking
pedestrians** (red) standing in for a raw FAST-LIO2 export — it is a
placeholder, labeled as such on the page.

To use a real pair (recommended once you export raw maps from a baseline):

```bash
# 1) clean map (height-colored), e.g. from your DOR-LIO static output
python3 tools/pcd_to_ply.py \
    -i /path/to/static_map_point.pcd \
    -o data/campus_clean.ply \
    --mode height --voxel 0.08 --max-points 700000

# 2) raw map (same scene, exported from FAST-LIO2 WITHOUT removal);
#    points farther than 0.3 m from the clean map are painted red
python3 tools/pcd_to_ply.py \
    -i /path/to/raw_map.pcd \
    -o data/campus_raw.ply \
    --mode diff --ref /path/to/static_map_point.pcd --diff-thresh 0.3

# 3) re-synthesize the demo raw map instead (placeholder workflow)
python3 tools/inject_pedestrians.py \
    --base data/campus_clean.ply --out data/campus_raw_demo.ply
```

`pcd_to_ply.py` reads ASCII and binary PCD with any field layout (needs
`x y z`; `intensity` is used when present), voxel-downsamples for web
payloads, and writes binary PLY with RGB.

Then register the files in `js/scenes.js`:

```js
explorer: [ { id: 'campus', title: 'Campus (handheld)', file: 'data/campus_clean.ply', badges: [...] } ],
compare:  [ { id: 'campus', title: 'Campus', raw: 'data/campus_raw.ply', clean: 'data/campus_clean.ply', ... } ],
```

Adding more sequences (Mall, Humanoid, Quadruped, Gazebo …) is just more
entries — the tabs are generated automatically.

## Other page content to fill in later

- Authors / affiliations (`index.html`, hero section)
- Paper PDF link, arXiv link
- Two additional simulation speed videos and their confirmed speed labels
- BibTeX block in the citation section

## Tools

| script | purpose |
| --- | --- |
| `tools/pcd_to_ply.py` | PCD → web PLY (downsample + height/diff coloring) |
| `tools/inject_pedestrians.py` | synthesize red pedestrian ghosts on a clean map (demo) |
| `tools/inspect_pcd.py` | header/bbox overview for PCD files |
| `tools/preview_pcd.py` | quick matplotlib previews |

Requires `numpy` (+`scipy` for diff mode).

## Manuscript results

Current result tables follow `DOR_LIO__ICRA_/root.tex`. The source hash and
numerical snapshot are in `data/paper-results.json`; transcription decisions
and source caveats are recorded in `docs/paper-data-update.md`.
Paper figures used on the page are copied to `images/paper/`.

## Synchronized keyframe tour

`#highlights` presents Local + Camera above a large Global view, with ten clickable
keyframes. `js/sync-player.js` controls muted autoplay in view, shared seeking,
play/pause, and independent looping. Clips are manually aligned; there is no
runtime clock correction or pause-all-on-buffering behavior. Keyframe IDs and approximate visual
match timestamps are recorded in `data/keyframes.json`.

Original videos stay in `ori_vedio/同一时刻/`; stream-copy web versions are in
`videos/synchronized/`. Run `bash tools/prepare_sync_videos.sh` to regenerate
fast-start web copies without re-encoding the video.

The preview server supports HTTP Range requests for MP4 seeking. Use it instead
of `python3 -m http.server` when checking keyframe jumps.

## Mall 01 point-cloud comparisons

The Before / After section now uses real Mall 01 maps with bottom pagination:
DOR-LIO vs FAST-LIO2, BTSA, and FAST-LIO2 + DUFOMap. Exported PLYs are in
`data/mall01/`; source identities, sampling, and display-only rigid alignment
are documented in `docs/mall01-point-cloud-comparison.md`.
The camera stays fixed when changing comparison pages.

## Paired public-dataset videos

`#public-datasets` now uses Dynamic01 / Dynamic03 buttons to switch two manually aligned
views: DOR-LIO on the left and FAST-LIO2 on the right. The four source clips in
`ori_vedio/画图/` are prepared by `bash tools/prepare_benchmark_videos.sh`.
`js/benchmark-player.js` provides muted autoplay in view, shared play/pause,
seeking, and looping. Numerical tables immediately follow the paired videos.

The synchronized Local and Camera views also use the new 4:3 clips from
`ori_vedio/画图/`; Global retains its previous source. Their existing keyframe
jump times are retained, with refreshed Camera thumbnails. Source/output video
stream fingerprints are recorded in `data/replacement-videos.json`.

## Autoplay and web playback optimization

All video sections autoplay muted when visible, loop independently, and pause
when offscreen or the browser tab is hidden. Explicit user pauses are retained.
Switching a scene starts the selected clips automatically. Shared buttons and
keyframes remain available; playback never seeks to correct inter-video drift.

The page uses `videos/optimized/` generated by
`python3 tools/optimize_web_videos.py`. These are lossy H.264 display copies
(CRF 23, maximum width 1280, faststart, no audio) retaining source frame count
and cadence. The 12 clips total 87.6 MB instead of 191.5 MB (54% smaller).
Original uploads and earlier stream-copy versions remain untouched.
`data/web-video-optimization.json` records each source, output, and size.

Point-cloud rendering pauses offscreen and is capped at 30 fps when visible;
the explorer initializes only when approached, reducing startup CPU/GPU work.
