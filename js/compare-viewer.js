/* DOR-LIO project page — before/after wipe comparison viewer.
 * One scene, two point clouds (raw | clean). The vertical handle splits the
 * viewport in screen space via two scissored render passes, so the split stays
 * vertical no matter how the camera is orbited. */
(function (global) {
  'use strict';

  const BG_DARK = 0x0b0f14;

  class CompareViewer {
    constructor(container, options) {
      this.container = container;
      this.opts = Object.assign({ pointSize: 1.6, leftLabel: 'Raw', rightLabel: 'DOR-LIO (Ours)' }, options);
      this._clock = new THREE.Clock();
      this._split = 0.5; // fraction of width

      container.classList.add('compare-viewer');
      container.innerHTML =
        '<div class="cmp-wrap">' +
        '  <div class="cmp-hint">Drag the ⟷ handle to wipe · Drag elsewhere to orbit</div>' +
        '  <span class="cmp-label cmp-label-left">' + this.opts.leftLabel + '</span>' +
        '  <span class="cmp-label cmp-label-right">' + this.opts.rightLabel + '</span>' +
        '  <div class="cmp-legend"><i class="cmp-dot cmp-dot-red"></i> dynamic artifacts</div>' +
        '  <div class="cmp-loading"><div class="cmp-loading-bar"><i></i></div><span class="cmp-loading-text">Loading maps…</span></div>' +
        '  <div class="cmp-handle" role="slider" aria-label="comparison wipe" aria-valuemin="0" aria-valuemax="100" tabindex="0">' +
        '    <div class="cmp-handle-line"></div>' +
        '    <div class="cmp-handle-grip">' +
        '      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
        '        <path d="M9.5 7 5 12l4.5 5M14.5 7l4.5 5-4.5 5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>' +
        '      </svg>' +
        '    </div>' +
        '  </div>' +
        '</div>';

      this._wrap = container.querySelector('.cmp-wrap');
      this._handle = container.querySelector('.cmp-handle');
      this._loading = container.querySelector('.cmp-loading');
      this._loadingBar = container.querySelector('.cmp-loading-bar i');
      this._loadingText = container.querySelector('.cmp-loading-text');
      this._leftLabel = container.querySelector('.cmp-label-left');
      this._rightLabel = container.querySelector('.cmp-label-right');
      this._raw = null;
      this._clean = null;
      this._home = null;

      this._renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
      this._renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this._renderer.setClearColor(BG_DARK, 1);
      this._renderer.autoClear = true;
      this._wrap.insertBefore(this._renderer.domElement, this._handle);

      this._scene = new THREE.Scene();
      this._camera = new THREE.PerspectiveCamera(55, 1, 0.1, 20000);
      this._camera.up.set(0, 0, 1);
      this._controls = new OrbitControlsZ(this._camera, this._renderer.domElement);
      if (this.opts.preserveView) this._controls.autoRotate = false;

      // handle interactions
      const handleEl = this._handle;
      handleEl.addEventListener('pointerdown', (e) => {
        e.stopPropagation();
        handleEl.setPointerCapture(e.pointerId);
        this._draggingHandle = true;
        this._moveSplit(e);
      });
      handleEl.addEventListener('pointermove', (e) => {
        if (this._draggingHandle) this._moveSplit(e);
      });
      handleEl.addEventListener('pointerup', () => { this._draggingHandle = false; });
      handleEl.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') { this._setSplit(this._split - 0.03); e.preventDefault(); }
        if (e.key === 'ArrowRight') { this._setSplit(this._split + 0.03); e.preventDefault(); }
      });

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

    setLabels(left, right) {
      this._leftLabel.textContent = left;
      this._rightLabel.textContent = right;
    }

    setLegend(text) {
      this.container.querySelector('.cmp-legend').textContent = text;
    }

    _setSplit(v) { this._split = Math.min(0.98, Math.max(0.02, v)); }

    _moveSplit(e) {
      const rect = this._wrap.getBoundingClientRect();
      this._setSplit((e.clientX - rect.left) / rect.width);
    }

    async loadPair(rawUrl, cleanUrl) {
      if (this._request) this._request.abort();
      const request = this._request = new AbortController();
      this._loading.style.display = 'flex';
      this._loadingText.textContent = 'Loading comparison…';
      this._loadingBar.style.background = '';
      this._loadingBar.style.width = '4%';
      for (const p of [this._raw, this._clean]) {
        if (p) { this._scene.remove(p); p.geometry.dispose(); p.material.dispose(); }
      }
      this._raw = this._clean = null;
      try {
        const loadOne = async (url, tag) => {
          const buf = await DORPLY.fetchPLY(url, (d, t) => {
            if (request !== this._request) return;
            const pct = t ? Math.round(d / t * 100) : 0;
            this._loadingText.textContent = `Loading ${tag}… ${pct}%`;
            this._loadingBar.style.width = Math.max(pct, 4) + '%';
          }, { signal: request.signal });
          if (request.signal.aborted) return null;
          return DORPLY.parsePLY(buf);
        };
        const [raw, clean] = await Promise.all([
          loadOne(rawUrl, 'left map'), loadOne(cleanUrl, 'right map')
        ]);
        if (request !== this._request || request.signal.aborted) return;
        const mk = (geo) => {
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.BufferAttribute(geo.positions, 3));
          g.setAttribute('color', new THREE.BufferAttribute(geo.colors, 3));
          const m = new THREE.PointsMaterial({ size: this.opts.pointSize, vertexColors: true, sizeAttenuation: false });
          return new THREE.Points(g, m);
        };
        for (const p of [this._raw, this._clean]) {
          if (p) { this._scene.remove(p); p.geometry.dispose(); p.material.dispose(); }
        }
        this._raw = mk(raw); this._clean = mk(clean);
        this._scene.add(this._raw); this._scene.add(this._clean);

        const reference = this.opts.reference === 'left' ? this._raw : this._clean;
        reference.geometry.computeBoundingBox();
        const bb = reference.geometry.boundingBox;
        const center = bb.getCenter(new THREE.Vector3());
        const radius = bb.getSize(new THREE.Vector3()).length() / 2;
        if (!this.opts.preserveView || !this._home) {
          this._controls.fit(center, radius * (this.opts.fitScale || 1));
          if (this.opts.initialView) this._controls.setView(...this.opts.initialView);
        }
        this._home = { center: center.clone(), radius };
      } catch (err) {
        if (request !== this._request || request.signal.aborted) return;
        request.abort();
        this._loadingText.textContent = 'Failed to load: ' + err.message;
        this._loadingBar.style.background = '#e5503a';
        console.error(err);
        return;
      }
      this._loading.style.display = 'none';
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

      const canvas = this._renderer.domElement;
      const w = canvas.clientWidth || 1, h = canvas.clientHeight || 1;
      const splitPx = Math.round(w * this._split);
      this._handle.style.left = (this._split * 100) + '%';
      this._handle.setAttribute('aria-valuenow', Math.round(this._split * 100));

      if (!this._raw || !this._clean) {
        this._renderer.setScissorTest(false);
        this._renderer.setViewport(0, 0, w, h);
        this._renderer.render(this._scene, this._camera);
        return;
      }
      this._renderer.setScissorTest(true);
      // left pass — raw map
      this._raw.visible = true;
      this._clean.visible = false;
      this._renderer.setScissor(0, 0, splitPx, h);
      this._renderer.setViewport(0, 0, w, h);
      this._renderer.render(this._scene, this._camera);
      // right pass — clean static map
      this._raw.visible = false;
      this._clean.visible = true;
      this._renderer.setScissor(splitPx, 0, w - splitPx, h);
      this._renderer.setViewport(0, 0, w, h);
      this._renderer.render(this._scene, this._camera);
      this._renderer.setScissorTest(false);
    }
  }

  global.CompareViewer = CompareViewer;
})(window);
