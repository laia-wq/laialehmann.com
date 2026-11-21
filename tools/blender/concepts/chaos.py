"""Ramshackle patchwork house concepts: crooked stacked rooms in mismatched
materials, turrets, chimneys, pipes, balconies, laundry, lanterns, a small
cottage garden. Three variants: tumble, stilts, tower.
Usage: ASSETS=<assets-raw> python chaos.py <out.png> <tumble|stilts|tower> [samples]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

ARGS = [a for a in sys.argv if not a.startswith('-')]
OUT, STYLE = ARGS[-3], ARGS[-2]
SAMPLES = int(ARGS[-1])
sc = reset()
from garden import *
from arch import meadow_flower, oakc

RG = random.Random({'tumble': 11, 'stilts': 23, 'tower': 37}[STYLE])
rust = varied('rust', (0.42, 0.22, 0.12), 0.2, 0.7, bump=0.4, bump_scale=60)
copper = varied('copper', (0.33, 0.55, 0.47), 0.12, 0.45, bump=0.2)
brass = solid('brass', (0.72, 0.52, 0.25), 0.35, metal=1.0)
iron2 = solid('iron2', (0.08, 0.07, 0.065), 0.5, metal=0.6)
planks_light = wood('planks_a', (0.55, 0.4, 0.27), 6, axis='Z')
planks_dark = wood('planks_b', (0.33, 0.24, 0.17), 6, axis='Z')
PAL_WALL = {
    'tumble': [stucco('plaster_ochre', (0.8, 0.6, 0.38)), stucco('plaster_rose', (0.78, 0.55, 0.5)), bricks('brick_red', (0.55, 0.26, 0.18), 3.5), planks_light, planks_dark],
    'stilts': [stucco('plaster_blue', (0.52, 0.6, 0.64)), planks_dark, bricks('brick_brown', (0.45, 0.3, 0.22), 3.5), stucco('plaster_cream', (0.8, 0.74, 0.62)), planks_light],
    'tower': [bricks('brick_red', (0.55, 0.26, 0.18), 3.5), stucco('plaster_moss', (0.6, 0.62, 0.48)), planks_light, stucco('plaster_ochre', (0.8, 0.6, 0.38)), planks_dark],
}[STYLE]
ROOFS = [tile_mat('slate', (0.24, 0.26, 0.3)), tile_mat('redtile', (0.58, 0.27, 0.17)), tile_mat('mossy', (0.34, 0.33, 0.24))]
win_glow = glass_glow('chaos_glow', (1.0, 0.62, 0.3), 4.5)
frame_m = solid('chaos_frame', (0.3, 0.2, 0.12), 0.6)
PAL = [(0.98, 0.95, 0.9), (0.98, 0.68, 0.76), (0.98, 0.82, 0.3), (0.72, 0.55, 0.95), (0.96, 0.45, 0.42), (0.99, 0.6, 0.3)]

def child(o, parent, local):
    o.parent = parent; o.location = local
    return o

def add_window(mod, w, d, h, face, u, z, ww, wh, round_=False):
    """Window on a module face, parented so it follows the module's tilt."""
    if face == 'front':
        loc = Vector((u, -d / 2 - 0.02, z)); size = (ww, 0.04, wh); fsize = (ww + 0.08, 0.05, wh + 0.08)
        sill = Vector((u, -d / 2 - 0.06, z - wh / 2 - 0.03)); ssize = (ww + 0.14, 0.12, 0.05)
    else:
        loc = Vector((w / 2 + 0.02, u, z)); size = (0.04, ww, wh); fsize = (0.05, ww + 0.08, wh + 0.08)
        sill = Vector((w / 2 + 0.06, u, z - wh / 2 - 0.03)); ssize = (0.12, ww + 0.14, 0.05)
    if round_:
        r = ww / 2
        rot = (math.pi / 2, 0, 0) if face == 'front' else (0, math.pi / 2, 0)
        child(cyl('rwin_frame', (0, 0, 0), r + 0.05, 0.05, frame_m, verts=24, rot=rot), mod, loc)
        child(cyl('rwin', (0, 0, 0), r, 0.06, win_glow, verts=24, rot=rot), mod, loc)
        for a in (0, math.pi / 2):
            b = box('rwin_bar', (0, 0, 0), (0.02, 0.07, 2 * r) if face == 'front' else (0.07, 0.02, 2 * r), frame_m, bevel=0)
            b.rotation_euler = (0, a, 0) if face == 'front' else (a, 0, 0)
            child(b, mod, loc)
        return
    child(box('wframe', (0, 0, 0), fsize, frame_m, bevel=0.01), mod, loc)
    child(box('wglass', (0, 0, 0), size, win_glow, bevel=0), mod, loc + (Vector((0, -0.01, 0)) if face == 'front' else Vector((0.01, 0, 0))))
    child(box('wbar', (0, 0, 0), (0.025, 0.06, wh) if face == 'front' else (0.06, 0.025, wh), frame_m, bevel=0), mod, loc)
    child(box('wbar', (0, 0, 0), (ww, 0.06, 0.025) if face == 'front' else (0.06, ww, 0.025), frame_m, bevel=0), mod, loc)
    child(box('wsill', (0, 0, 0), ssize, varied('sill_stone', (0.6, 0.55, 0.48), 0.1, 0.8), bevel=0.01), mod, sill)
    if RG.random() < 0.35:  # shutters
        sh = varied('shutter_' + STYLE, RG.choice([(0.3, 0.42, 0.38), (0.55, 0.25, 0.18), (0.32, 0.36, 0.48)]), 0.1, 0.6)
        for sg in (-1, 1):
            off = Vector((sg * (ww / 2 + ww * 0.28), -0.03, 0)) if face == 'front' else Vector((0.03, sg * (ww / 2 + ww * 0.28), 0))
            child(box('shutter', (0, 0, 0), (ww * 0.5, 0.03, wh) if face == 'front' else (0.03, ww * 0.5, wh), sh, bevel=0.006), mod, loc + off)
    if RG.random() < 0.35:  # flower box
        fb = varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75)
        child(box('fbox', (0, 0, 0), (ww + 0.1, 0.14, 0.1) if face == 'front' else (0.14, ww + 0.1, 0.1), fb, bevel=0.01), mod, sill + Vector((0, 0, 0.06)))

