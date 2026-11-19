"""
Build the globe's world in Blender, layer by layer, like a real terrarium:

  1 soil & gravel bowl      2 terrain: meadow, massif, distant ridges
  3 water: pool, stream, waterfall   4 rocks & boulders
  5 conifer forest (near + far)      6 broadleaf & blossom trees
  7 shrubs, ferns, grasses           8 wildflower meadows
  9 moss (hair, render only)

Every plant is a CC0 Poly Haven scan, placed as a linked duplicate so the
glTF export can use GPU instancing. Coordinates: Blender Z-up, sphere
centre at the origin, inner glass radius 0.972. Camera looks toward +Y.

Usage:  python build_world.py <assets-dir> <out-dir> <render|blend>
Env:    SAMPLES (default 48), RES (width, default 1100)
"""
import bpy, bmesh, sys, os, glob, math, random
from mathutils import Vector, noise, Matrix

ASSETS, OUT, MODE = sys.argv[-3], sys.argv[-2], sys.argv[-1]
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', '..', 'public', 'textures'))
os.makedirs(OUT, exist_ok=True)
random.seed(21)

INNER = 0.972
DEPTH = 0.5
GROUND = -DEPTH
EDGE = math.sqrt(INNER * INNER - DEPTH * DEPTH)
VEG = 0.6  # vegetation scale: smaller plants = a bigger-feeling world

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ------------------------------------------------------------------ helpers
def fbm(x, y, z, oct=4):
    a, f, s = 0.5, 1.0, 0.0
    for _ in range(oct):
        s += a * noise.noise(Vector((x * f, y * f, z * f)))
        a *= 0.5
        f *= 2.03
    return s

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def poly_dist(px, py, pts):
    best = 1e9
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy or 1
        u = max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / l2))
        dx, dy = ax + vx * u - px, ay + vy * u - py
        best = min(best, dx * dx + dy * dy)
    return math.sqrt(best)

def catmull(pts, n):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out

# ------------------------------------------------------------------ layout
# A central mountain; the waterfall drops off its front face into a lake;
# a stream leaves the lake to the right, under a bridge; paths wind through
# groves and meadows to two open pavilions; low hills ring the back.
FALL_X = 0.0

def fall_x(y):
    """The main falls' line wanders a little as it comes down the face."""
    return FALL_X + 0.011 * math.sin(y * 23 + 0.8) + 0.006 * math.sin(y * 51)

# Three falls, one from each peak: (name, x(y) along its line, top y, width scale, tier step)
FALLS = [
    ('main', fall_x, 0.0, 1.35, 0.1),
    ('west', lambda y: -0.19 + (0.03 - y) * 0.26 + 0.007 * math.sin(y * 31), 0.03, 0.6, 0.07),
    ('east', lambda y: 0.2 - (0.05 - y) * 0.19 + 0.006 * math.sin(y * 29 + 2), 0.05, 0.5, 0.07),
]

def fall_weight(x, y, spread=0.0012, pad=0.05):
    """1 on a falls line, falling off to 0 across it; 0 above its source."""
    w = 0.0
    for _, fx, top, sc, _ in FALLS:
        w = max(w, math.exp(-((x - fx(y)) ** 2) / (spread * sc)) * smoothstep(top + pad, top - 0.1, y))
    return w
LAKE = (0.0, -0.4, 0.2, 0.12)            # centre x, y, radius x, radius y
LAKE_Z = GROUND + 0.012
# The stream leaves the lake, bends toward the viewer, then runs up the right
# side into a small reed pond. It runs front-to-back where the bridge crosses,
# so the bridge is seen side-on from the default view.
POND = (0.6, -0.03, 0.085, 0.07)
STREAM = catmull([(0.17, -0.45), (0.29, -0.52), (0.43, -0.52), (0.56, -0.43), (0.62, -0.28), (0.62, -0.14), (0.6, -0.08)], 10)
PATHS = [
    catmull([(-0.6, -0.55), (-0.42, -0.5), (-0.3, -0.53), (-0.2, -0.5), (-0.1, -0.56), (0.05, -0.6), (0.2, -0.6), (0.3, -0.56), (0.32, -0.45)], 6),  # front, past the lake, over the stepping stones
    catmull([(0.32, -0.45), (0.37, -0.3), (0.45, -0.23), (0.52, -0.21), (0.57, -0.21), (0.62, -0.21), (0.67, -0.21), (0.72, -0.21), (0.77, -0.13), (0.74, 0.04)], 6),   # over the bridge
    catmull([(-0.42, -0.5), (-0.6, -0.2), (-0.58, 0.18), (-0.36, 0.5), (0.0, 0.64), (0.36, 0.52), (0.62, 0.24), (0.74, 0.04)], 6),  # around the back
    catmull([(-0.6, -0.12), (-0.5, -0.06), (-0.4, -0.04), (-0.2 + math.cos(math.radians(215)) * 0.25, 0.12 + math.sin(math.radians(215)) * 0.25)], 5),  # spur to the cave
    catmull([(-0.56, 0.26), (-0.48, 0.28)], 3),  # garden gate
]
BRIDGE = (0.62, -0.21)

def _cleft(a, b):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    l = math.hypot(b[0] - a[0], b[1] - a[1])
    return (mx, my), ((b[0] - a[0]) / l, (b[1] - a[1]) / l)
CLEFTS = [_cleft((0.0, 0.06), (0.21, 0.15)), _cleft((0.0, 0.06), (-0.2, 0.12))]

# Cave: an alcove cut into the west peak's flank, facing out (south-west).
CAVE_DIR = (math.cos(math.radians(215)), math.sin(math.radians(215)))
CAVE = (-0.2 + CAVE_DIR[0] * 0.2, 0.12 + CAVE_DIR[1] * 0.2)
TOWER = (0.47, 0.34)
WELL = (-0.41, -0.29)
GARDEN = (-0.4, 0.3, 0.5)     # x, y, facing
# Everything built: (x, y, keep-clear radius) for plants and moss.
STRUCTS = []
STEP_CROSSING = (0.31, -0.51)
PAVILIONS = [(-0.27, -0.6, 0.4, 'slate'), (0.0, 0.66, math.pi, 'terracotta')]  # x, y, facing, style
MASSIF = [(0.0, 0.06, 0.56, 0.33), (-0.2, 0.12, 0.38, 0.23), (0.21, 0.15, 0.42, 0.24)]
RIDGE = [(math.cos(a) * 0.78, math.sin(a) * 0.78, 0.1 + 0.06 * math.sin(a * 3.1), 0.2) for a in [math.radians(d) for d in range(30, 160, 26)]]

def terraced(h, step=0.05):
    q = math.floor(h / step) * step
    return q + ((h - q) / step) ** 4 * step

def lake_d(x, y):
    return math.hypot((x - LAKE[0]) / LAKE[2], (y - LAKE[1]) / LAKE[3])

def pond_d(x, y):
    return math.hypot((x - POND[0]) / POND[2], (y - POND[1]) / POND[3])

def strata(h, x, y):
    """Irregular rock strata: layers of varying thickness that dip across the
    massif, with ledges that come and go instead of even rings."""
    dip = 0.06 * x + 0.035 * y + 0.018 * fbm(x * 4 + 3, 2, y * 4, 3)
    w = h + dip
    step = 0.032 + 0.03 * (fbm(w * 9, 5, 0, 2) + 0.5)
    q = math.floor(w / step) * step
    t = (w - q) / step
    terr = q + t ** 3.5 * step
    keep = 0.45 + 0.55 * smoothstep(-0.2, 0.25, fbm(x * 7, 4, y * 7, 3))  # ledges fade in and out
    return h - (w - terr) * keep

def cave_local(x, y):
    """(into the mountain, across) coordinates relative to the cave mouth."""
    dx, dy = x - CAVE[0], y - CAVE[1]
    return -(dx * CAVE_DIR[0] + dy * CAVE_DIR[1]), -dx * CAVE_DIR[1] + dy * CAVE_DIR[0]

def cave_dark(x, y):
    return 0.0
    into, across = cave_local(x, y)
    return smoothstep(-0.004, 0.012, into) * smoothstep(0.03, 0.015, abs(across)) * smoothstep(0.05, 0.03, into)

def path_d(x, y):
    return min(poly_dist(x, y, p) for p in PATHS)

def massif_h(x, y):
    h = 0.0
    for px, py, ph, pr in MASSIF:
        r = math.hypot(x - px, (y - py) * 1.05) / pr
        if r < 1:
            h = max(h, ph * (1 - r ** 1.3) ** 1.2)
    if h > 0:
        ridged = 1 - abs(fbm(x * 6 + 7, 1, y * 6, 4)) * 2
        gullies = abs(fbm(math.atan2(y - 0.06, x) * 2.2, 3, h * 3, 3))  # vertical erosion runnels
        h = h * (0.88 + ridged * 0.16) * (0.95 + gullies * 0.1)
        h = strata(h, x, y)
        # A gorge on the front face where the falls drop.
        # Gorge for the falls, cut into three tiers: flat plunge pools with
        # near-vertical drops between them.
        for _, fx, top, sc, step in FALLS:
            chan = math.exp(-((x - fx(y)) ** 2) / (0.0012 * sc)) * smoothstep(top + 0.05, top - 0.1, y)
            if chan > 0.01:
                cut = h * (1 - 0.16 * chan)
                q = math.floor(cut / step) * step
                tier = q + ((cut - q) / step) ** 7 * step
                h = cut + (tier - cut) * min(1, chan * 1.6)
        # Clefts between the peaks, spanned by rope bridges.
        for (mx, my), (dx, dy) in CLEFTS:
            along = (x - mx) * dx + (y - my) * dy
            perp = abs(-(x - mx) * dy + (y - my) * dx)
            h -= 0.15 * math.exp(-(along * along) / 0.0008) * smoothstep(0.1, 0.035, perp)
        h = max(h, 0.0)
    r2 = 0.0
    for px, py, ph, pr in RIDGE:
        r = math.hypot(x - px, y - py) / pr
        if r < 1:
            r2 = max(r2, ph * (1 - r * r) ** 1.5 * (0.8 + fbm(x * 5, 9, y * 5, 3) * 0.5))
    return max(h, r2)

CAVE_FLOOR = 0.0  # set after the terrain function exists

def ground_at(x, y):
    r = math.hypot(x, y) / EDGE
    edge = max(0.0, 1 - min(1.0, r) ** 6)
    h = 0.035 + fbm(x * 3.2, 0.5, y * 3.2) * 0.045
    h += massif_h(x, y)
    sd = poly_dist(x, y, STREAM)
    h -= 0.03 * math.exp(-(sd * sd) / 0.0018)
    ld = lake_d(x, y)
    h -= 0.06 * smoothstep(1.25, 0.7, ld)
    h -= 0.045 * smoothstep(1.3, 0.6, pond_d(x, y))
    h -= 0.012 * math.exp(-(path_d(x, y) ** 2) / 0.0006)  # paths worn slightly in
    z = GROUND + h * edge
    zmax = math.sqrt(max(0.0, INNER * INNER * 0.88 - x * x - y * y))
    return min(z, zmax)

_cf = None
def _init_cave_floor():
    global CAVE_FLOOR, CAVE
    # Walk out from the west peak until we reach its foot, then stand just in front.
    # The mouth sits on the peak's flank where the rock is ~0.09 tall.
    r = 0.06
    while r < 0.35 and massif_h(-0.2 + CAVE_DIR[0] * r, 0.12 + CAVE_DIR[1] * r) > 0.09:
        r += 0.003
    CAVE = (-0.2 + CAVE_DIR[0] * r, 0.12 + CAVE_DIR[1] * r)
    # Cave floor at the level of the ground just outside the mouth.
    CAVE_FLOOR = 0.0
    CAVE_FLOOR = (ground_at(CAVE[0] + CAVE_DIR[0] * 0.012, CAVE[1] + CAVE_DIR[1] * 0.012) - GROUND)
_init_cave_floor()

def slope_at(x, y, e=0.01):
    return math.hypot(ground_at(x + e, y) - ground_at(x - e, y), ground_at(x, y + e) - ground_at(x, y - e)) / (2 * e)

def in_water(x, y, margin=0.0):
    return poly_dist(x, y, STREAM) < 0.035 + margin or lake_d(x, y) < 1.0 + margin * 6 or pond_d(x, y) < 1.0 + margin * 10

