import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { fbm3, fbmField, makeNoise3, normalMapFromField, rng } from './textures';

/**
 * The miniature world inside the globe, built like a real terrarium:
 * soil and gravel strata against the glass, a carpet of cushion moss, a
 * pebble path, mossy stones, a small stream, ferns, a gnarled tree with
 * flared roots and leaf pads, a small amber maple and two pines.
 * Everything is procedural and instanced. Coordinates are local to the
 * globe group; `c` is the sphere centre.
 */

export interface Interior {
  group: THREE.Group;
  groundAt(x: number, z: number): number;
  groundY: number;
  radius: number;
  update(t: number): void;
  setOpacity(o: number): void;
  transparents: THREE.Object3D[];
}

type V2 = [number, number];

const C = (h: string) => new THREE.Color(h);
const MOSS = ['#2c4615', '#3b5a19', '#4e6e1d', '#6a8a28', '#1f3210', '#869a36'].map(C);

/** Distance from p to a polyline. */
function polyDist(px: number, pz: number, pts: V2[]): number {
  let best = 1e9;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
    const vx = bx - ax, vz = bz - az;
    const l2 = vx * vx + vz * vz || 1;
    const u = Math.max(0, Math.min(1, ((px - ax) * vx + (pz - az) * vz) / l2));
    const dx = ax + vx * u - px, dz = az + vz * u - pz;
    best = Math.min(best, dx * dx + dz * dz);
  }
  return Math.sqrt(best);
}

function smoothPath(pts: V2[], n: number): V2[] {
  const curve = new THREE.CatmullRomCurve3(pts.map(([x, z]) => new THREE.Vector3(x, 0, z)));
  return curve.getPoints(n).map((p) => [p.x, p.z]);
}

