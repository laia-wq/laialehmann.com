import * as THREE from 'three';

/**
 * A soft grey photo studio used only for reflections and image-based light:
 * a warm-grey room, one tall window with mullions on the right (the crisp
 * reflection you see on the glass), a big diffuse softbox up-left for the
 * key, and a dim floor. Rendered into a PMREM cube at load.
 */
export function studioScene(): THREE.Scene {
  const scene = new THREE.Scene();

  const room = new THREE.Mesh(
    new THREE.SphereGeometry(12, 64, 32),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
      fragmentShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          float h = vDir.y;
          vec3 floorC = vec3(0.16, 0.15, 0.14);
          vec3 wall = vec3(0.48, 0.47, 0.45);
          vec3 ceil = vec3(0.62, 0.61, 0.6);
          vec3 c = h < 0.0 ? mix(wall * 0.7, floorC, smoothstep(0.0, 0.35, -h)) : mix(wall, ceil, smoothstep(0.1, 0.9, h));
          gl_FragColor = vec4(c, 1.0);
        }
      `,
    }),
  );
  scene.add(room);

  const emissive = (w: number, h: number, intensity: number, color = new THREE.Color(1, 0.98, 0.95)) =>
    new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: color.clone().multiplyScalar(intensity), side: THREE.DoubleSide }));

  // Tall window with mullions, right side and slightly behind.
  const win = new THREE.Group();
  const paneW = 1.7, paneH = 2.5, gap = 0.16;
  for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
      const p = emissive(paneW, paneH, 3.6, new THREE.Color(0.97, 0.99, 1.0));
      p.position.set((i - 0.5) * (paneW + gap), (j - 0.5) * (paneH + gap), 0);
      win.add(p);
    }
  }
  // Frame / wall around the panes is darker than the room so the bars read.
  const frame = new THREE.Mesh(new THREE.PlaneGeometry(paneW * 2 + gap * 3, paneH * 2 + gap * 3), new THREE.MeshBasicMaterial({ color: '#2a2928', side: THREE.DoubleSide }));
  frame.position.z = -0.02;
  win.add(frame);
  win.position.set(6.5, 5.5, 1.2);
  win.lookAt(0, 0.4, 0);
  scene.add(win);

  // Big soft key up-left/front.
  const key = emissive(9, 6, 1.5, new THREE.Color(1, 0.95, 0.88));
  key.position.set(-6, 6, 5);
  key.lookAt(0, 0, 0);
  scene.add(key);

  // Faint warm bounce low-left, and a thin overhead strip.
  const bounce = emissive(6, 1.5, 0.5, new THREE.Color(1, 0.9, 0.8));
  bounce.position.set(-7, 0.5, -3);
  bounce.lookAt(0, 0, 0);
  scene.add(bounce);
  const strip = emissive(0.5, 7, 0.9);
  strip.position.set(0.5, 9, -1.5);
  strip.rotation.x = Math.PI / 2;
  scene.add(strip);

  return scene;
}
