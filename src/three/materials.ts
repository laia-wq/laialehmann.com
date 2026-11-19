import * as THREE from 'three';
import { fbmField, fieldToTexture } from './textures';

/** One muted palette shared by every object in the scene. */
export const palette = {
  backdropTop: '#d6d3ce',
  backdropBottom: '#8e8a84',
  porcelain: '#efe9e0',
  bone: '#e4dccf',
  clay: '#c08a68',
  clayDark: '#8f6248',
  sage: '#a7b29a',
  slate: '#8c98a3',
  ink: '#3d3a36',
};

/** Matte porcelain/clay: the single material language for miniatures. */
export function clay(color: string, roughness = 0.62): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    metalness: 0,
    clearcoat: 0.18,
    clearcoatRoughness: 0.55,
    sheen: 0.25,
    sheenRoughness: 0.8,
    sheenColor: new THREE.Color('#ffffff'),
  });
}

export function glass(): THREE.MeshPhysicalMaterial {
  // Faint smudges and wipe marks: the glass is almost, but not quite, perfect.
  const S = 512;
  const broad = fbmField(S, 5, 4, 71);
  const fine = fbmField(S, 40, 3, 72);
  const rough = fieldToTexture(new Float32Array(S * S).map((_, i) => {
    const smudge = Math.max(0, broad[i] - 0.6) * 0.12;
    return 0.004 + smudge + fine[i] * 0.004;
  }), S, S, (v) => { const g = Math.min(255, v * 255); return [g, g, g]; });
  const m = new THREE.MeshPhysicalMaterial({
    color: '#ffffff',
    metalness: 0,
    roughness: 1,
    roughnessMap: rough,
    transmission: 1,
    thickness: 0.05,
    ior: 1.5,
    dispersion: 0.2,
    envMapIntensity: 3.6,
    specularIntensity: 1,
    side: THREE.FrontSide,
  });
  // Real studio glass shows the softboxes and window it reflects, not the
  // pin-point glints of analytic lights, so drop direct specular here.
  m.onBeforeCompile = (sh) => {
    sh.fragmentShader = sh.fragmentShader.replace(
      'vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;',
      'vec3 totalSpecular = reflectedLight.indirectSpecular;',
    );
  };
  return m;
}

/**
 * The inside surface of the sphere: no transmission (that is what caused
 * edge smearing), just faint reflections of the room, which is what you
 * see on the far wall of a real glass ball.
 */
export function glassBack(): THREE.MeshPhysicalMaterial {
  const m = new THREE.MeshPhysicalMaterial({
    color: '#ffffff',
    metalness: 0,
    roughness: 0.03,
    transparent: true,
    opacity: 0.08,
    envMapIntensity: 3.0,
    side: THREE.BackSide,
    depthWrite: false,
  });
  m.onBeforeCompile = noDirectSpecular;
  return m;
}

export function noDirectSpecular(sh: { fragmentShader: string }) {
  sh.fragmentShader = sh.fragmentShader.replace(
    'vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;',
    'vec3 totalSpecular = reflectedLight.indirectSpecular;',
  );
}

/** Soft radial backdrop (lighter behind the globe), also seen through glass. */
export function backdropTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d')!;
  g.fillStyle = palette.backdropBottom;
  g.fillRect(0, 0, 512, 512);
  const grad = g.createRadialGradient(256, 200, 10, 256, 230, 420);
  grad.addColorStop(0, palette.backdropTop);
  grad.addColorStop(0.5, '#b9b5af');
  grad.addColorStop(1, palette.backdropBottom);
  g.fillStyle = grad;
  g.fillRect(0, 0, 512, 512);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Soft radial blob used for contact shadows. */
export function shadowTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(40,30,20,0.55)');
  grad.addColorStop(0.45, 'rgba(40,30,20,0.22)');
  grad.addColorStop(1, 'rgba(40,30,20,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

export function contactShadow(size: number, opacity = 1): THREE.Mesh {
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshBasicMaterial({
      map: shadowTexture(),
      transparent: true,
      opacity,
      depthWrite: false,
    }),
  );
  m.rotation.x = -Math.PI / 2;
  m.renderOrder = -1;
  return m;
}
