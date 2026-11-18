import * as THREE from 'three';
import { canvasToField, fbmField, fieldToTexture, makeNoise3, normalMapFromField, rng } from './textures';

/**
 * Turned bronze pedestal in the spirit of an antique crystal-ball stand:
 * a wide fluted foot with a polished marble disc, a baluster stem with a
 * beaded knop, and a gadrooned cup that holds the sphere. The ornament is
 * real geometry (the radius is modulated around the axis), so it catches
 * light and casts shadow; crevices get a darker patina via vertex colour.
 */

export interface Band {
  y0: number;
  y1: number;
  lobes: number;
  amp: number; // fraction of the radius
  shape: 'flute' | 'bead';
}

/** Surface of revolution with angular ornament. Profile runs bottom → top as [radius, y]. */
export function revolve(profile: [number, number][], segments: number, bands: Band[], seed = 3): THREE.BufferGeometry {
  // Resample the profile so ornament bands get enough rows.
  const pts: [number, number][] = [];
  for (let i = 0; i < profile.length - 1; i++) {
    const [r0, y0] = profile[i], [r1, y1] = profile[i + 1];
    const len = Math.hypot(r1 - r0, y1 - y0);
    const steps = Math.max(1, Math.ceil(len / 0.006));
    for (let s = 0; s < steps; s++) pts.push([r0 + ((r1 - r0) * s) / steps, y0 + ((y1 - y0) * s) / steps]);
  }
  pts.push(profile[profile.length - 1]);

  const noise = makeNoise3(seed);
  const rows = pts.length, cols = segments + 1;
  const pos = new Float32Array(rows * cols * 3);
  const col = new Float32Array(rows * cols * 3);
  const uv = new Float32Array(rows * cols * 2);
  // Approximate arc length for v.
  const arc: number[] = [0];
  for (let i = 1; i < rows; i++) arc.push(arc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const total = arc[rows - 1] || 1;

  for (let i = 0; i < rows; i++) {
    const [r, y] = pts[i];
    for (let j = 0; j < cols; j++) {
      const th = (j / segments) * Math.PI * 2;
      let m = 1;
      let crevice = 0;
      for (const b of bands) {
        if (y < b.y0 || y > b.y1) continue;
        const t = (y - b.y0) / (b.y1 - b.y0);
        if (b.shape === 'flute') {
          // Gadroons: rounded lobes that swell in the middle of the band.
          const lobe = Math.abs(Math.sin((th * b.lobes) / 2));
          const env = Math.sin(Math.PI * t);
          m += b.amp * env * (Math.pow(lobe, 0.6) - 0.5);
          crevice = Math.max(crevice, (1 - Math.pow(lobe, 0.35)) * env);
        } else {
          // Beads: a row of little domes.
          const u = (th * b.lobes) / (Math.PI * 2);
          const fu = u - Math.floor(u) - 0.5;
          const fv = t - 0.5;
          const d = Math.min(1, Math.hypot(fu * 2, fv * 2));
          m += b.amp * Math.sqrt(Math.max(0, 1 - d * d));
          crevice = Math.max(crevice, Math.pow(d, 3) * 0.8);
        }
      }
      // A hint of hand-finished irregularity.
      const n = noise(Math.cos(th) * 3 + 11, y * 9, Math.sin(th) * 3);
      const rr = r * m * (1 + n * 0.0025);
      const k = (i * cols + j) * 3;
      pos[k] = Math.sin(th) * rr;
      pos[k + 1] = y;
      pos[k + 2] = Math.cos(th) * rr;
      const ao = 1 - crevice * 0.75;
      col[k] = col[k + 1] = col[k + 2] = ao;
      uv[(i * cols + j) * 2] = j / segments;
      uv[(i * cols + j) * 2 + 1] = arc[i] / total;
    }
  }
  const index: number[] = [];
  for (let i = 0; i < rows - 1; i++) {
    for (let j = 0; j < segments; j++) {
      const a = i * cols + j, b = a + 1, c = a + cols, d = c + 1;
      index.push(a, b, d, a, d, c);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(index);
  g.computeVertexNormals();
  // Weld the seam normals so the 0/2π column doesn't crease.
  const nor = g.getAttribute('normal') as THREE.BufferAttribute;
  for (let i = 0; i < rows; i++) {
    const a = i * cols, b = i * cols + segments;
    const nx = nor.getX(a) + nor.getX(b), ny = nor.getY(a) + nor.getY(b), nz = nor.getZ(a) + nor.getZ(b);
    const l = Math.hypot(nx, ny, nz) || 1;
    nor.setXYZ(a, nx / l, ny / l, nz / l);
    nor.setXYZ(b, nx / l, ny / l, nz / l);
  }
  return g;
}

function bronzeMaterial(): THREE.MeshPhysicalMaterial {
  // Hammered micro-surface + uneven polish.
  const S = 512;
  const fine = fbmField(S, 24, 3, 21);
  const broad = fbmField(S, 6, 4, 22);
  const rough = new Float32Array(S * S);
  for (let i = 0; i < rough.length; i++) rough[i] = 0.36 + broad[i] * 0.3 + (fine[i] - 0.5) * 0.14;
  const roughnessMap = fieldToTexture(rough, S, S, (v) => { const g = Math.max(0, Math.min(255, v * 255)); return [g, g, g]; });
  roughnessMap.repeat.set(3, 2);
  const normalMap = normalMapFromField(fine, S, S, 1.4);
  normalMap.wrapT = THREE.RepeatWrapping;
  normalMap.repeat.set(3, 2);
  const tint = fieldToTexture(broad, S, S, (v) => {
    // Old bronze: warm brown with darker, slightly olive patches.
    const t = Math.min(1, Math.max(0, (v - 0.35) * 2));
    const a = [138, 100, 62], b = [86, 66, 46];
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t] as [number, number, number];
  }, true);
  tint.repeat.set(2, 1);
  return new THREE.MeshPhysicalMaterial({
    color: '#ffffff',
    map: tint,
    vertexColors: true,
    metalness: 1,
    roughness: 1,
    roughnessMap,
    normalMap,
    normalScale: new THREE.Vector2(0.07, 0.07),
    envMapIntensity: 1.15,
  });
}

/** Polished oxblood marble with cream veins (2D domain-warped noise). */
function marbleMaterial(): THREE.MeshPhysicalMaterial {
  const S = 1024;
  const n1 = fbmField(S, 4, 5, 31);
  const n2 = fbmField(S, 9, 4, 32);
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d')!;
  const img = g.createImageData(S, S);
  for (let y = 0; y < S; y++) {
    for (let x = 0; x < S; x++) {
      const i = y * S + x;
      // Thin meandering veins along iso-lines of a warped field.
      const w = n1[i] + (n2[i] - 0.5) * 0.25 + (x / S) * 0.35;
      const f1 = Math.abs(((w * 7) % 1) - 0.5);
      const f2 = Math.abs(((n2[i] * 5 + (y / S) * 0.4) % 1) - 0.5);
      const vein = Math.exp(-f1 * 70) * 0.85 + Math.exp(-f2 * 110) * 0.35;
      const base = 0.72 + (n1[i] - 0.5) * 0.5;
      const r = 98 * base, gg = 46 * base, b = 38 * base;
      const vm = Math.min(1, vein);
      img.data[i * 4] = r + (214 - r) * vm;
      img.data[i * 4 + 1] = gg + (196 - gg) * vm;
      img.data[i * 4 + 2] = b + (172 - b) * vm;
      img.data[i * 4 + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = 8;
  return new THREE.MeshPhysicalMaterial({
    map,
    roughness: 0.16,
    metalness: 0,
    clearcoat: 0.6,
    clearcoatRoughness: 0.08,
    envMapIntensity: 0.9,
  });
}

async function plaqueMaterials(name: string, role: string) {
  try {
    await Promise.all([document.fonts.load('500 120px "Cormorant Garamond"'), document.fonts.load('500 40px "Inter Variable"')]);
  } catch { /* system fallback */ }
  const W = 1024, H = 256;
  const h = document.createElement('canvas');
  h.width = W; h.height = H;
  const g = h.getContext('2d')!;
  g.fillStyle = '#808080';
  g.fillRect(0, 0, W, H);
  // Raised border.
  g.strokeStyle = '#c8c8c8';
  g.lineWidth = 8;
  g.strokeRect(14, 14, W - 28, H - 28);
  g.strokeStyle = '#5a5a5a';
  g.lineWidth = 2;
  g.strokeRect(28, 28, W - 56, H - 56);
  // Engraved (recessed) lettering.
  g.fillStyle = '#202020';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.font = '500 104px "Cormorant Garamond", Georgia, serif';
  g.fillText(name, W / 2, H * 0.43);
  (g as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '10px';
  g.font = '600 26px "Inter Variable", system-ui, sans-serif';
  g.fillText(role.toUpperCase(), W / 2, H * 0.74);
  g.filter = 'blur(1.2px)';
  g.drawImage(h, 0, 0);
  const field = canvasToField(h);
  const normalMap = normalMapFromField(field, W, H, 3, false);
  // Colour: brass, with dark fill in the engraving (wax patina).
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const cg = c.getContext('2d')!;
  const img = cg.createImageData(W, H);
  const r = rng(5);
  for (let i = 0; i < W * H; i++) {
    const v = field[i];
    const engraved = v < 0.35 ? 1 : 0;
    const grain = (r() - 0.5) * 10;
    img.data[i * 4] = engraved ? 34 : 150 + grain;
    img.data[i * 4 + 1] = engraved ? 26 : 118 + grain;
    img.data[i * 4 + 2] = engraved ? 18 : 74 + grain * 0.6;
    img.data[i * 4 + 3] = 255;
  }
  cg.putImageData(img, 0, 0);
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = 8;
  // Engraving is matte; the plate is brushed.
  const rc = document.createElement('canvas');
  rc.width = W; rc.height = H;
  const rg = rc.getContext('2d')!;
  const rimg = rg.createImageData(W, H);
  for (let i = 0; i < W * H; i++) {
    const v = field[i] < 0.35 ? 235 : 130 + (r() - 0.5) * 30;
    rimg.data[i * 4] = rimg.data[i * 4 + 1] = rimg.data[i * 4 + 2] = v;
    rimg.data[i * 4 + 3] = 255;
  }
  rg.putImageData(rimg, 0, 0);
  const roughnessMap = new THREE.CanvasTexture(rc);
  return { map, normalMap, roughnessMap };
}

export interface Pedestal {
  group: THREE.Group;
  meshes: THREE.Mesh[];
  /** Local y where the sphere's lower surface rests and the cup's rim radius. */
  cupTop: number;
  cupRadius: number;
  /** Surfaces for shard contacts. */
  baseTop: number;
  baseRadius: number;
}

export function buildPedestal(name: string, role: string): Pedestal {
  const group = new THREE.Group();
  const bronze = bronzeMaterial();
  const S = 0.86; // base scale

  const base = new THREE.Mesh(
    revolve(
      [
        [0, 0], [0.86 * S, 0], [0.9 * S, 0.012], [0.915 * S, 0.035], [0.9 * S, 0.06], [0.885 * S, 0.075],
        [0.87 * S, 0.09], [0.84 * S, 0.165], [0.86 * S, 0.18], [0.875 * S, 0.195], [0.86 * S, 0.21], [0.82 * S, 0.215], [0.81 * S, 0.205],
      ],
      256,
      [
        { y0: 0.012, y1: 0.06, lobes: 72, amp: 0.025, shape: 'bead' },
        { y0: 0.09, y1: 0.165, lobes: 40, amp: 0.06, shape: 'flute' },
        { y0: 0.178, y1: 0.212, lobes: 96, amp: 0.012, shape: 'bead' },
      ],
    ),
    bronze,
  );
  base.castShadow = base.receiveShadow = true;
  group.add(base);

  // Marble disc set into the base, very slightly domed.
  const marble = new THREE.Mesh(new THREE.CylinderGeometry(0.81 * S, 0.81 * S, 0.02, 128, 1), marbleMaterial());
  marble.position.y = 0.197;
  marble.receiveShadow = true;
  group.add(marble);

  const stemProfile: [number, number][] = [
    [0.36, 0.205], [0.37, 0.22], [0.355, 0.245], [0.3, 0.262], [0.23, 0.3], [0.165, 0.36], [0.13, 0.41],
    [0.125, 0.44], [0.15, 0.47], [0.2, 0.5], [0.215, 0.53], [0.2, 0.56], [0.145, 0.585], [0.11, 0.62],
    [0.105, 0.66], [0.13, 0.69], [0.13, 0.71], [0.17, 0.73], [0.26, 0.78], [0.35, 0.835], [0.41, 0.88],
    [0.44, 0.91], [0.455, 0.93], [0.45, 0.945], [0.43, 0.955], [0.0, 0.955],
  ];
  const stem = new THREE.Mesh(
    revolve(stemProfile, 256, [
      { y0: 0.21, y1: 0.255, lobes: 36, amp: 0.03, shape: 'bead' },
      { y0: 0.485, y1: 0.575, lobes: 18, amp: 0.1, shape: 'flute' },
      { y0: 0.695, y1: 0.715, lobes: 40, amp: 0.05, shape: 'bead' },
      { y0: 0.73, y1: 0.9, lobes: 26, amp: 0.09, shape: 'flute' },
      { y0: 0.91, y1: 0.95, lobes: 80, amp: 0.018, shape: 'bead' },
    ], 7),
    bronze,
  );
  stem.castShadow = stem.receiveShadow = true;
  group.add(stem);

  // Brass plaque, leaning on a small foot at the front of the marble.
  const plaque = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.125, 0.008), new THREE.MeshPhysicalMaterial({ color: '#ffffff', metalness: 1, roughness: 0.4 }));
  plaque.position.set(0, 0.258, 0.545);
  plaque.rotation.x = -0.55;
  plaque.castShadow = true;
  plaque.receiveShadow = true;
  plaque.visible = false;
  plaque.userData.loaded = false;
  group.add(plaque);
  plaqueMaterials(name, role).then(({ map, normalMap, roughnessMap }) => {
    const front = new THREE.MeshPhysicalMaterial({ map, normalMap, roughnessMap, normalScale: new THREE.Vector2(1, 1), metalness: 1, roughness: 1, envMapIntensity: 1.2 });
    const edge = new THREE.MeshPhysicalMaterial({ color: '#b08a55', metalness: 1, roughness: 0.35 });
    // Box faces: +x, -x, +y, -y, +z (front), -z.
    (plaque as THREE.Mesh).material = [edge, edge, edge, edge, front, edge];
    plaque.userData.loaded = true;
    plaque.visible = true;
  });

  return {
    group,
    meshes: [base, marble, stem, plaque],
    cupTop: 0.955,
    cupRadius: 0.43,
    baseTop: 0.207,
    baseRadius: 0.8 * S,
  };
}