def ok(x, y, *, water=0.02, steps=0.04, max_slope=0.45, edge=0.93, path=0.035, build=0.012):
    if math.hypot(x, y) > EDGE * edge:
        return False
    if fall_weight(x, y, 0.004, 0.06) > 0.12:
        return False
    if in_water(x, y, water) or path_d(x, y) < path:
        return False
    if any(math.hypot(x - sx, y - sy) < r + build * 0.5 for sx, sy, r in STRUCTS):
        return False
    return slope_at(x, y) < max_slope

def rand_disc(edge=0.92):
    a = random.uniform(0, math.tau)
    r = math.sqrt(random.random()) * EDGE * edge
    return math.cos(a) * r, math.sin(a) * r

# ------------------------------------------------------------------ materials
def img(name, cs):
    im = bpy.data.images.load(os.path.join(TEX, name + '.webp'), check_existing=True)
    im.colorspace_settings.name = cs
    return im

def terrain_material():
    m = bpy.data.materials.new('terrain')
    nt = m.node_tree if m.node_tree else None
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.92
    tc = N.new('ShaderNodeTexCoord')
    def boxtex(name, cs, scale):
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale,) * 3
        L.new(tc.outputs['Object'], mp.inputs['Vector'])
        t = N.new('ShaderNodeTexImage'); t.image = img(name, cs); t.projection = 'BOX'; t.projection_blend = 0.3
        L.new(mp.outputs['Vector'], t.inputs['Vector'])
        return t
    rock = boxtex('mossy_rock_diff', 'sRGB', 2.2)
    rockn = boxtex('mossy_rock_nor', 'Non-Color', 2.2)
    moss = boxtex('aerial_grass_rock_diff', 'sRGB', 3.0)
    peb = boxtex('ganges_river_pebbles_diff', 'sRGB', 9.0)
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Hue'].default_value = 0.56; hsv.inputs['Saturation'].default_value = 1.5; hsv.inputs['Value'].default_value = 0.85
    L.new(moss.outputs['Color'], hsv.inputs['Color'])
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.62; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.82; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    north = N.new('ShaderNodeMath'); north.operation = 'MULTIPLY_ADD'; north.inputs[1].default_value = 0.22
    L.new(sep.outputs['Y'], north.inputs[0]); L.new(sep.outputs['Z'], north.inputs[2])
    L.new(north.outputs[0], ramp.inputs['Fac'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(ramp.outputs['Color'], mix.inputs['Factor']); L.new(rock.outputs['Color'], mix.inputs[6]); L.new(hsv.outputs['Color'], mix.inputs[7])
    attr = N.new('ShaderNodeAttribute'); attr.attribute_name = 'bed'
    mix2 = N.new('ShaderNodeMix'); mix2.data_type = 'RGBA'
    wet = N.new('ShaderNodeMix'); wet.data_type = 'RGBA'; wet.blend_type = 'MULTIPLY'; wet.inputs['Factor'].default_value = 1
    wet.inputs[7].default_value = (0.42, 0.4, 0.36, 1)  # wet pebbles are darker
    L.new(peb.outputs['Color'], wet.inputs[6])
    L.new(attr.outputs['Fac'], mix2.inputs['Factor']); L.new(mix.outputs[2], mix2.inputs[6]); L.new(wet.outputs[2], mix2.inputs[7])
    # Paths: packed earth with fine gravel.
    dirt = boxtex('ganges_river_pebbles_diff', 'sRGB', 22.0)
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 0.7
    tint.inputs[7].default_value = (0.62, 0.48, 0.34, 1)
    L.new(dirt.outputs['Color'], tint.inputs[6])
    pattr = N.new('ShaderNodeAttribute'); pattr.attribute_name = 'path'
    mix3 = N.new('ShaderNodeMix'); mix3.data_type = 'RGBA'
    L.new(pattr.outputs['Fac'], mix3.inputs['Factor']); L.new(mix2.outputs[2], mix3.inputs[6]); L.new(tint.outputs[2], mix3.inputs[7])
    wattr = N.new('ShaderNodeAttribute'); wattr.attribute_name = 'wet'
    dark = N.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
    dark.inputs[7].default_value = (0.42, 0.44, 0.42, 1)
    L.new(wattr.outputs['Fac'], dark.inputs['Factor']); L.new(mix3.outputs[2], dark.inputs[6])
    L.new(dark.outputs[2], b.inputs['Base Color'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.92; rr.inputs['To Max'].default_value = 0.25
    L.new(wattr.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8
    L.new(rockn.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m

# ------------------------------------------------------------------ layer 1: soil
def build_soil():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=160, ring_count=64, radius=INNER)
    o = bpy.context.object; o.name = 'soil'
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > GROUND + 0.002], context='VERTS')
    bm.to_mesh(o.data); bm.free()
    m = bpy.data.materials.new('soil'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.07; L.new(nz.outputs['Fac'], mul.inputs[0])
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'; L.new(sep.outputs['Z'], add.inputs[0]); L.new(mul.outputs[0], add.inputs[1])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -INNER; mr.inputs['From Max'].default_value = GROUND
    L.new(add.outputs[0], mr.inputs['Value'])
    ramp = N.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.55, 0.5, 0.44, 1)       # pale gravel
    mid = e.new(0.38); mid.color = (0.33, 0.29, 0.25, 1)          # grey grit
    lo = e.new(0.46); lo.color = (0.2, 0.12, 0.06, 1)             # loam
    e[1].position = 1.0; e[1].color = (0.12, 0.07, 0.035, 1)      # dark topsoil
    L.new(mr.outputs['Result'], ramp.inputs['Fac'])
    vor = N.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 160; L.new(tc.outputs['Object'], vor.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.45
    L.new(ramp.outputs['Color'], mx.inputs[6]); L.new(vor.outputs['Color'], mx.inputs[7]); L.new(mx.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.95
    o.data.materials.append(m)
    return o

# ------------------------------------------------------------------ layer 2: terrain
def build_terrain():
    RINGS, SEG = 220, 420
    verts, faces, bed = [(0, 0, ground_at(0, 0))], [], [(0.0, 0.0, 0.0)]
    for i in range(1, RINGS + 1):
        rr = (i / RINGS) ** 0.9 * EDGE
        for j in range(SEG):
            a = j / SEG * math.tau
            x, y = math.cos(a) * rr, math.sin(a) * rr
            verts.append((x, y, ground_at(x, y)))
            sd = poly_dist(x, y, STREAM)
            jag = fbm(x * 30, 2, y * 30, 2) * 0.12
            b_ = max(min(1, max(0, 1 - sd / 0.04)), smoothstep(1.16 + jag, 1.0, lake_d(x, y)), smoothstep(1.22 + jag, 1.0, pond_d(x, y)))
            pa = smoothstep(0.03, 0.016, path_d(x, y))
            wt = fall_weight(x, y, 0.0025, 0.06) * smoothstep(LAKE[1] + 0.02, LAKE[1] + 0.12, y)
            wt = max(wt, cave_dark(x, y))
            bed.append((b_, pa, wt))
    for j in range(SEG):
        faces.append((0, 1 + j, 1 + (j + 1) % SEG))
    for i in range(1, RINGS):
        for j in range(SEG):
            a = 1 + (i - 1) * SEG + j; b = 1 + (i - 1) * SEG + (j + 1) % SEG
            faces.append((a, a + SEG, b + SEG, b))
    me = bpy.data.meshes.new('terrain'); me.from_pydata(verts, [], faces); me.shade_smooth()
    attr = me.color_attributes.new('bed', 'FLOAT_COLOR', 'POINT')
    pat = me.color_attributes.new('path', 'FLOAT_COLOR', 'POINT')
    wet = me.color_attributes.new('wet', 'FLOAT_COLOR', 'POINT')
    for i, (v, p, w) in enumerate(bed):
        attr.data[i].color = (v, v, v, 1)
        pat.data[i].color = (p, p, p, 1)
        wet.data[i].color = (w, w, w, 1)
    # Planar UV over the disc, used for the lighting bake.
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / (2 * EDGE) + 0.5, co.y / (2 * EDGE) + 0.5)
    o = bpy.data.objects.new('terrain', me); scene.collection.objects.link(o)
    me.materials.append(terrain_material())
    return o

# ------------------------------------------------------------------ layer 3: water
def ribbon(name, pts, width_fn, z_fn, mat, uvs=False):
    verts, faces, uvd = [], [], []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[min(len(pts) - 1, i + 1)]; bx, by = pts[max(0, i - 1)]
        tx, ty = ax - bx, ay - by; tl = math.hypot(tx, ty) or 1
        w = width_fn(i, len(pts)); z = z_fn(x, y)
        for s in (-1, 1):
            verts.append((x - ty / tl * w * s, y + tx / tl * w * s, z)); uvd.append((s * 0.5 + 0.5, i / (len(pts) - 1)))
        if i:
            a = (i - 1) * 2; faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    if uvs:
        uv = me.uv_layers.new()
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvd[me.loops[li].vertex_index]
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); me.materials.append(mat)
    return o

def water_material():
    wm = bpy.data.materials.new('water'); wm.use_nodes = True
    nt = wm.node_tree; N = nt.nodes; b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.02, 0.05, 0.045, 1); b.inputs['Roughness'].default_value = 0.012
    b.inputs['Transmission Weight'].default_value = 0.45; b.inputs['IOR'].default_value = 1.33
    # Gentle ripples.
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08
    nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return wm

def curtain_material():
    """Falling water as one continuous sheet: brighter, whiter streaks on the
    drops; paler flowing water on the treads. Streaks change brightness, not
    opacity, so there are no see-through gaps between them."""
    fm = bpy.data.materials.new('waterfall'); fm.use_nodes = True
    nt = fm.node_tree; N = nt.nodes; L = nt.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['UV'], sep.inputs['Vector'])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (30, 1.4, 1)
    L.new(tc.outputs['UV'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.6
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    streak = N.new('ShaderNodeMapRange'); streak.inputs['From Min'].default_value = 0.35; streak.inputs['From Max'].default_value = 0.65
    L.new(nz.outputs['Fac'], streak.inputs['Value'])
    edge = N.new('ShaderNodeMath'); edge.operation = 'PINGPONG'; edge.inputs[1].default_value = 0.5
    L.new(sep.outputs['X'], edge.inputs[0])
    edge2 = N.new('ShaderNodeMath'); edge2.operation = 'MULTIPLY'; edge2.inputs[1].default_value = 4.0; edge2.use_clamp = True
    L.new(edge.outputs[0], edge2.inputs[0])
    dr = N.new('ShaderNodeAttribute'); dr.attribute_name = 'drop'
    # Opacity: 0.8 on treads, 0.85-1 on drops (never gappy), soft at the sides.
    dop = N.new('ShaderNodeMapRange'); dop.inputs['To Min'].default_value = 0.85; dop.inputs['To Max'].default_value = 1.0
    L.new(streak.outputs['Result'], dop.inputs['Value'])
    am = N.new('ShaderNodeMix'); am.data_type = 'FLOAT'; am.inputs[2].default_value = 0.8
    L.new(dr.outputs['Fac'], am.inputs['Factor']); L.new(dop.outputs['Result'], am.inputs[3])
    a = N.new('ShaderNodeMath'); a.operation = 'MULTIPLY'; L.new(am.outputs[0], a.inputs[0]); L.new(edge2.outputs[0], a.inputs[1])
    L.new(a.outputs[0], b.inputs['Alpha'])
    # Colour.
    dropc = N.new('ShaderNodeMix'); dropc.data_type = 'RGBA'
    dropc.inputs[6].default_value = (0.62, 0.72, 0.75, 1); dropc.inputs[7].default_value = (0.97, 0.99, 1.0, 1)
    L.new(streak.outputs['Result'], dropc.inputs['Factor'])
    treadc = N.new('ShaderNodeMix'); treadc.data_type = 'RGBA'
    treadc.inputs[6].default_value = (0.22, 0.32, 0.33, 1); treadc.inputs[7].default_value = (0.55, 0.66, 0.68, 1)
    L.new(streak.outputs['Result'], treadc.inputs['Factor'])
    cm = N.new('ShaderNodeMix'); cm.data_type = 'RGBA'
    L.new(dr.outputs['Fac'], cm.inputs['Factor']); L.new(treadc.outputs[2], cm.inputs[6]); L.new(dropc.outputs[2], cm.inputs[7])
    L.new(cm.outputs[2], b.inputs['Base Color'])
    em = N.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 0.35
    L.new(dr.outputs['Fac'], em.inputs[0])
    em2 = N.new('ShaderNodeMath'); em2.operation = 'MULTIPLY'; L.new(em.outputs[0], em2.inputs[0]); L.new(streak.outputs['Result'], em2.inputs[1])
    L.new(em2.outputs[0], b.inputs['Emission Strength'])
    b.inputs['Emission Color'].default_value = (0.9, 0.95, 1.0, 1)
    rgh = N.new('ShaderNodeMapRange'); rgh.inputs['To Min'].default_value = 0.04; rgh.inputs['To Max'].default_value = 0.3
    L.new(dr.outputs['Fac'], rgh.inputs['Value']); L.new(rgh.outputs['Result'], b.inputs['Roughness'])
    return fm

def curtain(name, lip, drop_to_z, width0, width1, outward, mat, segs=36, cols=6):
    """A sheet of falling water from a lip, arcing outward (toward -y) and
    widening as it falls; slightly convex across."""
    lx, ly, lz = lip
    verts, faces, uvs = [], [], []
    H = lz - drop_to_z
    for i in range(segs + 1):
        t = i / segs
        z = lz - H * t
        y = ly - outward * math.sqrt(t)
        w = width0 + (width1 - width0) * t
        for j in range(cols + 1):
            u = j / cols - 0.5
            bulge = 0.004 * (1 - (2 * u) ** 2)
            verts.append((lx + u * w, y - bulge, z)); uvs.append((j / cols, t))
            if i and j:
                a = (i - 1) * (cols + 1) + j - 1
                faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.shade_smooth()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); me.materials.append(mat)
    return o

def foam(name, x, y, z, rx, ry):
    """Churned white water: a noise-broken patch with no clean outline."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    warp = N.new('ShaderNodeTexNoise'); warp.inputs['Scale'].default_value = 3; warp.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Generated'], warp.inputs['Vector'])
    mixv = N.new('ShaderNodeMix'); mixv.data_type = 'VECTOR'; mixv.inputs['Factor'].default_value = 0.35
    L.new(tc.outputs['Generated'], mixv.inputs[4]); L.new(warp.outputs['Color'], mixv.inputs[5])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (-1.0, -1.0, 0.0); mp.inputs['Scale'].default_value = (2, 2, 0)
    L.new(mixv.outputs[1], mp.inputs['Vector'])
    grad = N.new('ShaderNodeTexGradient'); grad.gradient_type = 'SPHERICAL'
    L.new(mp.outputs['Vector'], grad.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 160; nz.inputs['Detail'].default_value = 10; nz.inputs['Roughness'].default_value = 0.7
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(nz.outputs['Fac'], mul.inputs[0]); L.new(grad.outputs['Fac'], mul.inputs[1])
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.75, 0.75, 0.75, 1)
    L.new(mul.outputs[0], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Alpha'])
    b.inputs['Base Color'].default_value = (0.95, 0.97, 0.98, 1); b.inputs['Roughness'].default_value = 0.5
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=8, size=2, location=(x, y, z))
    o = bpy.context.object; o.name = name; o.scale = (rx, ry, 1); o.data.materials.append(m)
    return o

def mist(name, x, y, z, size, density):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    vol = N.new('ShaderNodeVolumePrincipled'); vol.inputs['Color'].default_value = (1, 1, 1, 1)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    grad = N.new('ShaderNodeTexGradient'); grad.gradient_type = 'SPHERICAL'
    L.new(tc.outputs['Object'], grad.inputs['Vector'])
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(nz.outputs['Fac'], mul.inputs[0]); L.new(grad.outputs['Fac'], mul.inputs[1])
    d = N.new('ShaderNodeMath'); d.operation = 'MULTIPLY'; d.inputs[1].default_value = density
    L.new(mul.outputs[0], d.inputs[0]); L.new(d.outputs[0], vol.inputs['Density'])
    L.new(vol.outputs['Volume'], N['Material Output'].inputs['Volume'])
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x, y, z))
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(m)
    return o

def spring(name, x, y, z, sc):
    """A dark, wet fissure where a falls emerges: a sunken dark slot with the
    rock's own material around it."""
    dark = bpy.data.materials.get('spring_dark')
    if not dark:
        dark = bpy.data.materials.new('spring_dark'); dark.use_nodes = True
        b = dark.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.01, 0.012, 0.012, 1); b.inputs['Roughness'].default_value = 0.15
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=(x, y + 0.004, z + 0.002))
    o = bpy.context.object; o.name = name; o.scale = (0.009 * sc + 0.004, 0.006, 0.012 * sc + 0.004); o.data.materials.append(dark); o['tag'] = 'structure'

