import * as THREE from 'three';

/** One muted palette shared by every object in the scene. */
export const palette = {
  backdropTop: '#ebe6de',
  backdropBottom: '#c9bfb2',
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
  return new THREE.MeshPhysicalMaterial({
    color: '#ffffff',
    metalness: 0,
    roughness: 0.04,
    transmission: 1,
    thickness: 0.12,
    ior: 1.45,
    envMapIntensity: 1.1,
    specularIntensity: 1,
    clearcoat: 1,
    clearcoatRoughness: 0.03,
    attenuationColor: new THREE.Color('#eef3f2'),
    attenuationDistance: 2.5,
    side: THREE.DoubleSide,
  });
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
  grad.addColorStop(0.55, '#ddd6cc');
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
