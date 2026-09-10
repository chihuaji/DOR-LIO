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
      });
    });
    player.addEventListener('error', () => { error.hidden = false; });
  });
  // Keep audio and playback focused on the video the visitor chooses.
  const players = document.querySelectorAll('video');
  players.forEach((player) => player.addEventListener('play', () => {
    const group = player.closest('[data-sync-player]');
    players.forEach((other) => {
      if (other !== player && !(group && group.contains(other))) other.pause();
    });
  }));
})();
