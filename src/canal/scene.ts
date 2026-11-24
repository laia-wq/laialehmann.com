/**
 * The canal scene: a fixed view rendered in Blender (Cycles) shown exactly as
 * rendered, with a thin WebGL layer for the life a still image can't have:
 *   - the canal's reflections ripple (only where water shows)
 *   - smoke drifts up out of every chimney
 *   - candles flicker
 *   - on the first visit the lights are off, then come on one by one, in an
 *     order baked per window and lamp (delay.png), borders cross-fading
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
  owl?: { box: [number, number, number, number]; states: string[] };
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
uniform sampler2D uImg, uOff, uWater, uIds, uDelay, uOwl, uLightIdx, uLightW;
uniform vec3 uLightRow;       // idx map: rows used by the map, then the light table's row (v), and 1/width
uniform vec4 uOwlBox;         // where the owl's crop sits (uv)
uniform vec3 uOwlAB;          // frame A, frame B, blend A→B (frame 0 = eyes shut)
uniform float uOwlN;          // frames in the owl strip
uniform vec2 uImgPx;
uniform vec4 uView;          // screen uv -> image uv (the window zoom), identity otherwise
uniform float uTime, uHover, uMotion, uAspect, uOn, uIntroT, uLevel;
uniform vec4 uSmoke[${MAX_SMOKE}];
uniform vec4 uSmokeK[${MAX_SMOKE}];
uniform int uSmokeCount;
uniform vec4 uSmokeBox;       // min x, min y, max x, max y of all the plumes

float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

void main() {
  vec2 uv = vUv * uView.xy + uView.zw;
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) { gl_FragColor = vec4(0.043, 0.043, 0.063, 1.0); return; }
  float t = uTime * uMotion;
  float w = texture2D(uWater, uv).r;

  // Water: reflections ripple sideways (a few pixels) and bob a little,
  // with slow drifting noise so it never looks like a repeating pattern.
  vec2 q = vec2(uv.x * uAspect, uv.y) * 90.0;
  float n1 = vnoise(q * vec2(0.6, 2.2) + vec2(t * 0.35, t * 0.9));
  float n2 = vnoise(q * vec2(1.3, 4.5) - vec2(t * 0.5, t * 1.4));
  float ripple = sin(uv.y * 1300.0 + t * 1.8 + n1 * 5.0) * 0.6 + (n2 - 0.5) * 1.2;
  vec2 off = vec2(ripple * 2.6, (n1 - 0.5) * 1.4) * uImgPx * uMotion;
  // only open water moves, and only ever borrows from open water: nothing
  // standing in it (walls, lamps, boats, lily pads) gets smeared
  off *= smoothstep(0.85, 1.0, w) * smoothstep(0.85, 1.0, texture2D(uWater, uv + off).r);
  vec4 on = texture2D(uImg, uv + off);
  vec4 dark = texture2D(uOff, uv + off);
  on.rgb *= 1.0 + 0.04 * w * (n2 - 0.5) * uMotion;

  // Lights switching on: each window, lamp and sign fades up as a whole at
  // its own moment (r), and the light it throws follows it (g = how near a
  // light). Away from any light everything shares one moment, so no edge
  // ever sweeps across the street.
  // Where two lights' areas meet, the neighbour's moment is mixed in
  // (water.png g = its moment, b = how much), so borders cross-fade.
  vec4 D = texture2D(uDelay, uv);
  vec3 X = texture2D(uWater, uv).rgb;
  float near = smoothstep(0.0, 0.5, D.g);
  float k = mix(smoothstep(0.0, 0.55, uIntroT - 1.6 * mix(0.45, D.r, near)),
                smoothstep(0.0, 0.55, uIntroT - 1.6 * mix(0.45, X.g, near)), X.b);
  k *= uOn;
  vec4 c = mix(dark, on, k);

  // The owl: its crops are the render itself with the eyes in other states;
  // add only what differs from eyes-shut (frame 0), feathered at the edges.
  if (uOwlAB.x > 0.0 || uOwlAB.y > 0.0) {
    vec2 l = (uv - uOwlBox.xy) / (uOwlBox.zw - uOwlBox.xy);
    if (l.x > 0.0 && l.y > 0.0 && l.x < 1.0 && l.y < 1.0) {
      float fw = 1.0 / uOwlN;
      vec3 shut = texture2D(uOwl, vec2(l.x * fw, l.y)).rgb;
      vec3 st = mix(texture2D(uOwl, vec2((uOwlAB.x + l.x) * fw, l.y)).rgb, texture2D(uOwl, vec2((uOwlAB.y + l.x) * fw, l.y)).rgb, uOwlAB.z);
      float feather = smoothstep(0.0, 0.12, l.x) * smoothstep(0.0, 0.12, 1.0 - l.x) * smoothstep(0.0, 0.12, l.y) * smoothstep(0.0, 0.12, 1.0 - l.y);
      c.rgb += (st - shut) * feather * k;
    }
  }

  // Candle flicker around each small flame, and a soft halo round the street
  // lamps. Which flame a pixel belongs to, and how close it is, were worked
  // out once at load (uLightIdx / uLightW), so this is one lookup, not a loop.
  float f = 0.0, halo = 0.0;
  float li = texture2D(uLightIdx, vec2(uv.x, uv.y * uLightRow.x)).r * 255.0;
  if (li > 0.5) {
    vec4 T = texture2D(uLightIdx, vec2((li - 0.5) * uLightRow.z, uLightRow.y));
    float ph = T.r * 6.2832;
    float n = sin(t * 7.1 + ph) * 0.5 + sin(t * 12.7 + ph * 2.3) * 0.3 + sin(t * 23.0 + ph * 4.1) * 0.2;
    vec2 Wt = texture2D(uLightW, uv).rg;
    f = T.g * 0.1 * n * uMotion * Wt.r;
    halo = T.b * 0.1 * (1.0 + 0.25 * n * uMotion) * Wt.g;
  }
  c.rgb *= 1.0 + f * k;
  c.rgb += vec3(1.0, 0.66, 0.36) * halo * k;

  // Windows with a project behind them glow a touch rosier than the rest,
  // only where the glass is lit, so they read as different without shouting.
  float zm = texture2D(uLightW, uv).b;
  if (zm > 0.0) {
    float lum = dot(c.rgb, vec3(0.3, 0.59, 0.11));
    float wz = zm * smoothstep(0.32, 0.7, lum) * k;
    c.rgb = mix(c.rgb, c.rgb * vec3(1.02, 0.9, 1.0) + vec3(0.025, 0.0, 0.035) * lum, wz * 0.7);
  }

  // Chimney smoke. Each plume is noise carried up the column, so it billows
  // and tears instead of repeating; the breeze bends every plume the same
  // way, and each chimney has its own character (uSmokeK): how fast it rises,
  // how thick, how far it carries before thinning out, and whether it comes
  // steady or in puffs. Only pixels inside a plume's box pay for the noise.
  float a = 0.0;
  vec3 smokeCol = vec3(0.0);
  if (uv.x > uSmokeBox.x && uv.y > uSmokeBox.y && uv.x < uSmokeBox.z && uv.y < uSmokeBox.w)
  for (int i = 0; i < ${MAX_SMOKE}; i++) {
    if (i >= uSmokeCount) break;
    vec4 S = uSmoke[i];
    vec4 K = uSmokeK[i];             // rise speed, density, reach (in widths), puffiness
    vec2 rel = (uv - S.xy) / S.z;    // in chimney widths; y down
    rel.y *= 1.0 / uAspect;
    float h = -rel.y;                // height above the pot
    if (h < -0.6 || h > K.z * 1.35) continue;
    float hh = max(h, 0.0);
    // the breeze: bends the column over more the higher it gets, gusting
    float gust = 0.75 + 0.25 * sin(t * 0.21 + S.w * 6.0) + 0.12 * sin(t * 0.53 + S.w * 3.0);
    float cx = 0.055 * pow(hh, 1.55) * gust + 0.25 * sin(hh * 0.35 - t * 0.6 * K.x + S.w * 9.0) * min(1.0, hh * 0.2);
    float wdt = 0.75 + 0.2 * hh;
    float x = (rel.x - cx) / wdt;
    if (abs(x) > 2.6) continue;
    // noise rising with the smoke (advected up), warped so it curls
    vec2 q = vec2(x * 1.1, hh * 0.42 - t * 0.55 * K.x) + S.w * 17.0;
    float w1 = vnoise(q * 1.3 + vec2(0.0, t * 0.07));
    q += vec2(w1 - 0.5, 0.0) * 1.2;
    float n = 0.55 * vnoise(q * 1.7) + 0.3 * vnoise(q * 3.6 + 4.1) + 0.15 * vnoise(q * 7.3 + 9.2);
    float body = exp(-x * x * 1.35);
    // puffs: blobs leaving the pot at intervals (K.w = 0 steady, 1 all puffs)
    float puff = 0.5 + 0.5 * sin((hh * 0.55 - t * 0.9 * K.x) * 3.0 + S.w * 11.0);
    puff = mix(1.0, smoothstep(0.15, 0.85, puff), K.w);
    float rise = smoothstep(-0.4, 0.6, h) * exp(-hh / K.z * 1.6) * smoothstep(K.z * 1.35, K.z * 0.6, hh);
    float d = body * rise * puff * smoothstep(0.26, 0.8, n + 0.22 * body) * K.y;
    a += d;
    // fresh smoke near the pot catches the warm light from inside
    smokeCol += d * mix(vec3(0.62, 0.55, 0.5), vec3(0.47, 0.47, 0.52), smoothstep(0.0, 4.0, hh));
  }
  vec3 sc = a > 0.0 ? smokeCol / a : vec3(0.5);
  c.rgb = mix(c.rgb, sc * (0.5 + 0.5 * uLevel), clamp(a, 0.0, 0.72));

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
const V = `?v=${__ASSET_V__}`;
const loadRender = (name: string) => loadImage(BASE + name + '.avif' + V).catch(() => loadImage(BASE + name + '.webp' + V));

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
    const [data, img, off, water, ids, delay, owl] = await Promise.all([
      fetch(BASE + 'scene.json' + V).then((r) => r.json() as Promise<SceneJson>),
      loadRender('canal' + sfx),
      loadRender('canal-off' + sfx).catch(() => null),
      loadImage(BASE + 'water.png' + V),
      loadImage(BASE + 'ids.png' + V),
      loadImage(BASE + 'delay.png' + V).catch(() => null),
      loadImage(BASE + 'owl.png' + V).catch(() => null),
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

    this.gl = this.canvas.getContext('webgl', { antialias: false, premultipliedAlpha: false, alpha: false, depth: false, stencil: false, powerPreference: 'high-performance' });
    if (this.gl && this.setupGL(img, off ?? img, water, ids, delay, owl)) {
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

  private setupGL(img: HTMLImageElement, off: HTMLImageElement, water: HTMLImageElement, ids: HTMLImageElement, delay: HTMLImageElement | null, owl: HTMLImageElement | null) {
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
    for (const n of ['uTime', 'uHover', 'uMotion', 'uOn', 'uIntroT', 'uLevel', 'uOwlAB', 'uView']) this.u[n] = gl.getUniformLocation(p, n);
    gl.uniform4f(this.u.uView, 1, 1, 0, 0);
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
    const blank = document.createElement('canvas'); blank.width = blank.height = 1;
    if (!delay) tex(4, blank as unknown as HTMLImageElement, 'uDelay');
    tex(5, owl ?? (blank as unknown as HTMLImageElement), 'uOwl');
    if (owl && this.data.owl) {
      const b = this.data.owl.box;
      gl.uniform4f(gl.getUniformLocation(p, 'uOwlBox'), b[0], b[1], b[2], b[3]);
      gl.uniform1f(gl.getUniformLocation(p, 'uOwlN'), this.data.owl.states.length);
      this.owl = new OwlEyes(this.data.owl.states);
    }
    gl.uniform3f(this.u.uOwlAB, 0, 0, 0);
    gl.uniform2f(gl.getUniformLocation(p, 'uImgPx'), 1 / img.naturalWidth, 1 / img.naturalHeight);
    gl.uniform1f(gl.getUniformLocation(p, 'uAspect'), img.naturalWidth / img.naturalHeight);
    this.buildLightMaps(gl, p, img.naturalWidth / img.naturalHeight);
    const S = (this.data.smoke ?? []).slice(0, MAX_SMOKE);
    const sarr = new Float32Array(MAX_SMOKE * 4), karr = new Float32Array(MAX_SMOKE * 4);
    // each chimney's character: [rise speed, density, reach in widths, puffiness];
    // scene.json can name it (s.k), otherwise it's picked from a small set
    const KINDS: Record<string, [number, number, number, number]> = {
      hearth: [0.8, 0.85, 22, 0.15],     // a steady coal fire: a full, lazy column
      oven: [0.6, 1.05, 26, 0.05],       // the bakery: thick, rolling, carried far
      wisp: [1.4, 0.45, 15, 0.1],        // a thin draught, fast and soon gone
      stove: [1.1, 0.7, 12, 0.75],       // a stove pipe: short puffs
      banked: [0.5, 0.4, 18, 0.35],      // a fire banked low: faint, slow
    };
    // in the order the street's chimneys are built: tall house ×2, cream shop ×2, corner house, bakery, houseboat
    const order = ['banked', 'hearth', 'wisp', 'banked', 'hearth', 'oven', 'stove'];
    S.forEach((s, i) => {
      // smoke.json marks where the old baked puffs began, a little above the pot
      const k = (s as { k?: string }).k ?? order[i % order.length];
      const drop = k === 'stove' ? 0.8 : 3.2;
      sarr.set([s.x, s.y + s.r * drop * (img.naturalWidth / img.naturalHeight), Math.max(s.r, 0.004), (i * 0.37) % 1], i * 4);
      karr.set(KINDS[k] ?? KINDS.hearth, i * 4);
    });
    gl.uniform4fv(gl.getUniformLocation(p, 'uSmoke'), sarr);
    gl.uniform4fv(gl.getUniformLocation(p, 'uSmokeK'), karr);
    gl.uniform1i(gl.getUniformLocation(p, 'uSmokeCount'), S.length);
    const reach = (i: number) => karr[i * 4 + 2] * 1.4;
    const box = S.length
      ? [Math.min(...S.map((s, i) => s.x - s.r * (2 + 0.25 * reach(i)))), Math.min(...S.map((s, i) => s.y - s.r * reach(i) * (this.img.naturalWidth / this.img.naturalHeight))),
         Math.max(...S.map((s, i) => s.x + s.r * (4 + 0.075 * Math.pow(reach(i), 1.55) + 0.45 * reach(i)))), Math.max(...S.map((s) => s.y + s.r * 6))]
      : [2, 2, -1, -1];
    gl.uniform4f(gl.getUniformLocation(p, 'uSmokeBox'), box[0], box[1], box[2], box[3]);
    return true;
  }

  /** Work out once, for every pixel, which flame it belongs to (the nearest,
   *  if any is close) and how close: the shader then needs one lookup per
   *  pixel instead of looping over every light each frame. */
  private buildLightMaps(gl: WebGLRenderingContext, p: WebGLProgram, aspect: number) {
    const L = this.data.lights.slice(0, MAX_LIGHTS);
    const W = 700, H = Math.round(700 / aspect);
    // the index map has one extra row at the bottom: the lights' own table
    const idx = new Uint8Array(W * (H + 1) * 4), wt = new Uint8Array(W * H * 4), tab = idx.subarray(W * H * 4);
    L.forEach((l, i) => {
      const flick = l.k === 'candle' ? 0.06 : l.k === 'pl' ? 0.035 : l.k === 'gp' ? 0.0 : 0.045;   // globes are steady
      const halo = l.k === 'candle' && l.e >= 5 ? Math.min(1, l.e / 32) * 0.06 : 0;
      tab.set([Math.round(((i * 0.618) % 1) * 255), Math.round((flick / 0.1) * 255), Math.round((halo / 0.1) * 255), 255], i * 4);
    });
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const u = (x + 0.5) / W, v = (y + 0.5) / H;
      let best = -1, br2 = 0.006;
      for (let i = 0; i < L.length; i++) {
        const dx = (u - L[i].x) * aspect, dy = v - L[i].y, r2 = dx * dx + dy * dy;
        if (r2 < br2) { br2 = r2; best = i; }
      }
      const o = (y * W + x) * 4;
      if (best >= 0) {
        idx[o] = best + 1;
        wt[o] = Math.round(255 * Math.exp(-br2 / 0.00022));
        wt[o + 1] = Math.round(255 * Math.exp(-br2 / 0.0009));
      }
      idx[o + 3] = wt[o + 3] = 255;
    }
    const up = (unit: number, data: Uint8Array, w: number, h: number, name: string, nearest: boolean) => {
      const t = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);
      const f = nearest ? gl.NEAREST : gl.LINEAR;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.uniform1i(gl.getUniformLocation(p, name), unit);
    };
    up(6, idx, W, H + 1, 'uLightIdx', true);
    up(7, wt, W, H, 'uLightW', false);
    this.lw = { data: wt, w: W, h: H };
    gl.uniform3f(gl.getUniformLocation(p, 'uLightRow'), H / (H + 1), (H + 0.5) / (H + 1), 1 / W);
  }

  private lw: { data: Uint8Array; w: number; h: number } | null = null;
  /** Mark the windows that open a project (quads in image uv): they get a
   *  slightly different hue. Drawn into the light-weight map's spare channel. */
  setHighlights(quads: [number, number][][]) {
    const gl = this.gl, lw = this.lw;
    if (!gl || !lw) return;
    const c = document.createElement('canvas'); c.width = lw.w; c.height = lw.h;
    const x = c.getContext('2d', { willReadFrequently: true })!;
    x.fillStyle = '#fff';
    x.filter = 'blur(0.6px)';
    for (const q of quads) {
      x.beginPath();
      q.forEach(([u, v], i) => (i ? x.lineTo(u * lw.w, v * lw.h) : x.moveTo(u * lw.w, v * lw.h)));
      x.closePath(); x.fill();
    }
    const m = x.getImageData(0, 0, lw.w, lw.h).data;
    for (let i = 0; i < lw.w * lw.h; i++) lw.data[i * 4 + 2] = m[i * 4 + 3];
    gl.activeTexture(gl.TEXTURE7);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, lw.w, lw.h, gl.RGBA, gl.UNSIGNED_BYTE, lw.data);
    if (!this.motion) this.draw();
  }

  private resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h || !this.img) return;
    const ar = this.img.naturalWidth / this.img.naturalHeight;
    let cw = w, ch = w / ar;
    if (ch > h) { ch = h; cw = h * ar; }
    this.fit = { left: (w - cw) / 2, top: (h - ch) / 2, width: cw, height: ch, w, h };
    if (this.view) return this.applyView();
    const el = (this.fallback ?? this.canvas) as HTMLElement;
    el.style.width = `${cw}px`;
    el.style.height = `${ch}px`;
    this.events.onLayout?.({ left: (w - cw) / 2, top: (h - ch) / 2, width: cw, height: ch });
    if (!this.fallback) {
      // sharp on retina, but never more than ~2.1M pixels of shader work a frame
      let dpr = Math.min(window.devicePixelRatio || 1, 1.75, this.img.naturalWidth / cw);
      dpr = Math.min(dpr, Math.sqrt(2.1e6 / (cw * ch)));
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

  /** Where a building's middle is on screen (client px), for zooming into it. */
  groupCenter(g: string): { x: number; y: number } | null {
    const gi = this.data.groups.indexOf(g) + 1;
    if (!gi) return null;
    const { width: W, height: H, data } = this.ids;
    let sx = 0, sy = 0, n = 0;
    for (let y = 0; y < H; y += 4) for (let x = 0; x < W; x += 4) {
      if (Math.round(data[(y * W + x) * 4] / 40) === gi) { sx += x; sy += y; n++; }
    }
    if (!n) return null;
    const r = ((this.fallback ?? this.canvas) as HTMLElement).getBoundingClientRect();
    return { x: r.left + (sx / n / W) * r.width, y: r.top + (sy / n / H) * r.height };
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
    if (this.intro && s > 4.2) this.intro = false;
    return this.intro;
  }

  private draw() {
    const gl = this.gl, p = this.prog;
    if (!gl || !p) return;
    const now = performance.now();
    const s = (now - this.start) / 1000;            // since the lights started coming on
    const intro = this.introRunning(s);
    const fade = this.motion ? Math.max(0, 1 - (now - this.offAt) / 350) : 0;
    // the street's overall brightness, for the smoke: eases up with the lights
    const up = intro ? Math.min(1, Math.max(0, (s - this.dark - 0.3) / 2.2)) : 1;
    const level = (up * up * (3 - 2 * up)) * (this.lightsOff ? fade : 1);
    gl.uniform1f(this.u.uTime, (now - this.born) / 1000);   // never resets: smoke and water keep flowing
    gl.uniform1f(this.u.uLevel, level);
    gl.uniform1f(this.u.uMotion, this.motion);
    gl.uniform1f(this.u.uOn, this.lightsOff ? fade : 1);
    gl.uniform1f(this.u.uIntroT, intro ? s - this.dark : 100);
    // the owl only stirs once the street is lit and settled
    const awake = this.motion === 1 && !intro && !this.lightsOff;
    const ow = this.owl ? this.owl.at(now / 1000, awake) : [0, 0, 0];
    gl.uniform3f(this.u.uOwlAB, ow[0], ow[1], ow[2]);
    const idx = this.hover ? this.data.groups.indexOf(this.hover) + 1 : 0;
    gl.uniform1f(this.u.uHover, idx ? (idx * 40) / 255 : 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    if (document.hidden || (!this.motion && !this.intro && !this.lightsOff)) return;
    this.draw();
  };

  private owl: OwlEyes | null = null;
  private lightsOff = false;
  private born = performance.now();
  private dark = 0.9;           // seconds of darkness before the first light
  private offAt = 0;
  get lightsOn() { return !this.lightsOff; }
  /** The dock's lights switch: off fades the street dark, on replays the switch-on. */
  setLights(on: boolean) {
    if (!this.gl) return;
    if (on) { this.lightsOff = false; this.switchOnNow(); }
    else { this.lightsOff = true; this.offAt = performance.now(); }
    if (!this.motion) this.draw();
  }

  /** Test hook: replay the lights switching on. */
  replayIntro() {
    if (!this.gl) return;
    this.intro = true;
    this.start = performance.now();
  }
  /** The switch: no long dark pause, the lights start coming on straight away. */
  private switchOnNow() {
    this.replayIntro();
    this.dark = 0.15;
  }

  private fit: { left: number; top: number; width: number; height: number; w: number; h: number } | null = null;
  private view: { s: number; tx: number; ty: number } | null = null;
  /** Zoom the street inside the shader (for the window zoom), so it stays as
   *  sharp as the full-size render allows instead of stretching the canvas.
   *  The view is like a CSS transform on the stage: a stage point p shows at
   *  s * p + (tx, ty). null puts the street back as it was. Returns false if
   *  there's no WebGL (the caller then uses a CSS transform). */
  setView(v: { s: number; tx: number; ty: number } | null) {
    if (!this.gl || this.fallback) return false;
    const was = this.view;
    this.view = v;
    if (v) this.applyView();
    else if (was) { this.gl.uniform4f(this.u.uView, 1, 1, 0, 0); this.resize(); }
    return true;
  }
  private applyView() {
    const f = this.fit, v = this.view, gl = this.gl;
    if (!f || !v || !gl) return;
    // fill the whole stage while zoomed: margins become more street
    if (this.canvas.style.width !== `${f.w}px`) {
      this.canvas.style.width = `${f.w}px`; this.canvas.style.height = `${f.h}px`;
      let dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      dpr = Math.min(dpr, Math.sqrt(2.1e6 / (f.w * f.h)));
      this.canvas.width = Math.round(f.w * dpr); this.canvas.height = Math.round(f.h * dpr);
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }
    // screen px c -> stage px p = (c - t) / s -> image uv = (p - fit.left/top) / fit size
    gl.uniform4f(this.u.uView, f.w / (v.s * f.width), f.h / (v.s * f.height),
      (-v.tx / v.s - f.left) / f.width, (-v.ty / v.s - f.top) / f.height);
    this.draw();
  }

  dispose() {
    cancelAnimationFrame(this.raf);
  }
}

/** The owl on the corner house: eyes shut most of the time; now and then it
 *  wakes, blinks, glances about and dozes off again. Frames: 0 shut, then
 *  the other states in scene.json order (open, left, right, half). */
class OwlEyes {
  private seq: [number, number][] = [];   // [frame, seconds]
  private from = 0; private to = 0; private t0 = 0; private next = 0;
  private f: Record<string, number> = {};
  constructor(states: string[]) {
    states.forEach((s, i) => (this.f[s] = i));
  }
  private plan(t: number) {
    const { open, left, right, half, closed } = this.f;
    const r = Math.random;
    const blink: [number, number][] = [[half, 0.05], [closed, 0.07], [half, 0.05], [open, 0.5 + r() * 0.6]];
    const options: [number, number][][] = [
      [[half, 0.18], [open, 1.2 + r()], ...blink, [left, 0.8 + r() * 0.5], [open, 0.35], [right, 0.7 + r() * 0.5], [open, 0.5], [half, 0.3]],
      [[half, 0.2], [open, 0.8], [right, 1.1 + r() * 0.6], [open, 0.4], ...blink, [half, 0.35]],
      [[half, 1.4 + r()], [open, 0.25], [half, 0.5]],                    // just peeks
      [[half, 0.15], [open, 0.6], [left, 0.9], [right, 0.9], [left, 0.5], [open, 0.4], ...blink, [half, 0.3]],
    ];
    this.seq = [...options[Math.floor(r() * options.length)], [closed, 0]];
    this.next = t;
  }
  /** [frame A, frame B, blend] for time t (seconds). */
  at(t: number, awake: boolean): [number, number, number] {
    const closed = this.f.closed ?? 0;
    if (!awake) { this.seq = []; this.from = this.to = closed; this.next = t + 4 + Math.random() * 6; return [closed, closed, 0]; }
    if (!this.seq.length && t >= this.next && this.to === closed) this.plan(t);
    if (this.seq.length && t >= this.next) {
      const [fr, hold] = this.seq.shift()!;
      this.from = this.to; this.to = fr; this.t0 = t;
      this.next = t + hold;
      if (!this.seq.length) this.next = t + 7 + Math.random() * 12;   // asleep again for a while
    }
    const k = Math.min(1, (t - this.t0) / 0.06);
    return [this.from, this.to, k];
  }
}
