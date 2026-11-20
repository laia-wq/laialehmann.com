import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import type { Interior } from './interior';
import { loadVegetation, type Vegetation } from './veg';

/**
 * The world inside the globe, built in Blender (tools/blender/build_world.py)
 * and exported by tools/blender/export_web.py:
 *
 *  - static.glb: every solid thing with Cycles' sunset lighting baked into
 *    textures, drawn unlit (so it looks like the path-traced render and costs
 *    almost nothing to light)
 *  - veg.glb / veg.json: every plant as a real mesh, instanced (veg.ts)
 *  - water.glb: lake, pond, stream and the three falls, shaded live
 *  - world.json: plant instances, glow lights, mist plumes and a heightmap
 *
 * Blender is Z-up with the sphere centre at the origin; `zup` converts.
 */

interface WorldData {
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
  let veg: Vegetation | null = null;

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

  const gltf = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);

  // Still water at sunset: deep teal looking down, the warm peach-pink sky
  // reflected at grazing angles, with slow ripples.
  const waterMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, uniforms: { uTime },
    vertexShader: /* glsl */ `
      varying vec3 vW; varying vec3 vN; varying vec3 vL;
      void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vL = position; vN = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */ `
      uniform float uTime; varying vec3 vW; varying vec3 vN; varying vec3 vL;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
        return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
      void main(){
        vec3 V = normalize(cameraPosition - vW);
        float rip = n(vL.xz * 90.0 + uTime * 0.35) * 0.6 + n(vL.xz * 210.0 - uTime * 0.5) * 0.4;
        float fres = pow(1.0 - max(dot(V, vec3(0.0, 1.0, 0.0)), 0.0), 3.0);
        fres = clamp(fres + (rip - 0.5) * 0.12, 0.0, 1.0);
        vec3 deep = vec3(0.05, 0.12, 0.12);
        vec3 sky = mix(vec3(1.0, 0.72, 0.62), vec3(1.0, 0.86, 0.7), rip);
        vec3 col = mix(deep, sky, 0.08 + 0.62 * fres * fres);
        col += vec3(1.0, 0.8, 0.6) * pow(rip, 8.0) * 0.6;   // glints
        gl_FragColor = vec4(col, 0.9);
        #include <colorspace_fragment>
      }`,
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
        // Falling sheet: long vertical streaks racing down, thin and
        // see-through at the edges, foamy where it steps over a ledge.
        float t = uTime;
        float streak = n(vec2(vUv.x * 46.0, vUv.y * 2.2 - t * 2.6)) * 0.55 + n(vec2(vUv.x * 110.0, vUv.y * 5.0 - t * 4.2)) * 0.45;
        float churn = n(vec2(vUv.x * 14.0, vUv.y * 18.0 - t * 5.0));
        float wob = (n(vec2(vUv.y * 10.0 - t * 1.5, 3.0)) - 0.5) * 0.14;
        float edge = smoothstep(0.0, 0.26, vUv.x + wob) * smoothstep(1.0, 0.74, vUv.x - wob);
        vec3 deep = vec3(0.62, 0.72, 0.74);
        vec3 white = vec3(1.0, 0.97, 0.93);
        float foam = mix(churn, streak, vDrop);
        vec3 col = mix(deep, white, smoothstep(0.25, 0.85, foam));
        col *= mix(1.0, 1.08, vDrop);
        float a = edge * mix(0.75 * smoothstep(0.2, 0.7, churn) + 0.15, 0.22 + 0.62 * smoothstep(0.2, 0.9, streak), vDrop);
        gl_FragColor = vec4(col, a);
        #include <colorspace_fragment>
      }`,
  });

  const ready = (async () => {
    const [data, staticG, waterG] = await Promise.all([
      fetch(BASE + 'world.json').then((r) => r.json() as Promise<WorldData>),
      gltf.loadAsync(BASE + 'static.glb'),
      gltf.loadAsync(BASE + 'water.glb'),
    ]);
    hm = data.heightmap;

    // Static: baked lighting, drawn unlit. Ground and cliffs also get a
    // fine detail texture (triplanar, luminance only) so they stay crisp
    // when you walk right up to them.
    const [grassD, rockD] = await Promise.all([detailTexture('textures/aerial_grass_rock_diff.webp'), detailTexture('textures/mossy_rock_diff.webp')]);
    staticG.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const src = m.material as THREE.MeshStandardMaterial;
      if (src.map) { src.map.colorSpace = THREE.SRGBColorSpace; src.map.anisotropy = renderer.capabilities.getMaxAnisotropy(); }
      // Cycles renders were viewed at +0.8 EV; match that brightness.
      const mat = new THREE.MeshBasicMaterial({ map: src.map ?? null, color: new THREE.Color(1.75, 1.7, 1.65) });
      const name = (m.name + ' ' + (m.parent?.name ?? '')).toLowerCase();
      const det = name.includes('terrain') ? { d: grassD, rep: 26, amt: 0.75 } : name.includes('cliff') ? { d: rockD, rep: 13, amt: 0.85 } : name.includes('rocks') ? { d: rockD, rep: 30, amt: 0.6 } : null;
      if (det) withDetail(mat, det.d, det.rep, det.amt);
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

    // Plants: real meshes.
    veg = await loadVegetation(BASE, gltf, renderer, uTime, new THREE.Vector3(-4.4, 4.6, -1.2));
    zup.add(veg.root);
    mats.push(...veg.materials);

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
      (sp.material as THREE.SpriteMaterial).opacity = big ? 0.12 : 0.42;
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
    update(t, camera) {
      uTime.value = t;
      if (veg && camera) veg.update(camera, t);
    },
    setOpacity(o) {
      for (const m of mats) { m.transparent = o < 1; m.opacity = o; }
    },
  };
}