def build_fall(name, fx, y_top, sc, cm):
    """A falls that cascades down its tiered gorge, following the rock, then
    plunges into the lake. White and lifted off the rock where it drops; dark
    and glassy on the pool treads."""
    y = y_top
    prof = []
    while ground_at(fx(y), y) > LAKE_Z + 0.002 and y > LAKE[1]:
        prof.append((y, ground_at(fx(y), y)))
        y -= 0.002
    if len(prof) < 8:
        return
    # Carry on past the shore and plunge into the water.
    ly, lz = prof[-1]
    for k in range(1, 9):
        prof.append((ly - 0.003 * k, lz + (LAKE_Z - 0.016 - lz) * (k / 8) ** 0.8))
    base_y = prof[-1][0]
    verts, faces, uvs, drops = [], [], [], []
    cols = 8
    total = len(prof)
    raw = [abs(prof[max(0, i - 1)][1] - prof[min(total - 1, i + 1)][1]) / 0.004 for i in range(total)]
    steep = [sum(raw[max(0, i - 3):i + 4]) / len(raw[max(0, i - 3):i + 4]) for i in range(total)]
    for i, (py, pz) in enumerate(prof):
        t = i / max(1, total - 1)
        d = smoothstep(0.4, 1.4, steep[i])
        w = (0.016 + 0.026 * t) * sc * (1.0 + 0.3 * (1 - d)) * (1 + 0.06 * math.sin(i * 0.7) + 0.03 * math.sin(i * 2.3))
        x0 = fx(py)
        for j in range(cols + 1):
            u = j / cols - 0.5
            gz = max(ground_at(x0 + u * w, py), pz)
            lift = 0.006 + 0.007 * d          # falling water stands off the rock
            verts.append((x0 + u * w, py - 0.004 * (1 - (2 * u) ** 2) - 0.006 * d, gz + lift + 0.003 * (1 - (2 * u) ** 2)))
            uvs.append((j / cols, t)); drops.append(d)
            if i and j:
                a_ = (i - 1) * (cols + 1) + j - 1
                faces.append((a_, a_ + 1, a_ + cols + 2, a_ + cols + 1))
    me = bpy.data.meshes.new('waterfall_' + name); me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.shade_smooth()
    da = me.color_attributes.new('drop', 'FLOAT_COLOR', 'POINT')
    for k, d in enumerate(drops):
        da.data[k].color = (d, d, d, 1)
    fo = bpy.data.objects.new('waterfall_' + name, me); scene.collection.objects.link(fo); me.materials.append(cm)
    for i in range(3, total - 3):
        if prof[i - 3][1] - prof[i][1] > 0.025 and abs(prof[i][1] - prof[i + 3][1]) < 0.004:
            foam(f'foam_{name}{i}', fx(prof[i][0]), prof[i][0] - 0.006, prof[i][1] + 0.01, 0.024 * sc, 0.01 * sc)
    # Where the water hits the pool: churned foam and a contained plume of spray.
    foam(f'foam_{name}_lake', fx(base_y), base_y - 0.014, LAKE_Z + 0.002, 0.05 * sc, 0.035 * sc)
    # Thick spray: a dense plume at the plunge and a softer cloud rising up the drop.
    mist(f'mist_{name}', fx(base_y), base_y - 0.006, LAKE_Z + 0.03, (0.075 * sc, 0.06 * sc, 0.07 * sc), 90)
    mist(f'mist_{name}_rise', fx(base_y + 0.03), base_y + 0.02, LAKE_Z + 0.08, (0.06 * sc, 0.05 * sc, 0.09 * sc), 25)
    # The source: a dark wet cleft in the rock that the water spills out of.
    ty, tz = prof[0]
    spring(f'spring_{name}', fx(ty), ty, tz, sc)

def build_water():
    wm = water_material()
    for nm, (cx, cy, rx, ry), z in (('water_lake', LAKE, LAKE_Z), ('water_pond', POND, ground_at(POND[0], POND[1]) + 0.02)):
        bpy.ops.mesh.primitive_circle_add(vertices=96, radius=1, fill_type='NGON', location=(cx, cy, z))
        o = bpy.context.object; o.name = nm; o.scale = (rx * 1.12, ry * 1.12, 1)
        bpy.ops.object.transform_apply(scale=True); o.data.materials.append(wm)
    pond_z = ground_at(POND[0], POND[1]) + 0.02
    def stream_z(x, y):
        # Descend smoothly from the lake level to the pond level along the course.
        best = min(range(len(STREAM)), key=lambda k: (STREAM[k][0] - x) ** 2 + (STREAM[k][1] - y) ** 2)
        t = best / (len(STREAM) - 1)
        return max(ground_at(x, y) + 0.006, LAKE_Z + (pond_z - LAKE_Z) * t - 0.004)
    ribbon('water_stream', catmull(STREAM, 3), lambda i, n: 0.022 + 0.006 * math.sin(i * 0.37) + 0.004 * math.sin(i * 1.3), stream_z, wm)

    cm = curtain_material()
    for name, fx, top, sc, _ in FALLS:
        build_fall(name, fx, top, sc, cm)
    mist('mist_lake', LAKE[0], LAKE[1] + 0.04, LAKE_Z + 0.03, (0.24, 0.11, 0.035), 9)
    return None

