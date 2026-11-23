/**
 * Looking in at a window. Clicking a building on the street glides the view
 * in towards one of its windows, then hands over to a close-up rendered from
 * the same angle: a sharp object on the sill that stands for the project, and
 * behind frosted glass a soft shadow play of someone using it. The project's
 * write-up slides in beside it; "back to the street" glides back out.
 *
 * The angle changes on the way in: after the street zooms towards the
 * window, pre-rendered frames swing the camera round until it faces the
 * window straight on, then a sharp still takes over.
 *
 * Assets per window (public/windows/<id>/): fly_000..fly_NNN.webp (the swing),
 * <id>.avif/.webp (the straight-on still), pane.png (alpha = the glass),
 * closeup.json (where the glass is, where the window sits on the street, the
 * first frame's scale, how many frames).
 */
import { projects } from '../content/projects';
import { projectBody } from './panel';

export interface WindowSpec {
  id: string;
  /** canal building group that opens it */
  building: string;
  projects: string[];
  /** which shadow play runs behind the glass */
  play: (svg: SVGSVGElement, width: number) => (t: number) => void;
}

interface CloseJson {
  pane: { tl: [number, number]; tr: [number, number]; bl: [number, number] };
  street_target: [number, number];
  scale: number;
  /** the glass's width / height */
  aspect: number;
  /** how many frames the camera's swing has */
  frames?: number;
}

const byId = (id: string) => projects.find((p) => p.id === id);
const PANE_H = 400;     // the shadow play's own units: 400 tall, as wide as the glass is

export class WindowView {
  readonly el: HTMLElement;
  private raf = 0;
  private meta!: CloseJson;
  onClose: () => void = () => {};

