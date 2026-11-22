// Package a room render for the web (see tools/blender/concepts/room_*.py).
// Usage: node tools/blender/package_room.mjs <export-dir> <out-dir>
//   room.png (+ room-<variant>.png)  → room(.avif/.webp), room-<variant>(...)
//   mask_<group>.png (alpha)         → hl-<group>.png (white, alpha = the object, for CSS masks)
//                                      ids.png (red = 40 × group index) for picking
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import sharp from 'sharp';

const [src, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const scene = JSON.parse(readFileSync(`${src}/scene.json`, 'utf8'));
const [W, H] = scene.size;
const avif = { quality: 82, effort: 6, chromaSubsampling: '4:4:4' };

scene.variants = [];
for (const f of readdirSync(src).filter((f) => /^room(-[a-z]+)?\.png$/.test(f))) {
  const name = f.replace('.png', '');
  const img = sharp(`${src}/${f}`).resize(W, H);
  await img.clone().avif(avif).toFile(`${out}/${name}.avif`);
  await img.clone().webp({ quality: 88, effort: 6 }).toFile(`${out}/${name}.webp`);
  scene.variants.push(name);
}

const ids = new Uint8Array(W * H), best = new Uint8Array(W * H);
for (const [gi, g] of scene.groups.entries()) {
  const { data } = await sharp(`${src}/mask_${g}.png`).ensureAlpha().resize(W, H).raw().toBuffer({ resolveWithObject: true });
  const a = new Uint8Array(W * H);
  for (let i = 0; i < a.length; i++) {
    a[i] = data[i * 4 + 3];
    if (a[i] > 110 && a[i] > best[i]) { best[i] = a[i]; ids[i] = (gi + 1) * 40; }
  }
  const rgba = Buffer.alloc(W * H * 4, 255);
  for (let i = 0; i < a.length; i++) rgba[i * 4 + 3] = a[i];
  await sharp(rgba, { raw: { width: W, height: H, channels: 4 } }).resize(Math.round(W / 2), Math.round(H / 2)).png({ compressionLevel: 9 }).toFile(`${out}/hl-${g}.png`);
}
await sharp(Buffer.from(ids), { raw: { width: W, height: H, channels: 1 } }).resize(Math.round(W / 2), Math.round(H / 2), { kernel: 'nearest' }).png({ compressionLevel: 9 }).toFile(`${out}/ids.png`);
writeFileSync(`${out}/scene.json`, JSON.stringify(scene));
console.log('packaged room to', out, scene.groups.join(', '), '| variants:', scene.variants.join(', '));
