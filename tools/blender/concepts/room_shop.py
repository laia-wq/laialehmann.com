"""Room: Squirrels and Seeds — the corner shop, at night.

A small dry-goods shop run like a donation depot: shelves of jars and tins,
crates chalked IN and OUT, an old counter with a brass till, a ledger and
the laptop that replaced the ledger, a chalkboard with the numbers, and the
shop squirrel on the counter with an acorn.

Hotspots (room_kit.Group): counter, board, shelves, crates, squirrel.

Usage: blender python room_shop.py <out.png> [samples]
Env:   WEB_OUT=dir (masks + scene.json), RES_X/RES_Y, MARKER_FONT, NO_RENDER
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from room_kit import *
from canal_extras import limb
from mathutils import Matrix

OUT = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-2].endswith('.png') else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 96
RG = random.Random(7)
sc = reset()

W, D, H = 3.4, 2.8, 2.2
plaster = stucco('shop_plaster', (0.62, 0.5, 0.38), dirt=(0.42, 0.33, 0.26))
planks = wood('shop_floor', (0.36, 0.22, 0.13), scale=5.0, rough=0.6)
trim = solid('shop_trim', (0.24, 0.3, 0.26), 0.55)
oak = wood('oak', (0.42, 0.27, 0.15), scale=10.0, rough=0.5)
dark_oak = wood('dark_oak', (0.24, 0.15, 0.09), scale=10.0, rough=0.5)
brass = solid('brass', (0.78, 0.58, 0.28), 0.3, metal=1.0)
iron_m = solid('iron', (0.08, 0.08, 0.08), 0.5, metal=0.6)
glass = solid('jar_glass', (0.9, 0.95, 0.95), 0.05)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.9
chalk = solid('chalk', (0.9, 0.9, 0.86), 0.95, emit=(0.9, 0.9, 0.86), strength=0.15)
card = solid('card', (0.74, 0.6, 0.42), 0.9)
ink = solid('ink', (0.08, 0.07, 0.07), 0.8)

shell(W, D, H, plaster, planks, trim)
# wainscot panelling below the rail
for (loc, size) in (((0.02, D / 2, 0.45), (0.02, D, 0.8)), ((W / 2, D - 0.02, 0.45), (W, 0.02, 0.8))):
    box('wainscot', loc, size, trim, bevel=0)

# ---- window on the west wall: the canal at night outside, a bit of rain
cut(bpy.data.objects['wall_w'], box('win_cut', (-0.06, 2.0, 1.45), (0.4, 0.7, 0.9), None, bevel=0))
night = solid('night', (0.05, 0.07, 0.12), 0.5, emit=(0.05, 0.08, 0.16), strength=1.0)
box('win_night', (-0.1, 2.0, 1.45), (0.01, 0.7, 0.9), night, bevel=0)
for (y, z, sy, sz) in ((2.0, 1.45, 0.04, 0.9), (2.0, 1.45, 0.7, 0.04), (1.665, 1.45, 0.04, 0.94), (2.335, 1.45, 0.04, 0.94), (2.0, 1.9, 0.74, 0.04), (2.0, 1.0, 0.8, 0.05)):
    box('win_frame', (-0.02, y, z), (0.06, sy, sz), trim, bevel=0.004)
for k in range(3):   # far lit windows across the canal
    box('far_win', (-0.095, 1.78 + k * 0.2, 1.3 + (k % 2) * 0.25), (0.005, 0.06, 0.09), solid('far_glow', (1, 0.7, 0.4), 0.5, emit=(1, 0.62, 0.3), strength=3.0), bevel=0)

# ---- pendant lamps and the warm room light
for x in (1.6, 2.4):
    limb(Vector((x, 1.15, H)), Vector((x, 1.15, 1.95)), 0.004, iron_m)
    cyl('shade', (x, 1.15, 1.91), 0.13, 0.1, solid('shade_green', (0.12, 0.28, 0.2), 0.4, metal=0.3), verts=24, r2=0.04)
    sphere('bulb', (x, 1.15, 1.86), 0.035, solid('bulb', (1, 0.9, 0.7), 0.3, emit=(1.0, 0.72, 0.4), strength=25), 12)
    L = bpy.data.lights.new('pendant', 'POINT'); L.energy = 60; L.color = (1.0, 0.72, 0.42); L.shadow_soft_size = 0.08
    link(bpy.data.objects.new('pendant', L)).location = (x, 1.15, 1.82)
room_light((2.6, 0.6, 1.9), 70, (1, 0.7, 0.45), 0.6)
room_light((0.8, 0.8, 1.9), 35, (1, 0.75, 0.5), 0.6)

# ---- rug
box('rug', (1.9, 1.1, 0.004), (2.0, 1.3, 0.008), varied('rug', (0.42, 0.16, 0.12), 0.05, 0.95, bump=0.3, bump_scale=120), bevel=0)
box('rug_border', (1.9, 1.1, 0.003), (2.1, 1.4, 0.006), solid('rug_edge', (0.55, 0.45, 0.25), 0.95), bevel=0)

# ---- the counter: till, ledger, the laptop that replaced the ledger
with Group('counter'):
    box('counter', (1.9, 1.35, 0.46), (1.5, 0.5, 0.92), dark_oak, bevel=0.01)
    box('counter_top', (1.9, 1.33, 0.935), (1.6, 0.58, 0.04), oak, bevel=0.008)
    for k in range(4):
        box('counter_panel', (1.29 + k * 0.4, 1.09, 0.45), (0.32, 0.01, 0.6), oak, bevel=0.006)
    # brass till
    tl = Vector((2.45, 1.4, 0.955))
    box('till', tl + Vector((0, 0, 0.09)), (0.26, 0.22, 0.18), brass, bevel=0.02)
    box('till_top', tl + Vector((0, 0.04, 0.22)), (0.22, 0.08, 0.1), brass, bevel=0.02, rot=(0.3, 0, 0))
    for i in range(4):
        for j in range(3):
            cyl('till_key', tl + Vector((-0.08 + i * 0.05, -0.08 - j * 0.03, 0.17 - j * 0.01)), 0.012, 0.02, solid('key', (0.92, 0.9, 0.82), 0.4), verts=10)
    label('0.22', tl + Vector((0, 0.0, 0.245)), 0.04, solid('till_num', (0.2, 0.1, 0.05), 0.5), rot=(math.pi / 2 - 0.3, 0, 0), name='till_num')
    # open ledger with pencilled columns
    lg = Vector((1.35, 1.3, 0.955))
    for sg in (-1, 1):
        pg = box('ledger_page', lg + Vector((sg * 0.105, 0, 0.012 - 0.004 * abs(sg))), (0.2, 0.28, 0.008), solid('page', (0.92, 0.88, 0.78), 0.9), bevel=0.002, rot=(0, sg * -0.06, 0.1))
        for r_ in range(9):
            box('ledger_line', lg + Vector((sg * 0.105, -0.11 + r_ * 0.026, 0.018)), (0.17, 0.0025, 0.001), ink, bevel=0, rot=(0, 0, 0.1))
    box('ledger_cover', lg + Vector((0, 0, 0.002)), (0.44, 0.3, 0.008), solid('ledger', (0.35, 0.1, 0.08), 0.6), bevel=0.003, rot=(0, 0, 0.1))
    limb(lg + Vector((0.1, -0.16, 0.02)), lg + Vector((0.25, -0.12, 0.02)), 0.005, solid('pencil', (0.85, 0.65, 0.1), 0.5))
    # laptop, turned round on the counter to show you the stock page
    lp = Vector((1.9, 1.33, 0.955)); Rl = Matrix.Rotation(math.radians(45), 3, 'Z')
    alu = solid('alu', (0.6, 0.6, 0.62), 0.3, metal=0.9)
    box('laptop_base', lp + Vector((0, 0, 0.008)), (0.34, 0.23, 0.016), alu, bevel=0.004, rot=Rl.to_euler())
    box('laptop_keys', lp + Rl @ Vector((0, -0.02, 0.017)), (0.3, 0.12, 0.002), solid('keys', (0.12, 0.12, 0.13), 0.5), bevel=0, rot=Rl.to_euler())
    def ui(px, w, h):
        rect(px, w, h, 0, 0, w, h, (0.93, 0.9, 0.82))
        rect(px, w, h, 0, h - 9, w, h, (0.26, 0.38, 0.24))           # header
        rect(px, w, h, 3, h - 6, 30, h - 3, (0.95, 0.9, 0.75))
        rect(px, w, h, 0, 0, 16, h - 9, (0.85, 0.8, 0.7))           # sidebar
        for k in range(5): rect(px, w, h, 3, h - 16 - k * 8, 13, h - 13 - k * 8, (0.55, 0.5, 0.42))
        lv = [0.9, 0.35, 0.7, 0.15, 0.55, 0.8, 0.3]
        for k, v in enumerate(lv):                                   # stock rows with level bars
            y = h - 18 - k * 7
            rect(px, w, h, 20, y, 50, y + 4, (0.55, 0.5, 0.42))
            col = (0.75, 0.35, 0.2) if v < 0.25 else (0.85, 0.65, 0.25) if v < 0.5 else (0.35, 0.55, 0.3)
            rect(px, w, h, 54, y, 54 + int(36 * v), y + 4, col)
    scr = screen_image('laptop_ui', 96, 64, ui)
    hinge = lp + Rl @ Vector((0, 0.115, 0.016))
    tilt = Rl @ Matrix.Rotation(math.radians(-15), 3, 'X')
    box('laptop_lid', hinge + tilt @ Vector((0, 0.006, 0.115)), (0.34, 0.012, 0.23), alu, bevel=0.004, rot=tilt.to_euler())
    plane_with('laptop_screen', hinge + tilt @ Vector((0, -0.001, 0.115)), (0.31, 0.205), scr, (tilt @ Matrix.Rotation(math.radians(90), 3, 'X')).to_euler())
    # a clipboard with a pick list
    box('clipboard', (1.62, 1.12, 0.96), (0.16, 0.22, 0.008), dark_oak, bevel=0.002, rot=(0, 0, 0.4))
    box('clip_paper', (1.62, 1.12, 0.966), (0.14, 0.19, 0.002), solid('page', (0.92, 0.88, 0.78), 0.9), bevel=0, rot=(0, 0, 0.4))
    for r_ in range(6):
        box('clip_tick', (1.62 - 0.03 * math.sin(0.4) + r_ * 0.025 * math.sin(0.4), 1.18 - r_ * 0.025 * math.cos(0.4), 0.968), (0.1, 0.004, 0.001), ink, bevel=0, rot=(0, 0, 0.4))
    # a jar of acorns and a stack of receipts on a spike
    cyl('acorn_jar', (2.05, 1.5, 1.04), 0.06, 0.17, glass, verts=20)
    for k in range(14):
        a = k * 2.4; r = 0.035 * math.sqrt((k % 7) / 7)
        sphere('acorn', (2.05 + math.cos(a) * r, 1.5 + math.sin(a) * r, 0.975 + (k // 7) * 0.04), 0.018, solid('acorn', (0.5, 0.3, 0.12), 0.5), 8, (1, 1, 1.3))
    cyl('spike_base', (2.7, 1.25, 0.965), 0.04, 0.02, iron_m, verts=12)
    limb(Vector((2.7, 1.25, 0.97)), Vector((2.7, 1.25, 1.12)), 0.003, iron_m)
    for k in range(6):
        box('receipt', (2.7, 1.25, 0.98 + k * 0.012), (0.08, 0.1, 0.002), solid('receipt', (0.95, 0.93, 0.88), 0.9), bevel=0, rot=(0, 0, k * 0.4))

# ---- the shop squirrel, on the counter end with an acorn
with Group('squirrel'):
    _sq0 = set(bpy.data.objects.keys())
    sq = Vector((1.2, 1.45, 0.955))
    fur = varied('sq_fur', (0.42, 0.15, 0.05), 0.06, 0.9, bump=0.5, bump_scale=300)
    belly = solid('sq_belly', (0.88, 0.78, 0.62), 0.9)
    sphere('sq_body', sq + Vector((0, 0, 0.07)), 0.055, fur, 20, (0.9, 0.8, 1.25))
    sphere('sq_belly', sq + Vector((0.02, -0.025, 0.07)), 0.04, belly, 16, (0.7, 0.6, 1.2))
    hd = sq + Vector((0.01, -0.01, 0.15))
    sphere('sq_head', hd, 0.038, fur, 20, (0.95, 1.1, 0.95))
    sphere('sq_snout', hd + Vector((0.012, -0.035, -0.008)), 0.018, fur, 12)
    sphere('sq_nose', hd + Vector((0.016, -0.05, -0.004)), 0.005, ink, 8)
    for sg in (-1, 1):
        sphere('sq_eye', hd + Vector((sg * 0.02 + 0.008, -0.026, 0.01)), 0.0065, solid('sq_eye', (0.02, 0.02, 0.02), 0.1, coat=1.0), 10)
        cyl('sq_ear', hd + Vector((sg * 0.022, 0.005, 0.04)), 0.012, 0.03, fur, verts=8, r2=0.002)
        sphere('sq_foot', sq + Vector((sg * 0.03, -0.03, 0.01)), 0.016, fur, 10, (0.8, 1.4, 0.6))
        limb(sq + Vector((sg * 0.03, -0.03, 0.1)), sq + Vector((sg * 0.012, -0.05, 0.11)), 0.009, fur)
    sphere('sq_acorn', sq + Vector((0.0, -0.06, 0.115)), 0.016, solid('acorn', (0.5, 0.3, 0.12), 0.5), 10, (1, 1, 1.3))
    cyl('sq_acorn_cap', sq + Vector((0.0, -0.06, 0.133)), 0.017, 0.012, solid('acorn_cap', (0.32, 0.22, 0.12), 0.9), verts=12)
    for k in range(9):   # the big curled tail
        t = k / 8
        p = sq + Vector((-0.05 - 0.05 * math.sin(t * 2.6), 0.04 + 0.02 * t, 0.04 + 0.2 * t - 0.06 * t * t))
        sphere('sq_tail', p, 0.035 + 0.02 * math.sin(t * math.pi), fur, 14)
    # scale the whole squirrel up about its feet
    for n_ in set(bpy.data.objects.keys()) - _sq0:
        o = bpy.data.objects[n_]
        o.location = sq + (o.location - sq) * 1.6
        o.scale = o.scale * 1.6

# ---- shelves on the back wall: what came in, waiting to go out
with Group('shelves'):
    for z in (0.35, 0.8, 1.25, 1.7):
        box('shelf', (1.45, D - 0.17, z), (2.3, 0.3, 0.03), oak, bevel=0.005)
    for x in (0.3, 2.6):
        box('shelf_side', (x, D - 0.17, 1.0), (0.03, 0.3, 1.45), oak, bevel=0.005)
    seeds = [(0.85, 0.7, 0.3), (0.3, 0.2, 0.12), (0.9, 0.85, 0.7), (0.55, 0.4, 0.2), (0.75, 0.25, 0.15), (0.4, 0.5, 0.2)]
    tins = [(0.6, 0.18, 0.12), (0.2, 0.32, 0.45), (0.75, 0.6, 0.2), (0.3, 0.42, 0.3)]
    cloth = [(0.6, 0.25, 0.2), (0.3, 0.36, 0.5), (0.75, 0.68, 0.55), (0.35, 0.45, 0.32)]
    for zi, z in enumerate((0.35, 0.8, 1.25, 1.7)):
        x = 0.42
        while x < 2.48:
            kind = RG.choice(['jar', 'jar', 'tins', 'cloth', 'box']) if zi < 3 else RG.choice(['jar', 'box'])
            y = D - 0.17
            if kind == 'jar':
                h = RG.uniform(0.16, 0.24); r = RG.uniform(0.045, 0.06)
                cyl('jar', (x + r, y, z + 0.015 + h / 2), r, h, glass, verts=20)
                cyl('jar_fill', (x + r, y, z + 0.015 + h * 0.36), r * 0.9, h * 0.7, solid('seed%d' % (zi % 6), RG.choice(seeds), 0.8), verts=16)
                cyl('jar_lid', (x + r, y, z + 0.02 + h), r * 1.02, 0.025, brass, verts=20)
                box('jar_tag', (x + r, y - r - 0.002, z + 0.015 + h * 0.5), (r * 1.2, 0.002, 0.03), card, bevel=0)
                x += 2 * r + 0.03
            elif kind == 'tins':
                for k in range(RG.randint(2, 3)):
                    for s_ in range(RG.randint(1, 2)):
                        cyl('tin', (x + 0.04, y + RG.uniform(-0.05, 0.05), z + 0.06 + s_ * 0.1), 0.035, 0.1, solid('tin%d' % k, RG.choice(tins), 0.4, metal=0.5), verts=16)
                    x += 0.08
                x += 0.03
            elif kind == 'cloth':
                for s_ in range(RG.randint(3, 5)):
                    box('folded', (x + 0.13, y, z + 0.03 + s_ * 0.045), (0.24, 0.22, 0.04), varied('cloth%d' % s_, RG.choice(cloth), 0.1, 0.95, bump=0.3, bump_scale=200), bevel=0.012)
                x += 0.3
            else:
                bw = RG.uniform(0.14, 0.22); bh = RG.uniform(0.12, 0.25)
                box('goods_box', (x + bw / 2, y, z + 0.015 + bh / 2), (bw, 0.22, bh), card, bevel=0.004)
                box('goods_label', (x + bw / 2, y - 0.111, z + 0.015 + bh / 2), (bw * 0.6, 0.002, 0.04), solid('label_w', (0.92, 0.9, 0.84), 0.9), bevel=0)
                x += bw + 0.03
    # sacks of seed on the floor under the window
    for (x, y) in ((0.3, 1.45), (0.55, 1.5), (0.35, 1.15)):
        sphere('sack', (x, y, 0.15), 0.16, varied('burlap', (0.6, 0.48, 0.3), 0.06, 0.95, bump=0.5, bump_scale=150), 16, (0.85, 0.85, 1.1))
        cyl('sack_tie', (x, y, 0.33), 0.04, 0.05, solid('twine', (0.5, 0.4, 0.25), 0.9), verts=10)

# ---- crates chalked IN and OUT
with Group('crates'):
    for (x, y, word, items) in ((0.55, 0.45, 'IN', 'cans'), (3.0, 0.75, 'OUT', 'cloth')):
        box('crate', (x, y, 0.17), (0.5, 0.36, 0.34), varied('crate', (0.5, 0.36, 0.22), 0.1, 0.8), bevel=0.01)
        for k in range(3):
            box('crate_slat', (x, y - 0.181, 0.06 + k * 0.11), (0.5, 0.008, 0.08), varied('crate', (0.5, 0.36, 0.22), 0.1, 0.8), bevel=0.003)
        label(word, (x, y - 0.188, 0.2), 0.12, chalk, name='crate_word')
        for k in range(5):
            if items == 'cans':
                cyl('crate_can', (x - 0.16 + k * 0.08, y + RG.uniform(-0.08, 0.08), 0.37), 0.035, 0.1, solid('tin%d' % (k % 4), tins[k % 4], 0.4, metal=0.5), verts=14)
            else:
                box('crate_cloth', (x - 0.12 + (k % 3) * 0.12, y, 0.36 + (k // 3) * 0.05), (0.14, 0.26, 0.05), varied('cloth%d' % k, cloth[k % 4], 0.1, 0.95), bevel=0.012)

# ---- the chalkboard with the numbers
with Group('board'):
    bx = 2.95
    box('board', (bx, D - 0.04, 1.42), (0.7, 0.02, 0.62), solid('slate_b', (0.06, 0.08, 0.07), 0.85), bevel=0.004)
    box('board_frame', (bx, D - 0.022, 1.42), (0.76, 0.02, 0.68), oak, bevel=0.006)
    rot = (math.pi / 2, 0, 0)
    label('SQUIRRELS & SEEDS', (bx, D - 0.052, 1.65), 0.052, chalk, rot, name='chalk_t')
    for k, line in enumerate(('7 nonprofits piloting', '90,000 records, load-tested', 'stock page 4.7s  to  0.22s')):
        label(line, (bx, D - 0.052, 1.5 - k * 0.11), 0.043, chalk, rot, name='chalk_l')
    limb(Vector((bx - 0.3, D - 0.052, 1.6)), Vector((bx + 0.3, D - 0.052, 1.6)), 0.003, chalk)

# ---- thank-you notes from the seven nonprofits, pinned on a corkboard
with Group('notes'):
    cb = Vector((0.025, 0.75, 1.45))
    box('corkboard', cb, (0.02, 0.8, 0.55), varied('cork', (0.62, 0.45, 0.28), 0.05, 0.95, bump=0.6, bump_scale=300), bevel=0.004)
    box('cork_frame', cb + Vector((-0.004, 0, 0)), (0.02, 0.84, 0.59), oak, bevel=0.004)
    papers = [(0.95, 0.9, 0.6), (0.9, 0.75, 0.75), (0.75, 0.85, 0.95), (0.95, 0.95, 0.9), (0.8, 0.9, 0.7), (0.95, 0.8, 0.55), (0.9, 0.88, 0.95)]
    for k, col in enumerate(papers):
        p = cb + Vector((0.013, -0.3 + (k % 4) * 0.2 + RG.uniform(-0.03, 0.03), 0.12 - (k // 4) * 0.25 + RG.uniform(-0.03, 0.03)))
        nt = box('thank_note', p, (0.003, 0.15, 0.17), solid('note%d' % k, col, 0.9), bevel=0, rot=(RG.uniform(-0.15, 0.15), 0, 0))
        for r_ in range(4):
            box('note_line', p + Vector((0.002, 0, 0.05 - r_ * 0.03)), (0.002, 0.11 - (r_ == 3) * 0.05, 0.004), ink, bevel=0, rot=nt.rotation_euler)
        sphere('pin', p + Vector((0.01, 0, 0.07)), 0.009, solid('pin%d' % (k % 3), [(0.8, 0.15, 0.1), (0.15, 0.35, 0.7), (0.95, 0.8, 0.2)][k % 3], 0.3), 8)
    label('thank you!', cb + Vector((0.015, 0, 0.36)), 0.06, solid('paint_cream', (0.92, 0.86, 0.72), 0.8), rot=(math.pi / 2, 0, -math.pi / 2), name='thanks')

# ---- the donations drop box by the door, and a hand truck of boxes
with Group('crates'):
    db = Vector((0.45, 1.0, 0.0))
    box('drop_box', db + Vector((0, 0, 0.3)), (0.36, 0.3, 0.6), solid('drop_paint', (0.55, 0.2, 0.15), 0.6), bevel=0.012)
    box('drop_slot', db + Vector((0.181, 0, 0.5)), (0.004, 0.18, 0.025), ink, bevel=0)
    label('DONATIONS', db + Vector((0.185, 0, 0.36)), 0.05, solid('paint_cream', (0.92, 0.86, 0.72), 0.8), rot=(math.pi / 2, 0, math.pi / 2), name='drop_word')
    ht = Vector((3.05, 1.55, 0))
    for sg in (-1, 1):
        limb(ht + Vector((sg * 0.15, 0.12, 0.02)), ht + Vector((sg * 0.15, 0.2, 1.05)), 0.012, solid('red_iron', (0.5, 0.12, 0.08), 0.5, metal=0.4))
        cyl('ht_wheel', ht + Vector((sg * 0.18, 0.18, 0.08)), 0.08, 0.04, solid('tyre', (0.04, 0.04, 0.04), 0.8), verts=20, rot=(0, math.pi / 2, 0))
    box('ht_toe', ht + Vector((0, 0.0, 0.015)), (0.34, 0.2, 0.02), solid('red_iron', (0.5, 0.12, 0.08), 0.5, metal=0.4), bevel=0.003)
    for k in range(3):
        box('ht_box', ht + Vector((RG.uniform(-0.02, 0.02), 0.02, 0.15 + k * 0.25)), (0.3 - k * 0.03, 0.22, 0.24), card, bevel=0.005, rot=(0, 0, RG.uniform(-0.1, 0.1)))
        box('ht_tape', ht + Vector((0, 0.02, 0.27 + k * 0.25)), (0.06, 0.222, 0.004), solid('tape', (0.75, 0.65, 0.45), 0.4), bevel=0)

# ---- acorn string lights along the top of the shelves
for k in range(11):
    t = k / 10
    p = Vector((0.35 + 2.2 * t, D - 0.05, 1.92 - 0.08 * math.sin(t * math.pi * 2) ** 2))
    sphere('acorn_light', p, 0.025, solid('acorn_glow', (1, 0.8, 0.5), 0.4, emit=(1.0, 0.65, 0.3), strength=8), 10, (1, 1, 1.25))
    cyl('acorn_light_cap', p + Vector((0, 0, 0.028)), 0.026, 0.02, solid('acorn_cap', (0.32, 0.22, 0.12), 0.9), verts=10)
for k in range(10):
    t0, t1 = k / 10, (k + 1) / 10
    limb(Vector((0.35 + 2.2 * t0, D - 0.05, 1.96 - 0.08 * math.sin(t0 * math.pi * 2) ** 2)), Vector((0.35 + 2.2 * t1, D - 0.05, 1.96 - 0.08 * math.sin(t1 * math.pi * 2) ** 2)), 0.002, ink)
label('SQUIRRELS  &  SEEDS', (1.45, D - 0.002, 2.08), 0.09, solid('paint_cream', (0.92, 0.86, 0.72), 0.8), name='wall_sign')

# ---- odds and ends
stool = Vector((2.3, 0.75, 0))
cyl('stool_seat', stool + Vector((0, 0, 0.62)), 0.15, 0.04, oak, verts=20)
for k in range(3):
    a = k / 3 * 2 * math.pi
    limb(stool + Vector((math.cos(a) * 0.12, math.sin(a) * 0.12, 0)), stool + Vector((math.cos(a) * 0.07, math.sin(a) * 0.07, 0.6)), 0.014, dark_oak)
cyl('plant_pot', (3.15, D - 0.35, 0.14), 0.13, 0.28, varied('terracotta', (0.6, 0.32, 0.2), 0.08, 0.8), verts=20, r2=0.1)
for k in range(9):
    a = k * 0.7
    sphere('plant_leaf', (3.15 + math.cos(a) * 0.1, D - 0.35 + math.sin(a) * 0.08, 0.38 + (k % 3) * 0.12), 0.09, solid('leaf', (0.18, 0.32, 0.12), 0.6), 10, (1, 0.5, 0.35))

# ---- light, camera
lighting(sc, sun_rot=(math.radians(60), 0, math.radians(-40)), sun_energy=0.0, sun_color=(1, 1, 1),
         bg_top=(0.05, 0.05, 0.07), bg_bottom=(0.06, 0.05, 0.06), hdri_strength=0.05)
cam = iso_camera(sc, (1.55, 1.2, 0.95), 4.7, res=(int(os.environ.get('RES_X', 1400)), int(os.environ.get('RES_Y', 1050))))
if not os.environ.get('NO_RENDER'):
    render(sc, OUT, SAMPLES)
if os.environ.get('WEB_OUT'):
    export_web(sc, cam, os.environ['WEB_OUT'])
