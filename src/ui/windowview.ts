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
import { boxesPlay, dronePlay, rescuePlay, vrPlay, forestPlay, physicsPlay, signPlay, robotPlay, calendarPlay, blocksPlay, servePlay, rainPlay, firePlay, type Play } from './shadowplays';

export interface WindowSpec {
  id: string;
  /** canal building group that opens it */
  building: string;
  /** what the view says while you choose (only for more than one window) */
  hint?: string;
  /** what the street says when you point at it */
  label: string;
  /** every window's play shows (still) before a pick; picking one sets it going */
  idle?: boolean;
  /** one per window, in the order closeup.json lists them */
  panes: { project: string; label: string; play: Play }[];
}

type UV = [number, number];
interface PaneJson { tl: UV; tr: UV; bl: UV; aspect: number }
interface CloseJson {
  /** one window: its glass; or several, each with its glass */
  pane?: { tl: UV; tr: UV; bl: UV };
  aspect?: number;
  panes?: PaneJson[];
  street_target: UV;
  scale: number;
  /** how many frames the camera's swing has */
  frames?: number;
}

const byId = (id: string) => projects.find((p) => p.id === id);
const PANE_H = 400;
const V = `?v=${__ASSET_V__}`;     // the shadow play's own units: 400 tall, as wide as the glass is

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
  private static fetched = new Set<string>();
  static prefetch(id: string) {
    if (WindowView.fetched.has(id)) return;
    WindowView.fetched.add(id);
    const base = `${import.meta.env.BASE_URL}windows/${id}/`;
    fetch(base + 'closeup.json' + V).then((r) => r.json()).then((m: CloseJson) => {
      for (let k = 0; k < (m.frames ?? 0); k++) fetch(`${base}fly_${String(k).padStart(3, '0')}.webp${V}`).catch(() => {});
      fetch(`${base}${id}.webp${V}`).catch(() => {});
    }).catch(() => {});
  }

  private panes: PaneJson[] = [];
  private steps: ((t: number) => void)[] = [];
  private current = -1;
  private spec!: WindowSpec;

  async open(spec: WindowSpec, streetRect: DOMRect) {
    const base = `${import.meta.env.BASE_URL}windows/${spec.id}/`;
    this.meta = await fetch(base + 'closeup.json' + V).then((r) => r.json());
    this.spec = spec;
    this.panes = this.meta.panes ?? [{ ...this.meta.pane!, aspect: this.meta.aspect ?? 0.75 }];
    const multi = this.panes.length > 1;
    const pw = (k: number) => Math.round(PANE_H * this.panes[k].aspect);
    const plays = this.panes.map((_, k) => `
          <div class="window-play" data-k="${k}" style="-webkit-mask-image:url(${base}${multi ? `pane_${k}` : 'pane'}.png${V});mask-image:url(${base}${multi ? `pane_${k}` : 'pane'}.png${V})">
            <svg class="window-svg" viewBox="0 0 ${pw(k)} ${PANE_H}" width="${pw(k)}" height="${PANE_H}" aria-hidden="true"></svg>
          </div>`).join('');
    // each window's button covers its glass and reaches halfway to its
    // neighbours (and a little past the outer ones), so a click between two
    // windows still picks the nearer, never one further off
    const rects = this.panes.map((q) => {
      const l = Math.min(q.tl[0], q.bl[0]), r = Math.max(q.tr[0], q.tr[0] + q.bl[0] - q.tl[0]);
      const t = Math.min(q.tl[1], q.tr[1]), b = Math.max(q.bl[1], q.bl[1] + q.tr[1] - q.tl[1]);
      return { l, r, t, b };
    });
    const order = rects.map((_, k) => k).sort((a, b) => rects[a].l - rects[b].l);
    const hits = multi ? this.panes.map((_, k) => {
      const q = rects[k], i = order.indexOf(k), w = q.r - q.l, h = q.b - q.t;
      const prev = i > 0 ? rects[order[i - 1]] : null, next = i < order.length - 1 ? rects[order[i + 1]] : null;
      const l = prev ? (prev.r + q.l) / 2 : q.l - w * 0.18, r = next ? (q.r + next.l) / 2 : q.r + w * 0.18;
      const t = q.t - h * 0.08, b = q.b + h * 0.08;
      return `<button class="pane-hit" type="button" data-k="${k}" style="left:${l * 100}%;top:${t * 100}%;width:${(r - l) * 100}%;height:${(b - t) * 100}%"><span>${spec.panes[k]?.label ?? ''}</span></button>`;
    }).join('') : '';
    const glows = multi ? this.panes.map((_, k) => `<div class="pane-glow" data-k="${k}" style="-webkit-mask-image:url(${base}pane_${k}.png${V});mask-image:url(${base}pane_${k}.png${V})"></div>`).join('') : '';
    this.el.innerHTML = `
      <div class="room-stage">
        <div class="room-pic window-pic" style="aspect-ratio: 4 / 3">
          <canvas class="window-fly" width="960" height="720"></canvas>
          <picture><source srcset="${base}${spec.id}.avif${V}" type="image/avif"><img class="room-img window-still" src="${base}${spec.id}.webp${V}" alt="" decoding="async"></picture>
          ${plays}
          ${glows}
          ${hits}
        </div>
        ${multi ? `<button class="room-back window-back-float" type="button"><span aria-hidden="true">←</span> back to the street</button>
        <p class="window-hint">${spec.hint ?? ''}</p>` : ''}
      </div>
      <aside class="room-panel">
        <button class="room-back" type="button"><span aria-hidden="true">←</span> back to the street</button>
        <div class="room-body"></div>
      </aside>`;
    this.el.querySelectorAll('.room-back').forEach((b) => b.addEventListener('click', () => this.close()));
    this.el.querySelectorAll<HTMLButtonElement>('.pane-hit').forEach((b) => {
      const k = Number(b.dataset.k);
      const glow = (on: boolean) => this.el.querySelector(`.pane-glow[data-k="${k}"]`)?.classList.toggle('is-hot', on);
      b.addEventListener('click', () => this.select(k));
      b.addEventListener('pointerenter', () => glow(true));
      b.addEventListener('pointerleave', () => glow(false));
      b.addEventListener('focus', () => glow(b.matches(':focus-visible')));
      b.addEventListener('blur', () => glow(false));
    });
    // a click anywhere on the picture that isn't a window goes back out
    (this.el.querySelector('.room-stage') as HTMLElement).addEventListener('click', (e) => {
      if (!this.el.classList.contains('is-there')) return;
      if ((e.target as HTMLElement).closest('.pane-hit, .room-back')) return;
      this.close();
    });
    this.canvas = this.el.querySelector('.window-fly');
    this.steps = [...this.el.querySelectorAll<SVGSVGElement>('.window-svg')].map((svg, k) => (spec.panes[k]?.play ?? boxesPlay)(svg, pw(k)));
    this.current = -1;
    // the camera's swing round to face the window: pre-rendered frames. All
    // are fetched (compressed), but only a few around the playhead are kept
    // decoded at once, so memory stays small however big the frames are.
    const n = this.meta.frames ?? 0;
    this.frames = new Array(n);
    this.blobs = new Array(n);
    this.ready = false;
    const fetched = Promise.all(Array.from({ length: n }, (_, k) =>
      fetch(`${base}fly_${String(k).padStart(3, '0')}.webp${V}`).then((r) => r.blob()).then((bl) => { this.blobs[k] = bl; }).catch(() => {})));
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
    // settle on the sharp still. One window: its shadow play starts and the
    // write-up slides in. Several: wait for a pick.
    await stillReady;
    this.el.classList.add('is-there');
    this.fitPane();
    if (spec.idle) {
      this.steps.forEach((st) => st(0));
      this.el.querySelectorAll<HTMLElement>('.window-play').forEach((e) => e.classList.add('is-on'));
    }
    if (!multi) this.select(0);
    else (this.el.querySelector('.pane-hit') as HTMLElement)?.focus({ preventScroll: true });
  }

  /** Light up one window's shadow play and show its write-up. */
  private select(k: number) {
    if (k === this.current) return;
    this.current = k;
    cancelAnimationFrame(this.raf);
    const p = byId(this.spec.panes[k]?.project ?? '');
    const body = this.el.querySelector('.room-body') as HTMLElement;
    body.innerHTML = p ? projectBody(p, 2) : '';
    if (this.spec.idle) this.steps.forEach((st, j) => { if (j !== k) st(0); });
    else this.el.querySelectorAll<HTMLElement>('.window-play').forEach((e) => e.classList.toggle('is-on', Number(e.dataset.k) === k));
    this.el.querySelectorAll<HTMLElement>('.pane-hit').forEach((e) => e.setAttribute('aria-pressed', String(Number(e.dataset.k) === k)));
    const wasSettled = this.el.classList.contains('is-settled');
    this.el.classList.add('is-settled');
    // the picture moves aside for the write-up: lay the plays on again once it has
    setTimeout(() => this.fitPane(), wasSettled ? 0 : 650);
    const step = this.steps[k];
    const t0 = performance.now();
    const tick = () => { step(this.motion ? (performance.now() - t0) / 1000 : 4.5); if (this.motion) this.raf = requestAnimationFrame(tick); };
    tick();
    if (!wasSettled) (this.el.querySelector('.room-panel .room-back') as HTMLElement).focus({ preventScroll: true });
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

  /** Lay each shadow play onto its glass: the glass is a parallelogram on
   *  screen, so one affine matrix maps the play's rectangle onto it exactly. */
  private fitPane() {
    const pic = this.el.querySelector('.window-pic') as HTMLElement | null;
    if (!pic) return;
    const W = pic.clientWidth, H = pic.clientHeight;
    // once the write-up is open, the picture shrinks to the space left of it
    // (all of it for several windows, a little for one, centred on the glass)
    const panel = this.el.querySelector('.room-panel') as HTMLElement | null;
    const wide = innerWidth > 820;
    const free = wide ? innerWidth - (panel?.offsetWidth ?? 0) : innerWidth;
    const fit = Math.min(1, (free - 24) / W);
    this.el.style.setProperty('--settle-scale', String(this.panes.length > 1 ? Math.min(0.92, fit) : Math.min(0.9, Math.max(fit, 0.82))));
    this.el.querySelectorAll<SVGSVGElement>('.window-svg').forEach((svg, k) => {
      const q = this.panes[k]; if (!q) return;
      const { tl, tr, bl } = q;
      const PW = Math.round(PANE_H * q.aspect);
      const a = ((tr[0] - tl[0]) * W) / PW, b = ((tr[1] - tl[1]) * H) / PW;
      const c = ((bl[0] - tl[0]) * W) / PANE_H, d = ((bl[1] - tl[1]) * H) / PANE_H;
      svg.style.transform = `matrix(${a}, ${b}, ${c}, ${d}, ${tl[0] * W}, ${tl[1] * H})`;
    });
  }

  async close() {
    cancelAnimationFrame(this.raf);
    // the write-up slides away, the still and the shadow play fade, the camera swings back out
    this.el.classList.remove('is-settled', 'is-there');
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
    this.frames = []; this.blobs = []; this.geo = null; this.u = 0; this.u0 = 0; this.current = -1; this.steps = [];
  }
}

