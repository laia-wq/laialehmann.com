import * as THREE from 'three';
import { studioScene } from './studio';
import { glass, glassBack, noDirectSpecular } from './materials';
import { crackMaterial, fractureSphere, type Fracture } from './fracture';
import { ShatterSim } from './shatter';
import { buildPedestal, type Pedestal } from './pedestal';
import type { Interior } from './interior';
import { buildBlenderWorld } from './world';
import { contactBlob, paperBackdrop, shadowCatcher } from './setting';
import { Post } from './post';
import type { Project } from '../content/projects';

export type Phase = 'globe' | 'cracking' | 'shattering' | 'world' | 'focus';

export interface ExperienceEvents {
  onPhase(phase: Phase): void;
  onSelect(id: string): void;
  onHover(id: string | null): void;
  /** Screen position of each object's label anchor, every frame in world/focus. */
  onLabels(labels: { id: string; x: number; y: number; visible: boolean }[]): void;
  onWalk?(on: boolean): void;
}

// Scene dimensions (world units, floor at y = 0).
const R = 1;
const CUP_TOP = 0.45 * 0.95; // rim of the wooden base, level with the terrain inside
const CUP_R = 0.87;
const CUT_Y = -Math.sqrt(1 - CUP_R * CUP_R); // relative to the centre: the cup hides the glass below this
const GLOBE_Y = CUP_TOP - CUT_Y;

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const damp = (a: number, b: number, lambda: number, dt: number) => THREE.MathUtils.lerp(a, b, 1 - Math.exp(-lambda * dt));

interface PlacedObject {
  id: string;
  group: THREE.Group;
  hit: THREE.Mesh;
  anchor: THREE.Vector3; // local, label anchor
  hover: number;
}

export class Experience {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(30, 1, 0.01, 60);
  private last = performance.now();
  private root = new THREE.Group(); // rotates with drag
  private globeCenter = new THREE.Vector3(0, GLOBE_Y, 0);
  private glassMesh!: THREE.Mesh;
  private glassMaterial = glass();
  private shardMaterial!: THREE.MeshPhysicalMaterial;
  private shardEdgeMaterial!: THREE.MeshPhysicalMaterial;
  private hitSphere!: THREE.Mesh;
  private pedestal!: Pedestal;
  private backdrop!: { texture: THREE.Texture; fit(aspect: number): void };
  private interior!: Interior;
  private post!: Post;
  private quality: 0 | 1 = 1;
  private frameTimes: number[] = [];
  private fracture: Fracture | null = null;
  private shardGroup = new THREE.Group();
  private crackMesh: THREE.Mesh | null = null;
  private crackMat = crackMaterial();
  private sim: ShatterSim | null = null;
  private impact = new THREE.Vector3(0.35, 0.25, 0.9).normalize();
  private objects: PlacedObject[] = [];
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2(9, 9);
  private phase: Phase = 'globe';
  private events: ExperienceEvents;
  private container: HTMLElement;
  private running = true;
  private raf = 0;

  // Interaction state.
  private yaw = -0.35;
  private yawVel = 0;
  private pitch = 0;
  private drag: { x: number; y: number; moved: boolean; t: number; onGlobe: boolean } | null = null;
  private crack = 0; // 0..1 displayed
  private crackTarget = 0;
  private holding = false;
  private autoBreak = false;
  private breakTime = -1;
  private time = 0;

  // Camera animation.
  private camPos = new THREE.Vector3();
  private camLook = new THREE.Vector3();
  private camFrom = { pos: new THREE.Vector3(), look: new THREE.Vector3() };
  private camTo = { pos: new THREE.Vector3(), look: new THREE.Vector3() };
  private camT = 1;
  private camDur = 1;
  private camVia: THREE.Vector3 | null = null;
  private focused: string | null = null;
  private hovered: string | null = null;
  // Free camera inside the world: orbit (drag), zoom (wheel / pinch),
  // pan (right-drag / two fingers / shift-drag), double-click to fly there.
  private orb = { yaw: 0, pitch: 0.5, dist: 1.6, target: new THREE.Vector3() };
  private orbGoal = { yaw: 0, pitch: 0.5, dist: 1.6, target: new THREE.Vector3() };
  // Walk mode: a small person on the island.
  private walking = false;
  private walker = { pos: new THREE.Vector3(), heading: 0, pitch: -0.05, y: 0 };
  private keys = new Set<string>();
  private touches = new Map<number, { x: number; y: number; sx: number; sy: number; stick: boolean }>();
  private pinch: { d: number; cx: number; cy: number } | null = null;

