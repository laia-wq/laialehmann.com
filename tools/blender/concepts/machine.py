"""Walking machine-houses: rusty riveted hulls on jointed legs, with cottages,
chimneys, pipes, gardens and flags bolted all over. Three original variants.
Usage: ASSETS=<assets-raw> python machine.py <out.png> <kettle|beetle|snail> [samples]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

ARGS = [a for a in sys.argv if not a.startswith('-')]
OUT, STYLE, SAMPLES = ARGS[-3], ARGS[-2], int(ARGS[-1])
sc = reset()
from garden import *
from arch import meadow_flower

RG = random.Random({'kettle': 3, 'beetle': 5, 'snail': 9}[STYLE])
PAL = [(0.98, 0.95, 0.9), (0.98, 0.68, 0.76), (0.98, 0.82, 0.3), (0.72, 0.55, 0.95), (0.96, 0.45, 0.42), (0.99, 0.6, 0.3)]

def metal(name, base, rust_col, rough=0.55):
    """Riveted plate metal: blotchy rust over a base colour, plate seams in the bump."""
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.5; nz.inputs['Detail'].default_value = 8
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    fine = n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 40; l.new(tc.outputs['Object'], fine.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = 0.42; r.color_ramp.elements[0].color = (*base, 1)
    r.color_ramp.elements[1].position = 0.62; r.color_ramp.elements[1].color = (*rust_col, 1)
    l.new(nz.outputs['Fac'], r.inputs['Fac'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.35
    l.new(r.outputs['Color'], mx.inputs['A']); l.new(fine.outputs['Color'], mx.inputs['B'])
    l.new(mx.outputs['Result'], b.inputs['Base Color'])
    br = n.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 2.2; br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = 0.9; br.inputs['Row Height'].default_value = 0.45
    l.new(tc.outputs['Object'], br.inputs['Vector'])
    add = n.new('ShaderNodeMath'); add.operation = 'ADD'
    l.new(br.outputs['Fac'], add.inputs[0]); l.new(fine.outputs['Fac'], add.inputs[1])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35
    l.new(add.outputs['Value'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = 0.35
    return m

M = {
    'kettle': dict(hull=metal('hull', (0.42, 0.3, 0.26), (0.55, 0.28, 0.14)), belly=metal('belly', (0.26, 0.22, 0.22), (0.45, 0.24, 0.13)),
                   cap=metal('cap', (0.32, 0.5, 0.44), (0.5, 0.36, 0.22))),
    'beetle': dict(hull=metal('hull', (0.3, 0.38, 0.42), (0.55, 0.3, 0.16)), belly=metal('belly', (0.25, 0.24, 0.26), (0.48, 0.26, 0.14)),
                   cap=metal('cap', (0.55, 0.36, 0.22), (0.4, 0.22, 0.12))),
    'snail': dict(hull=metal('hull', (0.55, 0.38, 0.26), (0.42, 0.22, 0.12)), belly=metal('belly', (0.3, 0.27, 0.25), (0.45, 0.25, 0.14)),
                  cap=metal('cap', (0.35, 0.52, 0.46), (0.52, 0.38, 0.24))),
}[STYLE]
rustpipe = metal('pipe', (0.4, 0.24, 0.16), (0.55, 0.3, 0.15), 0.6)
iron_d = solid('iron_d', (0.08, 0.07, 0.065), 0.45, metal=0.7)
brass = solid('brass', (0.72, 0.52, 0.25), 0.35, metal=1.0)
plaster = [stucco('pl_cream', (0.85, 0.78, 0.64)), stucco('pl_ochre', (0.8, 0.62, 0.4)), stucco('pl_rose', (0.8, 0.6, 0.54)), wood('pl_planks', (0.5, 0.36, 0.24), 6, axis='Z')]
roofs = [tile_mat('rt_red', (0.62, 0.26, 0.16)), tile_mat('rt_slate', (0.26, 0.28, 0.32)), tile_mat('rt_orange', (0.75, 0.42, 0.2))]
win = glass_glow('m_glow', (1.0, 0.62, 0.3), 5.0)

# ------------------------------------------------------------------ parts
def on_ellipsoid(c, r, az, el):
    """Point and outward normal on an ellipsoid (centre c, radii r) at azimuth/elevation."""
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    p = Vector(c) + Vector((d.x * r[0], d.y * r[1], d.z * r[2]))
    n = Vector((d.x / r[0], d.y / r[1], d.z / r[2])).normalized()
    return p, n

def hull(c, r, mat, bands=(), rivets=True):
    o = sphere('hull', c, 1.0, mat, 48, r)
    for el in bands:  # riveted belts around the hull
        z = c[2] + math.sin(el) * r[2]; k = math.cos(el)
        ring = cyl('belt', (c[0], c[1], z), 1.0, 0.07, iron_d, verts=64); ring.scale = (r[0] * k + 0.035, r[1] * k + 0.035, 1)
        if rivets:
            for i in range(int(40 * k) + 8):
                a = i / (int(40 * k) + 8) * 2 * math.pi
                sphere('rivet', (c[0] + math.cos(a) * (r[0] * k + 0.06), c[1] + math.sin(a) * (r[1] * k + 0.06), z), 0.018, brass, 6)
    return o

def plates(c, r, n, mat, az_range=(-2.6, 0.6), el_range=(-0.5, 0.9)):
    """Patchwork repair plates riveted onto the hull (on the visible side)."""
    for _ in range(n):
        p, nn = on_ellipsoid(c, r, RG.uniform(*az_range), RG.uniform(*el_range))
        w, h = RG.uniform(0.25, 0.6), RG.uniform(0.2, 0.45)
        b = box('plate', p + nn * 0.015, (w, 0.03, h), RG.choice([M['hull'], M['cap'], rustpipe, M['belly']]), bevel=0.008, seg=1)
        b.rotation_euler = nn.to_track_quat('-Y', 'Z').to_euler()
        b.rotation_euler.rotate_axis('Y', RG.uniform(-0.3, 0.3))

def porthole(c, r, az, el, size=0.16):
    p, nn = on_ellipsoid(c, r, az, el)
    q = nn.to_track_quat('Z', 'Y').to_euler()
    rim = cyl('port_rim', p + nn * 0.02, size + 0.05, 0.08, brass, verts=24); rim.rotation_euler = q
    gl = cyl('port_glass', p + nn * 0.05, size, 0.04, win, verts=24); gl.rotation_euler = q
    for k in range(8):
        a = k / 8 * 2 * math.pi
        sphere('port_bolt', p + nn * 0.065 + (Matrix.Rotation(a, 3, nn) @ nn.orthogonal().normalized()) * (size + 0.03), 0.014, brass, 6)

def leg(hip, foot, knee_out, thick=0.09):
    hip, foot = Vector(hip), Vector(foot)
    knee = (hip + foot) / 2 + Vector(knee_out)
    limb(hip, knee, thick, iron_d); limb(knee, foot + Vector((0, 0, 0.1)), thick * 0.75, rustpipe)
    sphere('knee', knee, thick * 1.5, brass, 16)
    sphere('hip', hip, thick * 1.7, iron_d, 16)
    # piston along the thigh
    limb(hip + (knee - hip) * 0.15 + Vector((0, 0, 0.12)), knee + Vector((0, 0, 0.1)), thick * 0.35, brass)
    d = foot - knee; d.z = 0
    a = math.atan2(d.y, d.x) if d.length > 1e-3 else 0
    for k in (-0.5, 0, 0.5):  # three toes
        t = Vector((math.cos(a + k), math.sin(a + k), 0)) * 0.28
        limb(foot + Vector((0, 0, 0.1)), foot + t + Vector((0, 0, 0.02)), thick * 0.45, iron_d)
    sphere('ankle', foot + Vector((0, 0, 0.1)), thick * 1.1, iron_d, 12)

def stack(x, y, z, h, r=0.16, smoke=True):
    cyl('stack', (x, y, z + h / 2), r, h, rustpipe, verts=20, r2=r * 0.85)
    for k in range(int(h / 0.45)):
        cyl('stack_ring', (x, y, z + 0.3 + k * 0.45), r * 1.08, 0.04, iron_d, verts=20)
    cyl('stack_crown', (x, y, z + h + 0.06), r * 1.35, 0.12, iron_d, verts=20, r2=r)
    if smoke:
        sm = solid('smoke_dark', (0.32, 0.3, 0.3), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.55
        for k in range(6):
            sphere('smoke', (x + k * 0.12 + RG.uniform(-0.05, 0.05), y + k * 0.05, z + h + 0.25 + k * 0.2), 0.12 + k * 0.05, sm, 12)

def pipe_path(pts, r=0.045):
    pts = [Vector(p) for p in pts]
    for a, b in zip(pts, pts[1:]):
        limb(a, b, r, rustpipe); sphere('elbow', b, r * 1.25, rustpipe, 10)

def cottage(x, y, z, w, d, h, rot=0.0):
    """A little house bolted onto the machine: plaster or planks, lit windows, tiled roof."""
    mat = RG.choice(plaster)
    o = box('cottage', (x, y, z + h / 2), (w, d, h), mat, bevel=0.02)
    for (u, face) in [(RG.uniform(-w / 3, w / 3), 'f')] + ([(RG.uniform(-d / 4, d / 4), 's')] if RG.random() < 0.7 else []):
        ww, wh = RG.uniform(0.16, 0.26), RG.uniform(0.2, 0.3)
        if face == 'f':
            box('cw', (x + u, y - d / 2 - 0.01, z + h * 0.55), (ww, 0.03, wh), win, bevel=0)
            box('cwf', (x + u, y - d / 2 - 0.005, z + h * 0.55), (ww + 0.05, 0.02, wh + 0.05), solid('frame_w', (0.9, 0.88, 0.82), 0.5), bevel=0)
        else:
            box('cw', (x + w / 2 + 0.01, y + u, z + h * 0.55), (0.03, ww, wh), win, bevel=0)
            box('cwf', (x + w / 2 + 0.005, y + u, z + h * 0.55), (0.02, ww + 0.05, wh + 0.05), solid('frame_w', (0.9, 0.88, 0.82), 0.5), bevel=0)
    for k in range(3):  # timber struts underneath
        limb(Vector((x - w / 2 + 0.1 + k * (w - 0.2) / 2, y - d / 2 + 0.05, z)), Vector((x - w / 2 + 0.1 + k * (w - 0.2) / 2, y - d / 2 + 0.25, z - 0.35)), 0.03, plaster[3])
    gable_roof('c_roof', x, y, w, d, z + h, RG.uniform(0.25, 0.45), RG.choice(roofs), over=0.08, thick=0.05)
    if RG.random() < 0.6:
        cx = x + RG.uniform(-w / 3, w / 3)
        box('c_chim', (cx, y + d / 4, z + h + 0.35), (0.12, 0.12, 0.45), bricks('c_brick', (0.55, 0.27, 0.18), 6), bevel=0.005)
    room_light((x, y, z + h / 2), 25)

def green_tree(base, h=0.9, r=0.45, n=3):
    bark = varied('gt_bark', (0.3, 0.22, 0.16), 0.1, 0.9)
    b = Vector(base); top = b + Vector((RG.uniform(-0.05, 0.05), RG.uniform(-0.05, 0.05), h * 0.55))
    limb(b, top, 0.05, bark)
    for k in range(n):
        a = k / n * 2 * math.pi + RG.uniform(0, 1)
        c = top + Vector((math.cos(a) * r * 0.45, math.sin(a) * r * 0.45, RG.uniform(0.05, 0.3)))
        round_shrub(tuple(c), r * RG.uniform(0.55, 0.75), RG.choice([(0.3, 0.52, 0.14), (0.36, 0.58, 0.16), (0.26, 0.46, 0.12)]), n=int(260 * r))
    round_shrub(tuple(top + Vector((0, 0, r * 0.55))), r * 0.7, (0.34, 0.56, 0.15), n=int(260 * r))

def flags(a, b, n=9):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, t) + Vector((0, 0, -0.25 * 4 * t * (1 - t))) for t in [k / n for k in range(n + 1)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.006, iron_d)
    cols = [(0.85, 0.35, 0.35), (0.95, 0.8, 0.4), (0.45, 0.6, 0.75), (0.95, 0.9, 0.82), (0.55, 0.7, 0.5), (0.9, 0.6, 0.7)]
    for k, p in enumerate(pts[1:-1]):
        me = bpy.data.meshes.new('flag'); bm_ = bmesh.new()
        d = (b - a).normalized() * 0.08
        bm_.faces.new([bm_.verts.new(v) for v in (p - d, p + d, p + Vector((0, 0, -0.22)))]); bm_.to_mesh(me); bm_.free()
        me.materials.append(solid('flag%d' % (k % 6), cols[k % 6], 0.8)); link(bpy.data.objects.new('flag', me))

def lantern_hang(p):
    am = solid('lamp_amber', (1, 0.8, 0.5), 0.3, emit=(1.0, 0.6, 0.28), strength=10)
    cyl('lamp', p, 0.05, 0.11, am, verts=6); cyl('lamp_top', (p[0], p[1], p[2] + 0.075), 0.065, 0.04, brass, verts=6, r2=0.02)
    L = bpy.data.lights.new('hl', 'POINT'); L.energy = 6; L.color = (1, 0.62, 0.3)
    link(bpy.data.objects.new('hl', L)).location = p

# ------------------------------------------------------------------ ground
diorama_base(0, 0, 10.0, 8.6, grass_mat())
for _ in range(260):
    meadow_flower((RG.uniform(-4.8, 4.8), RG.uniform(-4.1, 4.1), 0), RG.uniform(0.1, 0.3), RG.choice(PAL))
rock = varied('rock', (0.5, 0.48, 0.44), 0.2, 0.85, bump=0.5)
for (x, y, s) in ((-4.0, -3.4, 0.4), (4.2, 3.4, 0.5), (4.3, -3.6, 0.3), (-4.2, 3.0, 0.35)):
    sphere('boulder', (x, y, s * 0.3), s, rock, 16, (1.3, 1.0, 0.7))
for (x, y) in ((-3.6, 2.6), (3.8, 2.9), (-3.9, -2.4)):
    green_tree((x, y, 0), 1.6, 0.7)
# footprints of the walker in the grass behind it
for k in range(5):
    cyl('print', (3.6 - k * 0.6, -2.6 + k * 0.2, 0.005), 0.18, 0.01, solid('print', (0.2, 0.28, 0.1), 0.95), verts=12)

# ------------------------------------------------------------------ machine
if STYLE == 'kettle':
    C = (0.0, 0.6, 2.7); Rr = (2.0, 1.7, 1.45)
    hull(C, Rr, M['hull'], bands=(-0.35, 0.25, 0.7))
    hull((0.0, 0.55, 1.75), (1.75, 1.45, 0.75), M['belly'], bands=(0.0,))
    hull((0.1, 0.8, 3.85), (1.05, 0.95, 0.65), M['cap'], bands=(0.1,))
    plates(C, Rr, 34, M['hull'])
    for (az, el) in ((-1.9, 0.1), (-1.4, 0.35), (-0.9, 0.05), (-0.5, 0.45), (-2.3, 0.5)):
        porthole(C, Rr, az, el, RG.uniform(0.1, 0.18))
    # spout-like cannon pipe out the front-right and a crane arm
    pipe_path([(1.4, -0.4, 2.4), (2.2, -1.0, 2.6), (2.7, -1.2, 2.5)], 0.13)
    cyl('spout_mouth', (2.75, -1.22, 2.5), 0.17, 0.12, brass, verts=20, rot=(0, math.pi / 2, -0.4))
    limb(Vector((-1.2, 0.0, 4.0)), Vector((-2.4, -0.6, 4.9)), 0.05, iron_d); limb(Vector((-2.4, -0.6, 4.9)), Vector((-2.4, -0.6, 4.2)), 0.012, iron_d)
    lantern_hang((-2.4, -0.6, 4.12))
    for (hip, foot, ko) in (((1.2, -0.3, 1.35), (2.1, -1.4, 0), (0.5, -0.3, 0.5)), ((-1.2, -0.3, 1.35), (-2.1, -1.3, 0), (-0.5, -0.3, 0.5)),
                            ((1.1, 1.5, 1.35), (2.2, 2.4, 0), (0.5, 0.3, 0.5)), ((-1.1, 1.5, 1.35), (-2.1, 2.5, 0), (-0.5, 0.3, 0.5))):
        leg(hip, foot, ko, 0.1)
    # cottages clinging on top and around
    cottage(-1.1, 0.0, 3.55, 1.0, 0.8, 0.75); cottage(0.85, 1.3, 3.75, 0.9, 0.8, 0.7); cottage(1.55, -0.05, 2.95, 0.8, 0.7, 0.65)
    cottage(-1.85, 0.3, 2.3, 0.7, 0.7, 0.6); cottage(0.2, 0.0, 4.25, 0.7, 0.6, 0.55)
    stack(0.6, 1.7, 3.6, 2.4, 0.18); stack(1.3, 1.5, 3.4, 1.7, 0.12); stack(-0.6, 1.5, 3.9, 1.2, 0.1, smoke=False)
    green_tree((-0.4, 1.0, 4.3), 0.8, 0.42); green_tree((1.7, 0.6, 3.6), 0.6, 0.32)
    flags((0.6, 1.7, 5.9), (-1.1, -0.2, 4.6), 10)
    pipe_path([(-1.7, -0.6, 2.2), (-1.9, -0.9, 3.0), (-1.4, -0.7, 3.6)])
elif STYLE == 'beetle':
    segs = [(-1.9, 0.7, 2.1, (1.0, 1.2, 0.95)), (-0.7, 0.7, 2.35, (1.25, 1.45, 1.2)), (0.7, 0.75, 2.4, (1.3, 1.5, 1.25)), (1.95, 0.8, 2.15, (1.05, 1.25, 1.0))]
    for (x, y, z, r) in segs:
        hull((x, y, z), r, M['hull'] if RG.random() < 0.6 else M['cap'], bands=(0.0, 0.55))
        plates((x, y, z), r, 10, M['hull'])
    hull((0.1, 0.75, 1.45), (2.8, 1.25, 0.6), M['belly'], bands=())
    # glass greenhouse dome at the front, full of green
    gd = sphere('green_dome', (2.55, 0.8, 2.55), 0.75, solid('dome_glass', (0.85, 0.95, 0.92), 0.04), 32, (1, 1, 0.9))
    gd.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.9
    for k in range(8):
        a = k / 8 * math.pi * 2
        limb(Vector((2.55, 0.8, 2.55 + 0.68)), Vector((2.55 + math.cos(a) * 0.75, 0.8 + math.sin(a) * 0.75, 2.55)), 0.015, brass)
    green_tree((2.55, 0.8, 2.3), 0.7, 0.4)
    for (x, y) in ((-1.4, 0.7), (0.0, 0.8), (1.3, 0.75)):
        porthole((x, y, 2.3), (1.2, 1.4, 1.2), -1.57, 0.0, 0.14)
    for i, x in enumerate((-2.0, 0.1, 2.0)):
        for side in (-1, 1):
            hip = (x, 0.75 + side * 1.0, 1.55)
            foot = (x + RG.uniform(-0.4, 0.4), 0.75 + side * 2.3, 0)
            leg(hip, foot, (0, side * 0.4, 0.7), 0.08)
    cottage(-1.8, 0.6, 3.0, 0.8, 0.8, 0.65); cottage(-0.5, 0.95, 3.45, 1.0, 0.85, 0.75); cottage(0.9, 0.5, 3.55, 0.9, 0.75, 0.7)
    cottage(-0.6, -0.4, 2.85, 0.7, 0.6, 0.55)
    stack(-0.1, 1.5, 3.3, 2.0, 0.15); stack(1.5, 1.3, 3.2, 1.4, 0.11)
    # paddle wheel on the side
    wc = Vector((-0.5, -0.65, 1.9))
    cyl('wheel_hub', wc, 0.12, 0.15, brass, verts=16, rot=(math.pi / 2, 0, 0))
    for k in range(10):
        a = k / 10 * 2 * math.pi
        p = wc + Vector((math.cos(a) * 0.65, 0, math.sin(a) * 0.65))
        limb(wc, p, 0.02, iron_d)
        box('paddle', p, (0.25, 0.05, 0.12), M['belly'], bevel=0.01, rot=(0, -a, 0))
    flags((-0.1, 1.5, 5.3), (2.55, 0.8, 3.3), 11)
    pipe_path([(1.9, 0.0, 2.6), (2.2, -0.3, 3.1), (1.6, -0.1, 3.6)])
    lantern_hang((-2.6, 0.3, 2.3)); lantern_hang((1.2, -0.65, 2.0))
else:  # snail: a spiral shell carrying a crooked lighthouse tower
    C = (-0.3, 0.7, 2.0)
    for k in range(7):  # spiral shell: shrinking spheres winding up
        t = k / 6
        a = t * 4.4
        r = 1.55 * (1 - 0.6 * t)
        p = (C[0] + math.cos(a) * 0.7 * (1 - t), C[1] + math.sin(a) * 0.6 * (1 - t), C[2] + t * 1.7)
        hull(p, (r, r * 0.9, r * 0.8), M['hull'] if k % 2 else M['cap'], bands=(0.0,) if k < 4 else ())
    plates(C, (1.6, 1.4, 1.3), 28, M['hull'])
    hull((C[0], C[1], 1.2), (2.0, 1.4, 0.55), M['belly'], bands=())
    # neck and head-like boiler at the front (a boiler, not a face)
    pipe_path([(1.4, 0.2, 1.6), (2.2, -0.3, 1.9), (2.7, -0.6, 2.4)], 0.22)
    hull((2.85, -0.7, 2.6), (0.45, 0.4, 0.4), M['cap'], bands=(0.0,))
    stack(2.9, -0.7, 2.9, 1.0, 0.09)
    # crooked lighthouse tower
    tw = cyl('tower', (-0.2, 0.9, 4.3), 0.42, 2.0, stucco('tower_white', (0.82, 0.76, 0.66)), verts=24, r2=0.34)
    tw.rotation_euler = (0.07, -0.08, 0)
    for k in range(4):
        cyl('tower_band', (-0.2 + k * -0.03, 0.9 + k * 0.03, 3.5 + k * 0.5), 0.43 - k * 0.02, 0.06, M['hull'], verts=24)
    cyl('lamp_room_floor', (-0.32, 1.05, 5.35), 0.55, 0.08, iron_d, verts=24)
    cyl('lamp_room', (-0.32, 1.05, 5.62), 0.36, 0.48, solid('lamp_glass', (1, 0.85, 0.6), 0.1, emit=(1.0, 0.75, 0.4), strength=6), verts=16)
    cyl('lamp_roof', (-0.32, 1.05, 6.05), 0.45, 0.4, M['cap'], verts=16, r2=0.03)
    room_light((-0.32, 1.05, 5.62), 120, (1.0, 0.75, 0.45))
    cottage(-1.5, 0.2, 2.75, 0.9, 0.8, 0.7); cottage(0.9, 1.3, 2.85, 0.85, 0.8, 0.65); cottage(0.9, 0.0, 2.2, 0.75, 0.7, 0.6)
    cottage(-1.2, 1.4, 3.3, 0.7, 0.7, 0.55)
    for (hip, foot, ko) in (((1.0, -0.3, 1.0), (1.8, -1.4, 0), (0.3, -0.3, 0.35)), ((-1.4, -0.3, 1.0), (-2.2, -1.3, 0), (-0.3, -0.3, 0.35)),
                            ((1.0, 1.6, 1.0), (1.9, 2.5, 0), (0.3, 0.3, 0.35)), ((-1.4, 1.6, 1.0), (-2.3, 2.4, 0), (-0.3, 0.3, 0.35))):
        leg(hip, foot, ko, 0.11)
    stack(0.7, 1.7, 2.9, 1.8, 0.14)
    green_tree((-1.7, 1.0, 3.0), 0.7, 0.38); green_tree((0.4, -0.3, 2.9), 0.55, 0.3)
    flags((-0.32, 1.05, 6.25), (2.9, -0.7, 4.0), 12)
    pipe_path([(-1.8, -0.4, 1.6), (-2.1, -0.6, 2.4), (-1.6, -0.3, 2.9)])
    lantern_hang((2.4, -1.0, 2.0))

lighting(sc, sun_rot=(math.radians(60), 0, math.radians(-48)), sun_energy=3.0, sun_color=(1.0, 0.8, 0.6),
         bg_top=(0.3, 0.5, 0.68), bg_bottom=(0.85, 0.86, 0.82), hdri_strength=0.45)
iso_camera(sc, (0.0, 0.4, 2.6), 11.5)
render(sc, OUT, SAMPLES)
