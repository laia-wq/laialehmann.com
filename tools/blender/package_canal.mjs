// Package the canal render for the web (see tools/blender/concepts/canal_final.py).
// Usage: node tools/blender/package_canal.mjs <export-dir> [out-dir=public/canal]
//   canal.png (2800×2100)       → canal(.avif/.webp) + canal-1400(.avif/.webp)
//   mask_water.png (alpha)      → water.png (grey = how much canal shows)
//   mask_<group>.png (alpha)    → ids.png (red = 40 × group index, 0 = nothing)
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import sharp from 'sharp';

const [src, out = 'public/canal'] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const scene = JSON.parse(readFileSync(`${src}/scene.json`, 'utf8'));
const [W, H] = scene.size;

// AVIF 4:4:4 keeps the dark sky gradient smooth (lossy WebP turns it blocky);
// near-lossless WebP is the fallback for browsers without AVIF.
const avif = { quality: 88, effort: 6, chromaSubsampling: '4:4:4' };
for (const [png, name] of [['canal.png', 'canal'], ['canal_off.png', 'canal-off']]) {
  if (!existsSync(`${src}/${png}`)) continue;
  await sharp(`${src}/${png}`).avif(avif).toFile(`${out}/${name}.avif`);
  await sharp(`${src}/${png}`).resize(1400, 1050).avif(avif).toFile(`${out}/${name}-1400.avif`);
  await sharp(`${src}/${png}`).webp({ nearLossless: true, quality: 60, effort: 6 }).toFile(`${out}/${name}.webp`);
  await sharp(`${src}/${png}`).resize(1400, 1050).webp({ nearLossless: true, quality: 60, effort: 6 }).toFile(`${out}/${name}-1400.webp`);
}
if (existsSync(`${src}/smoke.json`)) scene.smoke = JSON.parse(readFileSync(`${src}/smoke.json`, 'utf8'));
// Colours along the top, middle and bottom edges, for the page behind the letterbox.
{
  const { data, info } = await sharp(`${src}/canal.png`).removeAlpha().resize(64, 48).raw().toBuffer({ resolveWithObject: true });
  const row = (y) => { const c = [0, 0, 0]; for (const x of [0, 1, 62, 63]) for (let k = 0; k < 3; k++) c[k] += data[(y * info.width + x) * 3 + k] / 4; return c.map(Math.round); };
  scene.bg = [row(0), row(24), row(47)];
}

const alpha = async (f) => {
  const { data, info } = await sharp(f).ensureAlpha().resize(W, H).raw().toBuffer({ resolveWithObject: true });
  const a = new Uint8Array(info.width * info.height);
  for (let i = 0; i < a.length; i++) a[i] = data[i * 4 + 3];
  return a;
};

const water = await alpha(`${src}/mask_water.png`);
await sharp(Buffer.from(water), { raw: { width: W, height: H, channels: 1 } }).png({ compressionLevel: 9 }).toFile(`${out}/water.png`);

