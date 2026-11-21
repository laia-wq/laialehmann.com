"""House v5: the two-building house standing in shallow clear water.
Detailed paths (boardwalk, stepping stones, a little bridge) lead to a grassy
island with a nest daybed and a hanging egg chair. Koi, waterlilies, floating
candles. Brass Moroccan lanterns, shepherd-hook globe lamps, paper lantern
clusters, wall sconces. Bookcase planters, awnings, trailing flowers.
Usage: ASSETS=<assets-raw> python house_v5.py <out.png> [samples]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

OUT = sys.argv[-2] if sys.argv[-1].isdigit() else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 64
sc = reset()
from garden import *
from arch import *

brass = solid('brass', (0.78, 0.56, 0.26), 0.28, metal=1.0)
clean_stone = varied('clean_stone', (0.88, 0.85, 0.79), 0.03, 0.55, bump=0.04, bump_scale=80)
rattan = wood('rattan', (0.72, 0.52, 0.3), 30, rough=0.7)
linen = varied('linen', (0.93, 0.89, 0.82), 0.04, 0.9, bump=0.05, bump_scale=200)
terracotta_cushion = varied('cushion_tc', (0.78, 0.45, 0.3), 0.06, 0.9)
sage_cushion = varied('cushion_sage', (0.58, 0.66, 0.5), 0.06, 0.9)
PAL = [(0.98, 0.95, 0.9), (0.98, 0.68, 0.76), (0.98, 0.82, 0.3), (0.72, 0.55, 0.95), (0.96, 0.45, 0.42), (0.99, 0.6, 0.3)]

WL = -0.03   # water level
BOT = -0.22  # pond floor

def water_mat():
    m, n, l, b = node_mat('clear_water')
    b.inputs['Base Color'].default_value = (0.55, 0.82, 0.8, 1)
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.02
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat IOR'].default_value = 1.33; b.inputs['Coat Roughness'].default_value = 0.02
    b.inputs['Roughness'].default_value = 0.03
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 28; nz.inputs['Detail'].default_value = 1
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.025
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Coat Normal'])
    return m
def pond_floor():
    m, n, l, b = node_mat('pond_floor')
    tc = n.new('ShaderNodeTexCoord')
    vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 26; l.new(tc.outputs['Object'], vo.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; l.new(tc.outputs['Object'], nz.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].color = (0.3, 0.34, 0.24, 1); r.color_ramp.elements[1].color = (0.62, 0.58, 0.46, 1)
    mx = n.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'
    l.new(vo.outputs['Distance'], mx.inputs[0]); l.new(nz.outputs['Fac'], mx.inputs[1])
    l.new(mx.outputs['Value'], r.inputs['Fac']); l.new(r.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5
    l.new(vo.outputs['Distance'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.8
    return m

# ------------------------------------------------------------------ lamps
def moroccan(p, s=1.0, color=(1.0, 0.6, 0.28), chain=0.25):
    """Brass lantern: faceted amber glass, pierced caps, dome, finial, ring + chain."""
    x, y, z = p
    am = solid('moroccan_glass_' + str(color), (1, 0.8, 0.5), 0.3, emit=color, strength=9)
    cyl('mor_glass', (x, y, z), 0.065 * s, 0.15 * s, am, verts=8)
    for k in range(8):
        a = k / 8 * 2 * math.pi + math.pi / 8
        box('mor_bar', (x + math.cos(a) * 0.067 * s, y + math.sin(a) * 0.067 * s, z), (0.008 * s, 0.008 * s, 0.155 * s), brass, bevel=0)
    cyl('mor_base', (x, y, z - 0.085 * s), 0.07 * s, 0.03 * s, brass, verts=8, r2=0.05 * s)
    cyl('mor_foot', (x, y, z - 0.11 * s), 0.03 * s, 0.03 * s, brass, verts=8, r2=0.015 * s)
    cyl('mor_rim', (x, y, z + 0.085 * s), 0.075 * s, 0.025 * s, brass, verts=8)
    sphere('mor_dome', (x, y, z + 0.1 * s), 0.06 * s, brass, 16, (1, 1, 0.8))
    cyl('mor_finial', (x, y, z + 0.165 * s), 0.012 * s, 0.05 * s, brass, verts=8)
    sphere('mor_ring', (x, y, z + 0.2 * s), 0.016 * s, brass, 8)
    if chain:
        cyl('chain', (x, y, z + 0.2 * s + chain / 2), 0.004, chain, iron, verts=6)
    L = bpy.data.lights.new('mor', 'POINT'); L.energy = 10 * s; L.color = color; L.shadow_soft_size = 0.04
    link(bpy.data.objects.new('mor', L)).location = (x, y, z)

def globe_hook(x, y, h=1.0, face=0.0):
    """Shepherd's-hook post with a hanging glass globe."""
    cyl('hook_foot', (x, y, 0.06), 0.06, 0.05, brass, verts=16)
    cyl('hook_post', (x, y, 0.06 + h / 2), 0.018, h, brass, verts=10)
    c = Vector((x, y, 0.06 + h)); r = 0.13
    d = Vector((math.cos(face), math.sin(face), 0))
    pts = [c + d * (r - r * math.cos(t)) + Vector((0, 0, r * math.sin(t))) for t in [k / 6 * math.pi for k in range(7)]]
    for a, b in zip(pts, pts[1:]):
        limb(a, b, 0.012, brass)
    tip = pts[-1]
    cyl('hook_chain', tip - Vector((0, 0, 0.06)), 0.004, 0.12, iron, verts=6)
    g = solid('globe_glass', (1, 0.92, 0.8), 0.15, emit=(1.0, 0.74, 0.45), strength=10)
    sphere('globe', tip - Vector((0, 0, 0.19)), 0.065, g, 18)
    cyl('globe_cap', tip - Vector((0, 0, 0.12)), 0.025, 0.025, brass, verts=10)
    L = bpy.data.lights.new('gh', 'POINT'); L.energy = 9; L.color = (1.0, 0.72, 0.45); L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('gh', L)).location = tip - Vector((0, 0, 0.19))

