"""House v4: two buildings of different heights wrapped around an open garden.
Right/back: tall stone house on a marble colonnade, curved end, set-back top
floor, oak-clad bay. Left: lower timber house floating on slim columns with a
flower greenhouse on its roof. Floating stair between them. Big pond with
stepping stones and a fountain, bent weeping willow, cherries, meadow flowers.
Usage: ASSETS=<assets-raw> python house_v4.py <out.png> [samples]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

OUT = sys.argv[-2] if sys.argv[-1].isdigit() else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 64
sc = reset()
from garden import *

sand = stucco('sandstone', (0.84, 0.77, 0.66), dirt=(0.66, 0.6, 0.52))
oakc = wood('oak_clad', (0.6, 0.42, 0.27), 10, axis='Z')

def marble_mat():
    m, n, l, b = node_mat('marble')
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; nz.inputs['Detail'].default_value = 8; nz.inputs['Distortion'].default_value = 3.5
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 9
    l.new(nz.outputs['Color'], wv.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = 0.0; r.color_ramp.elements[0].color = (0.78, 0.76, 0.73, 1)
    r.color_ramp.elements[1].position = 0.05; r.color_ramp.elements[1].color = (0.95, 0.94, 0.91, 1)
    l.new(wv.outputs['Fac'], r.inputs['Fac']); l.new(r.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.18; b.inputs['Coat Weight'].default_value = 0.3
    return m
marble = marble_mat()
glow = glass_glow()

def opening(wall, x, y, z, w, h, axis='y', side=-1, cols=2, rows=1, depth=0.9, sill=True):
    """Clean opening: cut, warm glass, slim steel frame."""
    cut(wall, box('oc', (x, y, z + h / 2), (w, depth, h) if axis == 'y' else (depth, w, h), None, bevel=0))
    off = Vector((0, -side * 0.07, 0)) if axis == 'y' else Vector((-side * 0.07, 0, 0))
    P = lambda dx, dz: Vector((x, y, z)) + off + (Vector((dx, 0, dz)) if axis == 'y' else Vector((0, dx, dz)))
    S = lambda sx, sz, t=0.025: (sx, t, sz) if axis == 'y' else (t, sx, sz)
    box('glass', P(0, h / 2), S(w, h, 0.01), glow, bevel=0)
    t = 0.025
    for dx in [-w / 2 + t / 2, w / 2 - t / 2] + [-w / 2 + c * w / cols for c in range(1, cols)]:
        box('mull', P(dx, h / 2), S(t, h), iron, bevel=0)
    for dz in [t / 2, h - t / 2] + [r * h / rows for r in range(1, rows)]:
        box('mull', P(0, dz), S(w, t), iron, bevel=0)
    if sill:
        so = Vector((0, side * 0.03, 0)) if axis == 'y' else Vector((side * 0.03, 0, 0))
        box('sill', Vector((x, y, z - 0.02)) + so, S(w + 0.08, 0.04, 0.12), marble, bevel=0.008)

def column(x, y, z0, h, r=0.08):
    cyl('col', (x, y, z0 + h / 2), r, h, marble, verts=24)
    cyl('col_base', (x, y, z0 + 0.03), r * 1.5, 0.06, marble, verts=24, bevel=0.01)
    cyl('col_cap', (x, y, z0 + h - 0.03), r * 1.5, 0.06, marble, verts=24, bevel=0.01)

def slab(x0, x1, y0, y1, z, t=0.1, mat=None):
    box('slab', ((x0 + x1) / 2, (y0 + y1) / 2, z), (x1 - x0, y1 - y0, t), mat or marble, bevel=0.012)

def glass_rail(x0, x1, y0, y1, z, h=0.42):
    """Slim steel railing: top rail, mid rail, thin posts."""
    L = max(x1 - x0, y1 - y0); along_x = (x1 - x0) >= (y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for zz, t in ((z + h, 0.025), (z + h * 0.5, 0.012)):
        box('rail', (cx, cy, zz), (L, 0.025, t) if along_x else (0.025, L, t), iron, bevel=0)
    n = int(L / 0.6) + 1
    for k in range(n + 1):
        u = k / n
        q = (x0 + (x1 - x0) * u, cy) if along_x else (cx, y0 + (y1 - y0) * u)
        box('rail_post', (q[0], q[1], z + h / 2), (0.02, 0.02, h), iron, bevel=0)

def meadow_flower(p, h, col):
    stem = solid('mstem', (0.22, 0.38, 0.12), 0.6)
    cyl('mstem', (p[0], p[1], p[2] + h / 2), 0.006, h, stem, verts=5)
    fm = solid('mflower_' + str(col), col, 0.5)
    top = Vector((p[0], p[1], p[2] + h))
    for k in range(5):
        a = k / 5 * 2 * math.pi
        pe = sphere('mpetal', top + Vector((math.cos(a) * 0.022, math.sin(a) * 0.022, 0)), 0.024, fm, 8, (1, 0.45, 0.15))
        pe.rotation_euler = (0, 0, a)
    sphere('mheart', top + Vector((0, 0, 0.008)), 0.011, solid('mheart', (0.95, 0.72, 0.2), 0.5), 8)

def drift(cx, cy, rx, ry, n, palette, hmin=0.12, hmax=0.3, lilies=0):
    for _ in range(n):
        a, r = R.uniform(0, 6.28), math.sqrt(R.random())
        x, y = cx + math.cos(a) * r * rx, cy + math.sin(a) * r * ry
        if R.random() < 0.3:
            plant(R.choice(['flower_gazania', 'periwinkle_plant']), (x, y, 0), R.uniform(0.12, 0.22))
        else:
            meadow_flower((x, y, 0), R.uniform(hmin, hmax), R.choice(palette))
    for _ in range(lilies):
        a, r = R.uniform(0, 6.28), math.sqrt(R.random()) * 0.6
        garden_lily((cx + math.cos(a) * r * rx, cy + math.sin(a) * r * ry, 0), R.uniform(0.35, 0.55), R.choice([(0.98, 0.95, 0.9), (0.98, 0.6, 0.2)]))

def willow(base, height=2.9, crown=1.35):
    """Weeping willow with a bent, visible trunk and airy curtains."""
    bark = varied('willow_bark', (0.33, 0.27, 0.21), 0.1, 0.9, bump=0.6, bump_scale=30)
    bx, by, bz = base
    pts = [Vector((bx + 0.55 * math.sin(t * 1.9) * t, by - 0.25 * t * t, bz + t * height * 0.72)) for t in (k / 7 for k in range(8))]
    trunk(pts, 0.17, bark)
    top = pts[-1]
    me = leaf_shape('willow2', [(0, 0, 0), (0.007, 0.03, 0), (0.005, 0.07, 0), (0, 0.09, 0), (-0.005, 0.07, 0), (-0.007, 0.03, 0)], (0.42, 0.56, 0.16), 0.2)
    tips = []
    for i in range(8):
        a = i / 8 * 2 * math.pi + R.uniform(-0.2, 0.2)
        mid = top + Vector((math.cos(a) * crown * 0.35, math.sin(a) * crown * 0.35, 0.45))
        tip = top + Vector((math.cos(a) * crown * 0.75, math.sin(a) * crown * 0.75, 0.38))
        limb(top, mid, 0.06, bark); limb(mid, tip, 0.035, bark); tips.append((mid, tip))
    for (mid, tip) in tips:
        for k in range(30):
            t = R.random()
            s0 = mid.lerp(tip, t) + Vector((R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12), 0.02))
            L = R.uniform(0.7, 1.7)
            n = int(L / 0.06)
            out = (s0 - top); out.z = 0; out.normalize()
            for j in range(n):
                u = j / n
                p = s0 + out * (0.08 * u) - Vector((0, 0, u * L))
                o = link(bpy.data.objects.new('wl', me)); o.location = p
                o.rotation_euler = (R.uniform(2.7, 3.5), R.uniform(-0.4, 0.4), R.uniform(0, 6.28))
                s = R.uniform(1.0, 1.5); o.scale = (s, s, s)

# ------------------------------------------------------------------ ground
diorama_base(0, 0, 10.0, 8.6, grass_mat())

# ================================================================== RIGHT / BACK building (tall)
BY0, BY1 = 2.35, 4.15
GZ, F1, F2 = 1.25, 1.2, 1.15          # ground (open colonnade), floor 1, floor 2
z1, z2, z3 = GZ, GZ + F1, GZ + F1 + F2
XB0, XB1 = -4.85, 3.85                # + rounded end beyond XB1
RC = (BY1 - BY0) / 2
# ground floor: glass wall set well back behind a marble colonnade
gw = box('B_ground', ((XB0 + XB1) / 2 + 0.2, BY1 - 0.55, GZ / 2), (XB1 - XB0 - 0.4, 1.1, GZ), sand, bevel=0.02)
for x in [-4.2 + k * 0.95 for k in range(9)]:
    opening(gw, x, BY1 - 1.1, 0.06, 0.82, 1.05, cols=2, sill=False)
slab(XB0, XB1, BY0 - 0.1, BY1, 0.03, 0.06, travertine)
for x in [-4.6 + k * 1.15 for k in range(8)] + [XB1 + 0.6]:
    column(x, BY0 + 0.12, 0.06, GZ - 0.06)
# floor 1 (stone) with a rounded end and an oak-clad bay
B1 = box('B_f1', ((XB0 + XB1) / 2, (BY0 + BY1) / 2, z1 + F1 / 2), (XB1 - XB0, BY1 - BY0, F1), sand, bevel=0.02)
B1r = cyl('B_f1_round', (XB1, (BY0 + BY1) / 2, z1 + F1 / 2), RC, F1, sand, verts=48)
slab(XB0 - 0.08, XB1, BY0 - 0.12, BY1, z1, 0.1)
cyl('slab_round', (XB1, (BY0 + BY1) / 2, z1), RC + 0.12, 0.1, marble, verts=48)
for x in (-4.2, -3.1, -2.0, -0.9, 0.2):
    opening(B1, x, BY0, z1 + 0.22, 0.72, 0.8, cols=2)
for k in range(5):  # curved ribbon window on the round end
    a = -1.2 + k * 0.6
    box('round_glass', (XB1 + math.cos(a) * (RC - 0.02), (BY0 + BY1) / 2 + math.sin(a) * (RC - 0.02), z1 + 0.62), (0.03, 0.46, 0.8), glow, bevel=0, rot=(0, 0, a))
    box('round_mull', (XB1 + math.cos(a + 0.3) * RC, (BY0 + BY1) / 2 + math.sin(a + 0.3) * RC, z1 + 0.62), (0.04, 0.04, 0.82), iron, bevel=0)
# oak bay box cantilevered over the colonnade
bx0, bx1 = 1.2, 3.0
box('bay', ((bx0 + bx1) / 2, BY0 - 0.25, z1 + F1 / 2 + 0.05), (bx1 - bx0, 0.5, F1 - 0.1), oakc, bevel=0.02)
for k in range(int((bx1 - bx0) / 0.07)):
    box('bay_slat', (bx0 + 0.035 + k * 0.07, BY0 - 0.51, z1 + F1 / 2 + 0.05), (0.035, 0.03, F1 - 0.12), oakc, bevel=0.004)
box('bay_glass', ((bx0 + bx1) / 2 + 0.2, BY0 - 0.53, z1 + 0.62), (1.0, 0.02, 0.8), glow, bevel=0)
box('bay_frame', ((bx0 + bx1) / 2 + 0.2, BY0 - 0.515, z1 + 0.62), (1.06, 0.01, 0.86), iron, bevel=0)
# floor 2: set back, mostly glass, behind a terrace with glass rail, only on the right part
x2a = -0.3
B2 = box('B_f2', ((x2a + XB1) / 2, (BY0 + BY1) / 2 + 0.25, z2 + F2 / 2), (XB1 - x2a, BY1 - BY0 - 0.5, F2), sand, bevel=0.02)
cyl('B_f2_round', (XB1, (BY0 + BY1) / 2 + 0.25, z2 + F2 / 2), RC - 0.25, F2, sand, verts=48)
for x in (0.3, 1.3, 2.3, 3.3):
    opening(B2, x, BY0 + 0.5, z2 + 0.08, 0.8, 0.95, cols=2, sill=False)
slab(x2a - 0.1, XB1 + 0.01, BY0 + 0.15, BY1, z3, 0.12)
cyl('roof_round', (XB1, (BY0 + BY1) / 2 + 0.25, z3 + 0.006), RC - 0.13, 0.12, marble, verts=48)
glass_rail(x2a, XB1, BY0 - 0.08, BY0 - 0.06, z2 + 0.05)
for x in (0.6, 2.0, 3.2):
    pot((x, BY0 + 0.15, z2 + 0.05), 0.14, 0.26, R.choice(['fern_02', 'shrub_sorrel_01']), 0.45)
# lower terrace on the left part of B (connects to the stair)
glass_rail(XB0 + 0.1, x2a, BY0 - 0.08, BY0 - 0.06, z2 + 0.05)
for (x0_, x1_) in ((XB0 + 0.4, XB0 + 2.0), (-2.4, -0.8)):
    box('ter_planter', ((x0_ + x1_) / 2, BY1 - 0.3, z2 + 0.2), (x1_ - x0_, 0.38, 0.3), oakc, bevel=0.01)
    for k in range(10):
        meadow_flower(((x0_ + x1_) / 2 + R.uniform(-0.7, 0.7), BY1 - 0.3 + R.uniform(-0.12, 0.12), z2 + 0.35), R.uniform(0.15, 0.3),
                      R.choice([(0.98, 0.7, 0.78), (0.98, 0.95, 0.9), (0.98, 0.75, 0.3)]))
    plant('fern_02', ((x0_ + x1_) / 2, BY1 - 0.3, z2 + 0.35), 0.35)
hanging_ivy((-1.9, BY0 - 0.12, z2 + 0.05), (0, -1, 0), 2.8, 0.9, 14, 'vine', (0.26, 0.42, 0.1))
# details under the colonnade
for x in (-3.4, 0.4):
    box('bench', (x, BY1 - 1.35, 0.25), (1.0, 0.36, 0.06), oakc, bevel=0.01)
    for d in (-0.4, 0.4):
        box('bench_leg', (x + d, BY1 - 1.35, 0.13), (0.05, 0.3, 0.22), iron, bevel=0)
for x in (-4.0, -2.2, -0.5, 1.6, 3.2):
    pot((x, BY0 + 0.5, 0.06), 0.15, 0.32, R.choice(['shrub_sorrel_01', 'fern_02', 'flower_gazania']), 0.45)
for x in (-3.0, -0.9, 1.2, 3.0):
    lantern((x, BY0 + 0.5, GZ - 0.32), 0.9)
    cyl('chain', (x, BY0 + 0.5, GZ - 0.1), 0.006, 0.2, iron, verts=6)

# ================================================================== LEFT building (lower, floats on columns)
LX0, LX1 = -4.85, -2.0     # upper floor (wider)
LY0, LY1 = -3.45, 1.25
LZ = 1.35; LH = 1.25
slab(LX0, -2.6, LY0, LY1, 0.03, 0.06, travertine)  # paving under it
box('L_core', (LX0 + 0.45, LY1 - 0.9, LZ / 2), (0.9, 1.6, LZ), sand, bevel=0.02)  # small stone entry core at the back
for x in (-2.35, -4.5):
    for y in (-3.1, -1.6, -0.1):
        if x < -4 and y > -0.5: continue
        column(x, y, 0.06, LZ - 0.06, 0.075)
slab(LX0 - 0.05, LX1 + 0.08, LY0 - 0.08, LY1 + 0.05, LZ, 0.12)
L1 = box('L_f1', ((LX0 + LX1) / 2, (LY0 + LY1) / 2, LZ + LH / 2 + 0.06), (LX1 - LX0, LY1 - LY0, LH), oakc, bevel=0.02)
# vertical oak battens + big corner glazing toward the garden
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
slab(LX0 - 0.1, LX1 + 0.12, LY0 - 0.12, LY1 + 0.08, LZ + LH + 0.1, 0.1)
# roof deck + greenhouse full of flowers
RZ = LZ + LH + 0.15
box('deck', ((LX0 + LX1) / 2, (LY0 + LY1) / 2, RZ + 0.01), (LX1 - LX0 - 0.1, LY1 - LY0 - 0.1, 0.03), wood('deck', (0.52, 0.37, 0.24), 5), bevel=0.005)
glass_rail(LX1 - 0.03, LX1 - 0.01, LY0, LY1, RZ)
glass_rail(LX0, LX1, LY0 + 0.02, LY0 + 0.04, RZ)
gx0, gx1, gy0, gy1 = -4.6, -2.55, -3.1, -0.4
gh, gr = 0.95, 0.6
gl = solid('gh_glass', (0.88, 0.95, 0.93), 0.03); gl.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.93
fr = solid('gh_frame', (0.93, 0.93, 0.9), 0.35)
box('gh_walls', ((gx0 + gx1) / 2, (gy0 + gy1) / 2, RZ + gh / 2), (gx1 - gx0, gy1 - gy0, gh), gl, bevel=0)
# greenhouse roof: ridge along y
me = bpy.data.meshes.new('ghr'); bm_ = bmesh.new()
cx_ = (gx0 + gx1) / 2
v = [bm_.verts.new(p) for p in [(gx0, gy0, RZ + gh), (cx_, gy0, RZ + gh + gr), (gx1, gy0, RZ + gh), (gx0, gy1, RZ + gh), (cx_, gy1, RZ + gh + gr), (gx1, gy1, RZ + gh)]]
for f_ in ([v[0], v[1], v[4], v[3]], [v[1], v[2], v[5], v[4]], [v[0], v[1], v[2]], [v[3], v[5], v[4]]):
    bm_.faces.new(f_)
bm_.to_mesh(me); bm_.free(); me.materials.append(gl); link(bpy.data.objects.new('gh_roofglass', me))
for k in range(9):
    y = gy0 + k * (gy1 - gy0) / 8
    for (a, b) in (((gx0, y, RZ + gh), (cx_, y, RZ + gh + gr)), ((cx_, y, RZ + gh + gr), (gx1, y, RZ + gh))):
        limb(Vector(a), Vector(b), 0.015, fr)
    box('gh_post', (gx0, y, RZ + gh / 2), (0.03, 0.03, gh), fr, bevel=0); box('gh_post', (gx1, y, RZ + gh / 2), (0.03, 0.03, gh), fr, bevel=0)
for z in (RZ + 0.02, RZ + gh / 2, RZ + gh):
    for (x0_, y0_, x1_, y1_) in ((gx0, gy0, gx1, gy0), (gx0, gy1, gx1, gy1), (gx0, gy0, gx0, gy1), (gx1, gy0, gx1, gy1)):
        box('gh_rail', ((x0_ + x1_) / 2, (y0_ + y1_) / 2, z), (max(x1_ - x0_, 0.025), max(y1_ - y0_, 0.025), 0.025), fr, bevel=0)
limb(Vector((cx_, gy0, RZ + gh + gr)), Vector((cx_, gy1, RZ + gh + gr)), 0.02, fr)
# inside: benches of flowers, hanging baskets, climbing vines
for y in (gy0 + 0.35, gy1 - 0.35):
    box('gh_bench', (cx_, y, RZ + 0.3), (gx1 - gx0 - 0.3, 0.4, 0.05), oakc, bevel=0.005)
    for k in range(7):
        x = gx0 + 0.3 + k * (gx1 - gx0 - 0.6) / 6
        pot((x, y, RZ + 0.33), 0.08, 0.13, None)
        for j in range(3):
            meadow_flower((x + R.uniform(-0.04, 0.04), y + R.uniform(-0.04, 0.04), RZ + 0.44), R.uniform(0.08, 0.2),
                          R.choice([(0.98, 0.5, 0.6), (0.98, 0.85, 0.3), (0.7, 0.5, 0.95), (0.98, 0.95, 0.9), (0.95, 0.35, 0.3)]))
drift(cx_, (gy0 + gy1) / 2, 0.5, 0.5, 40, [(0.98, 0.5, 0.6), (0.98, 0.85, 0.3), (0.7, 0.5, 0.95)], 0.15, 0.4, lilies=6)
for k in range(3):
    p = (cx_, gy0 + 0.6 + k * 0.75, RZ + gh + 0.05)
    pot(p, 0.08, 0.12, 'periwinkle_plant', 0.15)
    hanging_ivy((p[0], p[1], p[2] + 0.05), (0, -1, 0), 0.2, 0.45, 5, 'ivy2', (0.28, 0.44, 0.1))
ivy_patch((gx1 - 0.05, -1.75, RZ), (1, 0, 0), 2.4, 0.9, 500, 'vine', (0.26, 0.42, 0.1))
room_light((cx_, (gy0 + gy1) / 2, RZ + 0.7), 60, (1.0, 0.8, 0.55))
# under the floating floor: open lounge
box('rug', (-3.35, -1.6, 0.065), (1.5, 1.9, 0.01), solid('rug', (0.72, 0.55, 0.42), 0.9), bevel=0)
box('long_bench', (-3.0, -1.6, 0.3), (0.45, 1.6, 0.08), oakc, bevel=0.01)
cyl('low_table', (-3.7, -1.6, 0.28), 0.32, 0.05, marble, verts=32, bevel=0.01)
cyl('low_table_base', (-3.7, -1.6, 0.14), 0.1, 0.24, iron, verts=16)
cyl('jar', (-3.7, -1.6, 0.34), 0.035, 0.08, solid('jar', (1, 0.8, 0.5), 0.2, emit=(1, 0.6, 0.25), strength=8), verts=12)
for y in (-2.9, -0.4):
    pot((-2.6, y, 0.06), 0.18, 0.4, 'shrub_sorrel_01', 0.55)
for (x, y) in ((-3.0, -2.6), (-3.6, -0.7), (-3.2, -1.6)):
    paper_lantern((x, y, LZ - 0.35), 0.1, (1.0, 0.62, 0.32))

# ================================================================== floating stair between them
SY0, SY1 = LY1 + 0.15, BY0 - 0.15
n = 14; rise = (RZ) / n; run = 0.24
for k in range(n):
    x = -0.75 - k * run
    box('tread', (x, (SY0 + SY1) / 2, (k + 1) * rise), (run + 0.02, SY1 - SY0, 0.05), oakc, bevel=0.006)
st = Vector((-0.75 + run / 2, SY0 + 0.03, 0)); en = Vector((-0.75 - n * run, SY0 + 0.03, RZ))
limb(st, en, 0.035, iron)
for k in range(0, n, 2):
    x = -0.75 - k * run
    box('stair_rail_post', (x, SY0 + 0.02, (k + 1) * rise + 0.45), (0.02, 0.02, 0.9), iron, bevel=0)

box('landing', ((-0.75 - n * run + LX0) / 2 + 0.1, (SY0 + SY1) / 2, RZ), (abs(-0.75 - n * run - LX0) + 0.2, SY1 - SY0 + 0.3, 0.1), marble, bevel=0.01)

# ================================================================== garden
# big pond with stepping-stone paths and a fountain
px, py, prx, pry = 1.35, -0.85, 2.25, 1.5
w = cyl('pond_water', (px, py, 0.035), 1.0, 0.03, water, verts=72); w.scale = (prx, pry, 1)
for k in range(64):
    a = k / 64 * 2 * math.pi
    sphere('pond_stone', (px + math.cos(a) * prx * 1.02, py + math.sin(a) * pry * 1.03, 0.04), R.uniform(0.09, 0.14), marble if k % 5 == 0 else stone, 12,
           (R.uniform(1.0, 1.5), R.uniform(0.8, 1.1), R.uniform(0.4, 0.6)))
paths = [[(px - 1.2, py - 2.0), (px - 0.95, py - 1.45), (px - 0.75, py - 0.95), (px - 0.5, py - 0.45), (px - 0.2, py + 0.0), (px + 0.15, py + 0.45), (px + 0.35, py + 0.95), (px + 0.4, py + 1.5), (px + 0.3, py + 2.05)],
         [(px - 0.2, py + 0.0), (px + 0.35, py - 0.25), (px + 0.9, py - 0.45), (px + 1.45, py - 0.55), (px + 2.0, py - 0.5), (px + 2.55, py - 0.35)]]
for path in paths:
    for (x, y) in path:
        cyl('stepstone', (x, y, 0.05), 0.2, 0.07, travertine, verts=24, bevel=0.015).scale = (1.0, R.uniform(0.75, 0.95), 1)
# fountain
fx, fy = px + 0.9, py + 0.55
cyl('f_basin', (fx, fy, 0.1), 0.45, 0.16, marble, verts=40, bevel=0.02)
cyl('f_water', (fx, fy, 0.18), 0.4, 0.02, water, verts=40)
cyl('f_stem', (fx, fy, 0.38), 0.07, 0.45, marble, verts=20)
cyl('f_bowl', (fx, fy, 0.62), 0.22, 0.08, marble, verts=32, r2=0.18, bevel=0.01)
cyl('f_bowl_w', (fx, fy, 0.665), 0.19, 0.01, water, verts=32)
jet = solid('jet', (0.9, 0.95, 1.0), 0.05); jet.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.8
cyl('f_jet', (fx, fy, 0.8), 0.012, 0.28, jet, verts=8)
for k in range(14):
    a = k / 14 * 2 * math.pi
    for j in range(5):
        t = j / 4
        sphere('drop', (fx + math.cos(a) * (0.02 + t * 0.18), fy + math.sin(a) * (0.02 + t * 0.18), 0.94 - t * t * 0.27), 0.012, jet, 6)
for k in range(22):
    a, rr = R.uniform(0, 6.28), R.uniform(0.35, 0.85)
    x, y = px + math.cos(a) * rr * prx, py + math.sin(a) * rr * pry
    if min(math.hypot(x - sx, y - sy) for path in paths for (sx, sy) in path) < 0.32 or math.hypot(x - fx, y - fy) < 0.6: continue
    waterlily((x, y, 0.055), R.uniform(0.08, 0.13))
for k in range(12):
    a = R.uniform(0, 6.28)
    plant('grass_medium_01', (px + math.cos(a) * prx * 1.14, py + math.sin(a) * pry * 1.16, 0), R.uniform(0.25, 0.45))
for (x, y) in ((px - 2.4, py), (px + 2.4, py + 0.6), (px, py - 1.7), (px - 1.2, py + 1.45), (px + 1.6, py - 1.35)):
    ground_light(x, y)

# trees
willow((4.15, -2.1, 0), 2.9, 1.3)
cherry_tree((-1.35, -3.2, 0), 2.1, 0.95, lean=0.2, lanterns=1)
cherry_tree((4.35, 1.35, 0), 2.3, 1.0, lean=-0.25, lanterns=1)
cherry_tree((-1.2, 1.05, 0), 1.6, 0.7, lean=0.1, lanterns=0)

# meadow flowers growing straight from the lawn (and a few lilies)
pal = [(0.98, 0.95, 0.9), (0.98, 0.7, 0.78), (0.98, 0.82, 0.3), (0.72, 0.55, 0.95), (0.95, 0.45, 0.4)]
for (cx, cy, rx, ry, nn, li) in ((-0.9, -2.2, 0.9, 0.7, 70, 4), (3.6, -3.6, 0.9, 0.45, 50, 0), (-1.6, -0.6, 0.45, 0.9, 50, 3),
                                (4.4, -0.2, 0.45, 0.8, 40, 3), (0.0, -3.7, 1.0, 0.35, 45, 0), (2.6, 1.75, 0.9, 0.35, 40, 2), (-0.4, 1.75, 0.5, 0.35, 25, 0)):
    drift(cx, cy, rx, ry, nn, pal, lilies=li)
for i in range(110):
    x, y = R.uniform(-2.3, 4.85), R.uniform(-4.15, 2.0)
    if (x - px) ** 2 / prx ** 2 + (y - py) ** 2 / pry ** 2 < 1.25: continue
    plant('grass_medium_01', (x, y, 0), R.uniform(0.12, 0.26))
# a stepping path from the front edge to the colonnade
for (x, y) in ((-0.2, -4.0), (-0.25, -3.45)):
    cyl('stepstone', (x, y, 0.03), 0.2, 0.05, travertine, verts=24, bevel=0.015)
for (x, y) in ((-0.6, -3.7), (3.3, 2.05), (0.2, 2.0), (-1.9, -2.6)):
    post_lamp(x, y, 0.85)
cyl('sl_pole', (4.7, -0.9, 1.2), 0.03, 2.4, iron, verts=10)
string_lights((-1.95, -2.5, LZ + 0.4), (4.7, -0.9, 2.35), 0.55, 24)
string_lights((2.2, BY0 - 0.2, z1 - 0.1), (4.7, -0.9, 2.35), 0.35, 12)

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
