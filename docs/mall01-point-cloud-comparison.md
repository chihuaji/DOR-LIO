# Mall 01 point-cloud comparison

The comparison viewer now has three pages, with DOR-LIO on the left:

1. DOR-LIO vs FAST-LIO2
2. DOR-LIO vs BTSA
3. DOR-LIO vs FAST-LIO2 + DUFOMap

The same camera and height colors are retained across pages. Previous/Next stop at
the first/last page. Changing pages cancels in-flight downloads and late results
cannot replace the selected pair. Only one pair of GPU geometries is retained.

## Source selection

All maps correspond to `floor1.bag` / Mall 01.

- DOR-LIO: `/home/hyd/dynamic_ws/yflio_dynamic_ws/pcd/my/longhufloor1.pcd`.
  Archived map, 1,215,326 points. Its sibling `MME.py` explicitly reads this file.
  This is not claimed to be a new final_ws rerun or the currently running map.
- FAST-LIO2: `baseline_icra/selfcollected_runs/results/fastlio2/offline_20260911_floor1/full_map.pcd`.
  Dense world-coordinate accumulation from the frontend used by DUFOMap.
- BTSA: `baseline_icra/selfcollected_runs/results/btsa/run_20260910T100519/btsa_floor1_static_map.pcd`.
  Static output from registered clouds minus detected dynamic points. This is the
  static-map rerun, not the earlier full-cloud archive used for the first drift table.
- DUFOMap: `baseline_icra/selfcollected_runs/results/dufomap/offline_20260911_floor1/static_map.pcd`.
  Point-level static output, with the same FAST-LIO2 poses as page 1.

Absolute source paths, point counts, source SHA-256, and output SHA-256 are in
`data/mall01/provenance.json`. Source files are read-only and no experiments were rerun.

## Display transformations and sampling

The baseline maps initially have a roughly 23-degree tilt relative to the archived
DOR-LIO map. A single rigid transform is estimated for FAST-LIO2, and **the exact
same transform** is used for DUFOMap. BTSA has a separately estimated rigid transform.
Transforms are stored in `data/mall01/display-transforms.json`. No scale, nonrigid
warping, ICP-based metric correction, or pose optimization is applied to the originals.

Registration uses deterministic 200,000-point source samples, 0.35 m voxel selection,
PCA orientation candidates, then trimmed point-to-point ICP with 3/1.5/0.7/0.35 m
thresholds (20 iterations each). Nearest-neighbor diagnostics in the transform JSON
are sample/display checks, **not** CD, map RMSE, DOR metrics, or registration guarantees.
Independent trajectories, incomplete coverage, moving returns, and local errors remain.

Web exports use at most two million evenly spaced source samples, shared 0.1 m
voxel selection, and a deterministic cap of 650,000 points per map. Each binary
PLY is about 9.75 MB. The same origin and DOR-LIO-derived 2nd–98th percentile
height color range are applied to all four exports. No geometry is selectively
marked as dynamic from map differences. Height-color saturation does not clip points.

These are **qualitative, downsampled, display-aligned maps from separate runs**;
their densities and settings differ. The previous synthetic pedestrian demo is no
longer used in this comparison section. No paper numbers or MME results were changed.

## Regeneration and validation

```bash
# Optional: recompute the display transforms from source maps.
OPENBLAS_NUM_THREADS=1 python3 tools/align_mall01_maps.py
# Export maps serially with bounded in-memory samples.
OPENBLAS_NUM_THREADS=1 python3 tools/prepare_mall01_maps.py
node tests/compare-loading.test.cjs
python3 tools/serve.py --port 8899
# http://127.0.0.1:8899/#compare
```
