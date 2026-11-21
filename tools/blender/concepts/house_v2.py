"""Modern Mediterranean house, v2: interlocking volumes, steel-framed glazing,
roof-terrace pergola, waterlily pond, lily garden, sculpted trees, lanterns.
Usage: ASSETS=<assets-raw> python house_v2.py <out.png> [samples]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

OUT = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-1].isdigit() else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 64
sc = reset()

# ------------------------------------------------------------------ materials
cream = stucco('stucco_cream', (0.88, 0.8, 0.68))
warm = stucco('stucco_warm', (0.86, 0.66, 0.5))
steel = solid('steel', (0.035, 0.035, 0.035), 0.35, metal=0.6)
oak = wood('oak', (0.55, 0.38, 0.24), 7)
slat = wood('slats', (0.5, 0.32, 0.19), 9, axis='Z')
travertine = varied('travertine', (0.8, 0.74, 0.64), 0.06, 0.7, bump=0.15, bump_scale=60)
stone = varied('fieldstone', (0.6, 0.56, 0.5), 0.2, 0.85, bump=0.4)
tiles = tile_mat('tiles', (0.66, 0.31, 0.19))
shutter = varied('shutter', (0.4, 0.48, 0.42), 0.06, 0.55)
water = solid('pond', (0.03, 0.09, 0.09), 0.04)
water.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = 1.0

def grass_mat():
    m, n, l, b = node_mat('lawn')
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; l.new(tc.outputs['Object'], nz.inputs['Vector'])
    fine = n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 90; l.new(tc.outputs['Object'], fine.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].color = (0.16, 0.26, 0.07, 1); r.color_ramp.elements[1].color = (0.36, 0.45, 0.14, 1)
    l.new(nz.outputs['Fac'], r.inputs['Fac']); l.new(r.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    l.new(fine.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.9
    return m

# ------------------------------------------------------------------ helpers
def steel_window(wall, x, y, z, w, h, cols=2, rows=3, axis='y', side=-1, depth=0.6, arched=False, glow=True):
    """Black steel-framed glazing with a slim grid (modern), recessed into a stucco wall."""
    if arched:
        a, b = arch_cutter('swc', (x, y, z), w, h, depth, axis); cut(wall, a); cut(wall, b)
    else:
        cut(wall, box('swc', (x, y, z + h / 2), (w, depth, h) if axis == 'y' else (depth, w, h), None, bevel=0))
    rec = 0.08
    off = Vector((0, -side * rec, 0)) if axis == 'y' else Vector((-side * rec, 0, 0))
    P = lambda dx, dz: Vector((x, y, z)) + off + (Vector((dx, 0, dz)) if axis == 'y' else Vector((0, dx, dz)))
    S = lambda sx, sz, t=0.03: (sx, t, sz) if axis == 'y' else (t, sx, sz)
    box('glass', P(0, h / 2) + off * 0.3, S(w, h, 0.01), glass_glow() if glow else solid('dark_glass', (0.04, 0.06, 0.07), 0.05), bevel=0)
    t = 0.028
    top = h - (w / 2 if arched else 0)
    box('mull', P(-w / 2 + t / 2, top / 2), S(t, top), steel, bevel=0)
    box('mull', P(w / 2 - t / 2, top / 2), S(t, top), steel, bevel=0)
    box('mull', P(0, t / 2), S(w, t), steel, bevel=0)
    if not arched: box('mull', P(0, h - t / 2), S(w, t), steel, bevel=0)
    for c in range(1, cols):
        box('mull', P(-w / 2 + c * w / cols, top / 2), S(t * 0.6, top), steel, bevel=0)
    for r in range(1, rows):
        box('mull', P(0, r * top / rows), S(w, t * 0.6), steel, bevel=0)
    # stone reveal / sill
    so = Vector((0, side * 0.04, 0)) if axis == 'y' else Vector((side * 0.04, 0, 0))
    box('sill', Vector((x, y, z - 0.025)) + so, S(w + 0.12, 0.05, 0.16), travertine, bevel=0.01)

def flower_box(x, y, z, w, axis='y', side=-1):
    so = Vector((0, side * 0.12, 0)) if axis == 'y' else Vector((side * 0.12, 0, 0))
    p = Vector((x, y, z)) + so
    box('fbox', p, (w, 0.2, 0.18) if axis == 'y' else (0.2, w, 0.18), varied('terracotta_pot', (0.62, 0.3, 0.17), 0.1, 0.75), bevel=0.015)
    for i in range(4):
        q = p + (Vector((-w / 2 + (i + 0.5) * w / 4, 0, 0.08)) if axis == 'y' else Vector((0, -w / 2 + (i + 0.5) * w / 4, 0.08)))
        plant(R.choice(['flower_gazania', 'periwinkle_plant', 'shrub_sorrel_01']), q, 0.22)
    hanging_ivy(p + Vector((0, 0, 0.06)), (0, side, 0) if axis == 'y' else (side, 0, 0), w, 0.55, 7, 'ivy2', (0.28, 0.42, 0.1))

def paper_lantern(p, r=0.12, color=(1.0, 0.55, 0.25)):
    m = solid('paper_' + str(color), (1, 0.85, 0.7), 0.6, emit=color, strength=7)
    sphere('paper', p, r, m, 20, (1, 1, 1.15))
    cyl('paper_cap', (p[0], p[1], p[2] + r * 1.12), r * 0.35, 0.03, steel, verts=12)
    cyl('paper_cord', (p[0], p[1], p[2] + r * 1.12 + 0.2), 0.004, 0.4, steel, verts=6)
    L = bpy.data.lights.new('pl', 'POINT'); L.energy = 6; L.color = color; L.shadow_soft_size = r
    link(bpy.data.objects.new('pl', L)).location = p

def post_lamp(x, y, h=1.1):
    cyl('lamp_post', (x, y, h / 2), 0.035, h, steel, verts=12)
    cyl('lamp_foot', (x, y, 0.04), 0.09, 0.08, steel, verts=16)
    lantern((x, y, h + 0.08), 1.1)

def ground_light(x, y):
    cyl('gl', (x, y, 0.06), 0.05, 0.12, steel, verts=12)
    cyl('gl_glow', (x, y, 0.125), 0.04, 0.012, solid('gl_glow', (1, 0.8, 0.5), 0.3, emit=(1, 0.7, 0.4), strength=20), verts=12)
    L = bpy.data.lights.new('gl', 'SPOT'); L.energy = 8; L.color = (1, 0.72, 0.42); L.spot_size = 1.2; L.spot_blend = 0.8
    o = link(bpy.data.objects.new('gl', L)); o.location = (x, y, 0.15)

def stylised_tree(base, height, crown, leaf_name, leaf_color, bark=(0.32, 0.24, 0.18), clusters=8, leaves=420, lean=0.0, spread=1.0):
    """Sculpted tree: curved trunk, a few limbs, dense leaf clusters (an ornamental maple / olive)."""
    bm_ = varied('bark_' + leaf_name, bark, 0.08, 0.85, bump=0.5, bump_scale=40)
    bx, by, bz = base
    pts = [Vector((bx, by, bz))]
    for k in range(1, 5):
        t = k / 4
        pts.append(Vector((bx + math.sin(t * 2.2) * 0.12 * spread + lean * t, by + math.cos(t * 1.7) * 0.06, bz + t * height * 0.6)))
    for a, b in zip(pts, pts[1:]):
        d = b - a; L = d.length; r = 0.09 * (1 - (a.z - bz) / height * 0.9)
        c = cyl('trunk', (a + b) / 2, r, L * 1.05, bm_, verts=12, r2=r * 0.85)
        c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    top = pts[-1]
    me = leaf_mesh(leaf_name, leaf_color)
    for i in range(clusters):
        a = i / clusters * 2 * math.pi + R.uniform(-0.3, 0.3)
        rr = crown * R.uniform(0.45, 0.85)
        cz = top.z + R.uniform(-0.15, 0.45) * height * 0.35
        cen = top + Vector((math.cos(a) * rr, math.sin(a) * rr * 0.85, cz - top.z))
        d = cen - top
        lb = cyl('limb', (top + cen) / 2, 0.035, d.length, bm_, verts=8, r2=0.015)
        lb.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        cr = crown * R.uniform(0.42, 0.6)
        for _ in range(leaves):
            v = Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 1))).normalized() * (R.random() ** 0.35) * cr
            v.z *= 0.7
            o = link(bpy.data.objects.new('leaf', me))
            o.location = cen + v
            o.rotation_euler = (R.uniform(0, 6.28), R.uniform(0, 6.28), R.uniform(0, 6.28))
            s = R.uniform(0.9, 1.6); o.scale = (s, s, s)
    # crown top cluster
    cen = top + Vector((0, 0, height * 0.18))
    for _ in range(leaves):
        v = Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 1))).normalized() * (R.random() ** 0.35) * crown * 0.6
        v.z *= 0.6
        o = link(bpy.data.objects.new('leaf', me)); o.location = cen + v
        o.rotation_euler = (R.uniform(0, 6.28), R.uniform(0, 6.28), R.uniform(0, 6.28))
        s = R.uniform(0.9, 1.6); o.scale = (s, s, s)

def waterlily(p, r=0.12):
    pad = cyl('pad', p, r, 0.008, varied('lilypad', (0.16, 0.34, 0.12), 0.25, 0.4), verts=20)
    cut(pad, box('notch', (p[0] + r * 0.7, p[1], p[2]), (r * 0.9, 0.012, 0.05), None, bevel=0, rot=(0, 0, R.uniform(0, 6.28))))
    pad.rotation_euler.z = R.uniform(0, 6.28)
    if R.random() < 0.45:
        col = R.choice([(0.98, 0.62, 0.72), (0.98, 0.95, 0.92), (0.95, 0.5, 0.62)])
        pm = solid('lilypetal_' + str(col), col, 0.45)
        pm.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.3
        for k in range(10):
            a = k / 10 * 2 * math.pi + (0.3 if k % 2 else 0)
            rr = 0.035 if k % 2 else 0.045
            pe = sphere('petal', (p[0] + math.cos(a) * rr, p[1] + math.sin(a) * rr, p[2] + 0.03 + (0.015 if k % 2 else 0)), 0.04, pm, 10, (1.0, 0.38, 0.16))
            pe.rotation_euler = (0, -0.6 if k % 2 else -0.35, a)
        sphere('lily_heart', (p[0], p[1], p[2] + 0.045), 0.018, solid('lily_heart', (0.95, 0.75, 0.2), 0.5), 10)

def garden_lily(p, h, col):
    stem_m = solid('lily_stem', (0.2, 0.36, 0.12), 0.6)
    cyl('lily_stem', (p[0], p[1], p[2] + h / 2), 0.008, h, stem_m, verts=6)
    for k in range(4):
        a = R.uniform(0, 6.28)
        lf = sphere('lily_leaf', (p[0] + math.cos(a) * 0.05, p[1] + math.sin(a) * 0.05, p[2] + h * R.uniform(0.15, 0.5)), 0.08, stem_m, 8, (0.18, 0.9, 0.06))
        lf.rotation_euler = (0.6, 0, a)
    pm = solid('glily_' + str(col), col, 0.5)
    pm.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.25
    top = Vector((p[0], p[1], p[2] + h))
    for k in range(6):
        a = k / 6 * 2 * math.pi
        pe = sphere('lily_petal', top + Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.02)), 0.05, pm, 10, (1, 0.32, 0.12))
        pe.rotation_euler = (0, -0.75, a)
    sphere('lily_center', top + Vector((0, 0, 0.02)), 0.014, solid('lily_anther', (0.45, 0.18, 0.08), 0.6), 8)

# ------------------------------------------------------------------ ground
BX, BY = 10.0, 8.0
diorama_base(0, 0, BX, BY, grass_mat())
for i in range(140):
    x, y = R.uniform(-4.8, 4.8), R.uniform(-3.8, 3.8)
    if -4.3 < x < 2.4 and -1.2 < y < 3.4: continue
    if (x - 3.1) ** 2 / 1.6 + (y + 0.3) ** 2 / 2.2 < 1.2: continue
    plant('grass_medium_01', (x, y, 0), R.uniform(0.18, 0.32))
# patio of travertine slabs in front of the house
for i in range(16):
    for j in range(4):
        x = -4.2 + i * 0.4 + (0.2 if j % 2 else 0); y = -1.35 + j * 0.4
        if x > 2.2: continue
        box('slab', (x, y, 0.015), (0.38, 0.38, 0.04), travertine, bevel=0.012)
# stepping stones from the front edge to the patio
for k, (x, y) in enumerate([(0.9, -3.7), (0.7, -3.1), (0.85, -2.5), (0.65, -1.9)]):
    box('step', (x, y, 0.02), (0.55, 0.42, 0.05), travertine, bevel=0.02, rot=(0, 0, R.uniform(-0.2, 0.2)))

# ------------------------------------------------------------------ house
# main two-storey volume (gabled terracotta roof)
A = box('main', (0.3, 1.9, 1.85), (3.8, 3.0, 3.7), cream, bevel=0.07)
box('plinth', (0.3, 1.9, 0.12), (3.9, 3.1, 0.24), travertine, bevel=0.02)
gable_roof('roofA', 0.3, 1.9, 3.8, 3.0, 3.7, 1.15, tiles, over=0.28)
# chimney
box('chimney', (1.5, 2.6, 4.7), (0.4, 0.4, 1.2), cream, bevel=0.03)
box('chimney_cap', (1.5, 2.6, 5.33), (0.52, 0.52, 0.06), travertine, bevel=0.01)
# a warm stucco stair tower with a curved top, joining the two volumes
TX, TY, TR = -1.65, 0.75, 0.72
T = cyl('tower', (TX, TY, 2.55), TR, 5.1, warm, verts=48, bevel=0.03)
for z in (0.9, 2.6, 4.0):
    steel_window(T, TX, TY - TR, z, 0.34, 0.95, 1, 3, side=-1, depth=0.9, arched=True)
cyl('tower_cap', (TX, TY, 5.13), TR + 0.08, 0.1, travertine, verts=48, bevel=0.02)
cyl('tower_roof', (TX, TY, 5.65), TR + 0.16, 0.95, varied('cone_tiles', (0.64, 0.3, 0.18), 0.05, 0.7, bump=0.4, bump_scale=18), verts=48, r2=0.03)
sphere('finial', (TX, TY, 6.15), 0.06, solid('brass', (0.75, 0.55, 0.25), 0.3, metal=1), 12)
# modern flat-roofed wing with full-height glazing and timber slats
W = box('wing', (-3.3, 1.9, 1.15), (2.4, 2.6, 2.3), cream, bevel=0.05)
box('wing_roof', (-3.3, 1.9, 2.34), (2.6, 2.8, 0.1), steel, bevel=0.01)
steel_window(W, -3.45, 0.6, 0.12, 1.7, 1.85, 4, 2, side=-1)
for k in range(9):
    box('slat', (-4.48, 0.72 + k * 0.28, 1.15), (0.05, 0.08, 2.2), slat, bevel=0.005)
# main volume front: big steel doors, arched windows upstairs with shutters, balcony
steel_window(A, 0.85, 0.4, 0.24, 1.5, 2.0, 3, 3, side=-1)
steel_window(A, -0.75, 0.4, 0.55, 0.7, 1.2, 2, 3, side=-1)
for x in (-0.75, 0.25):
    window(A, (x, 0.4, 2.2), 0.6, 1.15, side=-1, arched=True, sill_mat=travertine, shutters=shutter, frame_mat=steel)
    flower_box(x, 0.4, 2.13, 0.75)
steel_window(A, 1.4, 0.4, 2.1, 0.9, 1.35, 2, 3, side=-1)
# cantilevered balcony with a slim steel railing
box('balcony', (1.4, 0.05, 2.04), (1.5, 0.7, 0.1), travertine, bevel=0.02)
for k in range(16):
    box('rail_bar', (0.7 + k * 0.094, -0.27, 2.32), (0.012, 0.012, 0.5), steel, bevel=0)
box('rail_top', (1.4, -0.27, 2.58), (1.5, 0.03, 0.03), steel, bevel=0)
for xs in (0.67, 2.13):
    box('rail_side', (xs, 0.05, 2.58), (0.03, 0.66, 0.03), steel, bevel=0)
pot((1.95, 0.15, 2.09), 0.12, 0.2, 'fern_02', 0.45)
# right side (+x) windows
for y in (1.2, 2.6):
    steel_window(A, 2.2, y, 0.55, 0.7, 1.2, 2, 3, axis='x', side=1)
    window(A, (2.2, y, 2.2), 0.6, 1.1, axis='x', side=1, arched=True, sill_mat=travertine, shutters=shutter, frame_mat=steel)
# canopy over the doors: timber pergola with vines
for x in (0.0, 1.7):
    box('canopy_post', (x, -0.85, 1.1), (0.08, 0.08, 2.2), oak, bevel=0.01)
box('canopy_beam', (0.85, -0.85, 2.22), (2.0, 0.1, 0.12), oak, bevel=0.01)
for k in range(8):
    box('canopy_joist', (0.0 + k * 0.243, -0.25, 2.3), (0.06, 1.3, 0.08), oak, bevel=0.01)
ivy_patch((0.0, -0.9, 0.0), (0, -1, 0), 0.4, 2.2, 260, 'vine', (0.22, 0.38, 0.09))
hanging_ivy((0.85, -0.6, 2.32), (0, -1, 0), 2.0, 0.6, 12, 'vine', (0.22, 0.38, 0.09))
for k in range(220):  # vines across the top of the canopy
    o = link(bpy.data.objects.new('leaf', leaf_mesh('vine', (0.22, 0.38, 0.09))))
    o.location = (R.uniform(-0.1, 1.8), R.uniform(-0.85, 0.35), 2.36 + R.uniform(0, 0.06))
    o.rotation_euler = (R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), R.uniform(0, 6.28))
for k, x in enumerate((0.3, 0.85, 1.4)):
    paper_lantern((x, -0.5, 1.85 - 0.08 * (k % 2)), 0.11, (1.0, 0.55, 0.25) if k != 1 else (1.0, 0.75, 0.45))
lantern((-0.15, 0.33, 1.75), 1.1)
lantern((2.28, 1.9, 1.6), 1.0)
# roof terrace on the wing: pergola, lanterns, planters
for x in (-4.4, -2.2):
    for y in (0.75, 3.05):
        box('tpost', (x, y, 3.1), (0.07, 0.07, 1.5), oak, bevel=0.01)
for y in (0.75, 3.05):
    box('tbeam', (-3.3, y, 3.88), (2.4, 0.08, 0.1), oak, bevel=0.01)
for k in range(10):
    box('tslat', (-4.4 + k * 0.245, 1.9, 3.96), (0.05, 2.5, 0.06), oak, bevel=0.005)
hanging_ivy((-3.3, 0.72, 3.9), (0, -1, 0), 2.2, 0.8, 14, 'vine', (0.22, 0.38, 0.09))
for k in range(260):
    o = link(bpy.data.objects.new('leaf', leaf_mesh('vine', (0.22, 0.38, 0.09))))
    o.location = (R.uniform(-4.5, -2.1), R.uniform(0.7, 3.1), 4.0 + R.uniform(0, 0.06))
    o.rotation_euler = (R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), R.uniform(0, 6.28))
for x in (-4.0, -3.3, -2.6):
    paper_lantern((x, 1.4, 3.6), 0.1)
box('terrace_rail', (-3.3, 0.66, 2.62), (2.5, 0.03, 0.03), steel, bevel=0)
for k in range(24):
    box('trail_bar', (-4.5 + k * 0.1, 0.66, 2.5), (0.012, 0.012, 0.28), steel, bevel=0)
for x, n in ((-4.2, 'shrub_03'), (-2.4, 'shrub_sorrel_01')):
    pot((x, 1.0, 2.39), 0.16, 0.28, n, 0.55)
box('bench', (-3.3, 2.7, 2.6), (1.2, 0.4, 0.3), oak, bevel=0.02)

# ------------------------------------------------------------------ pond with waterlilies
px, py = 3.15, -0.35
pond_r = (1.25, 1.55)
o = cyl('pond_water', (px, py, 0.03), 1.0, 0.03, water, verts=48); o.scale = (pond_r[0], pond_r[1], 1)
for k in range(30):
    a = k / 30 * 2 * math.pi
    sphere('pond_stone', (px + math.cos(a) * pond_r[0] * 1.03, py + math.sin(a) * pond_r[1] * 1.03, 0.04), R.uniform(0.11, 0.17), stone, 12,
           (R.uniform(1.0, 1.5), R.uniform(0.8, 1.1), R.uniform(0.45, 0.7)))
for k in range(16):
    a, rr = R.uniform(0, 6.28), R.random() ** 0.6 * 0.82
    waterlily((px + math.cos(a) * rr * pond_r[0], py + math.sin(a) * rr * pond_r[1], 0.05), R.uniform(0.09, 0.14))
for k in range(5):
    a = R.uniform(-0.6, 1.4)
    plant('grass_medium_01', (px + math.cos(a) * pond_r[0] * 1.15, py + math.sin(a) * pond_r[1] * 1.15, 0), 0.5)
for (x, y) in ((2.0, -1.9), (4.3, -1.9), (4.4, 1.3)):
    ground_light(x, y)

# ------------------------------------------------------------------ lily garden (raised beds)
for (cx, cy, w, d) in ((-2.6, -2.7, 3.2, 1.0), (-4.3, -1.6, 0.9, 1.4)):
    box('bed_wall', (cx, cy, 0.14), (w + 0.12, d + 0.12, 0.28), stone, bevel=0.03)
    box('bed_soil', (cx, cy, 0.29), (w, d, 0.02), solid('soil', (0.13, 0.09, 0.06), 0.95), bevel=0)
    for k in range(int(w * d * 16)):
        x, y = cx + R.uniform(-w / 2 + 0.08, w / 2 - 0.08), cy + R.uniform(-d / 2 + 0.08, d / 2 - 0.08)
        garden_lily((x, y, 0.3), R.uniform(0.35, 0.6), R.choice([(0.98, 0.55, 0.15), (0.98, 0.95, 0.9), (0.95, 0.45, 0.55), (0.98, 0.75, 0.2)]))
    for k in range(int(w * d * 4)):
        plant(R.choice(['fern_02', 'periwinkle_plant']), (cx + R.uniform(-w / 2, w / 2) * 0.9, cy + R.uniform(-d / 2, d / 2) * 0.9, 0.3), 0.22)

# ------------------------------------------------------------------ trees, shrubs, pots
stylised_tree((3.8, 2.6, 0), 2.6, 1.2, 'maple_red', (0.62, 0.1, 0.06), clusters=9, leaves=380, lean=-0.2)
stylised_tree((-4.3, 3.3, 0), 3.0, 1.25, 'olive', (0.36, 0.44, 0.24), bark=(0.4, 0.36, 0.3), clusters=8, leaves=360, lean=0.3)
stylised_tree((4.4, -3.2, 0), 1.6, 0.7, 'maple_amber', (0.85, 0.42, 0.08), clusters=6, leaves=240, lean=-0.1)
for p, n, h in [((2.6, 0.6, 0), 'shrub_02', 0.9), ((-0.9, 0.0, 0), 'shrub_03', 0.6), ((2.4, 3.5, 0), 'shrub_sorrel_01', 0.5)]:
    plant(n, p, h)
for p, n in [((-0.2, -1.0, 0.035), 'fern_02'), ((2.0, -0.6, 0.035), 'shrub_sorrel_01'), ((-1.3, -1.0, 0.035), 'flower_gazania')]:
    pot(p, 0.2, 0.34, n, 0.6)
# patio furniture
cyl('table', (-1.6, -0.8, 0.45), 0.36, 0.04, travertine, verts=32, bevel=0.01)
cyl('table_leg', (-1.6, -0.8, 0.22), 0.04, 0.44, steel, verts=12)
for a in (0.6, 2.6, 4.6):
    cx, cy = -1.6 + math.cos(a) * 0.62, -0.8 + math.sin(a) * 0.62
    box('chair_seat', (cx, cy, 0.3), (0.34, 0.34, 0.04), oak, bevel=0.01, rot=(0, 0, a))
    box('chair_back', (cx + math.cos(a) * 0.16, cy + math.sin(a) * 0.16, 0.5), (0.04, 0.34, 0.38), oak, bevel=0.01, rot=(0, 0, a))
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            q = Vector((cx, cy, 0.15)) + Matrix.Rotation(a, 3, 'Z') @ Vector((s1 * 0.14, s2 * 0.14, 0))
            box('chair_leg', q, (0.025, 0.025, 0.3), steel, bevel=0)
cyl('candle_jar', (-1.6, -0.8, 0.52), 0.04, 0.1, solid('jar', (1, 0.8, 0.5), 0.2, emit=(1, 0.6, 0.25), strength=8), verts=12)

# string lights and post lamps
for (x, y) in ((-3.95, -1.65), (1.75, -1.95)):
    cyl('sl_pole', (x, y, 1.1), 0.03, 2.2, steel, verts=10)
string_lights((-3.95, -1.65, 2.18), (-0.9, 0.36, 2.95), 0.32, 13)
string_lights((-0.9, 0.36, 2.95), (1.75, -1.95, 2.18), 0.32, 13)
string_lights((-3.95, -1.65, 2.18), (1.75, -1.95, 2.18), 0.4, 20)
for (x, y) in ((1.25, -3.4), (0.3, -2.2)):
    post_lamp(x, y, 0.9)

# interior light
for p in [(0.3, 1.9, 1.0), (0.3, 1.9, 2.7), (-3.3, 1.9, 1.0), (-1.65, 1.2, 1.2), (-1.65, 1.2, 3.0)]:
    room_light(p, 110)

lighting(sc, sun_rot=(math.radians(74), 0, math.radians(-62)), sun_energy=2.0, sun_color=(1.0, 0.58, 0.32),
         bg_top=(0.22, 0.3, 0.42), bg_bottom=(0.86, 0.66, 0.56), hdri_strength=0.16)
iso_camera(sc, (-0.3, 0.4, 2.0), 13.2)
render(sc, OUT, SAMPLES)