def sconce(p, normal):
    n = Vector(normal).normalized()
    base = Vector(p)
    box('sconce_plate', base, (0.03, 0.08, 0.14) if abs(n.x) > 0.5 else (0.08, 0.03, 0.14), brass, bevel=0.005)
    limb(base, base + n * 0.12 + Vector((0, 0, 0.05)), 0.01, brass)
    g = solid('sconce_glass', (1, 0.92, 0.8), 0.15, emit=(1.0, 0.72, 0.42), strength=9)
    sphere('sconce_globe', base + n * 0.13 + Vector((0, 0, 0.11)), 0.055, g, 16)
    L = bpy.data.lights.new('sc', 'POINT'); L.energy = 6; L.color = (1, 0.72, 0.42)
    link(bpy.data.objects.new('sc', L)).location = base + n * 0.13 + Vector((0, 0, 0.11))

def floating_candle(x, y):
    cyl('fc_pad', (x, y, WL + 0.005), 0.08, 0.008, varied('lilypad', (0.16, 0.34, 0.12), 0.25, 0.4), verts=18)
    cyl('fc_jar', (x, y, WL + 0.04), 0.03, 0.06, solid('jar', (1, 0.8, 0.5), 0.2, emit=(1, 0.6, 0.25), strength=8), verts=12)
    L = bpy.data.lights.new('fc', 'POINT'); L.energy = 1.5; L.color = (1, 0.62, 0.3)
    link(bpy.data.objects.new('fc', L)).location = (x, y, WL + 0.08)

def paper_cluster(p, n=3):
    cols = [(1.0, 0.55, 0.25), (1.0, 0.75, 0.45), (0.98, 0.5, 0.45)]
    for k in range(n):
        a = k / n * 2 * math.pi
        paper_lantern((p[0] + math.cos(a) * 0.12, p[1] + math.sin(a) * 0.12, p[2] - k * 0.08), 0.07 + 0.025 * (k % 2), cols[k % 3])

# ------------------------------------------------------------------ plants
def bloom_strands(top, normal, width, length, strands, colors):
    """Bright trailing flowers spilling down a wall (geranium / bougainvillea feel)."""
    me = leaf_mesh('bright_leaf', (0.32, 0.5, 0.14))
    n = Vector(normal).normalized(); side = Vector((0, 0, 1)).cross(n).normalized()
    for s in range(strands):
        u = R.uniform(-0.5, 0.5) * width; L = length * R.uniform(0.4, 1.0)
        k = int(L / 0.035)
        for j in range(k):
            t = j / max(1, k - 1)
            p = Vector(top) + side * (u + math.sin(t * 5 + s) * 0.03) + n * (0.04 + 0.03 * math.sin(t * 3 + s)) - Vector((0, 0, t * L))
            o = link(bpy.data.objects.new('leaf', me)); o.location = p
            o.rotation_euler = (R.uniform(1.4, 2.8), R.uniform(-0.6, 0.6), R.uniform(0, 6.28))
            if R.random() < 0.45:
                fm = solid('bloom_' + str(colors[s % len(colors)]), colors[s % len(colors)], 0.5)
                sphere('bloom', p + n * 0.02, R.uniform(0.018, 0.028), fm, 8)

def flowers_patch(cx, cy, rx, ry, n, z=0.06, lilies=0):
    for _ in range(n):
        a, r = R.uniform(0, 6.28), math.sqrt(R.random())
        x, y = cx + math.cos(a) * r * rx, cy + math.sin(a) * r * ry
        if R.random() < 0.25:
            plant('flower_gazania', (x, y, z), R.uniform(0.12, 0.2))
        else:
            meadow_flower((x, y, z), R.uniform(0.1, 0.28), R.choice(PAL))
    for _ in range(lilies):
        a, r = R.uniform(0, 6.28), math.sqrt(R.random()) * 0.6
        garden_lily((cx + math.cos(a) * r * rx, cy + math.sin(a) * r * ry, z), R.uniform(0.35, 0.5), R.choice([(0.98, 0.95, 0.9), (0.98, 0.6, 0.2)]))

def flower_pot(p, r=0.16, h=0.32, n=9):
    pot(p, r, h, None)
    for _ in range(n):
        a, rr = R.uniform(0, 6.28), R.uniform(0, r * 0.7)
        meadow_flower((p[0] + math.cos(a) * rr, p[1] + math.sin(a) * rr, p[2] + h - 0.03), R.uniform(0.1, 0.25), R.choice(PAL))
    plant('flower_gazania', (p[0], p[1], p[2] + h - 0.03), 0.15)

def reeds(x, y, n=9):
    m = varied('reed', (0.4, 0.55, 0.18), 0.2, 0.6)
    for _ in range(n):
        h = R.uniform(0.25, 0.5)
        c = cyl('reed', (x + R.uniform(-0.08, 0.08), y + R.uniform(-0.08, 0.08), WL + h / 2), 0.006, h, m, verts=5, r2=0.002)
        c.rotation_euler = (R.uniform(-0.15, 0.15), R.uniform(-0.15, 0.15), 0)
    if R.random() < 0.6:
        cyl('cattail', (x, y, WL + 0.45), 0.014, 0.08, solid('cattail', (0.35, 0.22, 0.12), 0.8), verts=8)

def koi(x, y, a, col):
    fm = varied('koi_' + str(col), col, 0.1, 0.35)
    wm = solid('koi_white', (0.95, 0.93, 0.9), 0.35)
    z = WL - 0.05
    d = Vector((math.cos(a), math.sin(a), 0))
    sphere('koi_body', (x, y, z), 0.05, fm, 14, (1.0, 0.36, 0.3)).rotation_euler = (0, 0, a)
    sphere('koi_patch', Vector((x, y, z + 0.008)) + d * 0.015, 0.03, wm, 10, (1.0, 0.5, 0.35)).rotation_euler = (0, 0, a)
    t = sphere('koi_tail', Vector((x, y, z)) - d * 0.065, 0.03, fm, 10, (0.7, 0.9, 0.12))
    t.rotation_euler = (math.pi / 2, 0, a + math.pi / 2)

