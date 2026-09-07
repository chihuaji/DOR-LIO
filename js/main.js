/* DOR-LIO project page — page bootstrap: builds the two interactive viewers
 * from the scene registry (js/scenes.js). */
(function () {
  'use strict';

  function buildTabs(tabsEl, scenes, onPick) {
    scenes.forEach((s, i) => {
      const b = document.createElement('button');
      b.className = 'tab' + (i === 0 ? ' is-active' : '');
      b.textContent = s.title;
      b.addEventListener('click', () => {
        tabsEl.querySelectorAll('.tab').forEach((t) => t.classList.remove('is-active'));
        b.classList.add('is-active');
        onPick(s);
      });
      tabsEl.appendChild(b);
    });
  }

  // ---------------- Point Cloud Explorer ----------------
  const explorerMount = document.getElementById('explorer-viewer');
  if (explorerMount && window.CloudViewer) {
    const viewer = new CloudViewer(explorerMount, { pointSize: 1.6 });
    const scenes = (window.DOR_SCENES && window.DOR_SCENES.explorer) || [];
    const note = document.getElementById('explorer-note');
    const load = (s) => {
      if (note) note.textContent = s.note || '';
      viewer.load(s.file, { badges: s.badges });
    };
    buildTabs(document.getElementById('explorer-tabs'), scenes, load);
    if (scenes.length) load(scenes[0]);
  }

  // ---------------- Before/After compare ----------------
  const compareMount = document.getElementById('compare-viewer');
  if (compareMount && window.CompareViewer) {
    const cmp = new CompareViewer(compareMount, { pointSize: 1.6 });
    const scenes = (window.DOR_SCENES && window.DOR_SCENES.compare) || [];
    const note = document.getElementById('compare-note');
    let started = false;
    const load = (s) => {
      if (note) note.textContent = s.note || '';
      cmp.setLabels(s.leftLabel, s.rightLabel);
      cmp.loadPair(s.raw, s.clean);
    };
    buildTabs(document.getElementById('compare-tabs'), scenes, load);
    // 14 MB per pair — start loading when the section approaches the viewport
    const start = () => {
      if (started || !scenes.length) return;
      started = true;
      load(scenes[0]);
    };
    if ('IntersectionObserver' in window) {
      new IntersectionObserver((entries, obs) => {
        if (entries.some((e) => e.isIntersecting)) { start(); obs.disconnect(); }
      }, { rootMargin: '600px' }).observe(compareMount);
    } else {
      start();
    }
  }

  // ---------------- Misc page chrome ----------------
  const copyBtn = document.getElementById('bibtex-copy');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const code = document.querySelector('.bibtex code').innerText;
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.textContent = 'Copied ✓';
        setTimeout(() => { copyBtn.textContent = 'Copy BibTeX'; }, 1600);
      } catch (e) {
        copyBtn.textContent = 'Select & copy manually';
      }
    });
  }

  // sticky nav shadow after scrolling past hero
  const nav = document.getElementById('nav');
  const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 40);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
