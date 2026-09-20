# DOR-LIO / FAST-LIO2 platform videos

Published 2026-09-21. Left: DOR-LIO; right: FAST-LIO2. Height-colored maps, original fixed views and recording speeds retained. Red marks only DOR posterior DYNAMIC=2 labels mapped onto retained FAST-LIO2 points by verified raw point IDs. Labels do not enter FAST-LIO2 estimation and are not FAST-LIO2 detections or ground truth. These are qualitative comparisons, not ground-truth localization measurements.

- **Human:** DOR-LIO stride-10 screen recording (44.0 seconds) and the requested `fastlio2_ws` A2 dynamic-red recording (42.9 seconds). Independent recordings are not sensor-synchronized; FAST-LIO2 holds its final frame. The FAST-LIO2 run uses its native A2 decoder, 0.5 m matching/map filters and point_filter_num=1. It replaces the earlier `btsa_test/rebuild_ws` baseline.
- **Stairs:** seq01_3to2, approved `user_side_v1` DOR view and `requested_fastlio2_ws` FAST-LIO2 dynamic-red rendering. Same view and common sensor interval, 2x playback, 61.767 seconds. FAST-LIO2 uses the requested workspace's stairs configuration (0.5 m surface/map filters, point_filter_num=3).
- **Omni:** test2 DOR and `test2_requested_red` FAST-LIO2 dynamic-red rendering. Same view and common sensor interval, 2x playback, 54.7 seconds. FAST-LIO2 uses the requested workspace's Danshui configuration (0.5 m surface/map filters, point_filter_num=3).

All website assets are regular files, independent of source symlinks and removable drives. `sources.json` records exact input paths and SHA256 hashes. `../../tools/prepare_platform_comparisons.py` reproduces the composition when source recordings are available. Output: H.264, yuv420p, 30 fps, fast-start MP4, 1600x900, no audio; posters sampled at 70% of each video.