def module(cx, cy, z, w, d, h, mat=None, tilt=0.05, windows=2):
    mat = mat or RG.choice(PAL_WALL)
    o = box('room', (cx, cy, z + h / 2), (w, d, h), mat, bevel=0.025)
    o.rotation_euler = (RG.uniform(-tilt, tilt), RG.uniform(-tilt, tilt), RG.uniform(-tilt, tilt))
    # timber corner posts / beams on plaster rooms
    if mat not in (planks_light, planks_dark) and RG.random() < 0.6:
        for sx in (-1, 1):
            for sy in (-1, 1):
                child(box('post', (0, 0, 0), (0.07, 0.07, h + 0.02), planks_dark, bevel=0.008), o, Vector((sx * w / 2, sy * d / 2, 0)))
        child(box('beam', (0, 0, 0), (w + 0.06, 0.07, 0.08), planks_dark, bevel=0.008), o, Vector((0, -d / 2, h / 2 - 0.04)))
    for _ in range(windows):
        face = RG.choice(['front', 'front', 'side'])
        L = w if face == 'front' else d
        ww = RG.uniform(0.28, 0.5); wh = RG.uniform(0.35, 0.6)
        add_window(o, w, d, h, face, RG.uniform(-L / 2 + ww, L / 2 - ww), RG.uniform(-0.05, 0.12), ww, wh, round_=RG.random() < 0.15)
    room_light((cx, cy, z + h / 2), 40 * w * d)
    return o

