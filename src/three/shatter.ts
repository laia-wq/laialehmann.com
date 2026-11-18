import * as THREE from 'three';
import type { Shard } from './fracture';

/**
 * Rigid-body shards held together by springs, like the tearing springs in my
 * C++ engine. A shatter wave travels outward from the impact; as it reaches a
 * shard it receives an impulse, springs that stretch too far tear, and the
 * freed shards fall under gravity with impulse-based collisions (restitution
 * and friction) against the pedestal and the floor.
 */

const STEP = 1 / 120;
const GRAVITY = 7.5;

interface Body {
  mesh: THREE.Mesh;
  shard: Shard;
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  quat: THREE.Quaternion;
  ang: THREE.Vector3;
  invMass: number;
  invInertia: number;
  kicked: boolean;
  asleep: boolean;
  free: boolean;
}

interface Spring {
  a: number;
  b: number;
  rest: number;
  alive: boolean;
}

export interface Collider {
  /** Pedestal top surface (local y) and radius. */
  pedestalTop: number;
  pedestalRadius: number;
  /** Collar ring around the globe base. */
  collarTop: number;
  collarRadius: number;
  /** The diorama floor inside the globe. */
  stageTop: number;
  stageRadius: number;
  floorY: number;
}

export class ShatterSim {
  bodies: Body[] = [];
  springs: Spring[] = [];
  private acc = 0;
  private t = 0;
  private started = false;
  private center: THREE.Vector3;
  private impact: THREE.Vector3;
  private col: Collider;
  private rnd: () => number;

  constructor(meshes: THREE.Mesh[], shards: Shard[], center: THREE.Vector3, impact: THREE.Vector3, col: Collider) {
    this.center = center.clone();
    this.impact = impact.clone().normalize();
    this.col = col;
    let s = 11;
    this.rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    shards.forEach((sh, i) => {
      const m = 0.5 + sh.area * 4;
      this.bodies.push({
        mesh: meshes[i],
        shard: sh,
        pos: sh.center.clone(),
        vel: new THREE.Vector3(),
        quat: new THREE.Quaternion(),
        ang: new THREE.Vector3(),
        invMass: 1 / m,
        invInertia: 1 / (0.4 * m * Math.max(sh.radius, 0.05) ** 2),
        kicked: false,
        asleep: false,
        free: false,
      });
    });
    shards.forEach((sh, i) => {
      for (const j of sh.neighbors) {
        if (j > i) this.springs.push({ a: i, b: j, rest: sh.center.distanceTo(shards[j].center), alive: true });
      }
    });
  }

  /** Cracking phase: tiny displacement of shards near the impact, proportional to progress. */
  crackPose(progress: number) {
    for (const b of this.bodies) {
      const near = Math.max(0, 1 - b.shard.angle / Math.max(progress, 1e-3));
      const sink = near * near * 0.012 * Math.min(progress, 1);
      b.mesh.position.copy(b.pos).addScaledVector(b.shard.normal, -sink);
      const axis = new THREE.Vector3().crossVectors(b.shard.normal, this.impact);
      if (axis.lengthSq() > 1e-6) b.mesh.quaternion.setFromAxisAngle(axis.normalize(), -near * 0.035 * Math.min(progress, 1));
    }
  }

  start() {
    this.started = true;
    for (const b of this.bodies) b.quat.copy(b.mesh.quaternion), b.pos.copy(b.mesh.position);
  }

  get elapsed() {
    return this.t;
  }

  update(dt: number) {
    if (!this.started) return;
    this.acc = Math.min(this.acc + dt, STEP * 10);
    while (this.acc >= STEP) {
      this.step(STEP);
      this.acc -= STEP;
    }
    for (const b of this.bodies) {
      b.mesh.position.copy(b.pos);
      b.mesh.quaternion.copy(b.quat);
    }
  }

