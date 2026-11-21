/**
 * The canal scene: a fixed view rendered in Blender (Cycles) shown exactly as
 * rendered, with a thin WebGL layer for the life a still image can't have:
 *   - the canal's reflections ripple (only where water shows)
 *   - smoke drifts up out of every chimney
 *   - candles flicker
 *   - on the first visit the lights are off, then come on all at once, with a
 *     couple of lamps catching late
 * Hovering a building lifts it slightly; clicking reports which one.
 *
 * Assets (tools/blender/concepts/canal_final.py → tools/blender/package_canal.mjs):
 *   canal(.avif/.webp), canal-1400(...)   the render, lights on
 *   canal-off(...), canal-off-1400(...)    the same render with every light off
 *   water.png  ids.png  scene.json         masks, groups, lights, smoke sources
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
uniform sampler2D uImg, uOff, uWater, uIds;
uniform vec2 uImgPx;
uniform float uTime, uHover, uMotion, uAspect, uOn;
uniform vec4 uLights[${MAX_LIGHTS}];
uniform int uCount;
uniform vec4 uSmoke[${MAX_SMOKE}];
uniform int uSmokeCount;
uniform vec4 uLate[4];        // x, y, radius, how lit (0..1) for lamps that catch late

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
  vec2 off = vec2(ripple * 4.0, (n1 - 0.5) * 2.0) * uImgPx * w * uMotion;
  vec4 on = texture2D(uImg, uv + off);
  vec4 dark = texture2D(uOff, uv + off);
  on.rgb *= 1.0 + 0.04 * w * (n2 - 0.5) * uMotion;

  // Lights switching on: everything at once, except a few lamps that stutter.
  float k = uOn;
  for (int i = 0; i < 4; i++) {
    vec2 d = (uv - uLate[i].xy) * vec2(uAspect, 1.0);
    float g = exp(-dot(d, d) / (uLate[i].z * uLate[i].z));
    k = mix(k, k * uLate[i].w, g);
  }
  vec4 c = mix(dark, on, k);

  // Candle flicker around each small flame.
  float f = 0.0;
  for (int i = 0; i < ${MAX_LIGHTS}; i++) {
    if (i >= uCount) break;
    vec4 L = uLights[i];
    vec2 d = (uv - L.xy) * vec2(uAspect, 1.0);
    float r2 = dot(d, d);
    float n = sin(t * 7.1 + L.z) * 0.5 + sin(t * 12.7 + L.z * 2.3) * 0.3 + sin(t * 23.0 + L.z * 4.1) * 0.2;
    f += L.w * n * exp(-r2 / 0.00022);
  }
  c.rgb *= 1.0 + f * uMotion * k;

  // Chimney smoke: soft puffs rising, swelling and fading, drifting with the breeze.
  float a = 0.0;
  for (int i = 0; i < ${MAX_SMOKE}; i++) {
    if (i >= uSmokeCount) break;
    vec4 S = uSmoke[i];
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
  private late: { x: number; y: number; r: number; seed: number }[] = [];
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
    const [data, img, off, water, ids] = await Promise.all([
      fetch(BASE + 'scene.json').then((r) => r.json() as Promise<SceneJson>),
      loadRender('canal' + sfx),
      loadRender('canal-off' + sfx).catch(() => null),
      loadImage(BASE + 'water.png'),
      loadImage(BASE + 'ids.png'),
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
    if (this.gl && this.setupGL(img, off ?? img, water, ids)) {
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

  private setupGL(img: HTMLImageElement, off: HTMLImageElement, water: HTMLImageElement, ids: HTMLImageElement) {
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
    for (const n of ['uTime', 'uHover', 'uMotion', 'uOn', 'uLate']) this.u[n] = gl.getUniformLocation(p, n);
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
    gl.uniform2f(gl.getUniformLocation(p, 'uImgPx'), 1 / img.naturalWidth, 1 / img.naturalHeight);
    gl.uniform1f(gl.getUniformLocation(p, 'uAspect'), img.naturalWidth / img.naturalHeight);
    const L = this.data.lights.slice(0, MAX_LIGHTS);
    const arr = new Float32Array(MAX_LIGHTS * 4);
    L.forEach((l, i) => {
      const strength = l.k === 'candle' ? 0.06 : l.k === 'pl' ? 0.035 : 0.045;
      arr.set([l.x, l.y, (i * 2.399) % 6.283, strength], i * 4);
    });
    gl.uniform4fv(gl.getUniformLocation(p, 'uLights'), arr);
    gl.uniform1i(gl.getUniformLocation(p, 'uCount'), L.length);
    const S = (this.data.smoke ?? []).slice(0, MAX_SMOKE);
    const sarr = new Float32Array(MAX_SMOKE * 4);
    S.forEach((s, i) => sarr.set([s.x, s.y, Math.max(s.r, 0.004), (i * 0.37) % 1], i * 4));
    gl.uniform4fv(gl.getUniformLocation(p, 'uSmoke'), sarr);
    gl.uniform1i(gl.getUniformLocation(p, 'uSmokeCount'), S.length);
    // Pick a few street lamps / lanterns to catch late during the switch-on.
    const lamps = this.data.lights.filter((l) => l.k === 'candle' || l.k === 'gas' || l.k === 'wl');
    for (let i = 0; i < 4; i++) {
      const l = lamps[Math.floor(((i * 0.618 + 0.2) % 1) * lamps.length)] ?? { x: -1, y: -1 };
      this.late.push({ x: l.x, y: l.y, r: 0.05, seed: i * 1.7 });
    }
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
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = Math.round(Math.min(cw * dpr, this.img.naturalWidth));
      this.canvas.height = Math.round(Math.min(ch * dpr, this.img.naturalHeight));
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

  /** 0 = dark, 1 = lit. Dark for a beat, a flicker, then on; a few lamps stutter on after. */
  private switchOn(s: number): { on: number; late: number[] } {
    if (!this.intro) return { on: 1, late: [1, 1, 1, 1] };
    const step = (a: number, b: number) => Math.min(1, Math.max(0, (s - a) / (b - a)));
    let on = step(1.1, 1.25);
    if (s > 1.32 && s < 1.42) on = 0.35;           // the whole street blinks once
    const late = this.late.map((l, i) => {
      const t0 = 1.5 + i * 0.35;
      if (s < 1.1) return 1;
      if (s > t0 + 1.2) return 1;
      const flick = Math.sin((s - 1.1) * (17 + i * 5) + l.seed) > 0.2 ? 1 : 0;
      return s < t0 ? 0.08 + 0.4 * flick : flick * (0.6 + 0.4 * step(t0, t0 + 1.2));
    });
    if (s > 4.5) this.intro = false;
    return { on, late };
  }

  private draw() {
    const gl = this.gl, p = this.prog;
    if (!gl || !p) return;
    const s = (performance.now() - this.start) / 1000;
    const sw = this.switchOn(s);
    if (this.lightsOff) {
      const k = this.motion ? Math.max(0, 1 - (performance.now() - this.offAt) / 350) : 0;
      sw.on = k; sw.late = [k, k, k, k];
    }
    gl.uniform1f(this.u.uTime, s);
    gl.uniform1f(this.u.uMotion, this.motion);
    gl.uniform1f(this.u.uOn, sw.on);
    const late = new Float32Array(16);
    this.late.forEach((l, i) => late.set([l.x, l.y, l.r, sw.late[i]], i * 4));
    gl.uniform4fv(this.u.uLate, late);
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