# ------------------------------------------------------------------ structures
def wood_mat(name='wood', color=(0.23, 0.14, 0.08)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.75
    return m

def stone_mat(name):
    """Weathered stone: the scanned mossy-rock texture, darkened and desaturated."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (14, 14, 14)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    t = N.new('ShaderNodeTexImage'); t.image = img('mossy_rock_diff', 'sRGB'); t.projection = 'BOX'; t.projection_blend = 0.3
    L.new(mp.outputs['Vector'], t.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.35; hsv.inputs['Value'].default_value = 0.55
    L.new(t.outputs['Color'], hsv.inputs['Color']); L.new(hsv.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    return m

def box(name, loc, size, rot_z, mat, pitch=0.0, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.rotation_euler = (0, pitch, rot_z)
    if bevel:
        m = o.modifiers.new('bevel', 'BEVEL'); m.width = bevel; m.segments = 2
    o.data.materials.append(mat); o['tag'] = 'structure'
    bpy.ops.object.transform_apply(scale=True)
    return o

def hip_roof(name, x, y, z, half, peak, face, mat):
    """Curved hip roof: concave slopes that sweep out to upturned corners,
    given thickness, plus a finial."""
    n = 110
    verts, faces = [], []
    for i in range(n + 1):
        for j in range(n + 1):
            u = i / n * 2 - 1; v = j / n * 2 - 1
            m = max(abs(u), abs(v))
            zz = peak * (1 - m) ** 1.7                      # concave sweep
            zz += 0.006 * (abs(u * v) ** 3)                  # upturned corners
            along = v if abs(u) >= abs(v) else u          # position along the eave
            zz += 0.0016 * (0.5 - abs(((m * 12) % 1) - 0.5))           # tile courses
            zz += 0.0013 * abs(math.sin(along * math.pi * 9 * (1 - m * 0.4)))  # rounded tiles
            cu, cv = u * half, v * half
            c, s_ = math.cos(face), math.sin(face)
            verts.append((x + cu * c - cv * s_, y + cu * s_ + cv * c, z + zz))
            if i and j:
                a = (i - 1) * (n + 1) + j - 1
                faces.append((a, a + n + 1, a + n + 2, a + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.shade_smooth()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); me.materials.append(mat)
    sol = o.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.004; sol.offset = -1
    o['tag'] = 'structure'
    # Finial.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.004, location=(x, y, z + peak + 0.004))
    f = bpy.context.object; f.data.materials.append(mat); f['tag'] = 'structure'
    return o

def build_pavilions():
    STYLES = {
        # slate roof, dark stained timber
        'slate': dict(wood=(0.15, 0.09, 0.05), beam=(0.09, 0.055, 0.035), roof=(0.03, 0.033, 0.038), rough=0.5),
        # terracotta tiles, red-lacquered posts
        'terracotta': dict(wood=(0.2, 0.025, 0.016), beam=(0.2, 0.035, 0.025), roof=(0.36, 0.12, 0.05), rough=0.7),
    }
    stone = stone_mat('plinth')
    for x, y, face, style in PAVILIONS:
        st = STYLES[style]
        wood = wood_mat(f'pav_wood_{style}', st['wood']); beam = wood_mat(f'pav_beam_{style}', st['beam'])
        roofm = wood_mat(f'roof_{style}', st['roof']); roofm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = st['rough']
        if style == 'terracotta':
            wood.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.35  # lacquer
        STRUCTS.append((x, y, 0.07))
        g = max(ground_at(x + dx, y + dy) for dx in (-0.04, 0.04) for dy in (-0.04, 0.04))
        S = 0.074; H = 0.058
        c, s_ = math.cos(face), math.sin(face)
        P = lambda ox, oy: (x + ox * c - oy * s_, y + ox * s_ + oy * c)
        box('pav_plinth', (x, y, g - 0.004), (S * 1.18, S * 1.18, 0.016), face, stone, bevel=0.002)
        box('pav_floor', (x, y, g + 0.006), (S * 1.06, S * 1.06, 0.005), face, wood, bevel=0.001)
        # Front step.
        sx, sy = P(0, -S * 0.68)
        box('pav_step', (sx, sy, g - 0.002), (S * 0.4, 0.018, 0.008), face, stone, bevel=0.001)
        posts = []
        for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            px, py = P(dx * S * 0.44, dy * S * 0.44)
            box('pav_post', (px, py, g + 0.008 + H / 2), (0.0055, 0.0055, H), face, wood, bevel=0.0008)
            posts.append((px, py))
        # Beams and a low rail on three sides (open at the front).
        for (ax, ay), (bx2, by2), side in zip(posts, posts[1:] + posts[:1], range(4)):
            mx, my = (ax + bx2) / 2, (ay + by2) / 2
            ang = math.atan2(by2 - ay, bx2 - ax)
            ln = math.hypot(bx2 - ax, by2 - ay)
            box('pav_beam', (mx, my, g + 0.008 + H - 0.003), (ln + 0.008, 0.005, 0.006), ang, beam, bevel=0.0008)
            if side != 0:
                box('pav_rail', (mx, my, g + 0.008 + 0.018), (ln, 0.0035, 0.0035), ang, wood)
                for k in range(1, 6):
                    t = k / 6
                    box('pav_baluster', (ax + (bx2 - ax) * t, ay + (by2 - ay) * t, g + 0.008 + 0.009), (0.0018, 0.0018, 0.018), ang, wood)
        # A bench inside along the back.
        bx3, by3 = P(0, S * 0.3)
        box('pav_bench', (bx3, by3, g + 0.008 + 0.01), (S * 0.6, 0.012, 0.003), face, wood)
        hip_roof('pav_roof', x, y, g + 0.008 + H, S * 0.72, 0.034, face, roofm)

def build_bridge():
    wood = wood_mat('bridge_wood', (0.24, 0.15, 0.085))
    dark = wood_mat('bridge_beam', (0.13, 0.08, 0.045))
    bx, by = BRIDGE
    STRUCTS.append((bx, by, 0.1))
    # Align with the path, so it leads straight onto and off both ends.
    pth = PATHS[1]
    i = min(range(len(pth) - 1), key=lambda k: math.hypot(pth[k][0] - bx, pth[k][1] - by))
    tx, ty = pth[i + 1][0] - pth[i][0], pth[i + 1][1] - pth[i][1]
    ang = math.atan2(ty, tx)
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = -sa, ca                                # bridge's sideways axis
    L, W, N, ARCH = 0.15, 0.048, 15, 0.026
    ends = [ground_at(bx + ca * L / 2 * k, by + sa * L / 2 * k) for k in (-1, 1)]
    base = max(ends) + 0.004
    zf = lambda t: base + ARCH * (1 - (2 * t) ** 2)
    dz = lambda t: -8 * ARCH * t                     # derivative of the arch
    for k in range(N):
        t = k / (N - 1) - 0.5
        px, py = bx + ca * t * L, by + sa * t * L
        pitch = -math.atan(dz(t) / L)
        box('bridge_plank', (px, py, zf(t)), (L / N * 0.86, W * (1 + 0.04 * ((k * 7) % 3 - 1)), 0.0045), ang, wood, pitch=pitch, bevel=0.0006)
    for side in (-1, 1):
        ox, oy = nx * W / 2 * side, ny * W / 2 * side
        # Stringer under each edge and handrail above, following the arch.
        for k in range(N - 1):
            t0, t1 = k / (N - 1) - 0.5, (k + 1) / (N - 1) - 0.5; tm = (t0 + t1) / 2
            px, py = bx + ca * tm * L + ox * 0.9, by + sa * tm * L + oy * 0.9
            pitch = -math.atan(dz(tm) / L)
            box('bridge_stringer', (px, py, zf(tm) - 0.007), (L / (N - 1) * 1.04, 0.005, 0.009), ang, dark, pitch=pitch)
            px2, py2 = bx + ca * tm * L + ox, by + sa * tm * L + oy
            box('bridge_rail', (px2, py2, zf(tm) + 0.027), (L / (N - 1) * 1.04, 0.0042, 0.0042), ang, wood, pitch=pitch)
        for k in range(0, N, 4):
            t = k / (N - 1) - 0.5
            px, py = bx + ca * t * L + ox, by + sa * t * L + oy
            box('bridge_post', (px, py, zf(t) + 0.013), (0.0048, 0.0048, 0.03), ang, wood, bevel=0.0006)
    # Stone footings at each end.
    stone = stone_mat('footing')
    for k in (-1, 1):
        px, py = bx + ca * L / 2 * k * 0.98, by + sa * L / 2 * k * 0.98
        box('bridge_footing', (px, py, ground_at(px, py) + 0.002), (0.02, W * 1.25, 0.014), ang, stone, bevel=0.002)

def tube(name, pts, r, mat, seg=8):
    """A rope/branch: a curve with round bevel."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 2
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for k, (x, y, z) in enumerate(pts):
        sp.points[k].co = (x, y, z, 1)
    o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o); cu.materials.append(mat); o['tag'] = 'structure'
    return o

def rope_spans():
    """For each cleft: (main-side end, far end, deck height). Both ends sit at
    the same height: the lower of the two lips."""
    out = []
    for (mx, my), (dx, dy) in CLEFTS:
        reach = lambda sgn, k: ground_at(mx + dx * k * sgn, my + dy * k * sgn)
        lip = {sgn: max(reach(sgn, k / 200) for k in range(4, 20)) for sgn in (-1, 1)}
        target = min(lip.values()) - 0.004
        ends = []
        for sgn in (-1, 1):
            k = 0.015
            while k < 0.1 and reach(sgn, k) < target:
                k += 0.002
            ends.append((mx + dx * (k + 0.008) * sgn, my + dy * (k + 0.008) * sgn))
        out.append((ends[0], ends[1], target))
    return out

TUNNEL_R = (0.017, 0.024)  # half-width, height

def tunnel_axis():
    (a, _, za), (b, _, zb) = rope_spans()
    return Vector((a[0], a[1], za)), Vector((b[0], b[1], zb))

def in_tunnel(p, pad=0.0):
    A, B = tunnel_axis()
    ab = B - A; t = max(-0.25, min(1.25, (p - A).dot(ab) / ab.length_squared))
    floor = A.z + ab.z * max(0, min(1, t))
    q = A + ab * t
    side = Vector((-(ab.y), ab.x, 0)).normalized()
    across = (p - q).dot(side)
    up = p.z - floor
    if up < 0.001 or t < -0.25 or t > 1.25:
        return False
    return (across / (TUNNEL_R[0] + pad)) ** 2 + (up / (TUNNEL_R[1] + pad)) ** 2 < 1

def carve_tunnel(terrain):
    """Bore a walkway tunnel through the main peak, mouth to mouth, so the two
    rope bridges join one path through the mountain."""
    me = terrain.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(in_tunnel(v.co, 0.002) for v in f.verts)], context='FACES')
    bm.to_mesh(me); bm.free()
    A, B = tunnel_axis()
    ab = B - A; side = Vector((-(ab.y), ab.x, 0)).normalized()
    verts, faces = [], []
    NS, NA = 40, 20
    for i in range(NS + 1):
        t = -0.25 + 1.5 * i / NS
        q = A + ab * t
        floor = A.z + ab.z * max(0, min(1, t))
        for j in range(NA + 1):
            a = math.pi * j / NA
            jig = 1 + 0.12 * fbm(i * 0.4, j * 0.5, 3, 2)
            verts.append(tuple(Vector((q.x, q.y, floor)) + side * math.cos(a) * TUNNEL_R[0] * jig + Vector((0, 0, math.sin(a) * TUNNEL_R[1] * jig))))
            if i and j:
                k = (i - 1) * (NA + 1) + j - 1
                faces.append((k, k + 1, k + NA + 2, k + NA + 1))
    # Floor strip.
    base = len(verts)
    for i in range(NS + 1):
        t = -0.25 + 1.5 * i / NS
        q = A + ab * t; floor = A.z + ab.z * max(0, min(1, t))
        for sgn in (-1, 1):
            verts.append(tuple(Vector((q.x, q.y, floor + 0.0005)) + side * TUNNEL_R[0] * sgn))
        if i:
            k = base + (i - 1) * 2
            faces.append((k, k + 2, k + 3, k + 1))
    tm = bpy.data.meshes.new('tunnel'); tm.from_pydata(verts, [], faces)
    o = bpy.data.objects.new('tunnel', tm); scene.collection.objects.link(o); o['tag'] = 'structure'
    bm = bmesh.new(); bm.from_mesh(tm)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > ground_at(*f.calc_center_median().xy) + 0.001], context='FACES')
    bm.to_mesh(tm); bm.free()
    tm.shade_smooth()
    shade_like_mountain(o, 0.7)
    # Lanterns inside, so it glows from the bridges.
    for t in (0.3, 0.7):
        q = A + ab * t
        lp = bpy.data.lights.new('tunnel_lamp', 'POINT'); lp.energy = 0.05; lp.color = (1, 0.64, 0.32)
        lo = bpy.data.objects.new('tunnel_lamp', lp); lo.location = (q.x, q.y, q.z + 0.018); scene.collection.objects.link(lo)

def build_rope_bridges():
    plank = wood_mat('rope_plank', (0.2, 0.13, 0.075))
    rope = wood_mat('rope', (0.32, 0.26, 0.17)); rope.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
    for ((mx, my), (dx, dy)), (e0, e1, target) in zip(CLEFTS, rope_spans()):
        ends = [e0, e1]
        (ax, ay), (bx, by) = ends
        za = zb = target + 0.003
        for (ex, ey) in ends:  # small timber landing on each lip
            box('rope_landing', (ex, ey, target + 0.001), (0.026, 0.03, 0.004), math.atan2(dy, dx), plank, bevel=0.0005)
        L = math.hypot(bx - ax, by - ay); ang = math.atan2(by - ay, bx - ax)
        nx, ny = -math.sin(ang), math.cos(ang)
        W, N, SAG = 0.022, max(9, int(L / 0.009)), 0.012 + L * 0.06
        zf = lambda t: za + (zb - za) * t - SAG * 4 * t * (1 - t)
        for k in range(N):
            t = (k + 0.5) / N
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            slope = (zf(min(1, t + 0.01)) - zf(max(0, t - 0.01))) / (0.02 * L)
            box('rope_plank', (px, py, zf(t)), (L / N * 0.72, W, 0.003), ang, plank, pitch=-math.atan(slope))
        for side in (-1, 1):
            ox, oy = nx * W / 2 * side, ny * W / 2 * side
            hand = [(ax + (bx - ax) * t + ox, ay + (by - ay) * t + oy, zf(t) + 0.02) for t in [i / 24 for i in range(25)]]
            foot = [(ax + (bx - ax) * t + ox, ay + (by - ay) * t + oy, zf(t) - 0.001) for t in [i / 24 for i in range(25)]]
            tube('rope_hand', hand, 0.0012, rope); tube('rope_foot', foot, 0.001, rope)
            for k in range(1, 8):
                t = k / 8
                tube('rope_hanger', [foot[int(t * 24)], hand[int(t * 24)]], 0.0006, rope)
            for (ex, ey, ez) in ((ax + ox, ay + oy, za), (bx + ox, by + oy, zb)):
                box('rope_post', (ex, ey, ez + 0.012), (0.004, 0.004, 0.028), ang, plank, bevel=0.0006)

