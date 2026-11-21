"""House v3: an L-shaped Haussmann-style house (limestone, rusticated ground
floor, cornices, wrought-iron balconies, zinc mansard with dormers) wrapped
around a lush garden, joined at the corner by a modern glass pavilion.
Weeping willow, cherry blossoms, waterlily pond, lily beds, lanterns.
Usage: ASSETS=<assets-raw> python house_v3.py <out.png> [samples]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

OUT = sys.argv[-2] if sys.argv[-1].isdigit() else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 64
sc = reset()

limestone = stucco('limestone', (0.86, 0.8, 0.69), dirt=(0.6, 0.55, 0.48))
lime_trim = varied('lime_trim', (0.9, 0.85, 0.75), 0.04, 0.7, bump=0.08, bump_scale=50)
zinc = tile_mat('zinc', (0.33, 0.37, 0.41))
zinc_s = solid('zinc_s', (0.36, 0.4, 0.44), 0.4, metal=0.5)
iron = solid('iron', (0.03, 0.03, 0.035), 0.4, metal=0.7)
paint = solid('frame_paint', (0.88, 0.86, 0.8), 0.45)
oak = wood('oak', (0.55, 0.38, 0.24), 7)
travertine = varied('travertine', (0.8, 0.74, 0.64), 0.06, 0.7, bump=0.15, bump_scale=60)
stone = varied('fieldstone', (0.58, 0.55, 0.5), 0.2, 0.85, bump=0.4)
water = solid('pond', (0.025, 0.08, 0.08), 0.03); water.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = 1.0

def grass_mat():
    m, n, l, b = node_mat('lawn')
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; l.new(tc.outputs['Object'], nz.inputs['Vector'])
    fine = n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 90; l.new(tc.outputs['Object'], fine.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].color = (0.14, 0.24, 0.06, 1); r.color_ramp.elements[1].color = (0.34, 0.44, 0.13, 1)
    l.new(nz.outputs['Fac'], r.inputs['Fac']); l.new(r.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    l.new(fine.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.9
    return m

# ------------------------------------------------------------------ facade grammar
class Facade:
    """A wall plane: `axis` is its normal axis ('y' or 'x'), `side` the sign of
    the outward normal, `plane` its coordinate, u runs along the wall."""
    def __init__(s, wall, axis, side, plane):
        s.wall, s.axis, s.side, s.plane = wall, axis, side, plane
    def P(s, u, out, z):
        return Vector((u, s.plane + s.side * out, z)) if s.axis == 'y' else Vector((s.plane + s.side * out, u, z))
    def S(s, along, out, up):
        return (along, out, up) if s.axis == 'y' else (out, along, up)
    def band(s, u0, u1, z, h, out, mat=None, name='band'):
        box(name, s.P((u0 + u1) / 2, out / 2, z), s.S(u1 - u0, out, h), mat or lime_trim, bevel=0.008, seg=2)
    def cornice(s, u0, u1, z):
        for k, (h, o) in enumerate([(0.06, 0.05), (0.05, 0.1), (0.08, 0.16), (0.05, 0.2)]):
            s.band(u0 - o, u1 + o, z + k * 0.055, h, o, name='cornice')
        # dentils
        n = int((u1 - u0) / 0.09)
        for i in range(n):
            box('dentil', s.P(u0 + (i + 0.5) * (u1 - u0) / n, 0.07, z + 0.02), s.S(0.04, 0.07, 0.05), lime_trim, bevel=0.004, seg=1)
    def rustication(s, u0, u1, z0, z1):
        z = z0 + 0.1
        while z < z1 - 0.05:
            s.band(u0, u1, z, 0.13, 0.025, limestone, 'rustic')
            z += 0.19
    def window(s, u, z, w, h, arched=False, hood=None, balcony=False, keystone=False):
        c = (u, s.plane, z) if s.axis == 'y' else (s.plane, u, z)
        window(s.wall, c, w, h, axis=s.axis, side=s.side, arched=arched, frame_mat=paint, depth=0.9)
        # moulded surround
        t = 0.07
        top = h if not arched else h
        box('surround', s.P(u - w / 2 - t / 2, 0.025, z + top / 2), s.S(t, 0.05, top), lime_trim, bevel=0.01, seg=2)
        box('surround', s.P(u + w / 2 + t / 2, 0.025, z + top / 2), s.S(t, 0.05, top), lime_trim, bevel=0.01, seg=2)
        if not arched:
            box('surround', s.P(u, 0.025, z + h + t / 2), s.S(w + 2 * t, 0.05, t), lime_trim, bevel=0.01, seg=2)
        if keystone:
            box('keystone', s.P(u, 0.04, z + h + 0.02), s.S(0.12, 0.08, 0.2), lime_trim, bevel=0.012, seg=2)
        if hood == 'cornice':
            s.band(u - w / 2 - 0.14, u + w / 2 + 0.14, z + h + 0.12, 0.06, 0.12, name='hood')
            for sg in (-1, 1):
                box('console', s.P(u + sg * (w / 2 + 0.08), 0.06, z + h + 0.03), s.S(0.06, 0.1, 0.14), lime_trim, bevel=0.01)
        elif hood == 'pediment':
            for sg in (-1, 1):
                b = box('pediment', s.P(u + sg * (w / 4 + 0.04), 0.06, z + h + 0.2), s.S(w / 2 + 0.22, 0.1, 0.06), lime_trim, bevel=0.01)
                b.rotation_euler = (0, -sg * 0.38, 0) if s.axis == 'y' else (sg * 0.38 * s.side, 0, 0)
        if balcony:
            box('bal_slab', s.P(u, 0.18, z - 0.04), s.S(w + 0.3, 0.36, 0.07), lime_trim, bevel=0.012)
            railing(s, u - w / 2 - 0.13, u + w / 2 + 0.13, z + 0.0, 0.34, 0.33)

def railing(f, u0, u1, z, out, h=0.36):
    n = int((u1 - u0) / 0.055)
    for i in range(n + 1):
        u = u0 + i * (u1 - u0) / n
        box('bar', f.P(u, out, z + h / 2), f.S(0.012, 0.012, h), iron, bevel=0)
        if i % 2 == 0 and i < n:  # little scroll: a ring between bars
            sphere('scroll', f.P(u + (u1 - u0) / n / 2, out, z + h * 0.62), 0.022, iron, 10, (1, 0.35, 1) if f.axis == 'y' else (0.35, 1, 1))
    for zz in (z + 0.02, z + h * 0.45, z + h):
        box('rail', f.P((u0 + u1) / 2, out, zz), f.S(u1 - u0, 0.025, 0.022), iron, bevel=0)

def mansard(name, x0, x1, y0, y1, z0, h=1.0, inset=0.42, ov=0.12):
    """Steep zinc mansard: lower slope rising to a flat top."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    b = [bm.verts.new(v) for v in [(x0 - ov, y0 - ov, z0), (x1 + ov, y0 - ov, z0), (x1 + ov, y1 + ov, z0), (x0 - ov, y1 + ov, z0)]]
    t = [bm.verts.new(v) for v in [(x0 + inset, y0 + inset, z0 + h), (x1 - inset, y0 + inset, z0 + h), (x1 - inset, y1 - inset, z0 + h), (x0 + inset, y1 - inset, z0 + h)]]
    for i in range(4):
        bm.faces.new([b[i], b[(i + 1) % 4], t[(i + 1) % 4], t[i]])
    bm.faces.new(t); bm.faces.new(b[::-1])
    uv = bm.loops.layers.uv.new('UVMap')
    for f_ in bm.faces:
        nrm = f_.normal
        for lp in f_.loops:
            co = lp.vert.co
            u = co.x if abs(nrm.x) < abs(nrm.y) else co.y
            lp[uv].uv = (u, co.z * 1.6 + (co.x + co.y) * 0.0)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); me.materials.append(zinc)
    box(name + '_trim', ((x0 + x1) / 2, (y0 + y1) / 2, z0 + h + 0.03), (x1 - x0 - 2 * inset + 0.08, y1 - y0 - 2 * inset + 0.08, 0.06), zinc_s, bevel=0.01)
    return o

