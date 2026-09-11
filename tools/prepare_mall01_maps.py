#!/usr/bin/env python3
"""Export bounded-size display maps; never change source maps or evaluation results."""
import hashlib
import json
from pathlib import Path
import numpy as np
from pcd_to_ply import height_colors, voxel_downsample, limit_points, write_ply

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/home/hyd/icra-dor-ws/baseline_icra/selfcollected_runs/results')
SOURCES = {
    'ours': Path('/home/hyd/dynamic_ws/yflio_dynamic_ws/pcd/my/longhufloor1.pcd'),
    'fastlio2': BASE / 'fastlio2/offline_20260911_floor1/full_map.pcd',
    'btsa': BASE / 'btsa/run_20260910T100519/btsa_floor1_static_map.pcd',
    'dufomap': BASE / 'dufomap/offline_20260911_floor1/static_map.pcd',
}


def sample_pcd(path, cap=2000000):
    header = {}
    with path.open('rb') as stream:
        while True:
            line = stream.readline()
            if not line:
                raise ValueError('Incomplete PCD header')
            parts = line.decode('ascii').split()
            if not parts or parts[0].startswith('#'):
                continue
            header[parts[0]] = parts[1:]
            if parts[0] == 'DATA':
                offset = stream.tell()
                break
    if header['DATA'] != ['binary'] or set(header['TYPE']) != {'F'} or set(header['SIZE']) != {'4'}:
        raise ValueError('This exporter requires binary float32 source fields')
    if set(header.get('COUNT', ['1'])) != {'1'}:
        raise ValueError('Only scalar fields supported')
    count = int(header['POINTS'][0])
    dtype = np.dtype([(name, '<f4') for name in header['FIELDS']])
    if path.stat().st_size != offset + count * dtype.itemsize:
        raise ValueError('PCD payload size mismatch')
    cloud = np.memmap(path, dtype=dtype, mode='r', offset=offset, shape=(count,))
    # Evenly spaced deterministic samples across the entire file, not a prefix crop.
    indexes = np.linspace(0, count - 1, min(cap, count), dtype=np.int64)
    selected = cloud[indexes]
    points = np.column_stack([selected[c] for c in ['x', 'y', 'z']])
    return points[np.isfinite(points).all(axis=1)], count


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    output = ROOT / 'data/mall01'
    output.mkdir(exist_ok=True)
    transforms = json.loads((output / 'display-transforms.json').read_text())
    reference, _ = sample_pcd(SOURCES['ours'])
    origin = np.median(reference, axis=0).astype(float)
    zmin, zmax = np.percentile(reference[:, 2], [2, 98])
    del reference
    manifest = {
        'sequence': 'Mall 01 / floor1.bag',
        'purpose': 'Qualitative browser visualization only; no metric recomputation',
        'display_origin_in_dor_frame': origin.tolist(),
        'height_color_range_in_dor_frame_m': [float(zmin), float(zmax)],
        'sampling': {'pre_sample_cap': 2000000, 'voxel_m': 0.1, 'output_cap': 650000, 'seed': 0},
        'registration': 'Rigid display alignment only. FAST-LIO2 and DUFOMap share one transform. BTSA has a separately estimated rigid transform. No scale or nonrigid correction.',
        'maps': {},
    }
    for name, path in SOURCES.items():
        initial_stat = path.stat()
        points, count = sample_pcd(path)
        matrix = np.eye(4) if name == 'ours' else np.array(transforms[name]['matrix'])
        points = points @ matrix[:3, :3].T + matrix[:3, 3]
        points, _ = voxel_downsample(points, None, .1)
        points, _ = limit_points(points, None, 650000, seed=0)
        rgb, _, _ = height_colors(points, zmin=zmin, zmax=zmax)
        target = output / (name + '.ply')
        write_ply(target, points - origin, rgb)
        digest = sha256(path)
        final_stat = path.stat()
        assert (initial_stat.st_size, initial_stat.st_mtime_ns) == (final_stat.st_size, final_stat.st_mtime_ns), 'Source changed during export'
        manifest['maps'][name] = {'source': str(path), 'source_points': count, 'source_bytes': initial_stat.st_size,
                                  'source_sha256': digest, 'output_points': len(points), 'output': str(target.relative_to(ROOT)),
                                  'output_sha256': sha256(target), 'display_transform': matrix.tolist()}
        print(name, count, '->', len(points), flush=True)
        del points, rgb
    (output / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