def cave_chamber():
    """Ellipsoid chamber behind the mouth: centre, radii (along, across, up), floor z."""
    cx, cy = CAVE
    dx, dy = CAVE_DIR
    floor = GROUND + CAVE_FLOOR
    C = Vector((cx - dx * 0.05, cy - dy * 0.05, floor + 0.012))
    return C, (0.066, 0.05, 0.05), floor

def in_chamber(p, pad=0.0):
    C, (ra, rc, ru), floor = cave_chamber()
    dx, dy = CAVE_DIR
    v = p - C
    a = v.x * dx + v.y * dy; c = -v.x * dy + v.y * dx
    return (a / (ra + pad)) ** 2 + (c / (rc + pad)) ** 2 + (v.z / (ru + pad)) ** 2 < 1 and p.z > floor + 0.001

def shade_like_mountain(o, darkness):
    """Give a mesh the terrain's own material, darkened (via the 'wet' channel)
    so cave and tunnel walls read as the same rock as the mountain."""
    o.data.materials.append(bpy.data.materials['terrain'])
    for nm, val in (('bed', 0.0), ('path', 0.0), ('wet', darkness)):
        a = o.data.color_attributes.new(nm, 'FLOAT_COLOR', 'POINT')
        for i in range(len(a.data)):
            a.data[i].color = (val, val, val, 1)

def carve_cave(terrain):
    """Open the mountain face: remove terrain inside the chamber, then build the
    chamber's rock walls only where they're inside the mountain."""
    me = terrain.data
    bm = bmesh.new(); bm.from_mesh(me)
    kill = [f for f in bm.faces if any(in_chamber(v.co, 0.002) for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    # Round the cut edge into the opening: relax the boundary outline, then
    # curl the rim and the ring of vertices behind it inward and down.
    bm.verts.ensure_lookup_table()
    C0, _, floor0 = cave_chamber()
    rim = {v for e in bm.edges if e.is_boundary and (e.verts[0].co.xy - Vector(CAVE)).length < 0.12 for v in e.verts}
    ring2 = {n for v in rim for e in v.link_edges for n in e.verts if n not in rim}
    for _ in range(4):  # smooth the outline so it isn't jagged
        new = {}
        for v in rim:
            nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in rim]
            if len(nb) == 2:
                new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items():
            v.co = c
    for vs, k in ((rim, 0.008), (ring2, 0.004)):
        for v in vs:
            d = (C0 - v.co); d.z = 0
            if d.length > 1e-6:
                v.co += d.normalized() * k
            v.co.z -= k * 0.4 if v.co.z > floor0 + 0.02 else 0.0
    bm.to_mesh(me); bm.free()
    C, (ra, rc, ru), floor = cave_chamber()
    dx, dy = CAVE_DIR
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=40, radius=1, location=(0, 0, 0))
    o = bpy.context.object; o.name = 'cave_chamber'; o['tag'] = 'structure'
    for v in o.data.vertices:
        n = v.co.normalized()
        k = 1 + 0.12 * fbm(n.x * 3 + 5, n.y * 3, n.z * 3, 4)
        a, c, u = n.x * ra * k, n.y * rc * k, n.z * ru * k
        wx, wy = C.x + a * dx - c * dy, C.y + a * dy + c * dx
        wz = max(C.z + u, floor)  # flat floor
        v.co = (wx, wy, wz)
    bm = bmesh.new(); bm.from_mesh(o.data)
    def outside(f):
        p = f.calc_center_median()
        return p.z > ground_at(p.x, p.y) + 0.001  # in open air: that's the mouth
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if outside(f)], context='FACES')
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # face inward
    bm.to_mesh(o.data); bm.free()
    o.data.shade_smooth()
    shade_like_mountain(o, 0.75)
    STRUCTS.append((CAVE[0], CAVE[1], 0.06))

def build_cave():
    """Inside the cave: candles on the floor and a ledge, a lantern at the mouth,
    stalagmites, a little chest."""
    C, (ra, rc, ru), floor = cave_chamber()
    dx, dy = CAVE_DIR
    ax_, ay_ = -dy, dx
    P = lambda along, across, z: (C.x + dx * along + ax_ * across, C.y + dy * along + ay_ * across, floor + z)
    wax = wood_mat('wax', (0.82, 0.76, 0.62)); wax.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.6
    flame = bpy.data.materials.new('flame'); flame.use_nodes = True
    fb = flame.node_tree.nodes['Principled BSDF']
    fb.inputs['Base Color'].default_value = (1, 0.7, 0.3, 1); fb.inputs['Emission Color'].default_value = (1, 0.6, 0.22, 1); fb.inputs['Emission Strength'].default_value = 40
    def candle(along, across, z0, hgt):
        x, y, z = P(along, across, z0)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0019, depth=hgt, location=(x, y, z + hgt / 2))
        c = bpy.context.object; c.data.materials.append(wax); c['tag'] = 'structure'
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.0011, location=(x, y, z + hgt + 0.0016))
        f = bpy.context.object; f.scale.z = 1.8; f.data.materials.append(flame)
        lp = bpy.data.lights.new('candle', 'POINT'); lp.energy = 0.025; lp.color = (1, 0.62, 0.3); lp.shadow_soft_size = 0.001
        lo = bpy.data.objects.new('candle_light', lp); lo.location = (x, y, z + hgt + 0.004); scene.collection.objects.link(lo)
    for along, across, hgt in [(-0.03, 0.02, 0.012), (-0.034, 0.012, 0.008), (-0.028, 0.026, 0.006), (-0.012, -0.03, 0.01), (-0.006, -0.034, 0.006), (0.012, -0.03, 0.007)]:
        candle(along, across, 0.0, hgt)
    # A rock ledge at the back with three more candles.
    stone = stone_mat('ledge')
    lx, ly, lz = P(-0.045, -0.004, 0.012)
    box('cave_ledge', (lx, ly, lz), (0.016, 0.05, 0.024), math.atan2(dy, dx), stone, bevel=0.003)
    for k, across in enumerate((-0.016, 0.0, 0.015)):
        candle(-0.045, across, 0.024, (0.007, 0.011, 0.006)[k])
    # Stalagmites.
    for along, across, hgt in [(-0.02, -0.04, 0.02), (-0.04, 0.035, 0.026), (0.0, 0.04, 0.014)]:
        x, y, z = P(along, across, 0)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.006, radius2=0.0005, depth=hgt, location=(x, y, z + hgt / 2))
        g = bpy.context.object; g.data.materials.append(stone); g['tag'] = 'structure'
    # A small wooden chest.
    wood = wood_mat('chest', (0.2, 0.11, 0.05))
    cx2, cy2, cz2 = P(-0.02, -0.018, 0.005)
    box('chest', (cx2, cy2, cz2), (0.014, 0.01, 0.009), math.atan2(dy, dx) + 0.3, wood, bevel=0.0008)
    # Rough stone steps from the path up to the mouth.
    mx, my = CAVE
    yaw = math.atan2(dy, dx)
    for k in range(4):
        d = 0.012 + k * 0.011
        sx, sy = mx + dx * d, my + dy * d
        top = floor - k * max(0.0, (floor - ground_at(mx + dx * 0.06, my + dy * 0.06)) / 4)
        if top < ground_at(sx, sy) + 0.001:
            break
        box('cave_step', (sx, sy, (top + ground_at(sx, sy)) / 2 - 0.002), (0.012, 0.03 - k * 0.002, top - ground_at(sx, sy) + 0.004), yaw + random.uniform(-0.1, 0.1), stone, bevel=0.0015)
    # A lantern hanging just inside the mouth.
    lx, ly, lz = P(0.04, 0.0, 0.036)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.003, depth=0.006, location=(lx, ly, lz))
    ln = bpy.context.object; ln.data.materials.append(flame)
    lp = bpy.data.lights.new('lantern', 'POINT'); lp.energy = 0.05; lp.color = (1, 0.65, 0.32)
    lo = bpy.data.objects.new('lantern', lp); lo.location = (lx, ly, lz); scene.collection.objects.link(lo)

def build_well():
    """A stone well: coursed stone ring, dark water deep inside, two timber
    posts with a small tiled gable roof, a windlass with a crank, and a rope
    down to a bucket that could be lowered."""
    wx, wy = WELL
    STRUCTS.append((wx, wy, 0.05))
    g = min(ground_at(wx + dx, wy + dy) for dx in (-0.02, 0, 0.02) for dy in (-0.02, 0, 0.02)) - 0.002
    stone = stone_mat('well_stone'); stone.node_tree.nodes['Mapping'].inputs['Scale'].default_value = (30, 30, 30)
    wood = wood_mat('well_wood', (0.17, 0.1, 0.055))
    R, BH = 0.018, 0.0055
    for course in range(4):
        n = 14
        for k in range(n):
            a = (k + 0.5 * (course % 2)) / n * math.tau
            box('well_block', (wx + math.cos(a) * R, wy + math.sin(a) * R, g + BH * (course + 0.5)),
                (0.006, R * math.tau / n * 0.92, BH * 0.92), a, stone, bevel=0.0007)
    # Capstones.
    for k in range(10):
        a = k / 10 * math.tau
        box('well_cap', (wx + math.cos(a) * R, wy + math.sin(a) * R, g + BH * 4 + 0.0015), (0.008, R * math.tau / 10 * 0.95, 0.003), a, stone, bevel=0.0008)
    # Dark water far down.
    wm = bpy.data.materials.new('well_water'); wm.use_nodes = True
    wb = wm.node_tree.nodes['Principled BSDF']; wb.inputs['Base Color'].default_value = (0.005, 0.01, 0.012, 1); wb.inputs['Roughness'].default_value = 0.02
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=R - 0.003, depth=0.02, location=(wx, wy, g + 0.004))
    w = bpy.context.object; w.data.materials.append(wm); w['tag'] = 'structure'
    # Posts and roof.
    top = g + 0.062
    for sgn in (-1, 1):
        box('well_post', (wx + sgn * (R + 0.003), wy, g + 0.031), (0.003, 0.003, 0.062), 0, wood, bevel=0.0004)
    roofm = wood_mat('well_roof', (0.24, 0.09, 0.045))
    for sgn in (-1, 1):
        box('well_roof', (wx, wy + sgn * 0.009, top + 0.006), (0.05, 0.022, 0.0016), 0, roofm, pitch=0)
        r = bpy.context.object; r.rotation_euler = (0.6 * sgn, 0, 0)
    box('well_ridge', (wx, wy, top + 0.0128), (0.052, 0.0025, 0.0025), 0, wood)
    # Windlass with rope wound on it, and a crank.
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.0022, depth=2 * R + 0.008, location=(wx, wy, g + 0.04))
    ax = bpy.context.object; ax.rotation_euler = (0, math.pi / 2, 0); ax.data.materials.append(wood); ax['tag'] = 'structure'
    rope = wood_mat('well_rope', (0.34, 0.28, 0.18))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.0032, depth=0.014, location=(wx, wy, g + 0.04))
    coil = bpy.context.object; coil.rotation_euler = (0, math.pi / 2, 0); coil.data.materials.append(rope)
    box('crank_arm', (wx + R + 0.007, wy, g + 0.036), (0.0015, 0.0015, 0.01), 0, wood)
    box('crank_handle', (wx + R + 0.009, wy, g + 0.031), (0.005, 0.0015, 0.0015), 0, wood)
    # Rope down to the bucket, hanging just above the opening.
    tube('well_rope_line', [(wx, wy - 0.003, g + 0.037), (wx, wy - 0.003, g + 0.03)], 0.0006, rope)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.0038, radius2=0.0048, depth=0.0075, location=(wx, wy - 0.003, g + 0.026))
    bk = bpy.context.object; bk.data.materials.append(wood); bk['tag'] = 'structure'
    iron = wood_mat('iron', (0.05, 0.05, 0.05)); iron.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.8
    for zz in (0.024, 0.028):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.0044 if zz > 0.025 else 0.0041, minor_radius=0.0004, location=(wx, wy - 0.003, g + zz))
        bpy.context.object.data.materials.append(iron)
    tube('bucket_bail', [(wx - 0.0045, wy - 0.003, g + 0.0298), (wx, wy - 0.003, g + 0.0335), (wx + 0.0045, wy - 0.003, g + 0.0298)], 0.0004, iron)

