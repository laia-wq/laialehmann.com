#!/bin/sh
# Build a self-contained copy of the site for a static preview host that
# serves only common web file types: .glb models are renamed to .glb.wasm
# (binary-safe; the loader detects glTF by its header, not the extension).
# Usage: sh tools/preview_build.sh <out-dir>
set -e
OUT="$1"
rm -rf "$OUT"
npx vite build --base ./ --outDir "$OUT" --emptyOutDir
for f in $(find "$OUT" -name '*.glb'); do mv "$f" "$f.wasm"; done
sed -i -E 's/(static|water|veg)\.glb/\1.glb.wasm/g' "$OUT"/assets/Experience-*.js
rm -rf "$OUT/models"
rm -f "$OUT"/world/cards_*.webp
