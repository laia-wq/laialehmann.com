/**
 * Lily and Rain, Lily and Fire: one scene across three panes of glass (the
 * red bay's front and side, and the casement beside it).
 *
 * Behind all the glass stands one long row of lilies, close-packed but each
 * its own plant: stems clothed in narrow leaves, trumpets turned this way and
 * that, a few buds, all swaying a little in a loop with no seam. They're
 * silhouettes on frosted glass: the row nearer the glass sharper, the one
 * behind it softer.
 *
 * Pick the bay and it rains, outside, in front of everything: streaks at
 * three depths, brighter where they cross the lit glass, splashing on the
 * sill, and drops gathering on the panes and running down. Pick the casement
 * and a fire flares up behind its lilies, so they stand black against it,
 * its light flickering out onto the wall. Each fades when you pick the other.
 *
 * Layers, bottom to top, all inside the picture (so they move with it):
 *   fire    (masked to the glass, very soft, screen-blended)
 *   lilies  back row, front row (masked to the glass)
 *   outside rain, splashes, beads on the glass, firelight on the wall
 */
type UV = [number, number];
export interface LilyPane { tl: UV; tr: UV; bl: UV; aspect: number; kind: 'rain' | 'fire' }
export type LilyMode = 'idle' | 'rain' | 'fire';

const INK = '28, 13, 6';
const H = 400;                      // each pane's own units: 400 tall
const LOOP = 9;                     // the sway repeats every LOOP seconds, exactly

// a small seeded random, so the same lilies grow every time
function rng(seed: number) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

interface Flower { at: number; ang: number; len: number; kind: 'side' | 'face' | 'bud'; size: number; flip: number }
interface Lily { x: number; top: number; lean: number; amp: number; ph: number; n: number; leaves: { at: number; side: number; len: number; ang: number }[]; flowers: Flower[]; w: number }

function grow(PW: number, seed: number, spacing: number, tall: [number, number]): Lily[] {
  const r = rng(seed);
  const out: Lily[] = [];
  for (let x = -spacing * 0.3 + r() * spacing * 0.4; x < PW + spacing * 0.5; x += spacing * (0.75 + r() * 0.5)) {
    const top = H - (tall[0] + r() * (tall[1] - tall[0]));
    const leaves = [];
    const nl = 6 + Math.floor(r() * 3);
    for (let k = 0; k < nl; k++) {
      const at = 0.08 + (k / nl) * 0.72 + r() * 0.04;
      leaves.push({ at, side: k % 2 ? 1 : -1, len: (44 - at * 26) * (0.8 + r() * 0.4), ang: 0.35 + r() * 0.45 });
    }
    const flowers: Flower[] = [];
    const nf = r() < 0.25 ? 1 : r() < 0.7 ? 2 : 3;
    for (let k = 0; k < nf; k++) {
      const pick = r();
      flowers.push({ at: 0.86 + k * 0.05, ang: (k % 2 ? 1 : -1) * (0.5 + r() * 0.9) + (r() - 0.5) * 0.3, len: 10 + r() * 12,
        kind: k === nf - 1 && pick < 0.3 ? 'bud' : pick < 0.78 ? 'side' : 'face', size: 1.1 + r() * 0.4, flip: r() < 0.5 ? 1 : -1 });
    }
    out.push({ x, top, lean: (r() - 0.5) * 0.12, amp: 0.018 + r() * 0.022, ph: r() * Math.PI * 2, n: r() < 0.5 ? 1 : 2, leaves, flowers, w: 2.6 + r() * 1.2 });
  }
  return out;
}