def dormer(f, u, z0, w=0.5):
    """Zinc dormer with an arched top and a lit window, sitting on the mansard."""
    p = f.P(u, -0.15, z0 + 0.38)
    box('dormer', p, f.S(w + 0.14, 0.5, 0.7), lime_trim, bevel=0.02)
    cap = cyl('dormer_cap', f.P(u, -0.15, z0 + 0.73), w / 2 + 0.09, 0.56, zinc_s, verts=24, rot=(math.pi / 2, 0, 0) if f.axis == 'y' else (0, math.pi / 2, 0))
    box('dormer_glass', f.P(u, 0.11, z0 + 0.36), f.S(w * 0.72, 0.02, 0.5), glass_glow(), bevel=0)
    for du in (-w * 0.36, 0, w * 0.36):
        box('dormer_mull', f.P(u + du, 0.12, z0 + 0.36), f.S(0.025, 0.025, 0.52), paint, bevel=0)
    box('dormer_mull', f.P(u, 0.12, z0 + 0.36), f.S(w * 0.72, 0.025, 0.025), paint, bevel=0)
    sphere('oeil', f.P(u, 0.12, z0 + 0.74), 0.07, glass_glow(), 12, (1, 0.3, 1) if f.axis == 'y' else (0.3, 1, 1))

def chimney(x, y, z0, w=0.5, d=0.32):
    box('chimney', (x, y, z0 + 0.4), (w, d, 0.8), limestone, bevel=0.02)
    box('chimney_cap', (x, y, z0 + 0.83), (w + 0.08, d + 0.08, 0.06), lime_trim, bevel=0.01)
    for k in range(3):
        cyl('pot', (x - w / 3 + k * w / 3, y, z0 + 0.93), 0.05, 0.16, varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75), verts=10)

# ------------------------------------------------------------------ plants & props
def leaf_shape(name, pts, color, spread=0.3, subsurface=0.0):
    if name in LEAF: return LEAF[name]
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in pts]); bm.to_mesh(me); bm.free()
    m = varied('leafm_' + name, color, spread, 0.55)
    m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = subsurface
    me.materials.append(m); LEAF[name] = me
    return me

