import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { fbm3, makeNoise3, rng } from './textures';
import { cardMaterial, droopCard, leafClusterTexture, needleTexture } from './foliage';

/**
 * The world inside the globe, built like a real terrarium at golden hour:
 * a mossy mountain at the back with a waterfall cascading down its face
 * into a pool, a stream winding to the front, scanned stepping stones,
 * a gnarled tree with roots, a maple, pines, ferns, moss and grass, with
 * warm light shafts and mist.
 *
 * Ground and rock use scanned CC0 textures from Poly Haven (see
 * ATTRIBUTIONS.md), blended by slope with triplanar mapping so steep
 * cliffs don't stretch. Everything else is procedural or instanced.
 * Coordinates are local to the globe group; `c` is the sphere centre.
 */

export interface Interior {
  group: THREE.Group;
  groundAt(x: number, z: number): number;
  groundY: number;
  radius: number;
  update(t: number, camera?: THREE.Camera): void;
  setOpacity(o: number): void;
  transparents: THREE.Object3D[];
  /** Resolves when the lazy-loaded scanned assets are placed. */
  ready: Promise<void>;
}

type V2 = [number, number];
const C = (h: string) => new THREE.Color(h);

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

function taperedTube(curve: THREE.Curve<THREE.Vector3>, segs: number, r0: number, r1: number, radial: number, noise: (x: number, y: number, z: number) => number): THREE.BufferGeometry {
  const frames = curve.computeFrenetFrames(segs, false);
  const pos: number[] = [], idx: number[] = [], uv: number[] = [];
  const len = curve.getLength();
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const p = curve.getPointAt(t);
    const N = frames.normals[i], B = frames.binormals[i];
    const r = r0 + (r1 - r0) * Math.pow(t, 0.8);
    for (let j = 0; j <= radial; j++) {
      const a = (j / radial) * Math.PI * 2;
      const bump = 1 + noise(p.x * 60 + j * 0.3, p.y * 60, p.z * 60) * 0.3;
      const nx = Math.cos(a) * N.x + Math.sin(a) * B.x, ny = Math.cos(a) * N.y + Math.sin(a) * B.y, nz = Math.cos(a) * N.z + Math.sin(a) * B.z;
      pos.push(p.x + nx * r * bump, p.y + ny * r * bump, p.z + nz * r * bump);
      uv.push((j / radial) * Math.max(1, r0 * 60), t * len * 18);
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

/** Split a mesh into its connected pieces (the scanned rock sets hold several rocks). */
function splitComponents(g: THREE.BufferGeometry): THREE.BufferGeometry[] {
  const index = g.getIndex()!;
  const n = g.getAttribute('position').count;
  const parent = new Int32Array(n).map((_, i) => i);
  const find = (i: number): number => (parent[i] === i ? i : (parent[i] = find(parent[i])));
  for (let t = 0; t < index.count; t += 3) {
    const a = find(index.getX(t)), b = find(index.getX(t + 1)), c = find(index.getX(t + 2));
    parent[b] = a; parent[c] = a;
  }
  const groups = new Map<number, number[]>();
  for (let t = 0; t < index.count; t += 3) {
    const r = find(index.getX(t));
    let l = groups.get(r);
    if (!l) groups.set(r, (l = []));
    l.push(index.getX(t), index.getX(t + 1), index.getX(t + 2));
  }
  const out: THREE.BufferGeometry[] = [];
  for (const tris of groups.values()) {
    if (tris.length < 300) continue;
    const sub = g.clone();
    sub.setIndex(tris);
    out.push(sub);
  }
  return out;
}

const loader = new THREE.TextureLoader();
function tex(name: string, srgb: boolean, repeat = 1): THREE.Texture {
  const t = loader.load(`${import.meta.env.BASE_URL}textures/${name}.webp`);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = 8;
  t.repeat.set(repeat, repeat);
  return t;
}

/**
 * Terrain material: triplanar rock on steep faces, moss on gentle slopes,
 * pebbles where the vertex colour's blue channel marks the stream bed.
 */
function terrainMaterial(): THREE.MeshStandardMaterial {
  const rock = tex('mossy_rock_diff', true), rockN = tex('mossy_rock_nor', false);
  const moss = tex('aerial_grass_rock_diff', true), mossN = tex('aerial_grass_rock_nor', false);
  const peb = tex('ganges_river_pebbles_diff', true);
  const m = new THREE.MeshStandardMaterial({ roughness: 0.9, vertexColors: true });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, {
      tRock: { value: rock }, tRockN: { value: rockN }, tMoss: { value: moss }, tMossN: { value: mossN }, tPeb: { value: peb },
    });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vTP; varying vec3 vTN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvTP = position; vTN = normal;');
    sh.fragmentShader = sh.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform sampler2D tRock, tRockN, tMoss, tMossN, tPeb;
         varying vec3 vTP; varying vec3 vTN;
         vec4 tri(sampler2D t, vec3 p, vec3 w, float s) {
           return texture2D(t, p.zy * s) * w.x + texture2D(t, p.xz * s) * w.y + texture2D(t, p.xy * s) * w.z;
         }`,
      )
      .replace(
        '#include <map_fragment>',
        `vec3 tw = pow(abs(normalize(vTN)), vec3(4.0)); tw /= (tw.x + tw.y + tw.z);
         float slope = 1.0 - normalize(vTN).y;
         // Moss on gentle slopes, broken up so the transition isn't a clean line.
         float mossAmt = smoothstep(0.42, 0.22, slope + (tri(tRock, vTP, tw, 1.3).g - 0.45) * 0.5);
         vec3 rockC = tri(tRock, vTP, tw, 2.2).rgb * vec3(0.95, 0.93, 0.9);
         vec3 mossC = tri(tMoss, vTP, tw, 3.0).rgb;
         // Push the scanned ground toward deep, saturated moss greens.
         float ml = dot(mossC, vec3(0.333));
         mossC = mix(vec3(0.16, 0.25, 0.06), vec3(0.47, 0.6, 0.16), smoothstep(0.15, 0.6, ml)) * (0.7 + ml * 0.8);
         vec3 col = mix(rockC, mossC, mossAmt);
         // Vertex colour: r = darkening (damp/AO), b = pebble bed.
         col = mix(col, tri(tPeb, vTP, tw, 9.0).rgb * 0.8, vColor.b);
         col *= vColor.r;
         diffuseColor.rgb *= col;`,
      )
      .replace('#include <color_fragment>', '');
  };
  m.normalMap = rockN;
  m.normalScale.set(0.8, 0.8);
  return m;
}

export function buildInterior(c: THREE.Vector3, R: number): Interior {
  const group = new THREE.Group();
  const n3 = makeNoise3(41);
  const rnd = rng(9);
  const inner = R * 0.972;
  const depth = 0.55;
  const groundY = c.y - depth;
  const edgeR = Math.sqrt(inner * inner - depth * depth);

  // ---- layout (local x/z offsets from the centre)
  const M: V2 = [-0.16, -0.42]; // mountain peak
  const fallX = 0.02; // waterfall line on the mountain's front face
  const pool: V2 = [0.04, -0.06];
  const stream = smoothPath([pool, [0.16, 0.1], [0.12, 0.3], [0.28, 0.5], [0.24, 0.72]], 60);
  const steps = smoothPath([[-0.24, 0.72], [-0.2, 0.46], [-0.1, 0.24], [-0.05, 0.08]], 12);
  const treeAt: V2 = [-0.45, 0.2];

  // A craggy massif: three overlapping peaks with steep cliffs and moss ledges,
  // like cast-plaster rock in a real diorama (stepped strata, ridged erosion).
  const peaks: [number, number, number, number][] = [
    [M[0], M[1], 0.7, 0.42], [M[0] - 0.26, M[1] + 0.06, 0.48, 0.3], [M[0] + 0.3, M[1] - 0.02, 0.52, 0.32],
  ];
  const mountainH = (dx: number, dz: number) => {
    let h = 0;
    for (const [px, pz, ph, pr] of peaks) {
      const r = Math.hypot(dx - px, (dz - pz) * 1.1) / pr;
      if (r < 1) h = Math.max(h, ph * (1 - Math.pow(r, 1.4)) ** 1.15);
    }
    if (h <= 0) return 0;
    const ridged = 1 - Math.abs(fbm3(n3, dx * 6 + 7, 1, dz * 6, 4)) * 2;
    h *= 0.85 + ridged * 0.22;
    // Strata: flat ledges and near-vertical risers.
    const step = 0.05;
    const q = Math.floor(h / step) * step;
    h = q + Math.pow((h - q) / step, 4) * step;
    const notch = Math.exp(-((dx - fallX) ** 2) / 0.0012) * smoothstep(-0.36, -0.14, dz);
    return Math.max(0, h * (1 - notch * 0.25));
  };

  const groundAt = (x: number, z: number) => {
    const dx = x - c.x, dz = z - c.z;
    const r = Math.hypot(dx, dz) / edgeR;
    const edge = Math.max(0, 1 - Math.pow(Math.min(1, r), 6));
    let h = 0.03 + fbm3(n3, dx * 3.5, 0.5, dz * 3.5, 4) * 0.04;
    h += 0.05 * Math.exp(-((dx - treeAt[0]) ** 2 + (dz - treeAt[1]) ** 2) / 0.04); // knoll under the tree
    h += mountainH(dx, dz);
    const sd = polyDist(dx, dz, stream);
    h -= 0.03 * Math.exp(-(sd * sd) / 0.0025);
    h -= 0.035 * Math.exp(-((dx - pool[0]) ** 2 + (dz - pool[1]) ** 2) / 0.008);
    // Never poke through the glass.
    const y = groundY + h * edge;
    const maxY = c.y + Math.sqrt(Math.max(0, inner * inner * 0.9 - dx * dx - dz * dz));
    return Math.min(y, maxY);
  };

  // ---- terrain: one polar-grid mesh holds the meadow and the mountain
  const RINGS = 110, SEG = 300;
  const tPos: number[] = [], tCol: number[] = [], tIdx: number[] = [];
  const pushV = (x: number, z: number) => {
    const y = groundAt(x, z);
    tPos.push(x, y, z);
    const dx = x - c.x, dz = z - c.z;
    const sd = polyDist(dx, dz, stream);
    const pd = Math.hypot(dx - pool[0], dz - pool[1]);
    const bed = Math.max(THREE.MathUtils.clamp(1 - sd / 0.055, 0, 1), THREE.MathUtils.clamp(1 - pd / 0.11, 0, 1));
    // Darker in hollows and toward the glass; lighter on ridge tops.
    const rr = Math.hypot(dx, dz) / edgeR;
    const shade = 0.72 + fbm3(n3, x * 11, 2, z * 11, 3) * 0.35 - rr * rr * 0.12;
    tCol.push(shade, 0, bed);
  };
  pushV(c.x, c.z);
  for (let i = 1; i <= RINGS; i++) {
    const rr = Math.pow(i / RINGS, 0.9) * edgeR;
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
  tGeo.setIndex(tIdx);
  tGeo.computeVertexNormals();
  const shellMats: THREE.Material[] = [];
  const terrainMat = terrainMaterial();
  terrainMat.shadowSide = THREE.DoubleSide;
  const terrain = new THREE.Mesh(tGeo, terrainMat);
  terrain.receiveShadow = terrain.castShadow = true;
  group.add(terrain);

  // ---- moss shells (shell texturing): stacked offset copies of the ground,
  // each keeping only the strands taller than its height, so moss has volume.
  const SHELLS = 10;
  for (let L = 1; L <= SHELLS; L++) {
    const f = L / SHELLS;
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.9, side: THREE.DoubleSide, vertexColors: true });
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uF = { value: f };
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uF; varying vec3 vMP; varying vec3 vMN;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvMP = position; vMN = normal; transformed += normal * uF * 0.009;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform float uF; varying vec3 vMP; varying vec3 vMN;
          float hh(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
          float vn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
            return mix(mix(mix(hh(i), hh(i+vec3(1,0,0)), f.x), mix(hh(i+vec3(0,1,0)), hh(i+vec3(1,1,0)), f.x), f.y),
                       mix(mix(hh(i+vec3(0,0,1)), hh(i+vec3(1,0,1)), f.x), mix(hh(i+vec3(0,1,1)), hh(i+vec3(1,1,1)), f.x), f.y), f.z); }`)
        .replace('#include <color_fragment>', `
          float slope = 1.0 - normalize(vMN).y;
          float mpatch = vn(vMP * 9.0) * 0.7 + vn(vMP * 23.0) * 0.3;
          // Moss coverage: gentle slopes, not in the water, thinner on bare patches.
          float cover = smoothstep(0.5, 0.25, slope) * (1.0 - vColor.b) * smoothstep(0.25, 0.45, mpatch);
          // Strand height per cell: fine cells, lumpy cushions.
          float strand = hh(floor(vMP * 900.0)) * (0.55 + mpatch * 0.6) * cover;
          if (strand < uF) discard;
          vec3 deep = vec3(0.10, 0.2, 0.04), lime = vec3(0.42, 0.6, 0.12), gold = vec3(0.62, 0.58, 0.18), rust = vec3(0.45, 0.22, 0.08);
          float k = vn(vMP * 5.0 + 3.0);
          vec3 tipC = mix(lime, gold, smoothstep(0.55, 0.8, k));
          tipC = mix(tipC, rust, smoothstep(0.78, 0.9, vn(vMP * 7.0 + 11.0)));
          diffuseColor.rgb = mix(deep, tipC, uF) * (0.8 + hh(floor(vMP * 300.0)) * 0.35);`);
    };
    const shell = new THREE.Mesh(tGeo, mat);
    shell.receiveShadow = true;
    shell.castShadow = L === SHELLS / 2;
    group.add(shell);
    shellMats.push(mat);
  }

  // ---- soil cross-section with a gravel layer, seen through the glass
  const tmp = new THREE.Color();
  const th0 = Math.acos(-depth / inner);
  const soilGeo = new THREE.SphereGeometry(inner, 240, 40, 0, Math.PI * 2, th0, Math.PI - th0);
  const sp = soilGeo.getAttribute('position') as THREE.BufferAttribute;
  const sCol: number[] = [];
  for (let i = 0; i < sp.count; i++) {
    const x = sp.getX(i), y = sp.getY(i), z = sp.getZ(i);
    const d = (-depth - y) / (inner - depth);
    const wob = fbm3(n3, x * 4, y * 1.5, z * 4, 3) * 0.12;
    tmp.copy(C('#4a301a')).lerp(C('#2a1a0e'), THREE.MathUtils.clamp(0.5 + fbm3(n3, x * 7, y * 7, z * 7, 2), 0, 1));
    if (d + wob > 0.55) tmp.copy(C('#6f655b')).lerp(C('#c4b8a8'), THREE.MathUtils.clamp((fbm3(n3, x * 40, y * 40, z * 40, 2) + 0.5) * 1.3 - 0.1, 0, 1));
    if (d < 0.05) tmp.lerp(C('#2e4416'), 1 - d / 0.05);
    sCol.push(tmp.r, tmp.g, tmp.b);
  }
  soilGeo.setAttribute('color', new THREE.Float32BufferAttribute(sCol, 3));
  const soil = new THREE.Mesh(soilGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92 }));
  soil.position.copy(c);
  soil.receiveShadow = true;
  group.add(soil);

  const freeSpot = (x: number, z: number, clearStream = 0.06, maxSlope = 0.35) => {
    const dx = x - c.x, dz = z - c.z;
    if (Math.hypot(dx, dz) > edgeR * 0.93) return false;
    if (polyDist(dx, dz, stream) < clearStream) return false;
    if (Math.hypot(dx - pool[0], dz - pool[1]) < 0.12) return false;
    if (polyDist(dx, dz, steps) < 0.035) return false;
    const e = 0.01;
    const s = Math.hypot(groundAt(x + e, z) - groundAt(x - e, z), groundAt(x, z + e) - groundAt(x, z - e)) / (2 * e);
    return s < maxSlope;
  };

  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), pv = new THREE.Vector3(), e = new THREE.Euler();
  const uTime = { value: 0 };

  // ---- water: pool + stream surface (reflective, rippling)
  const ripple = tex('aerial_grass_rock_nor', false, 6);
  const waterMat = new THREE.MeshPhysicalMaterial({
    color: '#26403c', roughness: 0.03, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02,
    envMapIntensity: 2.2, normalMap: ripple, normalScale: new THREE.Vector2(0.12, 0.12),
    transparent: true, opacity: 0.88, side: THREE.DoubleSide, depthWrite: false,
  });
  const wPos: number[] = [], wIdx: number[] = [];
  const waterY = (x: number, z: number) => groundAt(x, z) + 0.008;
  for (let i = 0; i < stream.length; i++) {
    const [x, z] = stream[i];
    const [ax, az] = stream[Math.min(stream.length - 1, i + 1)], [bx, bz] = stream[Math.max(0, i - 1)];
    const tx = ax - bx, tz = az - bz, tl = Math.hypot(tx, tz) || 1;
    const w = 0.03 + Math.sin(i * 0.4) * 0.006;
    const y = Math.max(waterY(c.x + x, c.z + z), groundY + 0.004);
    for (const sgn of [-1, 1]) wPos.push(c.x + x + (-tz / tl) * w * sgn, y, c.z + z + (tx / tl) * w * sgn);
    if (i > 0) { const a = (i - 1) * 2; wIdx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const sGeo = new THREE.BufferGeometry();
  sGeo.setAttribute('position', new THREE.Float32BufferAttribute(wPos, 3));
  sGeo.setIndex(wIdx);
  sGeo.computeVertexNormals();
  const poolGeo = new THREE.CircleGeometry(0.1, 48);
  poolGeo.rotateX(-Math.PI / 2);
  poolGeo.deleteAttribute('uv');
  poolGeo.translate(c.x + pool[0], groundAt(c.x + pool[0], c.z + pool[1]) + 0.022, c.z + pool[1]);
  const water = new THREE.Mesh(mergeGeometries([sGeo.toNonIndexed(), poolGeo.toNonIndexed()]), waterMat);
  water.geometry.computeVertexNormals();
  water.renderOrder = 1;
  group.add(water);

  // ---- waterfall: a ribbon that follows the rock face down the notch
  const fallTop = -0.34, fallBottom = pool[1] - 0.05;
  const fPos: number[] = [], fUv: number[] = [], fIdx: number[] = [];
  const FS = 40;
  for (let i = 0; i <= FS; i++) {
    const t = i / FS;
    const dz = fallTop + (fallBottom - fallTop) * t;
    const w = 0.018 + t * 0.022;
    const y = groundAt(c.x + fallX, c.z + dz) + 0.012;
    for (const sgn of [-1, 1]) {
      fPos.push(c.x + fallX + sgn * w, y, c.z + dz + 0.006);
      fUv.push(sgn * 0.5 + 0.5, t);
    }
    if (i > 0) { const a = (i - 1) * 2; fIdx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const fGeo = new THREE.BufferGeometry();
  fGeo.setAttribute('position', new THREE.Float32BufferAttribute(fPos, 3));
  fGeo.setAttribute('uv', new THREE.Float32BufferAttribute(fUv, 2));
  fGeo.setIndex(fIdx);
  const fallMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: { uTime },
    vertexShader: /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: /* glsl */ `
      uniform float uTime; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
        return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
      void main(){
        float x = vUv.x;
        // Two noise scales scrolling at different speeds = falling water.
        float big = n(vec2(x * 9.0, vUv.y * 5.0 - uTime * 1.6));
        float small = n(vec2(x * 34.0, vUv.y * 22.0 - uTime * 4.2));
        float body = big * 0.6 + small * 0.4;
        // Hard-edged foam where the water breaks over ledges and at the bottom.
        float foamMask = smoothstep(0.55, 0.62, body + vUv.y * 0.25 - 0.08);
        float edge = smoothstep(0.0, 0.22, x + (small - 0.5) * 0.15) * smoothstep(1.0, 0.78, x - (small - 0.5) * 0.15);
        vec3 water = mix(vec3(0.33, 0.47, 0.48), vec3(0.62, 0.76, 0.78), big);
        vec3 col = mix(water, vec3(0.98, 1.0, 1.0), foamMask);
        float a = edge * mix(0.55, 0.95, foamMask);
        gl_FragColor = vec4(col, a);
      }`,
  });
  const SPRAY = 160;
  const sprayPos = new Float32Array(SPRAY * 3), spraySeed = new Float32Array(SPRAY);
  for (let k = 0; k < SPRAY; k++) spraySeed[k] = rnd();
  const sprayPts = new THREE.BufferGeometry();
  sprayPts.setAttribute('position', new THREE.BufferAttribute(sprayPos, 3));
  sprayPts.setAttribute('seed', new THREE.BufferAttribute(spraySeed, 1));
  const footY = groundAt(c.x + fallX, c.z + fallBottom);
  const foam = new THREE.Points(sprayPts, new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, uniforms: { uTime, uBase: { value: new THREE.Vector3(c.x + fallX, footY + 0.01, c.z + fallBottom) } },
    vertexShader: /* glsl */ `
      attribute float seed; uniform float uTime; uniform vec3 uBase; varying float vA;
      void main(){
        float t = fract(uTime * (0.5 + seed * 0.6) + seed * 7.0);
        float a = seed * 40.0;
        vec3 p = uBase + vec3(cos(a) * t * 0.05, t * (0.035 + seed * 0.03) - t * t * 0.04, sin(a) * t * 0.04 + 0.01);
        vA = (1.0 - t) * 0.8;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (2.0 + seed * 3.0) * 6.0 / -mv.z;
      }`,
    fragmentShader: /* glsl */ `varying float vA; void main(){ float d = length(gl_PointCoord - 0.5); gl_FragColor = vec4(1.0, 1.0, 1.0, smoothstep(0.5, 0.1, d) * vA); }`,
  }));
  foam.frustumCulled = false;
  group.add(foam);
  const fall = new THREE.Mesh(fGeo, fallMat);
  fall.renderOrder = 2;
  group.add(fall);

  // ---- mist and light shafts (soft additive cards)
  const softTex = (stops: [number, string][], w = 128, hgt = 128, linear = false) => {
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = hgt;
    const g = cv.getContext('2d')!;
    const gr = linear ? g.createLinearGradient(0, 0, w, 0) : g.createRadialGradient(w / 2, hgt / 2, 0, w / 2, hgt / 2, w / 2);
    for (const [o, col] of stops) gr.addColorStop(o, col);
    g.fillStyle = gr;
    g.fillRect(0, 0, w, hgt);
    if (linear) {
      // Fade along the length too.
      const v = g.createLinearGradient(0, 0, 0, hgt);
      v.addColorStop(0, 'rgba(0,0,0,1)'); v.addColorStop(0.15, 'rgba(0,0,0,0)'); v.addColorStop(0.7, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,1)');
      g.globalCompositeOperation = 'destination-out';
      g.fillStyle = v;
      g.fillRect(0, 0, w, hgt);
    }
    return new THREE.CanvasTexture(cv);
  };
  const mistTex = softTex([[0, 'rgba(255,240,220,0.7)'], [1, 'rgba(255,240,220,0)']]);
  const mists: THREE.Sprite[] = [];
  const mistSpots: [number, number, number, number][] = [
    [pool[0], pool[1], 0.05, 0.35], [-0.35, -0.1, 0.1, 0.6], [0.35, -0.2, 0.16, 0.5], [0.0, -0.45, 0.32, 0.7], [-0.1, 0.35, 0.05, 0.6],
  ];
  for (const [mx, mz, my, s] of mistSpots) {
    const sp2 = new THREE.Sprite(new THREE.SpriteMaterial({ map: mistTex, transparent: true, opacity: 0.2, depthWrite: false }));
    sp2.position.set(c.x + mx, groundAt(c.x + mx, c.z + mz) + my, c.z + mz);
    sp2.scale.set(s, s * 0.35, 1);
    sp2.userData.base = sp2.position.clone();
    sp2.userData.phase = rnd() * 10;
    mists.push(sp2);
    group.add(sp2);
  }
  const shaftTex = softTex([[0, 'rgba(255,214,150,0)'], [0.5, 'rgba(255,214,150,0.55)'], [1, 'rgba(255,214,150,0)']], 64, 256, true);
  const shafts: THREE.Mesh[] = [];
  const sunDir = new THREE.Vector3(0.55, -0.75, 0.35).normalize();
  for (let i = 0; i < 5; i++) {
    const len = 1.1, w = 0.06 + rnd() * 0.08;
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, len),
      new THREE.MeshBasicMaterial({ map: shaftTex, transparent: true, opacity: 0.16 + rnd() * 0.1, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    );
    const start = new THREE.Vector3(c.x - 0.45 + i * 0.14 + rnd() * 0.05, c.y + 0.45, c.z - 0.2 + rnd() * 0.2);
    m.position.copy(start).addScaledVector(sunDir, len / 2);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), sunDir.clone().negate());
    m.rotateY(rnd() * 0.6);
    m.userData.base = (m.material as THREE.MeshBasicMaterial).opacity;
    m.userData.phase = rnd() * 6;
    m.renderOrder = 3;
    shafts.push(m);
    group.add(m);
  }

  // ---- moss: dense fine tufts (not blobs), clustered colours incl. rust patches
  const tuft = new THREE.BufferGeometry();
  {
    const pos: number[] = [];
    const blades = 5;
    for (let k = 0; k < blades; k++) {
      const a = (k / blades) * Math.PI * 2;
      const ox = Math.cos(a), oz = Math.sin(a);
      const w = 0.09;
      // A short blade leaning outward.
      pos.push(-oz * w, 0, ox * w, oz * w, 0, -ox * w, ox * 0.45, 1, oz * 0.45);
    }
    tuft.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    tuft.computeVertexNormals();
    const nor = tuft.getAttribute('normal') as THREE.BufferAttribute;
    for (let i = 0; i < nor.count; i++) nor.setXYZ(i, nor.getX(i) * 0.4, 1, nor.getZ(i) * 0.4);
    nor.needsUpdate = true;
  }
  const mossMat = new THREE.MeshStandardMaterial({ roughness: 0.85, side: THREE.DoubleSide });
  mossMat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vH;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvH = position.y;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vH;').replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb *= mix(0.45, 1.25, vH);');
  };
  const MOSSN = 9000;
  const moss = new THREE.InstancedMesh(tuft, mossMat, MOSSN);
  const mossCols = {
    green: ['#4f8a18', '#6aa21e', '#3a6e12', '#8fb02a'].map(C),
    yellow: ['#a8b030', '#c4b83a', '#8a9a24'].map(C),
    rust: ['#8a4a1a', '#a85e22', '#6e3814'].map(C),
    deep: ['#2a4e12', '#335c16'].map(C),
  };
  let mi = 0;
  for (let tries = 0; mi < MOSSN && tries < MOSSN * 4; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.95;
    const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
    if (!freeSpot(x, z, 0.04, 0.9)) continue;
    const n1 = fbm3(n3, x * 7, 1, z * 7, 3), n2 = fbm3(n3, x * 13 + 5, 2, z * 13, 2);
    if (n1 + rnd() * 0.3 < -0.12) continue; // bare patches
    const pal = n2 > 0.22 ? mossCols.rust : n1 > 0.12 ? mossCols.yellow : n1 < -0.05 ? mossCols.deep : mossCols.green;
    const s = 0.008 + rnd() * 0.01 + Math.max(0, n1) * 0.012;
    pv.set(x, groundAt(x, z) - 0.001, z);
    e.set((rnd() - 0.5) * 0.4, rnd() * 6.28, (rnd() - 0.5) * 0.4);
    q.setFromEuler(e);
    sc.set(s * 1.4, s, s * 1.4);
    m4.compose(pv, q, sc);
    moss.setMatrixAt(mi, m4);
    moss.setColorAt(mi, tmp.copy(pal[Math.floor(rnd() * pal.length)]).multiplyScalar(0.85 + rnd() * 0.35));
    mi++;
  }
  moss.count = mi;
  moss.receiveShadow = true;
  group.add(moss);

  // ---- tiny white flowers in the moss
  const flowerGeo = (() => {
    const pos: number[] = [], col: number[] = [];
    const push = (x: number, y: number, z: number, cc: THREE.Color) => { pos.push(x, y, z); col.push(cc.r, cc.g, cc.b); };
    const stem = C('#5d8a2a'), petal = C('#f4f1e8'), eye = C('#e8c040');
    push(-0.03, 0, 0, stem); push(0.03, 0, 0, stem); push(0.02, 1, 0, stem);
    for (let k = 0; k < 5; k++) {
      const a = (k / 5) * Math.PI * 2, b = a + 0.5;
      push(0.02, 1, 0, eye); push(0.02 + Math.cos(a) * 0.22, 1.03, Math.sin(a) * 0.22, petal); push(0.02 + Math.cos(b) * 0.22, 1.03, Math.sin(b) * 0.22, petal);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals();
    const nor = g.getAttribute('normal') as THREE.BufferAttribute;
    for (let i = 0; i < nor.count; i++) nor.setXYZ(i, 0, 1, 0);
    return g;
  })();
  const flowerMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, side: THREE.DoubleSide, emissive: '#2a2618' });
  const FL = 700;
  const flowers = new THREE.InstancedMesh(flowerGeo, flowerMat, FL);
  let fl = 0;
  for (let cl = 0; cl < 24 && fl < FL; cl++) {
    const a = rnd() * 6.28, rr = 0.15 + rnd() * 0.7;
    const cx = c.x + Math.cos(a) * rr, cz = c.z + Math.sin(a) * rr;
    for (let k = 0; k < 30 && fl < FL; k++) {
      const x = cx + (rnd() - 0.5) * 0.09, z = cz + (rnd() - 0.5) * 0.09;
      if (!freeSpot(x, z, 0.05, 0.6)) continue;
      const hgt = 0.012 + rnd() * 0.018;
      pv.set(x, groundAt(x, z), z);
      e.set((rnd() - 0.5) * 0.4, rnd() * 6.28, (rnd() - 0.5) * 0.4);
      q.setFromEuler(e);
      sc.set(hgt * 0.32, hgt, hgt * 0.32);
      m4.compose(pv, q, sc);
      flowers.setMatrixAt(fl++, m4);
    }
  }
  flowers.count = fl;
  group.add(flowers);

  // ---- ferns
  const frondParts: number[] = [];
  {
    const leaflets = 16;
    const spine = (t: number) => new THREE.Vector3(t, Math.sin(t * Math.PI * 0.85) * 0.35 - t * t * 0.15, 0);
    for (let k = 1; k <= leaflets; k++) {
      const t = k / (leaflets + 1);
      const p0 = spine(t);
      const len = 0.26 * Math.sin(Math.PI * Math.min(1, t * 1.15)) + 0.03;
      for (const sgn of [-1, 1]) {
        const tip = p0.clone().add(new THREE.Vector3(len * 0.35, -len * 0.15, sgn * len));
        const a = spine(t - 0.022), b = spine(t + 0.022);
        frondParts.push(a.x, a.y, a.z, b.x, b.y, b.z, tip.x, tip.y, tip.z);
      }
    }
  }
  const frondGeo = new THREE.BufferGeometry();
  frondGeo.setAttribute('position', new THREE.Float32BufferAttribute(frondParts, 3));
  frondGeo.computeVertexNormals();
  const fernMat = new THREE.MeshStandardMaterial({ roughness: 0.6, side: THREE.DoubleSide });
  const FERN_SPOTS: V2[] = [[pool[0] - 0.14, pool[1] + 0.02], [pool[0] + 0.14, pool[1] + 0.04], [0.5, 0.05], [-0.3, 0.5], [0.42, 0.55], [-0.6, 0.0], [0.05, 0.62], [0.36, -0.12]];
  const ferns = new THREE.InstancedMesh(frondGeo, fernMat, FERN_SPOTS.length * 10);
  let fi = 0;
  for (const [fx, fz] of FERN_SPOTS) {
    const x = c.x + fx, z = c.z + fz;
    const y = groundAt(x, z);
    const size = 0.06 + rnd() * 0.04;
    for (let k = 0; k < 10; k++) {
      pv.set(x, y, z);
      e.set(0, (k / 10) * Math.PI * 2 + rnd() * 0.4, 0.3 + rnd() * 0.4, 'YZX');
      q.setFromEuler(e);
      const s = size * (0.7 + rnd() * 0.5);
      sc.set(s, s, s);
      m4.compose(pv, q, sc);
      ferns.setMatrixAt(fi, m4);
      ferns.setColorAt(fi, tmp.copy(C('#4d8a1e')).lerp(C('#9cc84a'), rnd() * 0.6));
      fi++;
    }
  }
  ferns.count = fi;
  ferns.castShadow = ferns.receiveShadow = true;
  group.add(ferns);

  // ---- trees
  const barkGeos: THREE.BufferGeometry[] = [];
  const pads: { p: THREE.Vector3; r: number; col: THREE.Color[] }[] = [];
  const green = ['#4f8a1e', '#6aa52c', '#3a6a18', '#8fbf3a'].map(C);
  const amber = ['#c8561a', '#e08a26', '#a83a14', '#f0b040'].map(C);

  const branch = (start: THREE.Vector3, dir: THREE.Vector3, len: number, r0: number, depthLeft: number, palette: THREE.Color[]) => {
    const pts = [start.clone()];
    const d = dir.clone();
    for (let i = 1; i <= 4; i++) {
      d.add(new THREE.Vector3((rnd() - 0.5) * 0.7, (rnd() - 0.3) * 0.3, (rnd() - 0.5) * 0.7)).normalize();
      pts.push(pts[i - 1].clone().addScaledVector(d, len / 4));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    barkGeos.push(taperedTube(curve, 10, r0, r0 * 0.55, 8, n3));
    const end = pts[pts.length - 1];
    if (depthLeft <= 0) {
      pads.push({ p: end.clone(), r: 0.045 + rnd() * 0.02, col: palette });
      return;
    }
    const kids = depthLeft >= 2 ? 3 : 2;
    for (let k = 0; k < kids; k++) {
      const a = (k / kids) * Math.PI * 2 + rnd() * 1.2;
      const nd = new THREE.Vector3(Math.cos(a), 0.25 + rnd() * 0.35, Math.sin(a)).add(d.clone().multiplyScalar(0.4)).normalize();
      branch(end, nd, len * (0.7 + rnd() * 0.15), r0 * 0.58, depthLeft - 1, palette);
    }

  };
  const tree = (at: V2, height: number, r0: number, palette: THREE.Color[], lean: THREE.Vector3) => {
    const x = c.x + at[0], z = c.z + at[1];
    const base = new THREE.Vector3(x, groundAt(x, z) - 0.01, z);
    for (let k = 0; k < 7; k++) {
      const a = (k / 7) * Math.PI * 2 + rnd() * 0.5;
      const pts = [
        base.clone().add(new THREE.Vector3(0, height * 0.14, 0)),
        base.clone().add(new THREE.Vector3(Math.cos(a) * r0 * 2.4, height * 0.04, Math.sin(a) * r0 * 2.4)),
        base.clone().add(new THREE.Vector3(Math.cos(a) * r0 * 5.5, -0.006, Math.sin(a) * r0 * 5.5)),
      ];
      barkGeos.push(taperedTube(new THREE.CatmullRomCurve3(pts), 8, r0 * 0.6, r0 * 0.12, 6, n3));
    }
    branch(base, lean.clone().normalize(), height * 0.55, r0, 3, palette);
  };
  tree(treeAt, 0.4, 0.028, green, new THREE.Vector3(0.45, 1, -0.1));
  tree([0.5, 0.18], 0.24, 0.013, amber, new THREE.Vector3(-0.2, 1, 0.1));

  // ---- conifers: trunk + tiers of drooping needle sprays (instanced)
  const sprayGeo = droopCard(0.3, 0.55);
  type Spray = { p: THREE.Vector3; yaw: number; tilt: number; len: number; tint: number };
  const sprays: Spray[] = [];
  const conifer = (x: number, z: number, h: number) => {
    const by = groundAt(x, z) - 0.01;
    // Keep the crown inside the glass.
    const topLim = c.y + Math.sqrt(Math.max(0, inner * inner * 0.88 - (x - c.x) ** 2 - (z - c.z) ** 2));
    h = Math.min(h, topLim - by);
    if (h < 0.06) return;
    const b = new THREE.Vector3(x, by, z);
    const lean = new THREE.Vector3((rnd() - 0.5) * 0.02, h, (rnd() - 0.5) * 0.02);
    const curve = new THREE.CatmullRomCurve3([b, b.clone().addScaledVector(lean, 0.5), b.clone().add(lean)]);
    barkGeos.push(taperedTube(curve, 8, 0.004 + h * 0.025, 0.001, 5, n3));
    const tiers = Math.round(10 + h * 40);
    const maxR = h * (0.3 + rnd() * 0.08);
    const tint = 0.75 + rnd() * 0.45;
    for (let w = 0; w < tiers; w++) {
      const t = 0.14 + (w / tiers) * 0.86;
      const rr = Math.pow(1 - t, 0.85) * maxR + 0.006;
      const per = Math.max(4, Math.round(5 + rr * 40));
      const p = curve.getPointAt(Math.min(1, t));
      for (let k = 0; k < per; k++) {
        sprays.push({ p: p.clone(), yaw: (k / per) * Math.PI * 2 + w * 2.4 + rnd() * 0.4, tilt: -0.15 - (1 - t) * 0.35 + (rnd() - 0.5) * 0.2, len: rr * (0.8 + rnd() * 0.45), tint: tint * (0.55 + t * 0.6) });
      }
    }
  };
  // A forest: dense on the mountain and around the back, thinning toward the front.
  const forestCount = 70;
  for (let i = 0, tries = 0; i < forestCount && tries < 2000; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.92;
    const dx = Math.cos(a) * rr, dz = Math.sin(a) * rr;
    const back = THREE.MathUtils.clamp(0.5 - dz, 0, 1.3);
    if (rnd() > back * 0.9) continue;
    if (Math.abs(dx - fallX) < 0.16 && dz > -0.42 && dz < 0.05) continue; // keep the falls and cliff visible
    if (mountainH(dx, dz) > 0.25 && rnd() < 0.5) continue; // bare crags near the top
    if (Math.hypot(dx - pool[0], dz - pool[1]) < 0.14 || polyDist(dx, dz, stream) < 0.07 || polyDist(dx, dz, steps) < 0.06) continue;
    if (Math.hypot(dx - treeAt[0], dz - treeAt[1]) < 0.16) continue;
    conifer(c.x + dx, c.z + dz, 0.12 + rnd() * 0.2 + back * 0.08);
    i++;
  }


  // Broadleaf foliage: leafy-twig cards arranged as cloud pads (bonsai style).
  const greenLeaves = cardMaterial(leafClusterTexture(['#4f8a1e', '#6aa52c', '#3a6a18', '#8fbf3a']), uTime, 0.06);
  const amberLeaves = cardMaterial(leafClusterTexture(['#c8561a', '#e08a26', '#a83a14', '#f0b040']), uTime, 0.06);
  const leafCard = droopCard(0.15, 1);
  const leafMat = greenLeaves;
  const PER_PAD = 90;
  void leafMat;
  for (const [mat, pal] of [[greenLeaves, green], [amberLeaves, amber]] as const) {
    const mine = pads.filter((p) => p.col === pal);
    const leaves = new THREE.InstancedMesh(leafCard, mat, mine.length * PER_PAD);
    let li = 0;
    for (const pad of mine) {
      for (let k = 0; k < PER_PAD; k++) {
        const u = rnd() * Math.PI * 2, rr = pad.r * Math.sqrt(rnd());
        // Dome-shaped cloud pad: higher in the middle, cards on top and sides.
        const dome = Math.sqrt(Math.max(0, 1 - (rr / pad.r) ** 2));
        const off = new THREE.Vector3(Math.cos(u) * rr, dome * pad.r * 0.75 * (0.3 + rnd() * 0.7) - pad.r * 0.15, Math.sin(u) * rr);
        pv.copy(pad.p).add(off);
        e.set(0, -u + (rnd() - 0.5) * 0.8, 0.5 - dome * 0.6 + (rnd() - 0.5) * 0.5, 'YZX');
        q.setFromEuler(e);
        const sz = 0.03 + rnd() * 0.02;
        sc.set(sz, sz, sz);
        m4.compose(pv.addScaledVector(new THREE.Vector3(Math.cos(u), 0, Math.sin(u)), -sz * 0.4), q, sc);
        leaves.setMatrixAt(li, m4);
        leaves.setColorAt(li, tmp.setScalar(0.7 + (off.y / pad.r) * 0.6 + rnd() * 0.2));
        li++;
      }
    }
    leaves.count = li;
    leaves.castShadow = leaves.receiveShadow = true;
    group.add(leaves);
  }

  const sprayMat = cardMaterial(needleTexture(), uTime, 0.03);
  const sprayMesh = new THREE.InstancedMesh(sprayGeo, sprayMat, sprays.length);
  sprays.forEach((sp, i) => {
    e.set(0, sp.yaw, sp.tilt, 'YZX');
    q.setFromEuler(e);
    sc.set(sp.len, sp.len, sp.len * 0.7);
    m4.compose(sp.p, q, sc);
    sprayMesh.setMatrixAt(i, m4);
    sprayMesh.setColorAt(i, tmp.setScalar(sp.tint * (0.85 + rnd() * 0.3)));
  });
  sprayMesh.castShadow = sprayMesh.receiveShadow = true;
  group.add(sprayMesh);

  // ---- a mossy fallen log by the stream
  {
    const a = new THREE.Vector3(c.x + 0.3, 0, c.z + 0.24), b = new THREE.Vector3(c.x + 0.52, 0, c.z + 0.36);
    a.y = groundAt(a.x, a.z) + 0.012; b.y = groundAt(b.x, b.z) + 0.016;
    const curve = new THREE.CatmullRomCurve3([a, a.clone().lerp(b, 0.5).add(new THREE.Vector3(0, 0.006, 0.01)), b]);
    barkGeos.push(taperedTube(curve, 14, 0.02, 0.016, 10, n3));
    // Moss along its top.
    for (let k = 0; k < 500 && mi < MOSSN; k++) {
      const t = rnd();
      const p = curve.getPointAt(t);
      const ang = (rnd() - 0.5) * 1.6;
      pv.set(p.x + Math.sin(ang) * 0.016 * 0.5, p.y + Math.cos(ang) * 0.018, p.z + Math.sin(ang) * 0.016);
      e.set(Math.sin(ang) * 0.8, rnd() * 6.28, 0);
      q.setFromEuler(e);
      const s = 0.006 + rnd() * 0.006;
      sc.set(s * 1.4, s, s * 1.4);
      m4.compose(pv, q, sc);
      moss.setMatrixAt(mi, m4);
      moss.setColorAt(mi, tmp.copy(mossCols.green[Math.floor(rnd() * 4)]).multiplyScalar(1.1));
      mi++;
    }
    moss.count = mi;
  }

  const barkMat = new THREE.MeshStandardMaterial({ map: tex('bark_brown_02_diff', true), normalMap: tex('bark_brown_02_nor', false), roughness: 0.95, color: '#c9b39a' });
  const bark = new THREE.Mesh(mergeGeometries(barkGeos.map((g) => (g.index ? g.toNonIndexed() : g))), barkMat);
  bark.castShadow = bark.receiveShadow = true;
  group.add(bark);

  // ---- grass, denser in the meadow, catching the low sun
  const blade = new THREE.BufferGeometry();
  blade.setAttribute('position', new THREE.Float32BufferAttribute([-0.0015, 0, 0, 0.0015, 0, 0, 0, 1, 0], 3));
  blade.setAttribute('normal', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 0, 0, 1], 3));
  const grassMat = new THREE.MeshStandardMaterial({ roughness: 0.7, side: THREE.DoubleSide });
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
  const GR = 6000;
  const grass = new THREE.InstancedMesh(blade, grassMat, GR);
  const grassCols = ['#7aa02a', '#9cb83a', '#c2b048', '#5e8a22'].map(C);
  let gi = 0;
  for (let tries = 0; gi < GR && tries < GR * 6; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.92;
    const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
    if (!freeSpot(x, z, 0.04, 0.5)) continue;
    pv.set(x, groundAt(x, z) - 0.002, z);
    e.set((rnd() - 0.5) * 0.5, rnd() * Math.PI, (rnd() - 0.5) * 0.5);
    q.setFromEuler(e);
    sc.set(1, 0.012 + rnd() * 0.024, 1);
    m4.compose(pv, q, sc);
    grass.setMatrixAt(gi, m4);
    grass.setColorAt(gi, tmp.copy(grassCols[Math.floor(rnd() * grassCols.length)]).multiplyScalar(0.8 + rnd() * 0.4));
    gi++;
  }
  grass.count = gi;
  grass.receiveShadow = true;
  group.add(grass);

  // ---- scanned rocks (lazy): stepping stones, boulders by the pool, scatter
  const rockMats: THREE.Material[] = [];
  const ready = (async () => {
    const gl = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
    const sets = await Promise.all(['rock_moss_set_01', 'rock_moss_set_02'].map((n) => gl.loadAsync(`/models/${n}.glb`)));
    const pieces: { geo: THREE.BufferGeometry; mat: THREE.Material; size: number }[] = [];
    for (const s of sets) {
      s.scene.updateMatrixWorld(true);
      s.scene.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const g = mesh.geometry.clone();
        g.applyMatrix4(mesh.matrixWorld);
        for (const part of splitComponents(g)) {
          part.computeBoundingBox();
          const bb = part.boundingBox!;
          const ctr = bb.getCenter(new THREE.Vector3());
          part.translate(-ctr.x, -bb.min.y, -ctr.z);
          const sz = bb.getSize(new THREE.Vector3());
          pieces.push({ geo: part, mat: mesh.material as THREE.Material, size: Math.max(sz.x, sz.z) });
        }
      });
    }
    if (!pieces.length) return;
    for (const p of pieces) rockMats.push(p.mat);
    const place = (x: number, z: number, size: number, flat: number) => {
      const p = pieces[Math.floor(rnd() * pieces.length)];
      const mesh = new THREE.Mesh(p.geo, p.mat);
      const k = size / p.size;
      mesh.scale.set(k, k * flat, k);
      mesh.rotation.y = rnd() * 6.28;
      mesh.position.set(x, groundAt(x, z) - size * 0.12 * flat, z);
      mesh.castShadow = mesh.receiveShadow = true;
      group.add(mesh);
    };
    // Stepping stones up the path to the pool.
    for (let i = 0; i < steps.length; i++) {
      const [sx, sz] = steps[i];
      place(c.x + sx + (rnd() - 0.5) * 0.01, c.z + sz, 0.045 + rnd() * 0.012, 0.35);
    }
    // Boulders framing the pool and the foot of the falls.
    const ring: V2[] = [[-0.12, -0.12], [0.16, -0.1], [-0.09, 0.03], [0.13, 0.04], [0.06, -0.17]];
    for (const [bx, bz] of ring) place(c.x + pool[0] + bx, c.z + pool[1] + bz, 0.05 + rnd() * 0.04, 0.8);
    // Along the stream and scattered in the meadow.
    for (let i = 6; i < stream.length; i += 7) {
      const [sx, sz] = stream[i];
      place(c.x + sx + (rnd() < 0.5 ? -1 : 1) * 0.05, c.z + sz, 0.025 + rnd() * 0.02, 0.6);
    }
    for (let i = 0; i < 10; i++) {
      const a = rnd() * 6.28, rr = 0.3 + rnd() * 0.45;
      const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
      if (freeSpot(x, z, 0.06, 0.5)) place(x, z, 0.02 + rnd() * 0.03, 0.7);
    }
  })().catch((err) => console.warn('Scanned rocks failed to load', err));

  const mats: THREE.Material[] = [terrainMat, soil.material as THREE.Material, mossMat, fernMat, barkMat, leafMat, amberLeaves, grassMat, sprayMat, flowerMat, ...shellMats];
  const transparents: THREE.Object3D[] = [water, fall, foam, ...mists, ...shafts];

  return {
    group,
    groundAt,
    groundY,
    radius: edgeR,
    transparents,
    ready: ready.then(() => undefined),
    update(t) {
      uTime.value = t;
      ripple.offset.set(t * 0.01, -t * 0.03);
      for (const s of mists) {
        const b = s.userData.base as THREE.Vector3;
        s.position.x = b.x + Math.sin(t * 0.08 + s.userData.phase) * 0.06;
        s.position.y = b.y + Math.sin(t * 0.13 + s.userData.phase) * 0.008;
      }
      for (const s of shafts) {
        (s.material as THREE.MeshBasicMaterial).opacity = s.userData.base * (0.75 + Math.sin(t * 0.35 + s.userData.phase) * 0.25);
      }
    },
    setOpacity(o) {
      for (const m of [...mats, ...rockMats]) { m.transparent = o < 1; m.opacity = o; }
    },
  };
}

function smoothstep(a: number, b: number, x: number) {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}
