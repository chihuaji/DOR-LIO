#!/usr/bin/env python3
"""gt_accumulator.py — 真值位姿累积原始点云（= 无动态滤除的 raw 地图）.

用 /ground_truth/state 把每帧 /scan 投到世界系并体素降采样累积，
关闭时保存 PCD 到 ~out_pcd。这就是网页对比滑块左侧的“无滤除”基线：
行人鬼影完整保留。
"""
import numpy as np
import rospy
import message_filters
from sensor_msgs.msg import PointCloud
from nav_msgs.msg import Odometry

VOXEL_SIZE = 0.05
LIDAR_OFFSET = np.array([0.0, 0.0, 0.2], dtype=np.float64)

accumulated = np.empty((0, 3), dtype=np.float32)
frame_count = 0


def quat_to_rot(qx, qy, qz, qw):
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ], dtype=np.float64)


def voxel_downsample(arr, voxel_size):
    if len(arr) == 0:
        return arr
    keys = np.floor(arr / voxel_size).astype(np.int32)
    dt = np.dtype([('x', np.int32), ('y', np.int32), ('z', np.int32)])
    view = np.ascontiguousarray(keys).view(dt).reshape(-1)
    _, idx = np.unique(view, return_index=True)
    return arr[idx]


def sync_cb(scan_msg, odom_msg):
    global accumulated, frame_count
    pts = np.array([[p.x, p.y, p.z] for p in scan_msg.points], dtype=np.float64)
    if len(pts) == 0:
        return
    p = odom_msg.pose.pose.position
    q = odom_msg.pose.pose.orientation
    R = quat_to_rot(q.x, q.y, q.z, q.w)
    pts_world = (R @ (pts + LIDAR_OFFSET).T).T + np.array([p.x, p.y, p.z])
    accumulated = np.vstack([accumulated,
                             voxel_downsample(pts_world.astype(np.float32), VOXEL_SIZE)])
    frame_count += 1
    if frame_count % 50 == 0:
        accumulated = voxel_downsample(accumulated, VOXEL_SIZE)
        rospy.loginfo(f'[gt_accumulator] {frame_count} frames | {len(accumulated)} voxels')


def save_pcd():
    out = rospy.get_param('~out_pcd', 'raw_map.pcd')
    if len(accumulated) == 0:
        rospy.logwarn('[gt_accumulator] nothing to save')
        return
    with open(out, 'w') as f:
        f.write('# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\n')
        f.write('SIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n')
        f.write(f'WIDTH {len(accumulated)}\nHEIGHT 1\n')
        f.write('VIEWPOINT 0 0 0 1 0 0 0\n')
        f.write(f'POINTS {len(accumulated)}\nDATA ascii\n')
        for p in accumulated:
            f.write(f'{p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n')
    rospy.loginfo(f'[gt_accumulator] saved {len(accumulated)} pts -> {out}')


if __name__ == '__main__':
    rospy.init_node('simlab_gt_accumulator')
    scan_sub = message_filters.Subscriber('/scan', PointCloud)
    odom_sub = message_filters.Subscriber('/ground_truth/state', Odometry)
    ts = message_filters.ApproximateTimeSynchronizer(
        [scan_sub, odom_sub], queue_size=30, slop=0.02)
    ts.registerCallback(sync_cb)
    rospy.on_shutdown(save_pcd)
    rospy.loginfo('[gt_accumulator] started (raw, no filtering)')
    rospy.spin()
