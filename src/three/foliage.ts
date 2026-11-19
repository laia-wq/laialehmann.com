import * as THREE from 'three';
import { rng } from './textures';

/**
 * Alpha-tested foliage cards, the standard real-time technique for trees:
 * a texture of a twig with needles (or a cluster of leaves) on a bent quad,
 * instanced many times. The textures are painted procedurally on a canvas.
 */

function canvas(w: number, h: number) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')!] as const;
}

function toTexture(c: HTMLCanvasElement) {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  t.generateMipmaps = true;
  return t;
}

/** A conifer twig seen from above: a woody axis with dense needles angled forward. */
export function needleTexture(): THREE.CanvasTexture {
  const W = 512, H = 192;
  const [c, g] = canvas(W, H);
  const r = rng(13);
  const mid = H / 2;
  g.lineCap = 'round';
  // Side shoots first, so the main axis sits on top.
  const shoot = (x0: number, y0: number, dirY: number, len: number) => {
    const steps = Math.floor(len / 3);
    for (let i = 0; i < steps; i++) {
      const t = i / steps;
      const x = x0 + t * len * 0.8;
      const y = y0 + dirY * t * len * 0.55;
      const nl = 18 * (1 - t * 0.5);
      for (const s of [-1, 1]) {
        const a = (s * 0.9 + (r() - 0.5) * 0.35) + Math.atan2(dirY * 0.55, 0.8);
        const shade = 0.55 + t * 0.45 + (r() - 0.5) * 0.2;
        g.strokeStyle = `rgb(${30 * shade + 10},${70 * shade + 20},${40 * shade + 12})`;
        g.lineWidth = 2.2;
        g.beginPath();
        g.moveTo(x, y);
        g.lineTo(x + Math.cos(a) * nl * 0.6 + nl * 0.4, y + Math.sin(a) * nl);
        g.stroke();
      }
    }
  };
  for (let k = 0; k < 9; k++) {
    const x = 30 + k * 50 + r() * 15;
    shoot(x, mid, -1, 140 - k * 12);
    shoot(x + 20, mid, 1, 140 - k * 12);
  }
  // Main axis needles.
  for (let x = 8; x < W - 8; x += 3) {
    const t = x / W;
    for (const s of [-1, 1]) {
      const a = s * (0.7 + (r() - 0.5) * 0.3);
      const nl = 22 * (1 - t * 0.4);
      const shade = 0.6 + t * 0.5;
      g.strokeStyle = `rgb(${34 * shade + 10},${80 * shade + 20},${44 * shade + 12})`;
      g.lineWidth = 2.6;
      g.beginPath();
      g.moveTo(x, mid);
      g.lineTo(x + Math.cos(a) * nl * 0.5 + nl * 0.5, mid + Math.sin(a) * nl);
      g.stroke();
    }
  }
  g.strokeStyle = '#4a3422';
  g.lineWidth = 4;
  g.beginPath();
  g.moveTo(0, mid);
  g.lineTo(W * 0.92, mid);
  g.stroke();
  return toTexture(c);
}

/** A leafy twig: several ovate leaves with midribs in slightly varied greens. */
export function leafClusterTexture(hues: string[]): THREE.CanvasTexture {
  const W = 256, H = 256;
  const [c, g] = canvas(W, H);
  const r = rng(29);
  g.strokeStyle = '#4b3726';
  g.lineWidth = 3;
  g.beginPath();
  g.moveTo(10, H - 10);
  g.quadraticCurveTo(W * 0.4, H * 0.55, W * 0.72, H * 0.28);
  g.stroke();
  for (let i = 0; i < 11; i++) {
    const t = 0.15 + (i / 11) * 0.85;
    const bx = 10 + (W * 0.72 - 10) * t, by = H - 10 - (H - 10 - H * 0.28) * t;
    const ang = -Math.PI / 4 + (i % 2 ? 1 : -1) * (0.9 + r() * 0.4);
    const len = 52 + r() * 26, wid = len * 0.42;
    g.save();
    g.translate(bx, by);
    g.rotate(ang);
    const col = hues[Math.floor(r() * hues.length)];
    const grd = g.createLinearGradient(0, -wid, 0, wid);
    grd.addColorStop(0, col);
    grd.addColorStop(1, shade(col, 0.7));
    g.fillStyle = grd;
    g.beginPath();
    g.moveTo(0, 0);
    g.bezierCurveTo(len * 0.3, -wid, len * 0.75, -wid * 0.6, len, 0);
    g.bezierCurveTo(len * 0.75, wid * 0.6, len * 0.3, wid, 0, 0);
    g.fill();
    g.strokeStyle = shade(col, 1.25);
    g.lineWidth = 1.2;
    g.beginPath();
    g.moveTo(2, 0);
    g.lineTo(len * 0.92, 0);
    g.stroke();
    g.restore();
  }
  return toTexture(c);
}

function shade(hex: string, k: number) {
  const c = new THREE.Color(hex).multiplyScalar(k);
  return `#${c.getHexString()}`;
}

/**
 * A card bent downward along its length (droop), with a second card crossed
 * at an angle so it has volume from any view. Card spans x 0..1.
 */
export function droopCard(droop: number, width: number): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  for (const roll of [0, 1.1]) {
    const seg = 6;
    const pos: number[] = [], uv: number[] = [], idx: number[] = [];
    for (let i = 0; i <= seg; i++) {
      const t = i / seg;
      const y = -droop * t * t;
      for (const s of [-1, 1]) {
        const lz = s * width * 0.5 * (1 - t * 0.35);
        pos.push(t, y + Math.sin(roll) * lz, Math.cos(roll) * lz);
        uv.push(t, s < 0 ? 0 : 1);
      }
      if (i > 0) { const a = (i - 1) * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    parts.push(g.toNonIndexed());
  }
  const pos = new Float32Array(parts.reduce((n, g) => n + g.getAttribute('position').array.length, 0));
  const uv = new Float32Array(parts.reduce((n, g) => n + g.getAttribute('uv').array.length, 0));
  let o = 0, u = 0;
  for (const g of parts) {
    pos.set(g.getAttribute('position').array as Float32Array, o); o += g.getAttribute('position').array.length;
    uv.set(g.getAttribute('uv').array as Float32Array, u); u += g.getAttribute('uv').array.length;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  // Foliage lighting reads best with normals bent toward "up/out" rather than the card's own.
  const n = new Float32Array(pos.length);
  for (let i = 0; i < pos.length; i += 3) { n[i] = 0.25; n[i + 1] = 0.95; n[i + 2] = 0; }
  out.setAttribute('normal', new THREE.BufferAttribute(n, 3));
  return out;
}

/** Shared material for foliage cards with alpha test and gentle wind. */
export function cardMaterial(map: THREE.Texture, uTime: { value: number }, wind = 0.05): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ map, alphaTest: 0.45, side: THREE.DoubleSide, roughness: 0.7 });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = uTime;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;').replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
       vec4 ip = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
       transformed.y += sin(uTime * 1.1 + ip.x * 23.0 + ip.z * 17.0) * ${wind.toFixed(3)} * position.x * position.x;`,
    );
  };
  return m;
}
