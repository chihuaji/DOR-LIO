#!/usr/bin/env python3
"""
pcd_to_ply.py — Convert PCD maps (DOR-LIO / FAST-LIO2 / LIO-SAM outputs) into
web-ready binary PLY files for the DOR-LIO project page.

Features
  * reads ASCII and binary PCD with arbitrary field layouts (needs x, y, z;
    intensity is used when present)
  * voxel-grid downsampling to keep web payloads small
  * colorization:
      - mode height : turbo colormap over z (default)
      - mode diff   : points far from a reference (clean) map are painted red
                      (dynamic artifacts removed by DOR-LIO), the rest use the
                      same height colormap as the reference so the before/after
                      wipe looks seamless
  * writes binary_little_endian PLY with float xyz + uchar rgb

Examples
  # clean map, height colored, ~700k points
  python3 pcd_to_ply.py -i static_map_point.pcd -o campus_clean.ply \
      --max-points 700000 --mode height

  # raw map, dynamic artifacts highlighted in red against the clean reference
  python3 pcd_to_ply.py -i scans.pcd -o campus_raw.ply \
      --ref static_map_point.pcd --mode diff --diff-thresh 0.3
"""
import argparse
import sys
import numpy as np

try:
    from scipy.spatial import cKDTree
except ImportError:
    cKDTree = None


# --------------------------------------------------------------------------- #
# PCD reading
# --------------------------------------------------------------------------- #
def read_pcd(path):
    with open(path, 'rb') as f:
        fields, sizes, types, counts = [], [], [], []
        n_points, data_kind = None, None
        while True:
            line = f.readline()
            if not line:
                raise ValueError('premature end of PCD header')
            text = line.decode('ascii', 'ignore').strip()
            if text.startswith('FIELDS'):
                fields = text.split()[1:]
            elif text.startswith('SIZE'):
                sizes = [int(v) for v in text.split()[1:]]
            elif text.startswith('TYPE'):
                types = text.split()[1:]
            elif text.startswith('COUNT'):
                counts = [int(v) for v in text.split()[1:]]
            elif text.startswith('POINTS'):
                n_points = int(text.split()[1])
            elif text.startswith('DATA'):
                data_kind = text.split()[1]
                break
        if any(c != 1 for c in counts):
            raise ValueError('multi-count PCD fields are not supported')
        type_map = {'F': {4: 'f4', 8: 'f8'}, 'U': {1: 'u1', 2: 'u2', 4: 'u4'},
                    'I': {1: 'i1', 2: 'i2', 4: 'i4'}}
        dtype = np.dtype([(fn, type_map[t][s]) for fn, t, s in zip(fields, types, sizes)])
        if data_kind == 'ascii':
            plain = np.loadtxt(f, dtype=np.float64, max_rows=n_points)
            data = plain
            names = fields
            if plain.ndim == 2 and plain.shape[1] == len(fields):
                def col(fname):
                    return plain[:, fields.index(fname)]
                xyz = np.column_stack([col('x'), col('y'), col('z')]).astype(np.float64)
                intensity = (col('intensity').astype(np.float64)
                             if 'intensity' in fields else None)
                return xyz, intensity
        else:
            raw = np.frombuffer(f.read(dtype.itemsize * n_points), dtype=dtype)
            data, names = raw, fields
    xyz = np.column_stack([np.asarray(data['x'], np.float64),
                           np.asarray(data['y'], np.float64),
                           np.asarray(data['z'], np.float64)])
    intensity = np.asarray(data['intensity'], np.float64) if 'intensity' in names else None
    return xyz, intensity


# --------------------------------------------------------------------------- #
# Voxel downsampling
# --------------------------------------------------------------------------- #
def voxel_downsample(points, intensity, voxel):
    """Keep one representative point per voxel cell (first hit)."""
    keys = np.floor(points / voxel).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    idx.sort()
    pts = points[idx]
    inten = intensity[idx] if intensity is not None else None
    return pts, inten


def limit_points(points, intensity, max_points, seed=0):
    if len(points) <= max_points:
        return points, intensity
    rng = np.random.default_rng(seed)
    keep = rng.choice(len(points), size=max_points, replace=False)
    keep.sort()
    return points[keep], (intensity[keep] if intensity is not None else None)