WILLOW_LEAF = [(0, 0, 0), (0.008, 0.03, 0), (0.006, 0.07, 0), (0, 0.09, 0), (-0.006, 0.07, 0), (-0.008, 0.03, 0)]
PETAL = [(0, 0, 0), (0.025, 0.012, 0.004), (0.03, 0.035, 0.006), (0.012, 0.05, 0.004), (-0.012, 0.05, 0.004), (-0.03, 0.035, 0.006), (-0.025, 0.012, 0.004)]

def trunk(pts, r0, bark):
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        d = b - a; r = r0 * (1 - k / len(pts) * 0.65)
        c = cyl('trunk', (a + b) / 2, r, d.length * 1.06, bark, verts=12, r2=r * 0.8)
        c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()

def limb(a, b, r, bark):
    d = b - a
    c = cyl('limb', (a + b) / 2, r, d.length, bark, verts=8, r2=r * 0.5)
    c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()

def weeping_willow(base, height=3.0, crown=1.5):
    bark = varied('willow_bark', (0.3, 0.25, 0.2), 0.1, 0.9, bump=0.6, bump_scale=30)
    bx, by, bz = base
    pts = [Vector((bx + math.sin(t * 1.8) * 0.15, by + math.sin(t * 1.3) * 0.08, bz + t * height * 0.62)) for t in (k / 5 for k in range(6))]
    trunk(pts, 0.16, bark)
    top = pts[-1]
    me = leaf_shape('willow', WILLOW_LEAF, (0.3, 0.44, 0.1), 0.25)
    tips = []
    for i in range(9):
        a = i / 9 * 2 * math.pi + R.uniform(-0.2, 0.2)
        tip = top + Vector((math.cos(a) * crown * 0.7, math.sin(a) * crown * 0.7, R.uniform(0.25, 0.6)))
        limb(top, tip, 0.06, bark); tips.append(tip)
    # dome of hanging curtains
    for k in range(520):
        a = R.uniform(0, 2 * math.pi); r = crown * math.sqrt(R.uniform(0.05, 1.0))
        sx, sy = top.x + math.cos(a) * r, top.y + math.sin(a) * r
        sz = top.z + 0.65 * (1 - (r / crown) ** 2) + 0.15
        L = R.uniform(1.0, 2.2) * (0.6 + 0.6 * r / crown)
        n = int(L / 0.035)
        for j in range(n):
            t = j / n
            p = Vector((sx + math.cos(a) * t * 0.12, sy + math.sin(a) * t * 0.12, sz - t * L))
            o = link(bpy.data.objects.new('wl', me)); o.location = p + Vector((R.uniform(-0.015, 0.015), R.uniform(-0.015, 0.015), 0))
            o.rotation_euler = (R.uniform(2.6, 3.6), R.uniform(-0.4, 0.4), R.uniform(0, 6.28))
            s = R.uniform(1.2, 1.8); o.scale = (s, s, s)

def cherry_tree(base, height=2.2, crown=1.1, lean=0.0, lanterns=2):
    bark = varied('cherry_bark', (0.24, 0.15, 0.13), 0.1, 0.7, bump=0.4, bump_scale=60)
    bx, by, bz = base
    pts = [Vector((bx + lean * t + math.sin(t * 2.6) * 0.1, by + math.cos(t * 2.0) * 0.06, bz + t * height * 0.55)) for t in (k / 4 for k in range(5))]
    trunk(pts, 0.11, bark)
    top = pts[-1]
    pink = leaf_shape('blossom', PETAL, (0.98, 0.7, 0.78), 0.25, 0.2)
    pale = leaf_shape('blossom2', PETAL, (0.99, 0.86, 0.88), 0.15, 0.2)
    cents = []
    for i in range(7):
        a = i / 7 * 2 * math.pi + R.uniform(-0.3, 0.3)
        c = top + Vector((math.cos(a) * crown * R.uniform(0.45, 0.8), math.sin(a) * crown * R.uniform(0.45, 0.8), R.uniform(0.0, 0.5)))
        limb(top, c, 0.045, bark); cents.append(c)
    cents.append(top + Vector((0, 0, 0.55)))
    for c in cents:
        cr = crown * R.uniform(0.42, 0.58)
        for _ in range(330):
            v = Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 1))).normalized() * (R.random() ** 0.3) * cr
            v.z *= 0.62
            o = link(bpy.data.objects.new('bl', pink if R.random() < 0.7 else pale)); o.location = c + v
            o.rotation_euler = (R.uniform(0, 6.28), R.uniform(0, 6.28), R.uniform(0, 6.28))
            s = R.uniform(0.9, 1.5); o.scale = (s, s, s)
    # fallen petals
    for _ in range(160):
        a, r = R.uniform(0, 6.28), crown * 1.2 * math.sqrt(R.random())
        o = link(bpy.data.objects.new('bl', pink)); o.location = (bx + math.cos(a) * r, by + math.sin(a) * r, bz + 0.012)
        o.rotation_euler = (R.uniform(-0.2, 0.2), R.uniform(-0.2, 0.2), R.uniform(0, 6.28))
    for k in range(lanterns):
        c = cents[k]
        paper_lantern(c + Vector((0, 0, -crown * 0.55)), 0.09)

