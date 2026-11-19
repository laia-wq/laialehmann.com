import * as THREE from 'three';

/**
 * A dark, moody room used only for reflections and image-based light.
 * Dark walls make the glass's highlights stark: a tall mullioned window on
 * the right, a long overhead softbox that draws the classic arc across the
 * top of the sphere, a warm low lamp glow, and a few small warm practicals
 * that show up as tiny bright reflections. Rendered into a PMREM cube.
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
          vec3 floorC = vec3(0.16, 0.13, 0.1);   // paper-toned table
          vec3 wall = vec3(0.025, 0.023, 0.021); // dark room: only the windows reflect
          vec3 ceil = vec3(0.05, 0.048, 0.046);
          vec3 c = h < 0.0 ? mix(wall, floorC, smoothstep(0.0, 0.3, -h)) : mix(wall, ceil, smoothstep(0.2, 0.9, h));
          // Warm glow low on the left (a lamp out of frame).
          float lamp = pow(max(0.0, dot(vDir, normalize(vec3(-0.8, 0.05, -0.4)))), 12.0);
          c += vec3(0.9, 0.45, 0.15) * lamp * 0.6;
          gl_FragColor = vec4(c, 1.0);
        }
      `,
    }),
  );
  scene.add(room);

  const emissive = (w: number, h: number, intensity: number, color = new THREE.Color(1, 0.98, 0.95)) =>
    new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: color.clone().multiplyScalar(intensity), side: THREE.DoubleSide }));

  // Tall window with mullions, upper right.
  const win = new THREE.Group();
  const paneW = 1.6, paneH = 2.4, gap = 0.18;
  for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
      const p = emissive(paneW, paneH, 30, new THREE.Color(0.9, 0.96, 1.0));
      p.position.set((i - 0.5) * (paneW + gap), (j - 0.5) * (paneH + gap), 0);
      win.add(p);
    }
  }
  win.position.set(6.2, 5.6, 1.6);
  win.lookAt(0, 0.4, 0);
  scene.add(win);

  // A second, smaller window on the left so both sides have a crisp glint.
  const win2 = new THREE.Group();
  for (let j = 0; j < 3; j++) {
    const p = emissive(1.1, 1.0, 20, new THREE.Color(0.92, 0.97, 1.0));
    p.position.set(0, (j - 1) * 1.12, 0);
    win2.add(p);
  }
  win2.position.set(-7, 3.2, -1.5);
  win2.lookAt(0, 0.6, 0);
  scene.add(win2);

  // Dark shapes (furniture, a doorway) give the reflections contrast.
  const dark = (w: number, h: number, pos: THREE.Vector3) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: '#050403', side: THREE.DoubleSide }));
    m.position.copy(pos);
    m.lookAt(0, pos.y, 0);
    scene.add(m);
  };
  dark(3, 5, new THREE.Vector3(-2, 1.5, -9));
  dark(5, 2.2, new THREE.Vector3(6, -0.5, -6));

  // Long overhead softbox, slightly in front: a sweeping arc on the sphere's top.
  const arc = emissive(8, 1.1, 18, new THREE.Color(1, 0.97, 0.92));
  arc.position.set(-4.5, 6.5, 3.6);
  arc.lookAt(0, 0, 0);
  scene.add(arc);

  // Warm practicals behind and to the side.
  const warm = new THREE.Color(1, 0.62, 0.3);
  const spots: [number, number, number, number][] = [[-7, 1.5, -6, 0.5], [5, 0.8, -7, 0.35], [-3, 2.5, -9, 0.3], [8, 2, -3, 0.25], [-8, 0.6, 2, 0.4]];
  for (const [x, y, z, r] of spots) {
    const d = new THREE.Mesh(new THREE.CircleGeometry(r, 24), new THREE.MeshBasicMaterial({ color: warm.clone().multiplyScalar(6), side: THREE.DoubleSide }));
    d.position.set(x, y, z);
    d.lookAt(0, 0, 0);
    scene.add(d);
  }
  return scene;
}
