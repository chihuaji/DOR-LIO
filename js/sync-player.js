/* Three views share the global video's clock and one playback intent. */
(function () {
  'use strict';
  const root = document.querySelector('[data-sync-player]');
  if (!root) return;
  const videos = [...root.querySelectorAll('video')];
  const master = root.querySelector('#tour-global');
  const followers = videos.filter((v) => v !== master);
  const toggle = root.querySelector('[data-sync-toggle]');
  const slider = root.querySelector('[data-sync-seek]');
  const time = root.querySelector('[data-sync-time]');
  const status = root.querySelector('[data-sync-status]');
  const keys = [...root.querySelectorAll('[data-keyframe-time]')];
  let wanted = true;
  let visible = false;
  let starting = false;
  let failed = false;
  let pendingTime = null;
  let generation = 0;
  const duration = () => Math.min(...videos.map((v) => v.duration || Infinity));
  const stamp = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  function refresh() {
    const end = duration();
    toggle.textContent = wanted ? 'Pause' : 'Play';
    toggle.setAttribute('aria-label', wanted ? 'Pause all views' : 'Play all views');
    if (Number.isFinite(end)) {
      slider.max = end;
      time.textContent = `${stamp(master.currentTime)} / ${stamp(end)}`;
    }
    slider.value = master.currentTime;
    const active = keys.filter((k) => +k.dataset.keyframeTime <= master.currentTime + 0.1).pop();
    keys.forEach((k) => {
      k.classList.toggle('is-active', k === active);
      if (k === active) k.setAttribute('aria-current', 'true');
      else k.removeAttribute('aria-current');
    });
  }
  function pauseAll() {
    generation++;
    videos.forEach((v) => v.pause());
  }
  async function start() {
    if (!wanted || !visible || document.hidden || starting || failed || pendingTime !== null) return;
    if (videos.some((v) => v.readyState < 3 || v.seeking)) return;
    starting = true;
    const ticket = generation;
    try {
      await Promise.all(videos.map((v) => v.play()));
      if (ticket !== generation || !wanted || !visible || document.hidden) {
        videos.forEach((v) => v.pause());
      } else status.textContent = 'Synchronized playback · Muted';
    } catch (error) {
      if (error.name === 'NotAllowedError') {
        wanted = false;
        pauseAll();
        status.textContent = 'Select Play to start all three views.';
      } else if (error.name !== 'AbortError') {
        pauseAll();
        wanted = false;
        status.textContent = 'Playback interrupted. Select Play to retry.';
      }
    } finally {
      starting = false;
      refresh();
    }
  }
  function seek(target, resume) {
    if (resume !== undefined) wanted = resume;
    pauseAll();
    if (videos.some((v) => v.readyState < 1)) {
      pendingTime = target;
      status.textContent = 'Loading the selected moment…';
      return;
    }
    pendingTime = null;
    const t = Math.max(0, Math.min(target, duration() - 0.05));
    videos.forEach((v) => { v.currentTime = t; });
    refresh();
    start();
  }
  videos.forEach((v) => {
    v.muted = true;
    v.defaultMuted = true;
    v.addEventListener('loadedmetadata', () => {
      if (pendingTime !== null && videos.every((p) => p.readyState >= 1)) seek(pendingTime);
      refresh();
    });
    v.addEventListener('canplay', start);
    v.addEventListener('seeked', start);
    v.addEventListener('waiting', () => {
      if (wanted) {
        pauseAll();
        status.textContent = 'Buffering synchronized views…';
      }
    });
    v.addEventListener('error', () => {
      failed = true;
      wanted = false;
      pauseAll();
      status.textContent = 'A video could not be loaded. Reload the page to retry.';
      refresh();
    });
  });
  master.addEventListener('ended', () => seek(0, true));
  toggle.addEventListener('click', () => {
    wanted = !wanted;
    if (wanted) {
      if (master.ended) seek(0, true);
      else start();
    } else {
      pauseAll();
      status.textContent = 'Paused · All views share the same timeline';
    }
    refresh();
  });
  slider.addEventListener('input', () => seek(+slider.value));
  keys.forEach((key) => key.addEventListener('click', () => seek(+key.dataset.keyframeTime, true)));
  root.querySelector('[data-sync-fullscreen]').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (root.requestFullscreen) await root.requestFullscreen();
      else status.textContent = 'Fullscreen is unavailable in this browser.';
    } catch (_) { status.textContent = 'Fullscreen is unavailable in this browser.'; }
  });
  // Other standalone demos may pause this group, but never individual synchronized peers.
  document.querySelectorAll('video').forEach((v) => {
    if (root.contains(v)) return;
    v.addEventListener('play', () => { wanted = false; pauseAll(); refresh(); });
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pauseAll();
    else start();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
      else pauseAll();
    }, { threshold: 0.08 }).observe(root);
  } else { visible = true; start(); }
  setInterval(() => {
    if (wanted && visible && !document.hidden && !master.paused && !master.seeking) {
      followers.forEach((v) => {
        if (!v.seeking && Math.abs(v.currentTime - master.currentTime) > 0.16) v.currentTime = master.currentTime;
      });
    }
    refresh();
    if (videos.some((v) => v.paused)) start();
  }, 250);
  refresh();
})();