def build_lilies():
    """Water lilies: notched pads in drifts on the pond and the lake's quiet
    edges (not near the falls), a few pink and white flowers."""
    pad_m = bpy.data.materials.new('lily_pad'); pad_m.use_nodes = True
    pb = pad_m.node_tree.nodes['Principled BSDF']; pb.inputs['Base Color'].default_value = (0.08, 0.2, 0.05, 1); pb.inputs['Roughness'].default_value = 0.3
    pinks = [wood_mat('lily_pink', (0.85, 0.42, 0.55)), wood_mat('lily_white', (0.92, 0.9, 0.86))]
    # One pad mesh: a disc with a wedge cut out.
    verts = [(0, 0, 0)]; faces = []
    n = 24
    for k in range(n + 1):
        a = 0.35 + (math.tau - 0.7) * k / n
        verts.append((math.cos(a), math.sin(a), 0))
        if k:
            faces.append((0, k, k + 1))
    me = bpy.data.meshes.new('lily_pad'); me.from_pydata(verts, [], faces); me.materials.append(pad_m)
    spots = []
    for _ in range(14):
        a = random.uniform(0, math.tau); r = math.sqrt(random.random()) * 0.85
        spots.append((POND[0] + math.cos(a) * POND[2] * r, POND[1] + math.sin(a) * POND[3] * r, ground_at(POND[0], POND[1]) + 0.0205))
    for _ in range(80):
        if len(spots) >= 34:
            break
        a = random.uniform(0, math.tau); r = random.uniform(0.55, 0.92)
        x, y = LAKE[0] + math.cos(a) * LAKE[2] * r, LAKE[1] + math.sin(a) * LAKE[3] * r
        if fall_weight(x, y, 0.01, 0.12) > 0.05 or y > LAKE[1] + 0.04:
            continue
        spots.append((x, y, LAKE_Z + 0.0005))
    for i, (x, y, z) in enumerate(spots):
        o = bpy.data.objects.new('lily_pad', me); scene.collection.objects.link(o); o['tag'] = 'structure'
        s_ = random.uniform(0.0045, 0.008)
        o.location = (x, y, z); o.scale = (s_, s_, 1); o.rotation_euler = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), random.uniform(0, math.tau))
        if i % 4 == 0:
            for k in range(6):
                a = k / 6 * math.tau
                bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.0012, radius2=0.0001, depth=0.003, location=(x + math.cos(a) * 0.0011, y + math.sin(a) * 0.0011, z + 0.0015))
                pt = bpy.context.object; pt.rotation_euler = (math.sin(a) * 0.6, -math.cos(a) * 0.6, a); pt.data.materials.append(pinks[i % 8 == 0])

def build_maples():
    """Canadian maples in autumn: a trunk with a few scanned leafy crowns,
    tinted scarlet, orange and gold, standing in clearings and meadows."""
    bushes = lib('shrub_02', ['shrub_02_a_LOD2', 'shrub_02_b_LOD2', 'shrub_02_c_LOD2'])
    tints = [(0.17, 1.6, 0.95, 'scarlet'), (0.22, 1.6, 1.0, 'crimson'), (0.27, 1.5, 1.05, 'orange'), (0.31, 1.4, 1.1, 'gold')]
    crowns = {t[3]: [tinted(o, *t) for o in bushes] for t in tints}
    bark = wood_mat('maple_bark', (0.09, 0.065, 0.05))
    k = 0
    for _ in range(4000):
        if k >= 14:
            break
        x, y = rand_disc(0.88)
        if not ok(x, y, max_slope=0.5, path=0.05, build=0.12) or massif_h(x, y) > 0.04:
            continue
        H = random.uniform(0.075, 0.11)
        g = ground_at(x, y)
        lean = Vector((random.uniform(-0.01, 0.01), random.uniform(-0.01, 0.01), H * 0.6))
        base = Vector((x, y, g - 0.004))
        tube('maple_trunk', [tuple(base), tuple(base + lean * 0.5 + Vector((0.003, 0, 0))), tuple(base + lean)], 0.0028, bark)
        # Two or three crowns, one hue per tree with a neighbouring hue mixed in.
        hue = random.choice(list(crowns))
        for c in range(random.randint(2, 3)):
            src = random.choice(crowns[hue if c < 2 else random.choice(list(crowns))])
            top = base + lean + Vector((random.uniform(-0.012, 0.012), random.uniform(-0.012, 0.012), random.uniform(-0.008, 0.01)))
            o = place(src, top.x, top.y, height=H * random.uniform(0.5, 0.7), sink=0, tilt=0.15, tag='maple')
            o.location.z = top.z - H * 0.15
        k += 1

def build_lamps():
    """Stone lanterns along the paths, each with a warm light."""
    stone = stone_mat('lamp_stone'); stone.node_tree.nodes['Mapping'].inputs['Scale'].default_value = (40, 40, 40)
    glow = bpy.data.materials.new('lamp_glow'); glow.use_nodes = True
    gb = glow.node_tree.nodes['Principled BSDF']; gb.inputs['Base Color'].default_value = (1, 0.8, 0.5, 1)
    gb.inputs['Emission Color'].default_value = (1, 0.62, 0.28, 1); gb.inputs['Emission Strength'].default_value = 12
    placed = []
    for pth in PATHS[:3]:
        acc = 0.0
        for (ax, ay), (bx, by) in zip(pth, pth[1:]):
            seg = math.hypot(bx - ax, by - ay); acc += seg
            if acc < 0.17:
                continue
            acc = 0.0
            nx, ny = -(by - ay) / seg, (bx - ax) / seg
            side = random.choice((-1, 1))
            x, y = bx + nx * 0.028 * side, by + ny * 0.028 * side
            if in_water(x, y, 0.01) or any(math.hypot(x - px, y - py) < 0.1 for px, py in placed) or slope_at(x, y) > 0.6:
                continue
            if any(math.hypot(x - sx, y - sy) < r + 0.01 for sx, sy, r in STRUCTS):
                continue
            g = ground_at(x, y); yaw = math.atan2(ny, nx)
            box('lamp_base', (x, y, g + 0.002), (0.008, 0.008, 0.005), yaw, stone, bevel=0.0008)
            box('lamp_post', (x, y, g + 0.011), (0.004, 0.004, 0.014), yaw, stone, bevel=0.0005)
            box('lamp_box', (x, y, g + 0.021), (0.0065, 0.0065, 0.006), yaw, glow, bevel=0.0005)
            bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.0068, radius2=0.0008, depth=0.005, location=(x, y, g + 0.0265))
            c = bpy.context.object; c.rotation_euler.z = yaw + math.pi / 4; c.data.materials.append(stone); c['tag'] = 'structure'
            lp = bpy.data.lights.new('lamp', 'POINT'); lp.energy = 0.02; lp.color = (1, 0.64, 0.32); lp.shadow_soft_size = 0.003
            lo = bpy.data.objects.new('lamp_light', lp); lo.location = (x, y, g + 0.021); scene.collection.objects.link(lo)
            STRUCTS.append((x, y, 0.008)); placed.append((x, y))

def build_tower():
    """An old ruined stone watchtower."""
    tx, ty = TOWER
    STRUCTS.append((tx, ty, 0.055))
    g = min(ground_at(tx + dx, ty + dy) for dx in (-0.03, 0, 0.03) for dy in (-0.03, 0, 0.03)) - 0.004
    stone = stone_mat('tower_stone')
    stone.node_tree.nodes['Mapping'].inputs['Scale'].default_value = (22, 22, 22)
    H, R = 0.13, 0.024
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=R, depth=H, location=(tx, ty, g + H / 2))
    t = bpy.context.object; t.name = 'tower'; t['tag'] = 'structure'; t.data.materials.append(stone)
    # Slight batter (wider at the base) and hand-laid irregularity.
    for v in t.data.vertices:
        k = 1.08 if v.co.z < 0 else 0.98
        v.co.x *= k; v.co.y *= k
    sub = t.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.subdivision_type = 'SIMPLE'
    tex = bpy.data.textures.new('tower_noise', 'CLOUDS'); tex.noise_scale = 0.006
    dm = t.modifiers.new('rough', 'DISPLACE'); dm.texture = tex; dm.strength = 0.0018
    # Corbelled ring and crenellations, with a broken section.
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=R * 1.12, depth=0.008, location=(tx, ty, g + H - 0.004))
    ring = bpy.context.object; ring.data.materials.append(stone); ring['tag'] = 'structure'
    for k in range(12):
        a = k / 12 * math.tau
        if 7 <= k <= 9:
            continue  # collapsed
        hh = 0.012 if k not in (6, 10) else 0.006
        box('merlon', (tx + math.cos(a) * R * 1.05, ty + math.sin(a) * R * 1.05, g + H + hh / 2), (0.008, 0.006, hh), a + math.pi / 2, stone, bevel=0.0008)
    # Rubble from the collapse.
    for k in range(4):
        a = 8 / 12 * math.tau + random.uniform(-0.3, 0.3); rr = R * random.uniform(1.4, 2.4)
        box('rubble', (tx + math.cos(a) * rr, ty + math.sin(a) * rr, ground_at(tx + math.cos(a) * rr, ty + math.sin(a) * rr) + 0.002),
            (random.uniform(0.004, 0.008),) * 3, random.uniform(0, 3), stone, bevel=0.001)
    # Windows (dark, arched slits) and a wooden door, facing the paths.
    dark = bpy.data.materials.new('window_dark'); dark.use_nodes = True
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.01, 0.009, 0.008, 1)
    door = wood_mat('tower_door', (0.12, 0.07, 0.04))
    for a, z, w_, h_ in ((-2.4, 0.07, 0.005, 0.012), (-0.9, 0.1, 0.005, 0.012), (1.0, 0.05, 0.005, 0.01)):
        box('window', (tx + math.cos(a) * R * 0.99, ty + math.sin(a) * R * 0.99, g + z), (0.003, w_, h_), a, dark)
    a = math.atan2(-0.1 - ty, 0.36 - tx)  # door toward the path
    box('door', (tx + math.cos(a) * R * 1.04, ty + math.sin(a) * R * 1.04, g + 0.012), (0.003, 0.011, 0.02), a, door, bevel=0.0006)

