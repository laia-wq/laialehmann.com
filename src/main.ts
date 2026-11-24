import '@fontsource/cormorant-garamond/latin-500.css';
import '@fontsource/cormorant-garamond/latin-500-italic.css';
import '@fontsource-variable/inter/index.css';
import './styles.css';
import { person, projects } from './content/projects';
import { Panel, projectBody } from './ui/panel';
import { drawSignature } from './ui/signature';
import { RoomView } from './ui/room';
import { roomForBuilding } from './content/rooms';
import { WindowView, zoomAt, loadZoomIndex, type WindowSpec } from './ui/windowview';

type Mode = 'scene' | '2d';

let reason = '';

function chooseMode(): Mode {
  const q = new URLSearchParams(location.search).get('mode');
  if (q === '2d') { reason = 'You asked for the simple version.'; return '2d'; }
  return 'scene';
}

const app = document.getElementById('app')!;

function renderIndex(): string {
  return `
    <section class="index" aria-labelledby="index-title">
      <header class="index-head">
        <h1 id="index-title" class="index-name">${person.name}</h1>
        <p class="index-role">${person.role}</p>
        <p class="index-intro">${person.intro}</p>
      </header>
      <ol class="index-list">
        ${projects.map((p) => `<li class="index-item"><article>${projectBody(p, 3)}</article></li>`).join('')}
      </ol>
    </section>`;
}

function boot2D() {
  document.documentElement.dataset.mode = '2d';
  const note = reason
    ? `<p class="mode-note">Showing the simple version. ${reason}<a href="?">Show the canal scene</a></p>`
    : '';
  app.innerHTML = `<main id="content">${note}${renderIndex()}</main>`;
}

const GROUP_NAMES: Record<string, string> = {
  tall: 'The tall brick house',
  shop: 'The corner shop',
  corner: 'The blue-shuttered house',
  bakery: 'The bakery',
  boat: 'The houseboat',
};

/** Rooms in the canal scene and the projects each one holds (rooms open later). */
const ROOMS: { room: string; where: string; ids: string[] }[] = [
  { room: 'Squirrels and Seeds', where: 'the corner shop', ids: ['squirrels-and-seeds'] },
  { room: 'Lilies & Rain, Lilies & Fire', where: 'the greenhouse, the blue-shuttered house', ids: ['lily-and-rain', 'lily-and-fire'] },
  { room: 'Waterloo API & WatIf', where: 'upstairs, the corner shop', ids: ['watif'] },
  { room: 'The workshop', where: 'the tall brick house', ids: ['brita-robot'] },
  { room: 'Design teams', where: 'the tall brick house', ids: ['wrl', 'warg', 'medtechresolve'] },
  { room: 'Hackathons & competitions', where: 'the attic', ids: ['bridgeway', 'physics-olympics'] },
  { room: 'Community', where: 'the bakery', ids: ['donation-drives', 'youth-council'] },
  { room: 'Late night projects', where: 'the houseboat', ids: ['forest-loss', 'physics-engine', 'signwise', 'saas'] },
];

const escHtml = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

