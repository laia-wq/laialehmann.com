"""Room: Squirrels and Seeds — a seed depot run by squirrels, doing inventory.

Everything is squirrel-sized: the counter comes up to a squirrel's chest,
the seed cabinet needs a rolling ladder. Six squirrels at work:
  - on the ladder, putting a jar back in its cubby          (stock on the shelf)
  - at the counter, typing on the laptop with the stock page (the tool)
  - by the scale with a clipboard, checking a delivery in    (what comes in)
  - hauling a sack of seed in through the door               (donations arriving)
  - tying up parcels on the OUT bench                        (what goes out)
  - asleep in a basket on top of the cabinet                 (it's late)
Around them: an apothecary cabinet of labelled seed drawers (some open, full
of seed), jars with real shoulders and corks, sacks spilling sunflower seeds
and acorns, a brass scale, crates chalked IN, parcels tied with twine, a
chalkboard with the real numbers, seven thank-you notes, seedlings sprouting
in eggshells on the round window's sill, and warm lamps against a cold night.

Hotspots: counter, cabinet, arrivals, parcels, board, notes.
Usage: blender python room_shop2.py <out.png> [samples]
Env:   WEB_OUT, RES_X/RES_Y, MARKER_FONT, HAND_FONT, NO_RENDER, SPP_DENOISE
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from room_kit import *
from canal_extras import limb
from mathutils import Matrix, Vector
import bmesh
import squirrel as SQ

OUT = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-2].endswith('.png') else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 96
HAND = os.environ.get('HAND_FONT', '')
RG = random.Random(21)
sc = reset()
FACE_CAM = math.radians(-135)          # a squirrel with this yaw looks at the camera

W, D, H = 3.0, 2.6, 2.0


# ------------------------------------------------------------------ helpers
def lathe(name, prof, loc, mat, segs=36, rot=(0, 0, 0)):
    """Spin a profile [(r, z), ...] (bottom to top) round z."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings = []
    for (r, z) in prof:
        ring = []
        for k in range(segs):
            a = k / segs * 2 * math.pi
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(segs):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]))
    if prof[0][0] > 0: bm.faces.new(list(reversed(rings[0])))
    if prof[-1][0] > 0: bm.faces.new(rings[-1])
    bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    return o


def hand(text, loc, size, mat, rot=(math.pi / 2, 0, 0), align='CENTER', name='hand'):
    return label(text, loc, size, mat, rot, align, font=HAND or None, extrude=0.0004, name=name)


