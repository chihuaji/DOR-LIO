#!/usr/bin/env python3
"""run_pipeline.py — DOR-LIO 仿真对比实验全流程编排（后台无头运行）.

一次运行完成：
  1. gen_world     按 (room, boxes, people, seed) 生成动态/静态世界对
  2. record        无头 Gazebo + 随机行人 + 机器人随机路线 + 动态标注器，录 gazebo.bag
  3. replay_dorlio 同一 bag 回放进 DOR-LIO（有滤除）→ static_map_point.pcd
  4. replay_raw    同一 bag 用真值位姿累积（无滤除）→ raw_map.pcd
  5. convert       两张图转 PLY（raw 侧动态鬼影自动标红），输出 web/{raw,clean}.ply
  6. result.json + status.json（供网页轮询）

用法（本身就可以用 nohup 放后台）：
  python3 run_pipeline.py --room 12 --boxes 8 --people 10 --seed 42 \
      --duration 90 --out-root ../runs
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
DOR_WEB = os.path.dirname(HERE)

# 使用 gazebo_sim 工作区（带 always_on 传感器修复 + 贴图行人 + IMU 噪声模型）
GAZEBO_SIM_WS = '/home/hyd/icra-dor-ws/gazebo_sim/livox_sim_ws'
YIFANLIO_WS = '/home/hyd/icra-dor-ws/final_ws'

# 每次运行随机 master 端口（11330-11399），彻底避开用户自己的 11311 会话与残留 master
import random as _random
MASTER_PORT = 11330 + _random.randint(0, 69)

ROS_ENV = (
    'source /opt/ros/noetic/setup.bash && '
    f'source {GAZEBO_SIM_WS}/devel/setup.bash && '
    f'source {YIFANLIO_WS}/devel/setup.bash && '
    # final_ws 的 devel 会重置 ROS_PACKAGE_PATH（overlay 链不含 livox_sim_ws），
    # 补回 livox 仿真包源码目录（GAZEBO_PLUGIN_PATH 不受影响）
    f'export ROS_PACKAGE_PATH={GAZEBO_SIM_WS}/src:$ROS_PACKAGE_PATH && '
    f'export ROS_MASTER_URI=http://127.0.0.1:{MASTER_PORT} && '
    # final_ws 的 devel 同样会重建 GAZEBO_PLUGIN_PATH（丢失 livox 插件），
    # 显式补回，否则雷达插件加载失败、/scan 静默无输出
    f'export GAZEBO_PLUGIN_PATH={GAZEBO_SIM_WS}/devel/lib:/opt/ros/noetic/lib:$GAZEBO_PLUGIN_PATH && '
    'export ROS_HOME=/tmp/dor_simlab_ros && '
    'mkdir -p /tmp/dor_simlab_ros && '
)

# launch 一律用绝对路径，避免 roslaunch 包名解析到 dynamic_ws 下的旧副本
HEADLESS_LAUNCH = (f'{GAZEBO_SIM_WS}/src/livox_laser_simulation/launch/'
                   'simlab_headless.launch')
REPLAY_LAUNCH = f'{YIFANLIO_WS}/src/yifanLIO/launch/simlab_replay.launch'

# 清理历史残留进程。注意用 [.] 防止 pkill -f 匹配到自身所在的 bash -c 命令行。
CLEANUP = (
    "pkill -9 -f 'simlab_headless[.]launch' ; "
    "pkill -9 -f 'gzserver.*auto_dynamic_room' ; "
    "pkill -9 -f 'dynamic_labeler[.]py' ; "
    "pkill -9 -f 'simlab/random_walker[.]py' ; "
    "pkill -9 -f 'simlab/random_driver[.]py' ; "
    "pkill -9 -f 'simlab/gt_accumulator[.]py' ; "
    "pkill -9 -f 'rosbag record.*gazebo[.]bag' ; "
    "pkill -9 -f 'rosbag play.*gazebo[.]bag' ; "
    "pkill -9 -f 'rosmaster.*-p 113[3-9][0-9]' ; "
    "true"
)

BAG_TOPICS = ['/scan', '/scan_labeled_pc2', '/imu/data', '/ground_truth/state',
              '/gazebo/model_states', '/tf', '/tf_static']

STAGES = ['gen_world', 'record', 'replay_dorlio', 'replay_raw', 'convert']


class Stage:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.status_path = os.path.join(out_dir, 'status.json')
        self.write('pending', 0.0, 'queued')

    def write(self, stage, progress, detail, error=None):
        status = {
            'stage': stage,
            'progress': round(progress, 3),
            'detail': detail,
            'error': error,
            'updated': time.time(),
        }
        tmp = self.status_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(status, f, indent=2)
        os.replace(tmp, self.status_path)


def sh(cmd, timeout=None, log=None, check=True):
    """Run a shell command under the ROS environment."""
    full = ROS_ENV + cmd
    proc = subprocess.run(['bash', '-c', full], capture_output=True, text=True,
                          timeout=timeout)
    if log:
        with open(log, 'a') as f:
            f.write(f'$ {cmd}\n{proc.stdout}\n{proc.stderr}\n')
    if check and proc.returncode != 0:
        raise RuntimeError(f'command failed ({proc.returncode}): {cmd}\n'
                           f'{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}')
    return proc


def popen(cmd, log_path):
    """Start a background process under the ROS environment (own session)."""
    full = ROS_ENV + f'exec {cmd}'
    logf = open(log_path, 'a')
    return subprocess.Popen(['bash', '-c', full], stdout=logf, stderr=logf,
                            start_new_session=True)


def stop(proc, name, sig_timeout=25, kill=True):
    """SIGINT a process, wait, escalate to SIGKILL."""
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=sig_timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    if kill:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def wait_for_topic(topic, timeout=90, log=None):
    """Wait until a topic publishes at least one message."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = subprocess.run(
            ['bash', '-c', ROS_ENV + f'timeout 4 rostopic echo -n 1 --noarr {topic}'],
            capture_output=True, text=True)
        if p.returncode == 0:
            return True
        time.sleep(1.5)
    raise RuntimeError(f'topic {topic} not available after {timeout}s')