  constructor(host: HTMLElement, private stage: HTMLElement) {
    this.el = document.createElement('section');
    this.el.className = 'room window-view';
    this.el.hidden = true;
    host.appendChild(this.el);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !this.el.hidden) this.close(); });
    addEventListener('resize', () => { if (!this.el.hidden) this.fitPane(); });
  }

  get isOpen() { return !this.el.hidden; }

  private frames: (ImageBitmap | undefined)[] = [];
  private blobs: (Blob | undefined)[] = [];
  private decoding = new Set<number>();
  /** decoded frames to keep ahead of / behind the playhead */
  private static AHEAD = 7;
  private static BEHIND = 2;
  streetView: ((v: { s: number; tx: number; ty: number } | null) => boolean) | null = null;

  /** Make sure frames around f are decoded (and free the rest); resolves once
   *  frame f and the next few are ready. */
  private want(f: number, dir = 1) {
    const n = this.frames.length, jobs: Promise<void>[] = [];
    const lo = dir > 0 ? f - WindowView.BEHIND : f - WindowView.AHEAD;
    const hi = dir > 0 ? f + WindowView.AHEAD : f + WindowView.BEHIND;
    for (let k = 0; k < n; k++) {
      if (k < lo || k > hi) { const fr = this.frames[k]; if (fr) { fr.close(); this.frames[k] = undefined; } continue; }
      if (this.frames[k] || this.decoding.has(k) || !this.blobs[k]) continue;
      this.decoding.add(k);
      jobs.push(createImageBitmap(this.blobs[k]!).then((bm) => {
        this.decoding.delete(k);
        if (this.frames.length === n) this.frames[k] = bm; else bm.close();
      }).catch(() => { this.decoding.delete(k); }));
    }
    return Promise.all(jobs).then(() => {});
  }
  private canvas: HTMLCanvasElement | null = null;
  private motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  /** the zoom's geometry, measured once at the start */
  private geo: { k: number; tx: number; ty: number; cx: number; cy: number } | null = null;
  private ready = false;
  private u = 0;

  /** Fetch a window's frames ahead of time (compressed, into the HTTP cache),
   *  so a click starts moving straight away. */
  static prefetch(id: string) {
    const base = `${import.meta.env.BASE_URL}windows/${id}/`;
    fetch(base + 'closeup.json').then((r) => r.json()).then((m: CloseJson) => {
      for (let k = 0; k < (m.frames ?? 0); k++) fetch(`${base}fly_${String(k).padStart(3, '0')}.webp`).catch(() => {});
      fetch(`${base}${id}.webp`).catch(() => {});
    }).catch(() => {});
  }

  async open(spec: WindowSpec, streetRect: DOMRect) {
    const base = `${import.meta.env.BASE_URL}windows/${spec.id}/`;
    this.meta = await fetch(base + 'closeup.json').then((r) => r.json());
    const p = byId(spec.projects[0]);
    this.el.innerHTML = `
      <div class="room-stage">
        <div class="room-pic window-pic" style="aspect-ratio: 4 / 3">
          <canvas class="window-fly" width="960" height="720"></canvas>
          <picture><source srcset="${base}${spec.id}.avif" type="image/avif"><img class="room-img window-still" src="${base}${spec.id}.webp" alt="" decoding="async"></picture>
          <div class="window-play" style="-webkit-mask-image:url(${base}pane.png);mask-image:url(${base}pane.png)">
            <svg class="window-svg" viewBox="0 0 ${this.paneW()} ${PANE_H}" width="${this.paneW()}" height="${PANE_H}" aria-hidden="true"></svg>
          </div>
        </div>
      </div>
      <aside class="room-panel">
        <button class="room-back" type="button"><span aria-hidden="true">←</span> back to the street</button>
        <div class="room-body">${p ? projectBody(p, 2) : ''}</div>
      </aside>`;
    this.el.querySelector('.room-back')!.addEventListener('click', () => this.close());
    this.canvas = this.el.querySelector('.window-fly');
    const svg = this.el.querySelector('.window-svg') as SVGSVGElement;
    const step = spec.play(svg, this.paneW());
    // the camera's swing round to face the window: pre-rendered frames. All
    // are fetched (compressed), but only a few around the playhead are kept
    // decoded at once, so memory stays small however big the frames are.
    const n = this.meta.frames ?? 0;
    this.frames = new Array(n);
    this.blobs = new Array(n);
    this.ready = false;
    const fetched = Promise.all(Array.from({ length: n }, (_, k) =>
      fetch(`${base}fly_${String(k).padStart(3, '0')}.webp`).then((r) => r.blob()).then((bl) => { this.blobs[k] = bl; }).catch(() => {})));
    const loaded = fetched.then(() => this.want(0)).then(() => { this.ready = true; });
    const still = this.el.querySelector('.window-still') as HTMLImageElement;
    const stillReady = still.decode ? still.decode().catch(() => {}) : Promise.resolve();

    loaded.then(() => { const f0 = this.frames[0]; if (f0 && this.canvas) { this.canvas.width = f0.width; this.canvas.height = f0.height; this.at(this.u); } });
    this.el.hidden = false;
    this.el.classList.add('is-open');
    const pic = this.el.querySelector('.window-pic') as HTMLElement;
    const c = pic.getBoundingClientRect();
    const sr = this.stage.getBoundingClientRect();
    this.geo = {
      k: (c.width / streetRect.width) / this.meta.scale,
      tx: streetRect.left - sr.left + this.meta.street_target[0] * streetRect.width,
      ty: streetRect.top - sr.top + this.meta.street_target[1] * streetRect.height,
      cx: c.left + c.width / 2 - sr.left, cy: c.top + c.height / 2 - sr.top,
    };
    this.stage.style.transformOrigin = '0 0';
    this.stage.style.transition = 'none';
    if (this.motion && n > 1) {
      await this.run(0, 1, 2300);
    } else {
      await loaded;
      this.at(1);
    }
    // settle on the sharp still; the shadow play starts behind the glass; the write-up slides in
    await stillReady;
    this.el.classList.add('is-settled');
    this.fitPane();
    const t0 = performance.now();
    const tick = () => { step(this.motion ? (performance.now() - t0) / 1000 : 4.5); if (this.motion) this.raf = requestAnimationFrame(tick); };
    tick();
    (this.el.querySelector('.room-back') as HTMLElement).focus({ preventScroll: true });
  }

  /* One continuous move, u = 0 (the street) .. 1 (facing the window):
   *  - the street zooms in towards the window (log-scale, so it feels even)
   *  - part way in, the first rendered frame fades in over the street, laid
   *    exactly where the window is on the zooming street, so the detailed
   *    version sharpens in place rather than cutting
   *  - the camera then swings round through the frames, each blended into the
   *    next so the motion has no steps */
  private static SPLIT = 0.46;      // street zoom ends, frames start
  private static FADE0 = 0.26;      // frames start fading in over the street
  private static OUT0 = 0.46;       // street starts fading out under them
  private static OUT1 = 0.6;

  private at(u: number) {
    this.u = u;
    const g = this.geo, cv = this.canvas;
    if (!g || !cv) return;
    const S = WindowView.SPLIT;
    const z = Math.min(1, u / S);
    const s = Math.exp(Math.log(g.k) * z);                 // street scale
    const w = g.k > 1 ? (s - 1) / (g.k - 1) : 1;            // how far the window has come to the centre
    const px = g.tx + (g.cx - g.tx) * w, py = g.ty + (g.cy - g.ty) * w;
    const v = { s, tx: px - s * g.tx, ty: py - s * g.ty };
    if (this.streetView && this.streetView(v)) this.stage.style.transform = '';
    else this.stage.style.transform = `translate(${v.tx}px, ${v.ty}px) scale(${s})`;
    const sm = (a: number, b: number) => { const t = Math.min(1, Math.max(0, (u - a) / (b - a))); return t * t * (3 - 2 * t); };
    this.stage.style.opacity = String(1 - sm(WindowView.OUT0, WindowView.OUT1));
    // the frames' canvas rides along with the street until the zoom is done
    const r = s / g.k;
    cv.style.transform = r < 0.9999 ? `translate(${px - g.cx}px, ${py - g.cy}px) scale(${r})` : '';
    cv.style.opacity = String(sm(WindowView.FADE0, S));
    const n = this.frames.length;
    const f = u <= S ? 0 : ((u - S) / (1 - S)) * (n - 1);
    this.want(Math.floor(f), u >= this.u0 ? 1 : -1);
    this.u0 = u;
    this.draw(f);
  }
  private u0 = 0;

  private draw(f: number) {
    const cv = this.canvas;
    const n = this.frames.length;
    if (!cv || !n) return;
    f = Math.max(0, Math.min(n - 1, f));
    const i = Math.floor(f), t = f - i;
    let a = this.frames[i];
    const b = this.frames[Math.min(n - 1, i + 1)];
    for (let k = 1; !a && k < n; k++) a = this.frames[i - k] ?? this.frames[i + k];
    if (!a) return;
    const x = cv.getContext('2d')!;
    x.globalAlpha = 1;
    x.drawImage(a, 0, 0, cv.width, cv.height);
    if (b && t > 0.01) { x.globalAlpha = t; x.drawImage(b, 0, 0, cv.width, cv.height); x.globalAlpha = 1; }
  }

  /** Move u from a to b over ms, eased in and out once over the whole move.
   *  If the frames aren't decoded yet the clock waits at the hand-over. */
  private run(a: number, b: number, ms: number) {
    cancelAnimationFrame(this.raf);
    return new Promise<void>((res) => {
      let last = performance.now(), t = 0;
      const S = WindowView.FADE0;
      const go = (now: number) => {
        const dt = Math.min(50, now - last); last = now;
        const e0 = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        const u0 = a + (b - a) * e0;
        // hold just before the frames would show until they're decoded
        if (this.ready || (a < b ? u0 < S : true)) t = Math.min(1, t + dt / ms);
        const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        this.at(a + (b - a) * e);
        if (t < 1) this.raf = requestAnimationFrame(go); else res();
      };
      this.raf = requestAnimationFrame(go);
    });
  }

  private paneW() { return Math.round(PANE_H * (this.meta.aspect ?? 0.75)); }

  /** Lay the shadow play onto the glass: the glass is a parallelogram on
   *  screen (orthographic camera), so one affine matrix maps the play's
   *  rectangle onto it exactly. */
  private fitPane() {
    const pic = this.el.querySelector('.window-pic') as HTMLElement | null;
    const svg = this.el.querySelector('.window-svg') as SVGSVGElement | null;
    if (!pic || !svg) return;
    const W = pic.clientWidth, H = pic.clientHeight;
    const { tl, tr, bl } = this.meta.pane;
    const PW = this.paneW();
    const a = ((tr[0] - tl[0]) * W) / PW, b = ((tr[1] - tl[1]) * H) / PW;
    const c = ((bl[0] - tl[0]) * W) / PANE_H, d = ((bl[1] - tl[1]) * H) / PANE_H;
    svg.style.transform = `matrix(${a}, ${b}, ${c}, ${d}, ${tl[0] * W}, ${tl[1] * H})`;
  }

  async close() {
    cancelAnimationFrame(this.raf);
    // the write-up slides away, the still and the shadow play fade, the camera swings back out
    this.el.classList.remove('is-settled');
    this.onClose();
    if (this.motion && this.frames.length > 1 && this.geo) {
      await new Promise((r) => setTimeout(r, 300));
      await this.run(this.u || 1, 0, 2000);
    }
    this.streetView?.(null);
    this.stage.style.transform = '';
    this.stage.style.opacity = '';
    this.stage.style.transition = '';
    this.el.classList.remove('is-open');
    this.el.hidden = true; this.el.innerHTML = '';
    for (const f of this.frames) f?.close();
    this.frames = []; this.blobs = []; this.geo = null; this.u = 0; this.u0 = 0;
  }
}

