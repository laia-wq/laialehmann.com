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

  private frames: HTMLImageElement[] = [];
  private canvas: HTMLCanvasElement | null = null;
  private motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;

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
    // the camera's swing round to face the window: pre-rendered frames
    const n = this.meta.frames ?? 0;
    this.frames = [];
    const loaded = Promise.all(Array.from({ length: n }, (_, k) => new Promise<void>((res) => {
      const im = new Image(); im.decoding = 'async';
      im.onload = im.onerror = () => res();
      im.src = `${base}fly_${String(k).padStart(3, '0')}.webp`;
      this.frames[k] = im;
    })));
    const still = this.el.querySelector('.window-still') as HTMLImageElement;
    const stillReady = still.decode ? still.decode().catch(() => {}) : Promise.resolve();

    // 1) glide in: the street moves so the window lands where the first frame
    //    will show it, at that frame's scale
    this.el.hidden = false;
    this.el.classList.add('is-open');
    const pic = this.el.querySelector('.window-pic') as HTMLElement;
    const c = pic.getBoundingClientRect();
    const k = (c.width / streetRect.width) / this.meta.scale;
    const sr = this.stage.getBoundingClientRect();
    const tx = streetRect.left - sr.left + this.meta.street_target[0] * streetRect.width;
    const ty = streetRect.top - sr.top + this.meta.street_target[1] * streetRect.height;
    const cx = c.left + c.width / 2 - sr.left, cy = c.top + c.height / 2 - sr.top;
    this.stage.style.transformOrigin = '0 0';
    this.stage.style.transition = this.motion ? 'transform 1.0s cubic-bezier(0.55, 0, 0.3, 1), opacity 0.25s ease 0.8s' : 'none';
    this.stage.style.transform = `translate(${cx - k * tx}px, ${cy - k * ty}px) scale(${k})`;
    this.stage.style.opacity = '0';
    await Promise.all([loaded, new Promise((r) => setTimeout(r, this.motion ? 820 : 0))]);
    // 2) the first frame takes over, then the camera swings round to face the window
    this.draw(0);
    this.canvas!.classList.add('is-on');
    if (this.motion && n > 1) await this.play(0, n - 1, 1100);
    else this.draw(n - 1);
    // 3) settle on the sharp still; the shadow play starts behind the glass; the write-up slides in
    await stillReady;
    this.el.classList.add('is-settled');
    this.fitPane();
    const t0 = performance.now();
    const tick = () => { step(this.motion ? (performance.now() - t0) / 1000 : 4.5); if (this.motion) this.raf = requestAnimationFrame(tick); };
    tick();
    (this.el.querySelector('.room-back') as HTMLElement).focus({ preventScroll: true });
  }

  private draw(i: number) {
    const im = this.frames[Math.max(0, Math.min(this.frames.length - 1, i))];
    const cv = this.canvas;
    if (!cv || !im || !im.naturalWidth) return;
    const x = cv.getContext('2d')!;
    x.drawImage(im, 0, 0, cv.width, cv.height);
  }

  /** Step through frames a→b over ms, eased. */
  private play(a: number, b: number, ms: number) {
    return new Promise<void>((res) => {
      const t0 = performance.now();
      const go = () => {
        const t = Math.min(1, (performance.now() - t0) / ms);
        const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        this.draw(Math.round(a + (b - a) * e));
        if (t < 1) requestAnimationFrame(go); else res();
      };
      go();
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
    const n = this.frames.length;
    if (this.motion && n > 1) {
      await new Promise((r) => setTimeout(r, 250));
      await this.play(n - 1, 0, 900);
    }
    // then the street glides back out from the window
    this.canvas?.classList.remove('is-on');
    this.stage.style.transition = this.motion ? 'transform 0.9s cubic-bezier(0.3, 0, 0.2, 1), opacity 0.2s ease' : 'none';
    this.stage.style.transform = '';
    this.stage.style.opacity = '';
    this.el.classList.remove('is-open');
    setTimeout(() => { if (!this.el.classList.contains('is-open')) { this.el.hidden = true; this.el.innerHTML = ''; this.stage.style.transition = ''; } }, 900);
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

/** Squirrels and Seeds: someone carries a box to the shelves, slides it in,
 *  takes out their phone and notes it down, then goes for the next one. */
export function boxesPlay(svg: SVGSVGElement, PW: number) {
  const sx = PW / 300;   // designed 300 wide; squeeze sideways to fit the glass
  svg.innerHTML = '';
  const ink = '#1c0d06';
  const shadow = el('g', { fill: ink, stroke: ink, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', filter: 'url(#soft)', opacity: 0.86 }, svg);
  const defs = el('defs', {}, svg);
  const f = el('filter', { id: 'soft', x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
  el('feGaussianBlur', { stdDeviation: 4.5 }, f);
  svg.insertBefore(defs, shadow);
  // shelves on the right, with boxes already stored
  const room = el('g', { transform: `scale(${sx} 1)` }, shadow);
  const shelves = el('g', { opacity: 0.55 }, room);
  for (const y of [150, 235, 320]) el('rect', { x: 190, y, width: 105, height: 7, stroke: 'none' }, shelves);
  el('rect', { x: 290, y: 120, width: 8, height: 280, stroke: 'none' }, shelves);
  const stored: [number, number, number, number][] = [[198, 118, 34, 32], [236, 124, 28, 26], [205, 205, 40, 30], [252, 210, 30, 25], [200, 292, 30, 28]];
  for (const [x, y, w, h] of stored) el('rect', { x, y, width: w, height: h, rx: 2, stroke: 'none' }, shelves);
  // the box that's about to be stored
  const box = el('rect', { width: 36, height: 30, rx: 2, stroke: 'none' }, room);
  // the person: head, body, two arms, two legs
  const person = el('g', {}, room);
  const head = el('circle', { r: 17, stroke: 'none' }, person);
  const body = el('path', { stroke: 'none' }, person);
  const armA = el('path', { fill: 'none', 'stroke-width': 11 }, person);
  const armB = el('path', { fill: 'none', 'stroke-width': 11 }, person);
  const legA = el('path', { fill: 'none', 'stroke-width': 14 }, person);
  const legB = el('path', { fill: 'none', 'stroke-width': 14 }, person);
  // the phone's glow shows through the blur as a small bright spot
  const glow = el('ellipse', { rx: 9, ry: 7, fill: '#fff3d6', stroke: 'none', opacity: 0, filter: 'url(#soft)' }, svg);
  const LOOP = 11;
  return (time: number) => {
    const t = time % LOOP;
    // walk in from the left carrying the box, to the shelf, lift, slide, phone, walk off
    const walkIn = seg(t, 0, 2.4), lift = seg(t, 2.6, 3.4), slide = seg(t, 3.4, 4.0), back = seg(t, 4.2, 4.6);
    const phoneUp = seg(t, 4.8, 5.3), phoneDown = seg(t, 8.0, 8.4), walkOut = seg(t, 8.6, 10.6);
    let x = lerp(-60, 150, walkIn); x = lerp(x, -80, walkOut);
    const walking = (t < 2.4 || t > 8.6) ? 1 : 0;
    const stepPh = t * 7.5;
    const bob = walking * Math.abs(Math.sin(stepPh)) * 4;
    const hipY = 300 - bob, shY = 205 - bob;
    head.setAttribute('cx', String(x + 4)); head.setAttribute('cy', String(shY - 30 + phoneUp * (1 - phoneDown) * 6));
    body.setAttribute('d', `M ${x - 20} ${shY} Q ${x} ${shY - 8} ${x + 22} ${shY} L ${x + 16} ${hipY} L ${x - 16} ${hipY} Z`);
    const sw = walking * Math.sin(stepPh) * 16;
    legA.setAttribute('d', `M ${x - 8} ${hipY} L ${x - 8 + sw} ${hipY + 50} L ${x - 4 + sw} ${hipY + 98}`);
    legB.setAttribute('d', `M ${x + 8} ${hipY} L ${x + 8 - sw} ${hipY + 50} L ${x + 12 - sw} ${hipY + 98}`);
    // the box: carried at the chest, lifted to the shelf, slid in
    const carry = t < 3.4 && t >= 0;
    const bx = carry ? lerp(x + 18, 205, lift) : lerp(205, 236, slide);
    const by = carry ? lerp(shY + 30, 289, lift) : 289;
    const stored = t >= 3.4 && t < LOOP - 0.4;
    box.setAttribute('x', String(bx)); box.setAttribute('y', String(by - 30));
    box.setAttribute('opacity', String(t < 0.05 ? 0 : stored && t > LOOP - 1 ? Math.max(0, (LOOP - 0.4 - t) / 0.6) : 1));
    // arms: round the box while carrying, reaching while storing, phone after
    const hold = carry || (t < 4.2);
    const reach = lift * (1 - back);
    const hx = hold ? lerp(x + 30, bx + 6, reach) : x + 18;
    const hy = hold ? lerp(shY + 22, by - 18, reach) : lerp(hipY - 10, shY + 18, phoneUp * (1 - phoneDown));
    const hx2 = hold ? hx + 22 : x + 22 * phoneUp * (1 - phoneDown) + 4;
    const hy2 = hold ? hy + 4 : lerp(hipY - 6, shY + 22, phoneUp * (1 - phoneDown));
    armA.setAttribute('d', `M ${x - 14} ${shY + 6} Q ${x - 2} ${(shY + hy) / 2 + 14} ${hx} ${hy}`);
    armB.setAttribute('d', `M ${x + 16} ${shY + 6} Q ${x + 26} ${(shY + hy2) / 2 + 12} ${hx2} ${hy2}`);
    // the phone: a soft glow at the hands while it's out, flickering as they tap
    const out = phoneUp * (1 - phoneDown);
    const tap = 0.85 + 0.15 * Math.sin(t * 19);
    glow.setAttribute('cx', String(((hx + hx2) / 2 + 2) * sx)); glow.setAttribute('cy', String((hy + hy2) / 2 - 6));
    glow.setAttribute('opacity', String(out * tap * 0.85));
  };
}

export const WINDOWS: WindowSpec[] = [
  { id: 'shop', building: 'shop', projects: ['squirrels-and-seeds'], play: boxesPlay },
];
export const windowForBuilding = (g: string) => WINDOWS.find((w) => w.building === g) ?? null;
