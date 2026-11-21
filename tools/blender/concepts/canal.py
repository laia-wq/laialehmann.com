"""Three old, grimy downtown buildings standing in canal water, joined by a
stone bridge and covered skybridges. Dusk, wet stone, warm windows, gas lamps.
Usage: ASSETS=<assets-raw> python canal.py <out.png> [samples]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

ARGS = [a for a in sys.argv if not a.startswith('-')]
OUT, SAMPLES = ARGS[-2], int(ARGS[-1])
sc = reset()
from garden import *

RG = random.Random(41)
iron = solid('iron_c', (0.05, 0.05, 0.05), 0.45, metal=0.7)
rustm = varied('rust_c', (0.36, 0.2, 0.12), 0.25, 0.7, bump=0.3, bump_scale=50)
soot_brick = bricks('soot_brick', (0.36, 0.2, 0.15), 3.2, mortar=(0.3, 0.28, 0.26))
red_brick = bricks('red_brick2', (0.45, 0.23, 0.16), 3.2, mortar=(0.4, 0.37, 0.33))
plaster_g = stucco('plaster_grime', (0.62, 0.56, 0.46), dirt=(0.2, 0.18, 0.16))
plaster_o = stucco('plaster_ochre_d', (0.6, 0.45, 0.3), dirt=(0.18, 0.15, 0.13))
quay = varied('quay_stone', (0.36, 0.34, 0.31), 0.15, 0.6, bump=0.5, bump_scale=14)
cobble = cobbles('wet_cobble', (0.32, 0.3, 0.28), 11, mortar=(0.1, 0.1, 0.1))
timber = wood('old_timber', (0.3, 0.22, 0.16), 6, axis='Z')
timber_h = wood('old_timber_h', (0.32, 0.24, 0.17), 6)
slate = tile_mat('slate_d', (0.16, 0.17, 0.2))
glow = glass_glow('warm_win', (1.0, 0.58, 0.26), 6.0)
dark_win = solid('dark_win', (0.03, 0.035, 0.04), 0.08)
cobble.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.35   # wet
quay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.45

def canal_water():
    m, n, l, b = node_mat('canal')
    b.inputs['Base Color'].default_value = (0.02, 0.035, 0.035, 1)
    b.inputs['Roughness'].default_value = 0.04
    tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 7
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.06
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

# ------------------------------------------------------------------ helpers
def window_y(wall, x, y, z, w, h, lit=True, side=-1, shutters=None, box_flowers=False):
    cut(wall, box('wc', (x, y, z + h / 2), (w, 0.8, h), None, bevel=0))
    off = -side * 0.07
    box('pane', (x, y + off, z + h / 2), (w, 0.01, h), glow if lit else dark_win, bevel=0)
    fr = solid('wframe_d', (0.18, 0.15, 0.12), 0.6)
    for dx in (-w / 2, 0, w / 2):
        box('wf', (x + dx, y + off * 0.8, z + h / 2), (0.025, 0.03, h), fr, bevel=0)
    for dz in (0, h * 0.6, h):
        box('wf', (x, y + off * 0.8, z + dz), (w, 0.03, 0.025), fr, bevel=0)
    box('sill', (x, y + side * 0.04, z - 0.025), (w + 0.1, 0.12, 0.05), quay, bevel=0.008)
    box('lintel', (x, y + side * 0.02, z + h + 0.05), (w + 0.12, 0.06, 0.1), quay, bevel=0.008)
    if shutters:
        for sg in (-1, 1):
            b = box('shutter', (x + sg * (w * 0.75 + 0.02), y + side * 0.03, z + h / 2), (w / 2, 0.03, h), shutters, bevel=0.005)
            b.rotation_euler.z = sg * RG.uniform(0.0, 0.5)
    if box_flowers:
        box('fbox', (x, y + side * 0.1, z + 0.02), (w, 0.14, 0.1), timber_h, bevel=0.008)
        for k in range(4):
            sphere('geranium', (x - w / 2 + 0.06 + k * w / 4, y + side * 0.1, z + 0.12), 0.04, solid('geranium', (0.75, 0.12, 0.12), 0.6), 8)
        hanging_ivy((x, y + side * 0.1, z + 0.05), (0, side, 0), w, 0.35, 4, 'ivy_d', (0.12, 0.22, 0.07))
    if lit:
        room_light((x, y - side * 0.5, z + h / 2), 14)

def window_x(wall, x, y, z, w, h, lit=True, side=1):
    cut(wall, box('wc', (x, y, z + h / 2), (0.8, w, h), None, bevel=0))
    off = -side * 0.07
    box('pane', (x + off, y, z + h / 2), (0.01, w, h), glow if lit else dark_win, bevel=0)
    fr = solid('wframe_d', (0.18, 0.15, 0.12), 0.6)
    for dy in (-w / 2, 0, w / 2):
        box('wf', (x + off * 0.8, y + dy, z + h / 2), (0.03, 0.025, h), fr, bevel=0)
    for dz in (0, h * 0.6, h):
        box('wf', (x + off * 0.8, y, z + dz), (0.03, w, 0.025), fr, bevel=0)
    box('sill', (x + side * 0.04, y, z - 0.025), (0.12, w + 0.1, 0.05), quay, bevel=0.008)
    if lit:
        room_light((x - side * 0.5, y, z + h / 2), 14)

def building(x0, x1, y0, y1, z0, floors, fh, mat, front_cols, side_cols, lit_p=0.6, shutters=None):
    W, D = x1 - x0, y1 - y0
    H = floors * fh
    o = box('bldg', ((x0 + x1) / 2, (y0 + y1) / 2, z0 + H / 2), (W, D, H), mat, bevel=0.02)
    for f in range(floors):
        z = z0 + f * fh + 0.25
        for k in range(front_cols):
            x = x0 + (k + 0.5) * W / front_cols
            if f == 0 and k == front_cols // 2: continue
            window_y(o, x, y0, z, min(0.5, W / front_cols * 0.55), fh * 0.55, RG.random() < lit_p, -1, shutters, box_flowers=RG.random() < 0.25 and f > 0)
        for k in range(side_cols):
            y = y0 + (k + 0.5) * D / side_cols
            window_x(o, x1, y, z, min(0.45, D / side_cols * 0.5), fh * 0.55, RG.random() < lit_p, 1)
        if f > 0:
            box('string', ((x0 + x1) / 2, y0 - 0.03, z0 + f * fh), (W + 0.04, 0.08, 0.06), quay, bevel=0.006)
            box('string', (x1 + 0.03, (y0 + y1) / 2, z0 + f * fh), (0.08, D + 0.04, 0.06), quay, bevel=0.006)
    # door
    dx = x0 + (front_cols // 2 + 0.5) * W / front_cols
    cut(o, box('dc', (dx, y0, z0 + 0.6), (0.55, 0.6, 1.1), None, bevel=0))
    box('door', (dx, y0 + 0.08, z0 + 0.55), (0.5, 0.05, 1.05), timber, bevel=0.01)
    sphere('knob', (dx + 0.16, y0 + 0.04, z0 + 0.55), 0.02, solid('brass_d', (0.6, 0.45, 0.22), 0.35, metal=1), 8)
    box('door_light', (dx, y0 - 0.05, z0 + 1.25), (0.5, 0.02, 0.12), glow, bevel=0)
    # cornice + drainpipe
    box('cornice', ((x0 + x1) / 2, (y0 + y1) / 2, z0 + H + 0.05), (W + 0.16, D + 0.16, 0.1), quay, bevel=0.01)
    cyl('drain', (x1 - 0.06, y0 - 0.06, z0 + H / 2), 0.035, H, rustm, verts=10)
    room_light(((x0 + x1) / 2, (y0 + y1) / 2, z0 + H / 2), 40)
    return o, z0 + H

def quay_block(x0, x1, y0, y1, top=0.28):
    box('quay', ((x0 + x1) / 2, (y0 + y1) / 2, (top - 0.3) / 2), (x1 - x0, y1 - y0, top + 0.3), quay, bevel=0.02)
    box('quay_top', ((x0 + x1) / 2, (y0 + y1) / 2, top + 0.005), (x1 - x0 - 0.04, y1 - y0 - 0.04, 0.02), cobble, bevel=0)
    # big coping stones along the visible edges
    for k in range(int((x1 - x0) / 0.36)):
        box('coping', (x0 + 0.18 + k * 0.36, y0 + 0.06, top + 0.03), (0.34, 0.14, 0.06), quay, bevel=0.012)
    for k in range(int((y1 - y0) / 0.36)):
        box('coping', (x1 - 0.06, y0 + 0.18 + k * 0.36, top + 0.03), (0.14, 0.34, 0.06), quay, bevel=0.012)
    # algae line at the waterline
    box('algae', ((x0 + x1) / 2, y0 - 0.005, 0.02), (x1 - x0, 0.01, 0.08), solid('algae', (0.08, 0.14, 0.06), 0.4), bevel=0)
    box('algae', (x1 + 0.005, (y0 + y1) / 2, 0.02), (0.01, y1 - y0, 0.08), solid('algae', (0.08, 0.14, 0.06), 0.4), bevel=0)

def gas_lamp(x, y, z0, h=1.15):
    cyl('lamp_base', (x, y, z0 + 0.08), 0.07, 0.16, iron, verts=12, r2=0.045)
    cyl('lamp_post', (x, y, z0 + h / 2), 0.025, h, iron, verts=10)
    for k in range(4):
        a = k / 4 * 2 * math.pi + math.pi / 4
        box('lamp_pane', (x + math.cos(a) * 0.06, y + math.sin(a) * 0.06, z0 + h + 0.12), (0.09, 0.01, 0.18),
            solid('gaslight', (1, 0.85, 0.55), 0.2, emit=(1.0, 0.68, 0.32), strength=12), bevel=0, rot=(0, 0, a + math.pi / 2))
    cyl('lamp_hat', (x, y, z0 + h + 0.25), 0.11, 0.08, iron, verts=4, r2=0.02)
    L = bpy.data.lights.new('gas', 'POINT'); L.energy = 22; L.color = (1.0, 0.66, 0.32); L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('gas', L)).location = (x, y, z0 + h + 0.12)

def wire(a, b, sag=0.3, bulbs=0):
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, t) + Vector((0, 0, -sag * 4 * t * (1 - t))) for t in [k / 14 for k in range(15)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.005, iron)

def laundry(a, b):
    a, b = Vector(a), Vector(b)
    wire(a, b, 0.15)
    cols = [(0.7, 0.66, 0.58), (0.4, 0.18, 0.16), (0.25, 0.32, 0.42), (0.6, 0.5, 0.3)]
    for k in range(1, 6):
        t = k / 6; p = a.lerp(b, t) + Vector((0, 0, -0.15 * 4 * t * (1 - t) - 0.12))
        box('cloth', p, (0.14, 0.01, 0.22), varied('cloth%d' % (k % 4), cols[k % 4], 0.05, 0.9), bevel=0, rot=(0, 0, math.atan2(b.y - a.y, b.x - a.x)))

def fire_escape(x0, x1, y, z_levels):
    for z in z_levels:
        box('fe_deck', ((x0 + x1) / 2, y - 0.3, z), (x1 - x0, 0.6, 0.03), iron, bevel=0)
        for k in range(int((x1 - x0) / 0.08) + 1):
            box('fe_bar', (x0 + k * 0.08, y - 0.6, z + 0.25), (0.012, 0.012, 0.5), iron, bevel=0)
        box('fe_rail', ((x0 + x1) / 2, y - 0.6, z + 0.5), (x1 - x0, 0.02, 0.02), iron, bevel=0)
    for a, b in zip(z_levels, z_levels[1:]):
        limb(Vector((x0 + 0.15, y - 0.3, a)), Vector((x1 - 0.2, y - 0.3, b)), 0.02, iron)
        for k in range(8):
            t = k / 7
            box('fe_step', (x0 + 0.15 + (x1 - x0 - 0.35) * t, y - 0.3, a + (b - a) * t), (0.08, 0.4, 0.015), iron, bevel=0)

def skybridge(a, b, z, w=0.6, h=0.75):
    """Covered timber skybridge between two buildings, with little lit windows."""
    a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
    d = b - a; L = d.length; ang = math.atan2(d.y, d.x); c = (a + b) / 2
    box('sb_body', (c.x, c.y, z + h / 2), (L, w, h), timber_h, bevel=0.015, rot=(0, 0, ang))
    box('sb_floor', (c.x, c.y, z - 0.03), (L + 0.1, w + 0.1, 0.08), quay, bevel=0.01, rot=(0, 0, ang))
    r = box('sb_roof', (c.x, c.y, z + h + 0.06), (L + 0.12, w + 0.2, 0.08), slate, bevel=0.01, rot=(0, 0, ang))
    r.data.materials.clear(); r.data.materials.append(varied('sb_roofm', (0.18, 0.19, 0.22), 0.1, 0.6))
    n = int(L / 0.35)
    nrm = Vector((-math.sin(ang), math.cos(ang), 0))
    for k in range(n):
        p = a + d * ((k + 0.5) / n) - nrm * (w / 2 + 0.005)
        box('sb_win', (p.x, p.y, z + h * 0.55), (0.18, 0.01, 0.26), glow, bevel=0, rot=(0, 0, ang))
    for t in (0.15, 0.85):  # iron brackets underneath
        p = a + d * t
        limb(Vector((p.x, p.y, z - 0.6)), Vector((p.x, p.y, z - 0.05)), 0.03, iron)
    room_light((c.x, c.y, z + h / 2), 20)

def arch_bridge(a, b, w=0.7, h=0.35):
    a, b = Vector(a), Vector(b); d = b - a; L = d.length; ang = math.atan2(d.y, d.x)
    n = 14
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        z0 = 0.28 + h * math.sin(math.pi * t0); z1 = 0.28 + h * math.sin(math.pi * t1)
        c = a + d * ((t0 + t1) / 2)
        box('br_seg', (c.x, c.y, (z0 + z1) / 2 - 0.08), (L / n + 0.02, w, 0.2), quay, bevel=0.01, rot=(0, -math.atan2(z1 - z0, L / n), ang))
        box('br_cob', (c.x, c.y, (z0 + z1) / 2 + 0.025), (L / n + 0.02, w - 0.14, 0.02), cobble, bevel=0, rot=(0, -math.atan2(z1 - z0, L / n), ang))
        nrm = Vector((-math.sin(ang), math.cos(ang), 0))
        for sg in (-1, 1):
            p = c + nrm * sg * (w / 2 - 0.05)
            box('br_parapet', (p.x, p.y, (z0 + z1) / 2 + 0.17), (L / n + 0.02, 0.1, 0.3), quay, bevel=0.01, rot=(0, -math.atan2(z1 - z0, L / n), ang))

def boat(x, y, a, L=1.0):
    hull = sphere('boat', (x, y, 0.06), 0.5, timber_h, 24, (L, 0.32, 0.22)); hull.rotation_euler.z = a
    cut(hull, box('boat_cut', (x, y, 0.3), (2.5, 1.5, 0.4), None, bevel=0))
    cut(hull, sphere('boat_in', (x, y, 0.1), 0.46, None, 20, (L * 0.95, 0.27, 0.2)))
    for k in (-0.2, 0.2):
        box('boat_seat', (x + math.cos(a) * k * L, y + math.sin(a) * k * L, 0.12), (0.06, 0.28, 0.03), timber, bevel=0.005, rot=(0, 0, a))
    lantern((x + math.cos(a) * 0.35 * L, y + math.sin(a) * 0.35 * L, 0.2), 0.6)

def crates(x, y, z):
    for k in range(3):
        box('crate', (x + (k % 2) * 0.26, y, z + 0.11 + (k // 2) * 0.22), (0.24, 0.24, 0.22), timber, bevel=0.01, rot=(0, 0, RG.uniform(-0.2, 0.2)))
    cyl('barrel', (x + 0.6, y, z + 0.17), 0.12, 0.34, timber_h, verts=16, bevel=0.02)
    for dz in (0.06, 0.28):
        cyl('barrel_hoop', (x + 0.6, y, z + dz), 0.125, 0.025, iron, verts=16)

def poster(x, y, z, w, h, col):
    box('poster', (x, y, z), (w, 0.01, h), varied('poster%d' % int(col[0] * 10), col, 0.15, 0.8), bevel=0)

# ------------------------------------------------------------------ stage
diorama_base(0, 0, 10.0, 8.6, canal_water(), z=0.0)

# three buildings on their own quays
quay_block(-4.85, -2.0, 0.2, 4.15)
quay_block(-1.15, 2.35, 1.6, 4.15)
quay_block(2.95, 4.85, -3.3, 1.55)
A, topA = building(-4.6, -2.3, 1.0, 3.9, 0.28, 4, 1.15, soot_brick, 3, 3, 0.55, varied('sh_green', (0.16, 0.24, 0.2), 0.1, 0.6))
B, topB = building(-0.95, 2.15, 2.25, 4.05, 0.28, 3, 1.2, plaster_g, 4, 2, 0.6, varied('sh_red', (0.35, 0.14, 0.12), 0.1, 0.6))
C, topC = building(3.15, 4.65, -2.3, 1.2, 0.28, 3, 1.1, plaster_o, 2, 4, 0.65, varied('sh_blue', (0.18, 0.22, 0.3), 0.1, 0.6))
# roofs: steep slate gable on A, flat with chimneys on B, gable on C
gable_roof('roofA', -3.45, 2.45, 2.3, 2.9, topA + 0.1, 1.2, slate, over=0.15)
gable_roof('roofC', 3.9, -0.55, 1.5, 3.5, topC + 0.1, 0.9, slate, over=0.15)
for (x, y, z, h) in ((-4.1, 3.4, topA + 0.6, 1.2), (-2.9, 1.6, topA + 0.5, 1.0), (-0.4, 3.6, topB + 0.1, 0.8), (1.5, 3.7, topB + 0.1, 0.7), (4.3, 0.8, topC + 0.4, 0.9)):
    box('chimney', (x, y, z + h / 2), (0.28, 0.28, h), red_brick, bevel=0.01)
    for k in range(2):
        cyl('ch_pot', (x - 0.06 + k * 0.12, y, z + h + 0.08), 0.045, 0.16, varied('pot_c', (0.45, 0.25, 0.16), 0.1, 0.8), verts=10)
    sm = solid('smoke_c', (0.22, 0.22, 0.24), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.4
    for k in range(4):
        sphere('smoke', (x + k * 0.1, y + k * 0.04, z + h + 0.35 + k * 0.22), 0.09 + k * 0.045, sm, 12)
box('B_roofwall', (0.6, 3.15, topB + 0.2), (3.1, 1.8, 0.3), plaster_g, bevel=0.01)
cyl('water_tank', (1.6, 2.9, topB + 0.85), 0.32, 0.9, timber, verts=20)
cyl('tank_roof', (1.6, 2.9, topB + 1.4), 0.36, 0.25, iron, verts=20, r2=0.02)
for k in range(4):
    a = k / 4 * 2 * math.pi + 0.5
    limb(Vector((1.6 + math.cos(a) * 0.25, 2.9 + math.sin(a) * 0.25, topB + 0.35)), Vector((1.6 + math.cos(a) * 0.3, 2.9 + math.sin(a) * 0.3, topB + 0.05)), 0.02, iron)
# shopfront on B: awning, sign, display window
box('awning_b', (-0.15, 2.0, 1.45), (1.4, 0.55, 0.03), varied('awning_d', (0.32, 0.12, 0.1), 0.05, 0.9), bevel=0, rot=(0.4, 0, 0))
box('sign_b', (1.15, 2.18, 1.6), (0.9, 0.04, 0.22), solid('sign', (0.12, 0.1, 0.08), 0.6), bevel=0.01)
box('sign_txt', (1.15, 2.155, 1.6), (0.7, 0.01, 0.08), solid('sign_glow', (1, 0.8, 0.5), 0.3, emit=(1.0, 0.7, 0.35), strength=6), bevel=0)
# skybridges and the stone bridge
skybridge((-2.3, 2.7), (-0.95, 2.75), 2.6)
skybridge((2.15, 2.5), (3.15, 1.0), 2.45, w=0.55)
arch_bridge((-2.0, 1.2, 0), (-1.15, 2.0, 0))
arch_bridge((2.35, 2.0, 0), (2.95, 1.25, 0), w=0.6, h=0.25)
# a long timber jetty from the front edge to C's quay and a floating walkway to A
for k in range(16):
    box('jetty', (2.7 + k * 0.0, -4.1 + k * 0.2, 0.2), (0.6, 0.18, 0.04), timber_h, bevel=0.004, rot=(0, 0, RG.uniform(-0.04, 0.04)))
for y in (-4.0, -3.2, -2.4, -1.6, -1.0):
    for x in (2.45, 2.95):
        cyl('jetty_post', (x, y, 0.1), 0.04, 0.4, timber, verts=8)
for k in range(10):
    box('float_walk', (-3.4 + RG.uniform(-0.03, 0.03), -3.9 + k * 0.42, 0.06), (0.55, 0.36, 0.06), timber_h, bevel=0.008, rot=(0, 0, RG.uniform(-0.08, 0.08)))
# street life: lamps, wires, laundry, fire escape, crates, posters, boats
for (x, y) in ((-2.3, 0.55), (-4.6, 0.55), (-0.9, 1.85), (2.2, 1.85), (3.2, -3.0), (4.6, 1.3)):
    gas_lamp(x, y, 0.28)
fire_escape(-0.6, 0.6, 2.25, [1.45, 2.65])
laundry((-2.3, 1.2, 3.6), (-0.95, 2.3, 3.4))
laundry((2.15, 2.3, 3.4), (3.15, 1.1, 3.2))
wire((-2.3, 0.9, 4.3), (3.15, -0.2, 3.3), 0.6)
wire((-4.6, 0.95, 4.0), (-0.95, 2.2, 3.55), 0.5)
crates(-4.3, 0.55, 0.28); crates(3.5, -2.85, 0.28)
for (x, z, col) in ((-4.1, 0.9, (0.75, 0.6, 0.35)), (-3.75, 1.0, (0.6, 0.2, 0.18)), (0.85, 0.95, (0.35, 0.45, 0.55))):
    poster(x, 0.99 if x < -2 else 2.24, z, 0.28, 0.4, col)
boat(-0.9, -0.8, 0.5, 1.1); boat(1.8, -2.6, -0.3, 0.9)
for (x, y) in ((-1.9, 0.0), (-1.1, 1.0), (2.8, -0.5), (2.85, -2.0)):
    cyl('mooring', (x, y, 0.15), 0.05, 0.4, timber, verts=10); cyl('mooring_cap', (x, y, 0.36), 0.06, 0.04, iron, verts=10)
for k in range(14):  # lily pads and floating leaves in the dark water
    x, y = RG.uniform(-1.8, 2.4), RG.uniform(-4.0, 1.0)
    cyl('pad', (x, y, 0.005), RG.uniform(0.06, 0.1), 0.006, varied('pad_d', (0.12, 0.24, 0.08), 0.3, 0.4), verts=14)
ivy_patch((-2.35, 1.6, 0.3), (1, 0, 0), 1.0, 2.6, 500, 'ivy_d', (0.12, 0.22, 0.07))
ivy_patch((3.4, -2.33, 0.3), (0, -1, 0), 0.6, 1.8, 350, 'ivy_d', (0.12, 0.22, 0.07))
for (x, y) in ((-3.0, 0.5), (0.2, 1.9)):
    pot((x, y, 0.28), 0.14, 0.26, 'fern_02', 0.4)

lighting(sc, sun_rot=(math.radians(78), 0, math.radians(-40)), sun_energy=0.6, sun_color=(0.55, 0.62, 0.85),
         bg_top=(0.05, 0.07, 0.13), bg_bottom=(0.35, 0.24, 0.24), hdri_strength=0.08)
iso_camera(sc, (-0.1, 0.4, 2.7), 13.4)
render(sc, OUT, SAMPLES)
