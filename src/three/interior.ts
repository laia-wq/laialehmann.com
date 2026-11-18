import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { fbm3, fbmField, makeNoise3, normalMapFromField, rng } from './textures';

/**
 * Phase A interior: a mossy hill inside the globe with a visible soil
 * cross-section, stylised firs, mossy rocks, swaying grass and low mist.
 * All coordinates are local to the globe group; `c` is the sphere centre.
 */

export interface Interior {
  group: THREE.Group;
  /** Terrain height at local (x, z). */
  groundAt(x: number, z: number): number;
  groundY: number;
  radius: number;
  update(t: number): void;
  setOpacity(o: number): void;
  /** Transparent bits to hide from the AO pre-pass. */
  transparents: THREE.Object3D[];
}

const moss = [new THREE.Color('#3f5a2c'), new THREE.Color('#5b7a37'), new THREE.Color('#8a9a4c'), new THREE.Color('#2c3f22')];

export function buildInterior(c: THREE.Vector3, R: number): Interior {
  const group = new THREE.Group();
  const n3 = makeNoise3(41);
  const rnd = rng(9);
  const inner = R * 0.972;
  const depth = 0.46; // ground level below the centre
  const groundY = c.y - depth;
  const edgeR = Math.sqrt(inner * inner - depth * depth);

  // Height: a rise towards the back-left, a softer one right, gentle noise; flattens at the glass.
  const groundAt = (x: number, z: number) => {
    const dx = x - c.x, dz = z - c.z;
    const r = Math.hypot(dx, dz) / edgeR;
    const edge = Math.max(0, 1 - Math.pow(Math.min(1, r), 6));
    const hill = 0.2 * Math.exp(-((dx + 0.28) ** 2 + (dz + 0.3) ** 2) / 0.16) + 0.1 * Math.exp(-((dx - 0.45) ** 2 + (dz + 0.15) ** 2) / 0.09);
    const n = fbm3(n3, dx * 3.2, 0.5, dz * 3.2, 4) * 0.06;
    return groundY + (hill + n) * edge;
  };

  // ---- terrain (polar grid so the edge is a perfect circle against the glass)
  const RINGS = 70, SEG = 220;
  const tPos: number[] = [], tCol: number[] = [], tIdx: number[] = [], tUv: number[] = [];
  const tmp = new THREE.Color();
  tPos.push(c.x, groundAt(c.x, c.z), c.z);
  tCol.push(...moss[1].toArray());
  tUv.push(0.5, 0.5);
  for (let i = 1; i <= RINGS; i++) {
    const rr = (i / RINGS) * edgeR;
    for (let j = 0; j < SEG; j++) {
      const a = (j / SEG) * Math.PI * 2;
      const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
      const y = groundAt(x, z);
      tPos.push(x, y, z);
      const v = fbm3(n3, x * 6, 3, z * 6, 3) + 0.5;
      const hgt = (y - groundY) / 0.22;
      tmp.copy(moss[0]).lerp(moss[1], THREE.MathUtils.clamp(v, 0, 1)).lerp(moss[2], THREE.MathUtils.clamp(hgt * 0.6 + (v - 0.6), 0, 0.6)).lerp(moss[3], THREE.MathUtils.clamp(0.4 - hgt, 0, 0.4));
      tCol.push(tmp.r, tmp.g, tmp.b);
      tUv.push(x * 2, z * 2);
    }
  }
  for (let j = 0; j < SEG; j++) tIdx.push(0, 1 + ((j + 1) % SEG), 1 + j);
  for (let i = 1; i < RINGS; i++) {
    for (let j = 0; j < SEG; j++) {
      const a = 1 + (i - 1) * SEG + j, b = 1 + (i - 1) * SEG + ((j + 1) % SEG);
      const cc = a + SEG, d = b + SEG;
      tIdx.push(a, b, d, a, d, cc);
    }
  }
  const tGeo = new THREE.BufferGeometry();
  tGeo.setAttribute('position', new THREE.Float32BufferAttribute(tPos, 3));
  tGeo.setAttribute('color', new THREE.Float32BufferAttribute(tCol, 3));
  tGeo.setAttribute('uv', new THREE.Float32BufferAttribute(tUv, 2));
  tGeo.setIndex(tIdx);
  tGeo.computeVertexNormals();
  const fine = fbmField(256, 32, 4, 44);
  const mossNormal = normalMapFromField(fine, 256, 256, 2.2);
  mossNormal.wrapT = THREE.RepeatWrapping;
  const terrainMat = new THREE.MeshPhysicalMaterial({
    vertexColors: true,
    roughness: 0.92,
    normalMap: mossNormal,
    normalScale: new THREE.Vector2(0.8, 0.8),
    sheen: 0.6,
    sheenRoughness: 0.7,
    sheenColor: new THREE.Color('#b6c98a'),
  });
  terrainMat.shadowSide = THREE.DoubleSide;
  const terrain = new THREE.Mesh(tGeo, terrainMat);
  terrain.receiveShadow = true;
  terrain.castShadow = true;
  group.add(terrain);

  // ---- soil cross-section: the part of an inner sphere below the ground, in strata
  const th0 = Math.acos(-depth / inner);
  const soilGeo = new THREE.SphereGeometry(inner, 160, 40, 0, Math.PI * 2, th0, Math.PI - th0);
  const sp = soilGeo.getAttribute('position') as THREE.BufferAttribute;
  const sCol: number[] = [];
  const loam = new THREE.Color('#3b2a1d'), clayC = new THREE.Color('#6b4a30'), rock = new THREE.Color('#5d5750'), mossTop = new THREE.Color('#3f5a2c');
  for (let i = 0; i < sp.count; i++) {
    const x = sp.getX(i), y = sp.getY(i), z = sp.getZ(i);
    const d = (-depth - y) / (inner - depth); // 0 at ground, 1 at bottom
    const wob = fbm3(n3, x * 5, y * 2, z * 5, 3) * 0.25;
    const band = Math.sin((d + wob) * 9) * 0.5 + 0.5;
    tmp.copy(loam).lerp(clayC, band * 0.5).lerp(rock, THREE.MathUtils.clamp((d - 0.45 + wob) * 2, 0, 0.8));
    if (d < 0.05) tmp.lerp(mossTop, 1 - d / 0.05);
    const pebble = fbm3(n3, x * 12, y * 12, z * 12, 2);
    tmp.multiplyScalar(0.9 + pebble * 0.3);
    sCol.push(tmp.r, tmp.g, tmp.b);
  }
  soilGeo.setAttribute('color', new THREE.Float32BufferAttribute(sCol, 3));
  const soil = new THREE.Mesh(soilGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, normalMap: mossNormal, normalScale: new THREE.Vector2(0.5, 0.5) }));
  soil.position.copy(c);
  soil.receiveShadow = true;
  group.add(soil);

  // ---- firs: layered, jittered cones merged into one geometry with vertex colours
  const firGeos: THREE.BufferGeometry[] = [];
  const firSpots: [number, number, number][] = [
    [-0.38, -0.42, 1.0], [-0.18, -0.55, 0.85], [-0.55, -0.12, 0.75], [-0.05, -0.32, 0.6], [0.42, -0.4, 0.72],
    [0.58, -0.05, 0.55], [-0.62, -0.38, 0.62], [0.22, -0.62, 0.5], [0.3, -0.28, 0.42],
  ];
  const needle = new THREE.Color('#24382a'), needleLit = new THREE.Color('#3e5a3a');
  for (const [fx, fz, s] of firSpots) {
    const x = c.x + fx, z = c.z + fz;
    const base = groundAt(x, z);
    const h = 0.42 * s;
    const tiers = 7;
    const parts: THREE.BufferGeometry[] = [];
    const trunk = new THREE.CylinderGeometry(0.008 * s, 0.014 * s, h * 0.35, 6);
    trunk.translate(0, h * 0.17, 0);
    paint(trunk, new THREE.Color('#3a2a1e'));
    parts.push(trunk);
    for (let k = 0; k < tiers; k++) {
      const t = k / (tiers - 1);
      const rad = (0.115 - t * 0.09) * s;
      const ch = h * (0.28 - t * 0.1);
      const cone = new THREE.ConeGeometry(rad, ch, 22, 5, false);
      const y0 = h * (0.22 + t * 0.62);
      cone.rotateY(rnd() * Math.PI);
      const p = cone.getAttribute('position') as THREE.BufferAttribute;
      const cols: number[] = [];
      for (let i = 0; i < p.count; i++) {
        const vx = p.getX(i), vy = p.getY(i), vz = p.getZ(i);
        const jag = 1 + (fbm3(n3, vx * 60 + k, vy * 60, vz * 60, 2)) * 0.35;
        // Drooping, ragged lower edge.
        const lower = vy < -ch * 0.3 ? 1 : 0;
        p.setXYZ(i, vx * jag, vy - lower * Math.abs(vx * vz) * 4, vz * jag);
        // Volume: tips and outer edges catch the light, the core is dark;
        // upward-facing needles hold a dusting of snow.
        const outer = THREE.MathUtils.clamp(Math.hypot(vx, vz) / Math.max(rad, 1e-4), 0, 1);
        const lit = THREE.MathUtils.clamp(0.35 + vx * 4 + vz * 2, 0, 1);
        const cc = needle.clone().multiplyScalar(0.55 + outer * 0.6).lerp(needleLit, lit * 0.5 * outer + rnd() * 0.1);
        if (vy > -ch * 0.1 && outer > 0.35 && rnd() < 0.45) cc.lerp(new THREE.Color('#eef1f2'), 0.55 + rnd() * 0.3);
        cols.push(cc.r, cc.g, cc.b);
      }
      cone.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
      cone.computeVertexNormals();
      cone.translate(0, y0, 0);
      parts.push(cone);
    }
    const tree = mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
    tree.rotateZ((rnd() - 0.5) * 0.06);
    tree.translate(x, base - 0.01, z);
    firGeos.push(tree);
  }
  const firs = new THREE.Mesh(mergeGeometries(firGeos), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide, normalMap: mossNormal, normalScale: new THREE.Vector2(1.5, 1.5) }));
  firs.castShadow = true;
  firs.receiveShadow = true;
  group.add(firs);

  // ---- mossy rocks
  const rockGeos: THREE.BufferGeometry[] = [];
  const rockSpots: [number, number, number][] = [[0.18, 0.28, 0.07], [0.26, 0.2, 0.04], [-0.3, 0.22, 0.05], [0.5, 0.25, 0.035], [-0.12, 0.5, 0.03]];
  for (const [rx, rz, s] of rockSpots) {
    const g = new THREE.IcosahedronGeometry(s, 3);
    const p = g.getAttribute('position') as THREE.BufferAttribute;
    const cols: number[] = [];
    for (let i = 0; i < p.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(p, i);
      const d = 1 + fbm3(n3, v.x * 18 + rx * 10, v.y * 18, v.z * 18, 4) * 0.7;
      v.multiplyScalar(d);
      v.y *= 0.62;
      p.setXYZ(i, v.x, v.y, v.z);
      const up = v.clone().normalize().y;
      const cc = new THREE.Color('#6d6a63').lerp(new THREE.Color('#8a8379'), rnd() * 0.5).lerp(moss[1], THREE.MathUtils.clamp((up - 0.35) * 2.2, 0, 1));
      cols.push(cc.r, cc.g, cc.b);
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    g.computeVertexNormals();
    const x = c.x + rx, z = c.z + rz;
    g.rotateY(rnd() * 6);
    g.translate(x, groundAt(x, z) + s * 0.15, z);
    rockGeos.push(g.index ? g.toNonIndexed() : g);
  }
  const rocks = new THREE.Mesh(mergeGeometries(rockGeos), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 }));
  rocks.castShadow = rocks.receiveShadow = true;
  group.add(rocks);

  // ---- grass: instanced tapered blades that sway
  const blade = new THREE.BufferGeometry();
  blade.setAttribute('position', new THREE.Float32BufferAttribute([-0.0022, 0, 0, 0.0022, 0, 0, -0.0013, 0.5, 0, 0.0013, 0.5, 0, 0, 1, 0], 3));
  blade.setAttribute('normal', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1], 3));
  blade.setIndex([0, 1, 3, 0, 3, 2, 2, 3, 4]);
  const COUNT = 16000;
  const grassMat = new THREE.MeshStandardMaterial({ vertexColors: false, roughness: 0.8, side: THREE.DoubleSide });
  const uTime = { value: 0 };
  grassMat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = uTime;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTime;')
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
         vec4 wp = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
         // Blade height lives in the instance's y scale; x/z are unscaled,
         // so the bend must be expressed in world units of that height.
         float bladeH = length(instanceMatrix[1].xyz);
         float sway = sin(uTime * 1.3 + wp.x * 9.0 + wp.z * 7.0) * 0.5 + sin(uTime * 2.1 + wp.z * 13.0) * 0.25;
         float bend = position.y * position.y * bladeH;
         transformed.x += (sway * 0.22 + 0.12) * bend;
         transformed.z += sway * 0.1 * bend;`,
      );
  };
  const grass = new THREE.InstancedMesh(blade, grassMat, COUNT);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), pv = new THREE.Vector3();
  const gc = new THREE.Color();
  let placed = 0;
  for (let tries = 0; placed < COUNT && tries < COUNT * 4; tries++) {
    const a = rnd() * Math.PI * 2, rr = Math.sqrt(rnd()) * edgeR * 0.9;
    const x = c.x + Math.cos(a) * rr, z = c.z + Math.sin(a) * rr;
    // Clumpy distribution.
    if (fbm3(n3, x * 7, 9, z * 7, 2) + rnd() * 0.25 < 0.05) continue;
    pv.set(x, groundAt(x, z) - 0.002, z);
    q.setFromEuler(new THREE.Euler((rnd() - 0.5) * 0.5, rnd() * Math.PI, (rnd() - 0.5) * 0.5));
    const hgt = 0.012 + rnd() * 0.022;
    sc.set(1 + rnd(), hgt, 1);
    m.compose(pv, q, sc);
    grass.setMatrixAt(placed, m);
    gc.copy(moss[1]).lerp(moss[2], rnd() * 0.9).lerp(moss[0], rnd() * 0.4);
    grass.setColorAt(placed, gc);
    placed++;
  }
  grass.count = placed;
  grass.receiveShadow = true;
  group.add(grass);

  // ---- low mist: a few soft billboards
  const mistTex = (() => {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 128;
    const g = cv.getContext('2d')!;
    const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,250,240,0.55)');
    gr.addColorStop(1, 'rgba(255,250,240,0)');
    g.fillStyle = gr;
    g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(cv);
  })();
  const mists: THREE.Sprite[] = [];
  for (let i = 0; i < 6; i++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: mistTex, transparent: true, opacity: 0.12, depthWrite: false }));
    const a = rnd() * Math.PI * 2, rr = rnd() * 0.5;
    s.position.set(c.x + Math.cos(a) * rr, groundY + 0.08 + rnd() * 0.08, c.z + Math.sin(a) * rr - 0.15);
    s.scale.set(0.7 + rnd() * 0.4, 0.22 + rnd() * 0.1, 1);
    s.userData.base = s.position.clone();
    s.userData.phase = rnd() * 10;
    mists.push(s);
    group.add(s);
  }

  const mats = [terrainMat, soil.material as THREE.Material, firs.material as THREE.Material, rocks.material as THREE.Material, grassMat];

  return {
    group,
    groundAt,
    groundY,
    radius: edgeR,
    transparents: mists,
    update(t) {
      uTime.value = t;
      for (const s of mists) {
        const b = s.userData.base as THREE.Vector3;
        s.position.x = b.x + Math.sin(t * 0.07 + s.userData.phase) * 0.12;
        s.position.y = b.y + Math.sin(t * 0.11 + s.userData.phase) * 0.01;
      }
    },
    setOpacity(o) {
      for (const mm of mats) { mm.transparent = o < 1; mm.opacity = o; }
      for (const s of mists) s.material.opacity = 0.12 * o;
    },
  };
}

function paint(g: THREE.BufferGeometry, color: THREE.Color) {
  const n = g.getAttribute('position').count;
  const cols = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { cols[i * 3] = color.r; cols[i * 3 + 1] = color.g; cols[i * 3 + 2] = color.b; }
  g.setAttribute('color', new THREE.BufferAttribute(cols, 3));
}