def round_shrub(p, r, color=(0.2, 0.33, 0.1), flowers=None, n=500):
    me = leaf_mesh('shrub_' + str(color), color)
    for _ in range(n):
        v = Vector((R.gauss(0, 1), R.gauss(0, 1), abs(R.gauss(0, 1)))).normalized() * (R.random() ** 0.3) * r
        v.z *= 0.8
        o = link(bpy.data.objects.new('sl', me)); o.location = Vector(p) + v
        o.rotation_euler = (R.uniform(0, 6.28), R.uniform(0, 6.28), R.uniform(0, 6.28))
        s = R.uniform(1.0, 1.6); o.scale = (s, s, s)
    if flowers:
        fm = solid('hydrangea_' + str(flowers), flowers, 0.6)
        for _ in range(int(r * 30)):
            v = Vector((R.gauss(0, 1), R.gauss(0, 1), abs(R.gauss(0, 1)) + 0.2)).normalized() * r * 0.95
            sphere('bloom', Vector(p) + v, R.uniform(0.05, 0.08), fm, 10)

def paper_lantern(p, r=0.1, color=(1.0, 0.55, 0.25)):
    m = solid('paper_' + str(color), (1, 0.85, 0.7), 0.6, emit=color, strength=7)
    sphere('paper', p, r, m, 18, (1, 1, 1.15))
    cyl('paper_cap', (p[0], p[1], p[2] + r * 1.12), r * 0.35, 0.03, iron, verts=10)
    cyl('paper_cord', (p[0], p[1], p[2] + r * 1.12 + 0.18), 0.004, 0.36, iron, verts=6)
    L = bpy.data.lights.new('pl', 'POINT'); L.energy = 5; L.color = color; L.shadow_soft_size = r
    link(bpy.data.objects.new('pl', L)).location = p

def post_lamp(x, y, h=1.0):
    cyl('lamp_post', (x, y, h / 2), 0.03, h, iron, verts=12)
    cyl('lamp_foot', (x, y, 0.04), 0.08, 0.08, iron, verts=16)
    lantern((x, y, h + 0.08), 1.05)

def ground_light(x, y):
    cyl('gl', (x, y, 0.05), 0.045, 0.1, iron, verts=12)
    cyl('gl_glow', (x, y, 0.105), 0.035, 0.01, solid('gl_glow', (1, 0.8, 0.5), 0.3, emit=(1, 0.7, 0.4), strength=20), verts=12)
    L = bpy.data.lights.new('gl', 'POINT'); L.energy = 3; L.color = (1, 0.72, 0.42)
    link(bpy.data.objects.new('gl', L)).location = (x, y, 0.2)

def waterlily(p, r=0.12):
    pad = cyl('pad', p, r, 0.008, varied('lilypad', (0.16, 0.34, 0.12), 0.25, 0.4), verts=20)
    pad.rotation_euler.z = R.uniform(0, 6.28)
    if R.random() < 0.5:
        col = R.choice([(0.98, 0.62, 0.72), (0.98, 0.95, 0.92), (0.95, 0.5, 0.62)])
        pm = solid('lilypetal_' + str(col), col, 0.45)
        for k in range(10):
            a = k / 10 * 2 * math.pi + (0.3 if k % 2 else 0); rr = 0.03 if k % 2 else 0.04
            pe = sphere('petal', (p[0] + math.cos(a) * rr, p[1] + math.sin(a) * rr, p[2] + 0.025 + (0.012 if k % 2 else 0)), 0.035, pm, 10, (1.0, 0.38, 0.16))
            pe.rotation_euler = (0, -0.6 if k % 2 else -0.35, a)
        sphere('lily_heart', (p[0], p[1], p[2] + 0.04), 0.016, solid('lily_heart', (0.95, 0.75, 0.2), 0.5), 10)

def garden_lily(p, h, col):
    stem_m = solid('lily_stem', (0.2, 0.36, 0.12), 0.6)
    cyl('lily_stem', (p[0], p[1], p[2] + h / 2), 0.008, h, stem_m, verts=6)
    for k in range(3):
        a = R.uniform(0, 6.28)
        lf = sphere('lily_leaf', (p[0] + math.cos(a) * 0.05, p[1] + math.sin(a) * 0.05, p[2] + h * R.uniform(0.15, 0.45)), 0.08, stem_m, 8, (0.18, 0.9, 0.06))
        lf.rotation_euler = (0.6, 0, a)
    pm = solid('glily_' + str(col), col, 0.5)
    top = Vector((p[0], p[1], p[2] + h))
    for k in range(6):
        a = k / 6 * 2 * math.pi
        pe = sphere('lily_petal', top + Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.02)), 0.05, pm, 10, (1, 0.32, 0.12))
        pe.rotation_euler = (0, -0.75, a)

# ------------------------------------------------------------------ ground
BX, BY = 10.0, 8.6
diorama_base(0, 0, BX, BY, grass_mat())
XL0, XL1 = -4.85, -3.0      # left wing x-range (facade faces +x)
YB0, YB1 = 2.45, 4.15       # back wing y-range (facade faces -y)
GF, F1, F2 = 1.35, 1.2, 1.15
Z1, Z2, ZT = GF, GF + F1, GF + F1 + F2

