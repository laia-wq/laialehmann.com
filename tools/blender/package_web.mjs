// Compress the Blender export for the web: meshopt geometry, WebP textures.
// Usage: node tools/blender/package_web.mjs <export-dir> [out-dir=public/world]
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync } from 'node:fs';
import sharp from 'sharp';
const [src, out = 'public/world'] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const gt = (args) => execFileSync('npx', ['gltf-transform', ...args], { stdio: 'inherit' });
gt(['optimize', `${src}/static.glb`, `${out}/static.glb`, '--compress', 'meshopt', '--texture-compress', 'webp', '--texture-size', '2048', '--simplify-ratio', '0.6', '--simplify-error', '0.0008']);
gt(['optimize', `${src}/water.glb`, `${out}/water.glb`, '--compress', 'meshopt', '--simplify', 'false']);
for (const k of ['tree', 'small']) {
  await sharp(`${src}/cards_${k}.png`).webp({ quality: 88, alphaQuality: 95 }).toFile(`${out}/cards_${k}.webp`);
}
copyFileSync(`${src}/world.json`, `${out}/world.json`);
console.log('packaged to', out);