# ------------------------------------------------------------------ stage: shallow water over a pebbly floor
BX, BY = 10.0, 8.6
diorama_base(0, 0, BX, BY, pond_floor(), z=BOT)
water = water_mat()
wme = bpy.data.meshes.new('water'); wbm = bmesh.new(); bmesh.ops.create_grid(wbm, x_segments=1, y_segments=1, size=0.5)
wbm.to_mesh(wme); wbm.free(); wo = link(bpy.data.objects.new('water', wme)); wo.scale = (BX - 0.06, BY - 0.06, 1); wo.location = (0, 0, WL); wme.materials.append(water)

def platform(x0, x1, y0, y1, mat, top=0.06):
    box('platform', ((x0 + x1) / 2, (y0 + y1) / 2, (top + BOT) / 2), (x1 - x0, y1 - y0, top - BOT), mat, bevel=0.015)

# ================================================================== RIGHT / BACK building
BY0, BY1 = 2.35, 4.15
GZ, F1, F2 = 1.25, 1.2, 1.15
z1, z2, z3 = GZ, GZ + F1, GZ + F1 + F2
XB0, XB1 = -4.85, 3.85
RC = (BY1 - BY0) / 2
platform(XB0, XB1 + RC + 0.15, BY0 - 0.45, BY1, marble)
gw = box('B_ground', ((XB0 + XB1) / 2 + 0.2, BY1 - 0.55, GZ / 2 + 0.03), (XB1 - XB0 - 0.4, 1.1, GZ), sand, bevel=0.02)
for x in [-4.2 + k * 0.95 for k in range(9)]:
    if abs(x - (-1.35)) < 0.3: continue
    opening(gw, x, BY1 - 1.1, 0.1, 0.82, 1.0, cols=2, sill=False)
# timber pivot door with a brass pull
box('door', (-1.35, BY1 - 1.12, 0.6), (0.62, 0.06, 1.05), oakc, bevel=0.01)
box('door_pull', (-1.15, BY1 - 1.17, 0.6), (0.02, 0.02, 0.4), brass, bevel=0)
for x in [-4.6 + k * 1.15 for k in range(8)] + [XB1 + 0.6]:
    column(x, BY0 - 0.2, 0.06, GZ - 0.06)
# floor 1
B1 = box('B_f1', ((XB0 + XB1) / 2, (BY0 + BY1) / 2, z1 + F1 / 2), (XB1 - XB0, BY1 - BY0, F1), sand, bevel=0.02)
cyl('B_f1_round', (XB1, (BY0 + BY1) / 2, z1 + F1 / 2), RC, F1, clean_stone, verts=48)
slab(XB0 - 0.08, XB1, BY0 - 0.42, BY1, z1, 0.1)
cyl('slab_round', (XB1, (BY0 + BY1) / 2, z1), RC + 0.12, 0.1, clean_stone, verts=48)
f1x = (-4.2, -3.1, -2.0, -0.9, 0.2)
for x in f1x:
    opening(B1, x, BY0, z1 + 0.22, 0.72, 0.8, cols=2)
for k in range(5):
    a = -1.2 + k * 0.6
    box('round_glass', (XB1 + math.cos(a) * (RC - 0.02), (BY0 + BY1) / 2 + math.sin(a) * (RC - 0.02), z1 + 0.62), (0.03, 0.46, 0.8), glow, bevel=0, rot=(0, 0, a))
    box('round_mull', (XB1 + math.cos(a + 0.3) * RC, (BY0 + BY1) / 2 + math.sin(a + 0.3) * RC, z1 + 0.62), (0.04, 0.04, 0.82), iron, bevel=0)
# striped awnings over two windows, flower boxes with trailing blooms under others
def awning(x, w=0.9):
    m, n_, l_, b_ = node_mat('awning')
    tc = n_.new('ShaderNodeTexCoord'); wv = n_.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 9; wv.inputs['Distortion'].default_value = 0
    l_.new(tc.outputs['Object'], wv.inputs['Vector'])
    r = n_.new('ShaderNodeValToRGB'); r.color_ramp.interpolation = 'CONSTANT'
    r.color_ramp.elements[0].color = (0.93, 0.9, 0.83, 1); r.color_ramp.elements[1].position = 0.5; r.color_ramp.elements[1].color = (0.45, 0.58, 0.5, 1)
    l_.new(wv.outputs['Fac'], r.inputs['Fac']); l_.new(r.outputs['Color'], b_.inputs['Base Color']); b_.inputs['Roughness'].default_value = 0.9
    box('awning', (x, BY0 - 0.2, z1 + 1.08), (w, 0.45, 0.02), m, bevel=0, rot=(0.45, 0, 0))
    for sgn in (-1, 1):
        limb(Vector((x + sgn * w / 2, BY0, z1 + 1.12)), Vector((x + sgn * w / 2, BY0 - 0.4, z1 + 0.95)), 0.008, brass)
for x in (-3.1, -0.9):
    awning(x)
for x in (-4.2, -2.0, 0.2):
    box('fbox', (x, BY0 - 0.1, z1 + 0.16), (0.78, 0.18, 0.14), varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75), bevel=0.012)
    for k in range(6):
        meadow_flower((x - 0.3 + k * 0.12, BY0 - 0.1, z1 + 0.22), R.uniform(0.08, 0.16), R.choice([(0.96, 0.3, 0.38), (0.98, 0.55, 0.65)]))
    bloom_strands((x, BY0 - 0.1, z1 + 0.2), (0, -1, 0), 0.7, 0.55, 6, [(0.96, 0.3, 0.38), (0.98, 0.55, 0.65), (0.98, 0.95, 0.9)])