# terrace slabs along both facades
for i in range(int((4.6 - XL1) / 0.42)):
    for j in range(3):
        box('slab', (XL1 + 0.21 + i * 0.42 + (0.21 if j % 2 else 0), YB0 - 0.25 - j * 0.42, 0.015), (0.4, 0.4, 0.04), travertine, bevel=0.012)
for j in range(int((YB0 - 0.9 + 3.9) / 0.42)):
    for i in range(2):
        box('slab', (XL1 + 0.25 + i * 0.42, -3.9 + 0.21 + j * 0.42 + (0.21 if i % 2 else 0), 0.015), (0.4, 0.4, 0.04), travertine, bevel=0.012)

# ------------------------------------------------------------------ the L
backW = box('back_wing', ((XL1 + 4.6) / 2, (YB0 + YB1) / 2, ZT / 2), (4.6 - XL1, YB1 - YB0, ZT), limestone, bevel=0.04)
leftW = box('left_wing', ((XL0 + XL1) / 2, (-3.6 + YB0 - 0.4) / 2, ZT / 2), (XL1 - XL0, YB0 - 0.4 + 3.6, ZT), limestone, bevel=0.04)
fB = Facade(backW, 'y', -1, YB0)
fL = Facade(leftW, 'x', 1, XL1)


def dress(f, u0, u1, n, door_bay):
    step = (u1 - u0) / n
    us = [u0 + (k + 0.5) * step for k in range(n)]
    # rusticated ground floor, interrupted by the openings
    gaps = [(u - (0.39 if k == door_bay else 0.28) - 0.09, u + (0.39 if k == door_bay else 0.28) + 0.09) for k, u in enumerate(us)]
    a = u0
    for g0, g1 in gaps:
        if g0 > a: f.rustication(a, g0, 0.0, Z1)
        a = g1
    if a < u1: f.rustication(a, u1, 0.0, Z1)
    f.band(u0, u1, Z1 - 0.02, 0.1, 0.07, name='string')
    f.band(u0, u1, Z2 - 0.02, 0.07, 0.05, name='string')
    f.cornice(u0, u1, ZT - 0.18)
    for k, u in enumerate(us):
        if k == door_bay:
            f.window(u, 0.05, 0.78, 1.15, arched=True, keystone=True)
            lantern(tuple(f.P(u - 0.62, 0.12, 0.95)), 1.0); lantern(tuple(f.P(u + 0.62, 0.12, 0.95)), 1.0)
        else:
            f.window(u, 0.18, 0.56, 0.98, arched=True, keystone=True)
        f.window(u, Z1 + 0.12, 0.52, 0.92, hood='pediment' if k % 2 else 'cornice', balcony=False)
        f.window(u, Z2 + 0.1, 0.5, 0.82, hood=None)
        box('bal_console', f.P(u - 0.3, 0.08, Z1 + 0.02), f.S(0.06, 0.14, 0.12), lime_trim, bevel=0.01)
        box('bal_console', f.P(u + 0.3, 0.08, Z1 + 0.02), f.S(0.06, 0.14, 0.12), lime_trim, bevel=0.01)
    # continuous wrought-iron balcony on the second floor (the Haussmann line)
    box('bal_long', f.P((u0 + u1) / 2, 0.2, Z2 + 0.04), f.S(u1 - u0, 0.4, 0.07), lime_trim, bevel=0.012)
    railing(f, u0 + 0.05, u1 - 0.05, Z2 + 0.08, 0.38, 0.36)
    # small balconettes on the first floor
    for u in us[::2]:
        railing(f, u - 0.33, u + 0.33, Z1 + 0.1, 0.08, 0.3)
    # flower boxes on the second-floor railing
    for u in us[1::2]:
        p = f.P(u, 0.48, Z2 + 0.48)
        box('fbox', p, f.S(0.5, 0.14, 0.14), varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75), bevel=0.012)
        hanging_ivy(tuple(p + Vector((0, 0, 0.05))), (0, -1, 0) if f.axis == 'y' else (1, 0, 0), 0.5, 0.75, 6, 'ivy2', (0.26, 0.4, 0.1))
        for d in (-0.15, 0.05, 0.18):
            plant(R.choice(['flower_gazania', 'periwinkle_plant']), tuple(f.P(u + d, 0.48, Z2 + 0.55)), 0.2)
    return us

