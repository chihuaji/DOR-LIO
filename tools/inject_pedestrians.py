#!/usr/bin/env python3
"""
inject_pedestrians.py — Synthesize walking-pedestrian ghost artifacts on top of
a real static map, producing a "raw accumulation" demo for the before/after
wipe slider on the DOR-LIO project page.

The static geometry and its colors come from the real DOR-LIO static map PLY
untouched; injected pedestrian points are painted red so the wipe highlights
exactly what dynamic object removal eliminates.

Usage:
  python3 inject_pedestrians.py --base data/campus_clean.ply \
      --out data/campus_raw_demo.ply --pedestrians 10
"""
import argparse
import numpy as np

try:
    from scipy.spatial import cKDTree
except ImportError:
    raise SystemExit('scipy is required')


def read_ply(path):
    with open(path, 'rb') as f:
        n, props, fmt = None, [], None
        while True:
            line = f.readline().decode('ascii').strip()
            if line.startswith('element vertex'):
                n = int(line.split()[2])
            elif line.startswith('property'):
                props.append(line.split()[1:])
            elif line.startswith('format'):
                fmt = line.split()[1]
            elif line == 'end_header':
                break
        names = [p[1] for p in props]
        assert fmt == 'binary_little_endian'
        assert names == ['x', 'y', 'z', 'red', 'green', 'blue'], names
        dtype = np.dtype([('xyz', '<f4', 3), ('rgb', 'u1', 3)])
        data = np.frombuffer(f.read(n * dtype.itemsize), dtype=dtype)
    return data['xyz'].astype(np.float64), data['rgb'].astype(np.int64)


def write_ply(path, points, rgb):
    n = len(points)
    header = (
        'ply\nformat binary_little_endian 1.0\n'
        'comment static geometry from DOR-LIO, pedestrians synthesized '
        '(demo placeholder)\n'
        f'element vertex {n}\n'
        'property float x\nproperty float y\nproperty float z\n'
        'property uchar red\nproperty uchar green\nproperty uchar blue\n'
        'end_header\n').encode('ascii')
    vertices = np.empty(n, dtype=[('xyz', '<f4', 3), ('rgb', 'u1', 3)])
    vertices['xyz'] = points
    vertices['rgb'] = rgb
    with open(path, 'wb') as f:
        f.write(header)
        f.write(vertices.tobytes())
    print(f'[write] {path}: {n} points '
          f'({(len(header) + n * 15) / 1e6:.1f} MB)')


# --------------------------------------------------------------------------- #
# Human body sampler (local frame: x forward, z up, origin at ground)
# --------------------------------------------------------------------------- #
def _ellipsoid(center, radii, n, rng):
    u = rng.uniform(0, 2 * np.pi, n)
    v = np.arccos(rng.uniform(-1, 1, n))
    d = np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1)
    return center + d * radii


def _limb(x0, x1, r, n, rng):
    t = rng.uniform(0, 1, n)
    ang = rng.uniform(0, 2 * np.pi, n)
    axis = x1 - x0
    # build orthonormal basis perpendicular to the limb axis
    a = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, a); u /= np.linalg.norm(u)
    v = np.cross(axis, u) / np.linalg.norm(axis)
    return (x0 + t[:, None] * axis
            + r * (np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * v))


def sample_human(rng, phase, n_points=900):
    """Return (points, normals) of a stylized pedestrian in walking pose."""
    pts = []
    swing = 0.18 * np.sin(phase)
    # torso
    pts.append(_ellipsoid(np.array([0, 0, 1.12]), np.array([0.17, 0.11, 0.33]),
                          int(n_points * 0.45), rng))
    # head
    pts.append(_ellipsoid(np.array([0, 0, 1.60]), np.array([0.10, 0.09, 0.11]),
                          int(n_points * 0.12), rng))
    # legs (swing with phase)
    for s in (+1, -1):
        pts.append(_limb(np.array([s * swing, s * 0.09, 0.80]),
                         np.array([-s * swing, s * 0.09, 0.02]),
                         0.055, int(n_points * 0.14), rng))
    # arms (opposite phase)
    for s in (+1, -1):
        pts.append(_limb(np.array([-s * swing, s * 0.24, 1.30]),
                         np.array([s * swing, s * 0.26, 0.78]),
                         0.040, int(n_points * 0.075), rng))
    pts = np.concatenate(pts)
    return pts