  constructor(container: HTMLElement, projects: Project[], events: ExperienceEvents) {
    this.container = container;
    this.events = events;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    // Full-resolution transmission so the world seen through the glass is crisp, not hazy.
    (this.renderer as THREE.WebGLRenderer & { transmissionResolutionScale?: number }).transmissionResolutionScale = 1;
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.domElement.setAttribute('aria-hidden', 'true');
    this.renderer.domElement.className = 'scene-canvas';
    container.appendChild(this.renderer.domElement);

    this.backdrop = paperBackdrop();
    this.scene.background = this.backdrop.texture;
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(studioScene(), 0, 0.1, 100, { size: 512 }).texture;
    this.scene.environmentIntensity = 0.55;
    pmrem.dispose();

    void projects; // miniatures arrive with the landscape (Phase B)
    this.buildLights();
    this.pedestal = buildPedestal('Laia Lehmann', 'Systems Design Engineering');
    this.root.add(this.pedestal.group);
    const t0 = performance.now();
    this.interior = buildBlenderWorld(this.globeCenter, this.renderer);
    if (new URLSearchParams(location.search).has('debug')) console.info(`interior built in ${(performance.now() - t0).toFixed(0)} ms`);
    this.root.add(this.interior.group);
    this.buildGlobe();
    this.scene.add(this.root);

    const qp = new URLSearchParams(location.search).get('quality');
    const lowPower = qp === 'low' || (qp !== 'high' && (navigator.hardwareConcurrency ?? 8) <= 4);
    this.quality = lowPower ? 0 : 1;
    this.post = new Post(this.renderer, this.scene, this.camera, this.quality);
    this.post.aoExclude = [this.glassMesh, this.shardGroup, ...this.interior.transparents];
    // The world's transparent bits (mist, water, glows) arrive once it loads.
    void this.interior.ready.then(() => { this.post.aoExclude = [this.glassMesh, this.shardGroup, ...this.interior.transparents]; if (this.crackMesh) this.post.aoExclude.push(this.crackMesh); });

    this.setCameraForGlobe(true);
    this.bindEvents();
    this.resize();
    new ResizeObserver(() => this.resize()).observe(container);
    document.addEventListener('visibilitychange', () => {
      this.running = !document.hidden;
      if (this.running) { this.last = performance.now(); this.loop(); }
    });
    this.loop();
  }

  // ---------------------------------------------------------------- build