  private step(h: number) {
    this.t += h;
    const waveSpeed = 5.5; // radians per second
    const rnd = this.rnd;

    // Shatter wave: impulse as it reaches each shard.
    for (const b of this.bodies) {
      if (b.kicked || this.t < b.shard.angle / waveSpeed) continue;
      b.kicked = true;
      b.free = true;
      const n = b.shard.normal;
      const near = Math.exp(-(b.shard.angle * b.shard.angle) / 0.6);
      const speed = 0.35 + 1.5 * near + rnd() * 0.3;
      // Outward, a little away from the impact, a little up.
      const away = n.clone().sub(this.impact.clone().multiplyScalar(0.5)).normalize();
      b.vel.addScaledVector(n, speed * 0.6).addScaledVector(away, speed * 0.25);
      // Every shard also drifts outward from the globe's axis, so pieces from
      // the top clear the diorama instead of landing on it.
      const horiz = new THREE.Vector3(n.x, 0, n.z);
      if (horiz.lengthSq() < 0.04) horiz.set(rnd() - 0.5, 0, rnd() - 0.5);
      horiz.normalize();
      b.vel.addScaledVector(horiz, 1.25 + rnd() * 0.5);
      b.vel.y += 0.25 + rnd() * 0.4;
      b.ang.set(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).multiplyScalar(6 * (0.4 + near));
    }

    // Springs: hold unkicked shards in place, tear when stretched.
    for (const s of this.springs) {
      if (!s.alive) continue;
      const A = this.bodies[s.a], B = this.bodies[s.b];
      const d = new THREE.Vector3().subVectors(B.pos, A.pos);
      const len = d.length();
      const stretch = len / s.rest;
      if (stretch > 1.05 || stretch < 0.95) { s.alive = false; continue; }
      if (!A.free || !B.free) continue;
      d.divideScalar(len);
      const rel = new THREE.Vector3().subVectors(B.vel, A.vel).dot(d);
      const f = (len - s.rest) * 900 + rel * 8;
      A.vel.addScaledVector(d, f * A.invMass * h);
      B.vel.addScaledVector(d, -f * B.invMass * h);
    }

    const c = this.col;
    const tmp = new THREE.Vector3();
    const r = new THREE.Vector3();
    const vp = new THREE.Vector3();
    for (const b of this.bodies) {
      if (!b.free || b.asleep) continue;
      b.vel.y -= GRAVITY * h;
      b.vel.multiplyScalar(Math.exp(-0.15 * h));
      b.pos.addScaledVector(b.vel, h);
      // Integrate orientation.
      const w = b.ang;
      const q = new THREE.Quaternion(w.x * h * 0.5, w.y * h * 0.5, w.z * h * 0.5, 0).multiply(b.quat);
      b.quat.set(b.quat.x + q.x, b.quat.y + q.y, b.quat.z + q.z, b.quat.w + q.w).normalize();

      // Contacts: test hull points against the support surfaces.
      let deepest = 0;
      let contact: THREE.Vector3 | null = null;
      for (const hp of b.shard.hull) {
        tmp.copy(hp).applyQuaternion(b.quat).add(b.pos);
        const rr = Math.hypot(tmp.x - this.center.x, tmp.z - this.center.z);
        let ground = c.floorY;
        if (rr < c.stageRadius) ground = c.stageTop;
        else if (rr < c.collarRadius) ground = c.collarTop;
        else if (rr < c.pedestalRadius) ground = c.pedestalTop;
        const pen = ground - tmp.y;
        if (pen > deepest) { deepest = pen; contact = tmp.clone(); }
      }
      if (contact) {
        b.pos.y += deepest;
        contact.y += deepest;
        r.subVectors(contact, b.pos);
        const n = new THREE.Vector3(0, 1, 0);
        vp.copy(b.ang).cross(r).add(b.vel);
        const vn = vp.dot(n);
        if (vn < 0) {
          const rn = new THREE.Vector3().crossVectors(r, n);
          const k = b.invMass + rn.lengthSq() * b.invInertia;
          const e = Math.abs(vn) > 0.8 ? 0.3 : 0.05;
          const jn = (-(1 + e) * vn) / k;
          b.vel.addScaledVector(n, jn * b.invMass);
          b.ang.addScaledVector(rn, jn * b.invInertia);
          // Coulomb friction.
          vp.copy(b.ang).cross(r).add(b.vel);
          const vt = vp.clone().addScaledVector(n, -vp.dot(n));
          const vtl = vt.length();
          if (vtl > 1e-5) {
            const t = vt.divideScalar(vtl);
            const rt = new THREE.Vector3().crossVectors(r, t);
            const kt = b.invMass + rt.lengthSq() * b.invInertia;
            const jt = Math.min(vtl / kt, 0.5 * jn);
            b.vel.addScaledVector(t, -jt * b.invMass);
            b.ang.addScaledVector(rt, -jt * b.invInertia);
          }
        }
        b.ang.multiplyScalar(Math.exp(-3 * h));
        if (b.vel.lengthSq() < 0.002 && b.ang.lengthSq() < 0.02) b.asleep = true;
      }
    }
  }
}