for x in (-3.65, -1.45, 0.75):
    sconce((x, BY0 - 0.01, z1 + 0.62), (0, -1, 0))
# oak bay box
bx0, bx1 = 1.2, 3.0
box('bay', ((bx0 + bx1) / 2, BY0 - 0.25, z1 + F1 / 2 + 0.05), (bx1 - bx0, 0.5, F1 - 0.1), oakc, bevel=0.02)
for k in range(int((bx1 - bx0) / 0.07)):
    box('bay_slat', (bx0 + 0.035 + k * 0.07, BY0 - 0.51, z1 + F1 / 2 + 0.05), (0.035, 0.03, F1 - 0.12), oakc, bevel=0.004)
box('bay_frame', ((bx0 + bx1) / 2 + 0.2, BY0 - 0.515, z1 + 0.62), (1.06, 0.01, 0.86), iron, bevel=0)
box('bay_glass', ((bx0 + bx1) / 2 + 0.2, BY0 - 0.53, z1 + 0.62), (1.0, 0.02, 0.8), glow, bevel=0)
box('bay_seat', ((bx0 + bx1) / 2 + 0.2, BY0 - 0.42, z1 + 0.3), (0.95, 0.15, 0.05), linen, bevel=0.01)
# climbing roses on the round end
ivy_patch((XB1 + 0.55, BY0 + 0.15, 0.06), (0.7, -0.7, 0), 0.6, 2.2, 450, 'rose_leaf', (0.2, 0.38, 0.1))
rm = solid('rose', (0.95, 0.5, 0.58), 0.5)
for _ in range(60):
    t = R.random()
    sphere('rose', (XB1 + 0.62 + R.uniform(-0.2, 0.2) + 0.05, BY0 + 0.08 + R.uniform(-0.2, 0.2), 0.1 + (t ** 1.3) * 2.0), 0.03, rm, 8)
# floor 2: set back, glass, terrace
x2a = -0.3
B2 = box('B_f2', ((x2a + XB1) / 2, (BY0 + BY1) / 2 + 0.25, z2 + F2 / 2), (XB1 - x2a, BY1 - BY0 - 0.5, F2), sand, bevel=0.02)
cyl('B_f2_round', (XB1, (BY0 + BY1) / 2 + 0.25, z2 + F2 / 2), RC - 0.25, F2, clean_stone, verts=48)
for x in (0.3, 1.3, 2.3, 3.3):
    opening(B2, x, BY0 + 0.5, z2 + 0.08, 0.8, 0.95, cols=2, sill=False)
slab(x2a - 0.1, XB1 + 0.01, BY0 + 0.15, BY1, z3, 0.12)
cyl('roof_round', (XB1, (BY0 + BY1) / 2 + 0.25, z3 + 0.006), RC - 0.13, 0.12, clean_stone, verts=48)
glass_rail(x2a, XB1, BY0 - 0.08, BY0 - 0.06, z2 + 0.05)
glass_rail(XB0 + 0.1, x2a, BY0 - 0.08, BY0 - 0.06, z2 + 0.05)
for x in (0.6, 2.0, 3.2):
    flower_pot((x, BY0 + 0.15, z2 + 0.05), 0.13, 0.24, 7)
# bookcase planters on the lower terrace: open shelves of books, flowers on top
BOOK = [(0.55, 0.2, 0.18), (0.22, 0.32, 0.45), (0.78, 0.65, 0.4), (0.3, 0.42, 0.3), (0.85, 0.82, 0.74), (0.6, 0.35, 0.2)]
def bookcase(x0, x1, y, z):
    w = x1 - x0; cx = (x0 + x1) / 2; H = 0.62; D = 0.36
    for (dx, sx) in ((-w / 2 + 0.02, 0.04), (w / 2 - 0.02, 0.04)):
        box('bc_side', (cx + dx, y, z + H / 2), (sx, D, H), oakc, bevel=0.005)
    for zz in (z + 0.02, z + 0.3, z + H - 0.06):
        box('bc_shelf', (cx, y, zz), (w, D, 0.04), oakc, bevel=0.005)
    box('bc_back', (cx, y + D / 2 - 0.01, z + H / 2), (w, 0.02, H), oakc, bevel=0)
    box('bc_trough', (cx, y, z + H + 0.02), (w, D, 0.14), oakc, bevel=0.01)
    for zz in (z + 0.04, z + 0.32):
        u = x0 + 0.06
        while u < x1 - 0.08:
            bw = R.uniform(0.025, 0.045); bh = R.uniform(0.17, 0.24)
            if R.random() < 0.08:
                u += 0.06; continue
            b = box('book', (u + bw / 2, y - 0.02, zz + bh / 2), (bw, 0.22, bh), (lambda i: varied('books%d' % i, BOOK[i], 0.18, 0.6))(R.randrange(len(BOOK))), bevel=0.002)
            if R.random() < 0.1: b.rotation_euler.y = 0.2
            u += bw + 0.003
    for _ in range(int(w * 24)):
        meadow_flower((R.uniform(x0 + 0.06, x1 - 0.06), y + R.uniform(-0.12, 0.12), z + H + 0.09), R.uniform(0.1, 0.3), R.choice(PAL))
    for _ in range(int(w * 3)):
        plant('flower_gazania', (R.uniform(x0 + 0.1, x1 - 0.1), y + R.uniform(-0.08, 0.08), z + H + 0.09), 0.2)
    bloom_strands((cx, y - D / 2, z + H + 0.08), (0, -1, 0), w * 0.8, 0.35, int(w * 4), [(0.98, 0.95, 0.9), (0.72, 0.55, 0.95)])