usB = dress(fB, XL1 + 0.25, 4.55, 6, 3)
usL = dress(fL, -3.55, YB0 - 0.55, 5, 2)
# roof gardens instead of pitched roofs: stone balustrade, lily beds, planters, pergola
def roof_garden(x0, x1, y0, y1, z, pergola=None):
    box('roof_deck', ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.03), (x1 - x0 - 0.1, y1 - y0 - 0.1, 0.06), travertine, bevel=0.01)
    # balustrade: plinth, turned balusters, top rail
    for (a, b, fixed, along) in ((x0, x1, y0, 'x'), (x0, x1, y1, 'x'), (y0, y1, x0, 'y'), (y0, y1, x1, 'y')):
        L = b - a; mid = (a + b) / 2
        if along == 'x':
            box('bal_plinth', (mid, fixed, z + 0.06), (L, 0.16, 0.1), lime_trim, bevel=0.01)
            box('bal_top', (mid, fixed, z + 0.5), (L + 0.04, 0.2, 0.08), lime_trim, bevel=0.015)
        else:
            box('bal_plinth', (fixed, mid, z + 0.06), (0.16, L, 0.1), lime_trim, bevel=0.01)
            box('bal_top', (fixed, mid, z + 0.5), (0.2, L + 0.04, 0.08), lime_trim, bevel=0.015)
        n = int(L / 0.13)
        for k in range(n):
            t = a + (k + 0.5) * L / n
            q = (t, fixed) if along == 'x' else (fixed, t)
            cyl('baluster', (q[0], q[1], z + 0.28), 0.035, 0.34, lime_trim, verts=10, r2=0.025)
            sphere('baluster_bulb', (q[0], q[1], z + 0.2), 0.045, lime_trim, 10, (1, 1, 1.3))
        for c in (a, b):
            q = (c, fixed) if along == 'x' else (fixed, c)
            box('pier', (q[0], q[1], z + 0.3), (0.2, 0.2, 0.6), lime_trim, bevel=0.015)
            sphere('pier_ball', (q[0], q[1], z + 0.66), 0.07, lime_trim, 12)
    # lily beds and planters along the inside of the balustrade
    soil = solid('soil', (0.13, 0.09, 0.06), 0.95)
    cols = [(0.98, 0.55, 0.15), (0.98, 0.95, 0.9), (0.95, 0.45, 0.55), (0.98, 0.75, 0.2)]
    beds = [((x0 + x1) / 2, y0 + 0.4, x1 - x0 - 0.7, 0.45), ((x0 + x1) / 2, y1 - 0.4, x1 - x0 - 0.7, 0.45)] if (x1 - x0) > (y1 - y0) \
        else [(x0 + 0.4, (y0 + y1) / 2, 0.45, y1 - y0 - 0.7), (x1 - 0.4, (y0 + y1) / 2, 0.45, y1 - y0 - 0.7)]
    for (cx, cy, w, d) in beds:
        box('roof_bed', (cx, cy, z + 0.17), (w, d, 0.24), varied('bed_stone', (0.7, 0.65, 0.57), 0.06, 0.8), bevel=0.02)
        box('roof_soil', (cx, cy, z + 0.3), (w - 0.06, d - 0.06, 0.02), soil, bevel=0)
        for k in range(int(w * d * 26)):
            garden_lily((cx + R.uniform(-w / 2 + 0.06, w / 2 - 0.06), cy + R.uniform(-d / 2 + 0.06, d / 2 - 0.06), z + 0.31), R.uniform(0.28, 0.5), R.choice(cols))
        for k in range(int(w * d * 5)):
            plant(R.choice(['fern_02', 'periwinkle_plant']), (cx + R.uniform(-w / 2, w / 2) * 0.85, cy + R.uniform(-d / 2, d / 2) * 0.85, z + 0.31), 0.2)
    for k in range(3):
        u = 0.25 + k * 0.25
        q = (x0 + (x1 - x0) * u, (y0 + y1) / 2) if (x1 - x0) > (y1 - y0) else ((x0 + x1) / 2, y0 + (y1 - y0) * u)
        round_shrub((q[0], q[1], z + 0.06), 0.26, (0.2, 0.34, 0.1), (0.95, 0.7, 0.8) if k == 1 else None, n=300)
    if pergola:
        (px0, px1, py0, py1) = pergola
        for (x, y) in ((px0, py0), (px1, py0), (px0, py1), (px1, py1)):
            box('pg_post', (x, y, z + 0.8), (0.08, 0.08, 1.6), oak, bevel=0.01)
        for y in (py0, py1):
            box('pg_beam', ((px0 + px1) / 2, y, z + 1.62), (px1 - px0 + 0.3, 0.08, 0.12), oak, bevel=0.01)
        n = int((px1 - px0) / 0.22)
        for k in range(n + 1):
            box('pg_slat', (px0 + k * (px1 - px0) / n, (py0 + py1) / 2, z + 1.72), (0.05, py1 - py0 + 0.3, 0.07), oak, bevel=0.005)
        for k in range(280):
            o = link(bpy.data.objects.new('leaf', leaf_mesh('vine', (0.22, 0.38, 0.09))))
            o.location = (R.uniform(px0, px1), R.uniform(py0, py1), z + 1.77 + R.uniform(0, 0.05))
            o.rotation_euler = (R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), R.uniform(0, 6.28))
        hanging_ivy(((px0 + px1) / 2, py0, z + 1.7), (0, -1, 0), px1 - px0, 0.7, 12, 'vine', (0.22, 0.38, 0.09))
        for k in range(3):
            paper_lantern((px0 + (k + 0.5) * (px1 - px0) / 3, (py0 + py1) / 2, z + 1.3), 0.09)
        box('roof_bench', ((px0 + px1) / 2, py1 - 0.25, z + 0.25), (px1 - px0 - 0.4, 0.38, 0.3), oak, bevel=0.02)
    string_lights((x0 + 0.1, y0 + 0.1, z + 0.75), (x1 - 0.1, y0 + 0.1, z + 0.75), 0.18, int((x1 - x0) / 0.35))

