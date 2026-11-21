/**
 * Laia's signature, drawn like a pen: each stroke is an SVG path, sampled
 * along its length and painted onto a canvas with a calligraphy nib (thick on
 * downstrokes, hairline on sideways strokes). On first view it writes itself.
 */

// viewBox 0 0 600 190. Baseline ~130, small letters ~14 tall, capitals ~125.
/** A copperplate capital L at (x, y) on the baseline: a long teardrop loop at
 *  the top, one slanted shaded downstroke, a small looped foot, out to the right. */
function capitalL(x: number, y: number, k: number) {
  const P = (px: number, py: number) => `${(x + px * k).toFixed(1)} ${(y + py * k).toFixed(1)}`;
  return `M ${P(36, -52)} C ${P(16, -78)}, ${P(22, -116)}, ${P(56, -121)} C ${P(76, -124)}, ${P(76, -106)}, ${P(62, -92)} `
    + `C ${P(46, -72)}, ${P(24, -30)}, ${P(12, -8)} C ${P(4, 6)}, ${P(-16, 11)}, ${P(-23, 3)} C ${P(-27, -6)}, ${P(-6, -12)}, ${P(14, -5)} C ${P(26, -1)}, ${P(36, 1)}, ${P(44, 0)}`;
}

// viewBox 0 0 600 190. Baseline 130, small letters ~14 tall, capitals ~120.
export const SIGNATURE_STROKES: { d: string; w: number }[] = [
  { w: 1.0, d: capitalL(98, 132, 0.96) },
  // a i a (small, quick), starting where the L's foot runs out
  { w: 0.8, d: 'M 140 130 C 144 121, 152 116, 153 121 C 149 117, 140 122, 142 128 C 144 133, 151 128, 154 121 C 153 126, 153 130, 158 129 C 161 124, 163 120, 164 119 C 164 124, 164 129, 168 129 C 172 121, 180 116, 181 121 C 177 117, 168 122, 170 128 C 172 133, 179 128, 182 121 C 181 126, 182 130, 190 129' },
  { w: 1.05, d: capitalL(196, 132, 1.03) },
  // e h m a n n, compressed into a fast scribble
  { w: 0.8, d: 'M 242 130 C 248 125, 252 119, 249 116 C 245 114, 240 124, 246 129 C 250 132, 256 126, 259 116 C 263 104, 266 90, 268 84 C 269 93, 265 112, 263 129 C 266 121, 271 116, 274 119 C 276 123, 274 128, 277 129 C 279 122, 283 116, 286 119 C 288 123, 286 128, 289 129 C 291 122, 295 116, 298 119 C 300 123, 298 128, 302 128 C 306 121, 314 117, 315 121 C 311 117, 303 122, 305 128 C 307 133, 314 127, 317 120 C 317 125, 317 129, 321 128 C 323 122, 327 117, 330 120 C 332 124, 330 128, 333 129 C 335 122, 339 117, 342 120 C 344 124, 342 128, 349 127' },
  // the tail: dips under the name, swings back left, then runs out long to the right
  { w: 0.9, d: 'M 349 127 C 371 124, 369 146, 319 154 C 259 163, 159 160, 89 152 C 69 150, 71 146, 99 148 C 219 156, 419 150, 570 140' },
];
export const SIGNATURE_DOT = { x: 586, y: 139, r: 2.8 };

export function drawSignature(canvas: HTMLCanvasElement, opts: { color: string; animate: boolean; width?: number; nib?: number }) {
  const VB_W = 600, VB_H = 190;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const cssW = opts.width ?? canvas.clientWidth ?? 300;
  const scale = cssW / VB_W;
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(VB_H * scale * dpr);
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${VB_H * scale}px`;
  const ctx = canvas.getContext('2d')!;
  ctx.setTransform(scale * dpr, 0, 0, scale * dpr, 0, 0);
  ctx.fillStyle = opts.color;
  // Sample every stroke into (x, y, width) dabs once.
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('width', '0'); svg.setAttribute('height', '0');
  svg.style.position = 'absolute';
  document.body.appendChild(svg);
  const nib = opts.nib ?? 4.4;
  const nibAngle = -0.6; // radians: a pen held at an angle
  const dabs: { x: number; y: number; r: number }[][] = SIGNATURE_STROKES.map(({ d, w }) => {
    const p = document.createElementNS(svgNS, 'path');
    p.setAttribute('d', d);
    svg.appendChild(p);
    const L = p.getTotalLength();
    const n = Math.max(2, Math.ceil(L / 0.6));
    const out: { x: number; y: number; r: number }[] = [];
    let prev = p.getPointAtLength(0);
    for (let i = 0; i <= n; i++) {
      const t = (i / n) * L;
      const q = p.getPointAtLength(t);
      const ang = Math.atan2(q.y - prev.y, q.x - prev.x);
      // thick across the nib, hairline along it; taper at both ends of a stroke
      const across = Math.abs(Math.sin(ang - nibAngle));
      const taper = Math.min(1, t / 6, (L - t) / 10);
      out.push({ x: q.x, y: q.y, r: Math.max(0.32, (0.18 + 0.82 * across) * nib * w * 0.5 * (0.35 + 0.65 * taper)) });
      prev = q;
    }
    return out;
  });
  svg.remove();
  const all = dabs.flat();
  const total = all.length;
  const paint = (upto: number) => {
    ctx.clearRect(0, 0, VB_W, VB_H);
    for (let i = 0; i < upto; i++) {
      const b = all[i];
      ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2); ctx.fill();
    }
    if (upto >= total) { ctx.beginPath(); ctx.arc(SIGNATURE_DOT.x, SIGNATURE_DOT.y, SIGNATURE_DOT.r, 0, Math.PI * 2); ctx.fill(); }
  };
  if (!opts.animate) { paint(total); return; }
  const dur = 1900, t0 = performance.now();
  const step = () => {
    const k = Math.min(1, (performance.now() - t0) / dur);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    paint(Math.round(e * total));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
