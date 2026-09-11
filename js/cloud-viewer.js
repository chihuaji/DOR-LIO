/* DOR-LIO project page — interactive point cloud viewer.
 * Drag to orbit, scroll/pinch to zoom, right-drag or two-finger to pan. */
(function (global) {
  'use strict';

  const BG_DARK = 0x0b0f14;

  class CloudViewer {
    constructor(container, options) {
      this.container = container;
      this.opts = Object.assign({ pointSize: 1.6, heightRamp: null }, options);
      this._clock = new THREE.Clock();

      container.classList.add('cloud-viewer');
      container.innerHTML =
        '<div class="cv-canvas-wrap">' +
        '  <div class="cv-hint">Drag to orbit · Scroll to zoom · Right-drag to pan</div>' +
        '  <div class="cv-badges"></div>' +
        '  <div class="cv-loading"><div class="cv-loading-bar"><i></i></div><span class="cv-loading-text">Loading map…</span></div>' +
        '</div>' +
        '<div class="cv-toolbar">' +
        '  <div class="cv-stat"></div>' +
        '  <div class="cv-controls">' +
        '    <label>Size <input type="range" class="cv-size" min="0.5" max="4" step="0.1" value="' + this.opts.pointSize + '"></label>' +
        '    <button class="cv-reset" title="Reset view">Reset</button>' +
        '    <button class="cv-spin" title="Toggle auto-rotate">Spin</button>' +
        '  </div>' +
        '</div>';

      this._wrap = container.querySelector('.cv-canvas-wrap');
      this._badges = container.querySelector('.cv-badges');
      this._loading = container.querySelector('.cv-loading');
      this._loadingBar = container.querySelector('.cv-loading-bar i');
      this._loadingText = container.querySelector('.cv-loading-text');
      this._stat = container.querySelector('.cv-stat');
      this._points = null;
      this._home = null;

      this._renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
      this._renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this._renderer.setClearColor(BG_DARK, 1);
      this._wrap.appendChild(this._renderer.domElement);

      this._scene = new THREE.Scene();
      this._scene.fog = new THREE.FogExp2(BG_DARK, 0.0);
      this._camera = new THREE.PerspectiveCamera(55, 1, 0.1, 20000);
      this._camera.up.set(0, 0, 1);
      this._controls = new OrbitControlsZ(this._camera, this._renderer.domElement);

      // subtle ground grid
      this._grid = null;

      container.querySelector('.cv-size').addEventListener('input', (e) => {
        if (this._points) this._points.material.size = parseFloat(e.target.value);
      });
      container.querySelector('.cv-reset').addEventListener('click', () => this._resetView());
      const spinBtn = container.querySelector('.cv-spin');
      spinBtn.addEventListener('click', () => {
        this._controls.autoRotate = !this._controls.autoRotate;
        spinBtn.classList.toggle('is-active', this._controls.autoRotate);
      });
      spinBtn.classList.add('is-active');

      this._inView = !('IntersectionObserver' in window);
      if ('IntersectionObserver' in window) {
        this._visibilityObserver = new IntersectionObserver(([entry]) => {
          this._inView = entry.isIntersecting;
        });
        this._visibilityObserver.observe(container);
      }
      this._lastRender = 0;
      this._resizeObserver = new ResizeObserver(() => this._resize());
      this._resizeObserver.observe(this._wrap);
      this._resize();
      this._animate = this._animate.bind(this);
      requestAnimationFrame(this._animate);
    }

    setBadges(list) {
      this._badges.innerHTML = (list || []).map((b) => `<span class="cv-badge">${b}</span>`).join('');
    }

    async load(url, meta) {
      this._loading.style.display = 'flex';
      this._loadingBar.style.width = '4%';
      try {
        const buf = await DORPLY.fetchPLY(url, (done, total) => {
          const pct = total ? Math.round(done / total * 100) : 0;
          this._loadingBar.style.width = Math.max(pct, 4) + '%';
          if (total) this._loadingText.textContent = `Loading map… ${pct}%`;
        });
        const geo = DORPLY.parsePLY(buf);
        if (this._points) {
          this._scene.remove(this._points);
          this._points.geometry.dispose();
          this._points.material.dispose();
        }
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(geo.positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(geo.colors, 3));
        const material = new THREE.PointsMaterial({
          size: this.opts.pointSize, vertexColors: true, sizeAttenuation: false,
        });
        this._points = new THREE.Points(geometry, material);
        this._scene.add(this._points);

        geometry.computeBoundingBox();
        const bb = geometry.boundingBox;
        const center = bb.getCenter(new THREE.Vector3());
        const radius = bb.getSize(new THREE.Vector3()).length() / 2;
        this._controls.fit(center, radius);
        this._home = { center: center.clone(), radius };
        this._controls.autoRotate = !this._controls.hasInteracted;
        this._stat.textContent = `${(geo.count / 1e6).toFixed(2)} M points`;
        if (meta && meta.badges) this.setBadges(meta.badges);
      } catch (err) {
        this._loadingText.textContent = 'Failed to load: ' + err.message;
        this._loadingBar.style.background = '#e5503a';
        console.error(err);
        return;
      }
      this._loading.style.display = 'none';
    }

    _resetView() {
      if (!this._home) return;
      this._controls.fit(this._home.center, this._home.radius);
      this._controls.setView(0.9, 0.95);
    }

    _resize() {
      const w = this._wrap.clientWidth || 1;
      const h = this._wrap.clientHeight || 1;
      this._renderer.setSize(w, h, false);
      this._camera.aspect = w / h;
      this._camera.updateProjectionMatrix();
    }

    _animate() {
      requestAnimationFrame(this._animate);
      if (!this._inView || document.hidden) return;
      const now = performance.now();
      if (now - this._lastRender < 1000 / 30) return;
      this._lastRender = now;
      const dt = Math.min(this._clock.getDelta(), 0.1);
      this._controls.update(dt);
      this._renderer.render(this._scene, this._camera);
    }
  }

  global.CloudViewer = CloudViewer;
})(window);
