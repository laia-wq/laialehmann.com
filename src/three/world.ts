import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import type { Interior } from './interior';

/**
 * The world inside the globe, built in Blender (tools/blender/build_world.py)
 * and exported by tools/blender/export_web.py:
 *
 *  - static.glb: every solid thing with Cycles' sunset lighting baked into
 *    textures, drawn unlit (so it looks like the path-traced render and costs
 *    almost nothing to light)
 *  - cards: each plant species rendered from two sides into an atlas; every
 *    plant instance is two crossed textured quads (GPU-instanced)
 *  - water.glb: lake, pond, stream and the three falls, shaded live
 *  - world.json: plant instances, glow lights, mist plumes and a heightmap
 *
 * Blender is Z-up with the sphere centre at the origin; `zup` converts.
 */

interface CardView { cx: number; cz: number; fw: number; fh: number; uv: [number, number, number, number] }
interface WorldData {
  cards: { kind: 'tree' | 'small'; views: [CardView, CardView] }[];
  instances: [number, number, number, number, number, number][];
  glows: { p: [number, number, number]; c: [number, number, number]; e: number; k: string }[];
  mists: { p: [number, number, number]; s: [number, number, number]; n: string }[];
  heightmap: { n: number; ext: number; z: (number | null)[][] };
}

const BASE = `${import.meta.env.BASE_URL}world/`;

function softTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,1)');
  gr.addColorStop(0.3, 'rgba(255,255,255,0.45)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

function cardMaterial(map: THREE.Texture, uTime: { value: number }) {
  return new THREE.ShaderMaterial({
    uniforms: { map: { value: map }, uTime, uTint: { value: new THREE.Color(1, 1, 1) }, uOpacity: { value: 1 } },
    transparent: false,
    side: THREE.DoubleSide,
    vertexShader: /* glsl */ `
      attribute float aView;
      attribute vec2 aQ;
      attribute vec4 aF0; attribute vec4 aF1; attribute vec4 aU0; attribute vec4 aU1;
      uniform float uTime;
      varying vec2 vUv;
      void main() {
        vec4 F = aView < 0.5 ? aF0 : aF1;
        vec4 U = aView < 0.5 ? aU0 : aU1;
        float h = F.x + (aQ.x - 0.5) * F.z;
        float z = F.y + (aQ.y - 0.5) * F.w;
        vec3 p = aView < 0.5 ? vec3(h, 0.0, z) : vec3(0.0, h, z);
        vec4 ip = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        float sway = sin(uTime * 1.3 + ip.x * 17.0 + ip.y * 11.0) * 0.012 * aQ.y * aQ.y * F.w;
        p.x += sway;
        vUv = U.xy + aQ * U.zw;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D map; uniform vec3 uTint; uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        vec4 c = texture2D(map, vUv);
        if (c.a < 0.5) discard;
        gl_FragColor = vec4(c.rgb * uTint, uOpacity);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function buildBlenderWorld(c: THREE.Vector3, renderer: THREE.WebGLRenderer): Interior {
  const group = new THREE.Group();
  group.position.copy(c);
  const zup = new THREE.Group();
  zup.rotation.x = -Math.PI / 2; // Blender (x, y, z) -> three (x, z, -y)
  group.add(zup);
  const uTime = { value: 0 };
  const transparents: THREE.Object3D[] = [];
  const mats: THREE.Material[] = [];
  const inner = 0.972, depth = 0.5;
  let hm: WorldData['heightmap'] | null = null;

  const groundAt = (x: number, z: number) => {
    // three local -> Blender: bx = x - c.x, by = -(z - c.z)
    if (!hm) return c.y - depth;
    const bx = x - c.x, by = -(z - c.z);
    const n = hm.n, e = hm.ext;
    const fx = ((bx + e) / (2 * e)) * (n - 1), fy = ((by + e) / (2 * e)) * (n - 1);
    const i = Math.max(0, Math.min(n - 2, Math.floor(fx))), j = Math.max(0, Math.min(n - 2, Math.floor(fy)));
    const tx = fx - i, ty = fy - j;
    const g = (a: number, b: number) => hm!.z[b][a] ?? -depth;
    const zb = (g(i, j) * (1 - tx) + g(i + 1, j) * tx) * (1 - ty) + (g(i, j + 1) * (1 - tx) + g(i + 1, j + 1) * tx) * ty;
    return c.y + zb;
  };

  const tex = new THREE.TextureLoader();
  const loadTex = (f: string) =>
    new Promise<THREE.Texture>((res, rej) => tex.load(BASE + f, (t) => { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); res(t); }, undefined, rej));
  const gltf = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);

  const waterMat = new THREE.MeshPhysicalMaterial({
    // Still water at sunset: teal depth with a warm rosy sheen from the sky.
    color: '#3d6c68', emissive: '#4a2c2a', emissiveIntensity: 0.35, roughness: 0.08, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 0.6, transparent: true, opacity: 0.86, depthWrite: false,
  });
  const fallMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, uniforms: { uTime },
    vertexShader: /* glsl */ `
      varying vec2 vUv; varying float vDrop;
      void main(){
        vUv = uv;
        vec3 n = normalize(mat3(modelMatrix) * normal);
        vDrop = 1.0 - smoothstep(0.35, 0.75, abs(n.y));
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform float uTime; varying vec2 vUv; varying float vDrop;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
        return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
      void main(){
        float big = n(vec2(vUv.x * 9.0, vUv.y * 6.0 - uTime * 1.8));
        float small = n(vec2(vUv.x * 34.0, vUv.y * 26.0 - uTime * 4.5));
        float s = big * 0.6 + small * 0.4;
        float edge = smoothstep(0.0, 0.2, vUv.x) * smoothstep(1.0, 0.8, vUv.x);
        vec3 drop = mix(vec3(0.75, 0.82, 0.86), vec3(1.0, 0.97, 0.94), s);
        vec3 tread = mix(vec3(0.2, 0.28, 0.28), vec3(0.6, 0.66, 0.66), s);
        vec3 col = mix(tread, drop, vDrop);
        float a = edge * mix(0.75, 0.88 + 0.12 * s, vDrop);
        gl_FragColor = vec4(col, a);
        #include <colorspace_fragment>
      }`,
  });

  const ready = (async () => {
    const [data, staticG, waterG, atlasTree, atlasSmall] = await Promise.all([
      fetch(BASE + 'world.json').then((r) => r.json() as Promise<WorldData>),
      gltf.loadAsync(BASE + 'static.glb'),
      gltf.loadAsync(BASE + 'water.glb'),
      loadTex('cards_tree.webp'),
      loadTex('cards_small.webp'),
    ]);
    hm = data.heightmap;

    // Static: baked lighting, drawn unlit.
    staticG.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const src = m.material as THREE.MeshStandardMaterial;
      if (src.map) src.map.colorSpace = THREE.SRGBColorSpace;
      // Cycles renders were viewed at +0.8 EV; match that brightness.
      const mat = new THREE.MeshBasicMaterial({ map: src.map ?? null, color: new THREE.Color(1.75, 1.7, 1.65) });
      m.material = mat;
      mats.push(mat);
    });
    group.add(staticG.scene);

    waterG.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.material = m.name.startsWith('waterfall') ? fallMat : waterMat;
      m.renderOrder = m.name.startsWith('waterfall') ? 2 : 1;
      transparents.push(m);
    });
    group.add(waterG.scene);

    // Plant cards, one instanced mesh per atlas.
    for (const kind of ['tree', 'small'] as const) {
      const list = data.instances.filter((it) => data.cards[it[0]].kind === kind);
      if (!list.length) continue;
      const geo = new THREE.BufferGeometry();
      const q = [0, 0, 1, 0, 1, 1, 0, 1];
      const aQ: number[] = [], aView: number[] = [], pos: number[] = [], idx: number[] = [];
      for (let v = 0; v < 2; v++) {
        for (let k = 0; k < 4; k++) { aQ.push(q[k * 2], q[k * 2 + 1]); aView.push(v); pos.push(0, 0, 0); }
        const b = v * 4; idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
      }
      geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      geo.setAttribute('aQ', new THREE.Float32BufferAttribute(aQ, 2));
      geo.setAttribute('aView', new THREE.Float32BufferAttribute(aView, 1));
      geo.setIndex(idx);
      const N = list.length;
      const F0 = new Float32Array(N * 4), F1 = new Float32Array(N * 4), U0 = new Float32Array(N * 4), U1 = new Float32Array(N * 4);
      const mat = cardMaterial(kind === 'tree' ? atlasTree : atlasSmall, uTime);
      const im = new THREE.InstancedMesh(geo, mat, N);
      const m4 = new THREE.Matrix4(), qn = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
      list.forEach(([ci, x, y, z, sc, rz], i) => {
        const [v0, v1] = data.cards[ci].views;
        F0.set([v0.cx, v0.cz, v0.fw, v0.fh], i * 4); F1.set([v1.cx, v1.cz, v1.fw, v1.fh], i * 4);
        U0.set(v0.uv, i * 4); U1.set(v1.uv, i * 4);
        qn.setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz);
        m4.compose(p.set(x, y, z), qn, s.setScalar(sc));
        im.setMatrixAt(i, m4);
      });
      geo.setAttribute('aF0', new THREE.InstancedBufferAttribute(F0, 4));
      geo.setAttribute('aF1', new THREE.InstancedBufferAttribute(F1, 4));
      geo.setAttribute('aU0', new THREE.InstancedBufferAttribute(U0, 4));
      geo.setAttribute('aU1', new THREE.InstancedBufferAttribute(U1, 4));
      im.frustumCulled = false;
      mats.push(mat);
      zup.add(im);
    }

    // Glows: candles, lanterns, fairy lights, tower windows.
    const soft = softTexture();
    const gpos: number[] = [], gcol: number[] = [], gsize: number[] = [], gseed: number[] = [];
    for (const g of data.glows) {
      gpos.push(...g.p);
      const k = g.k.startsWith('fairy') ? 1.0 : g.k.startsWith('candle') ? 0.6 : 1.3;
      gcol.push(...g.c.map((v) => v * 1.0));
      gsize.push(k);
      gseed.push(Math.random());
    }
    const gg = new THREE.BufferGeometry();
    gg.setAttribute('position', new THREE.Float32BufferAttribute(gpos, 3));
    gg.setAttribute('color', new THREE.Float32BufferAttribute(gcol, 3));
    gg.setAttribute('aSize', new THREE.Float32BufferAttribute(gsize, 1));
    gg.setAttribute('aSeed', new THREE.Float32BufferAttribute(gseed, 1));
    const glowMat = new THREE.ShaderMaterial({
      uniforms: { map: { value: soft }, uTime, uPx: { value: renderer.getPixelRatio() } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, vertexColors: true,
      vertexShader: /* glsl */ `
        attribute float aSize; attribute float aSeed; uniform float uTime; uniform float uPx;
        varying vec3 vC; varying float vA;
        void main(){
          vC = color;
          vA = 0.75 + 0.25 * sin(uTime * (1.5 + aSeed * 2.0) + aSeed * 40.0);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = aSize * 22.0 * uPx / -mv.z;
        }`,
      fragmentShader: /* glsl */ `
        uniform sampler2D map; varying vec3 vC; varying float vA;
        void main(){ float a = texture2D(map, gl_PointCoord).r; gl_FragColor = vec4(vC * a * vA, a); }`,
    });
    const glows = new THREE.Points(gg, glowMat);
    glows.frustumCulled = false;
    glows.renderOrder = 4;
    zup.add(glows);
    transparents.push(glows);

    // Mist plumes.
    const mistMat = new THREE.SpriteMaterial({ map: soft, color: '#fff3ea', transparent: true, opacity: 0.42, depthWrite: false });
    for (const m of data.mists) {
      const sp = new THREE.Sprite(mistMat);
      sp.position.set(...m.p);
      const big = m.n === 'mist_lake';
      sp.scale.set(m.s[0] * (big ? 2.2 : 3.2), m.s[2] * (big ? 1.4 : 3.2), 1);
      sp.material = mistMat.clone();
      (sp.material as THREE.SpriteMaterial).opacity = big ? 0.22 : 0.5;
      sp.userData.base = sp.position.clone();
      sp.userData.phase = Math.random() * 10;
      sp.renderOrder = 3;
      zup.add(sp);
      transparents.push(sp);
    }
  })();

  return {
    group,
    groundAt,
    groundY: c.y - depth,
    radius: Math.sqrt(inner * inner - depth * depth),
    transparents,
    ready: ready.catch((e) => console.error('World failed to load', e)) as Promise<void>,
    update(t) {
      uTime.value = t;
    },
    setOpacity(o) {
      for (const m of mats) { m.transparent = o < 1; m.opacity = o; }
    },
  };
}
