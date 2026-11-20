import * as THREE from 'three';
import type { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

/**
 * The island's plants as real meshes (tools/blender/export_veg.py):
 * every tree, shrub, flower and grass clump from the Blender scene, GPU
 * instanced per species. Big trees have two levels of detail; each frame
 * nearby instances use the detailed mesh and distant ones the light one.
 *
 * Colours are Blender's final material colours (autumn recolours included)
 * baked flat; light comes from the scene's sunset lights plus a soft
 * "light through leaves" term, and a little wind.
 */

interface VegJson {
  geoms: Record<string, { lod1: string | null; tris: number[] }>;
  protos: { geom: string; mats: (string | null)[]; tag: string }[];
  materials: Record<string, { tex: string | null; color?: [number, number, number]; alpha: boolean; vc: boolean }>;
  // proto, x, y, z, qx, qy, qz, qw, sx, sy, sz (Blender Z-up)
  instances: number[][];
}

export interface Vegetation {
  root: THREE.Group;
  materials: THREE.Material[];
  /** Pick level of detail for each instance from the camera (world space). */
  update(camera: THREE.Camera, t: number): void;
}

const LOD_NEAR = 0.55; // Blender units: within this, big trees use the detailed mesh

/** Each material slot's geometry plus its node transform (meshopt
 *  quantization stores the dequantize scale/offset on the node). */
function slotMeshes(obj: THREE.Object3D | undefined) {
  const out: { slot: number; geometry: THREE.BufferGeometry; node: THREE.Matrix4 }[] = [];
  if (!obj) return out;
  // Exported objects sit at the origin, so a node's world matrix is just
  // its (de)quantization transform.
  obj.updateWorldMatrix(true, true);
  obj.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    const name = (m.material as THREE.Material).name || 'slot0';
    out.push({ slot: Number(name.replace(/\D/g, '')) || 0, geometry: m.geometry, node: m.matrixWorld.clone() });
  });
  return out;
}