bookcase(XB0 + 0.4, XB0 + 2.0, BY1 - 0.3, z2 + 0.06)
bookcase(-2.4, -0.8, BY1 - 0.3, z2 + 0.06)
# roof deck on top of floor 2: loungers, a small pergola with a lantern
box('top_deck', (1.6, (BY0 + BY1) / 2 + 0.3, z3 + 0.075), (3.2, 1.0, 0.03), wood('deck', (0.52, 0.37, 0.24), 5), bevel=0.004)
for x in (0.6, 1.4):
    box('lounger', (x, (BY0 + BY1) / 2 + 0.25, z3 + 0.17), (0.5, 0.95, 0.12), oakc, bevel=0.01, rot=(0, 0, 0))
    box('lounger_pad', (x, (BY0 + BY1) / 2 + 0.25, z3 + 0.25), (0.46, 0.9, 0.05), linen, bevel=0.02)
for (x, y) in ((2.4, BY0 + 0.45), (3.4, BY0 + 0.45), (2.4, BY1 - 0.15), (3.4, BY1 - 0.15)):
    box('tp_post', (x, y, z3 + 0.6), (0.05, 0.05, 1.1), oakc, bevel=0.005)
for k in range(6):
    box('tp_slat', (2.4 + k * 0.2, (BY0 + BY1) / 2 + 0.25, z3 + 1.16), (0.04, 1.4, 0.05), oakc, bevel=0.004)
moroccan((2.9, (BY0 + BY1) / 2 + 0.25, z3 + 0.85), 1.1, chain=0.15)
flower_pot((3.5, BY1 - 0.35, z3 + 0.06), 0.15, 0.3, 9)
# lanterns under the colonnade
for x in (-3.9, -2.6, -0.2, 1.3, 2.6):
    moroccan((x, BY0 - 0.05, GZ - 0.3), 1.0, chain=0.18)
for x in (-3.4, 0.6):
    box('bench', (x, BY1 - 1.35, 0.3), (1.0, 0.36, 0.06), oakc, bevel=0.01)
    box('bench_pad', (x, BY1 - 1.35, 0.35), (0.95, 0.32, 0.04), sage_cushion, bevel=0.015)
    for d in (-0.4, 0.4):
        box('bench_leg', (x + d, BY1 - 1.35, 0.17), (0.05, 0.3, 0.22), iron, bevel=0)
for x in (-4.0, -2.2, 1.9, 3.3):
    flower_pot((x, BY0 + 0.25, 0.06), 0.16, 0.34, 10)

# ================================================================== LEFT building (on columns, dry marble floor)
LX0, LX1 = -4.85, -2.0
LY0, LY1 = -3.45, 1.25
LZ, LH = 1.35, 1.25
RZ = LZ + LH + 0.15
platform(LX0, LX1 + 0.12, LY0 - 0.1, LY1 + 1.1, marble)
box('L_core', (LX0 + 0.45, LY1 - 0.9, LZ / 2 + 0.03), (0.9, 1.6, LZ), sand, bevel=0.02)
for (x, y) in ((LX1 - 0.15, LY0 + 0.15), (LX1 - 0.15, LY1 - 0.15), (LX0 + 0.25, LY0 + 0.15), (LX1 - 0.15, -1.1)):
    column(x, y, 0.06, LZ - 0.06, 0.075)
slab(LX0 - 0.05, LX1 + 0.08, LY0 - 0.08, LY1 + 0.05, LZ, 0.12)
box('L_f1', ((LX0 + LX1) / 2, (LY0 + LY1) / 2, LZ + LH / 2 + 0.06), (LX1 - LX0, LY1 - LY0, LH), oakc, bevel=0.02)
for k in range(int((LY1 - LY0) / 0.09)):
    y = LY0 + 0.045 + k * 0.09
    if -2.9 < y < -0.3: continue
    box('batten', (LX1 + 0.02, y, LZ + LH / 2 + 0.06), (0.03, 0.04, LH - 0.04), oakc, bevel=0.003)
box('L_glass', (LX1 + 0.01, -1.6, LZ + LH / 2 + 0.06), (0.02, 2.5, LH - 0.18), glow, bevel=0)
for y in (-2.85, -2.2, -1.6, -1.0, -0.35):
    box('L_mull', (LX1 + 0.02, y, LZ + LH / 2 + 0.06), (0.03, 0.03, LH - 0.16), iron, bevel=0)
box('L_glass_f', (-3.4, LY0 - 0.01, LZ + LH / 2 + 0.06), (1.6, 0.02, LH - 0.18), glow, bevel=0)
for x in (-4.2, -3.4, -2.6):
    box('L_mull', (x, LY0 - 0.02, LZ + LH / 2 + 0.06), (0.03, 0.03, LH - 0.16), iron, bevel=0)
# planter ledge under the big window with trailing blooms
box('L_ledge', (LX1 + 0.12, -1.6, LZ + 0.12), (0.2, 2.6, 0.12), oakc, bevel=0.01)
for k in range(18):
    meadow_flower((LX1 + 0.12, -2.8 + k * 0.14, LZ + 0.17), R.uniform(0.06, 0.14), R.choice(PAL))
bloom_strands((LX1 + 0.16, -1.6, LZ + 0.12), (1, 0, 0), 2.4, 0.5, 10, [(0.95, 0.4, 0.6), (0.98, 0.95, 0.9), (0.98, 0.62, 0.3)])
sconce((LX1 + 0.01, LY0 + 0.45, LZ + 0.75), (1, 0, 0))
slab(LX0 - 0.1, LX1 + 0.12, LY0 - 0.12, LY1 + 0.08, LZ + LH + 0.1, 0.1)
box('deck', ((LX0 + LX1) / 2, (LY0 + LY1) / 2, RZ + 0.01), (LX1 - LX0 - 0.1, LY1 - LY0 - 0.1, 0.03), wood('deck', (0.52, 0.37, 0.24), 5), bevel=0.005)
glass_rail(LX1 - 0.03, LX1 - 0.01, LY0, LY1, RZ)
glass_rail(LX0, LX1, LY0 + 0.02, LY0 + 0.04, RZ)
# greenhouse full of flowers
gx0, gx1, gy0, gy1 = -4.6, -2.55, -3.1, -0.4
gh, gr = 0.95, 0.6
gl = solid('gh_glass', (0.88, 0.95, 0.93), 0.03); gl.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.93
fr = solid('gh_frame', (0.93, 0.93, 0.9), 0.35)
box('gh_walls', ((gx0 + gx1) / 2, (gy0 + gy1) / 2, RZ + gh / 2), (gx1 - gx0, gy1 - gy0, gh), gl, bevel=0)
me = bpy.data.meshes.new('ghr'); bm_ = bmesh.new(); cx_ = (gx0 + gx1) / 2
v = [bm_.verts.new(p) for p in [(gx0, gy0, RZ + gh), (cx_, gy0, RZ + gh + gr), (gx1, gy0, RZ + gh), (gx0, gy1, RZ + gh), (cx_, gy1, RZ + gh + gr), (gx1, gy1, RZ + gh)]]
for f_ in ([v[0], v[1], v[4], v[3]], [v[1], v[2], v[5], v[4]], [v[0], v[1], v[2]], [v[3], v[5], v[4]]):
    bm_.faces.new(f_)