/** Draw one lily in pane units; `sway` bends it from the root. */
function drawLily(c: CanvasRenderingContext2D, L: Lily, t: number) {
  const th = L.lean + L.amp * Math.sin((2 * Math.PI * L.n * t) / LOOP + L.ph);
  const base = { x: L.x, y: H + 30 }, len = base.y - L.top;
  // the stem curves more the higher it goes (a cantilever bending in the air)
  const at = (f: number) => {
    const b = th * f * f * 1.4;
    return { x: base.x + Math.sin(b) * len * f * 0.9, y: base.y - Math.cos(b * 0.5) * len * f, a: b };
  };
  c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath();
  for (let i = 0; i <= 12; i++) { const p = at(i / 12); i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y); }
  c.lineWidth = L.w; c.stroke();
  // leaves: narrow, pointed, angled up and out, smaller higher up
  for (const lf of L.leaves) {
    const p = at(lf.at), a = p.a - lf.side * lf.ang - Math.PI / 2 + th * 0.4;
    const dx = Math.cos(a), dy = Math.sin(a), nx = -dy, ny = dx;
    const l = lf.len, w = l * 0.17;
    c.beginPath();
    c.moveTo(p.x, p.y);
    c.quadraticCurveTo(p.x + dx * l * 0.45 + nx * w, p.y + dy * l * 0.45 + ny * w, p.x + dx * l + nx * w * 0.4 - lf.side * 0, p.y + dy * l + 2);
    c.quadraticCurveTo(p.x + dx * l * 0.45 - nx * w, p.y + dy * l * 0.45 - ny * w, p.x, p.y);
    c.fill();
  }
  for (const f of L.flowers) {
    const p = at(Math.min(1, f.at));
    const a = p.a + f.ang - Math.PI / 2;                        // pedicel direction
    const q = { x: p.x + Math.cos(a) * f.len, y: p.y + Math.sin(a) * f.len };
    c.beginPath(); c.moveTo(p.x, p.y); c.quadraticCurveTo(p.x + Math.cos(a) * f.len * 0.5, p.y + Math.sin(a) * f.len * 0.2, q.x, q.y);
    c.lineWidth = L.w * 0.7; c.stroke();
    const bob = Math.sin((2 * Math.PI * 2 * t) / LOOP + L.ph + f.at * 9) * 0.06;
    c.save(); c.translate(q.x, q.y);
    const s = f.size;
    if (f.kind === 'bud') {
      c.rotate(a + Math.PI / 2 + 0.5 * Math.sign(f.ang) + bob);
      c.beginPath(); c.moveTo(0, 0);
      c.bezierCurveTo(-6 * s, -6 * s, -5 * s, -26 * s, 0, -34 * s);
      c.bezierCurveTo(5 * s, -26 * s, 6 * s, -6 * s, 0, 0); c.fill();
    } else if (f.kind === 'side') {
      // a trumpet seen from the side: a slim tube flaring to six recurved tips, stamens out of the mouth
      c.rotate(a + bob + (f.flip < 0 ? Math.PI : 0) * 0); c.scale(1, f.flip);
      const Lt = 30 * s, R = 15 * s;
      c.beginPath();
      c.moveTo(0, -2.5 * s);
      c.bezierCurveTo(Lt * 0.35, -3 * s, Lt * 0.6, -R * 0.45, Lt * 0.92, -R);
      c.quadraticCurveTo(Lt * 1.05, -R * 1.25, Lt * 1.12, -R * 1.05);          // upper tip curling back
      c.quadraticCurveTo(Lt * 0.98, -R * 0.62, Lt * 1.08, -R * 0.4);
      c.quadraticCurveTo(Lt * 1.2, -R * 0.3, Lt * 1.22, -R * 0.05);            // middle tip
      c.quadraticCurveTo(Lt * 1.1, R * 0.1, Lt * 1.12, R * 0.38);
      c.quadraticCurveTo(Lt * 1.22, R * 0.6, Lt * 1.12, R * 1.08);             // lower tip
      c.quadraticCurveTo(Lt * 1.0, R * 1.2, Lt * 0.9, R * 0.95);
      c.bezierCurveTo(Lt * 0.6, R * 0.45, Lt * 0.35, 3 * s, 0, 2.5 * s);
      c.closePath(); c.fill();
      c.lineWidth = 0.9 * s;
      for (const [dy, ex] of [[-3, 1.32], [0, 1.4], [3.5, 1.3]] as const) {
        c.beginPath(); c.moveTo(Lt * 0.8, dy * s * 0.4); c.quadraticCurveTo(Lt * 1.1, dy * s, Lt * ex, dy * s * 1.3); c.stroke();
        c.beginPath(); c.ellipse(Lt * ex, dy * s * 1.3, 2.4 * s, 1.1 * s, 0.3, 0, Math.PI * 2); c.fill();
      }
    } else {
      // a trumpet facing you: six pointed tepals round a dark throat
      c.rotate(f.ang * 0.3 + bob);
      const R = 17 * s;
      c.beginPath();
      for (let k = 0; k < 6; k++) {
        const a0 = (k / 6) * Math.PI * 2 + 0.2, a1 = a0 + Math.PI / 6, a2 = a0 + Math.PI / 3;
        const w = k % 2 ? 0.85 : 1;
        if (!k) c.moveTo(Math.cos(a0) * R * 0.3, Math.sin(a0) * R * 0.3);
        c.quadraticCurveTo(Math.cos(a0 + 0.12) * R * 0.9 * w, Math.sin(a0 + 0.12) * R * 0.9 * w, Math.cos(a1) * R * w, Math.sin(a1) * R * w);
        c.quadraticCurveTo(Math.cos(a2 - 0.12) * R * 0.9 * w, Math.sin(a2 - 0.12) * R * 0.9 * w, Math.cos(a2) * R * 0.3, Math.sin(a2) * R * 0.3);
      }
      c.closePath(); c.fill();
    }
    c.restore();
  }
}

