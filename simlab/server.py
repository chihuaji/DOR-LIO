#!/usr/bin/env python3
"""server.py — DOR-LIO 仿真实验室后端（静态网站 + REST API 同端口）.

端点：
  GET  /api/health          在线状态 + 当前任务
  GET  /api/status          当前任务进度（status.json）
  POST /api/run             提交一次仿真对比实验（同一时刻只跑一个）
  GET  /api/runs            已完成实验列表
  GET  /runs/<id>/<file>    实验产物（PLY/PCD/bag）
  /                        网站静态文件（上级目录）

运行： python3 server.py --port 8900 [--host 0.0.0.0]
注意：0.0.0.0 会把"运行仿真"的能力开放给所有能访问该端口的人，
公网部署请自行加防火墙 / 反向代理鉴权。
"""
import argparse
import glob
import json
import os
import signal
import subprocess
import threading
import time

from flask import Flask, jsonify, request, send_from_directory, abort

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(HERE)
RUNS_ROOT = os.path.join(WEB_ROOT, 'runs')
os.makedirs(RUNS_ROOT, exist_ok=True)

app = Flask(__name__, static_folder=None)

# ------------------------------------------------------------------ jobs
class JobManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.job_dir = None
        self.started = 0.0

    @property
    def busy(self):
        with self.lock:
            return self.proc is not None and self.proc.poll() is None

    def start(self, params):
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                return None, 'a simulation is already running'
            exp_id = time.strftime('sim_%Y%m%d_%H%M%S') + f"_s{params['seed']}"
            job_dir = os.path.join(RUNS_ROOT, exp_id)
            os.makedirs(job_dir, exist_ok=True)
            with open(os.path.join(job_dir, 'status.json'), 'w') as f:
                json.dump({'stage': 'pending', 'progress': 0.0,
                           'detail': 'queued', 'error': None,
                           'updated': time.time()}, f)
            cmd = [
                'python3', os.path.join(HERE, 'run_pipeline.py'),
                '--room', str(params['room']),
                '--boxes', str(params['boxes']),
                '--people', str(params['people']),
                '--seed', str(params['seed']),
                '--duration', str(params['duration']),
                '--out-root', RUNS_ROOT,
            ]
            logf = open(os.path.join(job_dir, 'pipeline.log'), 'a')
            self.proc = subprocess.Popen(cmd, stdout=logf, stderr=logf,
                                         start_new_session=True)
            self.job_dir = job_dir
            self.started = time.time()
            return exp_id, None

    def status(self):
        with self.lock:
            running = self.proc is not None and self.proc.poll() is None
            job_dir = self.job_dir
        data = {'busy': running}
        if job_dir and os.path.exists(os.path.join(job_dir, 'status.json')):
            try:
                with open(os.path.join(job_dir, 'status.json')) as f:
                    data['job'] = json.load(f)
                data['job']['id'] = os.path.basename(job_dir)
            except (json.JSONDecodeError, OSError):
                pass
        elif job_dir:
            data['job'] = {'id': os.path.basename(job_dir), 'stage': 'unknown'}
        return data


jobs = JobManager()

LIMITS = {
    'room': (6.0, 24.0, float),
    'boxes': (0, 20, int),
    'people': (0, 30, int),
    'duration': (30, 240, int),
    'seed': (0, 999999, int),
}

# ------------------------------------------------------------------ api
@app.after_request
def cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp


@app.route('/api/health')
def health():
    return jsonify({'ok': True, 'busy': jobs.busy,
                    'uptime': int(time.time() - START)})


@app.route('/api/status')
def status():
    return jsonify(jobs.status())


@app.route('/api/run', methods=['POST', 'OPTIONS'])
def run():
    if request.method == 'OPTIONS':
        return ('', 204)
    payload = request.get_json(silent=True) or {}
    params = {}
    for key, (lo, hi, cast) in LIMITS.items():
        val = payload.get(key)
        if val is None:
            abort(400, description=f'missing param: {key}')
        try:
            val = cast(val)
        except (TypeError, ValueError):
            abort(400, description=f'bad param: {key}')
        if not (lo <= val <= hi):
            abort(400, description=f'{key} out of range [{lo}, {hi}]')
        params[key] = val
    exp_id, err = jobs.start(params)
    if exp_id is None:
        return jsonify({'error': err}), 409
    return jsonify({'ok': True, 'id': exp_id})


@app.route('/api/runs')
def list_runs():
    runs = []
    for path in sorted(glob.glob(os.path.join(RUNS_ROOT, '*', 'result.json')),
                       reverse=True):
        try:
            with open(path) as f:
                runs.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
        if len(runs) >= 50:
            break
    return jsonify({'runs': runs})


@app.route('/runs/<path:sub>')
def runs_files(sub):
    # 只允许访问 runs/ 下两层，防目录穿越
    parts = sub.split('/')
    if len(parts) > 3 or '..' in parts:
        abort(404)
    return send_from_directory(RUNS_ROOT, sub)


# ------------------------------------------------------------------ static site
@app.route('/')
def index():
    return send_from_directory(WEB_ROOT, 'index.html')


@app.route('/<path:sub>')
def static_files(sub):
    parts = sub.split('/')
    if '..' in parts:
        abort(404)
    # site assets (css/js/data/images) live in WEB_ROOT; simlab/ blocked
    if parts[0] in ('simlab', 'tools', 'runs'):
        abort(404)
    return send_from_directory(WEB_ROOT, sub)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8900)
    ap.add_argument('--host', default='127.0.0.1')
    args = ap.parse_args()
    START = time.time()
    signal.signal(signal.SIGINT, signal.default_int_handler)
    print(f'[server] site + api on http://{args.host}:{args.port}')
    app.run(host=args.host, port=args.port, threaded=True, debug=False)