bm_.to_mesh(me); bm_.free(); me.materials.append(gl); link(bpy.data.objects.new('gh_roofglass', me))
for k in range(9):
    y = gy0 + k * (gy1 - gy0) / 8
    limb(Vector((gx0, y, RZ + gh)), Vector((cx_, y, RZ + gh + gr)), 0.015, fr); limb(Vector((cx_, y, RZ + gh + gr)), Vector((gx1, y, RZ + gh)), 0.015, fr)
    box('gh_post', (gx0, y, RZ + gh / 2), (0.03, 0.03, gh), fr, bevel=0); box('gh_post', (gx1, y, RZ + gh / 2), (0.03, 0.03, gh), fr, bevel=0)
for z in (RZ + 0.02, RZ + gh / 2, RZ + gh):
    for (a0, b0, a1, b1) in ((gx0, gy0, gx1, gy0), (gx0, gy1, gx1, gy1), (gx0, gy0, gx0, gy1), (gx1, gy0, gx1, gy1)):
        box('gh_rail', ((a0 + a1) / 2, (b0 + b1) / 2, z), (max(a1 - a0, 0.025), max(b1 - b0, 0.025), 0.025), fr, bevel=0)
limb(Vector((cx_, gy0, RZ + gh + gr)), Vector((cx_, gy1, RZ + gh + gr)), 0.02, fr)
for y in (gy0 + 0.35, gy1 - 0.35):
    box('gh_bench', (cx_, y, RZ + 0.3), (gx1 - gx0 - 0.3, 0.4, 0.05), oakc, bevel=0.005)
    for k in range(7):
        x = gx0 + 0.3 + k * (gx1 - gx0 - 0.6) / 6
        flower_pot((x, y, RZ + 0.33), 0.08, 0.13, 4)
flowers_patch(cx_, (gy0 + gy1) / 2, 0.55, 0.5, 45, z=RZ + 0.03, lilies=5)
moroccan((cx_, (gy0 + gy1) / 2, RZ + gh + 0.2), 1.0, chain=0.2)
ivy_patch((gx1 - 0.05, -1.75, RZ), (1, 0, 0), 2.4, 0.9, 400, 'vine', (0.3, 0.46, 0.12))
room_light((cx_, (gy0 + gy1) / 2, RZ + 0.7), 50, (1.0, 0.8, 0.55))
# under the floating floor: lounge with lanterns
box('rug', (-3.35, -1.6, 0.065), (1.5, 1.9, 0.01), solid('rug', (0.72, 0.55, 0.42), 0.9), bevel=0)
box('long_bench', (-3.0, -1.6, 0.3), (0.45, 1.6, 0.08), oakc, bevel=0.01)
box('long_pad', (-3.0, -1.6, 0.36), (0.42, 1.55, 0.06), terracotta_cushion, bevel=0.02)
cyl('low_table', (-3.7, -1.6, 0.28), 0.32, 0.05, marble, verts=32, bevel=0.01)
cyl('low_table_base', (-3.7, -1.6, 0.14), 0.1, 0.24, iron, verts=16)
for (x, y) in ((-3.0, -2.6), (-3.6, -0.6), (-2.5, -1.6)):
    moroccan((x, y, LZ - 0.32), 0.95, chain=0.22)
for y in (-3.0, -0.2):
    flower_pot((-2.35, y, 0.06), 0.17, 0.36, 10)

# floating stair
SY0, SY1 = LY1 + 0.15, BY0 - 0.15
n = 14; rise = RZ / n; run = 0.24
for k in range(n):
    box('tread', (-0.75 - k * run, (SY0 + SY1) / 2, (k + 1) * rise), (run + 0.02, SY1 - SY0, 0.05), oakc, bevel=0.006)
limb(Vector((-0.75 + run / 2, SY0 + 0.03, 0.06)), Vector((-0.75 - n * run, SY0 + 0.03, RZ)), 0.035, iron)
for k in range(0, n, 2):
    box('stair_rail_post', (-0.75 - k * run, SY0 + 0.02, (k + 1) * rise + 0.45), (0.02, 0.02, 0.9), iron, bevel=0)
box('landing', ((-0.75 - n * run + LX0) / 2 + 0.1, (SY0 + SY1) / 2, RZ), (abs(-0.75 - n * run - LX0) + 0.2, SY1 - SY0 + 0.3, 0.1), marble, bevel=0.01)
platform(-1.1, -0.35, LY1 + 0.05, BY0 - 0.4, marble)

