#!/usr/bin/env python3
"""Quick PCD inspector: prints header info and bounding box."""
import sys
import numpy as np

def read_pcd(path, max_points=None):
    with open(path, 'rb') as f:
        header = {}
        lines = []
        while True:
            line = f.readline().decode('ascii', 'ignore').strip()
            lines.append(line)
            if line.startswith('VERSION'):
                header['version'] = line.split()[1]
            elif line.startswith('FIELDS'):
                header['fields'] = line.split()[1:]
            elif line.startswith('SIZE'):
                header['size'] = [int(x) for x in line.split()[1:]]
            elif line.startswith('TYPE'):
                header['type'] = line.split()[1:]
            elif line.startswith('COUNT'):
                header['count'] = [int(x) for x in line.split()[1:]]
            elif line.startswith('WIDTH'):
                header['width'] = int(line.split()[1])
            elif line.startswith('POINTS'):
                header['points'] = int(line.split()[1])
            elif line.startswith('DATA'):
                header['data'] = line.split()[1]
                break
        n = header['points']
        if max_points:
            n = min(n, max_points)
        if header['data'] == 'ascii':
            data = np.loadtxt(f, max_rows=n)
        else:
            itemsize = sum(s * c for s, c in zip(header['size'], header['count']))
            dtype_pair = list(zip(header['fields'], ['<f4' if t == 'F' else '<u4' if t == 'U' else '<i4' for t in header['type']]))
            dt = np.dtype(dtype_pair)
            buf = f.read(itemsize * n)
            data = np.frombuffer(buf, dtype=dt)
        return header, data

if __name__ == '__main__':
    for path in sys.argv[1:]:
        header, data = read_pcd(path, max_points=500000)
        arr = np.atleast_2d(np.asarray(data))
        if arr.dtype.names:
            x = arr['x'].astype(float); y = arr['y'].astype(float); z = arr['z'].astype(float)
        else:
            x, y, z = arr[:, 0], arr[:, 1], arr[:, 2]
        print(f"{path}")
        print(f"  fields={header['fields']} n={len(x)}")
        print(f"  x:[{x.min():8.2f},{x.max():8.2f}] y:[{y.min():8.2f},{y.max():8.2f}] z:[{z.min():7.2f},{z.max():7.2f}]")
