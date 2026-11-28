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
  lilies     the red bay's front and side (rain) and the casement beside it (fire); nothing outside
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
    'robot':     {'glass': [(-3.45, 1.33, 3.16)], 'sill_out': 0.055, 'prop_scale': 1.3, 'arch': True, 'clip_keep': 0.172, 'clear_front': 0.15, 'W0': 1.55, 'W1': 1.2, 'elev': 0.1, 'lens': 20, 'arc': 0.6, 'teams': ['brita-robot']},   # the bakery stands close in front: a wide lens from the gap
    'watif':     {'glass': [(0.21, 2.33, 2.08)], 'W0': 1.55, 'W1': 1.25, 'elev': 0.12, 'teams': ['watif']},
    'saas':      {'glass': [(0.21, 2.33, 3.28)], 'W0': 1.55, 'W1': 1.25, 'elev': 0.12, 'teams': ['saas']},
    # the red bay's front and side glass (rain) and the casement to its right (fire)
    'lilies':    {'glass': [(3.49, -0.14, 1.97), (3.79, 0.01, 1.97), (4.26, 0.28, 1.95)], 'frame': False, 'frost_out': 0.002, 'keep_mull': [False, False, True],
                  'W0': 2.3, 'W1': 1.95, 'elev': 0.16, 'side': 0.45,
                  'teams': ['lily-and-rain', 'lily-and-rain', 'lily-and-fire']},
    # the bakery's canal side, two windows: North Vancouver (soup) and the WUSA committee
    'community': {'glass': [(-2.93, -2.42, 0.83), (-2.93, -1.47, 0.83)], 'prop_scale': 1.55, 'W0': 2.2, 'W1': 2.05, 'elev': 0.22,
                  'teams': ['community', 'wusa'],
                  'hide_box': [(-3.0, -2.2, -2.15, -0.4, 0.0, 1.7)]},   # the poster and bike that hid the WUSA window   # the bakery's canal side: open water in front
}
GLASS_NAMES = ('pane', 'bay_glass', 'win_glass', 'shop_glass')
PROP_AT = {}     # where each zoom's sill thing stands (for the browser's steam etc.)


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
def lathe(name, prof, mat, loc, verts=48, smooth=True):
    """A solid of revolution: prof is [(radius, height), ...] going round the
    outline from the axis, out and up the outside, back down the inside, to
    the axis again. Spun into one closed, manifold surface."""
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for (r, z) in prof]
    es = [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:])]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=verts, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if smooth:
        for f in me.polygons: f.use_smooth = True
    o = link(bpy.data.objects.new(name, me)); o.location = loc
    if mat: o.data.materials.append(mat)
    return o


def _clear_glass(name, ior=1.5, tint=(0.96, 0.98, 1.0), alpha=0.12):
    """See-through glass that doesn't depend on light bounces (the street's
    render keeps those few): mostly transparent, with a clear-coat sheen and
    sharp highlights, faintly tinted."""
    m = solid(name, tint, 0.02)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Alpha'].default_value = alpha; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.02
    b.inputs['Specular IOR Level'].default_value = 0.8
    return m