const PUB = import.meta.env.BASE_URL;

/** A tiling detail texture plus its mean linear luminance (to keep the bake's tone). */
function detailTexture(path: string): Promise<{ tex: THREE.Texture; mean: number }> {
  return new Promise((res, rej) => {
    new THREE.TextureLoader().load(PUB + path, (tex) => {
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 8;
      const img = tex.image as HTMLImageElement;
      const c = document.createElement('canvas');
      c.width = c.height = 64;
      const g = c.getContext('2d')!;
      g.drawImage(img, 0, 0, 64, 64);
      const px = g.getImageData(0, 0, 64, 64).data;
      const lin = (v: number) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
      let sum = 0;
      for (let i = 0; i < px.length; i += 4) sum += 0.299 * lin(px[i]) + 0.587 * lin(px[i + 1]) + 0.114 * lin(px[i + 2]);
      res({ tex, mean: Math.max(sum / (px.length / 4), 1e-3) });
    }, undefined, rej);
  });
}

function withDetail(mat: THREE.MeshBasicMaterial, d: { tex: THREE.Texture; mean: number }, rep: number, amt: number) {
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uDetail = { value: d.tex };
    sh.uniforms.uMean = { value: d.mean };
    sh.uniforms.uRep = { value: rep };
    sh.uniforms.uAmt = { value: amt };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vDP; varying vec3 vDN; varying float vDepth;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvDP = position; vDN = normal; vDepth = -mvPosition.z;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform sampler2D uDetail; uniform float uMean; uniform float uRep; uniform float uAmt; varying vec3 vDP; varying vec3 vDN; varying float vDepth;')
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        vec3 an = abs(normalize(vDN)); an = pow(an, vec3(4.0)); an /= (an.x + an.y + an.z);
        vec3 dt = texture2D(uDetail, vDP.zy * uRep).rgb * an.x + texture2D(uDetail, vDP.xz * uRep).rgb * an.y + texture2D(uDetail, vDP.xy * uRep).rgb * an.z;
        float dl = dot(dt, vec3(0.299, 0.587, 0.114)) / uMean;
        float k = uAmt * mix(0.35, 1.0, 1.0 - smoothstep(0.08, 1.4, vDepth));
        diffuseColor.rgb *= mix(1.0, clamp(dl, 0.25, 2.2), k);`,
      );
  };
  mat.customProgramCacheKey = () => 'detail' + rep;
}