const ids = new Uint8Array(W * H);
const best = new Uint8Array(W * H);
for (const [gi, g] of scene.groups.entries()) {
  const a = await alpha(`${src}/mask_${g}.png`);
  for (let i = 0; i < a.length; i++) {
    if (a[i] > 110 && a[i] > best[i]) { best[i] = a[i]; ids[i] = (gi + 1) * 40; }
  }
}
await sharp(Buffer.from(ids), { raw: { width: W, height: H, channels: 1 } }).png({ compressionLevel: 9 }).toFile(`${out}/ids.png`);
// Switch-on order. delay.png (16-bit, linear) has every glowing thing emit
// (its random moment, 1, 0), the water a mirror, everything else black, so
// red/green is the moment of whatever lights that pixel, directly or in the
// canal's reflection. Every other pixel takes the moment of its nearest light
// (so a window, its glow on the wall and its reflection all come on together);
// green says how near a light it is.
if (existsSync(`${src}/delay.png`)) {
  const { data, info } = await sharp(`${src}/delay.png`).toColourspace('rgb16').raw({ depth: 'ushort' }).toBuffer({ resolveWithObject: true });
  const px = new Uint16Array(data.buffer, data.byteOffset, data.length / 2);
  const w = info.width, h = info.height, ch = info.channels, n = w * h;
  const own = new Float32Array(n).fill(-1), dist = new Float32Array(n).fill(1e9);
  let frontier = [];
  for (let i = 0; i < n; i++) {
    const r = px[i * ch] / 65535, g = px[i * ch + 1] / 65535;
    if (g > 0.04) { own[i] = Math.min(1, r / g); dist[i] = 0; frontier.push(i); }
  }
  // One window is several glowing things (glass, a lamp inside, a candle on
  // the sill), each with its own random moment, so it came on in clumps.
  // Join everything that glows within a few pixels into one patch and give
  // the whole patch one moment: the one most of its pixels already have
  // (the glass), so a window and its reflection still agree.
  {
    const R = 4, lit = new Uint8Array(n), grow = new Uint8Array(n), tmp = new Uint8Array(n);
    for (let i = 0; i < n; i++) lit[i] = own[i] >= 0 ? 1 : 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {          // dilate along x
      let v = 0; for (let d = -R; d <= R && !v; d++) { const xx = x + d; if (xx >= 0 && xx < w && lit[y * w + xx]) v = 1; }
      tmp[y * w + x] = v;
    }
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {          // then along y
      let v = 0; for (let d = -R; d <= R && !v; d++) { const yy = y + d; if (yy >= 0 && yy < h && tmp[yy * w + x]) v = 1; }
      grow[y * w + x] = v;
    }
    const label = new Int32Array(n).fill(-1), stack = new Int32Array(n);
    let patches = 0;
    for (let s0 = 0; s0 < n; s0++) {
      if (!grow[s0] || label[s0] >= 0) continue;
      let sp = 0; stack[sp++] = s0; label[s0] = patches;
      const members = [];
      while (sp) {
        const i = stack[--sp]; members.push(i);
        const x = i % w, y = (i / w) | 0;
        if (x > 0 && grow[i - 1] && label[i - 1] < 0) { label[i - 1] = patches; stack[sp++] = i - 1; }
        if (x < w - 1 && grow[i + 1] && label[i + 1] < 0) { label[i + 1] = patches; stack[sp++] = i + 1; }
        if (y > 0 && grow[i - w] && label[i - w] < 0) { label[i - w] = patches; stack[sp++] = i - w; }
        if (y < h - 1 && grow[i + w] && label[i + w] < 0) { label[i + w] = patches; stack[sp++] = i + w; }
      }
      const votes = new Map();
      for (const i of members) if (lit[i]) { const q = Math.round(own[i] * 255); votes.set(q, (votes.get(q) ?? 0) + 1); }
      let best = -1, bestN = -1;
      for (const [q, c] of votes) if (c > bestN) { best = q; bestN = c; }
      for (const i of members) if (lit[i]) own[i] = best / 255;
      patches++;
    }
    console.log('switch-on patches:', patches);
  }
  // spread outwards ring by ring from every lit pixel (nearest light wins)
  const steps = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.414], [-1, 1, 1.414], [1, -1, 1.414], [-1, -1, 1.414]];
  while (frontier.length) {
    const next = [];
    for (const i of frontier) {
      const x = i % w, y = (i / w) | 0;
      for (const [dx, dy, c] of steps) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const j = ny * w + nx, d = dist[i] + c;
        if (d < dist[j]) { if (dist[j] === 1e9) next.push(j); dist[j] = d; own[j] = own[i]; }
      }
    }
    frontier = next;
  }
  const outb = Buffer.alloc(n * 3);
  for (let i = 0; i < n; i++) {
    outb[i * 3] = Math.round(Math.max(0, own[i]) * 255);
    outb[i * 3 + 1] = Math.round(255 * Math.max(dist[i] === 0 ? 1 : 0, Math.exp(-dist[i] / 28)));
  }
  await sharp(outb, { raw: { width: w, height: h, channels: 3 } }).png({ compressionLevel: 9 }).toFile(`${out}/delay.png`);
}
// Extras (canal_final.py EXTRAS_OUT): the owl's eye states as same-sized
// crops of the full render, and the koi's jump frames (fish only, alpha).
const ex = `${src}/extras`;
if (existsSync(`${ex}/extras.json`)) {
  const meta = JSON.parse(readFileSync(`${ex}/extras.json`, 'utf8'));
  const st = meta.owl.states;
  const m0 = await sharp(`${ex}/owl_${st[0]}.png`).metadata();
  const ow = m0.width, oh = m0.height;
  await sharp({ create: { width: ow * st.length, height: oh, channels: 3, background: '#000' } })
    .composite(await Promise.all(st.map(async (s, i) => ({ input: await sharp(`${ex}/owl_${s}.png`).removeAlpha().png().toBuffer(), left: i * ow, top: 0 }))))
    .png({ compressionLevel: 9 }).toFile(`${out}/owl.png`);
  scene.owl = { box: meta.owl.box, states: st };
  if (meta.koi.length) {
    const sizes = await Promise.all(meta.koi.map((_, si) => sharp(`${ex}/koi_${si}_00.png`).metadata()));
    const cw = Math.max(...sizes.map((m) => m.width)), ch = Math.max(...sizes.map((m) => m.height));
    const n = meta.koi[0].n;
    const parts = [];
    for (const [si, k] of meta.koi.entries())
      for (let fi = 0; fi < n; fi++)
        parts.push({ input: `${ex}/koi_${si}_${String(fi).padStart(2, '0')}.png`, left: fi * cw, top: si * ch });
    await sharp({ create: { width: cw * n, height: ch * meta.koi.length, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
      .composite(parts).png({ compressionLevel: 9 }).toFile(`${out}/koi.png`);
    scene.koi = { cell: [cw, ch], n, spots: meta.koi.map((k, si) => ({ ...k, size: [sizes[si].width, sizes[si].height] })) };
  }
}
writeFileSync(`${out}/scene.json`, JSON.stringify(scene));
console.log('packaged canal to', out, scene.lights.length, 'lights');
