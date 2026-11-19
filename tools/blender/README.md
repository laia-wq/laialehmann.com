# Blender build (experimental)

`build_interior.py` builds the globe's interior layer by layer (soil, terrain
and mountain, water and waterfall, scanned rocks, scanned firs, ferns, moss)
and renders a Cycles reference image.

Requires Blender's Python module (`pip install bpy==5.3.0`, Python 3.13) and the
CC0 Poly Haven source files (fir_tree_01, fir_sapling, fern_02,
rock_moss_set_01/02, the sunset_forest HDRI) downloaded into an assets folder:

    python tools/blender/build_interior.py <assets-dir> <out-dir> render

Env vars: `SAMPLES` (default 48), `RES` (width, default 1000).
