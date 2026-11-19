import * as THREE from 'three';
import { fbmField, rng } from './textures';

/**
 * The room the globe sits in: a dark, out-of-focus backdrop (forest
 * silhouettes and warm bokeh, like a photo shot at f/1.8) and a varnished
 * walnut tabletop. Both are procedural.
 */

/**
 * Plain warm sketch paper: a quiet 2D backdrop so the globe stands out.
 * Fibre noise, a faint tooth and a soft vignette; no imagery. Call
 * `fit(aspect)` on resize so it covers the screen without stretching.
 */
export function paperBackdrop(): { texture: THREE.CanvasTexture; fit(aspect: number): void } {
  const W = 2048, H = 1280;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d')!;
  const r = rng(77);
  g.fillStyle = '#f3ede2';
  g.fillRect(0, 0, W, H);
  // Large soft mottling.
  const low = fbmField(256, 4, 4, 81);
  const tooth = fbmField(512, 160, 2, 82);
  const img = g.getImageData(0, 0, W, H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      const m = low[((y >> 3) % 256) * 256 + ((x >> 3) % 256)] - 0.5;
      const t = tooth[(y % 512) * 512 + (x % 512)] - 0.5;
      const v = m * 10 + t * 9;
      img.data[i] += v; img.data[i + 1] += v; img.data[i + 2] += v * 0.9;
    }
  }
  g.putImageData(img, 0, 0);
  // Fibres: a few thousand faint short strokes.
  g.lineCap = 'round';
  for (let k = 0; k < 2600; k++) {
    const x = r() * W, y = r() * H, a = r() * Math.PI, l = 4 + r() * 14;
    g.strokeStyle = r() < 0.5 ? `rgba(120,105,85,${0.04 + r() * 0.05})` : `rgba(255,252,245,${0.08 + r() * 0.08})`;
    g.lineWidth = 0.6 + r() * 0.6;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l);
    g.stroke();
  }
  // Soft vignette and a gentle light pool behind the globe.
  const v = g.createRadialGradient(W / 2, H * 0.45, H * 0.2, W / 2, H * 0.5, W * 0.62);
  v.addColorStop(0, 'rgba(255,250,240,0.25)');
  v.addColorStop(1, 'rgba(90,70,50,0.22)');
  g.fillStyle = v;
  g.fillRect(0, 0, W, H);

  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  const texAspect = W / H;
  return {
    texture,
    fit(aspect: number) {
      if (aspect > texAspect) {
        const s = texAspect / aspect;
        texture.repeat.set(1, s);
        texture.offset.set(0, (1 - s) / 2);
      } else {
        const s = aspect / texAspect;
        texture.repeat.set(s, 1);
        texture.offset.set((1 - s) / 2, 0);
      }
    },
  };
}

/** Invisible ground that only shows the globe's soft shadow on the paper. */
export function shadowCatcher(): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.CircleGeometry(12, 64), new THREE.ShadowMaterial({ color: '#3a2a1c', opacity: 0.32 }));
  m.rotation.x = -Math.PI / 2;
  m.receiveShadow = true;
  return m;
}

/** Soft contact shadow blob right under the base. */
export function contactBlob(size: number, opacity: number): THREE.Mesh {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, 'rgba(40,28,18,0.85)');
  gr.addColorStop(0.5, 'rgba(40,28,18,0.35)');
  gr.addColorStop(1, 'rgba(40,28,18,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 256, 256);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, opacity, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.002;
  return m;
}

/** Walnut planks: grain along x, a varnish clearcoat, slight wear. */
export function walnutTable(): THREE.Mesh {
  const S = 1024;
  const n1 = fbmField(S, 6, 5, 91);
  const n2 = fbmField(S, 16, 3, 92);
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d')!;
  const img = g.createImageData(S, S);
  const height = new Float32Array(S * S);
  const planks = 4;
  for (let y = 0; y < S; y++) {
    const plank = Math.floor((y / S) * planks);
    const py = ((y / S) * planks) % 1;
    for (let x = 0; x < S; x++) {
      const i = y * S + x;
      const warp = n1[i] * 3 + plank * 1.7;
      const ring = Math.abs(Math.sin((py * 9 + warp) * Math.PI));
      const grain = Math.pow(ring, 0.7) * 0.7 + n2[i] * 0.3;
      const seam = py < 0.006 || py > 0.994 ? 0.45 : 1;
      const tone = (0.5 + grain * 0.5) * seam * (0.85 + ((plank * 37) % 5) * 0.05);
      img.data[i * 4] = 58 * tone;
      img.data[i * 4 + 1] = 34 * tone;
      img.data[i * 4 + 2] = 21 * tone;
      img.data[i * 4 + 3] = 255;
      height[i] = grain * seam;
    }
  }
  g.putImageData(img, 0, 0);
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.repeat.set(2, 2);
  map.anisotropy = 8;
  void height;
  const mat = new THREE.MeshPhysicalMaterial({
    map,
    roughness: 0.5,
    clearcoat: 0.55,
    clearcoatRoughness: 0.22,
    envMapIntensity: 0.8,
  });
  const table = new THREE.Mesh(new THREE.CircleGeometry(16, 96), mat);
  table.rotation.x = -Math.PI / 2;
  table.receiveShadow = true;
  return table;
}