roof_garden(XL1, 4.6, YB0, YB1, ZT + 0.06, pergola=(1.2, 2.8, YB0 + 0.75, YB1 - 0.75))
roof_garden(XL0, XL1, -3.6, YB0 - 0.4, ZT + 0.06)

# modern glass pavilion at the corner of the L (joins the wings)
gx0, gx1, gy0, gy1 = XL0, XL1 + 0.05, YB0 - 0.4, YB1
gh = 2.55
glass = solid('pavilion_glass', (0.8, 0.85, 0.85), 0.03)
box('pav_floor', ((gx0 + gx1) / 2, (gy0 + gy1) / 2, 0.06), (gx1 - gx0, gy1 - gy0, 0.12), travertine, bevel=0.01)
box('pav_core', ((gx0 + gx1) / 2, (gy0 + gy1) / 2 + 0.6, gh / 2), (gx1 - gx0 - 0.3, gy1 - gy0 - 1.3, gh), glass_glow('pav_glow', (1.0, 0.7, 0.42), 2.2), bevel=0)
box('pav_roof', ((gx0 + gx1) / 2 + 0.15, (gy0 + gy1) / 2 - 0.15, gh + 0.06), (gx1 - gx0 + 0.5, gy1 - gy0 + 0.5, 0.12), solid('pav_roof', (0.92, 0.9, 0.86), 0.5), bevel=0.01)
for k in range(9):
    x = gx0 + 0.1 + k * (gx1 - gx0 - 0.2) / 8
    box('fin', (x, gy0 + 0.02, gh / 2), (0.035, 0.08, gh), iron, bevel=0)
box('pav_beam', ((gx0 + gx1) / 2, gy0 + 0.02, 1.3), (gx1 - gx0, 0.06, 0.04), iron, bevel=0)
# roof garden on the pavilion
for k in range(4):
    round_shrub(((gx0 + gx1) / 2 - 0.6 + k * 0.42, gy0 + 0.5, gh + 0.12), 0.22, (0.22, 0.36, 0.1), n=160)
hanging_ivy(((gx0 + gx1) / 2, gy0 - 0.1, gh + 0.1), (0, -1, 0), 1.6, 1.2, 14, 'ivy2', (0.26, 0.4, 0.1))
room_light(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 1.3), 160)

# ivy climbing the facades
ivy_patch((4.2, YB0 - 0.02, 0), (0, -1, 0), 0.9, 3.2, 900, 'ivy', (0.18, 0.32, 0.08))
ivy_patch((XL1 + 0.02, -3.3, 0), (1, 0, 0), 0.7, 2.6, 700, 'ivy', (0.18, 0.32, 0.08))

# ------------------------------------------------------------------ garden
# pond with waterlilies + a little stone bridge of stepping slabs
px, py, prx, pry = 1.6, -0.55, 1.75, 1.05
o = cyl('pond_water', (px, py, 0.03), 1.0, 0.03, water, verts=64); o.scale = (prx, pry, 1)
for k in range(44):
    a = k / 44 * 2 * math.pi
    sphere('pond_stone', (px + math.cos(a) * prx * 1.03, py + math.sin(a) * pry * 1.05, 0.04), R.uniform(0.1, 0.16), stone, 12,
           (R.uniform(1.0, 1.5), R.uniform(0.8, 1.1), R.uniform(0.45, 0.7)))
for k in range(26):
    a, rr = R.uniform(0, 6.28), R.random() ** 0.6 * 0.85
    waterlily((px + math.cos(a) * rr * prx, py + math.sin(a) * rr * pry, 0.05), R.uniform(0.08, 0.13))
for k in range(10):
    a = R.uniform(0, 6.28)
    plant(R.choice(['grass_medium_01', 'fern_02']), (px + math.cos(a) * prx * 1.18, py + math.sin(a) * pry * 1.2, 0), R.uniform(0.3, 0.5))
for (x, y) in ((px - 1.9, py - 0.6), (px + 1.9, py + 0.4), (px + 0.4, py - 1.3), (px - 0.9, py + 1.15)):
    ground_light(x, y)
# stepping-stone path from the front corner to the door of the back wing
for k, (x, y) in enumerate([(4.3, -3.9), (3.9, -3.4), (3.6, -2.85), (3.55, -2.25), (3.7, -1.65), (3.65, -1.05), (3.3, -0.2), (2.9, 0.45), (2.4, 1.0), (1.95, 1.55)]):
    box('step', (x, y, 0.02), (0.48, 0.38, 0.05), travertine, bevel=0.02, rot=(0, 0, R.uniform(-0.3, 0.3)))
for (x, y) in ((4.6, -3.2), (3.0, -2.6), (4.3, -0.6), (2.0, 0.9)):
    post_lamp(x, y, 0.85)

