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
// Switch-on order: delay.png has one random grey per glowing thing (alpha =
// where it is). Spread each grey into the light around it with a wide blur
// (premultiplied, then divided back out) → r = when, g = how near a light.
if (existsSync(`${src}/delay.png`)) {
  const { data, info } = await sharp(`${src}/delay.png`).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const n = info.width * info.height;
  const pre = Buffer.alloc(n * 2);
  for (let i = 0; i < n; i++) { const a = data[i * 4 + 3]; pre[i * 2] = Math.round(Math.pow(data[i * 4] / 255, 2.2) * a);   // back to an even 0..1 spread pre[i * 2 + 1] = a; }
  const blur = async (ch, sigma) => {
    const one = Buffer.alloc(n); for (let i = 0; i < n; i++) one[i] = pre[i * 2 + ch];
    return sharp(one, { raw: { width: info.width, height: info.height, channels: 1 } }).blur(sigma).extractChannel(0).raw().toBuffer();
  };
  const [ra, aa] = [await blur(0, 16), await blur(1, 16)];
  const [rs, as] = [await blur(0, 3), await blur(1, 3)];
  const outb = Buffer.alloc(n * 3);
  for (let i = 0; i < n; i++) {
    // near a light: its own grey (tight blur); further out: the wide blend
    const wide = aa[i] > 0 ? ra[i] / aa[i] : 0, tight = as[i] > 0 ? rs[i] / as[i] : wide;
    const wn = Math.min(1, Math.max(0, (as[i] - 10) / 60));
    const r = wide + (tight - wide) * wn;
    outb[i * 3] = Math.round(Math.min(1, r) * 255);
    outb[i * 3 + 1] = Math.min(255, Math.max(as[i], aa[i] * 6));
  }
  await sharp(outb, { raw: { width: info.width, height: info.height, channels: 3 } }).resize(700, 525).png({ compressionLevel: 9 }).toFile(`${out}/delay.png`);
}
writeFileSync(`${out}/scene.json`, JSON.stringify(scene));
console.log('packaged canal to', out, scene.lights.length, 'lights');
