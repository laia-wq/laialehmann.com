import '@fontsource/cormorant-garamond/latin-500.css';
import '@fontsource/cormorant-garamond/latin-500-italic.css';
import '@fontsource-variable/inter/index.css';
import './styles.css';
import { person, projects } from './content/projects';
import { Panel, projectBody } from './ui/panel';

type Mode = '3d' | '2d';

function webglAvailable(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGL2RenderingContext && c.getContext('webgl2'));
  } catch {
    return false;
  }
}

let reason = '';

function chooseMode(): Mode {
  const q = new URLSearchParams(location.search).get('mode');
  if (q === '2d') { reason = 'You asked for the simple version.'; return '2d'; }
  if (!webglAvailable()) { reason = 'This browser has WebGL 2 turned off or unavailable (check that hardware acceleration is on).'; return '2d'; }
  if (q === '3d') return '3d';
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { reason = 'Your system asks for reduced motion (on Windows: Settings → Accessibility → Visual effects → Animation effects).'; return '2d'; }
  const small = matchMedia('(max-width: 720px)').matches && matchMedia('(pointer: coarse)').matches;
  const lowPower = (navigator.hardwareConcurrency ?? 8) <= 2;
  if (small) { reason = 'Small touch screens get the simple version.'; return '2d'; }
  if (lowPower) { reason = 'This device looks low-powered.'; return '2d'; }
  return '3d';
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
  const canTry = webglAvailable();
  const note = reason
    ? `<p class="mode-note">Showing the simple version. ${reason}${canTry ? ' <a href="?mode=3d">Show the 3D globe</a>' : ''}</p>`
    : '';
  app.innerHTML = `<main id="content">${note}${renderIndex()}</main>`;
}

async function boot3D() {
  document.documentElement.dataset.mode = '3d';
  const placed = projects.filter((p) => p.object === 'acorn'); // Phase 1: only the acorn is modelled.
  app.innerHTML = `
    <header class="topbar">
      <span class="wordmark" aria-hidden="true">Laia Lehmann</span>
      <button class="skip-anim" type="button">Skip the animation</button>
    </header>
    <main id="content" tabindex="-1">
      <h1 class="visually-hidden">${person.name}, ${person.role}</h1>
      <div class="stage" id="stage"><div class="loading" aria-hidden="true"></div></div>
      <div class="globe-ui">
        <button class="alarm" type="button" aria-describedby="alarm-hint">
          <span class="alarm-small">In case of curiosity</span>
          <span class="alarm-big">Break glass</span>
        </button>
        <p class="hint" id="alarm-hint">Drag to turn the globe. Hold or tap the glass to break it.</p>
      </div>
      <div class="labels" aria-hidden="true"></div>
      <nav class="world-nav" aria-label="Projects">
        <ul>${placed.map((p) => `<li><button type="button" data-id="${p.id}">${p.title}</button></li>`).join('')}</ul>
      </nav>
      <p class="live visually-hidden" aria-live="polite"></p>
    </main>`;

  const stage = document.getElementById('stage')!;
  const labels = app.querySelector('.labels') as HTMLElement;
  const live = app.querySelector('.live') as HTMLElement;
  const panel = new Panel(app.querySelector('main')!);

  const { Experience } = await import('./three/Experience');
  stage.querySelector('.loading')?.remove();

  for (const p of placed) {
    const l = document.createElement('span');
    l.className = 'obj-label';
    l.dataset.id = p.id;
    l.textContent = p.title;
    labels.appendChild(l);
  }

  const exp = new Experience(stage, placed, {
    onPhase(phase) {
      document.documentElement.dataset.phase = phase;
      if (phase === 'world') live.textContent = 'You are inside the globe. Choose a project.';
    },
    onSelect(id) {
      open(id);
    },
    onHover(id) {
      labels.querySelectorAll<HTMLElement>('.obj-label').forEach((l) => l.classList.toggle('is-hover', l.dataset.id === id));
    },
    onLabels(list) {
      for (const it of list) {
        const l = labels.querySelector<HTMLElement>(`[data-id="${it.id}"]`);
        if (!l) continue;
        l.style.transform = `translate(${it.x}px, ${it.y}px) translate(-50%, -100%)`;
        l.style.opacity = it.visible ? '' : '0';
      }
    },
  });

  function open(id: string) {
    const p = projects.find((x) => x.id === id);
    if (!p) return;
    exp.focus(id);
    panel.open(p);
  }
  panel.onClose = () => {
    panel.close();
    exp.unfocus();
  };

  app.querySelector('.alarm')!.addEventListener('click', () => exp.breakGlass());
  app.querySelector('.skip-anim')!.addEventListener('click', () => {
    exp.skip();
    (app.querySelector('.world-nav button') as HTMLElement | null)?.focus();
  });
  app.querySelectorAll<HTMLButtonElement>('.world-nav button').forEach((b) =>
    b.addEventListener('click', () => open(b.dataset.id!)),
  );
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panel.isOpen) panel.onClose();
  });

  // Hook for automated screenshot checks (?mode=3d&debug).
  if (new URLSearchParams(location.search).has('debug')) (window as unknown as { __exp: unknown }).__exp = exp;
}

if (chooseMode() === '3d') boot3D().catch((err) => { console.error(err); reason = `The 3D scene hit an error: ${String(err?.message ?? err)}`; boot2D(); });
else boot2D();
