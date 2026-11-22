"""Shared materials and garden props for the house concepts (import after kit.reset())."""
from kit import *

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
    return c

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
    for _ in range(60):
        a, r = R.uniform(0, 6.28), crown * 1.1 * math.sqrt(R.random())
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

