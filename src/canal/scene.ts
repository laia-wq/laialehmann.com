/**
 * The canal scene: a fixed view rendered in Blender (Cycles) shown exactly as
 * rendered, with a thin WebGL layer for the life a still image can't have:
 *   - the canal's reflections ripple (only where water shows)
 *   - smoke drifts up out of every chimney
 *   - candles flicker
 *   - on the first visit the lights are off, then come on one by one, in an
 *     order baked per window and lamp (delay.png), a few stuttering first
 * Hovering a building lifts it slightly; clicking reports which one.
 *
 * Assets (tools/blender/concepts/canal_final.py → tools/blender/package_canal.mjs):
 *   canal(.avif/.webp), canal-1400(...)   the render, lights on
 *   canal-off(...), canal-off-1400(...)    the same render with every light off
 *   water.png  ids.png  delay.png  scene.json   masks, switch-on order, groups, lights, smoke
 */

export interface CanalEvents {
  onHover(group: string | null): void;
  onSelect(group: string): void;
  /** Where the render sits on screen (CSS px), so overlays can line up with it. */
  onLayout?(rect: { left: number; top: number; width: number; height: number }): void;
}

interface SceneJson {
  size: [number, number];
  groups: string[];
  lights: { x: number; y: number; k: string; c: [number, number, number]; e: number }[];
  smoke?: { x: number; y: number; r: number }[];
  bg?: [number, number, number][];
}

const BASE = `${import.meta.env.BASE_URL}canal/`;
const MAX_LIGHTS = 96;
const MAX_SMOKE = 16;
const SEEN_KEY = 'canal-lights-seen';