def glass_of_water(p):
    """A heavy tumbler, three-quarters full: thick base, real wall thickness,
    water with a meniscus, so it refracts the window behind it like the real thing."""
    g = _clear_glass('zp_glass2', 1.5, (0.92, 0.96, 0.98), 0.14)
    water = _clear_glass('zp_water2', 1.333, (0.5, 0.72, 0.92), 0.2)
    R0, R1, H = 0.024, 0.028, 0.095     # base and rim radius, height
    wall = 0.0022
    prof = [(0.0, 0.0), (R0 - 0.002, 0.0), (R0, 0.002), (R0 + (R1 - R0) * 0.5, H * 0.5), (R1, H), (R1 - wall, H),
            (R1 - wall - (R1 - R0) * 0.5, H * 0.5), (R0 - wall, 0.012), (0.0, 0.012)]
    o = lathe('zp_glass', prof, g, p)
    lvl = H * 0.74
    rt = R0 - wall + (R1 - R0) * (lvl - 0.012) / (H - 0.012) - 0.0003
    wprof = [(0.0, 0.0121), (R0 - wall - 0.0003, 0.0121), (rt, lvl - 0.0015), (rt - 0.0006, lvl), (rt * 0.7, lvl - 0.0004), (0.0, lvl - 0.0005)]
    lathe('zp_water', wprof, water, p)
    # a cork coaster under it, so it stands out from the stone
    cyl('zp_coaster', p + Vector((0, 0, -0.0015)), 0.04, 0.003, varied('zp_cork', (0.55, 0.38, 0.22), 0.1, 0.9, bump=0.6, bump_scale=300), verts=40)
    # a small light on it so the glass catches a highlight
    L = bpy.data.lights.new('zp_glint', 'POINT'); L.energy = 0.25; L.color = (1.0, 0.9, 0.75); L.shadow_soft_size = 0.01
    link(bpy.data.objects.new('zp_glint', L)).location = p + Vector((0.06, -0.12, 0.16))
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
    """A bowl of soup, steaming hot: a glazed stoneware bowl full of tomato
    soup with a swirl of cream, a spoon resting in it, a torn hunk of bread
    beside it on a folded cloth. Unmistakably a meal someone's been given."""
    R = Matrix.Rotation(yaw, 3, 'Z'); P = lambda x, y, z: p + R @ Vector((x, y, z))
    glaze = solid('zp_glaze', (0.16, 0.3, 0.42), 0.18, coat=0.6)
    inside = solid('zp_glaze_in', (0.88, 0.84, 0.76), 0.2, coat=0.6)
    soup = solid('zp_soup2', (0.7, 0.16, 0.04), 0.4)
    cream = solid('zp_cream', (0.95, 0.9, 0.8), 0.3)
    cloth = varied('zp_cloth', (0.78, 0.2, 0.16), 0.05, 0.9, bump=0.5, bump_scale=600)
    bread = varied('zp_bread', (0.72, 0.46, 0.2), 0.12, 0.8, bump=1.0, bump_scale=120)
    crumb = varied('zp_crumb', (0.92, 0.84, 0.66), 0.06, 0.9, bump=1.0, bump_scale=400)
    steel = solid('zp_spoon', (0.75, 0.75, 0.77), 0.15, metal=1.0)
    # the cloth, folded square under everything
    box('zp_cloth', P(-0.005, 0.0, 0.002), (0.13, 0.09, 0.004), cloth, bevel=0.002)
    # the bowl: a foot ring, a rounded body, a rolled rim; glazed blue outside, cream inside
    c = P(0.018, 0.0, 0.004)
    lathe('zp_bowl', [(0.0, 0.0), (0.016, 0.0), (0.017, 0.004), (0.022, 0.006), (0.034, 0.016), (0.041, 0.03), (0.043, 0.036),
                      (0.0425, 0.039), (0.04, 0.038), (0.037, 0.03), (0.03, 0.017), (0.016, 0.009), (0.0, 0.008)], glaze, c)
    lathe('zp_soup', [(0.0, 0.026), (0.0352, 0.026), (0.0383, 0.0345), (0.0, 0.0345)], soup, c)
    # a swirl of cream on top
    for k in range(10):
        a_ = k * 0.6; rr = 0.004 + k * 0.0022
        sphere('zp_cream', c + R @ Vector((rr * math.cos(a_), rr * math.sin(a_), 0.0347)), 0.0032, cream, 8, (1.2, 1.2, 0.18))
    # the spoon: bowl in the soup, handle up over the rim
    sphere('zp_spoon_bowl', P(0.01, -0.004, 0.034), 0.009, steel, 14, (1.4, 1.0, 0.25))
    limb(P(0.018, -0.006, 0.035), P(0.07, -0.022, 0.06), 0.0022, steel)
    # a torn hunk of bread: crust round, open crumb on the torn face
    bc = P(-0.05, 0.012, 0.004)
    sphere('zp_bread', bc + R @ Vector((0, 0, 0.014)), 0.026, bread, 18, (1.25, 0.9, 0.62))
    sphere('zp_crumb', bc + R @ Vector((0.022, 0.0, 0.014)), 0.016, crumb, 14, (0.35, 0.85, 0.8))
    for k in range(3):   # score marks across the crust
        b_ = box('zp_score', bc + R @ Vector((-0.012 + k * 0.011, 0, 0.03)), (0.003, 0.03, 0.002), solid('zp_score', (0.42, 0.24, 0.1), 0.85), bevel=0.001)
        b_.rotation_euler = (R @ Matrix.Rotation(0.5, 3, 'Z')).to_euler()
    return c


