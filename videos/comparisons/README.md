# DOR-LIO / FAST-LIO2 platform videos

Published 2026-09-21. Left: DOR-LIO; right: FAST-LIO2. Height-colored maps, original fixed views and recording speeds retained. These are qualitative comparisons, not ground-truth localization measurements.

- **Human:** original DOR-LIO and FAST-LIO2 stride-10 screen recordings (44.0 / 47.8 seconds). The recordings are not sensor-synchronized. The final DOR frame is held while FAST-LIO2 finishes; no time stretching or trajectory correction is applied during composition. Uses the original FAST-LIO2 recording, not yflio or the later 1 cm / 5 cm variants.
- **Stairs:** seq01_3to2, approved `user_side_v1` DOR view and `requested_fastlio2_ws` FAST-LIO2 height rendering. Same view and common sensor interval, 2x playback, 61.767 seconds. FAST-LIO2 uses the requested workspace's stairs configuration (0.5 m surface/map filters, point_filter_num=3).
- **Omni:** test2 DOR and `test2_requested` FAST-LIO2 height rendering. Same view and common sensor interval, 2x playback, 54.7 seconds. FAST-LIO2 uses the requested workspace's Danshui configuration (0.5 m surface/map filters, point_filter_num=3).

All website assets are regular files, independent of source symlinks and removable drives. `sources.json` records exact input paths and SHA256 hashes. `../../tools/prepare_platform_comparisons.py` reproduces the composition when source recordings are available. Output: H.264, yuv420p, 30 fps, fast-start MP4, 1600x900, no audio; posters sampled at 70% of each video.