export const WINDOWS: WindowSpec[] = [
  { id: 'shop', building: 'shop', label: 'Squirrels and Seeds', panes: [{ project: 'squirrels-and-seeds', label: 'Squirrels and Seeds', play: boxesPlay }] },
  { id: 'design', building: 'tall', label: 'Design teams', hint: 'three design teams, three windows. pick one.',
    panes: [
      { project: 'warg', label: 'WARG', play: dronePlay },
      { project: 'medtechresolve', label: 'MedTechResolve', play: rescuePlay },
      { project: 'wrl', label: 'Waterloo Reality Labs', play: vrPlay },
    ] },
  { id: 'firsts', building: 'boat', label: 'Where it started', hint: 'my first three projects. pick a window.',
    panes: [
      { project: 'forest-loss', label: 'Forest Loss Detection', play: forestPlay },
      { project: 'physics-engine', label: '2D Physics Engine', play: physicsPlay },
      { project: 'signwise', label: 'Signwise', play: signPlay },
    ] },
  { id: 'robot', building: 'tall', label: 'Sink-finding robot', panes: [{ project: 'brita-robot', label: 'Sink-finding robot', play: robotPlay }] },
  { id: 'watif', building: 'shop', label: 'Waterloo API + WatIf', panes: [{ project: 'watif', label: 'Waterloo API + WatIf', play: calendarPlay }] },
  { id: 'saas', building: 'shop', label: 'SaaS from scratch', panes: [{ project: 'saas', label: 'SaaS from scratch', play: blocksPlay }] },
  { id: 'lilies', building: 'corner', label: 'Lily and Rain, Lily and Fire', hint: 'two lilies. pick a window.', idle: true,
    panes: [
      { project: 'lily-and-rain', label: 'Lily and Rain', play: rainPlay },
      { project: 'lily-and-fire', label: 'Lily and Fire', play: firePlay },
    ] },
  { id: 'community', building: 'bakery', label: 'Community', panes: [{ project: 'community', label: 'Community', play: servePlay }] },
];
export const windowById = (id: string) => WINDOWS.find((w) => w.id === id) ?? null;