def roof_on(cx, cy, z, w, d, kind=None):
    kind = kind or RG.choice(['gable', 'gable', 'cone', 'dome', 'lean'])
    m = RG.choice(ROOFS)
    if kind == 'gable':
        gable_roof('roof', cx, cy, w, d, z, RG.uniform(0.45, 0.85), m, over=0.12)
    elif kind == 'cone':
        r = min(w, d) * 0.62
        cyl('cone_roof', (cx, cy, z + 0.55), r, 1.1, varied('cone_' + str(id(m) % 7), (0.3, 0.3, 0.33) if RG.random() < 0.5 else (0.56, 0.27, 0.17), 0.1, 0.7, bump=0.5, bump_scale=25), verts=24, r2=0.02).rotation_euler = (RG.uniform(-0.08, 0.08), RG.uniform(-0.08, 0.08), 0)
        sphere('finial', (cx, cy, z + 1.12), 0.04, brass, 10)
    elif kind == 'dome':
        r = min(w, d) * 0.55
        cyl('drum', (cx, cy, z + 0.06), r * 1.05, 0.12, planks_dark, verts=32)
        sphere('dome', (cx, cy, z + 0.12), r, copper, 32, (1, 1, 0.85))
        cyl('dome_spike', (cx, cy, z + 0.12 + r * 0.85 + 0.1), 0.015, 0.25, brass, verts=8)
    else:
        b = box('lean_roof', (cx, cy, z + 0.12), (w + 0.25, d + 0.25, 0.06), m, bevel=0.01); b.rotation_euler = (RG.uniform(0.15, 0.3), 0, 0)
        # lean roofs need UVs for the tile texture; fall back to plain material
        b.data.materials.clear(); b.data.materials.append(varied('lean_' + STYLE, (0.4, 0.3, 0.24), 0.1, 0.7, bump=0.3))

def turret(cx, cy, z, r, h):
    m = RG.choice(PAL_WALL)
    t = cyl('turret', (cx, cy, z + h / 2), r, h, m, verts=24, bevel=0.02)
    t.rotation_euler = (RG.uniform(-0.05, 0.05), RG.uniform(-0.05, 0.05), 0)
    for k in range(2):
        a = -math.pi / 2 + RG.uniform(-0.5, 0.9)
        box('t_win', (cx + math.cos(a) * r, cy + math.sin(a) * r, z + h * (0.35 + 0.35 * k)), (0.22, 0.05, 0.32), win_glow, bevel=0, rot=(0, 0, a + math.pi / 2))
    roof_on(cx, cy, z + h, 2 * r, 2 * r, RG.choice(['cone', 'cone', 'dome']))
    room_light((cx, cy, z + h / 2), 30)

