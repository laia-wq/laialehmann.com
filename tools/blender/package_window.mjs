// Package a window close-up (canal_final.py CLOSEUP=<id>) for the browser.
// Usage: node tools/blender/package_window.mjs <close-out-dir> <id> [out=public/windows/<id>]
import { copyFileSync, mkdirSync } from 'node:fs';
import sharp from 'sharp';

const [src, id, out = `public/windows/${id}`] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
await sharp(`${src}/${id}.png`).avif({ quality: 80, effort: 6, chromaSubsampling: '4:4:4' }).toFile(`${out}/${id}.avif`);
await sharp(`${src}/${id}.png`).webp({ quality: 86, effort: 6 }).toFile(`${out}/${id}.webp`);
// the glass mask: white where the glass is, alpha = how much
const { data, info } = await sharp(`${src}/pane.png`).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
for (let i = 0; i < info.width * info.height; i++) { data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = 255; }
await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).resize(Math.round(info.width / 2)).png({ compressionLevel: 9 }).toFile(`${out}/pane.png`);
copyFileSync(`${src}/closeup.json`, `${out}/closeup.json`);
console.log('packaged window', id, 'to', out);