/** Tube whose radius tapers from r0 to r1 along the curve, with bark bumps. */
function taperedTube(curve: THREE.Curve<THREE.Vector3>, segs: number, r0: number, r1: number, radial: number, noise: (x: number, y: number, z: number) => number): THREE.BufferGeometry {
  const frames = curve.computeFrenetFrames(segs, false);
  const pos: number[] = [], idx: number[] = [], uv: number[] = [];
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const p = curve.getPointAt(t);
    const N = frames.normals[i], B = frames.binormals[i];
    const r = r0 + (r1 - r0) * Math.pow(t, 0.8);
    for (let j = 0; j <= radial; j++) {
      const a = (j / radial) * Math.PI * 2;
      const bump = 1 + noise(p.x * 60 + j * 0.3, p.y * 60, p.z * 60) * 0.35;
      const nx = Math.cos(a) * N.x + Math.sin(a) * B.x, ny = Math.cos(a) * N.y + Math.sin(a) * B.y, nz = Math.cos(a) * N.z + Math.sin(a) * B.z;
      pos.push(p.x + nx * r * bump, p.y + ny * r * bump, p.z + nz * r * bump);
      uv.push(j / radial, t);
    }
  }
  for (let i = 0; i < segs; i++) {
    for (let j = 0; j < radial; j++) {
      const a = i * (radial + 1) + j, b = a + radial + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export function buildInterior(c: THREE.Vector3, R: number): Interior {
  const group = new THREE.Group();
  const n3 = makeNoise3(41);
  const rnd = rng(9);
  const inner = R * 0.972;
  const depth = 0.52;
  const groundY = c.y - depth;
  const edgeR = Math.sqrt(inner * inner - depth * depth);

  // ---- layout (local x/z offsets from the centre)
  const stream = smoothPath([[0.12, -0.78], [0.3, -0.4], [0.22, -0.05], [0.38, 0.32], [0.3, 0.7]], 60);
  const path = smoothPath([[-0.12, 0.8], [-0.05, 0.5], [-0.14, 0.22], [-0.2, 0.02]], 40);
  const treeAt: V2 = [-0.3, -0.12];

  const groundAt = (x: number, z: number) => {
    const dx = x - c.x, dz = z - c.z;
    const r = Math.hypot(dx, dz) / edgeR;
    const edge = Math.max(0, 1 - Math.pow(Math.min(1, r), 5));
    // Rises toward the back, with a knoll under the tree.
    let h = 0.07 * Math.max(0, -dz) + 0.05 * Math.exp(-((dx - treeAt[0]) ** 2 + (dz - treeAt[1]) ** 2) / 0.05);
    h += fbm3(n3, dx * 3.5, 0.5, dz * 3.5, 4) * 0.035;
    const sd = polyDist(dx, dz, stream);
    h -= 0.028 * Math.exp(-(sd * sd) / 0.0032); // stream bed
    return groundY + h * edge;
  };

  // ---- terrain surface (polar grid so the rim is a perfect circle)
  const RINGS = 80, SEG = 240;
  const tPos: number[] = [], tCol: number[] = [], tIdx: number[] = [], tUv: number[] = [];
  const tmp = new THREE.Color();
  const soilDark = C('#3a2a1a'), soilWet = C('#2a1d12');
  const pushV = (x: number, z: number) => {
    tPos.push(x, groundAt(x, z), z);
    tUv.push(x * 3, z * 3);
    const sd = polyDist(x - c.x, z - c.z, stream);
    const pd = polyDist(x - c.x, z - c.z, path);
    const v = fbm3(n3, x * 9, 3, z * 9, 3) + 0.5;
    tmp.copy(MOSS[4]).lerp(MOSS[1], THREE.MathUtils.clamp(v, 0, 1));
    if (pd < 0.06) tmp.lerp(soilDark, 1 - pd / 0.06);
    if (sd < 0.07) tmp.lerp(soilWet, 1 - sd / 0.07);
    tCol.push(tmp.r, tmp.g, tmp.b);
  };
  pushV(c.x, c.z);
  for (let i = 1; i <= RINGS; i++) {
    const rr = (i / RINGS) * edgeR;
    for (let j = 0; j < SEG; j++) {
      const a = (j / SEG) * Math.PI * 2;
      pushV(c.x + Math.cos(a) * rr, c.z + Math.sin(a) * rr);
    }
  }
  for (let j = 0; j < SEG; j++) tIdx.push(0, 1 + ((j + 1) % SEG), 1 + j);
  for (let i = 1; i < RINGS; i++) {
    for (let j = 0; j < SEG; j++) {
      const a = 1 + (i - 1) * SEG + j, b = 1 + (i - 1) * SEG + ((j + 1) % SEG);
      tIdx.push(a, b, b + SEG, a, b + SEG, a + SEG);
    }
  }
  const tGeo = new THREE.BufferGeometry();
  tGeo.setAttribute('position', new THREE.Float32BufferAttribute(tPos, 3));
  tGeo.setAttribute('color', new THREE.Float32BufferAttribute(tCol, 3));
  tGeo.setAttribute('uv', new THREE.Float32BufferAttribute(tUv, 2));
  tGeo.setIndex(tIdx);
  tGeo.computeVertexNormals();
  const fine = fbmField(256, 40, 4, 44);
  const fuzz = normalMapFromField(fine, 256, 256, 2.6);
  fuzz.wrapT = THREE.RepeatWrapping;
  const terrainMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, normalMap: fuzz, normalScale: new THREE.Vector2(1, 1) });
  terrainMat.shadowSide = THREE.DoubleSide;
  const terrain = new THREE.Mesh(tGeo, terrainMat);
  terrain.receiveShadow = terrain.castShadow = true;
  group.add(terrain);

  // ---- soil cross-section with a pale gravel layer at the bottom
  const th0 = Math.acos(-depth / inner);
  const soilGeo = new THREE.SphereGeometry(inner, 240, 72, 0, Math.PI * 2, th0, Math.PI - th0);
  const sp = soilGeo.getAttribute('position') as THREE.BufferAttribute;
  const sCol: number[] = [];
  const loam = C('#5b3c22'), peat = C('#3e2814'), gravel = C('#cfc4b6'), gravelDark = C('#7d7266');
  for (let i = 0; i < sp.count; i++) {
    const x = sp.getX(i), y = sp.getY(i), z = sp.getZ(i);
    const d = (-depth - y) / (inner - depth);
    const wob = fbm3(n3, x * 4, y * 1.5, z * 4, 3) * 0.12;
    tmp.copy(loam).lerp(peat, THREE.MathUtils.clamp(0.5 + fbm3(n3, x * 7, y * 7, z * 7, 2), 0, 1));
    if (d + wob > 0.5) {
      const g = fbm3(n3, x * 38, y * 38, z * 38, 2) + 0.5;
      tmp.copy(gravelDark).lerp(gravel, THREE.MathUtils.clamp(g * 1.3 - 0.1, 0, 1));
    }
    if (d < 0.04) tmp.lerp(MOSS[4], 1 - d / 0.04);
    sCol.push(tmp.r, tmp.g, tmp.b);
  }
  soilGeo.setAttribute('color', new THREE.Float32BufferAttribute(sCol, 3));
  const soil = new THREE.Mesh(soilGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 }));
  soil.position.copy(c);
  soil.receiveShadow = true;
  group.add(soil);

  const freeSpot = (x: number, z: number, clearPath = 0.06, clearStream = 0.07) => {
    const dx = x - c.x, dz = z - c.z;
    if (Math.hypot(dx, dz) > edgeR * 0.93) return false;
    if (polyDist(dx, dz, path) < clearPath) return false;
    if (polyDist(dx, dz, stream) < clearStream) return false;
    return true;
  };

  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), pv = new THREE.Vector3(), e = new THREE.Euler();

  // ---- cushion moss: bumpy hemispheres, instanced, in clustered colours
  const clump = new THREE.SphereGeometry(1, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2);
  {
    const p = clump.getAttribute('position') as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(p, i);
      const k = 1 + fbm3(n3, v.x * 4 + 3, v.y * 4, v.z * 4, 3) * 0.55 + fbm3(n3, v.x * 14, v.y * 14, v.z * 14, 2) * 0.12;
      v.multiplyScalar(k);
      p.setXYZ(i, v.x, Math.max(0, v.y) * 0.62, v.z);
    }
    clump.computeVertexNormals();
  }
  const mossMat = new THREE.MeshPhysicalMaterial({ roughness: 0.95, normalMap: fuzz, normalScale: new THREE.Vector2(1.6, 1.6), sheen: 0.35, sheenRoughness: 0.7, sheenColor: C('#c9dc8a') });
  const MOSSN = 520;
  const moss = new THREE.InstancedMesh(clump, mossMat, MOSSN);
  let mi = 0;
  for (let tries = 0; mi < MOSSN && tries < MOSSN * 12; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.95;
    const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
    if (!freeSpot(x, z, 0.045, 0.05)) continue;
    const cluster = fbm3(n3, x * 6, 1, z * 6, 2);
    if (cluster + rnd() * 0.3 < 0.02) continue;
    const s = 0.018 + Math.pow(rnd(), 1.8) * 0.05;
    pv.set(x, groundAt(x, z) - s * 0.15, z);
    e.set((rnd() - 0.5) * 0.3, rnd() * 6.28, (rnd() - 0.5) * 0.3);
    q.setFromEuler(e);
    sc.set(s * (0.8 + rnd() * 0.5), s * (0.6 + rnd() * 0.6), s * (0.8 + rnd() * 0.5));
    m4.compose(pv, q, sc);
    moss.setMatrixAt(mi, m4);
    const base = MOSS[Math.floor((cluster + 0.5) * 5.99 + rnd() * 1.2) % MOSS.length];
    moss.setColorAt(mi, tmp.copy(base).multiplyScalar(0.85 + rnd() * 0.3));
    mi++;
  }
  moss.count = mi;
  moss.castShadow = moss.receiveShadow = true;
  group.add(moss);

  // ---- pebbles: pale and packed along the path, darker by the stream
  const pebbleGeo = new THREE.IcosahedronGeometry(1, 2);
  {
    const p = pebbleGeo.getAttribute('position') as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(p, i);
      v.multiplyScalar(1 + fbm3(n3, v.x * 2.5, v.y * 2.5, v.z * 2.5, 2) * 0.35);
      p.setXYZ(i, v.x, v.y * 0.5, v.z);
    }
    pebbleGeo.computeVertexNormals();
  }
  const pebbleMat = new THREE.MeshPhysicalMaterial({ roughness: 0.55, clearcoat: 0.3, clearcoatRoughness: 0.4 });
  const PEB = 520;
  const pebbles = new THREE.InstancedMesh(pebbleGeo, pebbleMat, PEB);
  let pi = 0;
  const pale = [C('#e9e4da'), C('#d8d1c4'), C('#f2efe8'), C('#c9c0b2')];
  const darkStone = [C('#7d766c'), C('#5d5852'), C('#9a9186'), C('#4a4540')];
  for (let tries = 0; pi < PEB && tries < PEB * 10; tries++) {
    const onPath = pi < 340;
    let x: number, z: number;
    if (onPath) {
      const k = Math.min(path.length - 2, Math.floor(rnd() * (path.length - 1)));
      const [ax, az] = path[k], [bx, bz] = path[k + 1];
      const nx = -(bz - az), nz = bx - ax, nl = Math.hypot(nx, nz) || 1;
      const off = (rnd() - 0.5) * 0.09, u = rnd();
      x = c.x + ax + (bx - ax) * u + (nx / nl) * off;
      z = c.z + az + (bz - az) * u + (nz / nl) * off;
    } else {
      const k = Math.min(stream.length - 2, Math.floor(rnd() * (stream.length - 1)));
      const [ax, az] = stream[k];
      const a = rnd() * Math.PI * 2, rr = 0.03 + rnd() * 0.05;
      x = c.x + ax + Math.cos(a) * rr;
      z = c.z + az + Math.sin(a) * rr;
    }
    if (Math.hypot(x - c.x, z - c.z) > edgeR * 0.94) continue;
    const s = onPath ? 0.009 + rnd() * 0.009 : 0.006 + rnd() * 0.014;
    pv.set(x, groundAt(x, z) + s * 0.15, z);
    e.set((rnd() - 0.5) * 0.4, rnd() * 6.28, (rnd() - 0.5) * 0.4);
    q.setFromEuler(e);
    sc.set(s * (1 + rnd() * 0.4), s, s * (0.8 + rnd() * 0.3));
    m4.compose(pv, q, sc);
    pebbles.setMatrixAt(pi, m4);
    const pal = onPath ? pale : darkStone;
    pebbles.setColorAt(pi, tmp.copy(pal[Math.floor(rnd() * pal.length)]));
    pi++;
  }
  pebbles.count = pi;
  pebbles.castShadow = pebbles.receiveShadow = true;
  group.add(pebbles);

  // ---- stones: layered ledges, with moss on top
  const stoneGeos: THREE.BufferGeometry[] = [];
  const stones: [number, number, number, number][] = [[0.02, -0.56, 0.13, 1.4], [0.46, -0.2, 0.06, 1], [0.14, 0.18, 0.05, 0.9], [0.5, 0.48, 0.045, 1], [-0.55, 0.32, 0.05, 1.1], [0.2, -0.72, 0.05, 1]];
  for (const [sx, sz, s, tall] of stones) {
    const g = new THREE.IcosahedronGeometry(s, 5);
    const p = g.getAttribute('position') as THREE.BufferAttribute;
    const cols: number[] = [];
    const seed = sx * 13 + sz * 7;
    for (let i = 0; i < p.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(p, i);
      const dir = v.clone().normalize();
      let k = 1 + fbm3(n3, dir.x * 3 + seed, dir.y * 3, dir.z * 3, 4) * 0.55;
      k += Math.round(dir.y * 5) * 0.02; // strata ledges
      v.multiplyScalar(k);
      v.y = v.y * 0.75 * tall + s * 0.25;
      p.setXYZ(i, v.x, v.y, v.z);
      const grain = fbm3(n3, v.x * 90, v.y * 90, v.z * 90, 2);
      tmp.copy(C('#7b766e')).lerp(C('#a49d92'), THREE.MathUtils.clamp(0.5 + grain, 0, 1)).multiplyScalar(0.85 + (Math.abs(Math.round(dir.y * 5)) % 2) * 0.12);
      const mossy = THREE.MathUtils.clamp((dir.y - 0.25) * 2.4 + fbm3(n3, v.x * 30, v.y * 30, v.z * 30, 2) * 1.2, 0, 1);
      tmp.lerp(MOSS[2], mossy * 0.9);
      cols.push(tmp.r, tmp.g, tmp.b);
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    g.computeVertexNormals();
    g.rotateY(rnd() * 6.28);
    const x = c.x + sx, z = c.z + sz;
    g.translate(x, groundAt(x, z) - s * 0.2, z);
    stoneGeos.push(g.index ? g.toNonIndexed() : g);
  }
  const stoneMesh = new THREE.Mesh(mergeGeometries(stoneGeos), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, normalMap: fuzz, normalScale: new THREE.Vector2(0.6, 0.6) }));
  stoneMesh.castShadow = stoneMesh.receiveShadow = true;
  group.add(stoneMesh);

  // ---- stream: a reflective ribbon in the carved bed, gently rippling
  const wPos: number[] = [], wIdx: number[] = [], wUv: number[] = [];
  for (let i = 0; i < stream.length; i++) {
    const [x, z] = stream[i];
    const [ax, az] = stream[Math.min(stream.length - 1, i + 1)], [bx, bz] = stream[Math.max(0, i - 1)];
    const tx = ax - bx, tz = az - bz, tl = Math.hypot(tx, tz) || 1;
    const w = 0.032 + Math.sin(i * 0.4) * 0.006;
    const y = groundAt(c.x + x, c.z + z) + 0.006;
    for (const sgn of [-1, 1]) {
      wPos.push(c.x + x + (-tz / tl) * w * sgn, y, c.z + z + (tx / tl) * w * sgn);
      wUv.push(sgn * 0.5 + 0.5, i / 8);
    }
    if (i > 0) { const a = (i - 1) * 2; wIdx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const wGeo = new THREE.BufferGeometry();
  wGeo.setAttribute('position', new THREE.Float32BufferAttribute(wPos, 3));
  wGeo.setAttribute('uv', new THREE.Float32BufferAttribute(wUv, 2));
  wGeo.setIndex(wIdx);
  wGeo.computeVertexNormals();
  const ripple = normalMapFromField(fbmField(256, 12, 3, 61), 256, 256, 1.5);
  ripple.wrapT = THREE.RepeatWrapping;
  const waterMat = new THREE.MeshPhysicalMaterial({ color: '#3d5a55', roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.8, normalMap: ripple, normalScale: new THREE.Vector2(0.35, 0.35), transparent: true, opacity: 0.92, side: THREE.DoubleSide });
  const water = new THREE.Mesh(wGeo, waterMat);
  water.receiveShadow = true;
  group.add(water);

  // ---- ferns: fronds of leaflet pairs, instanced into rosettes
  const frondParts: number[] = [];
  {
    const leaflets = 14;
    const spine = (t: number) => new THREE.Vector3(t, Math.sin(t * Math.PI * 0.85) * 0.35 - t * t * 0.15, 0);
    for (let k = 1; k <= leaflets; k++) {
      const t = k / (leaflets + 1);
      const p0 = spine(t);
      const len = 0.28 * Math.sin(Math.PI * Math.min(1, t * 1.15)) + 0.04;
      for (const sgn of [-1, 1]) {
        const tip = p0.clone().add(new THREE.Vector3(len * 0.35, -len * 0.15, sgn * len));
        const a = spine(t - 0.025), b = spine(t + 0.025);
        frondParts.push(a.x, a.y, a.z, b.x, b.y, b.z, tip.x, tip.y, tip.z);
      }
    }
    for (let k = 0; k < 20; k++) {
      const a = spine(k / 20), b = spine((k + 1) / 20);
      frondParts.push(a.x, a.y, a.z - 0.01, b.x, b.y, b.z - 0.01, b.x, b.y, b.z + 0.01);
    }
  }
  const frondGeo = new THREE.BufferGeometry();
  frondGeo.setAttribute('position', new THREE.Float32BufferAttribute(frondParts, 3));
  frondGeo.computeVertexNormals();
  const fernMat = new THREE.MeshStandardMaterial({ roughness: 0.7, side: THREE.DoubleSide });
  const FERN_SPOTS: V2[] = [[0.08, -0.42], [0.55, 0.0], [-0.45, 0.45], [0.48, 0.62], [-0.05, -0.68], [-0.62, -0.1], [0.26, 0.5]];
  const ferns = new THREE.InstancedMesh(frondGeo, fernMat, FERN_SPOTS.length * 9);
  let fi = 0;
  for (const [fx, fz] of FERN_SPOTS) {
    const x = c.x + fx, z = c.z + fz;
    const y = groundAt(x, z);
    const size = 0.07 + rnd() * 0.04;
    for (let k = 0; k < 9; k++) {
      pv.set(x, y, z);
      e.set(0, (k / 9) * Math.PI * 2 + rnd() * 0.4, 0.35 + rnd() * 0.35, 'YZX');
      q.setFromEuler(e);
      const s = size * (0.7 + rnd() * 0.5);
      sc.set(s, s, s);
      m4.compose(pv, q, sc);
      ferns.setMatrixAt(fi, m4);
      ferns.setColorAt(fi, tmp.copy(C('#5f8f2e')).lerp(C('#8fb84a'), rnd() * 0.6));
      fi++;
    }
  }
  ferns.castShadow = ferns.receiveShadow = true;
  group.add(ferns);

  // ---- trees: gnarled trunk, roots and branches as tapered tubes; leaf pads
  const barkGeos: THREE.BufferGeometry[] = [];
  const pads: { p: THREE.Vector3; r: number; col: THREE.Color[] }[] = [];
  const green = [C('#4f7a28'), C('#6a9a32'), C('#3c6420'), C('#88ad45')];
  const amber = [C('#c0601f'), C('#d88a2c'), C('#a8401a'), C('#e0a640')];

  const branch = (start: THREE.Vector3, dir: THREE.Vector3, len: number, r0: number, depthLeft: number, palette: THREE.Color[]) => {
    const pts = [start.clone()];
    const d = dir.clone();
    const steps = 4;
    for (let i = 1; i <= steps; i++) {
      d.add(new THREE.Vector3((rnd() - 0.5) * 0.7, (rnd() - 0.3) * 0.3, (rnd() - 0.5) * 0.7)).normalize();
      pts.push(pts[i - 1].clone().addScaledVector(d, len / steps));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    barkGeos.push(taperedTube(curve, 10, r0, r0 * 0.55, 8, n3));
    const end = pts[pts.length - 1];
    if (depthLeft <= 0) {
      pads.push({ p: end.clone(), r: 0.065 + rnd() * 0.035, col: palette });
      return;
    }
    const kids = depthLeft >= 2 ? 3 : 2;
    for (let k = 0; k < kids; k++) {
      // Spread outward and only gently upward, like a bonsai's tiers.
      const a = (k / kids) * Math.PI * 2 + rnd() * 1.2;
      const nd = new THREE.Vector3(Math.cos(a), 0.25 + rnd() * 0.35, Math.sin(a)).add(d.clone().multiplyScalar(0.4)).normalize();
      branch(end, nd, len * (0.7 + rnd() * 0.15), r0 * 0.58, depthLeft - 1, palette);
    }
    if (depthLeft <= 1) pads.push({ p: curve.getPointAt(0.65), r: 0.05, col: palette });
  };

  const tree = (at: V2, height: number, r0: number, palette: THREE.Color[], lean: THREE.Vector3) => {
    const x = c.x + at[0], z = c.z + at[1];
    const base = new THREE.Vector3(x, groundAt(x, z) - 0.01, z);
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + rnd() * 0.5;
      const pts = [
        base.clone().add(new THREE.Vector3(0, height * 0.12, 0)),
        base.clone().add(new THREE.Vector3(Math.cos(a) * r0 * 2.4, height * 0.04, Math.sin(a) * r0 * 2.4)),
        base.clone().add(new THREE.Vector3(Math.cos(a) * r0 * 5, -0.004, Math.sin(a) * r0 * 5)),
      ];
      barkGeos.push(taperedTube(new THREE.CatmullRomCurve3(pts), 8, r0 * 0.55, r0 * 0.12, 6, n3));
    }
    branch(base, lean.clone().normalize(), height * 0.55, r0, 3, palette);
  };

  tree(treeAt, 0.42, 0.03, green, new THREE.Vector3(0.35, 1, 0.15));
  tree([0.52, 0.14], 0.26, 0.014, amber, new THREE.Vector3(-0.2, 1, 0.1));

  // Pines: a straight trunk with whorls of needle tufts.
  const pineTufts: { p: THREE.Vector3; r: number }[] = [];
  for (const [px, pz, h] of [[0.52, -0.45, 0.42], [-0.62, -0.42, 0.34]] as [number, number, number][]) {
    const x = c.x + px, z = c.z + pz;
    const b = new THREE.Vector3(x, groundAt(x, z) - 0.01, z);
    const curve = new THREE.CatmullRomCurve3([b, b.clone().add(new THREE.Vector3(0.005, h * 0.5, 0)), b.clone().add(new THREE.Vector3(0, h, 0.004))]);
    barkGeos.push(taperedTube(curve, 12, 0.009, 0.002, 6, n3));
    const whorls = 9;
    for (let w = 0; w < whorls; w++) {
      const t = 0.22 + (w / whorls) * 0.78;
      const y = b.y + h * t;
      const rr = (1 - t) * h * 0.42 + 0.018;
      for (let k = 0; k < 6; k++) {
        const a = (k / 6) * Math.PI * 2 + w;
        pineTufts.push({ p: new THREE.Vector3(x + Math.cos(a) * rr * 0.6, y - rr * 0.15, z + Math.sin(a) * rr * 0.6), r: rr * 0.55 });
      }
    }
  }

  const barkMat = new THREE.MeshStandardMaterial({ color: '#5a4232', roughness: 0.9, normalMap: fuzz, normalScale: new THREE.Vector2(2, 2) });
  const bark = new THREE.Mesh(mergeGeometries(barkGeos.map((g) => (g.index ? g.toNonIndexed() : g))), barkMat);
  bark.castShadow = bark.receiveShadow = true;
  group.add(bark);

  // Leaves: tiny diamond cards in flattened pads; pine needles as slim cards.
  const leaf = new THREE.BufferGeometry();
  leaf.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 0.5, 0.12, 0, 1, 0, 0, 0.5, -0.12, 0], 3));
  leaf.setAttribute('normal', new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  leaf.setIndex([0, 1, 2, 0, 2, 3]);
  const PER_PAD = 240, PER_TUFT = 70;
  const leafMat = new THREE.MeshStandardMaterial({ roughness: 0.65, side: THREE.DoubleSide });
  const uTime = { value: 0 };
  leafMat.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = uTime;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;').replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
       vec4 lp = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
       transformed.y += sin(uTime * 1.7 + lp.x * 40.0 + lp.z * 31.0) * 0.06 * position.x;`,
    );
  };
  const leaves = new THREE.InstancedMesh(leaf, leafMat, pads.length * PER_PAD + pineTufts.length * PER_TUFT);
  let li = 0;
  for (const pad of pads) {
    for (let k = 0; k < PER_PAD; k++) {
      const u = rnd() * Math.PI * 2, v = Math.acos(2 * rnd() - 1), rr = pad.r * Math.cbrt(rnd());
      pv.set(pad.p.x + Math.sin(v) * Math.cos(u) * rr, pad.p.y + Math.cos(v) * rr * 0.45 + 0.01, pad.p.z + Math.sin(v) * Math.sin(u) * rr);
      e.set(rnd() * 6.28, rnd() * 6.28, rnd() * 6.28);
      q.setFromEuler(e);
      const s = 0.014 + rnd() * 0.012;
      sc.set(s, s, s);
      m4.compose(pv, q, sc);
      leaves.setMatrixAt(li, m4);
      // Outer, upper leaves are lighter: they catch the light.
      const outer = rr / pad.r;
      const col = pad.col[Math.floor(rnd() * pad.col.length)];
      leaves.setColorAt(li, tmp.copy(col).multiplyScalar(0.7 + outer * 0.45 + (pv.y - pad.p.y) * 4));
      li++;
    }
  }
  for (const t of pineTufts) {
    for (let k = 0; k < PER_TUFT; k++) {
      pv.set(t.p.x + (rnd() - 0.5) * t.r * 2, t.p.y + (rnd() - 0.5) * t.r * 0.5, t.p.z + (rnd() - 0.5) * t.r * 2);
      e.set((rnd() - 0.5) * 0.6, rnd() * 6.28, -0.3 - rnd() * 0.4);
      q.setFromEuler(e);
      const s = 0.02 + rnd() * 0.014;
      sc.set(s, s * 0.35, s);
      m4.compose(pv, q, sc);
      leaves.setMatrixAt(li, m4);
      leaves.setColorAt(li, tmp.copy(C('#2d4a28')).lerp(C('#4a6e38'), rnd()));
      li++;
    }
  }
  leaves.count = li;
  leaves.castShadow = leaves.receiveShadow = true;
  group.add(leaves);

  // ---- a little grass between the moss
  const blade = new THREE.BufferGeometry();
  blade.setAttribute('position', new THREE.Float32BufferAttribute([-0.0016, 0, 0, 0.0016, 0, 0, 0, 1, 0], 3));
  blade.setAttribute('normal', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 0, 0, 1], 3));
  const grassMat = new THREE.MeshStandardMaterial({ roughness: 0.8, side: THREE.DoubleSide });
  grassMat.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = uTime;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;').replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
       vec4 wp = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
       float bladeH = length(instanceMatrix[1].xyz);
       float sway = sin(uTime * 1.3 + wp.x * 9.0 + wp.z * 7.0);
       transformed.x += (sway * 0.15 + 0.1) * position.y * position.y * bladeH;`,
    );
  };
  const GR = 3500;
  const grass = new THREE.InstancedMesh(blade, grassMat, GR);
  let gi = 0;
  for (let tries = 0; gi < GR && tries < GR * 6; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.9;
    const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
    if (!freeSpot(x, z, 0.05, 0.04)) continue;
    pv.set(x, groundAt(x, z) - 0.002, z);
    e.set((rnd() - 0.5) * 0.5, rnd() * Math.PI, (rnd() - 0.5) * 0.5);
    q.setFromEuler(e);
    sc.set(1, 0.012 + rnd() * 0.02, 1);
    m4.compose(pv, q, sc);
    grass.setMatrixAt(gi, m4);
    grass.setColorAt(gi, tmp.copy(MOSS[3]).lerp(MOSS[5], rnd()).multiplyScalar(0.8 + rnd() * 0.3));
    gi++;
  }
  grass.count = gi;
  grass.receiveShadow = true;
  group.add(grass);

  const mats: THREE.Material[] = [terrainMat, soil.material as THREE.Material, mossMat, pebbleMat, stoneMesh.material as THREE.Material, waterMat, fernMat, barkMat, leafMat, grassMat];

  return {
    group,
    groundAt,
    groundY,
    radius: edgeR,
    transparents: [water],
    update(t) {
      uTime.value = t;
      ripple.offset.set(t * 0.02, -t * 0.06);
    },
    setOpacity(o) {
      for (const m of mats) { m.transparent = o < 1 || m === waterMat; m.opacity = m === waterMat ? 0.92 * o : o; }
    },
  };
}