/** Where each zoom's windows are on the street (public/windows/index.json),
 *  only for zooms whose close-up has been rendered. */
type Quad = [number, number][];
let ZOOM_INDEX: { id: string; quads: Quad[]; hull: Quad | null }[] = [];
/** Convex hull (monotone chain): the outline round a group of windows, so the
 *  wall between them counts as part of the group but nothing beyond it does. */
const hullOf = (pts: [number, number][]): Quad => {
  const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: number[], a: number[], b: number[]) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo: Quad = [], hi: Quad = [];
  for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of [...p].reverse()) { while (hi.length >= 2 && cross(hi[hi.length - 2], hi[hi.length - 1], q) <= 0) hi.pop(); hi.push(q); }
  return [...lo.slice(0, -1), ...hi.slice(0, -1)];
};
export async function loadZoomIndex() {
  try {
    const base = `${import.meta.env.BASE_URL}windows/`;
    const idx: Record<string, Quad[]> & { ready?: string[] } = await fetch(base + 'index.json' + V).then((r) => r.json());
    ZOOM_INDEX = (idx.ready ?? []).filter((id) => windowById(id) && Array.isArray(idx[id])).map((id) => {
      const quads = idx[id] as Quad[];
      return { id, quads, hull: quads.length > 1 ? hullOf(quads.flat() as [number, number][]) : null };
    });
  } catch { ZOOM_INDEX = []; }
  return ZOOM_INDEX.map((z) => z.quads);
}
const inQuad = (q: Quad, u: number, v: number) => {
  let inside = false;
  for (let i = 0, j = q.length - 1; i < q.length; j = i++) {
    const [xi, yi] = q[i], [xj, yj] = q[j];
    if ((yi > v) !== (yj > v) && u < ((xj - xi) * (v - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};
/** The zoom whose window is under (u, v) on the street image, if any: a
 *  window itself first, then the wall between a group's windows. */
export const zoomAt = (u: number, v: number) => {
  const z = ZOOM_INDEX.find((e) => e.quads.some((q) => inQuad(q, u, v))) ?? ZOOM_INDEX.find((e) => e.hull && inQuad(e.hull, u, v));
  return z ? windowById(z.id) : null;
};
export const windowForBuilding = (g: string) => WINDOWS.find((w) => w.building === g) ?? null;