const VERT = `
attribute vec2 aPos;
varying vec2 vUv;
void main() { vUv = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5); gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FRAG = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uImg, uOff, uWater, uIds, uDelay;
uniform vec2 uImgPx;
uniform float uTime, uHover, uMotion, uAspect, uOn, uIntroT;
uniform vec4 uLights[${MAX_LIGHTS}];
uniform int uCount;
uniform vec4 uSmoke[${MAX_SMOKE}];
uniform int uSmokeCount;
uniform vec4 uSmokeBox;       // min x, min y, max x, max y of all the plumes

float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

void main() {
  vec2 uv = vUv;
  float t = uTime * uMotion;
  float w = texture2D(uWater, uv).r;

  // Water: reflections ripple sideways (a few pixels) and bob a little,
  // with slow drifting noise so it never looks like a repeating pattern.
  vec2 q = vec2(uv.x * uAspect, uv.y) * 90.0;
  float n1 = vnoise(q * vec2(0.6, 2.2) + vec2(t * 0.35, t * 0.9));
  float n2 = vnoise(q * vec2(1.3, 4.5) - vec2(t * 0.5, t * 1.4));
  float ripple = sin(uv.y * 2600.0 + t * 2.2 + n1 * 6.0) * 0.6 + (n2 - 0.5) * 1.6;
  vec2 off = vec2(ripple * 4.0, (n1 - 0.5) * 2.0) * uImgPx * uMotion;
  // only open water moves, and only ever borrows from open water: nothing
  // standing in it (walls, lamps, boats, lily pads) gets smeared
  off *= smoothstep(0.85, 1.0, w) * smoothstep(0.85, 1.0, texture2D(uWater, uv + off).r);
  vec4 on = texture2D(uImg, uv + off);
  vec4 dark = texture2D(uOff, uv + off);
  on.rgb *= 1.0 + 0.04 * w * (n2 - 0.5) * uMotion;

  // Lights switching on one after another: every window, lamp and sign has
  // its own moment (r), spread smoothly into the light it throws around it
  // (g = how close to one), and a few of them stutter before they catch.
  vec4 D = texture2D(uDelay, uv);
  float own = D.r;
  float delay = 1.5 * mix(vnoise(uv * 3.0 + 7.0), own, smoothstep(0.0, 0.6, D.g));
  float lt = uIntroT - delay;
  float k = smoothstep(0.0, 0.12, lt);
  float sid = fract(own * 53.7);
  if (sid > 0.8 && D.g > 0.3 && lt > 0.0 && lt < 0.6) k *= 0.25 + 0.75 * step(0.45, fract(lt * 5.5 + sid * 9.0));
  k *= uOn;
  vec4 c = mix(dark, on, k);

  // Candle flicker around each small flame, and a soft halo round the street
  // lamps (w = halo * 1000 + flicker, packed).
  float f = 0.0, halo = 0.0;
  for (int i = 0; i < ${MAX_LIGHTS}; i++) {
    if (i >= uCount) break;
    vec4 L = uLights[i];
    vec2 d = (uv - L.xy) * vec2(uAspect, 1.0);
    float r2 = dot(d, d);
    if (r2 > 0.006) continue;
    float n = sin(t * 7.1 + L.z) * 0.5 + sin(t * 12.7 + L.z * 2.3) * 0.3 + sin(t * 23.0 + L.z * 4.1) * 0.2;
    float fl = fract(L.w), hl = floor(L.w) / 1000.0;
    f += fl * n * uMotion * exp(-r2 / 0.00022);
    halo += hl * (1.0 + 0.25 * n * uMotion) * exp(-r2 / 0.0009);
  }
  c.rgb *= 1.0 + f * k;
  c.rgb += vec3(1.0, 0.66, 0.36) * halo * k;

  // Chimney smoke: soft puffs rising, swelling and fading, drifting with the breeze.
  float a = 0.0;
  if (uv.x > uSmokeBox.x && uv.y > uSmokeBox.y && uv.x < uSmokeBox.z && uv.y < uSmokeBox.w)
  for (int i = 0; i < ${MAX_SMOKE}; i++) {
    if (i >= uSmokeCount) break;
    vec4 S = uSmoke[i];
    vec2 rel = uv - S.xy;
    if (rel.y > S.z * 5.0 || rel.y < -0.11 - S.z * 5.0 || abs(rel.x - S.z * 2.5) > S.z * 9.0) continue;
    for (int j = 0; j < 6; j++) {
      float ph = fract(t * 0.055 + float(j) / 6.0 + S.w);
      vec2 cen = S.xy + vec2(S.z * (4.5 * ph + 0.7 * sin(t * 0.6 + float(j) * 1.7 + S.w * 6.0)), -0.11 * ph);
      float rad = S.z * (1.2 + 3.0 * ph);
      vec2 dd = vec2(uv.x - cen.x, (uv.y - cen.y) / uAspect);
      float dist = length(dd) / rad;
      float wisp = 0.75 + 0.5 * vnoise(dd / rad * 2.5 + vec2(float(j) * 3.1, t * 0.3));
      a += smoothstep(1.0, 0.1, dist) * (1.0 - ph) * smoothstep(0.0, 0.1, ph) * 0.6 * wisp;
    }
  }
  c.rgb = mix(c.rgb, vec3(0.5, 0.48, 0.52) * (0.55 + 0.45 * uOn), clamp(a, 0.0, 0.8));

  // Hover: lift the building under the pointer a little.
  float id = texture2D(uIds, uv).r;
  if (uHover > 0.0 && abs(id - uHover) < 0.03) c.rgb = c.rgb * 1.1 + vec3(0.008, 0.006, 0.004);

  // Dither: breaks up banding in the dark sky gradient.
  c.rgb += (hash(gl_FragCoord.xy + fract(uTime) * 0.0) - 0.5) / 255.0 * 1.5;
  gl_FragColor = c;
}`;

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((res, rej) => {
    const im = new Image();
    im.decoding = 'async';
    im.onload = () => res(im);
    im.onerror = rej;
    im.src = src;
  });
}
const loadRender = (name: string) => loadImage(BASE + name + '.avif').catch(() => loadImage(BASE + name + '.webp'));

function seen(): boolean {
  try { return localStorage.getItem(SEEN_KEY) === '1'; } catch { return false; }
}
function markSeen() {
  try { localStorage.setItem(SEEN_KEY, '1'); } catch { /* private mode: fine, it just plays again */ }
}

export class CanalScene {
  private container: HTMLElement;
  private events: CanalEvents;
  private canvas = document.createElement('canvas');
  private gl: WebGLRenderingContext | null = null;
  private prog: WebGLProgram | null = null;
  private u: Record<string, WebGLUniformLocation | null> = {};
  private img!: HTMLImageElement;
  private ids!: ImageData;
  private data!: SceneJson;
  private hover: string | null = null;
  private motion = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1;
  private start = performance.now();
  private raf = 0;
  private fallback: HTMLImageElement | null = null;
  private intro = true;
  ready: Promise<void>;

  constructor(container: HTMLElement, events: CanalEvents) {
    this.container = container;
    this.events = events;
    this.canvas.className = 'canal-canvas';
    this.canvas.setAttribute('role', 'img');
    this.canvas.setAttribute('aria-label', 'Four old buildings standing in dark canal water at night, joined by rickety bridges, with lit windows, lanterns and boats.');
    this.intro = !seen() && this.motion === 1;
    this.ready = this.init();
  }