def build_garden():
    """A small fenced garden: raised beds, rows of plants, a birdhouse."""
    gx, gy, face = GARDEN
    STRUCTS.append((gx, gy, 0.075))
    c, s_ = math.cos(face), math.sin(face)
    P = lambda ox, oy: (gx + ox * c - oy * s_, gy + ox * s_ + oy * c)
    g = ground_at(gx, gy)
    wood = wood_mat('garden_wood', (0.26, 0.17, 0.1))
    soil = wood_mat('bed_soil', (0.07, 0.045, 0.028)); soil.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1
    W, D = 0.12, 0.085
    # Picket fence with a gate gap on the west side.
    for side, (x0, y0, x1, y1) in enumerate(((-W/2, -D/2, W/2, -D/2), (W/2, -D/2, W/2, D/2), (W/2, D/2, -W/2, D/2), (-W/2, D/2, -W/2, -D/2))):
        n = int(math.hypot(x1 - x0, y1 - y0) / 0.006)
        for k in range(n + 1):
            t = k / n
            if side == 3 and 0.35 < t < 0.65:
                continue
            px, py = P(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            box('picket', (px, py, ground_at(px, py) + 0.008), (0.0018, 0.0018, 0.016), face, wood)
        for hgt in (0.006, 0.013):
            mx, my = P((x0 + x1) / 2, (y0 + y1) / 2)
            ln = math.hypot(x1 - x0, y1 - y0)
            box('fence_rail', (mx, my, g + hgt), (ln if side % 2 == 0 else 0.0014, 0.0014 if side % 2 == 0 else ln, 0.0014), face, wood)
    # Three raised beds with rows of plants.
    greens = lib('shrub_sorrel_01', ['shrub_sorrel_01*'])
    blooms = lib('flower_empodium', ['flower_empodium_e_LOD2']) + lib('flower_gazania', ['flower_gazania_a_LOD3'])
    for b_ in range(3):
        oy = -D / 2 + 0.018 + b_ * 0.025
        bx, by = P(0.004, oy)
        box('bed_frame', (bx, by, g + 0.004), (W * 0.78, 0.016, 0.008), face, wood, bevel=0.0005)
        box('bed_soil', (bx, by, g + 0.0075), (W * 0.74, 0.012, 0.002), face, soil)
        for k in range(12):
            px, py = P(-W * 0.35 + k * W * 0.063 + random.uniform(-0.002, 0.002), oy + random.uniform(-0.002, 0.002))
            src = random.choice(blooms if b_ == 1 else greens)
            o = place(src, px, py, width=random.uniform(0.012, 0.016), sink=0, tilt=0.1, tag='garden')
            o.location.z = g + 0.008
    # Birdhouse on a post at the corner.
    bx, by = P(W / 2 + 0.012, D / 2 + 0.008)
    box('bird_post', (bx, by, g + 0.02), (0.002, 0.002, 0.04), face, wood)
    paint = wood_mat('birdhouse', (0.28, 0.32, 0.3))
    box('bird_box', (bx, by, g + 0.044), (0.008, 0.007, 0.009), face, paint, bevel=0.0005)
    for sgn in (-1, 1):
        ox, oy = 0.0026 * sgn, 0
        px, py = P(W / 2 + 0.012 + ox * c, D / 2 + 0.008)
        o = box('bird_roof', (bx + 0.0024 * sgn * c, by + 0.0024 * sgn * s_, g + 0.0512), (0.0062, 0.0085, 0.0008), face, wood)
        o.rotation_euler = (0, 0.75 * sgn, face)
    hole = bpy.data.materials.new('hole'); hole.use_nodes = True
    hole.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.01, 0.01, 0.01, 1)
    fx_, fy_ = bx - s_ * 0.0036, by + c * 0.0036
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0014, depth=0.0006, location=(fx_, fy_, g + 0.045))
    hh = bpy.context.object; hh.rotation_euler = (math.pi / 2, 0, face); hh.data.materials.append(hole)

def build_cave_rocks(rocks):
    """Cave entrance at the foot of the west peak: two chunky standing stones,
    a heavy lintel, shoulder rocks, and a dark passage between them."""
    cx, cy = CAVE
    dx, dy = CAVE_DIR
    ax_, ay_ = -dy, dx
    floor = GROUND + CAVE_FLOOR
    chunky = [r for r in rocks if sorted(mesh_size(r))[0] > 0.55 * sorted(mesh_size(r))[2]] or rocks
    def stone(x, y, w, hgt, z0, yaw=None):
        src = random.choice(chunky)
        sz = mesh_size(src); k = w / max(sz.x, sz.y)
        o = place(src, x, y, width=w, sink=0, tilt=0.03, tag='cave')
        o.scale.z = o.scale.x * (hgt / (sz.z * k))
        if yaw is not None:
            o.rotation_euler.z = yaw
        o.location.z = z0 + hgt * 0.5
        return o
    H, GAP = 0.058, 0.026
    for sgn in (-1, 1):
        px, py = cx + ax_ * (GAP + 0.014) * sgn, cy + ay_ * (GAP + 0.014) * sgn
        stone(px, py, 0.03, H + 0.008, floor - 0.008)
        for k in range(3):
            qx = px + ax_ * (0.02 + 0.012 * k) * sgn - dx * (0.006 + 0.01 * k)
            qy = py + ay_ * (0.02 + 0.012 * k) * sgn - dy * (0.006 + 0.01 * k)
            stone(qx, qy, random.uniform(0.025, 0.035), random.uniform(0.03, 0.05) * (1 - 0.2 * k), ground_at(qx, qy) - 0.012)
    stone(cx - dx * 0.004, cy - dy * 0.004, 0.1, 0.024, floor + H - 0.004, yaw=math.atan2(ay_, ax_))
    stone(cx - dx * 0.03, cy - dy * 0.03, 0.07, 0.03, floor + H + 0.01)
    for k in range(3):
        qx = cx + dx * random.uniform(0.02, 0.04) + ax_ * random.uniform(-0.04, 0.04)
        qy = cy + dy * random.uniform(0.02, 0.04) + ay_ * random.uniform(-0.04, 0.04)
        stone(qx, qy, random.uniform(0.009, 0.014), 0.007, ground_at(qx, qy) - 0.002)

def build_stepping_stones(rocks, put):
    """Rounded, flat-topped stepping stones across the stream where the front
    path meets it, standing just proud of the water."""
    cx, cy = STEP_CROSSING
    i = min(range(len(STREAM) - 1), key=lambda k: math.hypot(STREAM[k][0] - cx, STREAM[k][1] - cy))
    tx, ty = STREAM[i + 1][0] - STREAM[i][0], STREAM[i + 1][1] - STREAM[i][1]
    l = math.hypot(tx, ty); ax, ay = -ty / l, tx / l
    m = stone_mat('step_stone'); m.node_tree.nodes['Mapping'].inputs['Scale'].default_value = (40, 40, 40)
    for k in range(-3, 4):
        x = cx + ax * k * 0.014 + random.uniform(-0.002, 0.002); y = cy + ay * k * 0.014 + random.uniform(-0.002, 0.002)
        r = random.uniform(0.0055, 0.007)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=(x, y, 0))
        o = bpy.context.object; o['tag'] = 'structure'
        seed = random.uniform(0, 40)
        for v in o.data.vertices:
            n = v.co.normalized()
            v.co = n * (1 + 0.1 * fbm(n.x * 2 + seed, n.y * 2, n.z * 2, 2))
            if v.co.z > 0.35:
                v.co.z = 0.35 + (v.co.z - 0.35) * 0.3  # flat top
        o.scale = (r * random.uniform(1.0, 1.25), r, r * 0.9)
        o.rotation_euler.z = random.uniform(0, 3)
        top = max(ground_at(x, y), LAKE_Z - 0.004) + 0.006
        o.location.z = top - r * 0.9 * 0.42
        o.data.shade_smooth() if hasattr(o.data, 'shade_smooth') else None
        o.data.materials.append(m)


def mesh_size(o):
    """Real evaluated size of a source at scale 1 (measured in the scene, so
    odd source units or modifiers can't skew placement)."""
    if 'size' not in o:
        t = bpy.data.objects.new('__measure', o.data)
        scene.collection.objects.link(t)
        bpy.context.view_layer.update()
        o['size'] = tuple(t.dimensions)
        bpy.data.objects.remove(t)
    return Vector(o['size'])

def tinted(src, hue, sat, val, tag):
    """A copy of a plant with its foliage colour shifted (e.g. autumn)."""
    o = src.copy(); o.data = src.data.copy(); o.name = f'{src.name}_{tag}'
    for i, m in enumerate(o.data.materials):
        if not m or not m.node_tree:
            continue
        m2 = m.copy(); m2.name = f'{m.name}_{tag}'
        nt = m2.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b and b.inputs['Base Color'].is_linked:
            link = b.inputs['Base Color'].links[0]
            hsv = nt.nodes.new('ShaderNodeHueSaturation')
            hsv.inputs['Hue'].default_value = hue; hsv.inputs['Saturation'].default_value = sat; hsv.inputs['Value'].default_value = val
            nt.links.new(link.from_socket, hsv.inputs['Color']); nt.links.new(hsv.outputs['Color'], b.inputs['Base Color'])
        o.data.materials[i] = m2
    o['size'] = tuple(mesh_size(src))
    return o

LIB = {}
def lib(asset, names):
    """Append objects whose names match (exact or prefix*) from an asset's .blend; keep out of scene."""
    key = (asset, tuple(names))
    if key in LIB:
        return LIB[key]
    f = glob.glob(os.path.join(ASSETS, asset, 'blend', '*.blend'))[0]
    with bpy.data.libraries.load(f, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names or any(n.startswith(p[:-1]) for p in names if p.endswith('*'))]
    objs = [o for o in dst.objects if o and o.type == 'MESH']
    for o in objs:
        o.matrix_world = Matrix.Identity(4)
        o.parent = None
    LIB[key] = objs
    return objs

PLACED = []
def place(src, x, y, height=None, width=None, rot=None, sink=0.0, tilt=0.06, tag='plant'):
    o = bpy.data.objects.new(src.name, src.data)
    o.modifiers.clear()
    for m in src.modifiers:  # keep geometry-node trees intact
        nm = o.modifiers.new(m.name, m.type)
        if m.type == 'NODES':
            nm.node_group = m.node_group
    d = mesh_size(src)
    if height:
        s = height / max(d.z, 1e-4)
    else:
        s = width / max(d.x, d.y, 1e-4)
    o.scale = (s, s, s)
    o.rotation_euler = (random.uniform(-tilt, tilt), random.uniform(-tilt, tilt), rot if rot is not None else random.uniform(0, math.tau))
    o.location = (x, y, ground_at(x, y) - sink * d.z * s)
    o['tag'] = tag
    scene.collection.objects.link(o)
    PLACED.append(o)
    return o

def scatter(srcs, count, size_fn, pred, tag, mode='width', cluster=None, min_d=0.0, sink=0.02, tilt=0.08, tries=40):
    pts = []
    for _ in range(count * tries):
        if len(pts) >= count:
            break
        x, y = rand_disc()
        if cluster and fbm(x * cluster[0] + cluster[1], 3, y * cluster[0], 3) < cluster[2]:
            continue
        if not pred(x, y):
            continue
        if min_d and any((x - px) ** 2 + (y - py) ** 2 < min_d * min_d for px, py in pts):
            continue
        src = random.choice(srcs)
        kw = {'height': size_fn()} if mode == 'height' else {'width': size_fn()}
        place(src, x, y, sink=sink, tilt=tilt, tag=tag, **kw)
        pts.append((x, y))
    return pts