def seed_mat(name, base, alt, scale=160.0):
    """A heap of small seeds: voronoi cells, each its own shade, bumpy."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = scale
    l.new(tc.outputs['Object'], vo.inputs['Vector'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*base, 1); mix.inputs['B'].default_value = (*alt, 1)
    sep = n.new('ShaderNodeSeparateColor'); l.new(vo.outputs['Color'], sep.inputs['Color'])
    l.new(sep.outputs['Red'], mix.inputs['Factor'])
    dark = n.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
    edge = n.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = 0.0; edge.inputs['From Max'].default_value = 0.5
    edge.inputs['To Min'].default_value = 0.0; edge.inputs['To Max'].default_value = 1.0
    l.new(vo.outputs['Distance'], edge.inputs['Value'])
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; l.new(edge.outputs['Result'], inv.inputs[1])
    l.new(inv.outputs['Value'], dark.inputs['Factor']); l.new(mix.outputs['Result'], dark.inputs['A'])
    dark.inputs['B'].default_value = (0.45, 0.4, 0.35, 1)
    l.new(dark.outputs['Result'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.8; bp.inputs['Distance'].default_value = 0.004
    l.new(vo.outputs['Distance'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.6
    return m


SEEDS = {
    'sunflower': ((0.12, 0.11, 0.1), (0.72, 0.7, 0.62)),
    'acorn':     ((0.45, 0.28, 0.12), (0.58, 0.4, 0.18)),
    'hazel':     ((0.5, 0.33, 0.18), (0.62, 0.45, 0.26)),
    'pumpkin':   ((0.72, 0.66, 0.42), (0.6, 0.62, 0.38)),
    'pine':      ((0.35, 0.22, 0.12), (0.62, 0.5, 0.35)),
    'beech':     ((0.42, 0.3, 0.2), (0.52, 0.4, 0.26)),
    'maple':     ((0.62, 0.42, 0.25), (0.7, 0.55, 0.32)),
    'chestnut':  ((0.32, 0.16, 0.08), (0.45, 0.24, 0.12)),
    'walnut':    ((0.52, 0.4, 0.25), (0.62, 0.5, 0.33)),
    'poppy':     ((0.15, 0.17, 0.22), (0.3, 0.32, 0.38)),
    'millet':    ((0.85, 0.72, 0.35), (0.92, 0.82, 0.5)),
    'oat':       ((0.78, 0.68, 0.45), (0.85, 0.76, 0.55)),
}
SEED_NAMES = list(SEEDS)


def seeds(kind):
    a, b_ = SEEDS[kind]
    return seed_mat('seed_' + kind, a, b_, 160 if kind not in ('acorn', 'chestnut', 'walnut', 'hazel') else 70)


# ------------------------------------------------------------------ materials
plaster = stucco('sq_plaster', (0.66, 0.52, 0.38), dirt=(0.45, 0.34, 0.25))
planks = wood('sq_floor', (0.34, 0.21, 0.12), scale=4.0, rough=0.55)
oak = wood('oak', (0.45, 0.28, 0.15), scale=12.0, rough=0.45)
walnut_w = wood('walnut', (0.25, 0.15, 0.09), scale=12.0, rough=0.4)
green_paint = varied('green_paint', (0.2, 0.3, 0.24), 0.04, 0.55, bump=0.15, bump_scale=80)
brass = solid('brass', (0.8, 0.6, 0.3), 0.28, metal=1.0)
iron_m = solid('iron', (0.07, 0.07, 0.07), 0.5, metal=0.7)
glass = solid('jar_glass', (0.95, 0.98, 0.97), 0.02)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1.0
glass.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.45
cork = varied('cork', (0.62, 0.45, 0.28), 0.06, 0.95, bump=0.6, bump_scale=400)
paper = solid('paper', (0.93, 0.89, 0.78), 0.9)
kraft = varied('kraft', (0.66, 0.5, 0.33), 0.05, 0.9, bump=0.2, bump_scale=300)
twine = solid('twine', (0.72, 0.6, 0.4), 0.9)
ink = solid('ink', (0.1, 0.08, 0.07), 0.8)
chalk = solid('chalk', (0.92, 0.92, 0.88), 0.95, emit=(0.92, 0.92, 0.88), strength=0.12)
cream = solid('paint_cream', (0.93, 0.87, 0.73), 0.7)
burlap = varied('burlap', (0.58, 0.46, 0.3), 0.06, 0.95, bump=0.7, bump_scale=260)

# ------------------------------------------------------------------ the room
box('floor', (W / 2, D / 2, -0.04), (W, D, 0.08), planks, bevel=0)
box('wall_w', (-0.06, D / 2, H / 2), (0.12, D + 0.12, H), plaster, bevel=0)
box('wall_n', (W / 2, D + 0.06, H / 2), (W + 0.12, 0.12, H), plaster, bevel=0)
for (loc, size) in (((0.01, D / 2, 0.3), (0.02, D, 0.6)), ((W / 2, D - 0.01, 0.3), (W, 0.02, 0.6))):
    box('wainscot', loc, size, green_paint, bevel=0)
for (loc, size) in (((0.02, D / 2, 0.61), (0.04, D, 0.035)), ((W / 2, D - 0.02, 0.61), (W, 0.04, 0.035))):
    box('dado', loc, size, walnut_w, bevel=0.006)
for (loc, size) in (((0.015, D / 2, 0.035), (0.03, D, 0.07)), ((W / 2, D - 0.015, 0.035), (W, 0.03, 0.07))):
    box('skirting', loc, size, walnut_w, bevel=0.004)
# exposed timber posts at the corner and along the walls
for p in ((0.03, D - 0.03), (0.03, 0.9), (1.9, D - 0.03)):
    box('post', (p[0], p[1], H / 2), (0.07, 0.07, H), walnut_w, bevel=0.008)
box('top_beam_w', (0.03, D / 2, H - 0.04), (0.08, D, 0.08), walnut_w, bevel=0.008)
box('top_beam_n', (W / 2, D - 0.03, H - 0.04), (W, 0.08, 0.08), walnut_w, bevel=0.008)
edge = solid('cut_edge', (0.09, 0.07, 0.06), 0.9)
for (loc, size) in (((-0.06, -0.005, H / 2), (0.125, 0.012, H)), ((W + 0.005, D + 0.06, H / 2), (0.012, 0.125, H)),
                    ((W / 2, -0.005, -0.04), (W, 0.012, 0.085)), ((W + 0.005, D / 2, -0.04), (0.012, D, 0.085))):
    box('cut', loc, size, edge, bevel=0)
# rug
box('rug', (1.55, 1.05, 0.004), (1.5, 1.0, 0.008), varied('rug', (0.45, 0.14, 0.1), 0.04, 0.95, bump=0.4, bump_scale=200), bevel=0)
box('rug_border', (1.55, 1.05, 0.003), (1.6, 1.1, 0.006), solid('rug_edge', (0.75, 0.6, 0.32), 0.95), bevel=0)
for k in range(14):
    for sg in (-1, 1):
        limb(Vector((0.8 + k * 0.11, 1.05 + sg * 0.55, 0.004)), Vector((0.8 + k * 0.11, 1.05 + sg * 0.6, 0.002)), 0.003, cream)

# ------------------------------------------------------------------ round window, night outside, seedlings on the sill
wc = Vector((-0.06, 1.55, 1.15)); wr = 0.34
cut(bpy.data.objects['wall_w'], cyl('win_cut', wc, wr, 0.4, None, verts=48, rot=(0, math.pi / 2, 0)))
night = solid('night', (0.04, 0.06, 0.12), 0.5, emit=(0.04, 0.07, 0.15), strength=1.0)
box('night', (-0.13, 1.55, 1.15), (0.01, 0.8, 0.8), night, bevel=0)
sphere('moon', (-0.125, 1.72, 1.3), 0.06, solid('moon', (1, 0.96, 0.85), 0.5, emit=(1, 0.95, 0.82), strength=6), 16, (0.15, 1, 1))
for k in range(4):     # the canal's lamps far off
    sphere('far_lamp', (-0.125, 1.33 + k * 0.1, 0.95 + (k % 2) * 0.05), 0.012, solid('far_glow', (1, 0.7, 0.4), 0.5, emit=(1, 0.62, 0.3), strength=8), 8, (0.15, 1, 1.4))
ring = cyl('win_ring', wc + Vector((0.06, 0, 0)), wr + 0.05, 0.06, walnut_w, verts=48, rot=(0, math.pi / 2, 0))
cut(ring, cyl('win_ring_in', wc, wr, 0.3, None, verts=48, rot=(0, math.pi / 2, 0)))
for a in (0, math.pi / 2):
    box('win_bar', wc + Vector((0.05, 0, 0)), (0.02, 2 * wr, 0.025), walnut_w, bevel=0).rotation_euler = (a, 0, 0)
box('win_sill', wc + Vector((0.1, 0, -wr - 0.02)), (0.2, 0.62, 0.035), oak, bevel=0.006)
for k in range(5):   # seedlings in eggshells: seeds becoming plants
    p = wc + Vector((0.11, -0.22 + k * 0.11, -wr + 0.0))
    shell = lathe('eggshell', [(0.0, 0.0), (0.02, 0.004), (0.03, 0.02), (0.032, 0.04), (0.03, 0.05)], p, solid('eggshell', (0.95, 0.9, 0.82), 0.6), 24)
    cyl('egg_soil', p + Vector((0, 0, 0.045)), 0.027, 0.006, solid('soil', (0.16, 0.1, 0.07), 0.95), verts=16)
    h = 0.03 + 0.02 * (k % 3)
    limb(p + Vector((0, 0, 0.045)), p + Vector((0, 0, 0.045 + h)), 0.002, solid('sprout', (0.45, 0.65, 0.25), 0.5))
    for sg in (-1, 1):
        sphere('sprout_leaf', p + Vector((sg * 0.009, 0, 0.045 + h)), 0.01, solid('sprout_leaf', (0.4, 0.62, 0.2), 0.5), 8, (1.4, 0.7, 0.2))
    hand(['sunflower', 'pumpkin', 'oak', 'maple', 'poppy'][k], p + Vector((0.034, 0, 0.022)), 0.008, ink, rot=(math.pi / 2, 0, math.pi / 2), name='egg_label')

# ------------------------------------------------------------------ the seed cabinet, ladder, sleeper on top
with Group('cabinet'):
    cx0, cx1, cz1 = 0.2, 1.72, 1.55
    cw = cx1 - cx0; cy = D - 0.17
    box('cab_body', ((cx0 + cx1) / 2, cy, 1.15 / 2), (cw, 0.3, 1.15), walnut_w, bevel=0.01)
    for sx in (cx0 - 0.01, cx1 + 0.01):
        box('cab_side', (sx, cy - 0.005, cz1 / 2 + 0.01), (0.035, 0.32, cz1 + 0.02), walnut_w, bevel=0.005)
    box('cab_top', ((cx0 + cx1) / 2, cy - 0.01, cz1 + 0.02), (cw + 0.06, 0.34, 0.04), oak, bevel=0.008)
    box('cab_plinth', ((cx0 + cx1) / 2, cy - 0.01, 0.05), (cw + 0.04, 0.33, 0.1), oak, bevel=0.006)
    cols, rows = 9, 6
    dw = (cw - 0.06) / cols; dh = (1.13 - 0.12) / rows
    fy = cy - 0.151
    open_drawers = {(1, 2), (4, 1), (6, 3), (2, 4)}
    for r_ in range(rows):
        for c_ in range(cols):
            x = cx0 + 0.03 + dw * (c_ + 0.5); z = 0.12 + dh * (r_ + 0.5)
            kind = SEED_NAMES[(r_ * cols + c_ * 5) % len(SEED_NAMES)]
            pull = 0.0
            if (c_, r_) in open_drawers:
                pull = 0.14
                # the drawer box, pulled out, heaped with seed
                box('drawer_box', (x, fy - pull / 2 + 0.01, z - 0.005), (dw - 0.02, pull + 0.05, dh - 0.03), oak, bevel=0.003)
                heap = sphere('seed_heap', (x, fy - pull / 2 + 0.01, z + 0.01), 0.06, seeds(kind), 16, ((dw - 0.03) / 0.12, (pull + 0.03) / 0.12, 0.35))
            box('drawer', (x, fy - pull, z), (dw - 0.012, 0.012, dh - 0.012), oak, bevel=0.004)
            box('label_frame', (x, fy - pull - 0.008, z + dh * 0.18), (dw * 0.55, 0.004, dh * 0.28), brass, bevel=0.002)
            box('label_card', (x, fy - pull - 0.0105, z + dh * 0.18), (dw * 0.48, 0.002, dh * 0.22), paper, bevel=0)
            hand(kind, (x, fy - pull - 0.0118, z + dh * 0.18), dh * 0.17, ink, name='drawer_t')
            cyl('drawer_knob', (x, fy - pull - 0.012, z - dh * 0.18), 0.011, 0.02, brass, verts=12, rot=(math.pi / 2, 0, 0))
    # top row: open cubbies with jars
    box('cubby_back', ((cx0 + cx1) / 2, cy + 0.12, 1.34), (cw - 0.04, 0.02, 0.38), oak, bevel=0)
    box('cubby_floor', ((cx0 + cx1) / 2, cy - 0.02, 1.155), (cw - 0.02, 0.28, 0.025), oak, bevel=0.003)
    for k in range(7):
        x = cx0 + 0.075 + k * (cw - 0.15) / 6
        box('cubby_div', (x, cy - 0.03, 1.34), (0.02, 0.26, 0.37), walnut_w, bevel=0.002)
    for k in range(6):
        x = cx0 + 0.075 + (k + 0.5) * (cw - 0.15) / 6
        if k == 4: continue   # the empty cubby the ladder squirrel is about to fill
        kind = SEED_NAMES[(k * 3) % len(SEED_NAMES)]
        h = 0.2
        lathe('jar', [(0.0, 0.0), (0.055, 0.0), (0.062, 0.01), (0.062, h * 0.78), (0.05, h * 0.9), (0.034, h * 0.95), (0.034, h)], (x, cy - 0.03, 1.17), glass, 32)
        lathe('jar_fill', [(0.0, 0.003), (0.056, 0.003), (0.056, h * 0.6), (0.03, h * 0.66), (0.0, h * 0.67)], (x, cy - 0.03, 1.17), seeds(kind), 28)
        lathe('jar_cork', [(0.0, 0.0), (0.03, 0.0), (0.033, 0.035), (0.0, 0.035)], (x, cy - 0.03, 1.17 + h - 0.012), cork, 20)
        box('jar_label', (x, cy - 0.094, 1.17 + h * 0.42), (0.07, 0.002, 0.045), paper, bevel=0)
        hand(kind, (x, cy - 0.096, 1.17 + h * 0.42), 0.022, ink, name='jar_t')
    # rolling library ladder on a brass rail
    box('ladder_rail', ((cx0 + cx1) / 2, cy - 0.2, 1.45), (cw, 0.02, 0.02), brass, bevel=0)
    lx = cx0 + 0.075 + 4.5 * (cw - 0.15) / 6
    for sg in (-1, 1):
        limb(Vector((lx + sg * 0.12, cy - 0.55, 0.0)), Vector((lx + sg * 0.12, cy - 0.21, 1.45)), 0.018, oak)
        cyl('ladder_wheel', (lx + sg * 0.12, cy - 0.55, 0.025), 0.025, 0.015, brass, verts=16, rot=(0, math.pi / 2, 0))
        cyl('ladder_hook', (lx + sg * 0.12, cy - 0.2, 1.47), 0.02, 0.04, brass, verts=12, rot=(0, math.pi / 2, 0))
    for k in range(7):
        t = (k + 0.6) / 7.4
        y = cy - 0.55 + 0.34 * t; z = 1.45 * t
        box('rung', (lx, y, z), (0.24, 0.05, 0.018), oak, bevel=0.003)
    # the ladder squirrel, putting a jar into its cubby
    t = 4.6 / 7.4
    objs, f = SQ.squirrel((lx, cy - 0.55 + 0.34 * t + 0.005, 1.45 * t + 0.01), 0.0, 'reach')
    hj = (f((-0.035, 0.07, 0.47)) + f((0.035, 0.07, 0.47))) / 2
    jx = Vector((hj.x, hj.y + 0.02, hj.z - 0.06))
    lathe('jar_held', [(0.0, 0.0), (0.05, 0.0), (0.056, 0.01), (0.056, 0.15), (0.03, 0.18), (0.03, 0.19)], jx, glass, 28)
    lathe('jar_held_fill', [(0.0, 0.003), (0.05, 0.003), (0.05, 0.11), (0.0, 0.12)], jx, seeds('acorn'), 24)
    lathe('jar_held_cork', [(0.0, 0.0), (0.028, 0.0), (0.03, 0.03), (0.0, 0.03)], jx + Vector((0, 0, 0.18)), cork, 18)
    # asleep in a basket on top of the cabinet
    bk = Vector((0.55, cy - 0.02, cz1 + 0.04))
    lathe('basket', [(0.0, 0.0), (0.15, 0.0), (0.18, 0.06), (0.19, 0.1), (0.175, 0.1), (0.16, 0.06), (0.13, 0.015), (0.0, 0.015)], bk,
          varied('wicker', (0.55, 0.4, 0.22), 0.06, 0.9, bump=0.8, bump_scale=300), 40)
    sphere('blanket', bk + Vector((0, 0, 0.03)), 0.15, varied('blanket', (0.55, 0.62, 0.7), 0.05, 0.95, bump=0.4, bump_scale=200), 20, (1, 1, 0.3))
    SQ.squirrel(bk + Vector((-0.02, 0.0, 0.03)), math.radians(-120), 'sleep', 0.95)
    for k in range(3):    # three little Zs drifting up
        hand('z', bk + Vector((0.12 + k * 0.05, -0.1, 0.25 + k * 0.07)), 0.03 + 0.012 * k, cream, rot=(math.pi / 2, 0, math.radians(45)), name='zzz')

# ------------------------------------------------------------------ the counter, the laptop, the typing squirrel
with Group('counter'):
    ct = Vector((1.75, 1.2, 0))
    box('counter', ct + Vector((0, 0, 0.2)), (0.95, 0.38, 0.4), green_paint, bevel=0.012)
    box('counter_top', ct + Vector((0, 0, 0.415)), (1.02, 0.44, 0.035), oak, bevel=0.008)
    for k in range(3):
        box('counter_panel', ct + Vector((-0.31 + k * 0.31, -0.192, 0.2)), (0.25, 0.006, 0.28), green_paint, bevel=0.006)
        box('panel_mould', ct + Vector((-0.31 + k * 0.31, -0.196, 0.2)), (0.21, 0.004, 0.24), walnut_w, bevel=0.003)
    TOPZ = 0.433
    # laptop: screen turned towards the room, the typist on its left side
    lp = ct + Vector((0.05, 0.02, TOPZ)); Rl = Matrix.Rotation(math.radians(70), 3, 'Z')
    alu = solid('alu', (0.62, 0.62, 0.64), 0.28, metal=0.9)
    box('laptop_base', lp + Vector((0, 0, 0.006)), (0.24, 0.17, 0.012), alu, bevel=0.003, rot=Rl.to_euler())
    box('laptop_keys', lp + Rl @ Vector((0, -0.015, 0.0125)), (0.21, 0.08, 0.002), solid('keys', (0.1, 0.1, 0.11), 0.5), bevel=0, rot=Rl.to_euler())
    def ui(px, w, h):
        rect(px, w, h, 0, 0, w, h, (0.94, 0.91, 0.84))
        rect(px, w, h, 0, h - 10, w, h, (0.27, 0.4, 0.27))
        rect(px, w, h, 4, h - 7, 40, h - 3, (0.96, 0.92, 0.78))
        rect(px, w, h, 0, 0, 20, h - 10, (0.86, 0.81, 0.71))
        for k in range(6): rect(px, w, h, 4, h - 18 - k * 9, 16, h - 14 - k * 9, (0.56, 0.5, 0.42))
        lv = [0.92, 0.38, 0.72, 0.14, 0.55, 0.83, 0.3, 0.66]
        for k, v in enumerate(lv):
            y = h - 20 - k * 8
            rect(px, w, h, 25, y, 25 + 4, y + 4, (0.6, 0.4, 0.2))
            rect(px, w, h, 32, y, 70, y + 4, (0.58, 0.53, 0.45))
            col = (0.78, 0.33, 0.2) if v < 0.25 else (0.88, 0.66, 0.25) if v < 0.5 else (0.36, 0.56, 0.31)
            rect(px, w, h, 76, y, 76 + int(44 * v), y + 4, col)
    scr = screen_image('stock_page', 128, 84, ui)
    hinge = lp + Rl @ Vector((0, 0.085, 0.012))
    tilt = Rl @ Matrix.Rotation(math.radians(-14), 3, 'X')
    box('laptop_lid', hinge + tilt @ Vector((0, 0.005, 0.085)), (0.24, 0.01, 0.17), alu, bevel=0.003, rot=tilt.to_euler())
    plane_with('laptop_screen', hinge + tilt @ Vector((0, -0.0012, 0.085)), (0.225, 0.152), scr, (tilt @ Matrix.Rotation(math.radians(90), 3, 'X')).to_euler())
    sticker = hinge + tilt @ Vector((0.05, 0.0105, 0.11))
    lathe('acorn_sticker', [(0.0, 0.0), (0.012, 0.0), (0.012, 0.001), (0.0, 0.001)], sticker, solid('sticker', (0.85, 0.55, 0.2), 0.5), 16,
          rot=(tilt @ Matrix.Rotation(math.radians(-90), 3, 'X')).to_euler())
    # the typist, on a cotton-reel stool at the counter's end, paws on the keys
    keys = lp + Rl @ Vector((0, -0.02, 0.014))
    st = ct + Vector((-0.6, -0.02, 0))
    lathe('reel', [(0.0, 0.0), (0.11, 0.0), (0.11, 0.03), (0.07, 0.04), (0.07, 0.24), (0.11, 0.25), (0.11, 0.28), (0.0, 0.28)], st, oak, 32)
    lathe('reel_thread', [(0.072, 0.045), (0.09, 0.05), (0.09, 0.23), (0.072, 0.235)], st, solid('thread', (0.7, 0.2, 0.15), 0.8), 32)
    SQ.squirrel(st + Vector((0, 0.0, 0.28)), math.radians(-70), 'type', 1.05)
    # ledger, brass bell, a mug, the receipt spike
    lg = ct + Vector((-0.28, 0.05, TOPZ))
    box('ledger', lg + Vector((0, 0, 0.012)), (0.2, 0.14, 0.024), solid('ledger', (0.4, 0.1, 0.08), 0.6), bevel=0.004, rot=(0, 0, 0.3))
    box('ledger_pages', lg + Vector((0.004, 0, 0.012)), (0.19, 0.13, 0.02), paper, bevel=0.002, rot=(0, 0, 0.3))
    bl = ct + Vector((0.38, -0.08, TOPZ))
    lathe('bell', [(0.0, 0.0), (0.04, 0.0), (0.04, 0.006), (0.034, 0.01), (0.03, 0.03), (0.018, 0.045), (0.006, 0.05), (0.006, 0.062), (0.0, 0.065)], bl, brass, 28)
    lathe('mug', [(0.0, 0.0), (0.03, 0.0), (0.032, 0.06), (0.029, 0.06), (0.027, 0.005), (0.0, 0.005)], ct + Vector((0.4, 0.12, TOPZ)), solid('mug', (0.85, 0.82, 0.72), 0.3), 24)
    cyl('cocoa', ct + Vector((0.4, 0.12, TOPZ + 0.045)), 0.027, 0.004, solid('cocoa', (0.3, 0.15, 0.08), 0.15), verts=20)
    sp = ct + Vector((0.2, 0.15, TOPZ))
    cyl('spike_base', sp + Vector((0, 0, 0.008)), 0.03, 0.016, iron_m, verts=12)
    limb(sp, sp + Vector((0, 0, 0.12)), 0.002, iron_m)
    for k in range(7):
        box('receipt', sp + Vector((0, 0, 0.02 + k * 0.01)), (0.06, 0.08, 0.0015), paper, bevel=0, rot=(0, 0, k * 0.5))

# ------------------------------------------------------------------ arrivals: the door, a sack coming in, the scale, crates chalked IN
with Group('arrivals'):
    # a little arched door in the west wall, ajar onto the night
    dz = 0.0; dy = 0.45
    cut(bpy.data.objects['wall_w'], box('door_cut', (-0.06, dy, 0.3), (0.4, 0.42, 0.6), None, bevel=0))
    box('door_night', (-0.13, dy, 0.3), (0.01, 0.44, 0.62), night, bevel=0)
    dr = box('door', (0.05, dy - 0.19, 0.3), (0.03, 0.4, 0.58), green_paint, bevel=0.006)
    dr.rotation_euler = (0, 0, math.radians(-55)); dr.location = (0.13, dy - 0.33, 0.29)
    sphere('door_knob', (0.24, dy - 0.27, 0.28), 0.015, brass, 10)
    box('door_lintel', (0.0, dy, 0.62), (0.06, 0.5, 0.05), walnut_w, bevel=0.004)
    # the squirrel hauling a sack of sunflower seed in
    objs, f = SQ.squirrel((0.45, 0.5, 0), math.radians(-150), 'carry')
    sk = (f((-0.07, 0.1, 0.2)) + f((0.07, 0.1, 0.2))) / 2 + Vector((0, 0, -0.02))
    sphere('carried_sack', sk + Vector((0.02, -0.03, 0)), 0.11, burlap, 20, (0.9, 0.75, 1.1))
    lathe('sack_neck', [(0.03, 0.0), (0.045, 0.02), (0.05, 0.04), (0.03, 0.045)], sk + Vector((0.02, -0.03, 0.11)), burlap, 16)
    # crates chalked IN, stacked with donated goods
    for (p, rot, word) in (((0.32, 1.05, 0), 0.05, 'IN'), ((0.34, 1.02, 0.31), -0.06, '')):
        p = Vector(p)
        cr = box('crate', p + Vector((0, 0, 0.15)), (0.42, 0.3, 0.3), varied('crate', (0.55, 0.4, 0.24), 0.1, 0.8, bump=0.2, bump_scale=60), bevel=0.008, rot=(0, 0, rot))
        for k in range(3):
            box('crate_slat', p + Matrix.Rotation(rot, 3, 'Z') @ Vector((0, -0.152, 0.05 + k * 0.1)), (0.42, 0.008, 0.07), varied('crate', (0.55, 0.4, 0.24), 0.1, 0.8), bevel=0.002, rot=(0, 0, rot))
        if word:
            label(word, p + Matrix.Rotation(rot, 3, 'Z') @ Vector((0, -0.158, 0.16)), 0.11, chalk, rot=(math.pi / 2, 0, rot), name='crate_word')
    for k in range(6):   # acorns and pinecones heaped on top
        q = Vector((0.24 + (k % 3) * 0.08, 0.95 + (k // 3) * 0.1, 0.63))
        lathe('acorn_nut', [(0.0, 0.0), (0.012, 0.004), (0.02, 0.018), (0.02, 0.032), (0.0, 0.034)], q, solid('acorn_shell', (0.52, 0.32, 0.12), 0.35, coat=0.3), 16)
        lathe('acorn_cap', [(0.0, 0.03), (0.022, 0.03), (0.024, 0.038), (0.016, 0.046), (0.0, 0.048)], q, varied('acorn_cup', (0.38, 0.28, 0.16), 0.05, 0.95, bump=1.0, bump_scale=500), 16)
    # the brass scale, an acorn on it, the checker with a clipboard
    sc_ = Vector((0.95, 0.75, 0))
    lathe('scale_base', [(0.0, 0.0), (0.12, 0.0), (0.12, 0.02), (0.06, 0.04), (0.03, 0.06), (0.0, 0.06)], sc_, brass, 32)
    limb(sc_ + Vector((0, 0, 0.05)), sc_ + Vector((0, 0, 0.32)), 0.012, brass)
    dial = sc_ + Vector((0, -0.03, 0.36))
    cyl('scale_dial', dial, 0.07, 0.03, brass, verts=32, rot=(math.pi / 2, 0, 0))
    cyl('scale_face', dial + Vector((0, -0.016, 0)), 0.06, 0.004, cream, verts=32, rot=(math.pi / 2, 0, 0))
    for k in range(12):
        a = k / 12 * 2 * math.pi
        limb(dial + Vector((math.cos(a) * 0.05, -0.019, math.sin(a) * 0.05)), dial + Vector((math.cos(a) * 0.056, -0.019, math.sin(a) * 0.056)), 0.0015, ink)
    limb(dial + Vector((0, -0.02, 0)), dial + Vector((0.03, -0.02, 0.04)), 0.002, solid('needle', (0.7, 0.1, 0.08), 0.4))
    lathe('scale_pan', [(0.0, 0.0), (0.1, 0.0), (0.12, 0.025), (0.115, 0.027), (0.095, 0.005), (0.0, 0.005)], sc_ + Vector((0, 0, 0.32)), brass, 32)
    q = sc_ + Vector((0, 0, 0.33))
    lathe('weighed_acorn', [(0.0, 0.0), (0.02, 0.006), (0.034, 0.03), (0.034, 0.055), (0.0, 0.058)], q, solid('acorn_shell', (0.52, 0.32, 0.12), 0.35, coat=0.3), 20)
    lathe('weighed_cap', [(0.0, 0.05), (0.037, 0.05), (0.04, 0.064), (0.026, 0.078), (0.0, 0.08)], q, varied('acorn_cup', (0.38, 0.28, 0.16), 0.05, 0.95, bump=1.0, bump_scale=500), 20)
    limb(q + Vector((0, 0, 0.078)), q + Vector((0.005, 0, 0.095)), 0.003, solid('acorn_stem', (0.3, 0.2, 0.1), 0.8))
    objs, f = SQ.squirrel((1.12, 0.55, 0), math.radians(-150), 'check')
    cbp = f((-0.04, 0.085, 0.22))
    box('clipboard', cbp, (0.09, 0.012, 0.12), walnut_w, bevel=0.002, rot=(0.35, 0, math.radians(-150)))
    box('clip_paper', cbp + Matrix.Rotation(math.radians(-150), 3, 'Z') @ Vector((0, -0.007, -0.006)), (0.08, 0.002, 0.1), paper, bevel=0, rot=(0.35, 0, math.radians(-150)))
    limb(f((0.035, 0.08, 0.25)), f((0.03, 0.1, 0.3)), 0.004, solid('pencil', (0.88, 0.68, 0.12), 0.5))
    # sacks along the wall, open and spilling
    for k, (p, kind, s_) in enumerate((((0.2, 1.45, 0), 'sunflower', 1.0), ((0.22, 1.75, 0), 'millet', 0.85), ((0.47, 1.6, 0), 'acorn', 0.9))):
        p = Vector(p)
        lathe('sack', [(0.0, 0.0), (0.13 * s_, 0.0), (0.16 * s_, 0.06 * s_), (0.165 * s_, 0.2 * s_), (0.14 * s_, 0.28 * s_), (0.15 * s_, 0.31 * s_), (0.13 * s_, 0.32 * s_)], p, burlap, 28)
        sphere('sack_heap', p + Vector((0, 0, 0.3 * s_)), 0.13 * s_, seeds(kind), 20, (1, 1, 0.45))
        box('sack_tag', p + Vector((0.12 * s_, -0.08 * s_, 0.2 * s_)), (0.002, 0.06, 0.04), kraft, bevel=0, rot=(0, 0, -0.6))
    sphere('spill', (0.55, 1.35, 0.004), 0.12, seeds('sunflower'), 16, (1.2, 0.8, 0.06))
    lathe('scoop', [(0.0, 0.0), (0.04, 0.0), (0.045, 0.05), (0.042, 0.05), (0.037, 0.004), (0.0, 0.004)], Vector((0.66, 1.4, 0.0)), brass, 24, rot=(1.3, 0, 0.5))

# ------------------------------------------------------------------ parcels going out
with Group('parcels'):
    ob = Vector((2.45, D - 0.25, 0))
    box('out_bench', ob + Vector((0, 0, 0.3)), (0.8, 0.36, 0.035), oak, bevel=0.006)
    for (dx, dy) in ((-0.36, -0.14), (0.36, -0.14), (-0.36, 0.14), (0.36, 0.14)):
        box('bench_leg', ob + Vector((dx, dy, 0.15)), (0.04, 0.04, 0.3), oak, bevel=0.003)
    box('out_shelf', ob + Vector((0, 0.05, 0.1)), (0.74, 0.28, 0.02), oak, bevel=0.003)
    label('OUT', ob + Vector((0, -0.182, 0.24)), 0.07, chalk, name='out_word')
    for k, (dx, dz, w_, d_, h_) in enumerate(((-0.25, 0.32, 0.18, 0.16, 0.12), (-0.05, 0.32, 0.22, 0.18, 0.1), (-0.15, 0.44, 0.16, 0.14, 0.09),
                                               (0.2, 0.12, 0.2, 0.18, 0.12), (-0.15, 0.12, 0.18, 0.16, 0.1))):
        c = ob + Vector((dx, 0.02, dz + h_ / 2))
        box('parcel', c, (w_, d_, h_), kraft, bevel=0.006, rot=(0, 0, 0.05 * (k - 2)))
        box('parcel_twine_a', c, (w_ + 0.004, 0.006, h_ + 0.004), twine, bevel=0, rot=(0, 0, 0.05 * (k - 2)))
        box('parcel_twine_b', c, (0.006, d_ + 0.004, h_ + 0.004), twine, bevel=0, rot=(0, 0, 0.05 * (k - 2)))
        box('parcel_tag', c + Vector((w_ / 2 - 0.02, -d_ / 2 - 0.004, 0)), (0.045, 0.002, 0.03), paper, bevel=0)
    # the packer, tying a bow on the last parcel
    pk = ob + Vector((-0.02, -0.3, 0.0))
    box('parcel_last', pk + Vector((0, 0, 0.05)), (0.16, 0.14, 0.1), kraft, bevel=0.006)
    objs, f = SQ.squirrel(ob + Vector((-0.05, -0.42, 0)), math.radians(-160), 'sit', 1.1)
    for sg in (-1, 1):
        sphere('bow_loop', pk + Vector((sg * 0.025, -0.02, 0.11)), 0.02, twine, 10, (1.2, 0.4, 0.8))
    limb(f((-0.025, 0.08, 0.17)), pk + Vector((0, -0.02, 0.105)), 0.002, twine)
    limb(f((0.025, 0.08, 0.17)), pk + Vector((0, -0.02, 0.105)), 0.002, twine)
    # a ball of twine, rolled off
    sphere('twine_ball', ob + Vector((0.45, -0.45, 0.05)), 0.05, varied('twine_ball', (0.72, 0.6, 0.4), 0.03, 0.9, bump=1.0, bump_scale=120), 16)

# ------------------------------------------------------------------ the chalkboard with the numbers, a hanging sign
with Group('board'):
    bx, bz = 2.45, 1.2
    box('board', (bx, D - 0.035, bz), (0.78, 0.02, 0.56), solid('slate', (0.06, 0.08, 0.07), 0.85), bevel=0.003)
    box('board_frame', (bx, D - 0.022, bz), (0.84, 0.02, 0.62), oak, bevel=0.006)
    box('chalk_ledge', (bx, D - 0.06, bz - 0.3), (0.8, 0.05, 0.015), oak, bevel=0.003)
    for k, c in enumerate(((0.95, 0.95, 0.9), (0.95, 0.7, 0.7), (0.7, 0.85, 0.95))):
        cyl('chalk_stick', (bx - 0.25 + k * 0.06, D - 0.06, bz - 0.285), 0.006, 0.04, solid('chalk%d' % k, c, 0.9), verts=8, rot=(0, math.pi / 2, 0))
    rot = (math.pi / 2, 0, 0)
    hand('this week', (bx, D - 0.046, bz + 0.2), 0.055, chalk, rot, name='chalk_h')
    limb(Vector((bx - 0.2, D - 0.046, bz + 0.165)), Vector((bx + 0.2, D - 0.046, bz + 0.165)), 0.002, chalk)
    for k, line in enumerate(('7 nonprofits piloting', '90,000 records load-tested', 'stock page  4.7s  ->  0.22s')):
        hand(line, (bx, D - 0.046, bz + 0.08 - k * 0.1), 0.045, chalk, rot, name='chalk_l')
    hand('(nuts!)', (bx + 0.26, D - 0.046, bz - 0.22), 0.03, chalk, rot, name='chalk_joke')
# painted sign over the cabinet, hung from brass brackets
sg_c = Vector((0.1, 1.0, 1.72))
for sg in (-1, 1):
    limb(Vector((0.02, sg_c.y + sg * 0.42, 1.92)), Vector((0.1, sg_c.y + sg * 0.42, 1.92)), 0.008, brass)
    limb(Vector((0.1, sg_c.y + sg * 0.42, 1.92)), sg_c + Vector((0, sg * 0.42, 0.07)), 0.003, brass)
box('sign_board', sg_c, (0.03, 1.0, 0.15), green_paint, bevel=0.01)
label('SQUIRRELS & SEEDS', sg_c + Vector((0.017, 0, 0)), 0.075, cream, rot=(math.pi / 2, 0, math.pi / 2), name='sign_t')

# ------------------------------------------------------------------ seven thank-you notes
with Group('notes'):
    cb = Vector((0.025, 0.95, 1.2))
    box('corkboard', cb, (0.02, 0.5, 0.42), varied('corkb', (0.62, 0.45, 0.28), 0.05, 0.95, bump=0.7, bump_scale=300), bevel=0.003)
    box('cork_frame', cb + Vector((-0.004, 0, 0)), (0.02, 0.54, 0.46), oak, bevel=0.004)
    papers = [(0.97, 0.92, 0.6), (0.92, 0.76, 0.78), (0.75, 0.86, 0.96), (0.96, 0.96, 0.92), (0.8, 0.92, 0.72), (0.97, 0.82, 0.56), (0.9, 0.86, 0.96)]
    words = ['thank you!', 'thanks :)', 'merci!', 'thank you', 'ty!!', 'thanks!', 'gracias']
    for k, col in enumerate(papers):
        p = cb + Vector((0.013, -0.18 + (k % 4) * 0.12 + RG.uniform(-0.015, 0.015), 0.08 - (k // 4) * 0.17 + RG.uniform(-0.02, 0.02)))
        tilt_ = RG.uniform(-0.18, 0.18)
        box('note', p, (0.002, 0.1, 0.11), solid('note%d' % k, col, 0.9), bevel=0, rot=(tilt_, 0, 0))
        hand(words[k], p + Vector((0.002, 0, 0.015)), 0.017, ink, rot=(math.pi / 2 + tilt_, 0, -math.pi / 2), name='note_t')
        for r_ in range(2):
            box('note_line', p + Vector((0.0015, 0, -0.015 - r_ * 0.018)), (0.001, 0.07, 0.003), ink, bevel=0, rot=(tilt_, 0, 0))
        sphere('pin', p + Vector((0.008, 0, 0.045)), 0.007, solid('pin%d' % (k % 3), [(0.8, 0.15, 0.1), (0.15, 0.35, 0.7), (0.95, 0.8, 0.2)][k % 3], 0.3), 8)

# ------------------------------------------------------------------ hanging dried sunflower heads, string lights, lamps
for k in range(4):
    p = Vector((2.05 + k * 0.22, D - 0.08, 1.88))
    limb(Vector((p.x, D - 0.03, 1.96)), p + Vector((0, 0, 0.06)), 0.002, twine)
    head_ = cyl('sunflower_head', p, 0.07, 0.025, seeds('sunflower'), verts=24, rot=(math.pi / 2 - 0.25, 0, 0))
    for j in range(14):
        a = j / 14 * 2 * math.pi
        sphere('dry_petal', p + Vector((math.cos(a) * 0.08, -0.005, math.sin(a) * 0.08)), 0.02, solid('dry_petal', (0.75, 0.5, 0.15), 0.8), 6, (1, 0.2, 0.45)).rotation_euler = (0, -a, 0)
for k in range(15):
    t = k / 14
    p = Vector((0.2 + 1.55 * t, D - 0.05, 1.66 - 0.06 * math.sin(t * math.pi * 3) ** 2))
    sphere('fairy', p, 0.011, solid('fairy', (1, 0.85, 0.6), 0.4, emit=(1, 0.7, 0.35), strength=12), 8)
for k in range(14):
    t0, t1 = k / 14, (k + 1) / 14
    limb(Vector((0.2 + 1.55 * t0, D - 0.05, 1.672 - 0.06 * math.sin(t0 * math.pi * 3) ** 2)), Vector((0.2 + 1.55 * t1, D - 0.05, 1.672 - 0.06 * math.sin(t1 * math.pi * 3) ** 2)), 0.0012, ink)
amber = solid('amber_glass', (1.0, 0.7, 0.35), 0.15)
amber.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.7
for (x, y) in ((2.15, 0.9),):
    limb(Vector((x, y, H + 0.3)), Vector((x, y, 1.44)), 0.003, iron_m)
    lathe('pendant_shade', [(0.012, 0.13), (0.03, 0.12), (0.06, 0.07), (0.1, 0.0), (0.098, -0.004), (0.058, 0.066), (0.028, 0.114), (0.01, 0.124)], (x, y, 1.3), amber, 36)
    sphere('pendant_bulb', (x, y, 1.34), 0.028, solid('bulb', (1, 0.9, 0.7), 0.3, emit=(1.0, 0.7, 0.38), strength=30), 12)
    L = bpy.data.lights.new('pendant', 'POINT'); L.energy = 22; L.color = (1.0, 0.7, 0.4); L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('pendant', L)).location = (x, y, 1.32)

# ------------------------------------------------------------------ broom, dustpan, a cart of acorns
box('dustpan', (2.55, 0.25, 0.012), (0.14, 0.12, 0.02), solid('pan_tin', (0.5, 0.25, 0.15), 0.4, metal=0.5), bevel=0.004, rot=(0, 0, 0.4))
sphere('pan_seeds', (2.55, 0.25, 0.02), 0.05, seeds('sunflower'), 12, (1, 0.8, 0.25))
for k in range(9):
    sphere('loose_seed', (2.3 + RG.uniform(0, 0.25), 0.35 + RG.uniform(-0.1, 0.1), 0.004), 0.007, seeds('sunflower'), 6, (1.6, 0.8, 0.5))
ca = Vector((2.25, 0.62, 0))
box('cart', ca + Vector((0, 0, 0.12)), (0.36, 0.22, 0.1), varied('cart_wood', (0.5, 0.18, 0.12), 0.06, 0.6), bevel=0.01, rot=(0, 0, 0.3))
for sx in (-0.12, 0.12):
    for sy in (-0.12, 0.12):
        cyl('cart_wheel', ca + Matrix.Rotation(0.3, 3, 'Z') @ Vector((sx, sy, 0.05)), 0.05, 0.02, walnut_w, verts=20, rot=(math.pi / 2, 0, 0.3))
limb(ca + Matrix.Rotation(0.3, 3, 'Z') @ Vector((0.18, 0, 0.12)), ca + Matrix.Rotation(0.3, 3, 'Z') @ Vector((0.35, 0, 0.3)), 0.008, walnut_w)
for k in range(7):
    q = ca + Matrix.Rotation(0.3, 3, 'Z') @ Vector((-0.12 + (k % 4) * 0.08, -0.05 + (k // 4) * 0.09, 0.16))
    lathe('cart_acorn', [(0.0, 0.0), (0.012, 0.004), (0.02, 0.018), (0.02, 0.032), (0.0, 0.034)], q, solid('acorn_shell', (0.52, 0.32, 0.12), 0.35, coat=0.3), 16)
    lathe('cart_cap', [(0.0, 0.03), (0.022, 0.03), (0.024, 0.038), (0.016, 0.046), (0.0, 0.048)], q, varied('acorn_cup', (0.38, 0.28, 0.16), 0.05, 0.95, bump=1.0, bump_scale=500), 16)

# ------------------------------------------------------------------ light, camera
room_light((1.6, 0.9, 1.7), 70, (1, 0.72, 0.45), 0.8)
fill = bpy.data.lights.new('front_fill', 'AREA'); fill.energy = 55; fill.size = 2.5; fill.color = (1.0, 0.82, 0.62)
fo = link(bpy.data.objects.new('front_fill', fill)); fo.location = (3.6, -1.2, 2.6); fo.rotation_euler = (math.radians(55), 0, math.radians(50))
room_light((0.9, 2.0, 1.4), 18, (1, 0.75, 0.5), 0.5)
room_light((2.1, 1.9, 1.0), 14, (1, 0.72, 0.48), 0.4)
mo = bpy.data.lights.new('moonlight', 'AREA'); mo.energy = 6; mo.size = 0.5; mo.color = (0.6, 0.72, 1.0)
o = link(bpy.data.objects.new('moonlight', mo)); o.location = (-0.3, 1.55, 1.2); o.rotation_euler = (0, math.radians(-90), 0)
lighting(sc, sun_rot=(math.radians(60), 0, math.radians(-40)), sun_energy=0.0, sun_color=(1, 1, 1),
         bg_top=(0.05, 0.05, 0.07), bg_bottom=(0.06, 0.05, 0.06), hdri_strength=0.04)
cam = iso_camera(sc, (1.45, 1.2, 0.98), 4.35, res=(int(os.environ.get('RES_X', 1400)), int(os.environ.get('RES_Y', 1050))))
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
if not os.environ.get('NO_RENDER'):
    render(sc, OUT, SAMPLES)
if os.environ.get('WEB_OUT'):
    export_web(sc, cam, os.environ['WEB_OUT'])
