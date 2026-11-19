import * as THREE from 'three';
import { ConvexHull } from 'three/examples/jsm/math/ConvexHull.js';

/**
 * Splits the glass sphere into shards with a spherical Voronoi diagram whose
 * seeds cluster around the impact point (small shards where it was struck,
 * large ones far away). Each shard is a real slab of glass with an inner
 * face and side walls, so edges catch the light as it tumbles.
 *
 * Also returns the crack network: every edge shared by two shards, tagged
 * with its angular distance from the impact so cracks can grow outward.
 */

export interface Shard {
  geometry: THREE.BufferGeometry;
  /** Centroid in globe-local coords (mesh origin). */
  center: THREE.Vector3;
  /** Outward unit normal at the centroid. */
  normal: THREE.Vector3;
  /** Angular distance from impact, radians. */
  angle: number;
  /** Sample points (relative to centre) used for ground contact. */
  hull: THREE.Vector3[];
  radius: number;
  area: number;
  neighbors: Set<number>;
}

export interface Fracture {
  shards: Shard[];
  cracks: THREE.BufferGeometry;
}

export interface FractureOptions {
  radius: number;
  thickness: number;
  /** Local-space centre of the globe. */
  center: THREE.Vector3;
  /** Unit vector from centre to the impact point. */
  impact: THREE.Vector3;
  /** Triangles whose centroid is below this local y (relative to centre) are dropped (hidden by the collar). */
  cutY: number;
  rng?: () => number;
}

