import { defineConfig } from 'vite';
import { createHash } from 'node:crypto';
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

/** A short hash of the rendered assets (names, sizes, times), added to their
 *  URLs so a browser fetches a new render instead of showing a cached one. */
function assetVersion(dirs: string[]) {
  const h = createHash('sha1');
  const walk = (d: string) => {
    let names: string[] = [];
    try { names = readdirSync(d).sort(); } catch { return; }
    for (const n of names) {
      const p = join(d, n), s = statSync(p);
      if (s.isDirectory()) walk(p); else h.update(`${p}:${s.size}:${s.mtimeMs}\n`);
    }
  };
  dirs.forEach(walk);
  return h.digest('hex').slice(0, 10);
}

export default defineConfig({
  define: {
    __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
    __ASSET_V__: JSON.stringify(assetVersion(['public/canal', 'public/windows'])),
  },
  base: '/',
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 800,
  },
});