def chimney(x, y, z, h=None):
    h = h or RG.uniform(0.6, 1.3)
    m = RG.choice([bricks('brick_red', (0.55, 0.26, 0.18), 3.5), rust, iron2])
    if m is iron2 or m is rust:
        c = cyl('flue', (x, y, z + h / 2), 0.06, h, m, verts=12)
        cyl('flue_hat', (x, y, z + h + 0.05), 0.12, 0.06, m, verts=12, r2=0.03)
    else:
        c = box('chimney', (x, y, z + h / 2), (0.24, 0.24, h), m, bevel=0.01)
        box('ch_cap', (x, y, z + h + 0.03), (0.3, 0.3, 0.06), varied('sill_stone', (0.6, 0.55, 0.48), 0.1, 0.8), bevel=0.01)
        cyl('ch_pot', (x, y, z + h + 0.12), 0.05, 0.14, varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75), verts=10)
    c.rotation_euler = (RG.uniform(-0.12, 0.12), RG.uniform(-0.12, 0.12), 0)
    # wisps of smoke
    sm = solid('smoke', (0.85, 0.83, 0.8), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.35
    for k in range(4):
        sphere('smoke', (x + k * 0.07, y - k * 0.03, z + h + 0.3 + k * 0.22), 0.08 + k * 0.04, sm, 12)

def pipe(a, b):
    a, b = Vector(a), Vector(b); mid = (a + b) / 2 + Vector((0, -0.15, 0.1))
    limb(a, mid, 0.03, rust); limb(mid, b, 0.03, rust)
    sphere('elbow', mid, 0.04, rust, 10)

def balcony(cx, y, z, w):
    box('balc', (cx, y - 0.22, z), (w, 0.44, 0.06), planks_light, bevel=0.01)
    for k in range(int(w / 0.09) + 1):
        box('baluster', (cx - w / 2 + k * w / int(w / 0.09), y - 0.43, z + 0.2), (0.02, 0.02, 0.36), planks_dark, bevel=0)
    box('rail', (cx, y - 0.43, z + 0.39), (w, 0.04, 0.04), planks_dark, bevel=0.005)
    for sg in (-1, 1):
        limb(Vector((cx + sg * w * 0.4, y, z - 0.4)), Vector((cx + sg * w * 0.4, y - 0.4, z - 0.03)), 0.025, planks_dark)

def laundry(a, b):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, t) + Vector((0, 0, -0.18 * 4 * t * (1 - t))) for t in [k / 10 for k in range(11)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.004, iron2)
    cols = [(0.85, 0.82, 0.75), (0.6, 0.35, 0.3), (0.45, 0.55, 0.65), (0.85, 0.72, 0.4)]
    for k in range(2, 9, 2):
        p = pts[k]
        box('cloth', p - Vector((0, 0, 0.12)), (0.16, 0.01, 0.22), varied('cloth%d' % k, cols[k // 2 % 4], 0.05, 0.9), bevel=0, rot=(0, 0, math.atan2(b.y - a.y, b.x - a.x)))

def hanging_lamp(p):
    x, y, z = p
    am = solid('lamp_amber', (1, 0.8, 0.5), 0.3, emit=(1.0, 0.6, 0.28), strength=9)
    cyl('lamp_glass', (x, y, z), 0.055, 0.12, am, verts=6)
    cyl('lamp_top', (x, y, z + 0.08), 0.07, 0.05, brass, verts=6, r2=0.02)
    cyl('lamp_chain', (x, y, z + 0.2), 0.004, 0.2, iron2, verts=6)
    L = bpy.data.lights.new('hl', 'POINT'); L.energy = 8; L.color = (1, 0.62, 0.3)
    link(bpy.data.objects.new('hl', L)).location = p

# ------------------------------------------------------------------ ground: small cottage garden
diorama_base(0, 0, 10.0, 8.6, grass_mat())
rocks = varied('found_rock', (0.5, 0.47, 0.42), 0.2, 0.85, bump=0.5)
for k in range(40):  # crooked cobbled path
    t = k / 39
    x = 2.6 - t * 2.4 + math.sin(t * 5) * 0.4; y = -4.0 + t * 3.0
    box('cobble', (x + RG.uniform(-0.15, 0.15), y, 0.02), (RG.uniform(0.18, 0.3), RG.uniform(0.16, 0.26), 0.05), rocks, bevel=0.025, rot=(0, 0, RG.uniform(0, 3)))
for _ in range(160):
    x, y = RG.uniform(-4.7, 4.7), RG.uniform(-4.0, 4.0)
    if -3.2 < x < 2.4 and -0.8 < y < 3.6: continue
    meadow_flower((x, y, 0), RG.uniform(0.1, 0.3), RG.choice(PAL))
cherry_tree((3.6, 2.4, 0), 2.2, 1.0, lean=-0.2, lanterns=1)
cherry_tree((-4.0, -2.8, 0), 1.8, 0.85, lean=0.2, lanterns=1)
for (x, y) in ((2.0, -3.0), (-0.2, -1.7), (3.2, -1.0)):
    cyl('lamp_post', (x, y, 0.55), 0.025, 1.1, iron2, verts=8)
    limb(Vector((x, y, 1.1)), Vector((x + 0.2, y, 1.18)), 0.015, iron2)
    hanging_lamp((x + 0.2, y, 0.98))
# a little pond and a woodpile
pw = cyl('pond', (3.2, -2.6, 0.02), 0.8, 0.02, solid('pond_c', (0.04, 0.1, 0.1), 0.05), verts=40); pw.scale = (1.0, 0.7, 1)
for k in range(22):
    a = k / 22 * 2 * math.pi
    sphere('pstone', (3.2 + math.cos(a) * 0.82, -2.6 + math.sin(a) * 0.58, 0.04), RG.uniform(0.07, 0.11), rocks, 10, (1.2, 0.9, 0.6))
for k in range(12):
    cyl('log', (-3.6 + (k % 4) * 0.13, -0.2, 0.08 + (k // 4) * 0.12), 0.06, 0.6, planks_light, verts=10, rot=(math.pi / 2, 0, 0))

# ------------------------------------------------------------------ the house
CX, CY = -0.6, 1.6
if STYLE == 'tumble':
    base = box('foundation', (CX, CY, 0.2), (4.6, 2.8, 0.4), rocks, bevel=0.06)
    a = module(CX - 1.2, CY, 0.4, 2.0, 2.4, 1.5, PAL_WALL[2])
    b = module(CX + 0.9, CY + 0.1, 0.4, 2.2, 2.2, 1.25, PAL_WALL[0])
    c = module(CX - 0.6, CY - 0.15, 1.9, 2.8, 2.2, 1.2, PAL_WALL[1])      # overhangs
    d = module(CX + 1.3, CY + 0.2, 1.65, 1.5, 1.6, 1.0, PAL_WALL[3])
    e = module(CX - 0.1, CY + 0.1, 3.1, 1.8, 1.7, 1.0, PAL_WALL[4])
    f = module(CX - 1.5, CY - 0.2, 3.1, 1.0, 1.1, 0.8, PAL_WALL[0])
    roof_on(CX - 0.1, CY + 0.1, 4.1, 1.8, 1.7, 'gable'); roof_on(CX + 1.3, CY + 0.2, 2.65, 1.5, 1.6, 'gable')
    roof_on(CX - 1.5, CY - 0.2, 3.9, 1.0, 1.1, 'dome')
    turret(CX + 2.05, CY - 0.75, 0.4, 0.42, 3.4); turret(CX - 2.3, CY + 0.6, 1.9, 0.35, 1.8)
    for (x, y, z) in ((CX - 0.9, CY + 0.6, 4.25), (CX + 0.5, CY + 0.5, 4.3), (CX + 1.8, CY + 0.6, 2.9), (CX - 1.9, CY + 0.2, 3.9)):
        chimney(x, y, z)
    balcony(CX + 0.4, CY - 1.25, 1.95, 1.2)
    pipe((CX + 1.9, CY - 0.6, 2.4), (CX + 0.7, CY - 1.0, 3.5))
    laundry((CX - 2.1, CY - 1.3, 2.9), (CX + 0.2, CY - 1.25, 2.6))
    for k in range(4):
        limb(Vector((CX - 2.0 + k * 0.9, CY - 1.1, 0.4)), Vector((CX - 2.0 + k * 0.9, CY - 1.25, 1.85)), 0.04, planks_dark)
    door_at = (CX + 0.6, CY - 1.0)
elif STYLE == 'stilts':
    # the whole house stands on crooked timber legs over the garden
    LZ = 1.1
    for (x, y) in ((-2.4, 0.4), (-2.6, 2.6), (0.2, 0.1), (0.4, 2.9), (1.6, 0.6), (1.7, 2.5), (-1.2, 0.0)):
        top = Vector((CX + x * 0.85 + 0.25, CY + (y - 1.5) * 0.8, LZ + 0.05))
        foot = Vector((CX + x + RG.uniform(-0.2, 0.2), CY + y - 1.5 + RG.uniform(-0.2, 0.2), 0.0))
        limb(foot, top, 0.09, planks_dark)
        cyl('leg_foot', (foot.x, foot.y, 0.06), 0.16, 0.12, rocks, verts=10)
    box('deck', (CX, CY, LZ + 0.06), (4.3, 2.9, 0.12), planks_light, bevel=0.02)
    a = module(CX - 1.0, CY + 0.2, LZ + 0.12, 2.2, 2.2, 1.35, PAL_WALL[0])
    b = module(CX + 1.15, CY + 0.35, LZ + 0.12, 1.6, 1.8, 1.6, PAL_WALL[1])
    c = module(CX - 0.3, CY + 0.25, LZ + 1.47, 2.4, 1.9, 1.1, PAL_WALL[2])
    d = module(CX + 1.3, CY + 0.4, LZ + 1.72, 1.2, 1.3, 0.9, PAL_WALL[3])
    e = module(CX - 0.5, CY + 0.35, LZ + 2.57, 1.4, 1.3, 0.85, PAL_WALL[4])
    roof_on(CX - 0.5, CY + 0.35, LZ + 3.42, 1.4, 1.3, 'gable'); roof_on(CX + 1.3, CY + 0.4, LZ + 2.62, 1.2, 1.3, 'dome')
    roof_on(CX - 1.4, CY + 0.25, LZ + 2.57, 0.9, 1.2, 'lean')
    turret(CX - 2.05, CY - 0.5, LZ + 0.12, 0.38, 2.6)
    for (x, y, z) in ((CX - 0.1, CY + 0.7, LZ + 3.6), (CX + 0.9, CY + 0.9, LZ + 2.6), (CX - 1.0, CY + 0.6, LZ + 2.6)):
        chimney(x, y, z)
    # ladder-stair up to the deck
    for k in range(9):
        box('step', (CX + 1.6 - k * 0.0, CY - 1.55 - 0.0 + k * 0.0 + (8 - k) * -0.11, (k + 1) * LZ / 9), (0.6, 0.18, 0.04), planks_light, bevel=0.005)
    limb(Vector((CX + 1.3, CY - 2.5, 0)), Vector((CX + 1.3, CY - 1.45, LZ)), 0.03, planks_dark)
    limb(Vector((CX + 1.9, CY - 2.5, 0)), Vector((CX + 1.9, CY - 1.45, LZ)), 0.03, planks_dark)
    balcony(CX - 0.4, CY - 0.7, LZ + 1.52, 1.6)
    pipe((CX + 1.75, CY - 0.4, LZ + 1.0), (CX + 1.6, CY - 0.3, LZ + 2.3))
    laundry((CX - 2.1, CY - 1.2, LZ + 1.0), (CX + 0.5, CY - 1.3, LZ + 0.9))
    for (x, y) in ((CX - 1.0, CY - 1.0), (CX + 0.6, CY - 1.0)):
        hanging_lamp((x, y, LZ - 0.25))
    box('hammock', (CX - 0.4, CY + 0.6, 0.55), (1.6, 0.5, 0.04), varied('hammock', (0.85, 0.72, 0.5), 0.05, 0.9), bevel=0.02, rot=(0, 0.0, 0.1))
    door_at = (CX + 1.6, CY - 1.4)
else:  # tower
    base = box('foundation', (CX, CY, 0.2), (3.2, 2.6, 0.4), rocks, bevel=0.06)
    t = cyl('tower_core', (CX, CY, 0.4 + 2.6), 0.85, 5.2, PAL_WALL[0], verts=32, bevel=0.02)
    t.rotation_euler = (0.06, -0.05, 0)
    for k, z in enumerate((1.0, 2.4, 3.8)):
        a = -math.pi / 2 + (k - 1) * 0.5
        box('tw', (CX + math.cos(a) * 0.86, CY + math.sin(a) * 0.86, z), (0.28, 0.05, 0.42), win_glow, bevel=0, rot=(0, 0, a + math.pi / 2))
    a = module(CX + 1.25, CY - 0.1, 0.4, 1.6, 2.0, 1.4, PAL_WALL[1])
    b = module(CX - 1.35, CY + 0.2, 0.4, 1.5, 1.8, 1.7, PAL_WALL[2])
    c = module(CX + 1.05, CY - 0.35, 2.2, 1.5, 1.4, 1.05, PAL_WALL[3])   # bolted on high
    d = module(CX - 1.15, CY - 0.2, 3.1, 1.3, 1.2, 0.95, PAL_WALL[4])
    e = module(CX + 0.2, CY - 0.5, 4.3, 1.4, 1.2, 0.9, PAL_WALL[1])
    for (x, y, z) in ((CX + 1.05, CY - 1.0, 2.2), (CX + 1.7, CY - 1.0, 2.2), (CX - 1.15, CY - 0.75, 3.1), (CX - 1.7, CY - 0.75, 3.1), (CX + 0.2, CY - 1.05, 4.3)):
        limb(Vector((x, y + 0.05, z - 0.6)), Vector((x, y, z)), 0.035, planks_dark)
    roof_on(CX, CY, 5.6, 1.9, 1.9, 'cone'); roof_on(CX + 1.25, CY - 0.1, 1.8, 1.6, 2.0, 'gable')
    roof_on(CX + 1.05, CY - 0.35, 3.25, 1.5, 1.4, 'dome'); roof_on(CX - 1.15, CY - 0.2, 4.05, 1.3, 1.2, 'gable')
    roof_on(CX + 0.2, CY - 0.5, 5.2, 1.4, 1.2, 'lean'); roof_on(CX - 1.35, CY + 0.2, 2.1, 1.5, 1.8, 'lean')
    turret(CX - 2.05, CY + 0.9, 0.4, 0.32, 2.2)
    add_window(t, 1.7, 1.7, 5.2, 'front', 0.0, 1.55, 0.7, 0.7, round_=True)
    for (x, y, z) in ((CX + 0.5, CY + 0.6, 5.6), (CX - 1.4, CY + 0.0, 4.1), (CX + 1.5, CY + 0.3, 3.4), (CX + 1.6, CY + 0.4, 1.9)):
        chimney(x, y, z)
    balcony(CX, CY - 0.85, 3.0, 1.0)
    pipe((CX + 0.8, CY - 0.6, 1.6), (CX + 0.9, CY - 0.9, 2.9)); pipe((CX - 0.6, CY - 0.7, 3.4), (CX - 0.9, CY - 0.8, 4.6))
    laundry((CX - 1.9, CY - 1.0, 2.5), (CX - 0.6, CY - 0.95, 2.8))
    door_at = (CX + 0.2, CY - 0.85)

# door, steps, pots, ivy, lanterns at the entrance
dx, dy = door_at
box('door', (dx, dy - 0.02, 0.85 if STYLE != 'stilts' else 1.6), (0.5, 0.06, 0.85), planks_dark, bevel=0.01)
sphere('knob', (dx + 0.15, dy - 0.07, 0.85 if STYLE != 'stilts' else 1.6), 0.025, brass, 8)
hanging_lamp((dx - 0.4, dy - 0.15, 1.35 if STYLE != 'stilts' else 2.05))
for k in range(3):
    pot((dx - 0.9 + k * 0.25 + (1.4 if k == 2 else 0), dy - 0.45, 0.0), 0.12 + 0.03 * k, 0.22 + 0.05 * k, None)
    for _ in range(6):
        meadow_flower((dx - 0.9 + k * 0.25 + (1.4 if k == 2 else 0) + RG.uniform(-0.06, 0.06), dy - 0.45 + RG.uniform(-0.06, 0.06), 0.2 + 0.05 * k), RG.uniform(0.08, 0.2), RG.choice(PAL))
ivy_patch((CX - 2.2, CY - 1.2, 0.3), (0, -1, 0), 1.2, 2.4, 600, 'ivy', (0.22, 0.36, 0.1))
ivy_patch((CX + 2.1, CY + 0.2, 0.3), (1, 0, 0), 1.0, 2.0, 400, 'ivy', (0.22, 0.36, 0.1))

lighting(sc, sun_rot=(math.radians(66), 0, math.radians(-52)), sun_energy=2.6, sun_color=(1.0, 0.66, 0.42),
         bg_top=(0.36, 0.46, 0.55), bg_bottom=(0.9, 0.8, 0.7), hdri_strength=0.35)
iso_camera(sc, (-0.3, 0.6, 2.2), 12.0)
render(sc, OUT, SAMPLES)