def normalize(v):
    return v / (np.linalg.norm(v) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='real clean map PLY')
    ap.add_argument('--out', required=True)
    ap.add_argument('--pedestrians', type=int, default=10)
    ap.add_argument('--step', type=float, default=0.45,
                    help='meters between accumulated human instances')
    ap.add_argument('--seed', type=int, default=7)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    base_xyz, base_rgb = read_ply(args.base)
    tree = cKDTree(base_xyz)
    center = (base_xyz.min(0) + base_xyz.max(0)) / 2
    extent = base_xyz.max(0) - base_xyz.min(0)

    ghost_pts = []
    n_paths = 0
    attempts = 0
    while n_paths < args.pedestrians and attempts < args.pedestrians * 40:
        attempts += 1
        seed_idx = rng.integers(0, len(base_xyz))
        start = base_xyz[seed_idx].copy()
        # ground must exist around the start
        nb = tree.query_ball_point(start[:2].tolist() + [1e9], r=0)  # unused
        near = base_xyz[tree.query_ball_point(start, 3.0)]
        if len(near) < 150:
            continue
        ground0 = np.percentile(near[:, 2], 10)
        start[2] = ground0

        direction2 = rng.uniform(-1, 1, 2)
        direction2 /= np.linalg.norm(direction2) + 1e-9
        length = rng.uniform(15, 45)
        n_steps = int(length / args.step)
        sensor = start[:2] + rng.uniform(-18, 18, 2)  # where the "scanner" is
        phase0 = rng.uniform(0, 2 * np.pi)
        speed_jitter = rng.uniform(0.9, 1.3)

        path_pts = []
        ok = True
        for i in range(n_steps):
            pos = start[:2] + direction2 * (i * args.step * speed_jitter)
            probe = np.array([pos[0], pos[1], start[2]])
            near = base_xyz[tree.query_ball_point(probe, 2.0)]
            if len(near) < 40:
                ok = i > 10  # allow paths to end at map borders
                break
            ground = np.percentile(near[:, 2], 10)
            # skip if local ground is a wall/roof (too high variance)
            if np.percentile(near[:, 2], 90) - ground > 6.0 and i == 0:
                ok = False
                break
            yaw = rng.uniform(0, 2 * np.pi)
            c, s = np.cos(yaw), np.sin(yaw)
            R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            human = sample_human(rng, phase0 + i * speed_jitter) @ R.T
            human[:, :2] += pos
            human[:, 2] += ground
            # keep only the side facing the sensor (partial scan shells)
            to_sensor = normalize(np.array([sensor[0] - pos[0],
                                            sensor[1] - pos[1], 0]))
            view = normalize(np.array([R[0, 0], R[1, 0], 0]))  # human forward
            facing = (human - np.array([pos[0], pos[1], ground])) @ to_sensor
            # crude: keep points whose offset direction is toward sensor
            off = human - np.array([pos[0], pos[1], ground])
            off[:, 2] = 0
            off = off / (np.linalg.norm(off, axis=1, keepdims=True) + 1e-9)
            keep = (off @ to_sensor) > 0.05
            # always keep head/torso core so silhouettes stay readable
            keep |= human[:, 2] > ground + 1.0
            human = human[keep] + rng.normal(0, 0.01, human[keep].shape)
            path_pts.append(human)
            _ = view  # (reserved)
        if not ok or not path_pts:
            continue
        ghost_pts.append(np.concatenate(path_pts))
        n_paths += 1
        print(f'  path {n_paths}: {len(path_pts)} instances, '
              f'{len(ghost_pts[-1])} points')

    if not ghost_pts:
        raise SystemExit('no pedestrian path found — check the base map')

    ghosts = np.concatenate(ghost_pts)
    # cap ghost density for web payload
    if len(ghosts) > 260000:
        sel = rng.choice(len(ghosts), 260000, replace=False)
        ghosts = ghosts[sel]
    ghost_rgb = np.zeros((len(ghosts), 3), dtype=np.int64)
    ghost_rgb[:, 0] = 235
    ghost_rgb[:, 1] = 52
    ghost_rgb[:, 2] = 66

    print(f'[inject] {len(ghosts)} ghost points from {n_paths} pedestrians '
          f'(red), on top of {len(base_xyz)} static points')
    write_ply(args.out,
              np.concatenate([base_xyz, ghosts]).astype(np.float32),
              np.concatenate([base_rgb, ghost_rgb]).astype(np.uint8))


if __name__ == '__main__':
    main()