interface Drop { x: number; y: number; v: number; len: number; z: number; land: number }
interface Splash { x: number; y: number; t: number; z: number }
interface Bead { x: number; y: number; r: number; slide: number; v: number; trail: number; born: number; pane: number }

export class LilyScene {
  private host: HTMLElement;
  private fireC: HTMLCanvasElement; private backC: HTMLCanvasElement; private frontC: HTMLCanvasElement; private outC: HTMLCanvasElement;
  private rows: { back: Lily[]; front: Lily[] }[];
  private mode: LilyMode = 'idle';
  private rainAmt = 0; private fireAmt = 0; private fireT0 = -1;
  private drops: Drop[] = []; private splashes: Splash[] = []; private beads: Bead[] = [];
  private raf = 0; private t0 = performance.now(); private last = performance.now();
  private motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  private W = 0; private Hpx = 0;
  private sparks: { x: number; y: number; vx: number; vy: number; life: number }[] = [];
  private ro: ResizeObserver;

  constructor(pic: HTMLElement, private panes: LilyPane[], masks: string[]) {
    this.host = document.createElement('div');
    this.host.className = 'lily-scene';
    const m = masks.map((u) => `url(${u})`).join(', ');
    const layer = (cls: string) => {
      const d = document.createElement('div'); d.className = 'lily-glass ' + cls;
      d.style.setProperty('-webkit-mask-image', m); d.style.setProperty('mask-image', m);
      this.host.appendChild(d); return d;
    };
    const mk = (cls: string, parent: HTMLElement) => { const c = document.createElement('canvas'); c.className = cls; parent.appendChild(c); return c; };
    // the fire's own masked layer screens onto the glass; the lilies sit over it
    this.fireC = mk('lily-fire', layer('lily-firelayer'));
    const glass = layer('lily-inklayer');
    this.backC = mk('lily-back', glass); this.frontC = mk('lily-front', glass);
    this.outC = mk('lily-out', this.host);
    pic.appendChild(this.host);
    this.rows = panes.map((q, k) => {
      const PW = H * q.aspect;
      return { back: grow(PW, 11 + k * 7, 26, [150, 260]), front: grow(PW, 53 + k * 13, 42, [130, 250]) };
    });
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(this.host);
    this.loop();
  }