function mulberry(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function fractureSphere(opt: FractureOptions): Fracture {
  const rnd = opt.rng ?? mulberry(7);
  const R = opt.radius;
  const T = opt.thickness;
  const impact = opt.impact.clone().normalize();
  const cut = opt.cutY;

  // 1. Seeds. Near the impact they sit on a jittered polar grid (rays x rings),
  //    which gives the spider-web look of struck glass; elsewhere an even spread.
  const seeds: THREE.Vector3[] = [impact.clone()];
  const tangent = new THREE.Vector3(0, 1, 0).cross(impact);
  if (tangent.lengthSq() < 1e-4) tangent.set(1, 0, 0);
  tangent.normalize();
  const bitangent = impact.clone().cross(tangent);
  const rings = [0.1, 0.22, 0.37, 0.56, 0.8, 1.1];
  rings.forEach((ringAngle, ri) => {
    const count = ri === 0 ? 7 : ri === 1 ? 9 : 11;
    for (let k = 0; k < count; k++) {
      const phi = ((k + (rnd() - 0.5) * 0.45 + (ri % 2) * 0.5) / count) * Math.PI * 2;
      const ang = ringAngle * (0.9 + rnd() * 0.2);
      seeds.push(
        impact.clone().multiplyScalar(Math.cos(ang))
          .addScaledVector(tangent, Math.sin(ang) * Math.cos(phi))
          .addScaledVector(bitangent, Math.sin(ang) * Math.sin(phi))
          .normalize(),
      );
    }
  });
  const far = 64;
  for (let i = 0; i < far; i++) {
    const y = 1 - (2 * (i + 0.5)) / far;
    const r = Math.sqrt(1 - y * y);
    const th = i * 2.399963 + rnd() * 0.6;
    const v = new THREE.Vector3(Math.cos(th) * r, y, Math.sin(th) * r).normalize();
    if (v.angleTo(impact) > 1.25) seeds.push(v);
  }

  // 2. Spherical Voronoi via the convex hull: each hull triangle's outward
  //    normal is a Voronoi vertex shared by its three seeds.
  const hull = new ConvexHull().setFromPoints(seeds);
  const seedIndex = new Map<THREE.Vector3, number>();
  seeds.forEach((s, i) => seedIndex.set(s, i));
  const faces = hull.faces.map((f) => {
    const ids: number[] = [];
    for (let e = 0; e < 3; e++) ids.push(seedIndex.get(f.getEdge(e).head().point)!);
    return { n: f.normal.clone().normalize(), ids };
  });
  const facesOf: number[][] = seeds.map(() => []);
  faces.forEach((f, fi) => f.ids.forEach((id) => facesOf[id].push(fi)));

  // Order each cell's vertices around its seed.
  const ring = (si: number) => {
    const s = seeds[si];
    const t = new THREE.Vector3(0, 1, 0).cross(s);
    if (t.lengthSq() < 1e-4) t.set(1, 0, 0);
    t.normalize();
    const b = s.clone().cross(t);
    return facesOf[si]
      .map((fi) => ({ fi, a: Math.atan2(faces[fi].n.dot(b), faces[fi].n.dot(t)) }))
      .sort((x, y) => x.a - y.a)
      .map((x) => x.fi);
  };

  // 3. Each Voronoi edge is subdivided and gently wobbled, deterministically
  //    per edge so both neighbouring shards get exactly the same border.
  const SUB = 5;
  const edgeCache = new Map<string, THREE.Vector3[]>();
  const edgePoints = (fa: number, fb: number): THREE.Vector3[] => {
    const lo = Math.min(fa, fb), hi = Math.max(fa, fb);
    const k = `${lo}_${hi}`;
    let pts = edgeCache.get(k);
    if (!pts) {
      const a = faces[lo].n, b = faces[hi].n;
      const side = a.clone().cross(b).normalize();
      const len = a.angleTo(b);
      let h = (lo * 73856093) ^ (hi * 19349663);
      const r = () => ((h = (h * 16807) % 2147483647) / 2147483647 + 1) % 1;
      pts = [a.clone()];
      for (let i = 1; i < SUB; i++) {
        const t = i / SUB;
        const p = a.clone().lerp(b, t).normalize();
        p.addScaledVector(side, (r() - 0.5) * len * 0.12 * Math.sin(Math.PI * t)).normalize();
        pts.push(p);
      }
      pts.push(b.clone());
      edgeCache.set(k, pts);
    }
    return lo === fa ? pts : [...pts].reverse();
  };

  const onCut = (p: THREE.Vector3) => {
    const r = Math.sqrt(1 - cut * cut);
    const l = Math.hypot(p.x, p.z) || 1;
    return new THREE.Vector3((p.x / l) * r, cut, (p.z / l) * r);
  };

  const neighborsOf: Set<number>[] = seeds.map(() => new Set<number>());
  const crackPos: number[] = [];
  const crackDist: number[] = [];
  const crackSide: number[] = [];
  const crackDone = new Set<string>();
  const angleFromImpact = (v: THREE.Vector3) => Math.acos(THREE.MathUtils.clamp(v.dot(impact), -1, 1));

  const addCrack = (pts: THREE.Vector3[]) => {
    for (let i = 0; i < pts.length - 1; i++) {
      const vi = pts[i], vj = pts[i + 1];
      if (vi.y < cut + 0.01 || vj.y < cut + 0.01) continue;
      const mid = vi.clone().add(vj).normalize();
      const along = vj.clone().sub(vi).normalize();
      const side = along.cross(mid).normalize();
      const p1 = vi.clone().multiplyScalar(R * 1.0015).add(opt.center);
      const p2 = vj.clone().multiplyScalar(R * 1.0015).add(opt.center);
      const d1 = angleFromImpact(vi), d2 = angleFromImpact(vj);
      const quad = [p1, p2, p1, p1, p2, p2];
      const dist = [d1, d2, d1, d1, d2, d2];
      const sign = [-1, -1, 1, 1, -1, 1];
      for (let q = 0; q < 6; q++) {
        crackPos.push(quad[q].x, quad[q].y, quad[q].z);
        crackDist.push(dist[q]);
        crackSide.push(sign[q], side.x, side.y, side.z);
      }
    }
  };

  const shards: Shard[] = [];
  const shardOfSeed = new Map<number, number>();

  seeds.forEach((seed, si) => {
    const order = ring(si);
    if (order.length < 3) return;
    // Dense boundary polygon.
    let poly: THREE.Vector3[] = [];
    for (let k = 0; k < order.length; k++) {
      const fa = order[k], fb = order[(k + 1) % order.length];
      const pts = edgePoints(fa, fb);
      poly.push(...pts.slice(0, -1));
      // Neighbour across this edge: the other seed shared by both faces.
      const nb = faces[fa].ids.find((id) => id !== si && faces[fb].ids.includes(id));
      if (nb !== undefined) {
        neighborsOf[si].add(nb);
        const key = si < nb ? `${si}_${nb}` : `${nb}_${si}`;
        if (!crackDone.has(key)) { crackDone.add(key); addCrack(pts); }
      }
    }
    // Clip against the collar plane (Sutherland-Hodgman, keep y >= cut).
    if (poly.every((p) => p.y < cut)) return;
    if (poly.some((p) => p.y < cut)) {
      const out: THREE.Vector3[] = [];
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const ina = a.y >= cut, inb = b.y >= cut;
        if (ina) out.push(a);
        if (ina !== inb) out.push(onCut(a.clone().lerp(b, (cut - a.y) / (b.y - a.y))));
      }
      // Densify the new flat edge along the cut circle.
      poly = [];
      for (let i = 0; i < out.length; i++) {
        const a = out[i], b = out[(i + 1) % out.length];
        poly.push(a);
        if (Math.abs(a.y - cut) < 1e-6 && Math.abs(b.y - cut) < 1e-6) {
          for (let k = 1; k < 4; k++) poly.push(onCut(a.clone().lerp(b, k / 4)));
        }
      }
    }
    if (poly.length < 3) return;

    // Cell centre (on the sphere).
    const c = new THREE.Vector3();
    poly.forEach((p) => c.add(p));
    c.normalize();
    if (c.y < cut) c.copy(seed);
    const normal = c.clone();
    const center = normal.clone().multiplyScalar(R - T * 0.5).add(opt.center);

    const pos: number[] = [], nor: number[] = [], spos: number[] = [], snor: number[] = [];
    const put = (arrP: number[], arrN: number[], v: THREE.Vector3, n: THREE.Vector3) => {
      arrP.push(v.x - center.x, v.y - center.y, v.z - center.z);
      arrN.push(n.x, n.y, n.z);
    };
    const outer = (v: THREE.Vector3) => v.clone().multiplyScalar(R).add(opt.center);
    const inner = (v: THREE.Vector3) => v.clone().multiplyScalar(R - T).add(opt.center);

    // Fan from the centre with two radial rings so the curvature is kept.
    const RINGS = 3;
    const ringPt = (p: THREE.Vector3, k: number) => (k === 0 ? c.clone() : c.clone().lerp(p, k / RINGS).normalize());
    let area = 0;
    for (let i = 0; i < poly.length; i++) {
      const pa = poly[i], pb = poly[(i + 1) % poly.length];
      for (let k = 0; k < RINGS; k++) {
        const a0 = ringPt(pa, k), b0 = ringPt(pb, k), a1 = ringPt(pa, k + 1), b1 = ringPt(pb, k + 1);
        const tris = k === 0 ? [[a0, a1, b1]] : [[a0, a1, b1], [a0, b1, b0]];
        for (const [x, y, z] of tris) {
          // Ensure outward winding.
          const nrm = y.clone().sub(x).cross(z.clone().sub(x));
          const [p, q, r] = nrm.dot(x) >= 0 ? [x, y, z] : [x, z, y];
          area += nrm.length() * 0.5;
          put(pos, nor, outer(p), p); put(pos, nor, outer(q), q); put(pos, nor, outer(r), r);
          put(pos, nor, inner(p), p.clone().negate()); put(pos, nor, inner(r), r.clone().negate()); put(pos, nor, inner(q), q.clone().negate());
        }
      }
      // Side wall.
      const o1 = outer(pa), o2 = outer(pb), i1 = inner(pa), i2 = inner(pb);
      const n = o2.clone().sub(o1).cross(i1.clone().sub(o1)).normalize();
      const mid = pa.clone().add(pb).normalize();
      const outwards = mid.clone().sub(c);
      const flip = n.dot(outwards) < 0;
      if (flip) n.negate();
      const quad = flip ? [o1, i1, o2, i1, i2, o2] : [o1, o2, i1, i1, o2, i2];
      for (const q of quad) put(spos, snor, q, n);
    }

    const geometry = new THREE.BufferGeometry();
    const faceVerts = pos.length / 3;
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos.concat(spos), 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(nor.concat(snor), 3));
    geometry.addGroup(0, faceVerts, 0);
    geometry.addGroup(faceVerts, spos.length / 3, 1);
    geometry.computeBoundingSphere();

    const hullPts: THREE.Vector3[] = [];
    const stride = Math.max(1, Math.floor(poly.length / 10));
    for (let i = 0; i < poly.length; i += stride) hullPts.push(outer(poly[i]).sub(center));
    hullPts.push(normal.clone().multiplyScalar(T * 0.5), normal.clone().multiplyScalar(-T * 0.5));

    shardOfSeed.set(si, shards.length);
    shards.push({
      geometry,
      center,
      normal,
      angle: angleFromImpact(normal),
      hull: hullPts,
      radius: geometry.boundingSphere!.radius,
      area: area * R * R,
      neighbors: new Set<number>(),
    });
  });

  // Map seed neighbours to shard neighbours.
  shardOfSeed.forEach((shardId, si) => {
    for (const nb of neighborsOf[si]) {
      const j = shardOfSeed.get(nb);
      if (j !== undefined) shards[shardId].neighbors.add(j);
    }
  });

  const cracks = new THREE.BufferGeometry();
  cracks.setAttribute('position', new THREE.Float32BufferAttribute(crackPos, 3));
  cracks.setAttribute('dist', new THREE.Float32BufferAttribute(crackDist, 1));
  cracks.setAttribute('side', new THREE.Float32BufferAttribute(crackSide, 4));
  return { shards, cracks };
}

