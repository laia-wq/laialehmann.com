import * as THREE from 'three';

/**
 * A minimal photo-studio environment for reflections: a warm gradient dome,
 * one large soft key window up-left and a thin strip light on the right.
 * Gives the glass a couple of clean, intentional highlights instead of the
 * busy box reflections of a generic room.
 */
export function studioScene(): THREE.Scene {
  const scene = new THREE.Scene();
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(10, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
      fragmentShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          float h = vDir.y * 0.5 + 0.5;
          vec3 low = vec3(0.42, 0.38, 0.34);
          vec3 high = vec3(0.86, 0.84, 0.80);
          gl_FragColor = vec4(mix(low, high, smoothstep(0.2, 0.9, h)), 1.0);
        }
      `,
    }),
  );
  scene.add(dome);

  const light = (w: number, h: number, intensity: number, pos: THREE.Vector3) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.98, 0.95).multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    m.position.copy(pos);
    m.lookAt(0, 0, 0);
    scene.add(m);
  };
  light(5, 4, 3.2, new THREE.Vector3(-5, 5, 5)); // key window
  light(0.6, 6, 2.2, new THREE.Vector3(6, 1.5, 2)); // strip
  light(6, 6, 0.9, new THREE.Vector3(0, 9, 0)); // overhead fill
  return scene;
}