# ================================================================== island lounge
IX, IY, IRX, IRY = 1.05, -0.75, 1.45, 1.05
isl = cyl('island_soil', (IX, IY, (BOT + 0.04) / 2), 1.0, 0.04 - BOT, varied('island_bank', (0.45, 0.38, 0.3), 0.1, 0.9, bump=0.4), verts=64)
isl.scale = (IRX, IRY, 1)
top = cyl('island_grass', (IX, IY, 0.05), 1.0, 0.02, grass_mat(), verts=64); top.scale = (IRX - 0.03, IRY - 0.03, 1)
for k in range(56):
    a = k / 56 * 2 * math.pi
    sphere('isl_stone', (IX + math.cos(a) * IRX, IY + math.sin(a) * IRY, 0.02), R.uniform(0.07, 0.11), stone if k % 4 else marble, 10,
           (R.uniform(1.0, 1.4), R.uniform(0.8, 1.1), R.uniform(0.5, 0.7)))
# woven nest daybed
nx, ny = IX - 0.45, IY - 0.05
nest = sphere('nest', (nx, ny, 0.3), 0.52, rattan, 32, (1, 1, 0.55))
cut(nest, box('nest_cut', (nx, ny, 0.62), (1.2, 1.2, 0.6), None, bevel=0))
cut(nest, sphere('nest_in', (nx, ny, 0.34), 0.47, None, 24, (1, 1, 0.5)))
sphere('nest_mattress', (nx, ny, 0.3), 0.44, linen, 24, (1, 1, 0.18))
for k, (dx, dy, m) in enumerate(((-0.25, 0.2, terracotta_cushion), (0.05, 0.3, sage_cushion), (0.28, 0.15, linen), (-0.3, -0.12, sage_cushion))):
    c = sphere('pillow', (nx + dx, ny + dy, 0.42), 0.13, m, 16, (1, 0.45, 0.75)); c.rotation_euler = (0.4, 0, math.atan2(dy, dx) + math.pi / 2)
box('throw', (nx + 0.1, ny - 0.15, 0.37), (0.4, 0.3, 0.02), terracotta_cushion, bevel=0.01, rot=(0.1, 0, 0.4))
# timber arch with a hanging egg chair and a paper-lantern cluster
ax, ay = IX + 0.65, IY + 0.05
pts = [Vector((ax - 0.55 + 1.1 * t, ay, 0.06 + 1.55 * math.sin(math.pi * t))) for t in [k / 10 for k in range(11)]]
for a, b in zip(pts, pts[1:]):
    limb(a, b, 0.045, oakc)
apex = Vector((ax, ay, 1.61))
cyl('egg_rope', (ax, ay, 1.38), 0.006, 0.45, iron, verts=6)
egg = sphere('egg', (ax, ay, 0.85), 0.32, rattan, 32, (1, 1, 1.25))
cut(egg, box('egg_open', (ax, ay - 0.3, 0.85), (0.7, 0.5, 0.6), None, bevel=0))
cut(egg, sphere('egg_in', (ax, ay + 0.03, 0.85), 0.28, None, 24, (1, 1, 1.2)))
sphere('egg_cushion', (ax, ay + 0.02, 0.66), 0.25, linen, 20, (1, 1, 0.3))
sphere('egg_pillow', (ax, ay + 0.14, 0.86), 0.16, sage_cushion, 16, (1, 0.4, 0.9))
paper_cluster((ax - 0.35, ay, 1.3), 3)
# low round table with tea, poufs, rug
cyl('isl_rug', (IX + 0.1, IY - 0.45, 0.065), 0.55, 0.01, solid('rug2', (0.8, 0.66, 0.5), 0.95), verts=40)
cyl('tea_table', (IX + 0.1, IY - 0.45, 0.22), 0.24, 0.04, oakc, verts=32, bevel=0.01)
cyl('tea_table_leg', (IX + 0.1, IY - 0.45, 0.13), 0.05, 0.16, oakc, verts=12)
cyl('teapot', (IX + 0.05, IY - 0.42, 0.29), 0.05, 0.08, solid('ceramic', (0.85, 0.8, 0.72), 0.3), verts=16)
for d in (0.12, -0.06):
    cyl('cup', (IX + 0.16 + d * 0.3, IY - 0.55, 0.265), 0.022, 0.03, solid('ceramic', (0.85, 0.8, 0.72), 0.3), verts=12)
cyl('isl_jar', (IX + 0.2, IY - 0.38, 0.28), 0.03, 0.07, solid('jar', (1, 0.8, 0.5), 0.2, emit=(1, 0.6, 0.25), strength=8), verts=12)
for (dx, dy, m) in ((0.55, -0.75, terracotta_cushion), (-0.25, -0.95, sage_cushion)):
    cyl('pouf', (IX + dx, IY + dy, 0.15), 0.17, 0.18, m, verts=24, bevel=0.05)
# small cherry on the island and flowers all round
cherry_tree((IX + 1.0, IY + 0.55, 0.06), 1.7, 0.75, lean=-0.1, lanterns=0)
moroccan((IX + 0.75, IY + 0.4, 1.1), 0.9, chain=0.15)
flowers_patch(IX, IY, IRX - 0.15, IRY - 0.15, 120, lilies=6)

# ================================================================== paths through the water
def plank_walk(pts, w=0.42):
    """Boardwalk on posts following a polyline."""
    deck = wood('boards', (0.55, 0.4, 0.27), 6)
    for a, b in zip(pts, pts[1:]):
        a, b = Vector((*a, 0)), Vector((*b, 0)); d = b - a; L = d.length; ang = math.atan2(d.y, d.x)
        nb = int(L / 0.1)
        for k in range(nb):
            c = a + d * ((k + 0.5) / nb)
            box('plank', (c.x, c.y, 0.045), (L / nb - 0.012, w, 0.035), deck, bevel=0.004, rot=(0, 0, ang))
        for t in (0.0, 0.5):
            c = a + d * t
            for sgn in (-1, 1):
                q = c + Vector((-math.sin(ang), math.cos(ang), 0)) * sgn * (w / 2 - 0.03)
                cyl('wpost', (q.x, q.y, (BOT + 0.03) / 2), 0.025, 0.03 - BOT, oakc, verts=8)

