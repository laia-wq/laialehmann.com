/**
 * Laia's signature, drawn like a pen: each stroke is an SVG path, sampled
 * along its length and widened into a filled vector outline by a calligraphy
 * nib (thick on downstrokes, hairline on sideways strokes). On first view it
 * writes itself.
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
/** the dot on the i of Laia: a quick slanted tick of the pen */
export const I_DOT = { x: 166, y: 108, r: 2.3 };

const SVG_NS = 'http://www.w3.org/2000/svg';
const VB_W = 600, VB_H = 190;

/** Each stroke as a filled outline: the pen's centreline, widened by a
 *  calligraphy nib (thick across the nib, hairline along it, tapered ends).
 *  Built from small quads all wound the same way, so loops that cross
 *  themselves stay solid. Pure vector: sharp at any size. */
function outlines(nib: number) {
  const tmp = document.createElementNS(SVG_NS, 'svg');
  tmp.setAttribute('width', '0'); tmp.setAttribute('height', '0');
  tmp.style.position = 'absolute';
  document.body.appendChild(tmp);
  const nibAngle = -0.6;
  const res = SIGNATURE_STROKES.map(({ d, w }) => {
    const p = document.createElementNS(SVG_NS, 'path');
    p.setAttribute('d', d);
    tmp.appendChild(p);
    const L = p.getTotalLength();
    const n = Math.max(2, Math.ceil(L / 0.9));
    const pts: { x: number; y: number }[] = [];
    for (let i = 0; i <= n; i++) { const q = p.getPointAtLength((i / n) * L); pts.push({ x: q.x, y: q.y }); }
    const left: [number, number][] = [], right: [number, number][] = [];
    let maxR = 0;
    pts.forEach((q, i) => {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n, i + 1)];
      const ang = Math.atan2(b.y - a.y, b.x - a.x);
      const t = (i / n) * L;
      const across = Math.abs(Math.sin(ang - nibAngle));
      const taper = Math.min(1, t / 6, (L - t) / 10);
      const r = Math.max(0.3, (0.18 + 0.82 * across) * nib * w * 0.5 * (0.35 + 0.65 * taper));
      maxR = Math.max(maxR, r);
      const nx = -Math.sin(ang), ny = Math.cos(ang);
      left.push([q.x + nx * r, q.y + ny * r]); right.push([q.x - nx * r, q.y - ny * r]);
    });
    const f = (v: number) => v.toFixed(2);
    let out = '';
    for (let i = 0; i < n; i++) {
      let quad = [left[i], left[i + 1], right[i + 1], right[i]];
      let area = 0;
      for (let k = 0; k < 4; k++) { const [x0, y0] = quad[k], [x1, y1] = quad[(k + 1) % 4]; area += x0 * y1 - x1 * y0; }
      if (area < 0) quad = quad.reverse();
      out += `M${f(quad[0][0])} ${f(quad[0][1])}L${f(quad[1][0])} ${f(quad[1][1])}L${f(quad[2][0])} ${f(quad[2][1])}L${f(quad[3][0])} ${f(quad[3][1])}Z`;
    }
    // round the two ends
    const cap = (q: { x: number; y: number }, r: number) => { const rr = f(r); return `M${f(q.x - r)} ${f(q.y)}a${rr} ${rr} 0 1 0 ${f(2 * r)} 0a${rr} ${rr} 0 1 0 ${f(-2 * r)} 0Z`; };
    out += cap(pts[0], Math.hypot(left[0][0] - pts[0].x, left[0][1] - pts[0].y)) + cap(pts[n], Math.hypot(left[n][0] - pts[n].x, left[n][1] - pts[n].y));
    return { d, fill: out, length: L, width: maxR * 2 + 2 };
  });
  tmp.remove();
  return res;
}

let cache: ReturnType<typeof outlines> | null = null;
let uid = 0;

/** Draw the signature into an <svg>; on first view it writes itself (a mask
 *  following each stroke's centreline uncovers the ink in pen order). */
export function drawSignature(svg: SVGSVGElement, opts: { color: string; animate: boolean; width?: number; nib?: number }) {
  cache ??= outlines(opts.nib ?? 4.4);
  const cssW = opts.width ?? 300;
  svg.setAttribute('viewBox', `0 0 ${VB_W} ${VB_H}`);
  svg.style.width = `${cssW}px`;
  svg.style.height = `${(cssW * VB_H) / VB_W}px`;
  if (svg.dataset.built) return;   // resize: the vector just scales
  svg.dataset.built = '1';
  const id = `sig-mask-${uid++}`;
  const dot = ({ x, y, r }: { x: number; y: number; r: number }) => `M${x - r} ${y}a${r} ${r * 0.8} 0 1 0 ${2 * r} 0a${r} ${r * 0.8} 0 1 0 ${-2 * r} 0Z`;
  const dots = dot(I_DOT) + dot(SIGNATURE_DOT);
  const ink = cache.map((s) => s.fill).join('') + dots;
  if (!opts.animate) {
    svg.innerHTML = `<path fill="${opts.color}" d="${ink}"/>`;
    return;
  }
  // one mask per stroke, so a stroke only uncovers its own ink
  svg.innerHTML = '<defs>' + cache.map((s, i) => `<mask id="${id}-${i}" maskUnits="userSpaceOnUse" x="0" y="0" width="${VB_W}" height="${VB_H}">`
    + `<path d="${s.d}" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="${s.width.toFixed(1)}" stroke-dasharray="${s.length.toFixed(1)} ${(s.length + 10).toFixed(1)}" stroke-dashoffset="${s.length.toFixed(1)}"/></mask>`).join('')
    + '</defs>' + cache.map((s, i) => `<path fill="${opts.color}" d="${s.fill}" mask="url(#${id}-${i})"/>`).join('')
    + `<path class="sig-dots" fill="${opts.color}" d="${dots}" opacity="0"/>`;
  const strokes = Array.from(svg.querySelectorAll('mask path')) as SVGPathElement[];
  const total = cache.reduce((a, s) => a + s.length, 0);
  const dur = 1900, t0 = performance.now();
  const step = () => {
    const k = Math.min(1, (performance.now() - t0) / dur);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    let left = e * total;
    cache!.forEach((s, i) => {
      const drawn = Math.max(0, Math.min(s.length, left));
      strokes[i].setAttribute('stroke-dashoffset', (s.length - drawn).toFixed(1));
      left -= s.length;
    });
    // the dots go on last, once the pen has finished
    svg.querySelector('.sig-dots')?.setAttribute('opacity', String(Math.min(1, Math.max(0, (k - 0.93) / 0.05))));
    if (k < 1) requestAnimationFrame(step);
    else svg.innerHTML = `<path fill="${opts.color}" d="${ink}"/>`;
  };
  requestAnimationFrame(step);
}
