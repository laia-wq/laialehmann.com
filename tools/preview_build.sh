#!/bin/sh
# Build a self-contained copy of the site for a static preview host.
# The canal scene only needs public/canal; the older globe/island assets
# (world/, textures/, models/) are left out to keep the upload small.
# Usage: sh tools/preview_build.sh <out-dir>
set -e
OUT="$1"
rm -rf "$OUT"
npx vite build --base ./ --outDir "$OUT" --emptyOutDir
rm -rf "$OUT/world" "$OUT/textures" "$OUT/models"