# ------------------------------------------------------------------ layer 4: rocks
def build_rocks():
    rocks = []
    for setname in ('rock_moss_set_01', 'rock_moss_set_02'):
        bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, setname, setname + '.gltf'))
        for o in list(bpy.context.selected_objects):
            if o.type != 'MESH':
                continue
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
            bpy.ops.mesh.separate(type='LOOSE')
            for p in bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = p
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                p.location = (0, 0, 0)
                bpy.context.scene.collection.objects.unlink(p) if p.name in bpy.context.scene.collection.objects else None
                for c in p.users_collection:
                    c.objects.unlink(p)
                d = sorted(p.dimensions)
                # Skip thin shell fragments: they read as floating flakes.
                if len(p.data.polygons) > 300 and d[0] > 0.35 * d[2]:
                    rocks.append(p)
    boulder = []  # the boulder scan's low LOD is a proxy shell; not used
    def put(x, y, w, flat, tag='rock', srcs=None, keep=False):
        if math.hypot(x, y) > EDGE * 0.92:
            return
        if not keep and path_d(x, y) < 0.025:
            return
        src = random.choice(srcs or rocks)
        sz = mesh_size(src)
        k = w / max(sz.x, sz.y)
        h = sz.z * k * flat
        o = place(src, x, y, width=w, sink=0.0, tilt=0.0, tag=tag)
        o.scale.z *= flat
        # Bed it into the ground: lowest ground under its footprint, then sink ~35%,
        # and lean it with the slope so it never perches.
        r = w * 0.45
        g = min(ground_at(x + dx * r, y + dy * r) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
        e = 0.008
        nrm = Vector((-(ground_at(x + e, y) - ground_at(x - e, y)) / (2 * e), -(ground_at(x, y + e) - ground_at(x, y - e)) / (2 * e), 1)).normalized()
        yaw = random.uniform(0, math.tau)
        o.rotation_mode = 'QUATERNION'
        from mathutils import Quaternion
        o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(nrm) @ Quaternion((0, 0, 1), yaw)
        o.location.z = g + h * 0.5 - h * 0.38
    # Boulders round the lake shore and at the foot of the falls.
    for k in range(14):
        a = k / 14 * math.tau + random.uniform(-0.15, 0.15)
        if abs(math.sin(a) - 1) < 0.25:  # keep the falls side partly open
            continue
        x = LAKE[0] + math.cos(a) * LAKE[2] * random.uniform(1.0, 1.15); y = LAKE[1] + math.sin(a) * LAKE[3] * random.uniform(1.0, 1.15)
        if path_d(x, y) > 0.03:
            put(x, y, random.uniform(0.035, 0.07), 0.75)
    # The rock shelf that splits the falls, and boulders flanking the plunge.
    for dx in (-0.055, 0.055):
        put(FALL_X + dx, LAKE[1] + LAKE[3] * 0.8, random.uniform(0.05, 0.07), 0.9)
    # Reeds-and-rocks rim for the pond.
    for k in range(9):
        a_ = k / 9 * math.tau + random.uniform(-0.2, 0.2)
        put(POND[0] + math.cos(a_) * POND[2] * 1.12, POND[1] + math.sin(a_) * POND[3] * 1.12, random.uniform(0.018, 0.035), 0.7)
    build_stepping_stones(rocks, put)
    for (x, y) in STREAM[2::3]:
        for side in (-1, 1):
            if random.random() < 0.7:
                put(x + side * random.uniform(0.045, 0.07), y + random.uniform(-0.02, 0.02), random.uniform(0.025, 0.05), 0.65)
    for _ in range(26):
        x, y = rand_disc()
        if ok(x, y, max_slope=0.6):
            put(x, y, random.uniform(0.03, 0.07), 0.7)

# ------------------------------------------------------------------ layer 5-8: vegetation
def build_vegetation():
    firs = lib('fir_tree_01', ['fir_tree_01_a_LOD2', 'fir_tree_01_b_LOD2', 'fir_tree_01_c_LOD2'])
    saplings = lib('fir_sapling', ['fir_sapling_a', 'fir_sapling_b', 'fir_sapling_c'])
    pines = lib('pine_sapling_small', ['pine_sapling_small_a', 'pine_sapling_small_b', 'pine_sapling_small_c'])
    # Groves all the way round, with clearings between them; smaller trees
    # up on the mountain's ledges; a few lone trees in the meadows.
    def grove(x, y):
        return fbm(x * 3.2 + 4, 7, y * 3.2, 3)
    n = 0
    pts = []
    for _ in range(14000):
        if n >= 130:
            break
        x, y = rand_disc()
        on_mtn = massif_h(x, y) > 0.08 and math.hypot(x, y) < 0.4
        if fall_weight(x, y, 0.006, 0.08) > 0.2:
            continue
        if not ok(x, y, water=0.04, max_slope=1.1 if on_mtn else 0.7, path=0.05, build=0.12):
            continue
        g = grove(x, y)
        if not on_mtn and g < -0.02 and random.random() > 0.06:
            continue  # clearing (with the odd lone tree)
        if any((x - px) ** 2 + (y - py) ** 2 < 0.04 ** 2 for px, py in pts):
            continue
        h = random.uniform(0.11, 0.24) * (VEG / 0.6) * (0.5 if on_mtn else 1.0) * (1.15 if y > 0.3 else 1.0)
        if ground_at(x, y) + h > math.sqrt(max(0, INNER * INNER * 0.86 - x * x - y * y)):
            continue
        r = random.random()
        src = random.choice(saplings) if on_mtn else (random.choice(firs) if r < 0.45 else random.choice(saplings if r < 0.72 else pines))
        place(src, x, y, height=h, sink=0.04, tilt=0.05, tag='tree')
        pts.append((x, y)); n += 1
    bushes = lib('shrub_02', ['shrub_02_a_LOD2', 'shrub_02_b_LOD2', 'shrub_02_c_LOD2'])
    build_maples()

    # Shrubs and bushes at forest edges and around boulders.
    scatter(bushes, 40, lambda: random.uniform(0.05, 0.1) * VEG / 0.72, lambda x, y: ok(x, y, max_slope=0.6) and y > -0.4, 'shrub', cluster=(4, 2, -0.05), min_d=0.04)
    tall = lib('shrub_03', ['shrub_03_a_LOD2', 'shrub_03_b_LOD2', 'shrub_03_c_LOD1'])
    scatter(tall, 70, lambda: random.uniform(0.04, 0.07), lambda x, y: ok(x, y), 'weed', mode='height', cluster=(5, 4, 0.0))
    # Ferns along the water.
    ferns = lib('fern_02', ['fern_02*'])
    scatter(ferns, 60, lambda: random.uniform(0.05, 0.085), lambda x, y: ok(x, y, water=0.005) and in_water(x, y, 0.08), 'fern')
    # Nettles, weeds and grass clumps fill the gaps.
    nettle = lib('nettle_plant', ['nettle_plant_medium_a_LOD3', 'nettle_plant_medium_b_LOD3'])
    scatter(nettle, 120, lambda: random.uniform(0.025, 0.045), lambda x, y: ok(x, y), 'weed', mode='height', cluster=(6, 8, 0.05))
    weeds = lib('weed_plant_02', ['weed_plant_02_a_LOD3', 'weed_plant_02_b_LOD3'])
    scatter(weeds, 140, lambda: random.uniform(0.03, 0.05), lambda x, y: ok(x, y), 'weed', cluster=(5, 11, -0.1))
    grass = lib('grass_medium_01', ['grass_medium_01_geonodes_large_a_LOD2', 'grass_medium_01_geonodes_large_b_LOD2'])
    scatter(grass, 500, lambda: random.uniform(0.04, 0.07), lambda x, y: ok(x, y, max_slope=0.5), 'grass', cluster=(3, 5, -0.15))
    sorrel = lib('shrub_sorrel_01', ['shrub_sorrel_01*'])
    scatter(sorrel, 160, lambda: random.uniform(0.012, 0.02), lambda x, y: ok(x, y, max_slope=0.9), 'groundcover')

    # Wildflower meadows: dense drifts of one or two species, like the references.
    flowers = {
        'yellow': lib('flower_ursinia', ['flower_ursinia_c_LOD2', 'flower_ursinia_d_LOD2', 'flower_ursinia_e_LOD2']) + lib('celandine_01', ['celandine_01_a_LOD2', 'celandine_01_b_LOD2']),
        'orange': lib('flower_gazania', ['flower_gazania_a_LOD3', 'flower_gazania_b_LOD3', 'flower_gazania_c_LOD3', 'flower_gazania_d_LOD3']),
        'purple': lib('periwinkle_plant', ['periwinkle_plant_01_LOD6', 'periwinkle_plant_02_LOD6']),
        'gold': lib('flower_empodium', ['flower_empodium_a_LOD2', 'flower_empodium_c_LOD2', 'flower_empodium_e_LOD2']),
    }
    drifts = 34
    for d in range(drifts):
        for _ in range(200):
            cx, cy = rand_disc(0.85)
            if ok(cx, cy, max_slope=0.4) and massif_h(cx, cy) < 0.05:
                break
        kind = random.choice(['yellow', 'purple', 'purple', 'orange', 'gold', 'yellow'])
        rad = random.uniform(0.06, 0.13)
        for _ in range(random.randint(25, 55)):
            a = random.uniform(0, math.tau); r = rad * math.sqrt(random.random())
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
            if not ok(x, y, max_slope=0.5):
                continue
            place(random.choice(flowers[kind]), x, y, width=random.uniform(0.03, 0.05), sink=0.0, tilt=0.15, tag='flower')

# ------------------------------------------------------------------ layer 9: moss (render only)
def build_moss(terrain):
    vg = terrain.vertex_groups.new(name='moss')
    for v in terrain.data.vertices:
        x, y, _ = v.co
        near = any(math.hypot(x - sx, y - sy) < r + 0.002 for sx, sy, r in STRUCTS) or fall_weight(x, y, 0.004, 0.06) > 0.2
        w = 0.0 if (near or in_water(x, y, -0.005) or path_d(x, y) < 0.028 or cave_dark(x, y) > 0.1) else max(0.0, min(1.0, (0.7 - slope_at(x, y)) / 0.5))
        w *= 0.6 + 0.4 * max(0, fbm(x * 9, 3, y * 9) + 0.5)
        vg.add([v.index], w, 'REPLACE')
    ps = terrain.modifiers.new('moss', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.type = 'HAIR'; st.count = 70000; st.hair_length = 0.009; st.emit_from = 'FACE'
    st.use_advanced_hair = True; st.factor_random = 0.003
    st.radius_scale = 1.0; st.root_radius = 0.0011; st.tip_radius = 0.0002; st.length_random = 0.6
    st.child_type = 'INTERPOLATED'; st.rendered_child_count = 8; st.child_radius = 0.01; st.clump_factor = 0.4
    ps.vertex_group_density = 'moss'; ps.vertex_group_length = 'moss'
    mm = bpy.data.materials.new('moss'); mm.use_nodes = True
    nt = mm.node_tree; N = nt.nodes
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    hair = N.new('ShaderNodeBsdfHairPrincipled'); hair.parametrization = 'COLOR'
    info = N.new('ShaderNodeHairInfo'); ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.03, 0.08, 0.01, 1); ramp.color_ramp.elements[1].color = (0.32, 0.5, 0.06, 1)
    nt.links.new(info.outputs['Intercept'], ramp.inputs['Fac'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
    tc = N.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    pal = N.new('ShaderNodeValToRGB'); pe = pal.color_ramp.elements
    pe[0].position = 0.35; pe[0].color = (1, 1, 1, 1); pe[1].position = 0.7; pe[1].color = (1.6, 1.15, 0.4, 1)
    rust = pe.new(0.78); rust.color = (1.4, 0.5, 0.15, 1)
    nt.links.new(nz.outputs['Fac'], pal.inputs['Fac'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    nt.links.new(ramp.outputs['Color'], mul.inputs[6]); nt.links.new(pal.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], hair.inputs['Color']); hair.inputs['Roughness'].default_value = 0.6
    nt.links.new(hair.outputs['BSDF'], N['Material Output'].inputs['Surface'])
    terrain.data.materials.append(mm); st.material = len(terrain.data.materials)

# ------------------------------------------------------------------ light, camera, render
def setup_render():
    w = bpy.data.worlds.new('w'); scene.world = w; w.use_nodes = True
    nt = w.node_tree
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(ASSETS, 'hdri', 'sunset_forest_2k.hdr'))
    bg = nt.nodes['Background']; bg.inputs['Strength'].default_value = 0.75
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    lp = nt.nodes.new('ShaderNodeLightPath')
    paper = nt.nodes.new('ShaderNodeBackground'); paper.inputs['Color'].default_value = (0.86, 0.82, 0.75, 1)
    mixs = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mixs.inputs['Fac']); nt.links.new(bg.outputs['Background'], mixs.inputs[1]); nt.links.new(paper.outputs['Background'], mixs.inputs[2])
    nt.links.new(mixs.outputs['Shader'], nt.nodes['World Output'].inputs['Surface'])
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 6.0; sun.color = (1.0, 0.78, 0.5); sun.angle = math.radians(2)
    so = bpy.data.objects.new('sun', sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(68), 0, math.radians(-140))
    cam = bpy.data.cameras.new('cam'); cam.lens = 50
    co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co)
    co.location = (0.0, -2.8, 0.85)
    co.rotation_euler = (Vector((0, 0.0, -0.2)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    cam.dof.use_dof = True; cam.dof.focus_distance = 2.9; cam.dof.aperture_fstop = 2.8
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
    scene.cycles.samples = int(os.environ.get('SAMPLES', 48)); scene.cycles.use_denoising = True; scene.cycles.max_bounces = 6
    res = int(os.environ.get('RES', 1100))
    scene.render.resolution_x, scene.render.resolution_y = res, int(res * 0.8)
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = 0.35
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4

if __name__ == '__main__':
    build_soil()
    terrain = build_terrain()
    carve_cave(terrain)
    carve_tunnel(terrain)
    global SHELF
    SHELF = build_water()
    build_pavilions()
    build_bridge()
    build_rope_bridges()
    build_cave()
    build_tower()
    build_garden()
    build_well()
    build_lamps()
    build_lilies()
    build_rocks()
    build_vegetation()
    if MODE == 'render':
        build_moss(terrain)
    setup_render()
    from collections import Counter
    print("placed", Counter(o["tag"] for o in PLACED)); print("CAVE", CAVE, CAVE_DIR, GROUND + CAVE_FLOOR)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'world.blend'))
    if MODE == 'render':
        scene.render.filepath = os.path.join(OUT, 'world.png')
        bpy.ops.render.render(write_still=True)
        print('rendered')
