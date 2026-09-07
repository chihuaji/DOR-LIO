/* DOR-LIO project page — minimal z-up orbit controls (rotate / pan / zoom),
 * mouse + touch, with inertial damping. No external dependencies. */
(function (global) {
  'use strict';

  class OrbitControlsZ {
    constructor(camera, domElement) {
      this.camera = camera;
      this.dom = domElement;
      this.target = new THREE.Vector3();
      this.minDistance = 0.5;
      this.maxDistance = 5000;
      this.autoRotate = true;
      this.autoRotateSpeed = 0.12; // radians per second
      this.enableDamping = true;
      this.dampingFactor = 0.12;

      // spherical state (z-up): azimuth theta, polar phi, radius r
      this._theta = 0.9;
      this._phi = 0.95;
      this._r = 100;
      this._vTheta = 0;
      this._vPhi = 0;
      this._pointerCache = new Map();
      this._animating = false;
      this._hasInteracted = false;
      this._pinchDist = 0;

      domElement.style.touchAction = 'none'; // we handle touch gestures
      domElement.addEventListener('contextmenu', (e) => e.preventDefault());
      domElement.addEventListener('pointerdown', (e) => this._onDown(e));
      domElement.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
      global.addEventListener('pointermove', (e) => this._onMove(e));
      global.addEventListener('pointerup', (e) => this._onUp(e));
      global.addEventListener('pointercancel', (e) => this._onUp(e));
    }

    get hasInteracted() { return this._hasInteracted; }

    _onDown(e) {
      this._pointerCache.set(e.pointerId, { x: e.clientX, y: e.clientY, button: e.button,
        shift: e.shiftKey || e.ctrlKey || e.metaKey });
      this._hasInteracted = true;
      this.autoRotate = false;
      try { this.dom.setPointerCapture(e.pointerId); } catch (err) { /* noop */ }
    }

    _onWheel(e) {
      e.preventDefault();
      this._hasInteracted = true;
      this.autoRotate = false;
      const scale = Math.exp(e.deltaY * 0.0012);
      this._r = Math.min(this.maxDistance, Math.max(this.minDistance, this._r * scale));
    }

    _onMove(e) {
      if (!this._pointerCache.has(e.pointerId)) return;
      const prev = this._pointerCache.get(e.pointerId);
      const dx = e.clientX - prev.x;
      const dy = e.clientY - prev.y;
      prev.x = e.clientX; prev.y = e.clientY;

      if (this._pointerCache.size === 1) {
        if (prev.button === 0 && !prev.shift) {
          const k = 2.2 / this.dom.clientHeight;
          this._vTheta -= dx * k * 0.28;
          this._vPhi -= dy * k * 0.28;
        } else {
          this._pan(dx, dy);
        }
      } else if (this._pointerCache.size === 2) {
        const pts = [...this._pointerCache.values()];
        const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
        if (this._pinchDist > 0) {
          const scale = this._pinchDist / Math.max(d, 1);
          this._r = Math.min(this.maxDistance, Math.max(this.minDistance, this._r * scale));
        }
        this._pinchDist = d;
        this._pan(dx * 0.5, dy * 0.5);
      }
    }

    _onUp(e) {
      this._pointerCache.delete(e.pointerId);
      this._pinchDist = 0;
    }

    _pan(dx, dy) {
      const cam = this.camera;
      const right = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 0);
      const up = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 1);
      const k = this._r * 1.6 / this.dom.clientHeight;
      this.target.addScaledVector(right, -dx * k).addScaledVector(up, dy * k);
    }

    fit(bboxCenter, bboxRadius) {
      this.target.copy(bboxCenter);
      const fov = this.camera.fov * Math.PI / 180;
      this._r = Math.max(bboxRadius / Math.tan(fov / 2) * 1.15, bboxRadius * 0.2, 1);
      this.minDistance = this._r * 0.02;
      this.maxDistance = this._r * 12;
    }

    setView(theta, phi) { this._theta = theta; this._phi = phi; }

    update(dt) {
      if (this.autoRotate) this._theta += this.autoRotateSpeed * dt;
      // apply momentum + damping
      this._theta += this._vTheta;
      this._phi += this._vPhi;
      if (this.enableDamping) { this._vTheta *= 0.82; this._vPhi *= 0.82; }
      else { this._vTheta = 0; this._vPhi = 0; }
      const lim = 0.03;
      this._phi = Math.min(Math.PI - lim, Math.max(lim, this._phi));

      const sp = Math.sin(this._phi);
      const eye = new THREE.Vector3(
        this.target.x + this._r * sp * Math.cos(this._theta),
        this.target.y + this._r * sp * Math.sin(this._theta),
        this.target.z + this._r * Math.cos(this._phi));
      this.camera.position.copy(eye);
      this.camera.lookAt(this.target);
    }
  }

  global.OrbitControlsZ = OrbitControlsZ;
})(window);