  private async init() {
    const big = Math.min(window.devicePixelRatio || 1, 2) * Math.max(innerWidth, innerHeight * 4 / 3) > 1500;
    const sfx = big ? '' : '-1400';
    const [data, img, off, water, ids, delay] = await Promise.all([
      fetch(BASE + 'scene.json').then((r) => r.json() as Promise<SceneJson>),
      loadRender('canal' + sfx),
      loadRender('canal-off' + sfx).catch(() => null),
      loadImage(BASE + 'water.png'),
      loadImage(BASE + 'ids.png'),
      loadImage(BASE + 'delay.png').catch(() => null),
    ]);
    this.data = data;
    this.img = img;
    const ic = document.createElement('canvas');
    ic.width = ids.naturalWidth; ic.height = ids.naturalHeight;
    const ictx = ic.getContext('2d', { willReadFrequently: true })!;
    ictx.drawImage(ids, 0, 0);
    this.ids = ictx.getImageData(0, 0, ic.width, ic.height);
    const [t, m, b] = data.bg ?? [[12, 13, 20], [4, 5, 8], [6, 7, 11]];
    this.container.style.background = `linear-gradient(to bottom, rgb(${t}), rgb(${m}) 50%, rgb(${b}))`;
    document.body.style.background = `rgb(${m})`;
    if (!off) this.intro = false;

    this.gl = this.canvas.getContext('webgl', { antialias: false, premultipliedAlpha: false, alpha: false });
    if (this.gl && this.setupGL(img, off ?? img, water, ids, delay)) {
      this.container.appendChild(this.canvas);
    } else {
      this.fallback = img;
      img.className = 'canal-canvas';
      img.alt = this.canvas.getAttribute('aria-label')!;
      this.container.appendChild(img);
      this.intro = false;
    }
    if (this.intro) markSeen();
    this.start = performance.now();
    this.bind();
    this.resize();
    new ResizeObserver(() => this.resize()).observe(this.container);
    this.loop();
  }

