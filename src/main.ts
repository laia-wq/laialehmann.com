import '@fontsource/cormorant-garamond/latin-500.css';
import '@fontsource/monsieur-la-doulaise/latin-400.css';
import '@fontsource/cormorant-garamond/latin-500-italic.css';
import '@fontsource-variable/inter/index.css';
import './styles.css';
import { person, projects } from './content/projects';
import { projectBody } from './ui/panel';

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

async function bootScene() {
  document.documentElement.dataset.mode = 'scene';
  app.innerHTML = `
    <header class="canal-top">
      <span class="wordmark">${person.name}</span>
      <a class="canal-list" href="?mode=2d">Project list</a>
    </header>
    <main id="content" tabindex="-1">
      <h1 class="visually-hidden">${person.name}, ${person.role}</h1>
      <div class="canal-stage" id="stage"></div>
      <p class="canal-label" aria-hidden="true"></p>
      <p class="live visually-hidden" aria-live="polite"></p>
    </main>`;
  const stage = document.getElementById('stage')!;
  const label = app.querySelector('.canal-label') as HTMLElement;
  const live = app.querySelector('.live') as HTMLElement;
  const { CanalScene } = await import('./canal/scene');
  let mx = 0, my = 0;
  stage.addEventListener('pointermove', (e) => { mx = e.clientX; my = e.clientY; label.style.transform = `translate(${mx + 14}px, ${my + 12}px)`; });
  const scene = new CanalScene(stage, {
    onHover(g) {
      label.textContent = g ? GROUP_NAMES[g] ?? '' : '';
      label.classList.toggle('is-on', !!g);
    },
    onSelect(g) {
      live.textContent = `${GROUP_NAMES[g] ?? g}: rooms coming soon.`;
    },
  });
  await scene.ready;
  if (new URLSearchParams(location.search).has('debug')) (window as unknown as { __scene: unknown }).__scene = scene;
}

if (chooseMode() === 'scene') bootScene().catch((err) => { console.error(err); reason = `The scene hit an error: ${String(err?.message ?? err)}`; boot2D(); });
else boot2D();
