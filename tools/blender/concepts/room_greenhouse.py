"""Room: Lilies & Rain + Lilies & Fire — one glasshouse, two halves.

Rain lilies really do bloom right after rain; fire lilies bloom after
bushfires. So: the left half is the rain side (cool, wet, pale lilies grown
for steady funding), the right half the fire side (ash and ember, orange
lilies grown for emergency and disaster preparation). A potting bench runs
down the middle with the four stages of tending, one per station:
  FIND    a seed catalogue and fanned packets (the open grants)
  DECIDE  a balance weighing two bulbs
  DRAFT   a bulb going into a glass pot, its roots made of paperwork
  REVIEW  the bloom on a stand, a magnifier, a tag
One gardener tends both; GARDENER=rain|fire puts them on that side (the
browser crossfades between the two renders when you switch tabs).
A garden stake carries the honest status: a seedling, no users yet.

Hotspots: rain, fire, find, decide, draft, review, status, gardener.
Usage: blender python room_greenhouse.py <out.png> [samples]
Env:   GARDENER=rain|fire, WEB_OUT, RES_X/RES_Y, MARKER_FONT, NO_RENDER
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from room_kit import *
from canal_extras import limb
from mathutils import Matrix

OUT = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-2].endswith('.png') else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 96
SIDE = os.environ.get('GARDENER', 'rain')
RG = random.Random(5)
sc = reset()

W, D, H = 4.0, 3.2, 2.3
MID = 2.0                       # x of the bench: rain side x < MID, fire side x > MID
brick = bricks('gh_brick', (0.5, 0.28, 0.2), scale=6.0)
floor_t = tile_mat('gh_floor', (0.5, 0.3, 0.22))
iron_g = solid('gh_iron', (0.16, 0.22, 0.2), 0.45, metal=0.6)
pane = solid('gh_pane', (0.75, 0.85, 0.85), 0.04)
pane.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.14
night = solid('gh_night', (0.04, 0.06, 0.1), 0.5, emit=(0.04, 0.07, 0.13), strength=1.0)
oak = wood('oak', (0.42, 0.27, 0.15), scale=10.0, rough=0.5)
weathered = wood('weathered', (0.45, 0.38, 0.3), scale=8.0, rough=0.8)
brass = solid('brass', (0.78, 0.58, 0.28), 0.3, metal=1.0)
paper = solid('paper', (0.93, 0.9, 0.82), 0.9)
ink = solid('ink', (0.08, 0.07, 0.07), 0.8)
red = solid('red_ink', (0.7, 0.1, 0.08), 0.6)
glass = solid('glass', (0.92, 0.96, 0.96), 0.03)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.95
terracotta = varied('terracotta', (0.62, 0.32, 0.2), 0.08, 0.8, bump=0.2)
soil = solid('soil', (0.16, 0.1, 0.07), 0.95)
ash_soil = varied('ash_soil', (0.2, 0.19, 0.18), 0.1, 0.95, bump=0.4, bump_scale=60)
cream = solid('paint_cream', (0.92, 0.86, 0.72), 0.8)
stake_m = solid('stake', (0.82, 0.74, 0.58), 0.8)

# ---- the glasshouse: brick floor and knee walls, iron-framed glass above
box('floor', (W / 2, D / 2, -0.04), (W, D, 0.08), floor_t, bevel=0)
box('knee_w', (-0.08, D / 2, 0.25), (0.16, D + 0.16, 0.5), brick, bevel=0.005)
box('knee_n', (W / 2, D + 0.08, 0.25), (W + 0.16, 0.16, 0.5), brick, bevel=0.005)
box('sill_w', (-0.08, D / 2, 0.52), (0.2, D + 0.2, 0.04), weathered, bevel=0.005)
box('sill_n', (W / 2, D + 0.08, 0.52), (W + 0.2, 0.2, 0.04), weathered, bevel=0.005)
for (loc, size) in (((-0.1, D / 2, 1.4), (0.01, D, 1.75)), ((W / 2, D + 0.1, 1.4), (W, 0.01, 1.75))):
    box('outside', loc, size, night, bevel=0)
with Group('glass'):
    box('pane_w', (-0.06, D / 2, 1.4), (0.006, D, 1.75), pane, bevel=0)
    box('pane_n', (W / 2, D + 0.06, 1.4), (W, 0.006, 1.75), pane, bevel=0)
for k in range(9):           # mullions
    y = k * D / 8
    box('mullion', (-0.06, y, 1.4), (0.035, 0.025, 1.78), iron_g, bevel=0)
for k in range(11):
    x = k * W / 10
    box('mullion', (x, D + 0.06, 1.4), (0.025, 0.035, 1.78), iron_g, bevel=0)
for z in (0.9, 1.6, 2.27):
    box('transom', (-0.06, D / 2, z), (0.035, D, 0.025), iron_g, bevel=0)
    box('transom', (W / 2, D + 0.06, z), (W, 0.035, 0.025), iron_g, bevel=0)
# a roof beam overhead, the first ribs of the glass roof, hanging baskets
# hanging signs over each half (painted boards on chains)
def hanging_board(c, text, col, txt_col, emit=0.0):
    for dx in (-0.25, 0.25):
        limb(c + Vector((dx, 0, 0.1)), c + Vector((dx * 0.6, 0, 0.45)), 0.004, iron_g)
    box('sign_board', c, (0.7, 0.04, 0.2), col, bevel=0.01)
    m = solid('sign_txt_%s' % text, txt_col, 0.6, emit=txt_col if emit else None, strength=emit)
    label(text, c + Vector((0, -0.022, 0)), 0.11, m, name='sign_t')
# the cut edge of the dollhouse
edge = solid('cut_edge', (0.1, 0.08, 0.07), 0.9)
box('cut_f1', (W / 2, -0.005, -0.04), (W, 0.012, 0.085), edge, bevel=0)
box('cut_f2', (W + 0.005, D / 2, -0.04), (0.012, D, 0.085), edge, bevel=0)

# ---- the RAIN side: cool, wet, pale lilies grown for steady funding
with Group('rain'):
    # tiered staging against the west glass
    for t in range(3):
        x0 = 0.18 + t * 0.26; z = 0.32 + t * 0.28
        box('stage_board', (x0, 1.55, z), (0.24, 2.6, 0.03), weathered, bevel=0.004)
        for y in (0.3, 2.8):
            box('stage_leg', (x0, y, z / 2), (0.04, 0.04, z), weathered, bevel=0.004)
    for k in range(10):     # pale lilies in pots along the staging
        t = k % 3; x0 = 0.18 + t * 0.26; z = 0.32 + t * 0.28
        y = 0.45 + (k // 3) * 0.7 + t * 0.2
        cyl('pot', (x0, y, z + 0.1), 0.08, 0.17, terracotta, verts=18, r2=0.06)
        cyl('pot_soil', (x0, y, z + 0.18), 0.075, 0.01, soil, verts=18)
        lily(Vector((x0, y, z + 0.18)), RG.uniform(0.32, 0.5), RG.choice([(0.97, 0.95, 0.92), (0.95, 0.9, 0.95), (0.9, 0.93, 0.98)]), RG.uniform(0.5, 1.0), 'rain_lily')
    # rain barrel fed from a downpipe through the glass, a dripping rose
    rb = Vector((0.45, 2.85, 0))
    cyl('barrel', rb + Vector((0, 0, 0.36)), 0.24, 0.72, oak, verts=28, bevel=0.01)
    for z in (0.12, 0.6):
        cyl('barrel_hoop', rb + Vector((0, 0, z)), 0.245, 0.04, iron_g, verts=28)
    cyl('barrel_water', rb + Vector((0, 0, 0.7)), 0.22, 0.01, solid('water_top', (0.1, 0.18, 0.2), 0.02), verts=28)
    limb(rb + Vector((0, 0.2, 2.2)), rb + Vector((0, 0.1, 0.75)), 0.03, iron_g)
    for k in range(5):
        sphere('drip', rb + Vector((0.0, 0.1, 0.72 + k * 0.05)), 0.008, glass, 8, (1, 1, 1.6))
    # watering cans, a puddle shining on the bricks
    for (p, a) in (((1.2, 0.55, 0), 0.4), ((0.9, 2.3, 0), 2.0)):
        p = Vector(p)
        cyl('can', p + Vector((0, 0, 0.13)), 0.1, 0.24, solid('can_zinc', (0.6, 0.63, 0.62), 0.35, metal=0.8), verts=20)
        limb(p + Vector((0.08 * math.cos(a), 0.08 * math.sin(a), 0.08)), p + Vector((0.3 * math.cos(a), 0.3 * math.sin(a), 0.3)), 0.014, solid('can_zinc', (0.6, 0.63, 0.62), 0.35, metal=0.8))
        cyl('can_rose', p + Vector((0.31 * math.cos(a), 0.31 * math.sin(a), 0.31)), 0.03, 0.02, brass, verts=12, rot=(0, 0.8, a))
    box('puddle', (1.15, 1.4, 0.002), (0.7, 0.45, 0.002), solid('puddle', (0.08, 0.1, 0.12), 0.02), bevel=0)
    hanging_board(Vector((0.9, 0.9, 1.95)), 'RAIN', varied('sign_wood', (0.3, 0.36, 0.4), 0.05, 0.7), (0.8, 0.9, 0.95))

# ---- the FIRE side: ash and ember, orange lilies grown for preparedness
with Group('fire'):
    # a raised bed of ash with charred stumps and orange fire lilies coming up
    bd = Vector((3.1, 2.3, 0))
    box('bed_edge', bd + Vector((0, 0, 0.15)), (1.4, 1.2, 0.3), solid('charred_wood', (0.08, 0.06, 0.05), 0.9), bevel=0.01)
    box('bed_ash', bd + Vector((0, 0, 0.29)), (1.34, 1.14, 0.02), ash_soil, bevel=0)
    for (dx, dy, h, r) in ((-0.4, 0.3, 0.35, 0.09), (0.35, -0.25, 0.25, 0.07), (0.45, 0.35, 0.18, 0.06)):
        cyl('stump', bd + Vector((dx, dy, 0.3 + h / 2)), r, h, solid('charred', (0.05, 0.045, 0.04), 0.95, coat=0.2), verts=10, r2=r * 0.8)
    for k in range(7):
        p = bd + Vector((RG.uniform(-0.55, 0.55), RG.uniform(-0.45, 0.45), 0.3))
        lily(p, RG.uniform(0.3, 0.55), RG.choice([(0.95, 0.35, 0.07), (0.92, 0.25, 0.08), (0.98, 0.5, 0.1)]), RG.uniform(0.6, 1.0), 'fire_lily')
    for k in range(18):      # embers in the ash
        sphere('ember', bd + Vector((RG.uniform(-0.6, 0.6), RG.uniform(-0.5, 0.5), 0.305)), RG.uniform(0.01, 0.02),
               solid('ember_glow', (1, 0.35, 0.05), 0.5, emit=(1.0, 0.3, 0.05), strength=RG.uniform(3, 8)), 8, (1, 1, 0.5))
    # a brazier keeping the frost off
    bz = Vector((3.5, 0.9, 0))
    for k in range(3):
        a = k / 3 * 2 * math.pi
        limb(bz + Vector((math.cos(a) * 0.18, math.sin(a) * 0.18, 0)), bz + Vector((math.cos(a) * 0.12, math.sin(a) * 0.12, 0.5)), 0.015, iron_g)
    cyl('brazier', bz + Vector((0, 0, 0.58)), 0.2, 0.16, solid('brazier_iron', (0.12, 0.1, 0.09), 0.6, metal=0.7), verts=20, r2=0.14)
    for k in range(9):
        sphere('coal', bz + Vector((RG.uniform(-0.1, 0.1), RG.uniform(-0.1, 0.1), 0.66)), 0.04,
               solid('coal_glow', (1, 0.4, 0.1), 0.6, emit=(1.0, 0.32, 0.06), strength=RG.uniform(4, 10)), 8)
    L = bpy.data.lights.new('brazier', 'POINT'); L.energy = 45; L.color = (1.0, 0.45, 0.15); L.shadow_soft_size = 0.15
    link(bpy.data.objects.new('brazier', L)).location = bz + Vector((0, 0, 0.8))
    # ready for the worst: sand buckets, a first-aid tin, a stack of sandbags
    for k in range(2):
        p = Vector((3.85, 1.45 + k * 0.28, 0))
        cyl('fire_bucket', p + Vector((0, 0, 0.13)), 0.11, 0.26, solid('fire_red', (0.72, 0.12, 0.08), 0.45), verts=18, r2=0.09)
        cyl('sand', p + Vector((0, 0, 0.25)), 0.1, 0.01, solid('sand', (0.76, 0.66, 0.45), 0.95), verts=18)
    for (dx, dz) in ((0.0, 0.1), (0.24, 0.1), (0.12, 0.27)):
        sphere('sandbag', Vector((3.2 + dx, 0.35, dz)), 0.13, varied('sandbag', (0.55, 0.48, 0.34), 0.06, 0.95, bump=0.4, bump_scale=120), 12, (1, 0.7, 0.55))
    box('aid_tin', (3.75, D - 0.1, 0.6), (0.18, 0.12, 0.12), solid('aid_red', (0.7, 0.12, 0.1), 0.5), bevel=0.01)
    box('aid_cross_h', (3.75, D - 0.161, 0.6), (0.08, 0.002, 0.024), cream, bevel=0)
    box('aid_cross_v', (3.75, D - 0.161, 0.6), (0.024, 0.002, 0.08), cream, bevel=0)
    # soot on the glass this side
    soot = solid('soot', (0.05, 0.04, 0.04), 0.9); soot.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.35
    box('soot_n', (3.1, D + 0.05, 1.3), (1.6, 0.004, 1.2), soot, bevel=0)
    hanging_board(Vector((3.1, 0.9, 1.95)), 'FIRE', varied('sign_char', (0.12, 0.08, 0.06), 0.05, 0.7), (1.0, 0.55, 0.25), emit=1.0)

# ---- the potting bench down the middle, four stations along it
bn = Vector((MID, 1.6, 0))
box('bench_top', bn + Vector((0, 0, 0.82)), (0.62, 2.7, 0.05), weathered, bevel=0.006)
box('bench_shelf', bn + Vector((0, 0, 0.25)), (0.56, 2.6, 0.03), weathered, bevel=0.004)
for dy in (-1.25, -0.42, 0.42, 1.25):
    for dx in (-0.27, 0.27):
        box('bench_leg', bn + Vector((dx, dy, 0.41)), (0.05, 0.05, 0.82), weathered, bevel=0.004)
for k in range(6):   # pots and sacks under the bench
    cyl('spare_pot', bn + Vector((RG.uniform(-0.15, 0.15), -1.1 + k * 0.42, 0.33)), 0.07, 0.13, terracotta, verts=16, r2=0.055)
TOP = 0.845


def stake(p, text, h=0.28):
    limb(p, p + Vector((0, 0, h)), 0.006, stake_m)
    box('stake_tag', p + Vector((0, 0, h)), (0.13, 0.008, 0.06), stake_m, bevel=0.003, rot=(0, 0, math.radians(45)))
    label(text, p + Vector((0.004, -0.004, h)), 0.028, ink, rot=(math.pi / 2, 0, math.radians(45)), name='stake_t')

with Group('find'):
    f = bn + Vector((0, -1.0, TOP))
    box('catalogue', f + Vector((-0.05, 0, 0.012)), (0.3, 0.22, 0.02), paper, bevel=0.002, rot=(0, 0, 0.2))
    for r_ in range(6):
        box('cat_line', f + Vector((-0.05, -0.07 + r_ * 0.028, 0.024)), (0.24, 0.004, 0.001), ink, bevel=0, rot=(0, 0, 0.2))
    label('open grants', f + Vector((-0.05, 0.08, 0.025)), 0.03, ink, rot=(0, 0, 0.2), name='cat_title')
    pk = [(0.85, 0.55, 0.3), (0.45, 0.6, 0.4), (0.8, 0.75, 0.4), (0.5, 0.55, 0.75), (0.8, 0.45, 0.5)]
    for k, c in enumerate(pk):
        box('seed_packet', f + Vector((0.17, -0.06 + k * 0.03, 0.02 + k * 0.004)), (0.1, 0.14, 0.004), solid('packet%d' % k, c, 0.8), bevel=0.001, rot=(0, 0, -0.5 + k * 0.25))
    stake(f + Vector((0.25, -0.15, 0)), 'FIND')

with Group('decide'):
    d = bn + Vector((0, -0.35, TOP))
    cyl('scale_base', d + Vector((0, 0, 0.015)), 0.08, 0.03, brass, verts=20)
    limb(d, d + Vector((0, 0, 0.3)), 0.01, brass)
    tilt = 0.12
    ends = [d + Vector((0, sg * 0.2 * math.cos(tilt), 0.3 - sg * 0.2 * math.sin(tilt))) for sg in (-1, 1)]
    limb(ends[0], ends[1], 0.006, brass)
    for e, s_ in zip(ends, (1.0, 1.3)):
        for sg in (-1, 1):
            limb(e, e + Vector((sg * 0.05, 0, -0.16)), 0.0015, brass)
        cyl('pan', e + Vector((0, 0, -0.16)), 0.07, 0.012, brass, verts=20, r2=0.055)
        sphere('bulb', e + Vector((0, 0, -0.12)), 0.035 * s_, solid('bulb_skin', (0.75, 0.6, 0.4), 0.7), 12, (1, 1, 0.85))
    stake(d + Vector((0.25, -0.1, 0)), 'DECIDE')

with Group('draft'):
    p = bn + Vector((0, 0.35, TOP))
    cyl('draft_pot', p + Vector((0, 0, 0.11)), 0.11, 0.2, glass, verts=28)
    cyl('draft_soil', p + Vector((0, 0, 0.19)), 0.1, 0.03, soil, verts=28)
    sphere('draft_bulb', p + Vector((0, 0, 0.22)), 0.045, solid('bulb_skin', (0.75, 0.6, 0.4), 0.7), 14, (1, 1, 0.85))
    for k in range(9):       # paperwork roots, curling down inside the glass
        a = k / 9 * 2 * math.pi
        prev = p + Vector((0, 0, 0.19))
        for j in range(4):
            t = (j + 1) / 4
            q = p + Vector((math.cos(a + t) * (0.02 + 0.07 * t), math.sin(a + t) * (0.02 + 0.07 * t), 0.19 - 0.16 * t))
            box('doc_root', (prev + q) / 2, (0.014, 0.003, (q - prev).length + 0.006), paper, bevel=0).rotation_euler = (q - prev).to_track_quat('Z', 'Y').to_euler()
            prev = q
    limb(p + Vector((0.15, -0.1, 0.01)), p + Vector((0.3, -0.05, 0.03)), 0.01, oak)
    box('trowel', p + Vector((0.12, -0.12, 0.01)), (0.1, 0.05, 0.005), solid('steel', (0.6, 0.6, 0.6), 0.3, metal=1.0), bevel=0.002, rot=(0, 0, 0.3))
    box('paper_pile', p + Vector((-0.12, 0.12, 0.02)), (0.14, 0.18, 0.03), paper, bevel=0.002, rot=(0, 0, 0.4))
    stake(p + Vector((0.25, -0.15, 0)), 'DRAFT')

with Group('review'):
    r = bn + Vector((0, 1.0, TOP))
    cyl('stand', r + Vector((0, 0, 0.05)), 0.07, 0.1, oak, verts=16)
    cyl('vase', r + Vector((0, 0, 0.18)), 0.05, 0.16, glass, verts=20, r2=0.035)
    top = lily(r + Vector((0, 0, 0.18)), 0.32, (0.96, 0.92, 0.9), 1.0, 'review_lily', scale=1.4)
    sphere('magnifier', r + Vector((0.16, -0.12, 0.25)), 0.06, glass, 16, (1, 0.15, 1))
    limb(r + Vector((0.16, -0.12, 0.19)), r + Vector((0.2, -0.16, 0.02)), 0.008, oak)
    limb(top + Vector((0, 0, -0.1)), top + Vector((-0.08, 0.1, -0.18)), 0.001, ink)
    box('tag', top + Vector((-0.09, 0.11, -0.22)), (0.07, 0.004, 0.05), paper, bevel=0)
    label('ready?', top + Vector((-0.09, 0.106, -0.22)), 0.014, red, name='tag_t')
    stake(r + Vector((0.25, -0.15, 0)), 'REVIEW')

# ---- the honest status: a seedling on its own stake at the front
with Group('status'):
    sp = Vector((2.7, 0.35, 0))
    cyl('seedling_pot', sp + Vector((0, 0, 0.08)), 0.07, 0.15, terracotta, verts=16, r2=0.055)
    cyl('seedling_soil', sp + Vector((0, 0, 0.155)), 0.065, 0.01, soil, verts=16)
    limb(sp + Vector((0, 0, 0.16)), sp + Vector((0, 0, 0.24)), 0.004, LEAF_M())
    for sg in (-1, 1):
        sphere('cotyledon', sp + Vector((sg * 0.025, 0, 0.245)), 0.022, LEAF_M(), 10, (1.3, 0.6, 0.15)).rotation_euler = (0, sg * 0.3, 0)
    limb(sp + Vector((0.06, 0, 0.0)), sp + Vector((0.06, 0, 0.45)), 0.006, stake_m)
    box('status_tag', sp + Vector((0.06, 0, 0.48)), (0.2, 0.01, 0.16), stake_m, bevel=0.003, rot=(0, 0, math.radians(45)))
    for k, line in enumerate(('SEEDLING', 'no users yet', 'first: 8-10 interviews')):
        label(line, sp + Vector((0.066, -0.006, 0.53 - k * 0.045)), 0.03 if k else 0.034, red if k == 0 else ink, rot=(math.pi / 2, 0, math.radians(45)), name='status_t')

# ---- the gardener, tending whichever side you're reading about
with Group('gardener'):
    g = Vector((1.35, 1.05, 0)) if SIDE == 'rain' else Vector((2.75, 1.25, 0))
    face = math.radians(-60) if SIDE == 'rain' else math.radians(30)
    Rg = Matrix.Rotation(face, 3, 'Z')
    P = lambda x, y, z: g + Rg @ Vector((x, y, z))
    skin = solid('skin', (0.72, 0.52, 0.4), 0.6)
    denim = varied('dungarees', (0.22, 0.3, 0.42), 0.05, 0.85, bump=0.3, bump_scale=300)
    knit = varied('jumper', (0.75, 0.62, 0.42), 0.05, 0.95, bump=0.5, bump_scale=250)
    boots = solid('boots', (0.12, 0.2, 0.14), 0.4, coat=0.5)
    hair = solid('hair', (0.12, 0.08, 0.06), 0.7)
    straw = varied('straw', (0.8, 0.68, 0.42), 0.06, 0.9, bump=0.4, bump_scale=200)
    for sg in (-1, 1):
        cyl('boot', P(sg * 0.07, 0.02, 0.09), 0.055, 0.18, boots, verts=14)
        sphere('boot_toe', P(sg * 0.07, -0.05, 0.03), 0.055, boots, 12, (1, 1.4, 0.6))
        cyl('leg', P(sg * 0.07, 0.0, 0.45), 0.06, 0.55, denim, verts=14)
    sphere('hips', P(0, 0, 0.72), 0.13, denim, 18, (1.1, 0.8, 0.8))
    cyl('torso', P(0, 0, 0.95), 0.13, 0.42, knit, verts=18, r2=0.115)
    box('bib', P(0, -0.11, 0.9), (0.18, 0.02, 0.22), denim, bevel=0.01, rot=Rg.to_euler())
    for sg in (-1, 1):
        limb(P(sg * 0.13, 0, 1.12), P(sg * 0.2, -0.12, 0.88), 0.042, knit)
        limb(P(sg * 0.2, -0.12, 0.88), P(sg * 0.14, -0.26, 0.86), 0.036, knit)
        sphere('hand', P(sg * 0.13, -0.29, 0.86), 0.035, skin, 10)
    sphere('neck', P(0, 0, 1.18), 0.045, skin, 10)
    hd = P(0, -0.01, 1.3)
    sphere('head', hd, 0.105, skin, 20, (0.95, 1, 1.05))
    sphere('hair_back', hd + Rg @ Vector((0, 0.03, 0.02)), 0.108, hair, 18, (1, 0.95, 1.02))
    sphere('hair_bun', hd + Rg @ Vector((0, 0.1, 0.06)), 0.05, hair, 12)
    cyl('hat_brim', hd + Vector((0, 0, 0.08)), 0.2, 0.012, straw, verts=28)
    cyl('hat_crown', hd + Vector((0, 0, 0.13)), 0.1, 0.1, straw, verts=24, r2=0.09)
    cyl('hat_band', hd + Vector((0, 0, 0.1)), 0.102, 0.025, solid('hat_band', (0.55, 0.15, 0.12), 0.6), verts=24)
    if SIDE == 'rain':      # a watering can, mid-pour
        c = P(0.0, -0.34, 0.8)
        cyl('g_can', c, 0.09, 0.2, solid('can_zinc', (0.6, 0.63, 0.62), 0.35, metal=0.8), verts=18, rot=(0.6, 0, face))
        limb(c, c + Rg @ Vector((-0.28, -0.05, -0.1)), 0.012, solid('can_zinc', (0.6, 0.63, 0.62), 0.35, metal=0.8))
    else:                   # a bucket of sand
        c = P(0.15, -0.3, 0.6)
        cyl('g_bucket', c, 0.1, 0.2, solid('fire_red', (0.72, 0.12, 0.08), 0.45), verts=18, r2=0.08)
        cyl('g_sand', c + Vector((0, 0, 0.09)), 0.095, 0.01, solid('sand', (0.76, 0.66, 0.45), 0.95), verts=18)

# ---- light, camera
room_light((1.0, 1.4, 2.1), 70, (0.75, 0.85, 1.0), 0.8)          # cool over the rain side
room_light((3.0, 1.6, 2.1), 70, (1.0, 0.7, 0.45), 0.8)           # warm over the fire side
room_light((2.0, 0.6, 2.0), 45, (1.0, 0.85, 0.65), 0.6)
for x in (1.4, 2.6):        # lanterns hung from the ridge beam over the bench
    limb(Vector((x, D / 2, H + 0.4)), Vector((x, D / 2, 1.95)), 0.004, iron_g)
    cyl('lantern', (x, D / 2, 1.88), 0.06, 0.14, glass, verts=12)
    cyl('lantern_top', (x, D / 2, 1.97), 0.07, 0.04, iron_g, verts=12, r2=0.03)
    sphere('lantern_flame', (x, D / 2, 1.86), 0.015, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1, 0.65, 0.3), strength=40), 8, (1, 1, 1.8))
    L = bpy.data.lights.new('candle', 'POINT'); L.energy = 14; L.color = (1, 0.68, 0.35); L.shadow_soft_size = 0.03
    link(bpy.data.objects.new('candle', L)).location = (x, D / 2, 1.87)
lighting(sc, sun_rot=(math.radians(60), 0, math.radians(-40)), sun_energy=0.0, sun_color=(1, 1, 1),
         bg_top=(0.05, 0.05, 0.07), bg_bottom=(0.06, 0.05, 0.06), hdri_strength=0.05)
cam = iso_camera(sc, (2.0, 1.5, 1.05), 5.4, res=(int(os.environ.get('RES_X', 1400)), int(os.environ.get('RES_Y', 1050))))
if not os.environ.get('NO_RENDER'):
    render(sc, OUT, SAMPLES)
if os.environ.get('WEB_OUT'):
    export_web(sc, cam, os.environ['WEB_OUT'])
