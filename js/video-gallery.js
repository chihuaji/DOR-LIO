/* A single player per gallery: switching scenes never leaves hidden videos playing. */
(function () {
  'use strict';
  document.querySelectorAll('[data-video-gallery]').forEach((gallery) => {
    const player = gallery.querySelector('video');
    const buttons = gallery.querySelectorAll('[data-src]');
    const error = gallery.querySelector('.video-error');
    buttons.forEach((button) => {
      button.setAttribute('aria-controls', player.id);
      button.addEventListener('click', () => {
        if (button.getAttribute('aria-pressed') === 'true') return;
        player.dispatchEvent(new Event('dor:beforechange'));
        player.pause();
        buttons.forEach((item) => {
          const selected = item === button;
          item.classList.toggle('is-active', selected);
          item.setAttribute('aria-pressed', String(selected));
        });
        error.hidden = true;
        player.poster = button.dataset.poster;
        player.src = button.dataset.src;
        player.setAttribute('aria-label', button.dataset.title + ' comparison video');
        gallery.querySelector('[data-video-title]').textContent = button.dataset.title;
        gallery.querySelector('[data-video-description]').textContent = button.dataset.description;
        gallery.querySelector('[data-video-download]').href = button.dataset.src;
        player.load();
        player.dispatchEvent(new Event('dor:sourcechange'));
      });
    });
    player.addEventListener('error', () => { error.hidden = false; });
  });
  // Standalone videos autoplay independently; multi-view groups have shared user controls.
  document.querySelectorAll('video').forEach((player) => {
    if (player.closest('[data-sync-player], [data-benchmark-player]')) return;
    let visible = false, userPaused = false, suppressPauseUntil = 0;
    player.muted = true;
    player.defaultMuted = true;
    player.loop = true;
    player.playsInline = true;
    player.autoplay = false; // IntersectionObserver starts it when visible.
    function play() {
      if (!visible || userPaused || document.hidden) return;
      player.preload = 'auto';
      player.play().catch(() => {}); // Native controls remain available if autoplay is blocked.
    }
    function pause() {
      suppressPauseUntil = performance.now() + 300;
      player.pause();
    }
    player.addEventListener('pause', () => {
      if (visible && !document.hidden && performance.now() > suppressPauseUntil) userPaused = true;
    });
    player.addEventListener('play', () => { userPaused = false; });
    player.addEventListener('dor:beforechange', () => { userPaused = false; suppressPauseUntil = performance.now() + 500; });
    player.addEventListener('dor:sourcechange', play);
    document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); else play(); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        if (visible) play(); else pause();
      }, { threshold: .1 }).observe(player);
    } else { visible = true; play(); }
  });
})();
