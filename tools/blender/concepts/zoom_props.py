"""The window zooms past the first two (the shop, the design teams): which
windows each one looks into, and the thing that sits on each sill.

Each window is found by the street's glass nearest a point, so the specs
don't depend on object names. A zoom has one or more windows; the camera
swings from the street's angle round to face them (for the bay, at an angle
that shows its front and its side together).

  firsts     houseboat cabin, 3 windows: forest loss, physics lab, Signwise
  robot      tall house, 3rd floor middle window: a glass of water
  watif      cream shop, 2nd floor: a little flip calendar
  saas       cream shop, top floor: a mug and a pad of sticky notes
  lilies     the red bay: front pane (rain) and the narrower side pane (fire); a potted lily
  community  bakery shopfront: a soup pot and a ladle
"""
import math
import bpy
from mathutils import Vector, Matrix
from kit import solid, varied, node_mat, box, cyl, sphere, link
from canal_extras import limb

ZOOMS = {
    'firsts':    {'glass': [(0.14, -1.45, 0.45), (0.55, -1.3, 0.45), (0.96, -1.15, 0.45)], 'frame': False, 'frost_out': 0.002, 'W0': 2.2, 'W1': 1.25, 'elev': 0.2,
                  'teams': ['forest-loss', 'physics-engine', 'signwise']},
    'robot':     {'glass': [(-3.45, 1.33, 3.16)], 'arch': True, 'W0': 1.55, 'W1': 1.2, 'elev': 0.1, 'lens': 20, 'arc': 0.6, 'teams': ['brita-robot']},   # the bakery stands close in front: a wide lens from the gap
    'watif':     {'glass': [(0.21, 2.33, 2.08)], 'W0': 1.55, 'W1': 1.25, 'elev': 0.12, 'teams': ['watif']},
    'saas':      {'glass': [(0.21, 2.33, 3.28)], 'W0': 1.55, 'W1': 1.25, 'elev': 0.12, 'teams': ['saas']},
    'lilies':    {'glass': [(3.49, -0.14, 1.97), (3.79, 0.01, 1.97)], 'frame': False, 'frost_out': 0.002, 'W0': 1.6, 'W1': 1.25, 'elev': 0.18, 'side': 0.75,
                  'teams': ['lily-and-rain', 'lily-and-fire']},
    'community': {'glass': [(-2.93, -2.42, 0.83)], 'W0': 1.55, 'W1': 1.3, 'elev': 0.15, 'teams': ['community']},   # the bakery's canal side: open water in front
}
GLASS_NAMES = ('pane', 'bay_glass', 'win_glass', 'shop_glass')


def _bb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])


def find_glass(sc, p):
    p = Vector(p)
    best = None
    for o in sc.objects:
        if o.type != 'MESH' or o.name.split('.')[0] not in GLASS_NAMES: continue
        lo, hi = _bb(o); d = ((lo + hi) / 2 - p).length
        if best is None or d < best[0]: best = (d, o)
    return best[1] if best and best[0] < 0.25 else None


def frame_of(o, toward):
    """The glass's centre, its width direction t, outward normal n (facing
    `toward`), and its width and height."""
    lo, hi = _bb(o); c = (lo + hi) / 2
    M = o.matrix_world.to_3x3()
    dims = [(M.col[i].length * (max(v.co[i] for v in o.data.vertices) - min(v.co[i] for v in o.data.vertices)), i) for i in range(3)]
    thin = min(dims)[1]
    n = M.col[thin].normalized()
    if n.dot(Vector(toward)) < 0: n = -n
    n.z = 0; n.normalize()
    t = Vector((-n.y, n.x, 0))
    thick = min(dims)[0]
    w = abs(t.x) * (hi.x - lo.x) + abs(t.y) * (hi.y - lo.y) - thick * (abs(n.x) * abs(t.x) + abs(n.y) * abs(t.y)) * 2
    h = hi.z - lo.z
    return c, t, n, w, h


# ---------------------------------------------------------------- sill things
def glass_of_water(p):
    g = solid('zp_glass', (0.85, 0.9, 0.92), 0.04)
    g.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1.0
    water = solid('zp_water', (0.7, 0.85, 0.9), 0.02)
    water.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1.0
    water.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.33
    o = cyl('zp_glass', p + Vector((0, 0, 0.045)), 0.022, 0.09, g, verts=24, r2=0.026)
    cyl('zp_water', p + Vector((0, 0, 0.032)), 0.02, 0.06, water, verts=24, r2=0.023)
    cyl('zp_glass_base', p + Vector((0, 0, 0.003)), 0.021, 0.006, g, verts=24)
    return o