  setMode(m: LilyMode) {
    if (m === this.mode) return;
    this.mode = m;
    if (m === 'fire') { this.fireT0 = this.now(); this.sparks = []; }
  }

  private now() { return (performance.now() - this.t0) / 1000; }

  private resize = () => {
    // the picture may be scaled by a CSS transform: size by its layout box
    const w = this.host.offsetWidth, h = this.host.offsetHeight;
    if (!w || !h) return;
    this.W = w; this.Hpx = h;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const set = (c: HTMLCanvasElement, k: number) => { c.width = Math.round(w * dpr * k); c.height = Math.round(h * dpr * k); };
    set(this.fireC, 0.35); set(this.backC, 0.6); set(this.frontC, 1); set(this.outC, 1);
    if (!this.motion) this.frame(4.5, 0);
  };

  /** pane k's units -> picture px */
  private paneM(k: number) {
    const q = this.panes[k], PW = H * q.aspect, W = this.W, Hh = this.Hpx;
    return [((q.tr[0] - q.tl[0]) * W) / PW, ((q.tr[1] - q.tl[1]) * Hh) / PW, ((q.bl[0] - q.tl[0]) * W) / H, ((q.bl[1] - q.tl[1]) * Hh) / H, q.tl[0] * W, q.tl[1] * Hh] as const;
  }
  private quadPx(k: number) {
    const q = this.panes[k], W = this.W, Hh = this.Hpx;
    const tl = [q.tl[0] * W, q.tl[1] * Hh], tr = [q.tr[0] * W, q.tr[1] * Hh], bl = [q.bl[0] * W, q.bl[1] * Hh];
    const br = [tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1]];
    return { tl, tr, bl, br };
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    if (document.hidden) return;
    const n = performance.now(), dt = Math.min(0.05, (n - this.last) / 1000); this.last = n;
    if (!this.motion) { this.frame(4.5, 0); return; }
    this.frame(this.now(), dt);
  };

  private frame(t: number, dt: number) {
    const target = (m: LilyMode) => (this.mode === m ? 1 : 0);
    const ease = (cur: number, to: number, up: number, down: number) => cur + Math.max(-dt / down, Math.min(dt / up, to - cur));
    if (this.motion) {
      this.rainAmt = ease(this.rainAmt, target('rain'), 3.0, 2.5);
      this.fireAmt = ease(this.fireAmt, target('fire'), 0.9, 1.8);
    } else { this.rainAmt = target('rain'); this.fireAmt = target('fire'); }
    this.drawFire(t, dt);
    this.drawLilies(t);
    this.drawOutside(t, dt);
  }

  // ---------------------------------------------------------------- lilies
  private drawLilies(t: number) {
    for (const [cv, which, alpha] of [[this.backC, 'back', 0.55], [this.frontC, 'front', 0.9]] as const) {
      const c = cv.getContext('2d')!;
      const s = cv.width / this.W;
      c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, cv.width, cv.height);
      c.fillStyle = c.strokeStyle = `rgba(${INK}, ${alpha})`;
      this.panes.forEach((_, k) => {
        const [a, b, cc, d, e, f] = this.paneM(k);
        c.setTransform(a * s, b * s, cc * s, d * s, e * s, f * s);
        for (const L of this.rows[k][which]) drawLily(c, L, t + (which === 'back' ? 0.7 : 0));
        if (which === 'front' && this.panes[k].kind === 'rain' && this.rainAmt > 0.01) this.drawRainInk(c, k, t);
      });
    }
  }

  /** Rain as part of the shadow play: dark streaks slanting down behind the
   *  glass, thickening as it sets in, with little splashes at the bottom. */
  private drawRainInk(c: CanvasRenderingContext2D, k: number, t: number) {
    const PW = H * this.panes[k].aspect, n = Math.round((PW / 4) * this.rainAmt);
    c.save();
    c.lineCap = 'round';
    c.strokeStyle = `rgba(${INK}, ${0.55 * Math.min(1, this.rainAmt * 1.5)})`;
    c.lineWidth = 1.7;
    c.beginPath();
    for (let i = 0; i < n; i++) {
      const sp = 0.9 + ((i * 7919) % 13) / 13 * 0.6, ph = ((i * 0.618) % 1);
      const u = this.motion ? (t * sp + ph) % 1 : ph;
      const x = ((i * 37.7) % (PW + 40)) - 20, y = -30 + u * (H + 40), len = 14 + (i % 5) * 3;
      c.moveTo(x + u * 18, y); c.lineTo(x + u * 18 - len * 0.18, y - len);
    }
    c.stroke();
    // splashes where it lands
    c.lineWidth = 1.2;
    c.beginPath();
    for (let i = 0; i < n / 3; i++) {
      const ph = ((i * 0.381) % 1), u = this.motion ? (t * 1.7 + ph) % 1 : ph;
      if (u > 0.35) continue;
      const x = ((i * 53.3) % PW), y = H - 6, r = 2 + u * 14;
      c.moveTo(x - r, y - r * 0.5); c.quadraticCurveTo(x - r * 0.4, y - r * 0.2, x, y);
      c.moveTo(x + r, y - r * 0.5); c.quadraticCurveTo(x + r * 0.4, y - r * 0.2, x, y);
    }
    c.stroke();
    c.restore();
  }

  // ---------------------------------------------------------------- fire
  private drawFire(t: number, dt: number) {
    const cv = this.fireC, c = cv.getContext('2d')!, s = cv.width / this.W;
    c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, cv.width, cv.height);
    const k = this.panes.findIndex((p) => p.kind === 'fire');
    if (k < 0 || this.fireAmt < 0.002) return;
    const [a, b, cc, d, e, f] = this.paneM(k);
    c.setTransform(a * s, b * s, cc * s, d * s, e * s, f * s);
    const PW = H * this.panes[k].aspect;
    // it catches: a pop of light, then flames shooting up past full height and settling
    const since = this.fireT0 >= 0 ? t - this.fireT0 : 99;
    const pop = Math.max(0, 1 - Math.abs(since - 0.12) / 0.25);
    const grow = since < 0 ? 0 : since < 0.5 ? (since / 0.5) * 1.18 : 1.18 - 0.18 * Math.min(1, (since - 0.5) / 0.8);
    const amt = this.fireAmt * Math.min(1, grow);
    c.globalCompositeOperation = 'lighter';
    // the glow filling the room behind the glass
    const fl = 0.85 + 0.1 * Math.sin(t * 11) + 0.06 * Math.sin(t * 23 + 1.3);
    const g = c.createRadialGradient(PW / 2, H * 0.95, 10, PW / 2, H * 0.7, H * 0.9);
    g.addColorStop(0, `rgba(255, 150, 60, ${0.85 * amt * fl})`); g.addColorStop(1, 'rgba(255, 90, 20, 0)');
    c.fillStyle = g; c.fillRect(-20, -20, PW + 40, H + 40);
    if (pop > 0) {
      const pg = c.createRadialGradient(PW / 2, H * 0.85, 0, PW / 2, H * 0.85, H * 0.7);
      pg.addColorStop(0, `rgba(255, 240, 200, ${pop * this.fireAmt})`); pg.addColorStop(1, 'rgba(255, 200, 120, 0)');
      c.fillStyle = pg; c.fillRect(-20, -20, PW + 40, H + 40);
    }
    // tongues of flame: each a teardrop whose height and lean flicker
    const N = 9;
    for (const [col, hk, wk] of [['255, 70, 15', 1.0, 1.0], ['255, 140, 35', 0.78, 0.7], ['255, 225, 140', 0.5, 0.42]] as const) {
      for (let i = 0; i < N; i++) {
        const x = PW * (0.1 + (0.8 * i) / (N - 1)) + Math.sin(t * 2.1 + i) * 4;
        const n = 0.62 + 0.22 * Math.sin(t * 7.3 + i * 1.9) + 0.12 * Math.sin(t * 13.1 + i * 3.7) + 0.08 * Math.sin(t * 29 + i);
        const h = (210 + 150 * Math.sin(i * 2.4 + 1) ** 2) * n * hk * amt;
        const w = (26 + (i % 3) * 6) * wk * (0.8 + 0.2 * amt);
        const lean = Math.sin(t * 3.1 + i * 0.8) * 18 * hk;
        const y0 = H + 4;
        c.beginPath();
        c.moveTo(x - w, y0);
        c.bezierCurveTo(x - w * 1.05, y0 - h * 0.45, x - w * 0.3 + lean * 0.5, y0 - h * 0.7, x + lean, y0 - h);
        c.bezierCurveTo(x + w * 0.3 + lean * 0.5, y0 - h * 0.7, x + w * 1.05, y0 - h * 0.45, x + w, y0);
        c.closePath();
        c.fillStyle = `rgba(${col}, ${0.7 * amt})`; c.fill();
      }
    }
    // sparks rising off it
    if (this.motion && this.fireAmt > 0.3 && Math.random() < dt * 14) {
      this.sparks.push({ x: PW * (0.15 + Math.random() * 0.7), y: H - 60 - Math.random() * 80, vx: (Math.random() - 0.5) * 30, vy: -60 - Math.random() * 80, life: 1 });
    }
    for (const sp of this.sparks) {
      sp.x += sp.vx * dt + Math.sin(t * 6 + sp.y * 0.05) * 0.6; sp.y += sp.vy * dt; sp.life -= dt * 0.9;
      c.fillStyle = `rgba(255, 200, 110, ${Math.max(0, sp.life) * this.fireAmt})`;
      c.beginPath(); c.arc(sp.x, sp.y, 2.2, 0, Math.PI * 2); c.fill();
    }
    this.sparks = this.sparks.filter((sp) => sp.life > 0);
    c.globalCompositeOperation = 'source-over';
  }

  // ---------------------------------------------------------------- outside: rain, beads, firelight
  private drawOutside(t: number, dt: number) {
    const cv = this.outC, c = cv.getContext('2d')!, s = cv.width / this.W, W = this.W, Hh = this.Hpx;
    c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, cv.width, cv.height);
    c.setTransform(s, 0, 0, s, 0, 0);
    const quads = this.panes.map((_, k) => this.quadPx(k));
    // firelight thrown out onto the wall round the casement
    const fk = this.panes.findIndex((p) => p.kind === 'fire');
    if (fk >= 0 && this.fireAmt > 0.002) {
      const q = quads[fk], cx = (q.tl[0] + q.br[0]) / 2, cy = (q.tl[1] + q.br[1]) / 2 + (q.bl[1] - q.tl[1]) * 0.2;
      const R = Math.abs(q.tr[0] - q.tl[0]) * 1.5;
      const fl = 0.8 + 0.12 * Math.sin(t * 9.7) + 0.08 * Math.sin(t * 17.3 + 2);
      const g = c.createRadialGradient(cx, cy, R * 0.2, cx, cy, R);
      g.addColorStop(0, `rgba(255, 130, 50, ${0.26 * this.fireAmt * fl})`); g.addColorStop(1, 'rgba(255, 110, 40, 0)');
      c.globalCompositeOperation = 'lighter'; c.fillStyle = g; c.fillRect(cx - R, cy - R, R * 2, R * 2); c.globalCompositeOperation = 'source-over';
    }
    const rainPanes = this.panes.map((p, k) => (p.kind === 'rain' ? k : -1)).filter((k) => k >= 0);
    // where drops land: the sills under the rain panes (their bottom edges)
    const sills = rainPanes.map((k) => { const q = quads[k]; return { x0: Math.min(q.bl[0], q.br[0]), x1: Math.max(q.bl[0], q.br[0]), y: (q.bl[1] + q.br[1]) / 2 + Hh * 0.012 }; });
    const inGlass = (x: number, y: number) => quads.some((q, k) => this.panes[k].kind && x > Math.min(q.tl[0], q.bl[0]) && x < Math.max(q.tr[0], q.br[0]) && y > Math.min(q.tl[1], q.tr[1]) && y < Math.max(q.bl[1], q.br[1]));
    const wind = 0.16;
    // rain: keep about `want` drops in the air
    const want = 0;   // the rain now falls in the shadow play, behind the glass (drawRainInk)
    if (this.motion) {
      while (this.drops.length < want) {
        const z = Math.random();                         // 0 far .. 1 near
        const x = Math.random() * (W * 1.2) - W * 0.1;
        const sill = sills.find((q) => x > q.x0 && x < q.x1);
        const land = z > 0.45 && sill && Math.random() < 0.55 ? sill.y : Hh * (0.9 + Math.random() * 0.15);
        this.drops.push({ x, y: -Math.random() * Hh, v: Hh * (0.9 + z * 1.1), len: Hh * (0.02 + z * 0.05), z, land });
      }
      if (this.drops.length > want) this.drops.splice(0, Math.min(this.drops.length - want, Math.ceil(dt * 400)));
    }
    c.lineCap = 'round';
    for (const d of this.drops) {
      d.y += d.v * dt; d.x += d.v * dt * wind;
      if (d.y > d.land) {
        if (d.z > 0.45) this.splashes.push({ x: d.x, y: d.land, t: 0, z: d.z });
        d.y = -d.len - Math.random() * Hh * 0.2; d.x = Math.random() * (W * 1.2) - W * 0.15;
        const sill = sills.find((q) => d.x > q.x0 && d.x < q.x1);
        d.land = d.z > 0.45 && sill && Math.random() < 0.55 ? sill.y : Hh * (0.9 + Math.random() * 0.15);
        continue;
      }
      const lit = inGlass(d.x, d.y) ? 1.7 : 1;
      const a = (0.14 + d.z * 0.36) * lit * Math.min(1, this.rainAmt * 1.4);
      const gr = c.createLinearGradient(d.x, d.y, d.x - d.len * wind, d.y - d.len);
      gr.addColorStop(0, `rgba(${lit > 1 ? '255, 236, 210' : '205, 215, 230'}, ${a})`); gr.addColorStop(1, 'rgba(205, 215, 230, 0)');
      c.strokeStyle = gr; c.lineWidth = 0.6 + d.z * 1.4;
      c.beginPath(); c.moveTo(d.x, d.y); c.lineTo(d.x - d.len * wind, d.y - d.len); c.stroke();
    }
    // splashes: a little crown of droplets and a ring
    for (const sp of this.splashes) {
      sp.t += dt;
      const k = sp.t / 0.32, a = (1 - k) * 0.5 * (0.5 + sp.z * 0.5);
      if (k >= 1) continue;
      c.strokeStyle = `rgba(220, 228, 240, ${a})`; c.lineWidth = 0.7;
      c.beginPath(); c.ellipse(sp.x, sp.y, 2 + k * 7 * sp.z, 0.6 + k * 1.6 * sp.z, 0, 0, Math.PI * 2); c.stroke();
      c.fillStyle = `rgba(225, 232, 242, ${a})`;
      for (let j = 0; j < 4; j++) {
        const vx = (j - 1.5) * 9 * sp.z, vy = -26 * sp.z * (1 - Math.abs(j - 1.5) * 0.25);
        c.beginPath(); c.arc(sp.x + vx * sp.t * 1.8, sp.y + vy * sp.t * 1.8 + 160 * sp.t * sp.t, 0.9, 0, Math.PI * 2); c.fill();
      }
    }
    this.splashes = this.splashes.filter((sp) => sp.t < 0.32);
    // beads on the glass: gather while it rains, grow, some run down, dry off after
    if (this.motion) {
      if (false && this.rainAmt > 0.2 && this.beads.length < 140 && Math.random() < dt * 22 * this.rainAmt) {
        const k = rainPanes[Math.floor(Math.random() * rainPanes.length)];
        if (k !== undefined) {
          const q = quads[k], u = Math.random(), v = Math.random();
          this.beads.push({ x: q.tl[0] + (q.tr[0] - q.tl[0]) * u + (q.bl[0] - q.tl[0]) * v, y: q.tl[1] + (q.tr[1] - q.tl[1]) * u + (q.bl[1] - q.tl[1]) * v,
            r: 0.8 + Math.random() * 1.6, slide: 0, v: 0, trail: 0, born: t, pane: k });
        }
      }
      for (const b of this.beads) {
        if (this.rainAmt > 0.2) b.r = Math.min(4.2, b.r + dt * Math.random() * 0.25 * this.rainAmt);
        else b.r -= dt * 0.35;                          // drying
        if (b.r > 3.3 && b.v === 0 && Math.random() < dt * 0.6) b.v = 25 + Math.random() * 35;
        if (b.v) { b.y += b.v * dt; b.x += Math.sin(b.y * 0.15) * 0.15; b.trail = Math.min(60, b.trail + b.v * dt); b.r -= dt * 0.25; }
      }
      this.beads = this.beads.filter((b) => { const q = quads[b.pane]; return b.r > 0.4 && b.y < Math.max(q.bl[1], q.br[1]); });
    }
    c.save();
    c.beginPath();
    for (const k of rainPanes) { const q = quads[k]; c.moveTo(q.tl[0], q.tl[1]); c.lineTo(q.tr[0], q.tr[1]); c.lineTo(q.br[0], q.br[1]); c.lineTo(q.bl[0], q.bl[1]); c.closePath(); }
    c.clip();
    for (const b of this.beads) {
      if (b.trail > 1) {
        const tg = c.createLinearGradient(b.x, b.y, b.x, b.y - b.trail);
        tg.addColorStop(0, 'rgba(255, 245, 225, 0.35)'); tg.addColorStop(1, 'rgba(255, 245, 225, 0)');
        c.strokeStyle = tg; c.lineWidth = b.r * 0.7; c.beginPath(); c.moveTo(b.x, b.y); c.lineTo(b.x, b.y - b.trail); c.stroke();
      }
      // a bead of water lit from behind: dark rim, bright lower lens, a glint up top
      const g = c.createRadialGradient(b.x, b.y + b.r * 0.25, b.r * 0.1, b.x, b.y, b.r);
      g.addColorStop(0, 'rgba(255, 246, 228, 0.55)'); g.addColorStop(0.7, 'rgba(255, 236, 205, 0.18)'); g.addColorStop(1, 'rgba(40, 24, 14, 0.45)');
      c.fillStyle = g; c.beginPath(); c.arc(b.x, b.y, b.r, 0, Math.PI * 2); c.fill();
      c.fillStyle = 'rgba(255, 255, 255, 0.7)'; c.beginPath(); c.arc(b.x - b.r * 0.35, b.y - b.r * 0.4, Math.max(0.4, b.r * 0.22), 0, Math.PI * 2); c.fill();
    }
    c.restore();
    if (false && !this.motion && this.rainAmt > 0) {
      // reduced motion: rain as still streaks
      const r = rng(7);
      c.strokeStyle = 'rgba(205, 215, 230, 0.22)'; c.lineWidth = 1;
      for (let i = 0; i < 160; i++) { const x = r() * W, y = r() * Hh, l = 10 + r() * 22; c.beginPath(); c.moveTo(x, y); c.lineTo(x - l * wind, y - l); c.stroke(); }
    }
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    this.host.remove();
  }
}