/** Material for the crack network: thin bright ribbons revealed outward from impact. */
export function crackMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      uProgress: { value: 0 },
      uWidth: { value: 0.0028 },
      uOpacity: { value: 1 },
    },
    vertexShader: /* glsl */ `
      attribute float dist;
      attribute vec4 side;
      uniform float uProgress;
      uniform float uWidth;
      varying float vReveal;
      varying float vEdge;
      varying float vFres;
      void main() {
        // Cracks are thicker and brighter close to the impact.
        float w = uWidth * mix(1.8, 0.7, clamp(dist / 2.0, 0.0, 1.0));
        vec3 p = position + side.yzw * side.x * w;
        vReveal = uProgress - dist;
        vEdge = side.x;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vec3 n = normalize(normalMatrix * normalize(position));
        vFres = 1.0 - abs(dot(n, normalize(-mv.xyz)));
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uOpacity;
      varying float vReveal;
      varying float vEdge;
      varying float vFres;
      void main() {
        if (vReveal < 0.0) discard;
        float grow = smoothstep(0.0, 0.08, vReveal);
        // One side of the ribbon catches the light, the other is in shade,
        // like the bevel of a real fracture.
        float lit = smoothstep(-0.2, 0.6, vEdge);
        vec3 col = mix(vec3(0.38, 0.40, 0.40), vec3(1.0), lit);
        float a = grow * mix(0.55, 0.95, lit) * mix(1.0, 0.45, vFres) * uOpacity;
        gl_FragColor = vec4(col, a);
      }
    `,
  });
}
