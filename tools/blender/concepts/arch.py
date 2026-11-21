"""Building helpers for the house concepts (import after kit.reset() and garden)."""
from kit import *
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

