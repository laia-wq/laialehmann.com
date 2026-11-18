import * as THREE from 'three';
import { studioScene } from './studio';
import { backdropTexture, clay, contactShadow, glass, palette } from './materials';
import { Snow } from './snow';
import { crackMaterial, fractureSphere, type Fracture } from './fracture';
import { ShatterSim } from './shatter';
import { builders } from './objects';
import { plaqueTexture } from './plaque';
import type { Project } from '../content/projects';

export type Phase = 'globe' | 'cracking' | 'shattering' | 'world' | 'focus';

export interface ExperienceEvents {
  onPhase(phase: Phase): void;
  onSelect(id: string): void;
  onHover(id: string | null): void;
  /** Screen position of each object's label anchor, every frame in world/focus. */
  onLabels(labels: { id: string; x: number; y: number; visible: boolean }[]): void;
}

// Scene dimensions (world units, floor at y = 0).
const R = 1;
const PEDESTAL_TOP = 0.9;
const COLLAR_TOP = 1.0;
const GLOBE_Y = 1.6;
const STAGE_Y = 1.08;
const STAGE_R = 0.8;
const CUT_Y = -0.6; // relative to the globe centre: where the collar hides the glass

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
  private pedestalParts: THREE.Mesh[] = [];
  private floorParts: THREE.Mesh[] = [];
  private islandShadow!: THREE.Mesh;
  private snow!: Snow;
  private fracture: Fracture | null = null;
  private shardGroup = new THREE.Group();
  private crackMesh: THREE.Mesh | null = null;
  private crackMat = crackMaterial();
  private sim: ShatterSim | null = null;
  private impact = new THREE.Vector3(0.35, 0.25, 0.9).normalize();
  private objects: PlacedObject[] = [];
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2(9, 9);
  private prevPointerWorld: THREE.Vector3 | null = null;
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
  private worldYaw = 0;

  constructor(container: HTMLElement, projects: Project[], events: ExperienceEvents) {
    this.container = container;
    this.events = events;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.domElement.setAttribute('aria-hidden', 'true');
    this.renderer.domElement.className = 'scene-canvas';
    container.appendChild(this.renderer.domElement);

    this.scene.background = backdropTexture();
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(studioScene(), 0.02).texture;
    this.scene.environmentIntensity = 0.7;
    pmrem.dispose();

    this.buildLights();
    this.buildPedestal();
    this.buildGlobe();
    this.buildWorld(projects);
    this.scene.add(this.root);

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
    const hemi = new THREE.HemisphereLight('#fff8ef', '#d6ccbf', 0.9);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight('#fff3e4', 2.1);
    key.position.set(-3.2, 6.5, 4.2);
    key.target.position.set(0, 1, 0);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = -2.4;
    key.shadow.camera.right = 2.4;
    key.shadow.camera.top = 3;
    key.shadow.camera.bottom = -2;
    key.shadow.camera.near = 2;
    key.shadow.camera.far = 14;
    key.shadow.radius = 6;
    key.shadow.blurSamples = 16;
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    this.scene.add(key, key.target);
    const rim = new THREE.DirectionalLight('#e8eef4', 0.9);
    rim.position.set(4, 3, -4);
    this.scene.add(rim);

    this.floorParts = [];
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.ShadowMaterial({ opacity: 0.09 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);
    const blob = contactShadow(3.4, 0.55);
    blob.position.y = 0.002;
    this.scene.add(blob);
    this.floorParts.push(floor, blob);
  }

  private buildPedestal() {
    const prof = (pts: [number, number][]) => pts.map(([x, y]) => new THREE.Vector2(x, y));
    const ped = new THREE.Mesh(
      new THREE.LatheGeometry(
        prof([
          [0, 0], [0.985, 0], [1.0, 0.012], [1.003, 0.055], [0.99, 0.072], [0.975, 0.08],
          [0.9, 0.78], [0.912, 0.79], [0.926, 0.82], [0.928, 0.86], [0.915, 0.89],
          [0.9, PEDESTAL_TOP], [0, PEDESTAL_TOP],
        ]),
        128,
      ),
      clay(palette.porcelain, 0.55),
    );
    ped.castShadow = true;
    ped.receiveShadow = true;
    this.root.add(ped);
    this.pedestalParts.push(ped);

    const collar = new THREE.Mesh(
      new THREE.LatheGeometry(
        prof([
          [0.78, PEDESTAL_TOP], [0.86, PEDESTAL_TOP], [0.868, 0.915], [0.868, 0.975],
          [0.858, 0.993], [0.84, COLLAR_TOP], [0.78, COLLAR_TOP],
        ]),
        128,
      ),
      clay(palette.bone, 0.5),
    );
    collar.castShadow = true;
    collar.receiveShadow = true;
    this.root.add(collar);
    this.pedestalParts.push(collar);

    // Engraved plaque on the front, following the pedestal curve.
    // The side tapers, so the plaque is a matching frustum segment.
    const arc = 0.74;
    const sideR = (y: number) => 0.975 - ((y - 0.08) * 0.075) / 0.7 + 0.003;
    const py = 0.43, ph = 0.25;
    const plaqueGeo = new THREE.CylinderGeometry(sideR(py + ph / 2), sideR(py - ph / 2), ph, 48, 1, true, -arc / 2, arc);
    const plaque = new THREE.Mesh(plaqueGeo, clay('#ffffff', 0.6));
    plaque.position.y = py;
    plaque.receiveShadow = true;
    plaque.visible = false;
    plaque.userData.loaded = false;
    this.root.add(plaque);
    this.pedestalParts.push(plaque);
    plaqueTexture('Laia Lehmann', 'Systems Design Engineering').then((tex) => {
      const m = plaque.material as THREE.MeshPhysicalMaterial;
      m.map = tex;
      m.needsUpdate = true;
      plaque.userData.loaded = true;
      plaque.visible = m.opacity > 0.001;
    });
  }

  private buildGlobe() {
    const theta = Math.acos(CUT_Y);
    this.glassMesh = new THREE.Mesh(new THREE.SphereGeometry(R, 128, 96, 0, Math.PI * 2, 0, theta), this.glassMaterial);
    this.glassMesh.position.copy(this.globeCenter);
    this.glassMesh.renderOrder = 3;
    this.root.add(this.glassMesh);

    this.hitSphere = new THREE.Mesh(new THREE.SphereGeometry(R, 24, 16), new THREE.MeshBasicMaterial({ visible: false }));
    this.hitSphere.position.copy(this.globeCenter);
    this.root.add(this.hitSphere);

    // Glass needn't write depth: the snow inside must still draw over it.
    this.glassMaterial.depthWrite = false;
    // Shards: clear faces that mostly reflect, and greenish edges like cut glass.
    // (Cheaper than transmission and it reads better while moving.)
    this.shardMaterial = new THREE.MeshPhysicalMaterial({
      color: '#f4f8f7',
      roughness: 0.03,
      metalness: 0,
      transparent: true,
      opacity: 0.16,
      envMapIntensity: 1.2,
      clearcoat: 1,
      clearcoatRoughness: 0.02,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.shardEdgeMaterial = new THREE.MeshPhysicalMaterial({
      color: '#cfe0da',
      roughness: 0.1,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      envMapIntensity: 1.2,
    });
    this.root.add(this.shardGroup);

    this.snow = new Snow({ count: 420, radius: R * 0.96, center: this.globeCenter, floorY: STAGE_Y });
    this.root.add(this.snow.points);
  }

  private buildWorld(projects: Project[]) {
    const prof = (pts: [number, number][]) => pts.map(([x, y]) => new THREE.Vector2(x, y));
    const stage = new THREE.Mesh(
      new THREE.LatheGeometry(
        prof([
          [0, STAGE_Y], [STAGE_R - 0.03, STAGE_Y], [STAGE_R - 0.006, STAGE_Y - 0.01], [STAGE_R, STAGE_Y - 0.03],
          [STAGE_R - 0.004, STAGE_Y - 0.1], [STAGE_R - 0.03, STAGE_Y - 0.125], [STAGE_R - 0.1, STAGE_Y - 0.14], [0, STAGE_Y - 0.14],
        ].reverse() as [number, number][]), // lathe profiles run bottom-to-top for outward normals
        128,
      ),
      clay(palette.porcelain, 0.7),
    );
    stage.receiveShadow = true;
    stage.castShadow = true;
    this.root.add(stage);
    // Once the pedestal is gone, a soft shadow far below lets the world float.
    this.islandShadow = contactShadow(2.6, 0.32);
    this.islandShadow.position.y = STAGE_Y - 0.7;
    this.islandShadow.visible = false;
    this.root.add(this.islandShadow);

    // Layout: objects on a gentle ring. Phase 1 only has the acorn.
    const placed = projects.filter((p) => p.object && builders[p.object]);
    placed.forEach((p, i) => {
      const group = builders[p.object!]();
      const n = placed.length;
      const a = n === 1 ? 0 : (i / n) * Math.PI * 2;
      const rr = n === 1 ? 0.05 : 0.45;
      group.position.set(Math.sin(a) * rr, STAGE_Y, Math.cos(a) * rr);
      group.userData.baseY = STAGE_Y;
      const hit = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), new THREE.MeshBasicMaterial({ visible: false }));
      hit.position.y = 0.1;
      hit.userData.id = p.id;
      group.add(hit);
      this.root.add(group);
      this.objects.push({ id: p.id, group, hit, anchor: new THREE.Vector3(0, 0.27, 0), hover: 0 });
    });
  }

  // ---------------------------------------------------------------- camera

  private globeView() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const hh = 2.05; // half the height to frame (pedestal + globe + room for the label)
    const hw = aspect < 0.8 ? 1.22 : 1.5;
    const dist = Math.max(hh / t, hw / (t * aspect));
    // Look a little below the middle so the label has room under the pedestal.
    const look = new THREE.Vector3(0, aspect < 0.8 ? 1.0 : 1.1, 0);
    return { pos: new THREE.Vector3(0, look.y + dist * 0.1, dist), look };
  }

  private worldView() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const hw = 1.15;
    const dist = Math.max(0.78 / t, hw / (t * aspect));
    const look = new THREE.Vector3(0, STAGE_Y + 0.02, 0);
    const dir = new THREE.Vector3(0, 0.5, 1).normalize();
    return { pos: look.clone().addScaledVector(dir, dist), look };
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
    // A touch of parallax from the cursor in the world view.
    const par = this.phase === 'world' ? 0.03 : this.phase === 'globe' || this.phase === 'cracking' ? 0.05 : 0;
    const px = THREE.MathUtils.clamp(this.pointer.x, -1, 1) * par;
    const py = THREE.MathUtils.clamp(this.pointer.y, -1, 1) * par;
    this.camera.position.set(this.camPos.x + px, this.camPos.y + py + this.pitch, this.camPos.z);
    this.camera.lookAt(this.camLook);
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
    this.snow.open = true;
    this.setPedestalOpacity(0);
    this.yaw = 0;
    this.yawVel = 0;
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
    const v = this.worldView();
    this.tweenCamera(v.pos, v.look, 1.0);
    this.setPhase('world');
  }

  hasObject(id: string) {
    return this.objects.some((o) => o.id === id);
  }

  private setPedestalOpacity(o: number) {
    for (const m of [...this.pedestalParts, ...this.floorParts]) {
      const mat = m.material as THREE.Material & { opacity: number; userData: { base?: number } };
      mat.userData.base ??= mat.opacity;
      mat.transparent = true;
      mat.opacity = mat.userData.base! * o;
      if (m.userData.loaded !== false) m.visible = o > 0.001;
      if (this.pedestalParts.includes(m)) m.castShadow = o > 0.5;
    }
    const sm = this.islandShadow.material as THREE.MeshBasicMaterial;
    sm.opacity = 0.32 * (1 - o);
    this.islandShadow.visible = o < 0.999;
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
    this.sim = new ShatterSim(this.shardGroup.children as THREE.Mesh[], this.fracture.shards, this.globeCenter, impact, {
      pedestalTop: PEDESTAL_TOP,
      pedestalRadius: 0.93,
      collarTop: COLLAR_TOP,
      collarRadius: 0.87,
      stageTop: STAGE_Y,
      stageRadius: STAGE_R + 0.01,
      floorY: 0,
    });
    // Swap the smooth sphere for the (still intact) shards.
    this.glassMesh.visible = false;
    this.setPhase('cracking');
  }

  private shatter() {
    if (!this.sim) return;
    this.sim.start();
    if (this.crackMesh) this.crackMesh.visible = false;
    this.breakTime = this.time;
    this.yawVel = 0;
    this.snow.open = true;
    this.snow.burst(this.impact.clone().add(this.globeCenter), 0.5);
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
        // Dive: rise slightly over the broken rim, then down into the world.
        const v = this.worldView();
        const via = new THREE.Vector3(0.1, GLOBE_Y + 1.5, 3.4);
        this.tweenCamera(v.pos, v.look, 2.8, via);
      }
      // Bring the diorama round to face the camera during the dive.
      this.yaw = damp(this.yaw, Math.round(this.yaw / (Math.PI * 2)) * Math.PI * 2, 1.6, dt);
      const fade = THREE.MathUtils.clamp((since - 1.3) / 1.0, 0, 1);
      this.shardMaterial.opacity = 0.16 * (1 - fade);
      this.shardEdgeMaterial.opacity = 0.8 * Math.min(1, since * 6) * (1 - fade);
      // The pedestal dissolves as we arrive, leaving the world floating.
      this.setPedestalOpacity(1 - THREE.MathUtils.clamp((since - 1.7) / 1.2, 0, 1));
      if (since > 3.6) {
        this.shardGroup.visible = false;
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
    window.addEventListener('pointercancel', () => { this.drag = null; this.holding = false; });
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
    const onGlobe = (this.phase === 'globe' || this.phase === 'cracking') && !!this.hitGlobe();
    this.drag = { x: e.clientX, y: e.clientY, moved: false, t: performance.now(), onGlobe };
    this.renderer.domElement.setPointerCapture?.(e.pointerId);
  }

  private onMove(e: PointerEvent) {
    this.setPointer(e);
    const d = this.drag;
    if (d) {
      const dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (!d.moved && Math.hypot(dx, dy) > 6) {
        d.moved = true;
        this.holding = false;
      }
      if (d.moved && (this.phase === 'globe' || this.phase === 'cracking' || this.phase === 'world')) {
        const k = this.phase === 'world' ? 0.004 : 0.008;
        this.yawVel = (e.movementX || 0) * k * 60;
        this.yaw += (e.movementX || 0) * k;
        if (this.phase === 'world') this.worldYaw = THREE.MathUtils.clamp(this.yaw, -0.7, 0.7), this.yaw = this.worldYaw;
        this.pitch = THREE.MathUtils.clamp(this.pitch + (e.movementY || 0) * 0.002, -0.25, 0.35);
      }
    }
    if (this.phase === 'world') this.setHover(this.hitObject());
  }

  private onUp(e: PointerEvent) {
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
    this.snow.setSwirl(this.phase === 'globe' || this.phase === 'cracking' ? (this.drag?.moved ? this.yawVel : this.yawVel * 0.3) : 0);

    // Cursor stirs the snow: ray through the cursor, pushed by cursor motion.
    if (this.pointer.x < 5 && (this.phase === 'globe' || this.phase === 'cracking')) {
      this.raycaster.setFromCamera(this.pointer, this.camera);
      const ray = this.raycaster.ray;
      const closest = ray.closestPointToPoint(this.root.localToWorld(this.globeCenter.clone()), new THREE.Vector3());
      if (this.prevPointerWorld) {
        const push = closest.clone().sub(this.prevPointerWorld);
        if (push.lengthSq() > 1e-7) {
          const inv = new THREE.Matrix4().copy(this.root.matrixWorld).invert();
          const o = ray.origin.clone().applyMatrix4(inv);
          const dir = ray.direction.clone().transformDirection(inv);
          const p = push.transformDirection(inv).multiplyScalar(Math.min(push.length() * 40, 1.2));
          this.snow.setStir(o, dir, p);
        }
      }
      this.prevPointerWorld = closest;
    } else this.prevPointerWorld = null;
  }

  // ---------------------------------------------------------------- loop

  private resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.snow.setPointScale(Math.min(w, h * 1.4) * 0.03);
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
    this.renderer.render(this.scene, this.camera);
  };

  private tick(dt: number) {
    this.time += dt;
    this.updateInput(dt);
    this.updateBreak(dt);
    this.updateCamera(dt);
    this.snow.update(dt);
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
