import { statusLabel, type Project } from '../content/projects';

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

const isPlaceholder = (href: string) => href.startsWith('TODO') || href.includes('TODO');

/** Shared markup for a project, used by the 3D panel and the 2D index. */
export function projectBody(p: Project, headingLevel: 2 | 3 = 2): string {
  const h = `h${headingLevel}`;
  const status = `<p class="p-status p-status--${p.status}">${esc(statusLabel[p.status])}</p>`;
  const highlights = p.highlights?.length
    ? `<ul class="p-highlights">${p.highlights.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`
    : '';
  const media = (p.media ?? [])
    .map((m) =>
      m.src
        ? `<figure class="p-media"><img src="${esc(m.src)}" alt="${esc(m.alt)}" loading="lazy" decoding="async" />${m.caption ? `<figcaption>${esc(m.caption)}</figcaption>` : ''}</figure>`
        : `<figure class="p-media p-media--placeholder" role="img" aria-label="${esc(m.alt)} (coming soon)"><span>${esc(m.caption ?? 'Image coming soon')}</span></figure>`,
    )
    .join('');
  const gallery = (p.media?.length ?? 0) > 1 ? `<div class="p-gallery">${media}</div>` : media;
  const stack = p.stack?.length
    ? `<ul class="p-stack" aria-label="Built with">${p.stack.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>`
    : '';
  const links = p.links?.filter((l) => !isPlaceholder(l.href)).length
    ? `<p class="p-links">${p.links!
        .filter((l) => !isPlaceholder(l.href))
        .map((l) => `<a href="${esc(l.href)}" target="_blank" rel="noopener">${esc(l.label)}<span aria-hidden="true"> ↗</span></a>`)
        .join('')}</p>`
    : '';
  return `
    ${status}
    <${h} class="p-title" id="p-title-${esc(p.id)}" tabindex="-1">${esc(p.title)}</${h}>
    <p class="p-summary">${esc(p.summary)}</p>
    ${highlights}
    ${p.body.map((b) => `<p class="p-text">${esc(b)}</p>`).join('')}
    ${gallery}
    ${stack}
    ${links}
  `;
}

export class Panel {
  readonly el: HTMLElement;
  private inner: HTMLElement;
  private returnFocus: HTMLElement | null = null;
  onClose: () => void = () => {};

  constructor(host: HTMLElement) {
    this.el = document.createElement('aside');
    this.el.className = 'panel';
    this.el.setAttribute('role', 'dialog');
    this.el.setAttribute('aria-modal', 'false');
    this.el.hidden = true;
    this.el.innerHTML = `
      <button class="panel-close" type="button" aria-label="Close project">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </button>
      <div class="panel-inner"></div>`;
    this.inner = this.el.querySelector('.panel-inner')!;
    this.el.querySelector('.panel-close')!.addEventListener('click', () => this.onClose());
    this.el.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.onClose();
    });
    host.appendChild(this.el);
  }

  get isOpen() {
    return !this.el.hidden;
  }

  open(p: Project) {
    if (!this.isOpen) this.returnFocus = document.activeElement as HTMLElement | null;
    this.inner.innerHTML = projectBody(p);
    this.el.setAttribute('aria-labelledby', `p-title-${p.id}`);
    this.el.hidden = false;
    this.inner.scrollTop = 0;
    requestAnimationFrame(() => {
      this.el.classList.add('is-open');
      (this.inner.querySelector('.p-title') as HTMLElement | null)?.focus({ preventScroll: true });
    });
  }

  close() {
    if (!this.isOpen) return;
    this.el.classList.remove('is-open');
    const done = () => { if (!this.el.classList.contains('is-open')) this.el.hidden = true; };
    window.matchMedia('(prefers-reduced-motion: reduce)').matches ? done() : setTimeout(done, 380);
    this.returnFocus?.focus?.({ preventScroll: true });
    this.returnFocus = null;
  }
}
