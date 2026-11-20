import * as THREE from 'three';
import { canvasToField, makeNoise3, normalMapFromField, rng } from './textures';

/**
 * Turned, varnished wooden base for the crystal globe: a moulded foot, a
 * carved band of flutes between bead rows, and a shallow cup. The ornament
 * is real geometry (the radius is modulated around the axis), so it catches
 * light and casts shadow; crevices get darker via vertex colour.
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

/**
 * Varnished mahogany as it looks on turned work: growth rings sweep around
 * the piece, with darker latewood lines, uneven colour and a glossy coat.
 */
/**
 * Real wood: Poly Haven's scanned "Dark Wood" (CC0), grain running around the
 * turned piece like the rings of a lathe-turned base, with a satin finish.
 */
function turnedWood(): THREE.MeshPhysicalMaterial {
  const L = new THREE.TextureLoader();
  const base = import.meta.env.BASE_URL + 'textures/';
  const t = (f: string, srgb: boolean) => {
    const x = L.load(base + f);
    x.wrapS = x.wrapT = THREE.RepeatWrapping;
    x.repeat.set(5, 1.4);
    x.anisotropy = 8;
    x.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    return x;
  };
  return new THREE.MeshPhysicalMaterial({
    map: t('dark_wood_diff.webp', true),
    normalMap: t('dark_wood_nor.webp', false),
    normalScale: new THREE.Vector2(0.6, 0.6),
    roughnessMap: t('dark_wood_rough.webp', false),
    roughness: 0.9,
    vertexColors: true,  // carving crevices stay darker
    clearcoat: 0.25,
    clearcoatRoughness: 0.35,
    envMapIntensity: 0.6,
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
    img.data[i * 4] = engraved ? 34 : 200 + grain;
    img.data[i * 4 + 1] = engraved ? 26 : 160 + grain;
    img.data[i * 4 + 2] = engraved ? 18 : 96 + grain * 0.6;
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
  const wood = turnedWood();

  // Squat turned base: foot, cove, a carved band (flutes between bead rows),
  // a shoulder, and a shallow cup the sphere sits in.
  // The base rises to the level of the terrain inside, so its wooden rim
  // hides the soil and the glass meets the world at ground level.
  const RIM = 0.87, KY = 0.95;
  const CUP_TOP = 0.45 * KY, CUP_R = RIM;
  // Offset the profile outward to the rim (rather than scaling it), so the
  // foot doesn't balloon: the base stays slim under the globe.
  const raw: [number, number][] = [
    [0, 0], [0.8, 0], [0.82, 0.012], [0.825, 0.055], [0.81, 0.075], [0.79, 0.085],
    [0.79, 0.1], [0.775, 0.115], [0.745, 0.13], [0.72, 0.15], [0.69, 0.175],
    [0.675, 0.19], [0.68, 0.205], [0.67, 0.215], [0.655, 0.22],
    [0.655, 0.345], // carved band
    [0.67, 0.35], [0.68, 0.365], [0.67, 0.38], [0.645, 0.39], [0.6, 0.405],
    [0.57, 0.42], [0.56, 0.435], [0.54, 0.448], [0.5, 0.45], [0, 0.45],
  ];
  const profile = raw.map(([r, y]) => [r === 0 ? 0 : r + (RIM - 0.5) * 0.82, y * KY] as [number, number]);
  const base = new THREE.Mesh(
    revolve(profile, 320, [
      { y0: 0.015, y1: 0.07, lobes: 150, amp: 0.012, shape: 'bead' },
      { y0: 0.19, y1: 0.215, lobes: 190, amp: 0.018, shape: 'bead' },
      { y0: 0.222, y1: 0.343, lobes: 70, amp: 0.05, shape: 'flute' },
      { y0: 0.348, y1: 0.38, lobes: 190, amp: 0.018, shape: 'bead' },
      { y0: 0.4, y1: 0.445, lobes: 96, amp: 0.025, shape: 'flute' },
    ].map((b) => ({ ...b, y0: b.y0 * KY, y1: b.y1 * KY })) as Band[], 7),
    wood,
  );
  base.castShadow = base.receiveShadow = true;
  group.add(base);

  // Brass plaque set into the front of the carved band, following its curve.
  const arc = 0.5, ph = 0.1 * KY, pr = 0.675 + (RIM - 0.5) * 0.82;
  const plaque = new THREE.Mesh(
    new THREE.CylinderGeometry(pr, pr, ph, 48, 1, true, -arc / 2, arc),
    new THREE.MeshPhysicalMaterial({ color: '#c9a061', metalness: 1, roughness: 0.4 }),
  );
  plaque.position.y = 0.283 * KY;
  plaque.castShadow = true;
  plaque.visible = false;
  plaque.userData.loaded = false;
  group.add(plaque);
  plaqueMaterials(name, role).then(({ map, normalMap, roughnessMap }) => {
    (plaque as THREE.Mesh).material = new THREE.MeshPhysicalMaterial({
      map, normalMap, roughnessMap, normalScale: new THREE.Vector2(1, 1), metalness: 1, roughness: 1, envMapIntensity: 1.3,
    });
    plaque.userData.loaded = true;
    plaque.visible = true;
  });

  return {
    group,
    meshes: [base, plaque],
    cupTop: CUP_TOP,
    cupRadius: CUP_R,
    baseTop: 0.39 * KY,
    baseRadius: 0.68 + (RIM - 0.5) * 0.82,
  };
}