# --------------------------------------------------------------------------- #
# Colorization
# --------------------------------------------------------------------------- #
def turbo(t):
    """Vectorized turbo colormap approximation, t in [0,1] -> uint8 RGB."""
    t = np.clip(t, 0.0, 1.0)[..., None]
    # polynomial fit coefficients (google turbo polynomial approximation)
    r = 0.13572138 + t * (4.61539260 + t * (-42.66032258 + t * (132.13108234 +
        t * (-152.94239396 + t * 59.28637943))))
    g = 0.09140261 + t * (2.19418839 + t * (4.84296658 + t * (-14.18503333 +
        t * (4.27729857 + t * 2.82956604))))
    b = 0.10667330 + t * (12.64187808 + t * (-60.58204836 + t * (110.36276771 +
        t * (-89.90310912 + t * 27.34824973))))
    rgb = np.concatenate([r, g, b], axis=-1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def height_colors(points, zmin=None, zmax=None, percentiles=(2, 98)):
    z = points[:, 2]
    if zmin is None or zmax is None:
        zmin, zmax = np.percentile(z, percentiles)
    t = (z - zmin) / max(zmax - zmin, 1e-6)
    return turbo(t), zmin, zmax


# --------------------------------------------------------------------------- #
# PLY writing
# --------------------------------------------------------------------------- #
def write_ply(path, points, rgb):
    n = len(points)
    header = (
        'ply\n'
        'format binary_little_endian 1.0\n'
        'comment generated by pcd_to_ply.py (DOR-LIO project page)\n'
        f'element vertex {n}\n'
        'property float x\n'
        'property float y\n'
        'property float z\n'
        'property uchar red\n'
        'property uchar green\n'
        'property uchar blue\n'
        'end_header\n'
    ).encode('ascii')
    vertices = np.empty(n, dtype=[('xyz', '<f4', 3), ('rgb', 'u1', 3)])
    vertices['xyz'] = points.astype(np.float32)
    vertices['rgb'] = rgb
    with open(path, 'wb') as f:
        f.write(header)
        f.write(vertices.tobytes())
    print(f'[write] {path}: {n} points, '
          f'{(len(header) + n * vertices.itemsize) / 1e6:.1f} MB')


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-i', '--input', required=True, help='input PCD file')
    ap.add_argument('-o', '--output', required=True, help='output PLY file')
    ap.add_argument('--mode', choices=['height', 'diff'], default='height',
                    help='height: turbo colormap by altitude | diff: highlight '
                         'points missing from the reference map in red')
    ap.add_argument('--ref', help='reference (clean) map PCD for diff mode')
    ap.add_argument('--diff-thresh', type=float, default=0.3,
                    help='NN distance (m) beyond which a point is "dynamic"')
    ap.add_argument('--voxel', type=float, default=0.05,
                    help='voxel size (m) for downsampling')
    ap.add_argument('--max-points', type=int, default=800000,
                    help='hard cap on output point count')
    ap.add_argument('--zmin', type=float, help='override height color range')
    ap.add_argument('--zmax', type=float)
    args = ap.parse_args()

    print(f'[read] {args.input}')
    points, intensity = read_pcd(args.input)
    print(f'  {len(points)} points, '
          f'x[{points[:,0].min():.1f},{points[:,0].max():.1f}] '
          f'y[{points[:,1].min():.1f},{points[:,1].max():.1f}] '
          f'z[{points[:,2].min():.1f},{points[:,2].max():.1f}]')

    if args.voxel > 0:
        points, intensity = voxel_downsample(points, intensity, args.voxel)
        print(f'  voxel {args.voxel} m -> {len(points)} points')
    points, intensity = limit_points(points, intensity, args.max_points)
    print(f'  capped -> {len(points)} points')

    if args.mode == 'diff':
        if not args.ref:
            ap.error('diff mode requires --ref')
        if cKDTree is None:
            ap.error('diff mode requires scipy')
        print(f'[read] reference {args.ref}')
        ref, _ = read_pcd(args.ref)
        ref, _ = voxel_downsample(ref, None, max(args.voxel, 0.05))
        print(f'  reference has {len(ref)} points (voxelized)')
        tree = cKDTree(ref)
        dist, _ = tree.query(points, k=1, distance_upper_bound=np.inf)
        dynamic = dist > args.diff_thresh
        frac = dynamic.mean() * 100
        print(f'  {dynamic.sum()} points ({frac:.1f}%) farther than '
              f'{args.diff_thresh} m from reference -> painted red')

        # Use the SAME height ramp as the reference would have, computed on the
        # static part of this cloud so both sides of the wipe match visually.
        zmin = args.zmin if args.zmin is not None else np.percentile(points[~dynamic, 2], 2) if (~dynamic).any() else points[:,2].min()
        zmax = args.zmax if args.zmax is not None else np.percentile(points[~dynamic, 2], 98) if (~dynamic).any() else points[:,2].max()
        rgb, _, _ = height_colors(points, zmin, zmax)
        red = np.zeros_like(rgb)
        red[:, 0] = 235
        red[:, 1] = 52
        red[:, 2] = 66
        rgb = np.where(dynamic[:, None], red, rgb)
    else:
        rgb, _, _ = height_colors(points, args.zmin, args.zmax)

    write_ply(args.output, points, rgb)


if __name__ == '__main__':
    sys.exit(main())
