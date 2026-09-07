#!/usr/bin/env python3
"""gen_world.py — 参数化生成 Gazebo 动态/静态世界对（贴图行人版，无 GUI，CLI）.

生成两个 world 文件（静态部分完全一致，仅行人不同）：
  auto_dynamic_room.world  含贴图行走行人（Gazebo actor: walk.dae 皮肤动画 +
                            幽灵碰撞体保证雷达可见 + 随机 waypoint 轨迹自动行走）
  auto_static_room.world   不含行人（真值静态参考）

用法:
  python3 gen_world.py --room 12 --boxes 8 --people 10 --seed 42 --out-dir runs/exp_x
"""
import argparse
import json
import math
import os
import random

WALL_T = 0.5
WALL_H = 4.5

WALK_DAE = ('/home/hyd/icra-dor-ws/gazebo_sim/livox_sim_ws/src/'
            'hunav_ros_sim/models/hunav_media/walk.dae')
GAZEBO_SIM_PKG = ('/home/hyd/icra-dor-ws/gazebo_sim/livox_sim_ws/src/'
                  'livox_laser_simulation')

# 预转换的机器人 SDF（xacro → gz sdf -p 生成），直接嵌入 world，
# 避开 gazebo_ros spawn 服务在 actor 场景下的竞态崩溃。
ROBOT_SDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robot.sdf')


def _robot_model_xml():
    import re
    with open(ROBOT_SDF) as f:
        sdf = f.read()
    m = re.search(r'<model name.*?</model>', sdf, re.S)
    if not m:
        raise RuntimeError(f'no <model> found in {ROBOT_SDF}')
    model = m.group(0)
    # model:// / package:// URI 在嵌入 world 时无人解析：
    #  - model:// 会触发联网模型库查询（弱网时挂起）
    #  - package://（雷达插件的 csv_file_name）裸 fstream 打不开
    # 一律替换为包内绝对路径
    model = model.replace(
        "model://livox_laser_simulation/",
        f"{GAZEBO_SIM_PKG}/")
    model = model.replace(
        "package://livox_laser_simulation/",
        f"{GAZEBO_SIM_PKG}/")
    if '<pose' not in model[:120]:
        model = model.replace("'>", "'>\n    <pose>0 0 0.12 0 0 0</pose>", 1)
    return model


def _wall_xml(name, x, y, sx, sy):
    return f"""
  <model name="{name}">
    <static>true</static>
    <pose>{x} {y} {WALL_H / 2} 0 0 0</pose>
    <link name="link">
      <collision name="c"><geometry><box><size>{sx} {sy} {WALL_H}</size></box></geometry></collision>
      <visual name="v">
        <geometry><box><size>{sx} {sy} {WALL_H}</size></box></geometry>
        <material><script><name>Gazebo/Grey</name></script></material>
      </visual>
    </link>
  </model>"""


def _box_xml(i, bx, by, size, yaw):
    return f"""
  <model name="static_box_{i}">
    <static>true</static>
    <pose>{bx} {by} {size / 2} 0 0 {yaw}</pose>
    <link name="link">
      <collision name="c"><geometry><box><size>{size} {size} {size}</size></box></geometry></collision>
      <visual name="v">
        <geometry><box><size>{size} {size} {size}</size></box></geometry>
        <material><script><name>Gazebo/Blue</name></script></material>
      </visual>
    </link>
  </model>"""


def _actor_xml(i, waypoints, speed, delay):
    """贴图行人：walk.dae 动画 + 幽灵碰撞（雷达可见、不产生物理接触）+
    随机 waypoint 闭合轨迹（录制期间不会循环跳变）。"""
    traj = ''
    for (x, y, yaw, t) in waypoints:
        traj += (f'        <waypoint><time>{t:.2f}</time>'
                 f'<pose>{x:.2f} {y:.2f} 0 0 0 {yaw:.2f}</pose></waypoint>\n')
    return f"""
  <actor name="dynamic_person_{i}">
    <link name="actor_link">
      <collision name="actor_collision">
        <pose>0 0 0.9 0 0 0</pose>
        <geometry><cylinder><radius>0.3</radius><length>1.8</length></cylinder></geometry>
        <surface><contact><collide_without_contact>true</collide_without_contact></contact></surface>
      </collision>
    </link>
    <skin><filename>{WALK_DAE}</filename><scale>1.0</scale></skin>
    <animation name="walking"><filename>{WALK_DAE}</filename><interpolate_x>true</interpolate_x></animation>
    <script>
      <loop>true</loop>
      <delay_start>{delay:.2f}</delay_start>
      <auto_start>true</auto_start>
      <trajectory id="{i + 1}" type="walking">
{traj}      </trajectory>
    </script>
  </actor>"""


