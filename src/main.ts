import '@fontsource/cormorant-garamond/latin-500.css';
import '@fontsource/monsieur-la-doulaise/latin-400.css';
import '@fontsource/cormorant-garamond/latin-500-italic.css';
import '@fontsource-variable/inter/index.css';
import './styles.css';
import { person, projects } from './content/projects';
import { Panel, projectBody } from './ui/panel';
import { drawSignature } from './ui/signature';

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
  { room: 'Lilies & Rain, Lilies & Fire', where: 'the blue-shuttered house', ids: ['lily-and-rain', 'lily-and-fire'] },
  { room: 'Forest Loss', where: 'upstairs, the blue-shuttered house', ids: ['forest-loss'] },
  { room: 'Waterloo API & WatIf', where: 'upstairs, the corner shop', ids: ['watif'] },
  { room: 'The workshop', where: 'the tall brick house', ids: ['brita-robot'] },
  { room: 'Design teams', where: 'the tall brick house', ids: ['wrl', 'warg', 'medtechresolve'] },
  { room: 'Hackathons & competitions', where: 'the attic', ids: ['bridgeway', 'physics-olympics'] },
  { room: 'Community', where: 'above the bakery', ids: ['donation-drives', 'youth-council'] },
  { room: 'Late night projects', where: 'the houseboat', ids: ['physics-engine', 'signwise', 'saas'] },
];

const escHtml = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

function updatedLabel() {
  const d = new Date(__BUILD_DATE__);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getFullYear()).slice(2)}`;
}

const ICONS = {
  projects: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="7" y="5" width="18" height="22" rx="1.5" fill="#2a2018" stroke="#c9a56b" stroke-width="1.2"/><rect x="10" y="8" width="5.5" height="7" fill="#ffb35c"/><rect x="16.5" y="8" width="5.5" height="7" fill="#ffd08a"/><rect x="10" y="16.5" width="5.5" height="7" fill="#3a3027"/><rect x="16.5" y="16.5" width="5.5" height="7" fill="#ffb35c"/></svg>',
  about: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 4c2.4 3 3 5.2 0 8.2-3-3-2.4-5.2 0-8.2z" fill="#ffc46b"/><rect x="12" y="12.5" width="8" height="14" rx="1" fill="#efe3cf"/><rect x="9" y="26" width="14" height="2.5" rx="1" fill="#c9a56b"/></svg>',
  lights: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 4a8 8 0 0 0-4.5 14.6c.8.6 1.3 1.5 1.3 2.5V23h6.4v-1.9c0-1 .5-1.9 1.3-2.5A8 8 0 0 0 16 4z" fill="var(--bulb, #ffd08a)"/><rect x="12.8" y="24" width="6.4" height="3" rx="1" fill="#9c8a72"/></svg>',
};

async function bootScene() {
  document.documentElement.dataset.mode = 'scene';
  const links = person.contact.map((l) => `<a href="${escHtml(l.href)}"${l.href.startsWith('mailto:') ? '' : ' target="_blank" rel="noopener"'}>${escHtml(l.label)}</a>`).join('');
  app.innerHTML = `
    <header class="canal-top">
      <div class="sig-block">
        <a class="sig" href="./" aria-label="${escHtml(person.name)}"><canvas class="sig-canvas" aria-hidden="true"></canvas></a>
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
        <button type="button" data-open="about">${ICONS.about}<span>about</span></button>
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
        <p class="sheet-lede">Each project lives in a room somewhere on the street. The rooms are being furnished; for now, here they all are.</p>
        <ol class="rooms">${ROOMS.map((r) => `<li><p class="room-name">${escHtml(r.room)}<span> · ${escHtml(r.where)}</span></p>
          <ul>${r.ids.map(byId).filter(Boolean).map((p) => `<li><button type="button" data-project="${p!.id}"><strong>${escHtml(p!.title)}</strong><span>${escHtml(p!.summary)}</span></button></li>`).join('')}</ul></li>`).join('')}</ol>`;
    } else {
      sheetInner.innerHTML = `<h2 class="sheet-title">About</h2>
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

  const sigCanvas = app.querySelector('.sig-canvas') as HTMLCanvasElement;
  const firstVisit = (() => { try { return localStorage.getItem('canal-lights-seen') !== '1'; } catch { return true; } })();
  const sigWidth = () => Math.min(380, Math.max(220, innerWidth * 0.24));
  drawSignature(sigCanvas, { color: '#efe3cf', animate: firstVisit && !matchMedia('(prefers-reduced-motion: reduce)').matches, width: sigWidth() });
  addEventListener('resize', () => drawSignature(sigCanvas, { color: '#efe3cf', animate: false, width: sigWidth() }));
  const { CanalScene } = await import('./canal/scene');
  stage.addEventListener('pointermove', (e) => { label.style.transform = `translate(${e.clientX + 14}px, ${e.clientY + 12}px)`; });
  const scene = new CanalScene(stage, {
    onHover(g) {
      label.textContent = g ? GROUP_NAMES[g] ?? '' : '';
      label.classList.toggle('is-on', !!g);
    },
    onSelect(g) {
      live.textContent = `${GROUP_NAMES[g] ?? g}: rooms coming soon.`;
      openSheet('projects');
    },
    onLayout() {    },
  });
  const lightsBtn = app.querySelector('.lights') as HTMLButtonElement;
  lightsBtn.addEventListener('click', () => {
    const on = !scene.lightsOn;
    scene.setLights(on);
    lightsBtn.setAttribute('aria-pressed', String(on));
    live.textContent = on ? 'Lights on.' : 'Lights off.';
  });
  await scene.ready;
  if (new URLSearchParams(location.search).has('debug')) (window as unknown as { __scene: unknown }).__scene = scene;
}

if (chooseMode() === 'scene') bootScene().catch((err) => { console.error(err); reason = `The scene hit an error: ${String(err?.message ?? err)}`; boot2D(); });
else boot2D();
