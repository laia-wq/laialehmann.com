// Compress the Blender export for the web: meshopt geometry, WebP textures.
// Usage: node tools/blender/package_web.mjs <export-dir> [out-dir=public/world]
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import sharp from 'sharp';
const [src, out = 'public/world'] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const gt = (args) => execFileSync('npx', ['gltf-transform', ...args], { stdio: 'inherit' });
gt(['optimize', `${src}/static.glb`, `${out}/static.glb`, '--compress', 'meshopt', '--texture-compress', 'webp', '--texture-size', '4096', '--simplify-ratio', '0.6', '--simplify-error', '0.0008']);
gt(['optimize', `${src}/water.glb`, `${out}/water.glb`, '--compress', 'meshopt', '--simplify', 'false']);
for (const f of readdirSync(out)) if (f.startsWith('cards_')) rmSync(`${out}/${f}`);
for (const f of readdirSync(src).filter((f) => /^cards_.*\.png$/.test(f))) {
  await sharp(`${src}/${f}`).webp({ quality: 84, alphaQuality: 92, effort: 5 }).toFile(`${out}/${f.replace('.png', '.webp')}`);
}
copyFileSync(`${src}/world.json`, `${out}/world.json`);
console.log('packaged to', out);