def run_pipeline(args, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    log_dir = os.path.join(out_dir, 'log')
    os.makedirs(log_dir, exist_ok=True)
    web_dir = os.path.join(out_dir, 'web')
    os.makedirs(web_dir, exist_ok=True)
    st = Stage(out_dir)
    t_start = time.time()

    # clean leftovers from any previous crashed run
    sh(CLEANUP, check=False, timeout=30)

    # 全程专用 rosmaster：各 roslaunch 直接加入而非各自拉起，
    # 否则上一阶段 roslaunch 退出会把自带的 master 一起带走
    # 注意：rosmaster 不读 ROS_MASTER_URI 环境变量，必须显式 -p 指定端口
    master = popen(f'rosmaster -p {MASTER_PORT}',
                   os.path.join(log_dir, 'rosmaster.log'))
    time.sleep(4)
    try:
        return run_stages(args, out_dir, st, log_dir, web_dir, t_start)
    finally:
        stop(master, 'rosmaster', sig_timeout=15)


def run_stages(args, out_dir, st, log_dir, web_dir, t_start):

    # ---------------- stage 1: world ----------------
    st.write('gen_world', 0.02, 'generating world pair')
    sh(f'python3 {HERE}/gen_world.py --room {args.room} --boxes {args.boxes} '
       f'--people {args.people} --seed {args.seed} --out-dir "{out_dir}"',
       log=os.path.join(log_dir, 'gen_world.log'))
    world = os.path.join(out_dir, 'auto_dynamic_room.world')
    st.write('gen_world', 0.08, f'seed={args.seed} room={args.room}m '
            f'boxes={args.boxes} people={args.people}')

    # ---------------- stage 2: simulate + record ----------------
    st.write('record', 0.10, 'starting headless gazebo')
    sim = popen(f'roslaunch {HEADLESS_LAUNCH} '
                f'world_name:={world} gui:=false',
                os.path.join(log_dir, 'gazebo.log'))
    try:
        wait_for_topic('/imu/data', timeout=120)
        if sim.poll() is not None:
            raise RuntimeError('gazebo died during startup — see log/gazebo.log')
        wait_for_topic('/scan', timeout=90)
        if sim.poll() is not None:
            raise RuntimeError('gazebo died before lidar came up — see log/gazebo.log')
        st.write('record', 0.16, 'gazebo up (textured actors walking), starting driver')

        # labeler 兼作 PointCloud→PointCloud2 转换器（LIO 订阅 /scan_labeled_pc2）
        labeler = popen(f'python3 -u /home/hyd/icra-dor-ws/gazebo_sim/dynamic_labeler.py',
                        os.path.join(log_dir, 'labeler.log'))
        driver = popen(f'python3 -u {HERE}/random_driver.py _room_size:={args.room} '
                       f'_speed:={args.speed}',
                       os.path.join(log_dir, 'driver.log'))
        time.sleep(6)  # let actors get moving before recording
        wait_for_topic('/scan_labeled_pc2', timeout=90)
        if sim.poll() is not None:
            raise RuntimeError('gazebo died while running — see log/gazebo.log')

        bag_path = os.path.join(out_dir, 'gazebo.bag')
        st.write('record', 0.22, f'recording {args.duration}s bag')
        rec = popen(f'rosbag record -q --buffsize 0 -O {bag_path} '
                    + ' '.join(BAG_TOPICS),
                    os.path.join(log_dir, 'record.log'))

        # progress updates while recording
        t0 = time.time()
        while time.time() - t0 < args.duration:
            time.sleep(2)
            frac = min((time.time() - t0) / args.duration, 1.0)
            st.write('record', 0.22 + 0.33 * frac,
                     f'recording {int(time.time() - t0)}/{args.duration}s')

        st.write('record', 0.56, 'stopping simulation')
        stop(rec, 'rosbag', sig_timeout=25)
        time.sleep(2)
        stop(labeler, 'labeler', sig_timeout=8)
        stop(driver, 'driver', sig_timeout=8)
        stop(sim, 'roslaunch', sig_timeout=40)
        time.sleep(4)
        sh(CLEANUP, check=False, timeout=30)
        if not os.path.exists(bag_path):
            raise RuntimeError('bag file missing after recording')
        if not os.path.getsize(bag_path) > 1e6:
            raise RuntimeError('bag suspiciously small')
    except Exception:
        stop(sim, 'roslaunch')
        sh(CLEANUP, check=False, timeout=30)
        raise

    # ---------------- stage 3: replay through DOR-LIO ----------------
    st.write('replay_dorlio', 0.60, 'replaying bag through DOR-LIO (filtered)')
    replay_out = os.path.join(out_dir, 'dorlio_out')
    os.makedirs(replay_out, exist_ok=True)
    sh(f'rosparam set use_sim_time true', check=False)
    lio = popen(f'roslaunch {REPLAY_LAUNCH} save_map_path:={replay_out}/',
                os.path.join(log_dir, 'lio.log'))
    time.sleep(6)
    play = popen(f'rosbag play --clock {bag_path}',
                 os.path.join(log_dir, 'play_lio.log'))
    play.wait(timeout=args.duration + 300)
    time.sleep(3)
    # 地图保存由 /save_map 话题触发（freenode.save_map_callback），关停不会保存
    st.write('replay_dorlio', 0.72, 'saving filtered static map…')
    static_map = os.path.join(replay_out, 'static_map_point.pcd')
    sh('rostopic pub -1 /save_map std_msgs/Empty', check=False, timeout=30)
    for _ in range(60):  # ASCII PCD 写盘可能较慢，最多等 5 分钟
        if os.path.exists(static_map):
            break
        time.sleep(5)
    stop(lio, 'lio', sig_timeout=60)
    sh("pkill -9 -f 'devel/lib/lio/lio' ; true", check=False, timeout=20)
    if not os.path.exists(static_map):
        raise RuntimeError('DOR-LIO did not produce static_map_point.pcd — '
                           f'check {log_dir}/lio.log')

    # ---------------- stage 4: raw GT accumulation (no filtering) ----------------
    st.write('replay_raw', 0.76, 'replaying bag for raw accumulation (unfiltered)')
    raw_pcd = os.path.join(out_dir, 'raw_map.pcd')
    sh('rosparam set use_sim_time true', check=False)
    acc = popen(f'python3 -u {HERE}/gt_accumulator.py _out_pcd:={raw_pcd}',
                os.path.join(log_dir, 'accumulator.log'))
    time.sleep(4)
    play2 = popen(f'rosbag play --clock {bag_path}',
                  os.path.join(log_dir, 'play_acc.log'))
    play2.wait(timeout=args.duration + 300)
    time.sleep(3)
    stop(acc, 'accumulator', sig_timeout=120)
    sh('rosparam set use_sim_time false', check=False)
    if not os.path.exists(raw_pcd):
        raise RuntimeError('raw map missing — check accumulator.log')

    # ---------------- stage 5: convert for web ----------------
    st.write('convert', 0.88, 'converting maps to web PLY')
    clean_ply = os.path.join(web_dir, 'clean.ply')
    raw_ply = os.path.join(web_dir, 'raw.ply')
    sh(f'python3 {DOR_WEB}/tools/pcd_to_ply.py -i {static_map} -o {clean_ply} '
       f'--mode height --voxel 0.06 --max-points 500000',
       log=os.path.join(log_dir, 'convert.log'))
    sh(f'python3 {DOR_WEB}/tools/pcd_to_ply.py -i {raw_pcd} -o {raw_ply} '
       f'--mode diff --ref {static_map} --diff-thresh 0.25 '
       f'--voxel 0.06 --max-points 600000',
       log=os.path.join(log_dir, 'convert.log'))

    result = {
        'id': os.path.basename(out_dir),
        'params': {'room': args.room, 'boxes': args.boxes, 'people': args.people,
                   'seed': args.seed, 'duration': args.duration},
        'created': time.time(),
        'wall_time_s': round(time.time() - t_start, 1),
        'files': {
            'bag': 'gazebo.bag',
            'clean_ply': 'web/clean.ply',
            'raw_ply': 'web/raw.ply',
            'static_map_pcd': 'dorlio_out/static_map_point.pcd',
            'raw_map_pcd': 'raw_map.pcd',
        },
    }
    with open(os.path.join(out_dir, 'result.json'), 'w') as f:
        json.dump(result, f, indent=2)
    st.write('done', 1.0, f'finished in {result["wall_time_s"]}s')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--room', type=float, default=12.0)
    ap.add_argument('--boxes', type=int, default=8)
    ap.add_argument('--people', type=int, default=10)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--duration', type=int, default=90)
    ap.add_argument('--speed', type=float, default=0.8)
    ap.add_argument('--out-root', default=os.path.join(DOR_WEB, 'runs'))
    args = ap.parse_args()

    import random as _r
    seed = args.seed if args.seed is not None else _r.randint(0, 999999)
    args.seed = seed

    exp_id = time.strftime('sim_%Y%m%d_%H%M%S') + f'_s{seed}'
    out_dir = os.path.join(args.out_root, exp_id)
    os.makedirs(out_dir, exist_ok=True)
    print(f'[pipeline] run dir: {out_dir}')

    st = Stage(out_dir)
    try:
        result = run_pipeline(args, out_dir)
        print(f'[pipeline] DONE in {result["wall_time_s"]}s -> {out_dir}')
    except Exception as e:
        traceback.print_exc()
        st.write('error', 0.0, str(e)[:400], error=traceback.format_exc()[-3000:])
        # best-effort cleanup
        sh(CLEANUP, check=False, timeout=30)
        sys.exit(1)


if __name__ == '__main__':
    main()