export async function loadVegetation(base: string, loader: GLTFLoader, renderer: THREE.WebGLRenderer, uTime: { value: number }, sunDir: THREE.Vector3): Promise<Vegetation> {
  const [data, gltf] = await Promise.all([
    fetch(base + 'veg.json').then((r) => r.json() as Promise<VegJson>),
    loader.loadAsync(base + 'veg/veg.glb'),
  ]);
  const root = new THREE.Group();
  root.name = 'vegetation';
  const texLoader = new THREE.TextureLoader();
  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());

  // ---- materials
  const shared = {
    uTime,
    uSun: { value: sunDir.clone().normalize() },
    uSunCol: { value: new THREE.Color('#ffb070') },
  };
  const mats = new Map<string, THREE.MeshStandardMaterial>();
  const all: THREE.Material[] = [];
  const makeMat = (key: string) => {
    const d = data.materials[key];
    const m = new THREE.MeshStandardMaterial({
      roughness: 0.82,
      metalness: 0,
      side: THREE.DoubleSide,
      vertexColors: d.vc,
      envMapIntensity: 1.1,
    });
    if (d.tex) {
      const t = texLoader.load(base + 'veg/' + d.tex.replace(/\.png$/, '.webp'));
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = aniso;
      t.flipY = false;
      m.map = t;
      m.color.setScalar(1.12);
    } else if (d.color) m.color.setRGB(d.color[0], d.color[1], d.color[2], THREE.SRGBColorSpace);
    if (d.alpha) {
      m.alphaTest = 0.45;
      // Alpha-to-coverage gives soft, non-flickering leaf edges under MSAA.
      m.alphaToCoverage = true;
    }
    m.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, shared);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime;')
        .replace(
          '#include <project_vertex>',
          `vec4 ipos = instanceMatrix * vec4(transformed, 1.0);
          vec3 ip = instanceMatrix[3].xyz;
          // Wind: grows with height above the plant's base (island units, Z-up).
          float hgt = max(ipos.z - ip.z, 0.0);
          float ph = ip.x * 23.0 + ip.y * 17.0;
          float sway = sin(uTime * 1.4 + ph) * 0.6 + sin(uTime * 2.3 + ph * 1.7) * 0.4;
          ipos.xy += vec2(sway, sway * 0.6) * 0.06 * hgt * hgt;
          vec4 mvPosition = modelViewMatrix * ipos;
          gl_Position = projectionMatrix * mvPosition;`,
        );
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform vec3 uSun; uniform vec3 uSunCol;')
        .replace(
          '#include <lights_fragment_end>',
          `#include <lights_fragment_end>
          // Sun shining through leaves: bright when looking toward the sun.
          vec3 sunV = normalize((viewMatrix * vec4(uSun, 0.0)).xyz);
          float through = pow(clamp(dot(normalize(-vViewPosition), sunV), 0.0, 1.0), 3.0);
          float wrap = clamp(dot(normal, sunV) * 0.5 + 0.5, 0.0, 1.0);
          reflectedLight.indirectDiffuse += diffuseColor.rgb * uSunCol * (0.6 * through + 0.22 * wrap);`,
        );
    };
    m.customProgramCacheKey = () => 'veg';
    all.push(m);
    return m;
  };
  const matFor = (key: string | null) => {
    if (!key || !data.materials[key]) key = Object.keys(data.materials)[0];
    let m = mats.get(key);
    if (!m) { m = makeMat(key); mats.set(key, m); }
    return m;
  };

  // ---- instances grouped by prototype
  const byProto = new Map<number, number[][]>();
  for (const it of data.instances) {
    const l = byProto.get(it[0]) ?? [];
    l.push(it);
    byProto.set(it[0], l);
  }

  interface Lod { meshes: THREE.InstancedMesh[]; nodes: THREE.Matrix4[]; }
  interface Batch { matrices: THREE.Matrix4[]; centers: THREE.Vector3[]; radius: number; lod0: Lod; lod1: Lod | null; }
  const batches: Batch[] = [];
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();

  const build = (objName: string, proto: VegJson['protos'][number], n: number): Lod => {
    const parts = slotMeshes(gltf.scene.getObjectByName(objName));
    const meshes = parts.map(({ slot, geometry }) => {
      const im = new THREE.InstancedMesh(geometry, matFor(proto.mats[slot] ?? null), n);
      im.frustumCulled = false;
      im.count = 0;
      root.add(im);
      return im;
    });
    return { meshes, nodes: parts.map((p) => p.node) };
  };

  for (const [pi, list] of byProto) {
    const proto = data.protos[pi];
    const g = data.geoms[proto.geom];
    if (!g) continue;
    const matrices: THREE.Matrix4[] = [], centers: THREE.Vector3[] = [];
    for (const it of list) {
      p.set(it[1], it[2], it[3]);
      q.set(it[4], it[5], it[6], it[7]);
      s.set(it[8], it[9], it[10]);
      matrices.push(new THREE.Matrix4().compose(p, q, s));
      centers.push(p.clone());
    }
    const lod0 = build(proto.geom, proto, list.length);
    const lod1 = g.lod1 ? build(g.lod1, proto, list.length) : null;
    batches.push({ matrices, centers, radius: 0, lod0, lod1 });
    // Static batches (no LOD) are filled once.
    if (!lod1) lod0.meshes.forEach((im, k) => { matrices.forEach((mm, i) => im.setMatrixAt(i, m4.multiplyMatrices(mm, lod0.nodes[k]))); im.count = matrices.length; im.instanceMatrix.needsUpdate = true; });
  }

  const camLocal = new THREE.Vector3();
  const inv = new THREE.Matrix4();
  let lastCam = new THREE.Vector3(1e9, 0, 0);

  return {
    root,
    materials: all,
    update(camera: THREE.Camera) {
      root.updateWorldMatrix(true, false);
      inv.copy(root.matrixWorld).invert();
      camLocal.setFromMatrixPosition(camera.matrixWorld).applyMatrix4(inv);
      if (camLocal.distanceToSquared(lastCam) < 1e-6) return;
      lastCam.copy(camLocal);
      const near2 = LOD_NEAR * LOD_NEAR;
      for (const b of batches) {
        if (!b.lod1) continue;
        let n0 = 0, n1 = 0;
        for (let i = 0; i < b.matrices.length; i++) {
          const close = b.centers[i].distanceToSquared(camLocal) < near2;
          if (close) { b.lod0.meshes.forEach((im, k) => im.setMatrixAt(n0, m4.multiplyMatrices(b.matrices[i], b.lod0.nodes[k]))); n0++; }
          else { b.lod1.meshes.forEach((im, k) => im.setMatrixAt(n1, m4.multiplyMatrices(b.matrices[i], b.lod1!.nodes[k]))); n1++; }
        }
        for (const im of b.lod0.meshes) { im.count = n0; im.instanceMatrix.needsUpdate = true; }
        for (const im of b.lod1.meshes) { im.count = n1; im.instanceMatrix.needsUpdate = true; }
      }
    },
  };
}
