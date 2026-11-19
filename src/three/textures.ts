import * as THREE from 'three';

/**
 * Procedural texture helpers: seeded value noise / fBm, canvas height maps,
 * and conversion of a height map into a tangent-space normal map.
 * Everything is generated at load time, so there are no image downloads.
 */

export function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Tileable 2D value noise on a `period` lattice. */
export function makeNoise2(seed = 1, period = 256) {
  const r = rng(seed);
  const table = new Float32Array(period * period);
  for (let i = 0; i < table.length; i++) table[i] = r();
  const at = (x: number, y: number) => table[((y % period) + period) % period * period + (((x % period) + period) % period)];
  const fade = (t: number) => t * t * (3 - 2 * t);
  return (x: number, y: number) => {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = fade(x - xi), yf = fade(y - yi);
    const a = at(xi, yi), b = at(xi + 1, yi), c = at(xi, yi + 1), d = at(xi + 1, yi + 1);
    return a + (b - a) * xf + (c - a) * yf + (a - b - c + d) * xf * yf;
  };
}

/** 3D value noise (not tileable), for displacing geometry. */
export function makeNoise3(seed = 1) {
  const r = rng(seed);
  const P = 256;
  const perm = new Uint8Array(P * 2);
  const vals = new Float32Array(P);
  for (let i = 0; i < P; i++) { perm[i] = i; vals[i] = r() * 2 - 1; }
  for (let i = P - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  for (let i = 0; i < P; i++) perm[i + P] = perm[i];
  const h = (x: number, y: number, z: number) => vals[perm[(perm[(perm[x & 255] + y) & 511] + z) & 511]];
  const fade = (t: number) => t * t * (3 - 2 * t);
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  return (x: number, y: number, z: number) => {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
    const u = fade(x - xi), v = fade(y - yi), w = fade(z - zi);
    return lerp(
      lerp(lerp(h(xi, yi, zi), h(xi + 1, yi, zi), u), lerp(h(xi, yi + 1, zi), h(xi + 1, yi + 1, zi), u), v),
      lerp(lerp(h(xi, yi, zi + 1), h(xi + 1, yi, zi + 1), u), lerp(h(xi, yi + 1, zi + 1), h(xi + 1, yi + 1, zi + 1), u), v),
      w,
    );
  };
}

export function fbm3(noise: (x: number, y: number, z: number) => number, x: number, y: number, z: number, oct = 4) {
  let a = 0.5, f = 1, s = 0;
  for (let i = 0; i < oct; i++) { s += a * noise(x * f, y * f, z * f); a *= 0.5; f *= 2.03; }
  return s;
}

/**
 * Grayscale fBm field, values 0..1, tileable. `scale` is the number of noise
 * cells across the texture for the first octave; each octave doubles it.
 */
export function fbmField(size: number, scale: number, octaves = 4, seed = 1): Float32Array {
  const r = rng(seed);
  const hashTable = new Float32Array(4096);
  for (let i = 0; i < hashTable.length; i++) hashTable[i] = r();
  const perm = new Uint16Array(4096);
  for (let i = 0; i < 4096; i++) perm[i] = i;
  for (let i = 4095; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
  const lat = (xi: number, yi: number, per: number) => {
    const x = ((xi % per) + per) % per, y = ((yi % per) + per) % per;
    return hashTable[perm[(perm[x & 4095] + y) & 4095]];
  };
  const fade = (t: number) => t * t * (3 - 2 * t);
  const out = new Float32Array(size * size);
  const base = Math.max(1, Math.round(scale));
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let a = 0.5, s = 0, norm = 0, per = base;
      for (let o = 0; o < octaves; o++) {
        const fx = (x / size) * per, fy = (y / size) * per;
        const xi = Math.floor(fx), yi = Math.floor(fy);
        const u = fade(fx - xi), v = fade(fy - yi);
        const n00 = lat(xi, yi, per), n10 = lat(xi + 1, yi, per), n01 = lat(xi, yi + 1, per), n11 = lat(xi + 1, yi + 1, per);
        s += a * (n00 + (n10 - n00) * u + (n01 - n00) * v + (n00 - n10 - n01 + n11) * u * v);
        norm += a;
        a *= 0.5;
        per *= 2;
      }
      out[y * size + x] = s / norm;
    }
  }
  return out;
}

export function fieldToTexture(field: Float32Array, w: number, h: number, map: (v: number) => [number, number, number], srgb = false): THREE.DataTexture {
  const data = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const [r, g, b] = map(field[i]);
    data[i * 4] = r; data[i * 4 + 1] = g; data[i * 4 + 2] = b; data[i * 4 + 3] = 255;
  }
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

/** Read a canvas into a 0..1 height field (red channel). */
export function canvasToField(c: HTMLCanvasElement): Float32Array {
  const g = c.getContext('2d')!;
  const d = g.getImageData(0, 0, c.width, c.height).data;
  const f = new Float32Array(c.width * c.height);
  for (let i = 0; i < f.length; i++) f[i] = d[i * 4] / 255;
  return f;
}

/** Sobel height → tangent-space normal map. `wrapX` for fields that tile horizontally. */
export function normalMapFromField(field: Float32Array, w: number, h: number, strength: number, wrapX = true): THREE.DataTexture {
  const data = new Uint8Array(w * h * 4);
  const at = (x: number, y: number) => {
    x = wrapX ? (x + w) % w : Math.min(w - 1, Math.max(0, x));
    y = Math.min(h - 1, Math.max(0, y));
    return field[y * w + x];
  };
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const dx = (at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x - 1, y) + at(x - 1, y + 1));
      const dy = (at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1));
      // Canvas y grows downward; texture v grows upward, hence +dy.
      let nx = -dx * strength, ny = dy * strength, nz = 1;
      const l = Math.hypot(nx, ny, nz);
      nx /= l; ny /= l; nz /= l;
      const i = (y * w + x) * 4;
      data[i] = (nx * 0.5 + 0.5) * 255;
      data[i + 1] = (ny * 0.5 + 0.5) * 255;
      data[i + 2] = (nz * 0.5 + 0.5) * 255;
      data[i + 3] = 255;
    }
  }
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat);
  t.wrapS = wrapX ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.ClampToEdgeWrapping;
  t.flipY = true; // match canvas orientation
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

export function canvasTexture(c: HTMLCanvasElement, srgb: boolean): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.wrapS = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}
