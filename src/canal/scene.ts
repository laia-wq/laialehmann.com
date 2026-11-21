/**
 * The canal scene: a fixed view rendered in Blender (Cycles) shown exactly as
 * rendered, with a thin WebGL layer on top for life that a still image can't
 * have: a faint shimmer on the water and candles that flicker. Hovering a
 * building lifts it slightly; clicking it reports which one (rooms come later).
 *
 * Assets (tools/blender/concepts/canal_final.py → tools/blender/package_canal.mjs):
 *   canal.webp / canal-1400.webp   the render (2800×2100 / 1400×1050)
 *   water.png                       where the canal is visible (grey)
 *   ids.png                         which building each pixel belongs to
 *   scene.json                      groups and every flickering light (0..1 coords)
 */

export interface CanalEvents {
  onHover(group: string | null): void;
  onSelect(group: string): void;
}

interface SceneJson {
  size: [number, number];
  groups: string[];
  lights: { x: number; y: number; k: string; c: [number, number, number]; e: number }[];
  bg?: [number, number, number][];
}

const BASE = `${import.meta.env.BASE_URL}canal/`;
const MAX_LIGHTS = 96;

const VERT = `
attribute vec2 aPos;
varying vec2 vUv;
void main() { vUv = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5); gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FRAG = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uImg, uWater, uIds;
uniform vec2 uImgPx;          // 1 / image size in pixels
uniform float uTime, uHover, uMotion, uAspect;
uniform vec4 uLights[${MAX_LIGHTS}];   // x, y, phase, strength
uniform int uCount;
void main() {
  vec2 uv = vUv;
  float w = texture2D(uWater, uv).r * uMotion;
  // Water: a slow sideways wobble of a pixel or so, only where the canal shows.
  float wave = sin(uv.y * 1400.0 + uTime * 1.3 + sin(uv.x * 40.0 + uTime * 0.6) * 2.5)
             + 0.6 * sin(uv.y * 620.0 - uTime * 0.9 + uv.x * 25.0);
  vec2 off = vec2(wave * 0.7, 0.0) * uImgPx * 1.6 * w;
  vec4 c = texture2D(uImg, uv + off);
  c.rgb *= 1.0 + 0.025 * w * sin(uv.x * 300.0 + uTime * 0.8 + uv.y * 900.0);
  // Candle flicker: a soft, tiny brightness wobble around each flame.
  float f = 0.0;
  for (int i = 0; i < ${MAX_LIGHTS}; i++) {
    if (i >= uCount) break;
    vec4 L = uLights[i];
    vec2 d = (uv - L.xy) * vec2(uAspect, 1.0);
    float r2 = dot(d, d);
    float n = sin(uTime * 7.1 + L.z) * 0.5 + sin(uTime * 12.7 + L.z * 2.3) * 0.3 + sin(uTime * 23.0 + L.z * 4.1) * 0.2;
    f += L.w * n * exp(-r2 / 0.00022);
  }
  c.rgb *= 1.0 + f * uMotion;
  // Hover: lift the building under the pointer a little.
  float id = texture2D(uIds, uv).r;
  if (uHover > 0.0 && abs(id - uHover) < 0.03) c.rgb = c.rgb * 1.1 + vec3(0.008, 0.006, 0.004);
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

export class CanalScene {
  private container: HTMLElement;
  private events: CanalEvents;
  private canvas = document.createElement('canvas');
  private gl: WebGLRenderingContext | null = null;
  private prog: WebGLProgram | null = null;
  private img!: HTMLImageElement;
  private ids!: ImageData;
  private data!: SceneJson;
  private hover: string | null = null;
  private motion = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1;
  private start = performance.now();
  private raf = 0;
  private fallback: HTMLImageElement | null = null;
  ready: Promise<void>;

  constructor(container: HTMLElement, events: CanalEvents) {
    this.container = container;
    this.events = events;
    this.canvas.className = 'canal-canvas';
    this.canvas.setAttribute('role', 'img');
    this.canvas.setAttribute('aria-label', 'Four old buildings standing in dark canal water at night, joined by rickety bridges, with lit windows, lanterns and boats.');
    this.ready = this.init();
  }

  private async init() {
    const big = Math.min(window.devicePixelRatio || 1, 2) * Math.max(innerWidth, innerHeight * 4 / 3) > 1500;
    const [data, img, water, ids] = await Promise.all([
      fetch(BASE + 'scene.json').then((r) => r.json() as Promise<SceneJson>),
      loadImage(BASE + (big ? 'canal.avif' : 'canal-1400.avif')).catch(() => loadImage(BASE + (big ? 'canal.webp' : 'canal-1400.webp'))),
      loadImage(BASE + 'water.png'),
      loadImage(BASE + 'ids.png'),
    ]);
    this.data = data;
    this.img = img;
    // Ids for hit-testing on the CPU.
    const ic = document.createElement('canvas');
    ic.width = ids.naturalWidth; ic.height = ids.naturalHeight;
    const ictx = ic.getContext('2d', { willReadFrequently: true })!;
    ictx.drawImage(ids, 0, 0);
    this.ids = ictx.getImageData(0, 0, ic.width, ic.height);
    // The page behind the letterbox continues the render's own edge colours,
    // and the render's edges fade into it, so there is no visible rectangle.
    const [t, m, b] = data.bg ?? [[12, 13, 20], [4, 5, 8], [6, 7, 11]];
    this.container.style.background = `linear-gradient(to bottom, rgb(${t}), rgb(${m}) 50%, rgb(${b}))`;
    document.body.style.background = `rgb(${m})`;

    this.gl = this.canvas.getContext('webgl', { antialias: false, premultipliedAlpha: false, alpha: false });
    if (this.gl && this.setupGL(img, water, ids)) {
      this.container.appendChild(this.canvas);
    } else {
      this.fallback = img;
      img.className = 'canal-canvas';
      img.alt = this.canvas.getAttribute('aria-label')!;
      this.container.appendChild(img);
    }
    this.bind();
    this.resize();
    new ResizeObserver(() => this.resize()).observe(this.container);
    this.loop();
  }

  private setupGL(img: HTMLImageElement, water: HTMLImageElement, ids: HTMLImageElement) {
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
    tex(1, water, 'uWater');
    tex(2, ids, 'uIds', true);
    gl.uniform2f(gl.getUniformLocation(p, 'uImgPx'), 1 / img.naturalWidth, 1 / img.naturalHeight);
    gl.uniform1f(gl.getUniformLocation(p, 'uAspect'), img.naturalWidth / img.naturalHeight);
    // Flicker only the small flames (candles, lanterns, paper lanterns, globes).
    const L = this.data.lights.slice(0, MAX_LIGHTS);
    const arr = new Float32Array(MAX_LIGHTS * 4);
    L.forEach((l, i) => {
      const strength = l.k === 'candle' ? 0.06 : l.k === 'pl' ? 0.035 : 0.045;
      arr.set([l.x, l.y, (i * 2.399) % 6.283, strength], i * 4);
    });
    gl.uniform4fv(gl.getUniformLocation(p, 'uLights'), arr);
    gl.uniform1i(gl.getUniformLocation(p, 'uCount'), L.length);
    return true;
  }

  /** Fit the 4:3 render inside the container ("contain"), centred. */
  private resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h || !this.img) return;
    const ar = this.img.naturalWidth / this.img.naturalHeight;
    let cw = w, ch = w / ar;
    if (ch > h) { ch = h; cw = h * ar; }
    const el = (this.fallback ?? this.canvas) as HTMLElement;
    el.style.width = `${cw}px`;
    el.style.height = `${ch}px`;
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

  private draw() {
    const gl = this.gl, p = this.prog;
    if (!gl || !p) return;
    const t = (performance.now() - this.start) / 1000;
    gl.uniform1f(gl.getUniformLocation(p, 'uTime'), t);
    gl.uniform1f(gl.getUniformLocation(p, 'uMotion'), this.motion);
    const idx = this.hover ? this.data.groups.indexOf(this.hover) + 1 : 0;
    gl.uniform1f(gl.getUniformLocation(p, 'uHover'), idx ? (idx * 40) / 255 : 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    if (document.hidden || !this.motion) return;
    this.draw();
  };

  dispose() {
    cancelAnimationFrame(this.raf);
  }
}