# lily beds along the front, curving round
for (cx, cy, w, d) in ((-1.4, -3.65, 3.0, 0.75), (-2.45, -2.1, 0.75, 2.2)):
    box('bed_wall', (cx, cy, 0.12), (w + 0.12, d + 0.12, 0.24), stone, bevel=0.03)
    box('bed_soil', (cx, cy, 0.25), (w, d, 0.02), solid('soil', (0.13, 0.09, 0.06), 0.95), bevel=0)
    for k in range(int(w * d * 22)):
        x, y = cx + R.uniform(-w / 2 + 0.06, w / 2 - 0.06), cy + R.uniform(-d / 2 + 0.06, d / 2 - 0.06)
        garden_lily((x, y, 0.26), R.uniform(0.3, 0.55), R.choice([(0.98, 0.55, 0.15), (0.98, 0.95, 0.9), (0.95, 0.45, 0.55), (0.98, 0.75, 0.2)]))
    for k in range(int(w * d * 5)):
        plant(R.choice(['fern_02', 'periwinkle_plant', 'flower_gazania']), (cx + R.uniform(-w / 2, w / 2) * 0.9, cy + R.uniform(-d / 2, d / 2) * 0.9, 0.26), 0.2)

# trees: weeping willow over the pond, cherry blossoms around the garden
weeping_willow((3.4, 0.55, 0), 3.1, 1.45)
cherry_tree((-1.1, -1.3, 0), 2.3, 1.05, lean=0.15)
cherry_tree((4.35, -2.7, 0), 2.2, 1.0, lean=-0.2, lanterns=1)
cherry_tree((-0.1, 1.05, 0), 1.7, 0.8, lean=0.1, lanterns=1)
# shrubs and hydrangeas along the walls
for (x, y, r, fl) in ((-1.9, 1.75, 0.35, (0.55, 0.62, 0.9)), (0.9, 1.8, 0.3, (0.92, 0.62, 0.78)), (-2.65, -0.5, 0.32, (0.6, 0.66, 0.92)),
                      (-2.6, 0.9, 0.28, None), (1.6, 1.85, 0.25, None), (4.5, 1.6, 0.35, (0.95, 0.7, 0.8)), (0.2, -2.7, 0.25, None)):
    round_shrub((x, y, 0.0), r, (0.18, 0.32, 0.09), fl, n=int(r * 1400))
for i in range(160):
    x, y = R.uniform(-2.8, 4.8), R.uniform(-4.1, 2.0)
    if (x - px) ** 2 / prx ** 2 + (y - py) ** 2 / pry ** 2 < 1.4: continue
    if -2.9 < x < 0.2 and -4.1 < y < -3.2: continue
    plant(R.choice(['grass_medium_01', 'grass_medium_01', 'fern_02', 'periwinkle_plant']), (x, y, 0), R.uniform(0.15, 0.35))
# patio table under the cherry, pots by the doors
cyl('table', (0.35, 0.05, 0.45), 0.32, 0.04, travertine, verts=32, bevel=0.01)
cyl('table_leg', (0.35, 0.05, 0.22), 0.04, 0.44, iron, verts=12)
for a in (0.4, 2.4, 4.4):
    cx, cy = 0.35 + math.cos(a) * 0.55, 0.05 + math.sin(a) * 0.55
    box('chair_seat', (cx, cy, 0.3), (0.32, 0.32, 0.04), oak, bevel=0.01, rot=(0, 0, a))
    box('chair_back', (cx + math.cos(a) * 0.15, cy + math.sin(a) * 0.15, 0.5), (0.04, 0.32, 0.36), oak, bevel=0.01, rot=(0, 0, a))
cyl('candle_jar', (0.35, 0.05, 0.51), 0.035, 0.09, solid('jar', (1, 0.8, 0.5), 0.2, emit=(1, 0.6, 0.25), strength=8), verts=12)
for p, n in [((usB[3] - 0.55, YB0 - 0.35, 0.035), 'shrub_03'), ((usB[3] + 0.55, YB0 - 0.35, 0.035), 'shrub_03'),
             ((XL1 + 0.35, usL[2] - 0.55, 0.035), 'fern_02'), ((XL1 + 0.35, usL[2] + 0.55, 0.035), 'fern_02')]:
    pot(p, 0.18, 0.4, n, 0.55)
# string lights across the garden between the wings
cyl('sl_pole', (4.7, -1.6, 1.15), 0.03, 2.3, iron, verts=10)
string_lights((XL1 + 0.1, -1.2, 2.3), (4.7, -1.6, 2.25), 0.5, 22)
string_lights((1.2, YB0 + 0.0, 2.5), (4.7, -1.6, 2.25), 0.4, 14)

# interiors glow
for x in (-2.0, 0.0, 2.0, 3.8):
    room_light((x, (YB0 + YB1) / 2, 0.8), 70); room_light((x, (YB0 + YB1) / 2, 2.0), 60)
for y in (-2.8, -1.0, 0.8):
    room_light(((XL0 + XL1) / 2, y, 0.8), 70); room_light(((XL0 + XL1) / 2, y, 2.0), 60)

lighting(sc, sun_rot=(math.radians(70), 0, math.radians(-58)), sun_energy=2.3, sun_color=(1.0, 0.62, 0.36),
         bg_top=(0.24, 0.33, 0.44), bg_bottom=(0.88, 0.7, 0.6), hdri_strength=0.3)
iso_camera(sc, (-0.2, 0.3, 1.7), 13.6)
render(sc, OUT, SAMPLES)
