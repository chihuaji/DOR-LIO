/* DOR-LIO project page — binary PLY loader for LiDAR maps.
 * Supports little-endian binary PLY with float x/y/z (+ uchar rgb).
 * Missing colors are replaced by a height (turbo) ramp. */
(function (global) {
  'use strict';

  const HEADER_STATE = { MAGIC: 0, BODY: 1 };

  async function fetchPLY(url, onProgress, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
    const total = Number(res.headers.get('Content-Length')) || 0;
    if (!res.body || !window.ReadableStream) return new Uint8Array(await res.arrayBuffer());
    const reader = res.body.getReader();
    const chunks = [];
    let received = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.length;
      if (onProgress) onProgress(received, total);
    }
    const buf = new Uint8Array(received);
    let off = 0;
    for (const c of chunks) { buf.set(c, off); off += c.length; }
    return buf;
  }

  function parsePLY(buf) {
    // find end of header
    const text = new TextDecoder('ascii').decode(buf.subarray(0, Math.min(buf.length, 65536)));
    const headerEnd = text.indexOf('end_header');
    if (headerEnd < 0) throw new Error('not a PLY file (end_header missing)');
    const headerText = text.slice(0, headerEnd);
    // header is ASCII, so the decoded char offset equals the byte offset.
    // data starts right after the newline that follows 'end_header'.
    let j = headerEnd + 'end_header'.length;
    while (j < buf.length && buf[j] !== 10) j++;
    if (j >= buf.length) throw new Error('PLY header terminator not found');
    const dataStart = j + 1;

    let nVertices = 0, fmt = '';
    const props = [];
    for (const line of headerText.split(/\r?\n/)) {
      const t = line.trim().split(/\s+/);
      if (t[0] === 'format') fmt = t[1];
      else if (t[0] === 'element' && t[1] === 'vertex') nVertices = parseInt(t[2], 10);
      else if (t[0] === 'property' && t[2]) props.push({ type: t[1], name: t[2] });
    }
    if (fmt !== 'binary_little_endian') throw new Error(`unsupported PLY format: ${fmt}`);

    const TYPE = { float: 4, uchar: 1, char: 1, ushort: 2, short: 2, uint: 4, int: 4, double: 8 };
    let stride = 0;
    const offsets = {};
    for (const p of props) { offsets[p.name] = stride; stride += TYPE[p.type]; }

    const positions = new Float32Array(nVertices * 3);
    const colors = new Float32Array(nVertices * 3);
    const dv = new DataView(buf.buffer, buf.byteOffset + dataStart);
    const o = offsets, hasRGB = offsets.red !== undefined;

    let zmin = Infinity, zmax = -Infinity;
    for (let i = 0; i < nVertices; i++) {
      const base = i * stride;
      const x = dv.getFloat32(base + o.x, true);
      const y = dv.getFloat32(base + o.y, true);
      const z = dv.getFloat32(base + o.z, true);
      positions[3 * i] = x; positions[3 * i + 1] = y; positions[3 * i + 2] = z;
      if (z < zmin) zmin = z; if (z > zmax) zmax = z;
      if (hasRGB) {
        colors[3 * i] = dv.getUint8(base + o.red) / 255;
        colors[3 * i + 1] = dv.getUint8(base + o.green) / 255;
        colors[3 * i + 2] = dv.getUint8(base + o.blue) / 255;
      }
    }
    if (!hasRGB) {
      // height ramp fallback
      const zr = Math.max(zmax - zmin, 1e-6);
      for (let i = 0; i < nVertices; i++) {
        const t = (positions[3 * i + 2] - zmin) / zr;
        const c = turbo(t);
        colors[3 * i] = c[0]; colors[3 * i + 1] = c[1]; colors[3 * i + 2] = c[2];
      }
    }
    return { positions, colors, count: nVertices };
  }

  function turbo(t) {
    t = Math.min(1, Math.max(0, t));
    const r = 0.13572138 + t * (4.61539260 + t * (-42.66032258 + t * (132.13108234 + t * (-152.94239396 + t * 59.28637943))));
    const g = 0.09140261 + t * (2.19418839 + t * (4.84296658 + t * (-14.18503333 + t * (4.27729857 + t * 2.82956604))));
    const b = 0.10667330 + t * (12.64187808 + t * (-60.58204836 + t * (110.36276771 + t * (-89.90310912 + t * 27.34824973))));
    return [Math.min(Math.max(r, 0), 1), Math.min(Math.max(g, 0), 1), Math.min(Math.max(b, 0), 1)];
  }

  global.DORPLY = { fetchPLY, parsePLY, turbo, HEADER_STATE };
})(window);