// ---------------------------------------------------------------- shadow plays
const NS = 'http://www.w3.org/2000/svg';
const el = <K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, parent: Element) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  parent.appendChild(e);
  return e;
};
const ease = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t));
const seg = (t: number, a: number, b: number) => ease((t - a) / (b - a));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Two-bone reach: from root towards target with segment lengths l1, l2;
 *  the joint bends to the side `bend` (+1 / -1 across the root→target line). */
function ik(rx: number, ry: number, tx: number, ty: number, l1: number, l2: number, bend: number) {
  let dx = tx - rx, dy = ty - ry;
  let d = Math.hypot(dx, dy);
  const max = l1 + l2 - 0.01;
  if (d > max) { dx *= max / d; dy *= max / d; d = max; }
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  const ux = dx / d, uy = dy / d;
  return { jx: rx + ux * a - uy * h * bend, jy: ry + uy * a + ux * h * bend, ex: rx + dx, ey: ry + dy };
}

/** Squirrels and Seeds: someone carries a box to the shelves, slides it in,
 *  takes out their phone and notes it down, then goes for the next one. */
export function boxesPlay(svg: SVGSVGElement, PW: number) {
  const sx = PW / 300;   // designed 300 wide; squeeze sideways to fit the glass
  svg.innerHTML = '';
  const ink = '#1c0d06';
  const defs = el('defs', {}, svg);
  const f = el('filter', { id: 'soft', x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
  el('feGaussianBlur', { stdDeviation: 1.9 }, f);
  const shadow = el('g', { fill: ink, stroke: ink, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', filter: 'url(#soft)', opacity: 0.86 }, svg);
  const room = el('g', { transform: `scale(${sx} 1)` }, shadow);
  // shelves on the right, further from the glass so a little softer: jars,
  // a stack of folded clothes, tins and boxes already stored
  const shelves = el('g', {}, room);
  for (const y of [150, 235, 320]) el('rect', { x: 186, y, width: 112, height: 7, stroke: 'none' }, shelves);
  el('rect', { x: 291, y: 110, width: 8, height: 290, stroke: 'none' }, shelves);
  el('rect', { x: 188, y: 110, width: 5, height: 290, stroke: 'none' }, shelves);
  const stored: [number, number, number, number][] = [[200, 118, 30, 32], [200, 292, 32, 28]];
  for (const [x, y, w, h] of stored) el('rect', { x, y, width: w, height: h, rx: 2, stroke: 'none' }, shelves);
  for (const [x, w, h] of [[238, 14, 22], [256, 12, 18], [272, 14, 24]]) {          // jars with lids
    el('rect', { x, y: 150 - h, width: w, height: h, rx: 4, stroke: 'none' }, shelves);
    el('rect', { x: x - 1, y: 150 - h - 4, width: w + 2, height: 5, rx: 1, stroke: 'none' }, shelves);
  }
  for (let k = 0; k < 4; k++) el('rect', { x: 198 + (k % 2) * 2, y: 235 - 7 * (k + 1), width: 40, height: 6, rx: 3, stroke: 'none' }, shelves);   // folded clothes
  for (const x of [244, 258, 272]) el('rect', { x, y: 302, width: 11, height: 18, rx: 2, stroke: 'none' }, shelves);                          // tins
  // the box about to be stored, flaps open
  const box = el('path', { stroke: 'none' }, room);
  // the person, drawn in profile
  const person = el('g', {}, room);
  const legBack = el('path', { fill: 'none', 'stroke-width': 13 }, person);
  const shoeBack = el('path', { stroke: 'none' }, person);
  const armBack = el('path', { fill: 'none', 'stroke-width': 9 }, person);
  const handBack = el('circle', { r: 5, stroke: 'none' }, person);
  const torso = el('path', { stroke: 'none' }, person);
  const head = el('path', { stroke: 'none' }, person);
  const hair = el('path', { stroke: 'none' }, person);
  const strands = el('path', { fill: 'none', 'stroke-width': 1.4 }, person);
  const legFront = el('path', { fill: 'none', 'stroke-width': 13.5 }, person);
  const shoeFront = el('path', { stroke: 'none' }, person);
  const armFront = el('path', { fill: 'none', 'stroke-width': 9.5 }, person);
  const handFront = el('path', { stroke: 'none' }, person);
  // the phone: a small dark slab in the hand, its screen a soft light
  const phone = el('rect', { width: 7, height: 12, rx: 1.5, stroke: 'none' }, person);
  const glow = el('ellipse', { rx: 6, ry: 4.5, fill: '#fff1d2', stroke: 'none', opacity: 0, filter: 'url(#soft)' }, svg);
  const LOOP = 11;
  const GROUND = 396;
  const set = (e: Element, d: string) => e.setAttribute('d', d);
  return (time: number) => {
    const t = time % LOOP;
    const walkIn = seg(t, 0, 2.4), lift = seg(t, 2.6, 3.4), slide = seg(t, 3.4, 4.0), back = seg(t, 4.2, 4.7);
    const shove = 1 - Math.pow(1 - Math.min(1, Math.max(0, (t - 3.5) / 1.4)), 3);   // pushed along the shelf, out of sight
    const phoneUp = seg(t, 4.7, 5.6), phoneDown = seg(t, 7.8, 8.6), walkOut = seg(t, 8.7, 10.7);
    let x = lerp(-60, 150, walkIn); x = lerp(x, -80, walkOut);
    const face = t > 8.7 ? -1 : 1;                         // walks off the way they came
    const walking = (t < 2.4 || t > 8.7) ? 1 : 0;
    const ph = t * 7.5;
    const bob = walking * Math.abs(Math.sin(ph)) * 3.5;
    const out = phoneUp * (1 - phoneDown);                  // phone in hand
    const hipY = 298 - bob, shY = 206 - bob;
    // in the person's own frame: +X is the way they face
    const X = (u: number) => x + face * u;
    // legs: each foot swings and lifts a little, the knee bends forward
    const leg = (side: number) => {
      const s_ = walking * Math.sin(ph + (side > 0 ? 0 : Math.PI));
      const fx = X(2 + s_ * 18), fy = GROUND - Math.max(0, walking * Math.cos(ph + (side > 0 ? 0 : Math.PI))) * 7;
      const hx = X(side * 2), j = ik(hx, hipY, fx, fy, 50, 49, -face);
      const toe = fx + face * 15;
      return { d: `M ${hx} ${hipY} L ${j.jx} ${j.jy} L ${j.ex} ${j.ey}`,
               shoe: `M ${j.ex - face * 7} ${j.ey - 6} Q ${j.ex + face * 4} ${j.ey - 9} ${toe} ${j.ey - 1} Q ${toe + face * 1} ${j.ey + 3} ${toe - face * 3} ${j.ey + 3} L ${j.ex - face * 8} ${j.ey + 3} Z` };
    };
    const lb = leg(-1), lf = leg(1);
    set(legBack, lb.d); set(shoeBack, lb.shoe); set(legFront, lf.d); set(shoeFront, lf.shoe);
    // torso: jumper with rounded shoulders, a soft hem over the hips
    const lean = out * 4;                                    // leans over the phone
    set(torso, `M ${X(-5 + lean)} ${shY - 8} Q ${X(-17 + lean)} ${shY - 4} ${X(-17 + lean)} ${shY + 10} Q ${X(-19)} ${shY + 50} ${X(-15)} ${hipY - 6}
      Q ${X(-17)} ${hipY + 4} ${X(-14)} ${hipY + 9} L ${X(15)} ${hipY + 9} Q ${X(18)} ${hipY + 2} ${X(15)} ${hipY - 8}
      Q ${X(13)} ${shY + 52} ${X(18 + lean)} ${shY + 22} Q ${X(19 + lean)} ${shY + 4} ${X(10 + lean)} ${shY - 2} L ${X(6 + lean)} ${shY - 10} Z`);
    // head in profile: brow, nose, lips, chin; looks down at the phone
    const hx = X(4 + lean * 1.4), hy = shY - 30 + out * 5;
    const P = (u: number, v: number) => `${hx + face * u} ${hy + v}`;
    set(head, `M ${P(-12, -14)} Q ${P(-2, -22)} ${P(9, -16)} Q ${P(14, -10)} ${P(13, -3)} L ${P(18, 3)} Q ${P(19, 5)} ${P(14, 6)}
      Q ${P(15, 9)} ${P(13, 10)} Q ${P(14, 13)} ${P(11, 15)} Q ${P(9, 19)} ${P(3, 19)} Q ${P(-1, 19)} ${P(-1, 24)} L ${P(-1, 31)}
      L ${P(-9, 31)} Q ${P(-10, 22)} ${P(-14, 14)} Q ${P(-17, 0)} ${P(-12, -14)} Z`);
    // hair: swept back into a bun, a fringe over the brow
    set(hair, `M ${P(10, -12)} Q ${P(6, -24)} ${P(-6, -21)} Q ${P(-16, -18)} ${P(-17, -5)} Q ${P(-18, 4)} ${P(-14, 10)}
      Q ${P(-12, 2)} ${P(-11, -4)} Q ${P(-2, -14)} ${P(10, -12)} Z
      M ${P(-14, -14)} m ${-face * 5} 0 a 8 8 0 1 0 ${face * 0.1} 0 Z`);
    set(strands, `M ${P(-19, -12)} q ${-face * 5} 6 ${-face * 3} 12 M ${P(-16, -6)} q ${-face * 2} 7 ${-face * 1} 12`);
    // the box: carried at the chest, lifted to the shelf, slid in
    const carry = t < 3.4;
    const bx = carry ? lerp(X(16), 228, lift) : lerp(228, 360, shove);
    const by = carry ? lerp(shY + 34, 235, lift) : 235;
    const bw = 36, bh = 28, fl = 10 * (1 - slide);
    box.setAttribute('opacity', '1');
    set(box, `M ${bx} ${by - bh} L ${bx + bw} ${by - bh} L ${bx + bw} ${by} L ${bx} ${by} Z
      M ${bx} ${by - bh} L ${bx - 6} ${by - bh - fl} L ${bx + 4} ${by - bh - fl * 0.9} L ${bx + 9} ${by - bh} Z
      M ${bx + bw} ${by - bh} L ${bx + bw + 6} ${by - bh - fl} L ${bx + bw - 4} ${by - bh - fl * 0.9} L ${bx + bw - 9} ${by - bh} Z`);
    // arms: round the box while carrying, reaching up to store it, the phone after
    const hold = t < 4.2;
    const reach = lift * (1 - back);
    const swing = walking * Math.sin(ph) * 14;
    let fx: number, fy: number, gx: number, gy: number;
    if (hold) {
      fx = lerp(bx + (face > 0 ? bw - 4 : 4), bx + 30, reach); fy = lerp(by - bh / 2, by - bh + 4, reach);
      gx = lerp(bx + 6, bx + 8, reach); gy = lerp(by - 6, by - bh + 8, reach);
    } else if (out > 0.01) {
      fx = X(lerp(6 + swing, 32, out)); fy = lerp(hipY + 2, shY + 30, out);
      gx = X(lerp(-6 - swing, 27, out)); gy = lerp(hipY, shY + 35, out);
    } else {
      fx = X(6 + swing); fy = hipY + 2; gx = X(-6 - swing); gy = hipY;
    }
    const shF = { x: X(4 + lean), y: shY + 6 }, shB = { x: X(-6 + lean), y: shY + 6 };
    const aF = ik(shF.x, shF.y, fx, fy, 34, 33, face), aB = ik(shB.x, shB.y, gx, gy, 34, 33, face);
    set(armFront, `M ${shF.x} ${shF.y} L ${aF.jx} ${aF.jy} L ${aF.ex} ${aF.ey}`);
    set(armBack, `M ${shB.x} ${shB.y} L ${aB.jx} ${aB.jy} L ${aB.ex} ${aB.ey}`);
    handBack.setAttribute('cx', String(aB.ex)); handBack.setAttribute('cy', String(aB.ey));
    // front hand: palm with a thumb sticking up
    const hX = aF.ex, hY = aF.ey;
    set(handFront, `M ${hX - face * 5} ${hY - 4} Q ${hX + face * 4} ${hY - 6} ${hX + face * 7} ${hY} Q ${hX + face * 4} ${hY + 6} ${hX - face * 4} ${hY + 4} Z
      M ${hX} ${hY - 4} q ${face * 3} -6 ${face * 6} -5 q ${-face * 1} 4 ${-face * 4} 6 Z`);
    // the phone in the front hand, screen towards the face; a steady soft glow
    phone.setAttribute('x', String(hX + face * 2 - 3.5)); phone.setAttribute('y', String(hY - 14));
    phone.setAttribute('opacity', String(Math.min(1, out * 1.5)));
    glow.setAttribute('cx', String((hX + face * 2) * sx)); glow.setAttribute('cy', String(hY - 8));
    glow.setAttribute('opacity', String(out * out * 0.7));
  };
}

export const WINDOWS: WindowSpec[] = [
  { id: 'shop', building: 'shop', projects: ['squirrels-and-seeds'], play: boxesPlay },
];
export const windowForBuilding = (g: string) => WINDOWS.find((w) => w.building === g) ?? null;
