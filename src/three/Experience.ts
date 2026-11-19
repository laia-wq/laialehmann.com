import * as THREE from 'three';
import { studioScene } from './studio';
import { glass, glassBack, noDirectSpecular } from './materials';
import { Snow } from './snow';
import { crackMaterial, fractureSphere, type Fracture } from './fracture';
import { ShatterSim } from './shatter';
import { buildPedestal, type Pedestal } from './pedestal';
import { buildInterior, type Interior } from './interior';
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
}

// Scene dimensions (world units, floor at y = 0).
const R = 1;
const CUP_TOP = 0.45; // rim of the wooden cup the sphere rests in
const CUP_R = 0.5;
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
    this.interior = buildInterior(this.globeCenter, R);
    if (new URLSearchParams(location.search).has('debug')) console.info(`interior built in ${(performance.now() - t0).toFixed(0)} ms`);
    this.root.add(this.interior.group);
    this.buildGlobe();
    this.scene.add(this.root);

    const qp = new URLSearchParams(location.search).get('quality');
    const lowPower = qp === 'low' || (qp !== 'high' && (navigator.hardwareConcurrency ?? 8) <= 4);
    this.quality = lowPower ? 0 : 1;
    this.post = new Post(this.renderer, this.scene, this.camera, this.quality);
    this.post.aoExclude = [this.glassMesh, this.shardGroup, this.snow.points, ...this.interior.transparents];

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
    this.scene.add(new THREE.HemisphereLight('#f3f1ec', '#6e604f', 0.6));
    const key = new THREE.DirectionalLight('#fff1dd', 2.8);
    key.position.set(-3.6, 6.2, 4.4);
    key.target.position.set(0, 0.9, 0);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3.2, bottom: -3, near: 1, far: 18 });
    key.shadow.radius = 6;
    key.shadow.blurSamples = 24;
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.015;
    this.scene.add(key, key.target);
    const rim = new THREE.DirectionalLight('#dce8f5', 1.3);
    rim.position.set(4, 3.5, -4.5);
    this.scene.add(rim);
    const fill = new THREE.DirectionalLight('#e8eef5', 0.5);
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

    // Glass needn't write depth: the snow inside must still draw over it.
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

    this.snow = new Snow({ count: 300, radius: R * 0.96, center: this.globeCenter, floorY: this.interior.groundY, groundAt: this.interior.groundAt });
    this.root.add(this.snow.points);
  }

  // ---------------------------------------------------------------- camera

  private globeView() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const hh = 1.6; // half the height to frame (stand + sphere + room for the label)
    const hw = aspect < 0.8 ? 1.18 : 1.4;
    const dist = Math.max(hh / t, hw / (t * aspect));
    // Look a little below the middle so the label has room under the stand.
    const look = new THREE.Vector3(0, aspect < 0.8 ? 0.98 : 1.05, 0);
    return { pos: new THREE.Vector3(0, look.y + dist * 0.12, dist), look };
  }

  private worldView() {
    const aspect = this.camera.aspect || 1;
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const hw = 1.05;
    const dist = Math.max(0.62 / t, hw / (t * aspect));
    const look = new THREE.Vector3(0, this.interior.groundY + 0.05, -0.05);
    const dir = new THREE.Vector3(0, 0.42, 1).normalize();
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
    this.post?.setSize(w, h);
    this.camera.aspect = w / h;
    this.backdrop.fit(w / h);
    this.camera.updateProjectionMatrix();
    this.snow.setPointScale(Math.min(w, h * 1.4) * 0.022);
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
    this.post.setFocus(p.y * 0.5 + 0.5, inGlobe ? 0.5 : 0.16, inGlobe ? 0.4 : 1.0);
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
        this.post.aoExclude = [this.glassMesh, this.shardGroup, this.snow.points, ...this.interior.transparents];
        this.resize();
      }
    }
  }

  private tick(dt: number) {
    this.time += dt;
    this.updateInput(dt);
    this.updateBreak(dt);
    this.updateCamera(dt);
    this.snow.update(dt);
    this.interior.update(this.time);
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