def flip_calendar(p, yaw):
    R = Matrix.Rotation(yaw, 3, 'Z'); P = lambda x, y, z: p + R @ Vector((x, y, z))
    paper = varied('zp_paper', (0.92, 0.9, 0.84), 0.03, 0.8)
    red = solid('zp_red', (0.7, 0.1, 0.08), 0.5)
    ink = solid('zp_ink', (0.08, 0.08, 0.1), 0.6)
    for sg in (-1, 1):   # an A-frame stand
        b_ = box('zp_cal', P(0, sg * 0.012, 0.035), (0.09, 0.004, 0.075), paper, bevel=0.002); b_.rotation_euler = (R @ Matrix.Rotation(sg * 0.3, 3, 'X')).to_euler()
    b_ = box('zp_cal_top', P(0, -0.024, 0.066), (0.09, 0.006, 0.014), red, bevel=0.002); b_.rotation_euler = (R @ Matrix.Rotation(-0.3, 3, 'X')).to_euler()
    for k in range(4):   # wire rings
        c = cyl('zp_ring', P(-0.03 + k * 0.02, -0.022, 0.073), 0.004, 0.003, solid('zp_wire', (0.6, 0.6, 0.62), 0.3, metal=1), verts=10)
        c.rotation_euler = (R @ Matrix.Rotation(math.pi / 2, 3, 'Y')).to_euler()
    for r in range(3):   # a little grid of days, one circled
        for k in range(5):
            b_ = box('zp_day', P(-0.032 + k * 0.016, -0.026, 0.045 - r * 0.014), (0.01, 0.001, 0.008), ink if (r, k) != (1, 3) else red, bevel=0)
            b_.rotation_euler = (R @ Matrix.Rotation(-0.3, 3, 'X')).to_euler()
    limb(P(0.06, -0.01, 0.002), P(0.075, -0.05, 0.004), 0.003, solid('zp_pencil', (0.9, 0.7, 0.1), 0.5))


def mug_and_notes(p, yaw):
    R = Matrix.Rotation(yaw, 3, 'Z'); P = lambda x, y, z: p + R @ Vector((x, y, z))
    mug = varied('zp_mug', (0.2, 0.36, 0.5), 0.04, 0.35)
    o = cyl('zp_mug', P(0, 0, 0.03), 0.022, 0.06, mug, verts=20)
    cyl('zp_coffee', P(0, 0, 0.058), 0.019, 0.003, solid('zp_coffee', (0.12, 0.06, 0.03), 0.2), verts=20)
    h = cyl('zp_handle', P(0.026, 0, 0.032), 0.012, 0.006, mug, verts=16); h.rotation_euler = (R @ Matrix.Rotation(math.pi / 2, 3, 'X')).to_euler()
    for k in range(6):   # a squared-up pad of sticky notes, top one curling
        b_ = box('zp_note', P(-0.06, 0.005, 0.002 + k * 0.002), (0.038, 0.038, 0.002), solid('zp_note', (0.98, 0.85, 0.25), 0.7), bevel=0)
        b_.rotation_euler = (R @ Matrix.Rotation(0.15 * (k % 2), 3, 'Z')).to_euler()
    return o


def potted_lily(p):
    pot = varied('zp_pot', (0.62, 0.34, 0.22), 0.08, 0.85)
    cyl('zp_pot', p + Vector((0, 0, 0.03)), 0.03, 0.06, pot, verts=16, r2=0.036)
    cyl('zp_soil', p + Vector((0, 0, 0.058)), 0.033, 0.004, solid('soil', (0.13, 0.09, 0.06), 0.95), verts=16)
    leaf = solid('zp_leaf', (0.18, 0.36, 0.14), 0.55)
    petal = solid('zp_petal', (0.96, 0.94, 0.88), 0.45)
    for k, (dx, dy, hgt) in enumerate(((0.0, 0.0, 0.2), (0.012, 0.01, 0.16), (-0.012, -0.006, 0.18))):
        base = p + Vector((dx, dy, 0.06)); top = base + Vector((dx * 2, dy * 2, hgt))
        limb(base, top, 0.0025, leaf)
        for j in range(5):   # a trumpet of five petals
            a = j * 2 * math.pi / 5 + k
            tip = top + Vector((math.cos(a) * 0.022, math.sin(a) * 0.022, 0.018))
            pt = cyl('zp_petal', (top + tip) / 2, 0.007, (tip - top).length, petal, verts=6, r2=0.002)
            pt.rotation_euler = (tip - top).to_track_quat('Z', 'Y').to_euler()
    for j in range(5):   # long strap leaves
        a = j * 1.3
        tip = p + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.13))
        lf = box('zp_leaf', (p + Vector((0, 0, 0.06)) + tip) / 2, (0.008, 0.002, (tip - p).length * 0.9), leaf, bevel=0.001)
        lf.rotation_euler = (tip - p - Vector((0, 0, 0.06))).to_track_quat('Z', 'Y').to_euler()