def stepping(pts, r=0.19):
    for (x, y) in pts:
        c = cyl('stepstone', (x, y, (BOT + 0.05) / 2), r, 0.05 - BOT, travertine, verts=28, bevel=0.015)
        c.scale = (1.0, R.uniform(0.75, 0.95), 1); c.rotation_euler.z = R.uniform(0, 3)

def arched_bridge(a, b, w=0.45, h=0.22):
    a, b = Vector(a), Vector(b); d = b - a; L = d.length; ang = math.atan2(d.y, d.x)
    nb = int(L / 0.09)
    for k in range(nb):
        t = (k + 0.5) / nb
        c = a + d * t
        z = 0.05 + h * math.sin(math.pi * t)
        box('br_plank', (c.x, c.y, z), (L / nb - 0.01, w, 0.035), oakc, bevel=0.004, rot=(0, -math.cos(math.pi * t) * h * math.pi / L * 0.9, ang))
    for sgn in (-1, 1):
        off = Vector((-math.sin(ang), math.cos(ang), 0)) * sgn * (w / 2)
        rp = [a + d * (k / 12) + off + Vector((0, 0, 0.05 + h * math.sin(math.pi * k / 12) + 0.32)) for k in range(13)]
        for p, q in zip(rp, rp[1:]):
            limb(p, q, 0.014, brass)
        for k in range(0, 13, 3):
            p = rp[k]; limb(p - Vector((0, 0, 0.32)), p, 0.012, brass)

plank_walk([(0.75, -4.25), (0.8, -3.3), (1.0, -2.45), (IX - 0.05, IY - IRY + 0.05)])
stepping([(IX + IRX - 0.05, IY - 0.3), (2.85, -0.55), (3.25, -0.25), (3.45, 0.25), (3.35, 0.75), (3.1, 1.25), (2.95, 1.75)])
stepping([(4.55, -4.0), (4.2, -3.55), (3.8, -3.15), (3.35, -2.8), (2.9, -2.45), (2.45, -2.05), (2.1, -1.7)])
arched_bridge((IX - IRX + 0.05, IY - 0.15, 0), (LX1 + 0.15, -1.0, 0))
stepping([(IX - 0.3, IY + IRY), (IX - 0.55, IY + IRY + 0.45), (-0.2, 0.95), (-0.6, 1.25)])
for (x, y, f) in ((0.55, -3.8, 0.0), (1.15, -2.9, math.pi), (3.75, -2.95, math.pi / 2), (2.6, -0.25, math.pi), (3.75, 1.0, math.pi), (-1.1, -1.35, -math.pi / 2)):
    platform(x - 0.09, x + 0.09, y - 0.09, y + 0.09, travertine, top=0.06)
    globe_hook(x, y, 0.95, f)

# water life: waterlilies, floating candles, koi, reeds
def clear(x, y):
    if (x - IX) ** 2 / (IRX + 0.25) ** 2 + (y - IY) ** 2 / (IRY + 0.25) ** 2 < 1: return False
    if x < LX1 + 0.4 and y < LY1 + 1.1: return False
    if y > BY0 - 0.6: return False
    return True
placed = 0
while placed < 34:
    x, y = R.uniform(-1.8, 4.7), R.uniform(-4.1, 2.0)
    if clear(x, y) and abs(x - 0.85) > 0.35:
        waterlily((x, y, WL + 0.01), R.uniform(0.08, 0.14)); placed += 1
for (x, y) in ((-0.6, -2.8), (2.2, -3.4), (4.3, -1.8), (2.4, 0.6), (-1.2, 0.2), (4.0, 1.5), (0.0, -3.9), (3.0, -1.2)):
    floating_candle(x, y)
for (x, y, a, c) in ((1.8, -2.7, 0.6, (0.95, 0.45, 0.15)), (2.1, -2.95, 0.9, (0.95, 0.95, 0.9)), (-0.8, -3.4, 2.6, (0.9, 0.3, 0.1)),
                     (3.9, -0.9, 4.0, (0.98, 0.6, 0.2)), (0.1, 0.5, 5.2, (0.95, 0.4, 0.15)), (4.2, -3.0, 1.8, (0.95, 0.95, 0.9))):
    koi(x, y, a, c)
for (x, y) in ((-1.7, -3.9), (-1.75, 0.5), (4.75, -0.6), (4.7, 2.0), (2.0, -4.1), (-1.6, -2.2)):
    reeds(x, y)

# cherries on little stone islets
for (x, y, h, cr) in ((-0.9, -3.15, 2.0, 0.9), (4.25, -1.75, 2.2, 1.0)):
    c = cyl('islet', (x, y, (BOT + 0.06) / 2), 0.42, 0.06 - BOT, stone, verts=24, bevel=0.03)
    cyl('islet_grass', (x, y, 0.065), 0.38, 0.015, grass_mat(), verts=24)
    flowers_patch(x, y, 0.3, 0.3, 18, z=0.07)
    cherry_tree((x, y, 0.07), h, cr, lean=0.1, lanterns=0)
    moroccan((x + 0.35, y - 0.2, 1.15), 0.9, chain=0.2)

# interiors glow
for x in (-3.5, -1.5, 0.5, 2.5, 4.0):
    room_light((x, (BY0 + BY1) / 2, z1 + 0.6), 60)
for x in (0.5, 2.5):
    room_light((x, (BY0 + BY1) / 2 + 0.25, z2 + 0.6), 60)
for x in (-3.5, -1.0, 2.0):
    room_light((x, BY1 - 0.55, 0.7), 50)
room_light(((LX0 + LX1) / 2, -1.6, LZ + 0.7), 90)

lighting(sc, sun_rot=(math.radians(68), 0, math.radians(-55)), sun_energy=2.5, sun_color=(1.0, 0.66, 0.42),
         bg_top=(0.3, 0.42, 0.5), bg_bottom=(0.9, 0.78, 0.68), hdri_strength=0.35)
iso_camera(sc, (-0.1, 0.0, 1.5), 13.2)
render(sc, OUT, SAMPLES)
