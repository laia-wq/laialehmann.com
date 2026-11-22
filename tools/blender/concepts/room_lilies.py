"""Room: Lilies & Rain + Lilies & Fire — the blue-shuttered house, ground floor.

A small town clerk's office that has become a greenhouse. In the middle a
lily grows from a bulb whose roots are documents (the paperwork a grant
needs) up to one bloom (the application). Around it, the four steps:
  Find    - the wall map of small towns with pins, a card catalogue of grants
  Decide  - a brass balance weighing two folders
  Draft   - the clerk's desk under the rainy window, a typewriter mid-page
  Review  - a table with a stamp, ink pad and red pencil, pages stamped DRAFT
In the corner, the Fire alcove in ash and ember: a little stove, an
emergency kit, sandbags and an orange lily. Pinned by the desk, the honest
status: no users yet; interviews come first.

Hotspots: bloom, find, decide, draft, review, fire, status.
Usage: blender python room_lilies.py <out.png> [samples]   (env as room_shop.py)
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *
from room_kit import *
from canal_extras import limb
from mathutils import Matrix

OUT = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-2].endswith('.png') else sys.argv[-1]
SAMPLES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 96
RG = random.Random(11)
sc = reset()

W, D, H = 3.6, 3.0, 2.3
plaster = stucco('lil_plaster', (0.56, 0.6, 0.58), dirt=(0.4, 0.42, 0.4))
planks = wood('lil_floor', (0.4, 0.27, 0.17), scale=5.0, rough=0.6)
trim = solid('lil_trim', (0.2, 0.26, 0.36), 0.55)        # the house's blue shutters, inside
oak = wood('oak', (0.42, 0.27, 0.15), scale=10.0, rough=0.5)
walnut = wood('walnut', (0.26, 0.16, 0.1), scale=10.0, rough=0.45)
brass = solid('brass', (0.78, 0.58, 0.28), 0.3, metal=1.0)
iron_m = solid('iron', (0.08, 0.08, 0.08), 0.5, metal=0.6)
paper = solid('paper', (0.93, 0.9, 0.82), 0.9)
ink = solid('ink', (0.08, 0.07, 0.07), 0.8)
red = solid('red_ink', (0.7, 0.1, 0.08), 0.6)
glass = solid('glass', (0.92, 0.96, 0.96), 0.03)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.95
leaf = varied('lily_leaf', (0.18, 0.36, 0.14), 0.08, 0.5)
cream = solid('paint_cream', (0.92, 0.86, 0.72), 0.8)

shell(W, D, H, plaster, planks, trim)
for (loc, size) in (((0.02, D / 2, 0.45), (0.02, D, 0.8)), ((W / 2, D - 0.02, 0.45), (W, 0.02, 0.8))):
    box('wainscot', loc, size, trim, bevel=0)


def lily(base, stem_h, col, open_=1.0, name='lily', lean=(0.0, 0.0), scale=1.0):
    """A lily: stem with a few strap leaves, six curled petals, stamens."""
    _b = set(bpy.data.objects.keys())
    top = base + Vector((lean[0], lean[1], stem_h))
    limb(base, top, 0.012, leaf)
    for k in range(4):
        a = k * 1.7; z = 0.15 + k * stem_h * 0.18
        p = base + Vector((lean[0] * z / stem_h, lean[1] * z / stem_h, z))
        lf = sphere(name + '_leaf', p + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.03)), 0.12, leaf, 12, (0.12, 0.9, 0.05))
        lf.rotation_euler = (0.9, 0, a + math.pi / 2)
    pm = solid(name + '_petal', col, 0.55, coat=0.3)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        d = Vector((math.cos(a), math.sin(a), 0))
        out = 0.06 + 0.04 * open_
        p = top + d * out + Vector((0, 0, 0.06 - 0.03 * open_))
        pe = sphere(name + '_petal', p, 0.075, pm, 14, (0.32, 1.0, 0.06))
        pe.rotation_euler = (0, 0, 0)
        pe.rotation_euler = (Matrix.Rotation(a + math.pi / 2, 3, 'Z') @ Matrix.Rotation(-(0.5 + 0.5 * open_), 3, 'X')).to_euler()
        # curled tip
        tip = top + d * (out + 0.07) + Vector((0, 0, 0.09 - 0.07 * open_))
        sphere(name + '_tip', tip, 0.03, pm, 10, (0.35, 1.0, 0.12)).rotation_euler = (Matrix.Rotation(a + math.pi / 2, 3, 'Z') @ Matrix.Rotation(0.6, 3, 'X')).to_euler()
    for k in range(6):
        a = k / 6 * 2 * math.pi + 0.3
        e = top + Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.1))
        limb(top + Vector((0, 0, 0.02)), e, 0.002, solid('stamen', (0.85, 0.85, 0.6), 0.6))
        sphere('anther', e, 0.008, solid('anther', (0.6, 0.25, 0.08), 0.6), 6, (1, 1, 1.8))
    if scale != 1.0:   # grow the flower head (not the stem) about its centre
        for n_ in set(bpy.data.objects.keys()) - _b:
            o = bpy.data.objects[n_]
            if (o.location - top).length < 0.25 and 'leaf' not in o.name:
                o.location = top + (o.location - top) * scale; o.scale = o.scale * scale
    return top


# ---- the window with the rain: the clerk's desk under it (Draft)
cut(bpy.data.objects['wall_w'], box('win_cut', (-0.06, 1.55, 1.45), (0.4, 1.3, 1.1), None, bevel=0))
night = solid('night', (0.06, 0.08, 0.13), 0.5, emit=(0.05, 0.08, 0.15), strength=1.0)
box('win_night', (-0.11, 1.55, 1.45), (0.01, 1.3, 1.1), night, bevel=0)
for k in range(5):   # lights across the canal, blurred by rain
    sphere('far_light', (-0.105, 1.0 + k * 0.26, 1.15 + (k % 3) * 0.13), 0.025, solid('far_glow', (1, 0.7, 0.4), 0.5, emit=(1, 0.6, 0.3), strength=5.0), 8, (0.2, 1, 1.4))
pane = solid('pane', (0.7, 0.8, 0.85), 0.04); pane.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.12
with Group('window'):
    box('win_glass', (-0.075, 1.55, 1.45), (0.006, 1.3, 1.1), pane, bevel=0)
for (y, z, sy, sz) in ((1.55, 1.45, 0.04, 1.1), (1.55, 1.45, 1.3, 0.04), (0.88, 1.45, 0.05, 1.15), (2.22, 1.45, 0.05, 1.15), (1.55, 2.02, 1.38, 0.05), (1.55, 0.88, 1.45, 0.06)):
    box('win_frame', (-0.03, y, z), (0.07, sy, sz), trim, bevel=0.004)
# (the rain itself runs down the glass in the browser)

with Group('draft'):
    dk = Vector((0.45, 1.55, 0))
    box('desk_top', dk + Vector((0, 0, 0.76)), (0.6, 1.3, 0.04), walnut, bevel=0.008)
    for (dx, dy) in ((-0.26, -0.6), (0.26, -0.6), (-0.26, 0.6), (0.26, 0.6)):
        box('desk_leg', dk + Vector((dx, dy, 0.37)), (0.05, 0.05, 0.74), walnut, bevel=0.005)
    box('desk_drawers', dk + Vector((0.0, -0.4, 0.55)), (0.55, 0.42, 0.36), walnut, bevel=0.006)
    for k in range(2):
        cyl('drawer_knob', dk + Vector((0.28, -0.4, 0.48 + k * 0.15)), 0.012, 0.02, brass, verts=10, rot=(0, math.pi / 2, 0))
    # typewriter, a page half typed
    tw = dk + Vector((0.05, 0.25, 0.78)); Rt = Matrix.Rotation(math.radians(90), 3, 'Z')
    tm = solid('typewriter', (0.12, 0.16, 0.14), 0.35, coat=0.6)
    box('tw_body', tw + Vector((0, 0, 0.06)), (0.3, 0.34, 0.12), tm, bevel=0.03, rot=Rt.to_euler())
    cyl('tw_platen', tw + Vector((-0.06, 0, 0.14)), 0.025, 0.38, ink, verts=16, rot=(math.pi / 2, 0, 0))
    for r_ in range(4):
        for c_ in range(9):
            cyl('tw_key', tw + Vector((0.13 - r_ * 0.035, -0.12 + c_ * 0.03, 0.1 + r_ * 0.012)), 0.01, 0.015, solid('tw_keycap', (0.9, 0.88, 0.8), 0.4), verts=10)
    pg = box('tw_page', tw + Vector((-0.08, 0, 0.26)), (0.006, 0.22, 0.24), paper, bevel=0, rot=(0, -0.25, 0))
    for r_ in range(6):
        box('tw_line', tw + Vector((-0.075 + 0.0, 0, 0.2 + r_ * 0.025)), (0.004, 0.17 - (r_ == 5) * 0.08, 0.004), ink, bevel=0, rot=(0, -0.25, 0))
    label('Grant application', tw + Vector((-0.072, 0, 0.36)), 0.016, ink, rot=(math.pi / 2, 0.25, math.pi / 2), name='tw_title')
    # nameplate, tea gone cold, a lamp
    box('nameplate', dk + Vector((0.22, -0.2, 0.8)), (0.05, 0.3, 0.06), brass, bevel=0.004, rot=(0, -0.35, 0))
    label('TOWN CLERK', dk + Vector((0.25, -0.2, 0.805)), 0.03, ink, rot=(math.pi / 2, 0.35, math.pi / 2), name='nameplate_t')
    cyl('teacup', dk + Vector((0.15, 0.55, 0.81)), 0.035, 0.06, solid('cup', (0.9, 0.88, 0.82), 0.3), verts=16)
    cyl('saucer', dk + Vector((0.15, 0.55, 0.782)), 0.06, 0.008, solid('cup', (0.9, 0.88, 0.82), 0.3), verts=20)
    cyl('tea', dk + Vector((0.15, 0.55, 0.835)), 0.03, 0.004, solid('tea', (0.35, 0.18, 0.06), 0.1), verts=16)
    dl = dk + Vector((-0.15, -0.5, 0.78))
    cyl('lamp_base', dl, 0.07, 0.02, brass, verts=16)
    limb(dl, dl + Vector((0.05, 0.05, 0.35)), 0.008, brass)
    cyl('lamp_shade', dl + Vector((0.08, 0.08, 0.36)), 0.09, 0.1, solid('banker_green', (0.08, 0.32, 0.2), 0.2, coat=0.8), verts=20, r2=0.05, rot=(0.5, -0.4, 0))
    L = bpy.data.lights.new('desk_lamp', 'POINT'); L.energy = 25; L.color = (1, 0.78, 0.5); L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('desk_lamp', L)).location = dl + Vector((0.1, 0.1, 0.3))
    # chair
    ch = dk + Vector((0.55, 0.15, 0))
    box('chair_seat', ch + Vector((0, 0, 0.46)), (0.4, 0.4, 0.04), walnut, bevel=0.006)
    for (dx, dy) in ((-0.17, -0.17), (0.17, -0.17), (-0.17, 0.17), (0.17, 0.17)):
        box('chair_leg', ch + Vector((dx, dy, 0.23)), (0.035, 0.035, 0.46), walnut, bevel=0.004)
    box('chair_back', ch + Vector((0.19, 0, 0.72)), (0.03, 0.38, 0.45), walnut, bevel=0.006)
    sphere('cardigan', ch + Vector((0.18, 0, 0.88)), 0.12, varied('cardigan', (0.6, 0.5, 0.3), 0.06, 0.95, bump=0.4, bump_scale=200), 12, (0.4, 1.4, 0.7))

# ---- the honest status, pinned by the window
with Group('status'):
    st = Vector((0.02, 0.5, 1.4))
    box('status_card', st, (0.005, 0.34, 0.42), solid('kraft', (0.72, 0.58, 0.4), 0.9), bevel=0, rot=(0.04, 0, 0))
    lines = ('STATUS', 'no users yet', 'first:', '8-10 interviews', 'then build')
    for k, line in enumerate(lines):
        label(line, st + Vector((0.006, 0, 0.15 - k * 0.07)), 0.034 if k else 0.045, red if k == 0 else ink, rot=(math.pi / 2, 0, -math.pi / 2), name='status_t')
    sphere('pin', st + Vector((0.01, 0, 0.19)), 0.012, red, 8)

# ---- the lily in the middle: document roots, one bloom (the application)
with Group('bloom'):
    lc = Vector((1.85, 1.35, 0))
    cyl('plinth', lc + Vector((0, 0, 0.25)), 0.32, 0.5, walnut, verts=32, bevel=0.01)
    cyl('pot_glass', lc + Vector((0, 0, 0.72)), 0.24, 0.44, glass, verts=40)
    cyl('pot_soil', lc + Vector((0, 0, 0.82)), 0.225, 0.06, solid('soil', (0.16, 0.1, 0.07), 0.95), verts=40)
    cyl('pot_water', lc + Vector((0, 0, 0.64)), 0.225, 0.28, solid('pot_water', (0.6, 0.75, 0.8), 0.05), verts=40)
    bpy.data.materials['pot_water'].node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.9
    bulb = sphere('bulb', lc + Vector((0, 0, 0.88)), 0.07, solid('bulb_skin', (0.75, 0.6, 0.4), 0.7), 16, (1, 1, 0.85))
    # roots: curling strips of paper, each a document a grant needs
    for k in range(14):
        a = k / 14 * 2 * math.pi + RG.uniform(-0.15, 0.15)
        prev = lc + Vector((0, 0, 0.84))
        for j in range(5):
            t = (j + 1) / 5
            q = lc + Vector((math.cos(a + t * 0.6) * (0.03 + 0.17 * t), math.sin(a + t * 0.6) * (0.03 + 0.17 * t), 0.84 - 0.36 * t))
            box('doc_root', (prev + q) / 2, (0.022, 0.004, (q - prev).length + 0.01), paper, bevel=0).rotation_euler = (q - prev).to_track_quat('Z', 'Y').to_euler()
            if j % 2 == 0:
                box('doc_line', (prev + q) / 2 + Vector((0, 0, 0)), (0.016, 0.0045, 0.002), ink, bevel=0).rotation_euler = (q - prev).to_track_quat('Z', 'Y').to_euler()
            prev = q
    top = lily(lc + Vector((0, 0, 0.9)), 0.75, (0.96, 0.9, 0.9), 1.0, 'bloom', scale=1.7)
    # the bloom carries a little tag: the application
    limb(top + Vector((0.02, 0, -0.1)), top + Vector((0.16, -0.05, -0.2)), 0.001, ink)
    box('app_tag', top + Vector((0.17, -0.05, -0.25)), (0.004, 0.08, 0.1), paper, bevel=0, rot=(0, 0, -0.6))
    label('application', top + Vector((0.172, -0.052, -0.25)), 0.014, ink, rot=(math.pi / 2, 0, math.pi / 2 - 0.6), name='app_tag_t')
    # a second, smaller bud: the next one
    lily(lc + Vector((0.08, 0.06, 0.9)), 0.45, (0.95, 0.8, 0.82), 0.0, 'bud', lean=(0.1, 0.1), scale=1.3)

# ---- Find: map of small towns, pins and string; card catalogue
with Group('find'):
    mp = Vector((0.9, D - 0.025, 1.55))
    box('map', mp, (0.9, 0.01, 0.65), solid('map_paper', (0.86, 0.8, 0.62), 0.9), bevel=0)
    box('map_frame', mp + Vector((0, 0.01, 0)), (0.96, 0.012, 0.71), walnut, bevel=0.004)
    for k in range(9):   # rivers and roads
        limb(mp + Vector((-0.4 + k * 0.1, -0.008, RG.uniform(-0.28, 0.28))), mp + Vector((-0.35 + k * 0.1, -0.008, RG.uniform(-0.28, 0.28))), 0.003, solid('map_road', (0.55, 0.45, 0.35), 0.9))
    limb(mp + Vector((-0.44, -0.008, 0.2)), mp + Vector((0.44, -0.008, -0.15)), 0.006, solid('map_river', (0.45, 0.6, 0.72), 0.6))
    pins = [mp + Vector((RG.uniform(-0.4, 0.4), -0.015, RG.uniform(-0.27, 0.27))) for _ in range(12)]
    for k, p in enumerate(pins):
        sphere('map_pin', p, 0.012, [red, solid('pin_green', (0.2, 0.5, 0.25), 0.4), solid('pin_yellow', (0.9, 0.75, 0.2), 0.4)][k % 3], 8)
    for a, b in zip(pins[:6], pins[1:7]):
        limb(a, b, 0.0015, red)
    label('small towns, open grants', mp + Vector((0, -0.012, 0.36)), 0.035, ink, name='map_title')
    cc = Vector((0.9, D - 0.22, 0))
    box('catalogue', cc + Vector((0, 0, 0.45)), (0.8, 0.36, 0.9), oak, bevel=0.01)
    for r_ in range(4):
        for c_ in range(4):
            p = cc + Vector((-0.3 + c_ * 0.2, -0.181, 0.15 + r_ * 0.2))
            box('drawer_face', p, (0.17, 0.006, 0.16), oak, bevel=0.004)
            box('drawer_label', p + Vector((0, -0.004, 0.04)), (0.07, 0.002, 0.03), paper, bevel=0)
            cyl('drawer_pull', p + Vector((0, -0.006, -0.01)), 0.012, 0.01, brass, verts=10, rot=(math.pi / 2, 0, 0))
    # one drawer pulled out, index cards standing up
    box('drawer_out', cc + Vector((0.1, -0.36, 0.75)), (0.17, 0.36, 0.14), oak, bevel=0.004)
    for k in range(8):
        box('index_card', cc + Vector((0.1, -0.48 + k * 0.03, 0.82 + (k == 3) * 0.04)), (0.15, 0.002, 0.1), paper, bevel=0)
    sphere('magnifier_lens', cc + Vector((-0.2, -0.05, 0.93)), 0.05, glass, 16, (1, 1, 0.15))
    limb(cc + Vector((-0.15, -0.08, 0.92)), cc + Vector((-0.05, -0.15, 0.92)), 0.008, walnut)

# ---- Decide: a brass balance weighing two folders
with Group('decide'):
    sd = Vector((1.95, D - 0.3, 0))
    box('side_table', sd + Vector((0, 0, 0.7)), (0.6, 0.4, 0.04), walnut, bevel=0.006)
    for (dx, dy) in ((-0.26, -0.16), (0.26, -0.16), (-0.26, 0.16), (0.26, 0.16)):
        box('table_leg', sd + Vector((dx, dy, 0.35)), (0.04, 0.04, 0.7), walnut, bevel=0.004)
    bc = sd + Vector((0, 0, 0.72))
    cyl('scale_base', bc + Vector((0, 0, 0.015)), 0.08, 0.03, brass, verts=20)
    limb(bc, bc + Vector((0, 0, 0.35)), 0.01, brass)
    tilt = 0.12
    ends = [bc + Vector((sg * 0.22 * math.cos(tilt), 0, 0.35 - sg * 0.22 * math.sin(tilt))) for sg in (-1, 1)]
    limb(ends[0], ends[1], 0.006, brass)
    sphere('scale_top', bc + Vector((0, 0, 0.37)), 0.02, brass, 10)
    for e, col in zip(ends, ((0.55, 0.65, 0.35), (0.8, 0.45, 0.3))):
        for sg in (-1, 1):
            limb(e, e + Vector((sg * 0.06, 0, -0.18)), 0.0015, brass)
        cyl('pan', e + Vector((0, 0, -0.18)), 0.08, 0.012, brass, verts=20, r2=0.06)
        box('folder', e + Vector((0, 0, -0.15)), (0.13, 0.1, 0.03), solid('folder%.1f' % col[0], col, 0.8), bevel=0.003)
    label('fits?  worth it?', sd + Vector((0, -0.201, 0.62)), 0.03, cream, name='decide_t')

# ---- Review: stamp, ink pad, red pencil, pages stamped DRAFT
with Group('review'):
    rv = Vector((2.55, 0.55, 0))
    box('review_table', rv + Vector((0, 0, 0.72)), (0.8, 0.55, 0.04), oak, bevel=0.008)
    for (dx, dy) in ((-0.35, -0.23), (0.35, -0.23), (-0.35, 0.23), (0.35, 0.23)):
        box('table_leg', rv + Vector((dx, dy, 0.36)), (0.045, 0.045, 0.72), oak, bevel=0.004)
    for k in range(5):
        pg = box('review_page', rv + Vector((-0.1 + k * 0.015, 0.02 - k * 0.01, 0.745 + k * 0.004)), (0.24, 0.32, 0.003), paper, bevel=0, rot=(0, 0, 0.15 - k * 0.07))
    top_rot = (0, 0, 0.15 - 4 * 0.07)
    for r_ in range(8):
        box('review_line', rv + Vector((-0.04, 0.1 - r_ * 0.03, 0.765)), (0.16, 0.004, 0.001), ink, bevel=0, rot=top_rot)
    label('DRAFT', rv + Vector((-0.05, -0.08, 0.768)), 0.05, red, rot=(0, 0, 0.5), name='stamp_mark')
    limb(rv + Vector((-0.12, 0.05, 0.768)), rv + Vector((0.02, 0.06, 0.768)), 0.0025, red)   # a red correction
    st_ = rv + Vector((0.22, 0.08, 0.74))
    cyl('stamp_base', st_ + Vector((0, 0, 0.02)), 0.04, 0.04, walnut, verts=16)
    cyl('stamp_handle', st_ + Vector((0, 0, 0.09)), 0.02, 0.1, walnut, verts=12)
    sphere('stamp_knob', st_ + Vector((0, 0, 0.15)), 0.03, walnut, 12)
    box('ink_pad', rv + Vector((0.22, -0.12, 0.75)), (0.12, 0.08, 0.02), solid('pad_tin', (0.3, 0.1, 0.1), 0.4, metal=0.5), bevel=0.004)
    limb(rv + Vector((0.05, -0.2, 0.748)), rv + Vector((0.25, -0.15, 0.748)), 0.006, red)
    # a clerk's stool
    cyl('stool', rv + Vector((0.1, -0.5, 0.45)), 0.15, 0.04, walnut, verts=20)
    for k in range(3):
        a = k / 3 * 2 * math.pi
        limb(rv + Vector((0.1 + math.cos(a) * 0.12, -0.5 + math.sin(a) * 0.12, 0)), rv + Vector((0.1 + math.cos(a) * 0.07, -0.5 + math.sin(a) * 0.07, 0.43)), 0.013, walnut)

# ---- the Fire alcove: ash and ember
with Group('fire'):
    fa = Vector((3.05, D, 0))
    ash = solid('ash_wall', (0.16, 0.14, 0.13), 0.95)
    box('alcove_back', fa + Vector((0, -0.04, H / 2)), (1.0, 0.04, H), ash, bevel=0)
    box('alcove_floor', fa + Vector((0, -0.45, 0.012)), (1.0, 0.9, 0.024), solid('hearth_tile', (0.25, 0.12, 0.08), 0.8), bevel=0.003)
    box('alcove_arch', fa + Vector((0, -0.07, 1.95)), (1.0, 0.06, 0.12), solid('ember_trim', (0.45, 0.16, 0.08), 0.6), bevel=0.01)
    # little cast-iron stove with embers in the window
    sv = fa + Vector((-0.1, -0.35, 0))
    box('stove', sv + Vector((0, 0, 0.33)), (0.42, 0.36, 0.5), iron_m, bevel=0.02)
    for dx in (-0.17, 0.17):
        box('stove_leg', sv + Vector((dx, 0, 0.04)), (0.05, 0.3, 0.08), iron_m, bevel=0.004)
    box('stove_window', sv + Vector((0, -0.181, 0.33)), (0.24, 0.004, 0.16), solid('embers', (1, 0.4, 0.1), 0.4, emit=(1.0, 0.32, 0.06), strength=6), bevel=0)
    limb(sv + Vector((0, 0, 0.58)), sv + Vector((0, 0.15, 1.9)), 0.05, iron_m)
    L = bpy.data.lights.new('ember', 'POINT'); L.energy = 18; L.color = (1.0, 0.4, 0.12); L.shadow_soft_size = 0.1
    link(bpy.data.objects.new('ember', L)).location = sv + Vector((0, -0.3, 0.33))
    # emergency kit on a shelf: lantern, first-aid tin, radio, water
    box('kit_shelf', fa + Vector((0.25, -0.15, 1.25)), (0.42, 0.26, 0.03), walnut, bevel=0.004)
    box('first_aid', fa + Vector((0.12, -0.15, 1.33)), (0.14, 0.1, 0.12), solid('aid_red', (0.7, 0.12, 0.1), 0.5), bevel=0.01)
    box('aid_cross_h', fa + Vector((0.12, -0.201, 1.33)), (0.07, 0.002, 0.02), cream, bevel=0)
    box('aid_cross_v', fa + Vector((0.12, -0.201, 1.33)), (0.02, 0.002, 0.07), cream, bevel=0)
    cyl('kit_lantern', fa + Vector((0.32, -0.15, 1.35)), 0.04, 0.14, solid('lantern_tin', (0.55, 0.5, 0.4), 0.4, metal=0.7), verts=12)
    for k in range(3):
        cyl('water_bottle', fa + Vector((0.42 - k * 0.0, -0.12 + k * 0.0, 1.35 + k * 0.0)), 0.025, 0.12, glass, verts=12)
    # sandbags and an orange lily in a jar
    for k, (dx, dz) in enumerate(((0.3, 0.08), (0.42, 0.08), (0.36, 0.2))):
        sphere('sandbag', fa + Vector((dx, -0.55, dz)), 0.12, varied('sandbag', (0.55, 0.48, 0.34), 0.06, 0.95, bump=0.4, bump_scale=120), 12, (1, 0.7, 0.55))
    jar = fa + Vector((-0.3, -0.25, 0.0))
    cyl('fire_vase', jar + Vector((0, 0, 0.18)), 0.07, 0.36, solid('vase_char', (0.12, 0.1, 0.1), 0.4, coat=0.5), verts=20, r2=0.05)
    lily(jar + Vector((0, 0, 0.36)), 0.38, (0.95, 0.42, 0.1), 0.9, 'fire_lily')
    label('Lilies & Fire', fa + Vector((0, -0.065, 1.95)), 0.05, solid('ember_text', (1, 0.6, 0.3), 0.6, emit=(1, 0.5, 0.2), strength=1.2), name='fire_sign')

label('Lilies & Rain', (1.0, D - 0.002, 2.08), 0.12, cream, name='rain_sign')

# ---- light, camera
room_light((1.8, 1.2, 2.1), 110, (1, 0.74, 0.5), 0.7)
room_light((2.6, 0.5, 1.9), 45, (0.9, 0.85, 0.8), 0.6)
room_light((0.6, 1.6, 1.9), 30, (0.8, 0.85, 1.0), 0.6)
lighting(sc, sun_rot=(math.radians(60), 0, math.radians(-40)), sun_energy=0.0, sun_color=(1, 1, 1),
         bg_top=(0.05, 0.05, 0.07), bg_bottom=(0.06, 0.05, 0.06), hdri_strength=0.05)
cam = iso_camera(sc, (1.7, 1.4, 1.0), 5.0, res=(int(os.environ.get('RES_X', 1400)), int(os.environ.get('RES_Y', 1050))))
if not os.environ.get('NO_RENDER'):
    render(sc, OUT, SAMPLES)
if os.environ.get('WEB_OUT'):
    export_web(sc, cam, os.environ['WEB_OUT'])