  private buildLights() {
    // Daylight in a quiet room: soft fill, a warm key, a cool rim.
    this.scene.add(new THREE.HemisphereLight('#ffd9cc', '#6e504a', 0.55));
    // Golden-hour key, low from the back-left: rims the trees and throws long shadows.
    const key = new THREE.DirectionalLight('#ffb57a', 3.6);
    key.position.set(-4.4, 4.6, -1.2);
    key.target.position.set(0, 0.9, 0);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3.2, bottom: -3, near: 1, far: 18 });
    key.shadow.radius = 6;
    key.shadow.blurSamples = 24;
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.015;
    this.scene.add(key, key.target);
    const rim = new THREE.DirectionalLight('#f2b8c8', 1.1);
    rim.position.set(4, 3.5, -4.5);
    const front = new THREE.DirectionalLight('#ffd8bf', 1.1);
    front.position.set(-1.5, 3, 5);
    this.scene.add(front);
    this.scene.add(rim);
    const fill = new THREE.DirectionalLight('#f0c8d0', 0.45);
    fill.position.set(4, 1.5, 4);
    this.scene.add(fill);

    this.scene.add(shadowCatcher());
    this.scene.add(contactBlob(2.2, 0.55));
  }

  private buildGlobe() {
    const theta = Math.acos(CUT_Y);
    this.glassMesh = new THREE.Mesh(new THREE.SphereGeometry(R, 128, 96, 0, Math.PI * 2, 0, theta), this.glassMaterial);
    this.glassMesh.position.copy(this.globeCenter);
    this.glassMesh.renderOrder = 3;
    this.glassMesh.castShadow = false;
    const back = new THREE.Mesh(this.glassMesh.geometry, glassBack());
    back.renderOrder = 1;
    this.glassMesh.add(back);
    this.root.add(this.glassMesh);

    this.hitSphere = new THREE.Mesh(new THREE.SphereGeometry(R, 24, 16), new THREE.MeshBasicMaterial({ visible: false }));
    this.hitSphere.position.copy(this.globeCenter);
    this.root.add(this.hitSphere);

    // Glass needn't write depth: the glows inside must still draw over it.
    this.glassMaterial.depthWrite = false;
    // Shards: clear faces that mostly reflect, and greenish edges like cut glass.
    // (Cheaper than transmission and it reads better while moving.)
    this.shardMaterial = new THREE.MeshPhysicalMaterial({
      color: '#f4f8f7',
      roughness: 0.02,
      metalness: 0,
      transparent: true,
      opacity: 0.07,
      envMapIntensity: 2.4,
      specularIntensity: 1,
      ior: 1.5,
      clearcoat: 1,
      clearcoatRoughness: 0.02,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.shardEdgeMaterial = new THREE.MeshPhysicalMaterial({
      color: '#f3e6d6',
      roughness: 0.08,
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
      envMapIntensity: 1.2,
    });
    this.shardMaterial.onBeforeCompile = noDirectSpecular;
    this.shardEdgeMaterial.onBeforeCompile = noDirectSpecular;
    // Until it actually breaks, the clear sphere stays; only the cracks show.
    this.shardGroup.visible = false;
    this.root.add(this.shardGroup);

  }

  // ---------------------------------------------------------------- camera

  private globeView() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const hh = 1.82; // half the height to frame (stand + sphere + room for the label)
    const hw = aspect < 0.8 ? 1.18 : 1.4;
    const dist = Math.max(hh / t, hw / (t * aspect));
    // Look a little below the middle so the label has room under the stand.
    const look = new THREE.Vector3(0, aspect < 0.8 ? 0.98 : 1.05, 0);
    return { pos: new THREE.Vector3(0, look.y + dist * 0.12, dist), look };
  }

  /** Default free-camera framing once inside: the whole island, fairly close. */
  private resetOrbit() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const dist = Math.max(0.55 / t, 0.92 / (t * aspect));
    this.orbGoal.yaw = 0;
    this.orbGoal.pitch = 0.42;
    this.orbGoal.dist = dist;
    this.orbGoal.target.set(0, this.interior.groundY + 0.12, -0.02).add(new THREE.Vector3(0, 0, 0));
    this.orb.yaw = this.orbGoal.yaw; this.orb.pitch = this.orbGoal.pitch; this.orb.dist = this.orbGoal.dist;
    this.orb.target.copy(this.orbGoal.target);
  }

  private orbitPose(o: { yaw: number; pitch: number; dist: number; target: THREE.Vector3 }) {
    const cp = Math.cos(o.pitch);
    const pos = o.target.clone().add(new THREE.Vector3(Math.sin(o.yaw) * cp, Math.sin(o.pitch), Math.cos(o.yaw) * cp).multiplyScalar(o.dist));
    return { pos, look: o.target.clone() };
  }

  private worldView() {
    return this.orbitPose(this.orbGoal);
  }

  private static EYE = 0.017;

  private walkPose() {
    const w = this.walker;
    const pos = new THREE.Vector3(w.pos.x, w.y, w.pos.z);
    const dir = new THREE.Vector3(-Math.sin(w.heading) * Math.cos(w.pitch), Math.sin(w.pitch), -Math.cos(w.heading) * Math.cos(w.pitch));
    return { pos, look: pos.clone().add(dir) };
  }

  /** Point on the island under a screen position (ray-marched against the heightmap). */
  private groundUnder(ndc: THREE.Vector2): THREE.Vector3 | null {
    this.raycaster.setFromCamera(ndc, this.camera);
    const { origin, direction } = this.raycaster.ray;
    const p = new THREE.Vector3();
    let prev = origin.clone();
    for (let s = 0.004; s < 6; s *= 1.04) {
      p.copy(origin).addScaledVector(direction, s);
      if (Math.hypot(p.x, p.z) < this.interior.radius && p.y < this.interior.groundAt(p.x, p.z)) {
        // Refine between prev and p.
        let a = prev.clone(), b = p.clone();
        for (let k = 0; k < 12; k++) {
          const m = a.clone().lerp(b, 0.5);
          if (m.y < this.interior.groundAt(m.x, m.z)) b = m; else a = m;
        }
        return b;
      }
      prev.copy(p);
    }
    return null;
  }

  get isWalking() {
    return this.walking;
  }

  /** Toggle walk mode (a small person on the island) from the UI. */
  setWalk(on: boolean) {
    if (this.phase !== 'world' || on === this.walking) return;
    this.walking = on;
    if (on) {
      const t = this.orb.target;
      const r = Math.hypot(t.x, t.z), max = this.interior.radius * 0.9;
      this.walker.pos.set(t.x, 0, t.z);
      if (r > max) this.walker.pos.multiplyScalar(max / r);
      this.walker.heading = this.orb.yaw;
      this.walker.pitch = -0.05;
      this.walker.y = this.interior.groundAt(this.walker.pos.x, this.walker.pos.z) + Experience.EYE;
      const v = this.walkPose();
      this.tweenCamera(v.pos, v.look, 1.4);
    } else {
      this.orbGoal.target.set(this.walker.pos.x, this.walker.y - Experience.EYE * 0.5, this.walker.pos.z);
      this.orbGoal.yaw = this.walker.heading;
      this.orbGoal.pitch = 0.5;
      this.orbGoal.dist = 0.35;
      Object.assign(this.orb, { yaw: this.orbGoal.yaw, pitch: this.orbGoal.pitch, dist: this.orbGoal.dist });
      this.orb.target.copy(this.orbGoal.target);
      const v = this.orbitPose(this.orbGoal);
      this.tweenCamera(v.pos, v.look, 1.2);
    }
    this.events.onWalk?.(on);
  }

  private focusView(id: string) {
    const o = this.objects.find((x) => x.id === id)!;
    const p = o.group.getWorldPosition(new THREE.Vector3());
    const look = p.clone().add(new THREE.Vector3(0, 0.1, 0));
    const wide = this.camera.aspect > 1.1;
    const dir = new THREE.Vector3(0, 0.28, 1).normalize();
    const pos = look.clone().addScaledVector(dir, wide ? 1.9 : 2.9);
    if (wide) {
      // Shift so the object sits in the left part of the screen, beside the panel.
      const right = new THREE.Vector3(1, 0, 0);
      look.addScaledVector(right, 0.3);
      pos.addScaledVector(right, 0.3);
    } else {
      // Panel is a bottom sheet: push the object up.
      look.y -= 0.42;
      pos.y -= 0.42;
    }
    return { pos, look };
  }

  private setCameraForGlobe(instant = false) {
    const v = this.globeView();
    if (instant) {
      this.camPos.copy(v.pos);
      this.camLook.copy(v.look);
      this.camT = 1;
    } else this.tweenCamera(v.pos, v.look, 1.2);
  }

  private tweenCamera(pos: THREE.Vector3, look: THREE.Vector3, dur: number, via: THREE.Vector3 | null = null) {
    this.camFrom.pos.copy(this.camPos);
    this.camFrom.look.copy(this.camLook);
    this.camTo.pos.copy(pos);
    this.camTo.look.copy(look);
    this.camVia = via;
    this.camT = 0;
    this.camDur = dur;
  }

  private updateCamera(dt: number) {
    if (this.camT < 1) {
      this.camT = Math.min(1, this.camT + dt / this.camDur);
      const e = ease(this.camT);
      if (this.camVia) {
        // Quadratic Bézier through `via` for the dive.
        const a = this.camFrom.pos, b = this.camVia, c = this.camTo.pos;
        const u = 1 - e;
        this.camPos.set(
          u * u * a.x + 2 * u * e * b.x + e * e * c.x,
          u * u * a.y + 2 * u * e * b.y + e * e * c.y,
          u * u * a.z + 2 * u * e * b.z + e * e * c.z,
        );
      } else this.camPos.lerpVectors(this.camFrom.pos, this.camTo.pos, e);
      this.camLook.lerpVectors(this.camFrom.look, this.camTo.look, e);
    }
    else if (this.phase === 'world') {
      if (this.walking) this.updateWalk(dt);
      else {
        const o = this.orb, g = this.orbGoal;
        o.yaw = damp(o.yaw, g.yaw, 12, dt);
        o.pitch = damp(o.pitch, g.pitch, 12, dt);
        o.dist = Math.exp(damp(Math.log(o.dist), Math.log(g.dist), 9, dt));
        o.target.lerp(g.target, 1 - Math.exp(-9 * dt));
      }
      const v = this.walking ? this.walkPose() : this.orbitPose(this.orb);
      if (!this.walking) {
        // Never dip under the ground.
        const floor = this.interior.groundAt(v.pos.x, v.pos.z) + 0.006;
        if (Math.hypot(v.pos.x, v.pos.z) < this.interior.radius && v.pos.y < floor) v.pos.y = floor;
      }
      this.camPos.copy(v.pos);
      this.camLook.copy(v.look);
    }
    // Near plane follows the scale we're looking at (walking is tiny).
    const near = this.walking ? 0.0012 : this.phase === 'world' ? Math.max(0.002, Math.min(0.01, this.orb.dist * 0.02)) : 0.01;
    if (Math.abs(this.camera.near - near) > 1e-5) { this.camera.near = near; this.camera.updateProjectionMatrix(); }
    // A touch of parallax from the cursor in the globe view.
    const par = this.phase === 'globe' || this.phase === 'cracking' ? 0.05 : 0;
    const px = THREE.MathUtils.clamp(this.pointer.x, -1, 1) * par;
    const py = THREE.MathUtils.clamp(this.pointer.y, -1, 1) * par;
    const inWorld = this.phase === 'world' || this.phase === 'focus';
    this.camera.position.set(this.camPos.x + px, this.camPos.y + py + (inWorld ? 0 : this.pitch), this.camPos.z);
    this.camera.lookAt(this.camLook);
  }

  private updateWalk(dt: number) {
    const w = this.walker;
    let f = 0, s = 0;
    const k = this.keys;
    if (k.has('KeyW') || k.has('ArrowUp')) f += 1;
    if (k.has('KeyS') || k.has('ArrowDown')) f -= 1;
    if (k.has('KeyA')) s -= 1;
    if (k.has('KeyD')) s += 1;
    if (k.has('ArrowLeft')) w.heading += dt * 1.6;
    if (k.has('ArrowRight')) w.heading -= dt * 1.6;
    // Touch: a virtual stick wherever a finger went down on the left third.
    for (const t of this.touches.values()) {
      if (!t.stick) continue;
      f += THREE.MathUtils.clamp(-(t.y - t.sy) / 60, -1, 1);
      s += THREE.MathUtils.clamp((t.x - t.sx) / 60, -1, 1);
    }
    const speed = (k.has('ShiftLeft') || k.has('ShiftRight') ? 0.09 : 0.04) * dt;
    const fx = -Math.sin(w.heading), fz = -Math.cos(w.heading);
    w.pos.x += (fx * f - fz * s) * speed;
    w.pos.z += (fz * f + fx * s) * speed;
    const r = Math.hypot(w.pos.x, w.pos.z), max = this.interior.radius * 0.95;
    if (r > max) w.pos.multiplyScalar(max / r);
    const ground = this.interior.groundAt(w.pos.x, w.pos.z) + Experience.EYE;
    w.y = damp(w.y || ground, ground, 14, dt);
  }

  // ---------------------------------------------------------------- public API

  get currentPhase() {
    return this.phase;
  }

  /** Start the break from the button or keyboard: cracks grow, then shatter. */
  breakGlass() {
    if (this.phase !== 'globe' && this.phase !== 'cracking') return;
    if (!this.fracture) this.prepareFracture(this.defaultImpact());
    this.autoBreak = true;
  }

  /** Skip everything and go straight to the world. */
  skip() {
    if (this.phase === 'world' || this.phase === 'focus') return;
    this.glassMesh.visible = false;
    this.shardGroup.visible = false;
    if (this.crackMesh) this.crackMesh.visible = false;
    this.yaw = 0;
    this.yawVel = 0;
    this.resetOrbit();
    const v = this.worldView();
    this.camPos.copy(v.pos);
    this.camLook.copy(v.look);
    this.camT = 1;
    this.setPhase('world');
  }

  focus(id: string) {
    if (!this.objects.find((o) => o.id === id)) return;
    if (this.phase !== 'world' && this.phase !== 'focus') this.skip();
    this.focused = id;
    const v = this.focusView(id);
    this.tweenCamera(v.pos, v.look, 1.1);
    this.setPhase('focus');
  }

  unfocus() {
    if (this.phase !== 'focus') return;
    this.focused = null;
    Object.assign(this.orb, { yaw: this.orbGoal.yaw, pitch: this.orbGoal.pitch, dist: this.orbGoal.dist });
    this.orb.target.copy(this.orbGoal.target);
    const v = this.orbitPose(this.orbGoal);
    this.tweenCamera(v.pos, v.look, 1.0);
    this.setPhase('world');
  }

  hasObject(id: string) {
    return this.objects.some((o) => o.id === id);
  }

  private setPhase(p: Phase) {
    this.phase = p;
    this.container.dataset.phase = p;
    this.events.onPhase(p);
  }

  // ---------------------------------------------------------------- break

  private defaultImpact() {
    // Upper-right of the side facing the camera, in globe-local coords.
    const v = new THREE.Vector3(0.32, 0.28, 0.9).normalize();
    v.applyAxisAngle(new THREE.Vector3(0, 1, 0), -this.yaw);
    return v;
  }

  private prepareFracture(impact: THREE.Vector3) {
    this.impact.copy(impact);
    this.fracture = fractureSphere({
      radius: R,
      thickness: 0.028,
      center: this.globeCenter,
      impact,
      cutY: CUT_Y,
    });
    for (const sh of this.fracture.shards) {
      const m = new THREE.Mesh(sh.geometry, [this.shardMaterial, this.shardEdgeMaterial]);
      m.position.copy(sh.center);
      m.renderOrder = 3;
      this.shardGroup.add(m);
    }
    this.crackMesh = new THREE.Mesh(this.fracture.cracks, this.crackMat);
    this.crackMesh.renderOrder = 4;
    this.crackMesh.frustumCulled = false;
    this.root.add(this.crackMesh);
    this.post.aoExclude.push(this.crackMesh);
    this.sim = new ShatterSim(this.shardGroup.children as THREE.Mesh[], this.fracture.shards, this.globeCenter, impact, {
      pedestalTop: this.pedestal.baseTop,
      pedestalRadius: this.pedestal.baseRadius,
      collarTop: CUP_TOP,
      collarRadius: CUP_R + 0.03,
      stageTop: this.interior.groundY,
      stageRadius: this.interior.radius,
      floorY: 0,
    });
    this.setPhase('cracking');
  }

  private shatter() {
    if (!this.sim) return;
    this.sim.start();
    // Swap the smooth sphere for the shards at the moment it breaks.
    this.glassMesh.visible = false;
    this.shardGroup.visible = true;
    if (this.crackMesh) this.crackMesh.visible = false;
    this.breakTime = this.time;
    this.yawVel = 0;
    this.setPhase('shattering');
  }

  private updateBreak(dt: number) {
    if (this.phase === 'cracking') {
      if (this.holding) this.crackTarget = Math.min(1, this.crackTarget + dt * 1.15);
      if (this.autoBreak) this.crackTarget = Math.min(1, this.crackTarget + dt * 1.3);
      this.crack = damp(this.crack, this.crackTarget, 10, dt);
      if (this.crackTarget >= 1 && this.crack > 0.97) this.shatter();
      // Crack front in radians from the impact; reaches the far side at 1.
      const front = this.crack * 3.4;
      this.crackMat.uniforms.uProgress.value = front;
      this.sim?.crackPose(front * 0.6);
    }
    if (this.phase === 'shattering') {
      this.sim?.update(dt);
      const since = this.time - this.breakTime;
      if (since > 0.28 && this.camVia === null && this.camT >= 1) {
        // Dive: rise over the broken rim, then swoop down close to the island.
        this.resetOrbit();
        const v = this.worldView();
        // Rise above the sphere's top, then swing down into it.
        const via = new THREE.Vector3(0.15, GLOBE_Y + 1.9, 2.6);
        this.tweenCamera(v.pos, v.look, 3.0, via);
      }
      // Bring the diorama round to face the camera during the dive.
      this.yaw = damp(this.yaw, Math.round(this.yaw / (Math.PI * 2)) * Math.PI * 2, 1.6, dt);
      const fade = THREE.MathUtils.clamp((since - 2.0) / 1.2, 0, 1);
      this.shardMaterial.opacity = 0.07 * (1 - fade);
      this.shardEdgeMaterial.opacity = 0.35 * (1 - fade);
      if (since > 3.6) {
        this.shardGroup.visible = false;
        this.yaw = 0;
        this.camVia = null;
        this.setPhase('world');
      }
    }
  }

  // ---------------------------------------------------------------- input

  private bindEvents() {
    const el = this.renderer.domElement;
    el.addEventListener('pointerdown', (e) => this.onDown(e));
    window.addEventListener('pointermove', (e) => this.onMove(e));
    window.addEventListener('pointerup', (e) => this.onUp(e));
    window.addEventListener('pointercancel', (e) => { this.drag = null; this.holding = false; this.touches.delete(e.pointerId); this.pinch = null; });
    el.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });
    el.addEventListener('dblclick', (e) => this.onDouble(e));
    el.addEventListener('contextmenu', (e) => { if (this.phase === 'world') e.preventDefault(); });
    window.addEventListener('keydown', (e) => {
      if (this.phase !== 'world') return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
      if (e.code === 'Escape' && this.walking) { this.setWalk(false); return; }
      if (this.walking && /^(Key[WASD]|Arrow(Up|Down|Left|Right)|Shift(Left|Right))$/.test(e.code)) {
        this.keys.add(e.code);
        e.preventDefault();
      }
    });
    window.addEventListener('keyup', (e) => this.keys.delete(e.code));
    window.addEventListener('blur', () => this.keys.clear());
    el.addEventListener('pointerleave', () => { this.pointer.set(9, 9); this.setHover(null); });
  }

  private setPointer(e: PointerEvent) {
    const r = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  }

  private hitGlobe(): THREE.Intersection | null {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObject(this.hitSphere, false);
    return hits[0] ?? null;
  }

  private hitObject(): string | null {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.objects.map((o) => o.hit), false);
    return hits[0] ? (hits[0].object.userData.id as string) : null;
  }

  private onDown(e: PointerEvent) {
    this.setPointer(e);
    if (e.pointerType === 'touch') {
      const r = this.renderer.domElement.getBoundingClientRect();
      const stick = this.walking && e.clientX - r.left < r.width * 0.38;
      this.touches.set(e.pointerId, { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, stick });
      const pts = [...this.touches.values()].filter((t) => !t.stick);
      if (pts.length === 2 && this.phase === 'world' && !this.walking) {
        this.pinch = { d: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y), cx: (pts[0].x + pts[1].x) / 2, cy: (pts[0].y + pts[1].y) / 2 };
        this.drag = null;
        return;
      }
      if (stick) return;
    }
    const onGlobe = (this.phase === 'globe' || this.phase === 'cracking') && !!this.hitGlobe();
    this.drag = { x: e.clientX, y: e.clientY, moved: false, t: performance.now(), onGlobe };
    Object.assign(this.drag, { px: e.clientX, py: e.clientY, pan: e.button === 2 });
    this.renderer.domElement.setPointerCapture?.(e.pointerId);
  }

  private onMove(e: PointerEvent) {
    this.setPointer(e);
    const tp = this.touches.get(e.pointerId);
    if (tp) {
      tp.x = e.clientX; tp.y = e.clientY;
      if (tp.stick) return;
      if (this.pinch) {
        const pts = [...this.touches.values()].filter((t) => !t.stick);
        if (pts.length >= 2) {
          const dd = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
          const cx = (pts[0].x + pts[1].x) / 2, cy = (pts[0].y + pts[1].y) / 2;
          this.zoomBy(this.pinch.d / Math.max(dd, 1));
          this.panBy(cx - this.pinch.cx, cy - this.pinch.cy);
          this.pinch = { d: dd, cx, cy };
        }
        return;
      }
    }
    const d = this.drag;
    if (d) {
      const dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (!d.moved && Math.hypot(dx, dy) > 6) {
        d.moved = true;
        this.holding = false;
      }
      const mx = e.clientX - (d as { px?: number }).px!, my = e.clientY - (d as { py?: number }).py!;
      (d as { px?: number }).px = e.clientX; (d as { py?: number }).py = e.clientY;
      if (d.moved && (this.phase === 'globe' || this.phase === 'cracking')) {
        const k = 0.008;
        this.yawVel = mx * k * 60;
        this.yaw += mx * k;
        this.pitch = THREE.MathUtils.clamp(this.pitch + my * 0.002, -0.25, 0.35);
      } else if (d.moved && this.phase === 'world') {
        if (this.walking) {
          this.walker.heading += mx * 0.004;
          this.walker.pitch = THREE.MathUtils.clamp(this.walker.pitch + my * 0.003, -1.2, 1.1);
        } else if ((e.buttons & 2) || e.shiftKey || (d as { pan?: boolean }).pan) {
          this.panBy(mx, my);
        } else {
          this.orbGoal.yaw -= mx * 0.006;
          this.orbGoal.pitch = THREE.MathUtils.clamp(this.orbGoal.pitch + my * 0.004, 0.03, 1.45);
        }
      }
    }
    if (this.phase === 'world') this.setHover(this.hitObject());
  }

  private onUp(e: PointerEvent) {
    const tp = this.touches.get(e.pointerId);
    this.touches.delete(e.pointerId);
    if (this.pinch) { if ([...this.touches.values()].filter((t) => !t.stick).length < 2) this.pinch = null; this.drag = null; return; }
    if (tp?.stick) return;
    const d = this.drag;
    this.drag = null;
    this.holding = false;
    if (!d || d.moved) return;
    this.setPointer(e);
    if (this.phase === 'world' || this.phase === 'focus') {
      const id = this.hitObject();
      if (id) this.events.onSelect(id);
    } else if (d.onGlobe && performance.now() - d.t < 220) {
      // A tap knocks the glass: each knock spreads the cracks further.
      this.knock();
    }
  }

  private panBy(dx: number, dy: number) {
    const g = this.orbGoal;
    const h = this.renderer.domElement.clientHeight || 800;
    const k = (2 * g.dist * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2))) / h;
    const right = new THREE.Vector3(Math.cos(g.yaw), 0, -Math.sin(g.yaw));
    const fwd = new THREE.Vector3(-Math.sin(g.yaw), 0, -Math.cos(g.yaw));
    g.target.addScaledVector(right, -dx * k).addScaledVector(fwd, dy * k / Math.max(Math.sin(g.pitch), 0.35));
    const r = Math.hypot(g.target.x, g.target.z), max = this.interior.radius;
    if (r > max) { g.target.x *= max / r; g.target.z *= max / r; }
    const floor = this.interior.groundAt(g.target.x, g.target.z) + 0.01;
    g.target.y = THREE.MathUtils.clamp(g.target.y, floor, floor + 0.5);
  }

  private zoomBy(f: number) {
    const g = this.orbGoal;
    const before = g.dist;
    g.dist = THREE.MathUtils.clamp(g.dist * f, 0.05, 3.2);
    // Zooming in pulls the pivot toward what's under the cursor.
    if (g.dist < before && this.pointer.x < 5) {
      const hit = this.groundUnder(this.pointer);
      if (hit) {
        hit.y += 0.01;
        g.target.lerp(hit, Math.min(0.6, 1 - g.dist / before) );
      }
    }
  }

  private onWheel(e: WheelEvent) {
    if (this.phase !== 'world') return;
    e.preventDefault();
    this.setPointer(e as unknown as PointerEvent);
    if (this.walking) {
      this.walker.pitch = THREE.MathUtils.clamp(this.walker.pitch - e.deltaY * 0.001, -1.2, 1.1);
      return;
    }
    const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    this.zoomBy(Math.exp(dy * 0.0012));
  }

  private onDouble(e: MouseEvent) {
    if (this.phase !== 'world' || this.walking) return;
    this.setPointer(e as PointerEvent);
    const hit = this.groundUnder(this.pointer);
    if (!hit) return;
    this.orbGoal.target.copy(hit).add(new THREE.Vector3(0, 0.012, 0));
    this.orbGoal.dist = Math.min(this.orbGoal.dist, 0.22);
    this.orbGoal.pitch = Math.min(this.orbGoal.pitch, 0.45);
  }

  private knock() {
    const hit = this.hitGlobe();
    if (!this.fracture) {
      const local = hit ? this.root.worldToLocal(hit.point.clone()).sub(this.globeCenter).normalize() : this.defaultImpact();
      if (local.y < CUT_Y + 0.15) local.y = CUT_Y + 0.15;
      this.prepareFracture(local.normalize());
    }
    this.crackTarget = Math.min(1, this.crackTarget + 0.34);
  }

  private setHover(id: string | null) {
    if (id === this.hovered) return;
    this.hovered = id;
    this.renderer.domElement.style.cursor = id ? 'pointer' : '';
    this.events.onHover(id);
  }

  private updateInput(dt: number) {
    // Start growing cracks once the press has been held still.
    const d = this.drag;
    if (d && d.onGlobe && !d.moved && !this.holding && performance.now() - d.t > 220) {
      if (!this.fracture) {
        const hit = this.hitGlobe();
        const local = hit ? this.root.worldToLocal(hit.point.clone()).sub(this.globeCenter).normalize() : this.defaultImpact();
        if (local.y < CUT_Y + 0.15) local.y = CUT_Y + 0.15;
        this.prepareFracture(local.normalize());
      }
      this.holding = true;
    }
    this.renderer.domElement.style.cursor =
      this.phase === 'globe' || this.phase === 'cracking' ? (this.hitGlobe() ? 'grab' : '') : this.hovered ? 'pointer' : '';

    if (!this.drag && (this.phase === 'globe' || this.phase === 'cracking')) {
      // Inertia, then a slow idle turn.
      this.yawVel = damp(this.yawVel, this.phase === 'globe' ? 0.06 : 0, 1.5, dt);
      this.yaw += this.yawVel * dt;
      this.pitch = damp(this.pitch, 0, 2, dt);
    }
    if (this.phase === 'world' && !this.drag) this.pitch = damp(this.pitch, 0, 2, dt);
    if (this.phase === 'focus') {
      this.yaw = damp(this.yaw, 0, 3, dt);
      this.pitch = damp(this.pitch, 0, 3, dt);
    }
    this.root.rotation.y = this.yaw;

  }

  // ---------------------------------------------------------------- loop

  private resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.post?.setSize(w, h);
    this.camera.aspect = w / h;
    this.backdrop.fit(w / h);
    this.camera.updateProjectionMatrix();
    if (this.camT >= 1) {
      const v =
        this.phase === 'world' ? this.worldView()
        : this.phase === 'focus' && this.focused ? this.focusView(this.focused)
        : this.phase === 'shattering' ? null
        : this.globeView();
      if (v) { this.camPos.copy(v.pos); this.camLook.copy(v.look); }
    }
  }

  private loop = () => {
    if (!this.running) return;
    this.raf = requestAnimationFrame(this.loop);
    const now = performance.now();
    const dt = Math.min((now - this.last) / 1000, 1 / 20);
    this.last = now;
    this.tick(dt);
    this.updateFocusBand();
    this.post.render(this.time);
    this.adapt(now);
  };

  /** Keep the tilt-shift sharp band on the subject. */
  private updateFocusBand() {
    const target = this.phase === 'globe' || this.phase === 'cracking' ? this.globeCenter.clone().setY(GLOBE_Y - 0.25) : this.camLook.clone();
    const p = this.root.localToWorld(target).project(this.camera);
    const inGlobe = this.phase === 'globe' || this.phase === 'cracking';
    // Keep the globe fully sharp; only a whisper of tilt-shift once inside.
    this.post.setFocus(p.y * 0.5 + 0.5, inGlobe ? 1.0 : 0.3, inGlobe ? 0.0 : 0.35);
  }

  /** If the first seconds run slowly, drop to the cheaper pipeline. */
  private adapt(now: number) {
    if (this.quality === 0 || this.frameTimes.length > 240 || new URLSearchParams(location.search).get('quality') === 'high') return;
    this.frameTimes.push(now);
    if (this.frameTimes.length === 240) {
      const avg = (this.frameTimes[239] - this.frameTimes[60]) / 179;
      if (avg > 26) {
        this.quality = 0;
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
        this.post = new Post(this.renderer, this.scene, this.camera, 0);
        this.post.aoExclude = [this.glassMesh, this.shardGroup, ...this.interior.transparents];
        this.resize();
      }
    }
  }

  private tick(dt: number) {
    this.time += dt;
    this.updateInput(dt);
    this.updateBreak(dt);
    this.updateCamera(dt);
    this.interior.update(this.time, this.camera);
    this.updateObjects(dt);
  }

  /** Test hook: advance the simulation by `seconds` without rendering each step. */
  debugAdvance(seconds: number) {
    for (let t = 0; t < seconds; t += 1 / 60) this.tick(1 / 60);
    this.last = performance.now();
  }

  private updateObjects(dt: number) {
    const showLabels = this.phase === 'world' || this.phase === 'focus';
    const labels: { id: string; x: number; y: number; visible: boolean }[] = [];
    const v = new THREE.Vector3();
    for (const o of this.objects) {
      const target = o.id === this.hovered && this.phase === 'world' ? 1 : 0;
      o.hover = damp(o.hover, target, 8, dt);
      o.group.position.y = o.group.userData.baseY + o.hover * 0.01;
      o.group.rotation.y = Math.sin(this.time * 0.4) * 0.15 + o.hover * 0.3;
      if (showLabels) {
        v.copy(o.anchor);
        o.group.localToWorld(v);
        v.project(this.camera);
        const w = this.container.clientWidth, h = this.container.clientHeight;
        labels.push({ id: o.id, x: (v.x * 0.5 + 0.5) * w, y: (-v.y * 0.5 + 0.5) * h, visible: v.z < 1 });
      }
    }
    if (showLabels) this.events.onLabels(labels);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.renderer.dispose();
  }
}