function updatedLabel() {
  const d = new Date(__BUILD_DATE__);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getFullYear()).slice(2)}`;
}

const ICONS = {
  // a lit arched window: what the projects are
  projects: '<svg viewBox="0 0 32 32" aria-hidden="true"><defs><radialGradient id="ic-glass" cx="50%" cy="62%" r="62%"><stop offset="0" stop-color="#ffe0a3"/><stop offset="0.6" stop-color="#ffb35c"/><stop offset="1" stop-color="#c8692e"/></radialGradient></defs><circle cx="16" cy="17" r="13" fill="#ffb35c" opacity="0.12"/><path d="M8.5 27V13.5a7.5 7.5 0 0 1 15 0V27z" fill="url(#ic-glass)"/><path d="M12.2 7.6c-1.6 2.3-2.2 6-1.4 9.6 1.3-2.6 1.2-6.2 1.4-9.6z" fill="#8a3b2a" opacity="0.75"/><path d="M8.5 27V13.5a7.5 7.5 0 0 1 15 0V27zM16 6v21M8.5 18h15" fill="none" stroke="#e7cc9c" stroke-width="1.4" stroke-linejoin="round"/><rect x="6.5" y="26.6" width="19" height="2.4" rx="1" fill="#e7cc9c"/></svg>',
  // an old cameo portrait in an oval frame: who I am
  profile: '<svg viewBox="0 0 32 32" aria-hidden="true"><defs><clipPath id="ic-oval"><ellipse cx="16" cy="17" rx="8.2" ry="10.2"/></clipPath></defs><ellipse cx="16" cy="17" rx="8.2" ry="10.2" fill="#3a2a1f"/><g clip-path="url(#ic-oval)" fill="#f2dcb5"><circle cx="16" cy="14.6" r="3.7"/><path d="M8.6 28c.6-4.8 3.6-7.6 7.4-7.6s6.8 2.8 7.4 7.6z"/></g><ellipse cx="16" cy="17" rx="9.2" ry="11.2" fill="none" stroke="#e7cc9c" stroke-width="1.5"/><path d="M13.6 4.6c.6-1.6 4.2-1.6 4.8 0" fill="none" stroke="#e7cc9c" stroke-width="1.3" stroke-linecap="round"/><circle cx="16" cy="5.6" r="1" fill="#e7cc9c"/></svg>',
  // a street lantern, glowing or dark
  lights: '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="14.5" r="10" fill="var(--halo, #ffd08a)" opacity="0.16"/><path d="M11.6 10.4h8.8l-1.3 9h-6.2z" fill="var(--bulb, #ffd08a)"/><path d="M11.6 10.4h8.8l-1.3 9h-6.2zM16 10.4v9" fill="none" stroke="#d9b98a" stroke-width="1.2" stroke-linejoin="round"/><path d="M10.4 10.6h11.2L18.8 6.4h-5.6z" fill="#d9b98a"/><circle cx="16" cy="4.9" r="1.2" fill="#d9b98a"/><rect x="12.4" y="19.2" width="7.2" height="2" rx="0.8" fill="#d9b98a"/><rect x="15.1" y="21" width="1.8" height="6.4" fill="#a8916f"/><rect x="12.6" y="27.2" width="6.8" height="1.8" rx="0.8" fill="#a8916f"/></svg>',
};

async function bootScene() {
  document.documentElement.dataset.mode = 'scene';
  const links = person.contact.map((l) => `<a href="${escHtml(l.href)}"${l.href.startsWith('mailto:') ? '' : ' target="_blank" rel="noopener"'}>${escHtml(l.label)}</a>`).join('');
  app.innerHTML = `
    <header class="canal-top">
      <div class="sig-block">
        <a class="sig" href="./" aria-label="${escHtml(person.name)}"><svg class="sig-canvas" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"></svg></a>
        <p class="sig-sub">${escHtml(person.tagLeft)} · university of waterloo</p>
      </div>
      <nav class="top-links" aria-label="Contact">${links}</nav>
    </header>
    <main id="content" tabindex="-1">
      <h1 class="visually-hidden">${escHtml(person.name)}, ${escHtml(person.role)}</h1>
      <div class="canal-stage" id="stage"></div>
      <p class="invite">${escHtml(person.invite)}</p>
      <nav class="dock" aria-label="Sections">
        <button type="button" data-open="projects">${ICONS.projects}<span>projects</span></button>
        <button type="button" data-open="about">${ICONS.profile}<span>profile</span></button>
        <button type="button" class="lights" aria-pressed="true">${ICONS.lights}<span>lights</span></button>
      </nav>
      <p class="updated">last updated ${updatedLabel()}</p>
      <p class="canal-label" aria-hidden="true"></p>
      <section class="sheet" id="sheet" role="dialog" aria-modal="true" hidden>
        <button class="sheet-close" type="button" aria-label="Close">×</button>
        <div class="sheet-inner"></div>
      </section>
      <p class="live visually-hidden" aria-live="polite"></p>
    </main>`;
  const stage = document.getElementById('stage')!;
  const label = app.querySelector('.canal-label') as HTMLElement;
  const live = app.querySelector('.live') as HTMLElement;
  const sheet = document.getElementById('sheet')!;
  const sheetInner = sheet.querySelector('.sheet-inner') as HTMLElement;
  const panel = new Panel(app.querySelector('main')!);
  panel.onClose = () => panel.close();

  const byId = (id: string) => projects.find((p) => p.id === id);
  const openSheet = (which: 'projects' | 'about') => {
    if (which === 'projects') {
      sheetInner.innerHTML = `<h2 class="sheet-title">Projects</h2>
        <p class="sheet-lede">Each project has a window somewhere on the street. A few can be looked into already; here they all are.</p>
        <ol class="rooms">${ROOMS.map((r) => `<li><p class="room-name">${escHtml(r.room)}<span> · ${escHtml(r.where)}</span></p>
          <ul>${r.ids.map(byId).filter(Boolean).map((p) => `<li><button type="button" data-project="${p!.id}"><strong>${escHtml(p!.title)}</strong><span>${escHtml(p!.summary)}</span></button></li>`).join('')}</ul></li>`).join('')}</ol>`;
    } else {
      sheetInner.innerHTML = `<h2 class="sheet-title">Profile</h2>
        <div class="sonder">
          <p class="sonder-word">${escHtml(person.sonder.word)} <span>(n.)</span></p>
          <p class="sonder-def">${escHtml(person.sonder.definition)}</p>
          <p>${escHtml(person.sonder.windows)}</p>
          <p>${escHtml(person.sonder.projects)}</p>
        </div>
        <p class="sheet-lede">${escHtml(person.intro)}</p>
        <dl class="facts">
          <dt>Studying</dt><dd>Honours Systems Design Engineering, University of Waterloo (2026–2031)</dd>
          <dt>Awards</dt><dd>${person.scholarships.map(escHtml).join('<br>')}</dd>
          <dt>Speaks</dt><dd>${person.spoken.map(escHtml).join(', ')}</dd>
          <dt>Builds with</dt><dd>${person.languages.map(escHtml).join(', ')}</dd>
          <dt>Elsewhere</dt><dd class="facts-links">${links}</dd>
        </dl>`;
    }
    sheet.hidden = false;
    requestAnimationFrame(() => sheet.classList.add('is-open'));
    (sheet.querySelector('.sheet-close') as HTMLElement).focus();
  };
  const closeSheet = () => { sheet.classList.remove('is-open'); setTimeout(() => { if (!sheet.classList.contains('is-open')) sheet.hidden = true; }, 250); };
  sheet.querySelector('.sheet-close')!.addEventListener('click', closeSheet);
  sheet.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest('[data-project]') as HTMLElement | null;
    if (b) { const p = byId(b.dataset.project!); if (p) panel.open(p); }
    else if (e.target === sheet) closeSheet();
  });
  app.querySelectorAll<HTMLButtonElement>('[data-open]').forEach((b) => b.addEventListener('click', () => openSheet(b.dataset.open as 'projects' | 'about')));
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (panel.isOpen) panel.close();
    else if (!sheet.hidden) closeSheet();
  });

  const sigCanvas = app.querySelector('.sig-canvas') as SVGSVGElement;
  const firstVisit = (() => { try { return localStorage.getItem('canal-lights-seen') !== '1'; } catch { return true; } })();
  const sigWidth = () => Math.min(320, Math.max(190, innerWidth * 0.2));
  drawSignature(sigCanvas, { color: '#efe3cf', animate: firstVisit && !matchMedia('(prefers-reduced-motion: reduce)').matches, width: sigWidth() });
  addEventListener('resize', () => drawSignature(sigCanvas, { color: '#efe3cf', animate: false, width: sigWidth() }));
  const { CanalScene } = await import('./canal/scene');
  stage.addEventListener('pointermove', (e) => { label.style.transform = `translate(${e.clientX + 14}px, ${e.clientY + 12}px)`; });
  // windows you can look into: found by where the pointer is on the street image
  const zoomQuads = loadZoomIndex();
  const streetUV = (x: number, y: number) => {
    const c = stage.querySelector('.canal-canvas') as HTMLElement | null;
    if (!c) return null;
    const r = c.getBoundingClientRect();
    return [(x - r.left) / r.width, (y - r.top) / r.height] as const;
  };
  let pointed: WindowSpec | null = null;
  stage.addEventListener('pointermove', (e) => {
    if (windowView.isOpen) return;
    const uv = streetUV(e.clientX, e.clientY);
    const z = uv ? zoomAt(uv[0], uv[1]) : null;
    if (z === pointed) return;
    pointed = z;
    if (z) { WindowView.prefetch(z.id); label.textContent = z.label; label.classList.add('is-on'); }
    stage.style.cursor = z ? 'pointer' : '';
  });
  const openZoom = (win: WindowSpec) => {
    label.classList.remove('is-on');
    app.classList.add('is-looking');
    const canvas = stage.querySelector('.canal-canvas') as HTMLElement;
    windowView.open(win, canvas.getBoundingClientRect()).catch(() => { app.classList.remove('is-looking'); windowView.close(); openSheet('projects'); });
    live.textContent = win.panes.length > 1 ? `${win.label}. Pick a window.` : `Looking in at ${win.label}.`;
  };
  // a click on a window opens its zoom before the street's own click sees it
  stage.addEventListener('click', (e) => {
    if (windowView.isOpen) return;
    const uv = streetUV(e.clientX, e.clientY);
    const z = uv ? zoomAt(uv[0], uv[1]) : null;
    if (z) { e.stopPropagation(); e.preventDefault(); openZoom(z); }
  }, true);
  const scene = new CanalScene(stage, {
    onHover(g) {
      if (pointed) return;     // a window's own label wins over its building's
      label.textContent = g ? GROUP_NAMES[g] ?? '' : '';
      label.classList.toggle('is-on', !!g);
    },
    onSelect(g) {
      const room = roomForBuilding(g);
      if (!room) { openSheet('projects'); return; }
      // lean in towards the building, then the room opens
      const c = scene.groupCenter(g);
      if (c) { const r = stage.getBoundingClientRect(); stage.style.transformOrigin = `${c.x - r.left}px ${c.y - r.top}px`; }
      app.classList.add('is-entering');
      label.classList.remove('is-on');
      setTimeout(() => { roomView.open(room).catch((err) => { console.error(err); app.classList.remove('is-entering'); }); }, 380);
      live.textContent = `${room.name}.`;
    },
    onLayout() {    },
  });
  const roomView = new RoomView(app);
  const windowView = new WindowView(app, stage);
  windowView.onClose = () => app.classList.remove('is-looking');
  windowView.streetView = (v) => scene.setView(v);
  // fetch the window's zoom frames once the street has settled, so a click moves at once
  const idle = (cb: () => void) => ('requestIdleCallback' in window ? (window as any).requestIdleCallback(cb, { timeout: 8000 }) : setTimeout(cb, 4000));
  setTimeout(() => idle(() => WindowView.prefetch('shop')), 3500);
  roomView.onClose = () => app.classList.remove('is-entering');
  const lightsBtn = app.querySelector('.lights') as HTMLButtonElement;
  lightsBtn.addEventListener('click', () => {
    const on = !scene.lightsOn;
    scene.setLights(on);
    lightsBtn.setAttribute('aria-pressed', String(on));
    live.textContent = on ? 'Lights on.' : 'Lights off.';
  });
  await scene.ready;
  scene.setHighlights((await zoomQuads).flat());
  if (new URLSearchParams(location.search).has('debug')) (window as unknown as { __scene: unknown }).__scene = scene;
}

if (chooseMode() === 'scene') bootScene().catch((err) => { console.error(err); reason = `The scene hit an error: ${String(err?.message ?? err)}`; boot2D(); });
else boot2D();