def soup_pot(p, yaw):
    R = Matrix.Rotation(yaw, 3, 'Z'); P = lambda x, y, z: p + R @ Vector((x, y, z))
    steel = solid('zp_steel', (0.55, 0.55, 0.57), 0.3, metal=1.0)
    o = cyl('zp_pot', P(0, 0, 0.035), 0.04, 0.07, steel, verts=24)
    cyl('zp_soup', P(0, 0, 0.066), 0.037, 0.004, solid('zp_soup', (0.6, 0.32, 0.1), 0.3), verts=24)
    for sg in (-1, 1):
        h = cyl('zp_pot_handle', P(sg * 0.046, 0, 0.06), 0.008, 0.004, steel, verts=12); h.rotation_euler = (R @ Matrix.Rotation(math.pi / 2, 3, 'X')).to_euler()
    limb(P(0.012, 0.0, 0.05), P(0.03, 0.012, 0.14), 0.0035, steel)        # the ladle's handle
    sphere('zp_ladle', P(0.008, -0.004, 0.05), 0.012, steel, 10, (1, 1, 0.6))
    for k in range(3):   # a stack of bowls beside it
        cyl('zp_bowl', P(-0.075, 0.0, 0.012 + k * 0.012), 0.028, 0.016, varied('zp_bowl', (0.9, 0.88, 0.82), 0.02, 0.35), verts=20, r2=0.018)
    return o


def place_all(sc, toward):
    """Clear each zoom window's sill and reveal, then put its thing there."""
    bpy.context.view_layer.update()
    for zid, spec in ZOOMS.items():
        for k, gp in enumerate(spec['glass']):
            g = find_glass(sc, gp)
            if g is None: print('ZOOM no glass for', zid, gp); continue
            c, t, n, w, h = frame_of(g, toward)
            bottom = c.z - h / 2
            if zid in ('firsts', 'lilies'): continue      # the boat's flower boxes and the bay keep what they have
            for o in list(sc.objects):
                if o.type not in ('MESH', 'CURVE') or o.name.startswith(('zp_', 'dt_', 'plush')): continue
                lo, hi = _bb(o); q = (lo + hi) / 2 - c
                along, out = q.dot(t), q.dot(n)
                if abs(along) < w / 2 + 0.06 and 0.005 < out < 0.25 and bottom - 0.02 < q.z + c.z < bottom + 0.3:
                    if o.name.split('.')[0] not in ('sill', 'shutter', 'louvre', 'voussoir', 'string', 'A', 'B', 'C', 'D', 'mull', 'pane', 'wc', 'wct', 'lintel'):
                        o.hide_render = True
            sp = c + n * 0.13 + Vector((0, 0, bottom - c.z - 0.005))
            yaw = math.atan2(n.y, n.x) + math.pi / 2
            if zid == 'robot': glass_of_water(sp + t * (w * 0.28))
            elif zid == 'watif': flip_calendar(sp - t * (w * 0.26), yaw)
            elif zid == 'saas': mug_and_notes(sp + t * (w * 0.25), yaw)
            elif zid == 'community': soup_pot(sp - t * (w * 0.22), yaw)
        if zid == 'lilies':
            g = find_glass(sc, spec['glass'][0])
            if g is not None:
                c, t, n, w, h = frame_of(g, toward)
                potted_lily(c + n * 0.02 - t * (w * 0.3) + Vector((0, 0, -h / 2 + 0.01)))


STREET_DIR = Vector((math.sin(math.radians(45)) * math.sin(math.radians(58)), -math.cos(math.radians(45)) * math.sin(math.radians(58)), math.cos(math.radians(58))))