def committee_papers(p, yaw):
    """A committee member's things: the meeting papers squared up in a stack
    with a black binder clip, the top sheet printed (lines of text and a small
    green leaf, the sustainability position), a pen across it, and a folded
    name card standing beside."""
    R = Matrix.Rotation(yaw, 3, 'Z'); P = lambda x, y, z: p + R @ Vector((x, y, z)); rot = lambda m=Matrix.Identity(3): (R @ m).to_euler()
    paper = varied('zp_paper2', (0.93, 0.92, 0.88), 0.02, 0.8)
    ink = solid('zp_ink2', (0.12, 0.12, 0.14), 0.6)
    for k in range(9):   # the stack, a little ragged
        b_ = box('zp_sheet', P(0.004 * math.sin(k * 2.1), 0.003 * math.cos(k * 1.7), 0.0015 + k * 0.0022), (0.085, 0.11, 0.0018), paper, bevel=0)
        b_.rotation_euler = rot(Matrix.Rotation(0.03 * math.sin(k * 1.3), 3, 'Z'))
    ztop = 0.0015 + 9 * 0.0022
    b_ = box('zp_text', P(0.0, 0.042, ztop + 0.0002), (0.05, 0.007, 0.0004), ink, bevel=0); b_.rotation_euler = rot()   # the heading
    for r in range(8):   # lines of text
        L = 0.066 if r % 3 != 2 else 0.042
        b_ = box('zp_text', P(-0.002 - (0.066 - L) / 2, 0.026 - r * 0.0085, ztop + 0.0002), (L, 0.0022, 0.0004), solid('zp_ink_g', (0.35, 0.35, 0.37), 0.6), bevel=0); b_.rotation_euler = rot()
    leaf = solid('zp_leafmark', (0.18, 0.5, 0.2), 0.5)
    sphere('zp_leafmark', P(0.03, 0.043, ztop + 0.0004), 0.006, leaf, 8, (1.6, 0.8, 0.12))
    # a black binder clip on the top edge, its silver arms folded back
    b_ = box('zp_clip', P(0.0, 0.054, ztop - 0.006), (0.03, 0.006, 0.016), solid('zp_clipk', (0.04, 0.04, 0.045), 0.35), bevel=0.002); b_.rotation_euler = rot()
    steel = solid('zp_clipwire', (0.75, 0.75, 0.78), 0.2, metal=1.0)
    for sg in (-1, 1):
        limb(P(sg * 0.012, 0.054, ztop + 0.002), P(sg * 0.012, 0.04, ztop + 0.003), 0.0012, steel)
    # a pen across the stack
    limb(P(-0.035, -0.04, ztop + 0.004), P(0.04, -0.02, ztop + 0.004), 0.0035, solid('zp_pen', (0.08, 0.15, 0.4), 0.3))
    limb(P(0.04, -0.02, ztop + 0.004), P(0.047, -0.018, ztop + 0.004), 0.0022, steel)
    # a folded name card standing beside it: white, with a dark band where a name would be
    for sg in (-1, 1):
        b_ = box('zp_tent', P(0.085, sg * 0.009, 0.017), (0.07, 0.0016, 0.036), paper, bevel=0)
        b_.rotation_euler = rot(Matrix.Rotation(sg * 0.42, 3, 'X'))
    b_ = box('zp_tent_band', P(0.085, -0.0175, 0.02), (0.05, 0.0006, 0.008), ink, bevel=0); b_.rotation_euler = rot(Matrix.Rotation(-0.42, 3, 'X'))
    return p


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
            sp = c + n * spec.get('sill_out', 0.13) + Vector((0, 0, bottom - c.z - 0.005))
            yaw = math.atan2(n.y, n.x) + math.pi / 2
            before = set(bpy.data.objects.keys())
            if zid == 'robot': at = sp + t * (w * 0.2); glass_of_water(at)
            elif zid == 'watif': at = sp - t * (w * 0.26); flip_calendar(at, yaw)
            elif zid == 'saas': at = sp + t * (w * 0.25); mug_and_notes(at, yaw)
            elif zid == 'community' and k == 0: at = sp - t * (w * 0.12); soup_pot(at, yaw)
            elif zid == 'community': at = sp + t * (w * 0.05); committee_papers(at, yaw)
            else: continue
            if zid not in PROP_AT: PROP_AT[zid] = at.copy()
            k_ = spec.get('prop_scale', 1.0)
            if k_ != 1.0:   # scale the whole set about where it stands
                bpy.context.view_layer.update()        # so matrix_world reflects where they were just put
                M = Matrix.Translation(at) @ Matrix.Scale(k_, 4) @ Matrix.Translation(-at)
                for nm in set(bpy.data.objects.keys()) - before:
                    o = bpy.data.objects[nm]
                    if o.parent is None: o.matrix_world = M @ o.matrix_world
                if zid == 'community' and k == 0: PROP_AT[zid] = at + Vector((0, 0, 0.045 * k_))   # the steam rises from the bowl
                if zid == 'robot': PROP_AT[zid] = at + Vector((0, 0, 0.1 * k_))


STREET_DIR = Vector((math.sin(math.radians(45)) * math.sin(math.radians(58)), -math.cos(math.radians(45)) * math.sin(math.radians(58)), math.cos(math.radians(58))))
