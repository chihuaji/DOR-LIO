/* DOR-LIO project page — Live Simulation Lab.
 * 与后端 (simlab/server.py) 交互：网站访客选择 人数/房间/方块/时长/种子，
 * 后台真实运行 Gazebo + DOR-LIO，产出 raw(无滤除) / clean(有滤除) 点云，
 * 就地加载进对比滑块。后端离线时给出提示（静态托管降级）。 */
(function (global) {
  'use strict';

  const STAGE_LABELS = {
    gen_world: '生成随机场景',
    record: 'Gazebo 仿真 + 录包',
    replay_dorlio: 'DOR-LIO 回放（有滤除）',
    replay_raw: '真值累积回放（无滤除）',
    convert: '转换为网页点云',
    done: '完成',
    error: '失败',
    pending: '排队中',
  };

  const API = {
    async health() {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 2500);
      try {
        const r = await fetch('/api/health', { signal: ctl.signal });
        clearTimeout(t);
        if (!r.ok) throw 0;
        return await r.json();
      } catch (e) {
        clearTimeout(t);
        return null;
      }
    },
    async status() {
      const r = await fetch('/api/status');
      if (!r.ok) throw new Error('status ' + r.status);
      return r.json();
    },
    async run(params) {
      const r = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.error || ('HTTP ' + r.status));
      }
      return r.json();
    },
    async runs() {
      const r = await fetch('/api/runs');
      if (!r.ok) throw new Error('runs ' + r.status);
      return (await r.json()).runs;
    },
  };

  function el(sel, root) { return (root || document).querySelector(sel); }

  class SimLab {
    constructor(root) {
      this.root = root;
      root.innerHTML =
        '<div class="lab-grid">' +
        '  <div class="lab-panel">' +
        '    <div class="lab-panel-title">实验参数 <span class="lab-online" id="lab-online"><i></i>检测中…</span></div>' +
        '    <label class="lab-field">房间边长 <output id="v-room">12</output> m' +
        '      <input id="p-room" type="range" min="8" max="20" step="1" value="12"></label>' +
        '    <label class="lab-field">静态方块 <output id="v-boxes">8</output> 个' +
        '      <input id="p-boxes" type="range" min="0" max="16" step="1" value="8"></label>' +
        '    <label class="lab-field">行走行人 <output id="v-people">10</output> 人' +
        '      <input id="p-people" type="range" min="0" max="25" step="1" value="10"></label>' +
        '    <label class="lab-field">录制时长 <output id="v-dur">60</output> s' +
        '      <input id="p-dur" type="range" min="30" max="120" step="10" value="60"></label>' +
        '    <label class="lab-field lab-seed">随机种子' +
        '      <span><input id="p-seed" type="number" min="0" max="999999" value="42">' +
        '      <button id="p-dice" class="lab-dice" title="随机种子">🎲</button></span></label>' +
        '    <button id="lab-run" class="lab-run">▶ 运行仿真对比</button>' +
        '    <p class="lab-note">同一随机种子 → 相同方块布局与行人路线。机器人巡游路线随机。' +
        '    后台真实运行 Gazebo + DOR-LIO，耗时约 (时长 × 3 + 2) 分钟。</p>' +
        '  </div>' +
        '  <div class="lab-progress">' +
        '    <div class="lab-stage-list" id="lab-stages"></div>' +
        '    <div class="lab-bar"><i id="lab-bar-fill"></i></div>' +
        '    <div class="lab-detail" id="lab-detail">等待启动…</div>' +
        '    <div class="lab-result" id="lab-result"></div>' +
        '  </div>' +
        '</div>' +
        '<div class="lab-viewer" id="lab-viewer" hidden></div>';

      this._bind();
      this._checkOnline();
    }

    _bind() {
      const sync = (id, out) => el('#' + out, this.root).textContent =
        el('#' + id, this.root).value;
      [['p-room', 'v-room'], ['p-boxes', 'v-boxes'],
       ['p-people', 'v-people'], ['p-dur', 'v-dur']].forEach(([i, o]) => {
        el('#' + i, this.root).addEventListener('input', () => sync(i, o));
      });
      el('#p-dice', this.root).addEventListener('click', () => {
        el('#p-seed', this.root).value = Math.floor(Math.random() * 100000);
      });
      el('#lab-run', this.root).addEventListener('click', () => this._start());
    }

    async _checkOnline() {
      const badge = el('#lab-online', this.root);
      const btn = el('#lab-run', this.root);
      this.health = await API.health();
      if (this.health && this.health.ok) {
        badge.classList.add('is-online');
        badge.innerHTML = '<i></i>后端在线';
        btn.disabled = false;
        // 如果后端正忙（上次任务还在跑），直接进入轮询
        const st = await API.status().catch(() => null);
        if (st && st.busy) this._poll();
      } else {
        badge.classList.add('is-offline');
        badge.innerHTML = '<i></i>后端离线';
        btn.disabled = true;
        el('#lab-detail', this.root).innerHTML =
          '仿真后端未运行。本地启动方式：<code>python3 simlab/server.py</code>' +
          '（需要 ROS + Gazebo 的机器）。';
      }
    }

    _stages(active) {
      const order = ['gen_world', 'record', 'replay_dorlio', 'replay_raw', 'convert', 'done'];
      const idx = active ? order.indexOf(active) : -1;
      el('#lab-stages', this.root).innerHTML = order.map((s, i) => {
        const cls = i < idx ? 'is-done' : (i === idx ? 'is-active' : '');
        return `<div class="lab-stage ${cls}"><span class="lab-stage-dot"></span>` +
               `${STAGE_LABELS[s] || s}</div>`;
      }).join('');
    }

    async _start() {
      if (!this.health || !this.health.ok) return;
      const btn = el('#lab-run', this.root);
      const params = {
        room: parseFloat(el('#p-room', this.root).value),
        boxes: parseInt(el('#p-boxes', this.root).value, 10),
        people: parseInt(el('#p-people', this.root).value, 10),
        duration: parseInt(el('#p-dur', this.root).value, 10),
        seed: parseInt(el('#p-seed', this.root).value, 10),
      };
      btn.disabled = true;
      btn.textContent = '运行中…';
      el('#lab-result', this.root).innerHTML = '';
      try {
        await API.run(params);
        this._poll();
      } catch (e) {
        el('#lab-detail', this.root).textContent = '提交失败：' + e.message;
        btn.disabled = false;
        btn.textContent = '▶ 运行仿真对比';
      }
    }

    _poll() {
      if (this._timer) clearInterval(this._timer);
      const btn = el('#lab-run', this.root);
      this._timer = setInterval(async () => {
        let st;
        try { st = await API.status(); } catch (e) { return; }
        if (!st.job) return;
        const j = st.job;
        this._stages(j.stage);
        el('#lab-bar-fill', this.root).style.width = Math.round(j.progress * 100) + '%';
        el('#lab-detail', this.root).textContent =
          `${STAGE_LABELS[j.stage] || j.stage} — ${j.detail || ''}`;
        if (j.stage === 'done') {
          clearInterval(this._timer); this._timer = null;
          btn.disabled = false; btn.textContent = '▶ 再跑一次';
          this._loadResult(j.id);
        } else if (j.stage === 'error') {
          clearInterval(this._timer); this._timer = null;
          btn.disabled = false; btn.textContent = '▶ 重新运行';
          el('#lab-detail', this.root).innerHTML =
            `<span class="lab-err">失败：${j.detail || 'see server logs'}</span>`;
        }
      }, 2000);
    }

    async _loadResult(id) {
      const box = el('#lab-result', this.root);
      box.innerHTML = `<a class="lab-open" href="#lab-viewer">结果已生成 ↓</a>`;
      const mount = el('#lab-viewer', this.root);
      mount.hidden = false;
      mount.innerHTML = '<div class="lab-viewer-title">仿真结果 — 拖动把手对比' +
        '<span class="lab-viewer-sub">左：无滤除原始累积（红=动态点） · 右：DOR-LIO 静态地图</span></div>' +
        '<div class="viewer-mount" id="lab-cmp"></div>';
      if (global.CompareViewer) {
        const cmp = new global.CompareViewer(el('#lab-cmp', mount), { pointSize: 1.6 });
        cmp.loadPair(`/runs/${id}/web/raw.ply`, `/runs/${id}/web/clean.ply`);
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('simlab-root');
    if (root) global.SIMLAB = new SimLab(root);
  });
})(window);
