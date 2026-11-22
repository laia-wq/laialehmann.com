/**
 * A room behind one of the canal's windows: the pre-rendered cutaway on the
 * left, the project told plainly on the right. Nothing has to be clicked to
 * learn about the project; the room illustrates it. Hovering an object
 * lights its line in the panel (and the other way round); clicking an object
 * scrolls to its line. Rooms with more than one project get a tab per
 * project, and may swap to another render of the room for each.
 */
import { projects, type Project } from '../content/projects';
import type { Room } from '../content/rooms';
import { projectBody } from './panel';

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

interface RoomJson { size: [number, number]; groups: string[]; variants: string[] }

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((res, rej) => {
    const im = new Image();
    im.decoding = 'async';
    im.onload = () => res(im);
    im.onerror = rej;
    im.src = src;
  });
}

export class RoomView {
  readonly el: HTMLElement;
  private room!: Room;
  private data!: RoomJson;
  private ids: ImageData | null = null;
  private hot: string | null = null;
  private tab = 0;
  private returnFocus: HTMLElement | null = null;
  onClose: () => void = () => {};

  constructor(host: HTMLElement) {
    this.el = document.createElement('section');
    this.el.className = 'room';
    this.el.hidden = true;
    this.el.setAttribute('aria-label', 'Room');
    host.appendChild(this.el);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !this.el.hidden) this.close(); });
  }

  get isOpen() { return !this.el.hidden; }

  async open(room: Room) {
    this.room = room;
    this.tab = 0;
    this.returnFocus = document.activeElement as HTMLElement | null;
    const base = `${import.meta.env.BASE_URL}rooms/${room.id}/`;
    this.data = await fetch(base + 'scene.json').then((r) => r.json());
    const pic = (v: string) => `<picture><source srcset="${base}${v}.avif" type="image/avif"><img class="room-img" data-variant="${v}" src="${base}${v}.webp" alt="" decoding="async"></picture>`;
    const variants = this.data.variants.length ? this.data.variants : ['room'];
    const tabs = room.projects.length > 1
      ? `<div class="room-tabs" role="tablist">${room.projects.map((id, i) => `<button role="tab" type="button" data-tab="${i}" aria-selected="${i === 0}">${esc(byId(id)?.title ?? id)}</button>`).join('')}</div>`
      : '';
    this.el.innerHTML = `
      <div class="room-stage">
        <div class="room-pic" style="aspect-ratio:${this.data.size[0]} / ${this.data.size[1]}">
          ${variants.map(pic).join('')}
          ${this.data.groups.map((g) => `<div class="room-hl" data-hl="${g}" style="-webkit-mask-image:url(${base}hl-${g}.png);mask-image:url(${base}hl-${g}.png)"></div>`).join('')}
        </div>
        <p class="room-hint" aria-hidden="true"></p>
      </div>
      <aside class="room-panel">
        <button class="room-back" type="button"><span aria-hidden="true">←</span> back to the street</button>
        <p class="room-name">${esc(room.name)}</p>
        ${tabs}
        <div class="room-body"></div>
      </aside>`;
    this.el.querySelectorAll<HTMLImageElement>('.room-img').forEach((im, i) => im.classList.toggle('is-on', i === 0));
    this.renderBody();
    this.bind(base);
    this.el.hidden = false;
    requestAnimationFrame(() => this.el.classList.add('is-open'));
    (this.el.querySelector('.room-back') as HTMLElement).focus({ preventScroll: true });
    loadImage(base + 'ids.png').then((im) => {
      const c = document.createElement('canvas');
      c.width = im.naturalWidth; c.height = im.naturalHeight;
      const x = c.getContext('2d', { willReadFrequently: true })!;
      x.drawImage(im, 0, 0);
      this.ids = x.getImageData(0, 0, c.width, c.height);
    }).catch(() => {});
  }

  close() {
    this.el.classList.remove('is-open');
    setTimeout(() => { if (!this.el.classList.contains('is-open')) { this.el.hidden = true; this.el.innerHTML = ''; } }, 450);
    this.onClose();
    this.returnFocus?.focus?.({ preventScroll: true });
  }

  private project(): Project | undefined { return byId(this.room.projects[this.tab]); }

  private renderBody() {
    const p = this.project();
    const pid = this.room.projects[this.tab];
    const spots = this.room.spots.filter((s) => !s.project || s.project === pid);
    const body = this.el.querySelector('.room-body')!;
    body.innerHTML = `
      ${p ? projectBody(p, 2) : ''}
      <h3 class="room-sub">In this room</h3>
      <ul class="room-spots">${spots.map((s) => `<li data-spot="${s.group}" tabindex="0"><strong>${esc(s.label)}</strong><span>${esc(s.text)}</span></li>`).join('')}</ul>`;
    // the room's own list belongs near the top: move it under the summary
    const list = body.querySelector('.room-spots')!, sub = body.querySelector('.room-sub')!;
    const summary = body.querySelector('.p-summary');
    if (summary) { summary.after(sub); sub.after(list); }
    // swap the render if this tab has its own (e.g. the gardener on the fire side)
    const v = this.room.variants?.[pid] ?? 'room';
    this.el.querySelectorAll<HTMLImageElement>('.room-img').forEach((im) => im.classList.toggle('is-on', im.dataset.variant === v));
  }

  private setHot(g: string | null, from: 'room' | 'panel') {
    if (g === this.hot) return;
    this.hot = g;
    this.el.querySelectorAll<HTMLElement>('.room-hl').forEach((h) => h.classList.toggle('is-on', h.dataset.hl === g));
    this.el.querySelectorAll<HTMLElement>('[data-spot]').forEach((li) => li.classList.toggle('is-hot', li.dataset.spot === g));
    const pic = this.el.querySelector('.room-pic') as HTMLElement;
    pic.style.cursor = g && from === 'room' ? 'pointer' : '';
    const hint = this.el.querySelector('.room-hint') as HTMLElement;
    const spot = this.room.spots.find((s) => s.group === g);
    hint.textContent = spot ? spot.label : '';
    hint.classList.toggle('is-on', !!spot && from === 'room');
  }

  private groupAt(e: PointerEvent | MouseEvent): string | null {
    if (!this.ids) return null;
    const r = (this.el.querySelector('.room-pic') as HTMLElement).getBoundingClientRect();
    const u = (e.clientX - r.left) / r.width, v = (e.clientY - r.top) / r.height;
    if (u < 0 || v < 0 || u > 1 || v > 1) return null;
    const x = Math.min(this.ids.width - 1, Math.floor(u * this.ids.width)), y = Math.min(this.ids.height - 1, Math.floor(v * this.ids.height));
    const id = Math.round(this.ids.data[(y * this.ids.width + x) * 4] / 40);
    const g = id > 0 ? this.data.groups[id - 1] : null;
    const pid = this.room.projects[this.tab];
    return g && this.room.spots.some((s) => s.group === g && (!s.project || s.project === pid)) ? g : null;
  }

  private bind(_base: string) {
    const pic = this.el.querySelector('.room-pic') as HTMLElement;
    const hint = this.el.querySelector('.room-hint') as HTMLElement;
    pic.addEventListener('pointermove', (e) => {
      this.setHot(this.groupAt(e), 'room');
      const r = this.el.querySelector('.room-stage')!.getBoundingClientRect();
      hint.style.transform = `translate(${e.clientX - r.left + 14}px, ${e.clientY - r.top + 12}px)`;
    });
    pic.addEventListener('pointerleave', () => this.setHot(null, 'room'));
    pic.addEventListener('click', (e) => {
      const g = this.groupAt(e);
      if (!g) return;
      const li = this.el.querySelector(`[data-spot="${g}"]`) as HTMLElement | null;
      if (!li) return;
      li.scrollIntoView({ behavior: 'smooth', block: 'center' });
      li.classList.remove('is-pulse'); void li.offsetWidth; li.classList.add('is-pulse');
    });
    const panel = this.el.querySelector('.room-panel')!;
    panel.addEventListener('pointerover', (e) => {
      const li = (e.target as HTMLElement).closest('[data-spot]') as HTMLElement | null;
      this.setHot(li?.dataset.spot ?? null, 'panel');
    });
    panel.addEventListener('focusin', (e) => {
      const li = (e.target as HTMLElement).closest('[data-spot]') as HTMLElement | null;
      if (li) this.setHot(li.dataset.spot!, 'panel');
    });
    panel.addEventListener('pointerleave', () => this.setHot(null, 'panel'));
    this.el.querySelector('.room-back')!.addEventListener('click', () => this.close());
    this.el.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach((b) => b.addEventListener('click', () => {
      this.tab = Number(b.dataset.tab);
      this.el.querySelectorAll('[data-tab]').forEach((t) => t.setAttribute('aria-selected', String(t === b)));
      this.renderBody();
      this.setHot(null, 'panel');
    }));
  }
}

const byId = (id: string) => projects.find((p) => p.id === id);
