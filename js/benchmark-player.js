/* Public benchmarks: one sequence selector and a shared two-video timeline. */
(function () {
  'use strict';
  const root = document.querySelector('[data-benchmark-player]');
  if (!root) return;
  const videos = [...root.querySelectorAll('video')];
  const master = videos[0];
  const tabs = [...root.querySelectorAll('[data-benchmark-sequence]')];
  const toggle = root.querySelector('[data-benchmark-toggle]');
  const seekBar = root.querySelector('[data-benchmark-seek]');
  const time = root.querySelector('[data-benchmark-time]');
  const status = root.querySelector('[data-benchmark-status]');
  let wanted = true, visible = false, starting = false, failed = false, epoch = 0;
  const duration = () => Math.min(...videos.map(v => v.duration || Infinity));
  const stamp = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  function refresh() {
    toggle.textContent = wanted ? 'Pause' : 'Play';
    toggle.setAttribute('aria-label', `${wanted ? 'Pause' : 'Play'} both benchmark videos`);
    const end = duration();
    if (Number.isFinite(end)) {
      seekBar.max = end;
      time.textContent = `${stamp(master.currentTime)} / ${stamp(end)}`;
    }
    seekBar.value = master.currentTime;
  }
  function pause() { epoch++; videos.forEach(v => v.pause()); }
  async function play() {
    if (!wanted || !visible || document.hidden || starting || failed) return;
    if (videos.every(v => !v.paused)) return;
    starting = true;
    const ticket = epoch;
    try {
      await Promise.all(videos.map(v => v.play()));
      if (ticket !== epoch) return;
      if (wanted && visible && !document.hidden) status.textContent = 'Playing · Muted';
      else videos.forEach(v => v.pause());
    } catch (error) {
      if (ticket === epoch && error.name !== 'AbortError') {
        wanted = false; pause(); status.textContent = 'Select Play to start both videos.';
      }
    } finally { starting = false; refresh(); }
  }
  function seek(value) {
    if (videos.some(v => v.readyState < 1)) return;
    pause();
    const t = Math.max(0, Math.min(value, duration() - .04));
    videos.forEach(v => { v.playbackRate = 1; v.currentTime = t; });
    refresh(); play();
  }
  tabs.forEach(tab => tab.addEventListener('click', () => {
    if (tab.getAttribute('aria-pressed') === 'true') return;
    pause(); failed = false; wanted = true;
    const sequence = tab.dataset.benchmarkSequence;
    tabs.forEach(t => { t.classList.toggle('is-active', t === tab); t.setAttribute('aria-pressed', String(t === tab)); });
    videos.forEach((v, i) => {
      const method = i === 0 ? 'ours' : 'fastlio2';
      v.poster = `images/benchmarks/${sequence}-${method}.jpg`;
      v.src = `videos/optimized/${sequence}-${method}.mp4`;
      v.setAttribute('aria-label', `${tab.textContent} ${i === 0 ? 'DOR-LIO' : 'FAST-LIO2'} comparison`);
      v.load();
    });
    status.textContent = 'Loading both views…'; refresh();
  }));
  videos.forEach(v => {
    v.muted = true; v.defaultMuted = true; v.loop = true;
    v.addEventListener('canplay', play);
    v.addEventListener('seeked', play);
    v.addEventListener('waiting', () => { if (wanted && visible) status.textContent = 'Loading video…'; });
    v.addEventListener('error', () => { failed = true; wanted = false; pause(); status.textContent = 'Unable to load this video. Select another sequence or reload to retry.'; refresh(); });
  });
  toggle.addEventListener('click', () => { wanted = !wanted; if (wanted) play(); else { pause(); status.textContent = 'Paused'; } refresh(); });
  seekBar.addEventListener('input', () => seek(+seekBar.value));
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); else play(); });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) play(); else pause(); }, { threshold: .1 }).observe(root);
  } else { visible = true; play(); }
  setInterval(() => {
    if (videos.some(v => v.paused)) play();
    if (visible && !document.hidden) refresh();
  }, 250);
})();
