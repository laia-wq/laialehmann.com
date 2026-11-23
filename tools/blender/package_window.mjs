// Package a window close-up (canal_final.py CLOSEUP=<id>) for the browser.
// Usage: node tools/blender/package_window.mjs <close-out-dir> <id> [out=public/windows/<id>]
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import sharp from 'sharp';

const [src, id, out = `public/windows/${id}`] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
await sharp(`${src}/${id}.png`).avif({ quality: 80, effort: 6, chromaSubsampling: '4:4:4' }).toFile(`${out}/${id}.avif`);
await sharp(`${src}/${id}.png`).webp({ quality: 86, effort: 6 }).toFile(`${out}/${id}.webp`);
// the glass masks: white where the glass is, alpha = how much. One for a
// single window (pane.png), or one per window (pane_0.png, pane_1.png, ...)
const masks = ['pane', ...Array.from({ length: 8 }, (_, k) => `pane_${k}`)].filter((m) => existsSync(`${src}/${m}.png`));
for (const m of masks) {
  const { data, info } = await sharp(`${src}/${m}.png`).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  for (let i = 0; i < info.width * info.height; i++) { data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = 255; }
  await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).resize(Math.round(info.width / 2)).png({ compressionLevel: 9 }).toFile(`${out}/${m}.png`);
}
copyFileSync(`${src}/closeup.json`, `${out}/closeup.json`);
// the camera's swing, at the size it was rendered (sharp on big screens)
const n = JSON.parse(readFileSync(`${src}/closeup.json`, 'utf8')).frames ?? 0;
for (let k = 0; k < n; k++) {
  const f = `${src}/fly_${String(k).padStart(3, '0')}.png`;
  if (existsSync(f)) await sharp(f).webp({ quality: 76, effort: 5 }).toFile(`${out}/fly_${String(k).padStart(3, '0')}.webp`);
}
// mark this zoom ready in the street's index (its click areas switch on)
const idxPath = `${out}/../index.json`;
if (existsSync(idxPath)) {
  const idx = JSON.parse(readFileSync(idxPath, 'utf8'));
  idx.ready = [...new Set([...(idx.ready ?? []), id])];
  writeFileSync(idxPath, JSON.stringify(idx));
}
console.log('packaged window', id, 'to', out);