def build_world(room_size, num_boxes, num_people, seed, include_dynamic,
                traj_seconds=600.0):
    """同名随机种子下，静态部分（方块位置）在两份 world 中完全一致。

    注意：sun 和地面全部内联，不使用 model://sun / model://ground_plane
    include —— 否则 gazebo 会尝试联网下载模型（~/.gazebo/models 无缓存时
    直接挂起，无头流水线不可接受）。
    """
    rng = random.Random(seed)
    half = room_size / 2.0
    margin = 1.6  # 与墙的安全距离

    xml = f"""<?xml version="1.0" ?>
<sdf version="1.6">
<world name="default">
  <light type='directional' name='sun'>
    <cast_shadows>false</cast_shadows>
    <pose>0 0 10 0 0 0</pose>
    <diffuse>0.8 0.8 0.8 1</diffuse>
    <specular>0.2 0.2 0.2 1</specular>
    <direction>-0.5 0.1 -0.9</direction>
  </light>
  <model name='ground_plane'>
    <static>true</static>
    <link name='link'>
      <collision name='collision'>
        <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
        <surface><friction><ode><mu>1</mu><mu2>1</mu2></ode></friction></surface>
      </collision>
      <visual name='visual'>
        <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
        <material><script><name>Gazebo/Grey</name></script></material>
      </visual>
    </link>
  </model>
"""
    if include_dynamic:
        xml += _robot_model_xml()
    xml += _wall_xml("wall_n", 0, half, room_size + WALL_T, WALL_T)
    xml += _wall_xml("wall_s", 0, -half, room_size + WALL_T, WALL_T)
    xml += _wall_xml("wall_e", half, 0, WALL_T, room_size - WALL_T)
    xml += _wall_xml("wall_w", -half, 0, WALL_T, room_size - WALL_T)

    # ---- 随机方块（互不重叠、远离出生点）----
    placed = []
    for i in range(num_boxes):
        for _ in range(80):
            size = rng.uniform(0.5, 1.5)
            bx = rng.uniform(-half + margin + size, half - margin - size)
            by = rng.uniform(-half + margin + size, half - margin - size)
            if math.hypot(bx, by) < 1.2 + size:
                continue
            if all(math.hypot(bx - px, by - py) > (size + ps) / 2 + 0.6
                   for (px, py, ps) in placed):
                placed.append((bx, by, size))
                break
        else:
            continue
        yaw = rng.uniform(0, 3.14)
        xml += _box_xml(i, bx, by, size, yaw)

    # ---- 贴图行人：随机 waypoint 轨迹 ----
    if include_dynamic and num_people > 0:
        for i in range(num_people):
            speed = rng.uniform(0.8, 1.5)
            delay = rng.uniform(0.0, 3.0)
            # 随机路线：从随机起点开始连续取点，速度决定时刻
            cx = rng.uniform(-half + margin, half - margin)
            cy = rng.uniform(-half + margin, half - margin)
            t = 0.0
            waypoints = []
            while t < traj_seconds:
                # 取一个新目标（离方块有一定距离）
                for _ in range(40):
                    nx = rng.uniform(-half + margin, half - margin)
                    ny = rng.uniform(-half + margin, half - margin)
                    if math.hypot(nx - cx, ny - cy) < 1.5:
                        continue
                    if any(math.hypot(nx - bx, ny - by) < bs / 2 + 0.9
                           for (bx, by, bs) in placed):
                        continue
                    break
                else:
                    nx, ny = 0.0, 0.0
                yaw = math.atan2(ny - cy, nx - cx)
                waypoints.append((cx, cy, yaw, t))
                t += math.hypot(nx - cx, ny - cy) / speed
                cx, cy = nx, ny
            waypoints.append((cx, cy, waypoints[-1][2], t))  # 收尾点
            xml += _actor_xml(i, waypoints, speed, delay)

    xml += """
</world>
</sdf>
"""
    return xml


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--room', type=float, default=12.0, help='房间边长 (m)')
    ap.add_argument('--boxes', type=int, default=8, help='静态方块数量')
    ap.add_argument('--people', type=int, default=10, help='动态行人数量')
    ap.add_argument('--seed', type=int, default=None, help='随机种子（缺省随机）')
    ap.add_argument('--traj-seconds', type=float, default=600.0,
                    help='行人轨迹总时长（录制期间不循环）')
    ap.add_argument('--out-dir', required=True, help='输出目录')
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    os.makedirs(args.out_dir, exist_ok=True)

    dyn_path = os.path.join(args.out_dir, 'auto_dynamic_room.world')
    sta_path = os.path.join(args.out_dir, 'auto_static_room.world')
    with open(dyn_path, 'w') as f:
        f.write(build_world(args.room, args.boxes, args.people, seed, True,
                            args.traj_seconds))
    with open(sta_path, 'w') as f:
        f.write(build_world(args.room, args.boxes, args.people, seed, False))

    meta = dict(room=args.room, boxes=args.boxes, people=args.people, seed=seed)
    with open(os.path.join(args.out_dir, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2)

    print(f'[gen_world] seed={seed} room={args.room}m boxes={args.boxes} '
          f'people={args.people}')
    print(f'[gen_world] dynamic -> {dyn_path}')
    print(f'[gen_world] static  -> {sta_path}')


if __name__ == '__main__':
    main()