  private setupGL(img: HTMLImageElement, off: HTMLImageElement, water: HTMLImageElement, ids: HTMLImageElement, delay: HTMLImageElement | null) {
    const gl = this.gl!;
    const sh = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.warn(gl.getShaderInfoLog(s)); return null; }
      return s;
    };
    const vs = sh(gl.VERTEX_SHADER, VERT), fs = sh(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return false;
    const p = gl.createProgram()!;
    gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) return false;
    gl.useProgram(p);
    this.prog = p;
    for (const n of ['uTime', 'uHover', 'uMotion', 'uOn', 'uIntroT']) this.u[n] = gl.getUniformLocation(p, n);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(p, 'aPos');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const tex = (unit: number, im: HTMLImageElement, name: string, nearest = false) => {
      const t = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, im);
      const f = nearest ? gl.NEAREST : gl.LINEAR;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.uniform1i(gl.getUniformLocation(p, name), unit);
    };
    tex(0, img, 'uImg');
    tex(1, off, 'uOff');
    tex(2, water, 'uWater');
    tex(3, ids, 'uIds', true);
    if (delay) tex(4, delay, 'uDelay');
    else { const blank = document.createElement('canvas'); blank.width = blank.height = 1; tex(4, blank as unknown as HTMLImageElement, 'uDelay'); }
    gl.uniform2f(gl.getUniformLocation(p, 'uImgPx'), 1 / img.naturalWidth, 1 / img.naturalHeight);
    gl.uniform1f(gl.getUniformLocation(p, 'uAspect'), img.naturalWidth / img.naturalHeight);
    const L = this.data.lights.slice(0, MAX_LIGHTS);
    const arr = new Float32Array(MAX_LIGHTS * 4);
    L.forEach((l, i) => {
      const strength = l.k === 'candle' ? 0.06 : l.k === 'pl' ? 0.035 : 0.045;
      // street lamps and lanterns (the brighter flames) get a soft glow around them
      const halo = l.k === 'candle' && l.e >= 5 ? Math.round(Math.min(1, l.e / 32) * 60) : 0;
      arr.set([l.x, l.y, (i * 2.399) % 6.283, halo + strength], i * 4);
    });
    gl.uniform4fv(gl.getUniformLocation(p, 'uLights'), arr);
    gl.uniform1i(gl.getUniformLocation(p, 'uCount'), L.length);
    const S = (this.data.smoke ?? []).slice(0, MAX_SMOKE);
    const sarr = new Float32Array(MAX_SMOKE * 4);
    S.forEach((s, i) => sarr.set([s.x, s.y, Math.max(s.r, 0.004), (i * 0.37) % 1], i * 4));
    gl.uniform4fv(gl.getUniformLocation(p, 'uSmoke'), sarr);
    gl.uniform1i(gl.getUniformLocation(p, 'uSmokeCount'), S.length);
    const box = S.length
      ? [Math.min(...S.map((s) => s.x - s.r * 7)), Math.min(...S.map((s) => s.y - 0.11 - s.r * 5)), Math.max(...S.map((s) => s.x + s.r * 12)), Math.max(...S.map((s) => s.y + s.r * 5))]
      : [2, 2, -1, -1];
    gl.uniform4f(gl.getUniformLocation(p, 'uSmokeBox'), box[0], box[1], box[2], box[3]);
    return true;
  }

  private resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h || !this.img) return;
    const ar = this.img.naturalWidth / this.img.naturalHeight;
    let cw = w, ch = w / ar;
    if (ch > h) { ch = h; cw = h * ar; }
    const el = (this.fallback ?? this.canvas) as HTMLElement;
    el.style.width = `${cw}px`;
    el.style.height = `${ch}px`;
    this.events.onLayout?.({ left: (w - cw) / 2, top: (h - ch) / 2, width: cw, height: ch });
    if (!this.fallback) {
      // sharp on retina, but never more than ~2.6M pixels of shader work a frame
      let dpr = Math.min(window.devicePixelRatio || 1, 2, this.img.naturalWidth / cw);
      dpr = Math.min(dpr, Math.sqrt(2.6e6 / (cw * ch)));
      this.canvas.width = Math.round(cw * dpr);
      this.canvas.height = Math.round(ch * dpr);
      this.gl?.viewport(0, 0, this.canvas.width, this.canvas.height);
      this.draw();
    }
  }

  private groupAt(clientX: number, clientY: number): string | null {
    const el = (this.fallback ?? this.canvas) as HTMLElement;
    const r = el.getBoundingClientRect();
    const u = (clientX - r.left) / r.width, v = (clientY - r.top) / r.height;
    if (u < 0 || u > 1 || v < 0 || v > 1) return null;
    const x = Math.min(this.ids.width - 1, Math.floor(u * this.ids.width));
    const y = Math.min(this.ids.height - 1, Math.floor(v * this.ids.height));
    const id = Math.round(this.ids.data[(y * this.ids.width + x) * 4] / 40);
    return id > 0 ? this.data.groups[id - 1] ?? null : null;
  }

  private bind() {
    const el = (this.fallback ?? this.canvas) as HTMLElement;
    el.addEventListener('pointermove', (e) => this.setHover(this.groupAt(e.clientX, e.clientY)));
    el.addEventListener('pointerleave', () => this.setHover(null));
    el.addEventListener('click', (e) => {
      const g = this.groupAt(e.clientX, e.clientY);
      if (g) this.events.onSelect(g);
    });
  }

  private setHover(g: string | null) {
    if (g === this.hover) return;
    this.hover = g;
    ((this.fallback ?? this.canvas) as HTMLElement).style.cursor = g ? 'pointer' : '';
    this.events.onHover(g);
    if (!this.motion) this.draw();
  }

  /** Still dark for a moment, then the lights come on one by one (the shader
   *  staggers them); the intro is over once the last one has caught. */
  private introRunning(s: number) {
    if (this.intro && s > 3.6) this.intro = false;
    return this.intro;
  }

  private draw() {
    const gl = this.gl, p = this.prog;
    if (!gl || !p) return;
    const s = (performance.now() - this.start) / 1000;
    const intro = this.introRunning(s);
    const fade = this.motion ? Math.max(0, 1 - (performance.now() - this.offAt) / 350) : 0;
    gl.uniform1f(this.u.uTime, s);
    gl.uniform1f(this.u.uMotion, this.motion);
    gl.uniform1f(this.u.uOn, this.lightsOff ? fade : 1);
    gl.uniform1f(this.u.uIntroT, intro ? s - 0.9 : 100);
    const idx = this.hover ? this.data.groups.indexOf(this.hover) + 1 : 0;
    gl.uniform1f(this.u.uHover, idx ? (idx * 40) / 255 : 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    if (document.hidden || (!this.motion && !this.intro && !this.lightsOff)) return;
    this.draw();
  };

  private lightsOff = false;
  private offAt = 0;
  get lightsOn() { return !this.lightsOff; }
  /** The dock's lights switch: off fades the street dark, on replays the switch-on. */
  setLights(on: boolean) {
    if (!this.gl) return;
    if (on) { this.lightsOff = false; this.replayIntro(); }
    else { this.lightsOff = true; this.offAt = performance.now(); }
    if (!this.motion) this.draw();
  }

  /** Test hook: replay the lights switching on. */
  replayIntro() {
    if (!this.gl) return;
    this.intro = true;
    this.start = performance.now();
  }

  dispose() {
    cancelAnimationFrame(this.raf);
  }
}
