// Package the canal render for the web (see tools/blender/concepts/canal_final.py).
// Usage: node tools/blender/package_canal.mjs <export-dir> [out-dir=public/canal]
//   canal.png (2800×2100)       → canal(.avif/.webp) + canal-1400(.avif/.webp)
//   mask_water.png (alpha)      → water.png (grey = how much canal shows)
//   mask_<group>.png (alpha)    → ids.png (red = 40 × group index, 0 = nothing)
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import sharp from 'sharp';

const [src, out = 'public/canal'] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const scene = JSON.parse(readFileSync(`${src}/scene.json`, 'utf8'));
const [W, H] = scene.size;

// AVIF 4:4:4 keeps the dark sky gradient smooth (lossy WebP turns it blocky);
// near-lossless WebP is the fallback for browsers without AVIF.
const avif = { quality: 80, effort: 6, chromaSubsampling: '4:4:4' };
await sharp(`${src}/canal.png`).avif(avif).toFile(`${out}/canal.avif`);
await sharp(`${src}/canal.png`).resize(1400, 1050).avif(avif).toFile(`${out}/canal-1400.avif`);
await sharp(`${src}/canal.png`).webp({ nearLossless: true, quality: 60, effort: 6 }).toFile(`${out}/canal.webp`);
await sharp(`${src}/canal.png`).resize(1400, 1050).webp({ nearLossless: true, quality: 60, effort: 6 }).toFile(`${out}/canal-1400.webp`);
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
writeFileSync(`${out}/scene.json`, JSON.stringify(scene));
console.log('packaged canal to', out, scene.lights.length, 'lights');
