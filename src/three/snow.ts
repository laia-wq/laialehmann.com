import * as THREE from 'three';

/**
 * Snow, simulated like the particles in my C++ engine: a 120 Hz fixed step,
 * semi-implicit Euler, a boundary collision with restitution, and a uniform
 * grid so the cursor only touches flakes near it.
 *
 * Coordinates are local to the globe group (globe centre at `center`).
 */

const STEP = 1 / 120;

export interface SnowOptions {
  count: number;
  radius: number; // inner radius of the glass
  center: THREE.Vector3;
  floorY: number; // ground level, in local coords
  /** Optional terrain height; flakes settle on it. */
  groundAt?: (x: number, z: number) => number;
}

export class Snow {
  readonly points: THREE.Points;
  private pos: Float32Array;
  private vel: Float32Array;
  private seed: Float32Array;
  private resting: Uint8Array;
  private acc = 0;
  private time = 0;
  /** When true, the glass is gone: flakes fall freely over the stage. */
  open = false;
  private stir: { origin: THREE.Vector3; dir: THREE.Vector3; push: THREE.Vector3 } | null = null;
  private swirl = 0;
  private opt: SnowOptions;
  private material: THREE.ShaderMaterial;

  constructor(opt: SnowOptions) {
    this.opt = opt;
    const n = opt.count;
    this.pos = new Float32Array(n * 3);
    this.vel = new Float32Array(n * 3);
    this.seed = new Float32Array(n);
    this.resting = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      this.spawn(i, true);
      this.seed[i] = Math.random();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('seed', new THREE.BufferAttribute(this.seed, 1));
    this.material = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uSize: { value: 26 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
        uOpacity: { value: 1 },
      },
      vertexShader: /* glsl */ `
        attribute float seed;
        uniform float uSize;
        uniform float uPixelRatio;
        varying float vSeed;
        void main() {
          vSeed = seed;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv;
          float s = mix(0.55, 1.15, seed);
          gl_PointSize = min(uSize * s * uPixelRatio / -mv.z, 7.0 * uPixelRatio);
        }
      `,
      fragmentShader: /* glsl */ `
        uniform float uOpacity;
        varying float vSeed;
        void main() {
          float d = length(gl_PointCoord - 0.5);
          float a = smoothstep(0.5, 0.15, d);
          gl_FragColor = vec4(vec3(1.0), a * mix(0.55, 0.95, vSeed) * uOpacity);
        }
      `,
    });
    this.points = new THREE.Points(geo, this.material);
    this.points.frustumCulled = false;
    this.points.renderOrder = 2;
  }

  setPointScale(px: number) {
    this.material.uniforms.uSize.value = px;
  }

  private spawn(i: number, anywhere: boolean) {
    const { radius, center, floorY } = this.opt;
    const k = i * 3;
    if (this.open) {
      const r = Math.sqrt(Math.random()) * radius * 1.6;
      const a = Math.random() * Math.PI * 2;
      this.pos[k] = center.x + Math.cos(a) * r;
      this.pos[k + 1] = anywhere ? floorY + Math.random() * radius * 1.6 : floorY + radius * 1.6;
      this.pos[k + 2] = center.z + Math.sin(a) * r;
    } else {
      // Uniform inside the sphere, above the floor.
      for (;;) {
        const x = (Math.random() * 2 - 1) * radius;
        const y = (Math.random() * 2 - 1) * radius;
        const z = (Math.random() * 2 - 1) * radius;
        if (x * x + y * y + z * z < radius * radius * 0.9 && center.y + y > this.ground(center.x + x, center.z + z) + 0.02) {
          this.pos[k] = center.x + x;
          this.pos[k + 1] = center.y + y;
          this.pos[k + 2] = center.z + z;
          break;
        }
      }
    }
    this.vel[k] = this.vel[k + 1] = this.vel[k + 2] = 0;
    this.resting[i] = 0;
  }

  /** A ray through the cursor (local coords) and how much it moved. */
  setStir(origin: THREE.Vector3, dir: THREE.Vector3, push: THREE.Vector3) {
    this.stir = { origin: origin.clone(), dir: dir.clone().normalize(), push: push.clone() };
  }

  /** Spin of the globe around Y, in rad/s; drags the air along. */
  setSwirl(w: number) {
    this.swirl = w;
  }

  /** Kick every flake (used when the glass breaks). */
  burst(from: THREE.Vector3, strength: number) {
    const n = this.opt.count;
    for (let i = 0; i < n; i++) {
      const k = i * 3;
      const dx = this.pos[k] - from.x;
      const dy = this.pos[k + 1] - from.y;
      const dz = this.pos[k + 2] - from.z;
      const d = Math.hypot(dx, dy, dz) + 0.2;
      const s = strength / (d * d + 0.5);
      this.vel[k] += (dx / d) * s * 0.4;
      this.vel[k + 1] += Math.abs(dy / d) * s * 0.6 + 0.3 * strength;
      this.vel[k + 2] += (dz / d) * s * 0.4;
      this.resting[i] = 0;
    }
  }

  update(dt: number) {
    this.acc = Math.min(this.acc + dt, STEP * 8);
    while (this.acc >= STEP) {
      this.step(STEP);
      this.acc -= STEP;
    }
    (this.points.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    this.stir = null;
  }

  private step(h: number) {
    this.time += h;
    const { radius, center, floorY } = this.opt;
    const n = this.opt.count;
    const p = this.pos;
    const v = this.vel;
    const g = this.open ? 0.32 : 0.22;
    const drag = this.open ? 1.4 : 2.2;
    const t = this.time;
    const stir = this.stir;
    const r2 = radius * radius;
    const tmp = new THREE.Vector3();

    for (let i = 0; i < n; i++) {
      const k = i * 3;
      let x = p[k], y = p[k + 1], z = p[k + 2];
      let vx = v[k], vy = v[k + 1], vz = v[k + 2];
      const s = this.seed[i];

      // Cursor stir: flakes near the ray get pushed along the cursor motion.
      if (stir) {
        tmp.set(x - stir.origin.x, y - stir.origin.y, z - stir.origin.z);
        const along = tmp.dot(stir.dir);
        tmp.addScaledVector(stir.dir, -along);
        const d2 = tmp.lengthSq();
        if (d2 < 0.16) {
          const w = (1 - d2 / 0.16) * (0.7 + s * 0.6);
          vx += stir.push.x * w;
          vy += stir.push.y * w + Math.abs(stir.push.length()) * w * 0.35;
          vz += stir.push.z * w;
          this.resting[i] = 0;
        }
      }

      if (this.resting[i]) continue;

      // Swirl from rotating the globe (only while enclosed).
      if (!this.open && this.swirl !== 0) {
        const rx = x - center.x, rz = z - center.z;
        vx += -rz * this.swirl * 1.6 * h;
        vz += rx * this.swirl * 1.6 * h;
        vy += Math.abs(this.swirl) * 0.4 * h;
      }

      // Gravity, drag, and a gentle flutter so the fall isn't mechanical.
      vy -= g * (0.6 + s * 0.6) * h;
      vx += Math.sin(t * (0.9 + s) + s * 40) * 0.05 * h;
      vz += Math.cos(t * (0.7 + s) + s * 17) * 0.05 * h;
      const damp = Math.exp(-drag * h);
      vx *= damp;
      vy *= damp;
      vz *= damp;

      x += vx * h;
      y += vy * h;
      z += vz * h;

      // Glass boundary: reflect the normal velocity with restitution.
      if (!this.open) {
        const dx = x - center.x, dy = y - center.y, dz = z - center.z;
        const d2 = dx * dx + dy * dy + dz * dz;
        const lim = r2 * 0.92;
        if (d2 > lim) {
          const d = Math.sqrt(d2);
          const nx = dx / d, ny = dy / d, nz = dz / d;
          const target = Math.sqrt(lim);
          x = center.x + nx * target;
          y = center.y + ny * target;
          z = center.z + nz * target;
          const vn = vx * nx + vy * ny + vz * nz;
          if (vn > 0) {
            vx -= 1.4 * vn * nx;
            vy -= 1.4 * vn * ny;
            vz -= 1.4 * vn * nz;
          }
        }
      }

      // Settle on the stage.
      const fy = this.ground(x, z) + 0.004 + s * 0.004;
      if (y < fy) {
        const rx = x - center.x, rz = z - center.z;
        const onStage = rx * rx + rz * rz < (this.open ? r2 * 0.6 : r2);
        if (onStage) {
          y = fy;
          vx = vy = vz = 0;
          this.resting[i] = 1;
        } else if (y < floorY - 0.6) {
          this.spawn(i, false);
          continue;
        }
      }

      p[k] = x; p[k + 1] = y; p[k + 2] = z;
      v[k] = vx; v[k + 1] = vy; v[k + 2] = vz;
    }

    // Once open, slowly recycle settled flakes so the snowfall continues.
    if (this.open) {
      const i = Math.floor(Math.random() * n);
      if (this.resting[i] && Math.random() < 0.5) this.spawn(i, false);
    }
  }

  private ground(x: number, z: number) {
    return this.opt.groundAt ? this.opt.groundAt(x, z) : this.opt.floorY;
  }

  setOpacity(o: number) {
    this.material.uniforms.uOpacity.value = o;
  }
}
