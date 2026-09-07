#!/usr/bin/env python3
"""Render quick top-down + side previews of PCD maps to verify pairing."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inspect_pcd import read_pcd

def load_xyz(path):
    header, data = read_pcd(path, max_points=600000)
    arr = np.asarray(data)
    if arr.dtype.names:
        x, y, z = arr['x'].astype(float), arr['y'].astype(float), arr['z'].astype(float)
    else:
        x, y, z = arr[:, 0], arr[:, 1], arr[:, 2]
    return x, y, z

def preview(path, out):
    x, y, z = load_xyz(path)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].scatter(x, y, c=z, s=0.1, cmap='turbo', linewidths=0)
    axes[0].set_title('top-down (x-y)')
    axes[0].set_aspect('equal')
    axes[1].scatter(x, z, c=z, s=0.1, cmap='turbo', linewidths=0)
    axes[1].set_title('side (x-z)')
    axes[1].set_aspect('equal')
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(path, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    print('saved', out)

if __name__ == '__main__':
    import sys
    jobs = [
        ('/home/hyd/dynamic_ws/utonia/gazebo_scans.pcd', '/tmp/prev_gazebo_raw.png'),
        ('/home/hyd/dynamic_ws/gazebo/static_map.pcd', '/tmp/prev_gazebo_clean.png'),
        ('/home/hyd/icra-dor-ws/final_ws/src/yifanLIO/PCD/20260905-135900_scans.pcd', '/tmp/prev_real_raw.png'),
        ('/home/hyd/icra-dor-ws/final_ws/src/yifanLIO/PCD/static_map_point.pcd', '/tmp/prev_real_clean.png'),
    ]
    for p, o in jobs:
        preview(p, o)
