"""Small set pieces for the canal scene (canal_final.py): a bicycle, an owl
whose eyes the browser opens now and then, and a koi that jumps.

The owl and the fish are rendered twice: once into the main image (owl with
its eyes shut, no fish) and once more as small crops / frames that the
browser lays over the image (see src/canal/scene.ts)."""
import math, os, json
import bpy
from mathutils import Vector, Matrix
from kit import solid, varied, box, cyl, sphere, cut, node_mat, link


def limb(a, b, r, mat):
    """A straight rod from a to b (no taper)."""
    a, b = Vector(a), Vector(b); d = b - a
    c = cyl('rod', (a + b) / 2, r, max(d.length, 1e-4), mat, verts=8)
    c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return c


def _frame(origin, yaw, lean=0.0):
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(lean, 3, 'X')
    O = Vector(origin)
    return lambda x, y, z: O + R @ Vector((x, y, z)), R


def bicycle(origin, yaw, lean, iron, frame_col=(0.18, 0.3, 0.32), basket=True):
    """An old step-through town bike: spoked wheels, mudguards, a sprung
    saddle and a wicker basket with baguettes in it. Local frame: x along the
    bike (front = +x), z up; `lean` tips it onto its side (onto a wall)."""
    P, R = _frame(origin, yaw, lean)
    fm = solid('bike_paint', frame_col, 0.45, metal=0.3, coat=0.4)
    chrome = solid('bike_chrome', (0.75, 0.75, 0.72), 0.25, metal=1.0)
    rubber = solid('bike_tyre', (0.04, 0.04, 0.04), 0.8)
    leather = solid('bike_saddle', (0.32, 0.18, 0.1), 0.55)
    wr, wb = 0.155, 0.27            # wheel radius, half wheelbase
    for cx in (-wb, wb):
        c = P(cx, 0, wr)
        rot = (R @ Matrix.Rotation(math.pi / 2, 3, 'X')).to_euler()
        tyre = cyl('bike_tyre', c, wr, 0.022, rubber, verts=40, rot=rot)
        cut(tyre, cyl('bike_tyre_in', c, wr - 0.018, 0.1, None, verts=40, rot=rot))
        rim = cyl('bike_rim', c, wr - 0.017, 0.014, chrome, verts=40, rot=rot)
        cut(rim, cyl('bike_rim_in', c, wr - 0.027, 0.1, None, verts=40, rot=rot))
        cyl('bike_hub', c, 0.014, 0.04, chrome, verts=12, rot=rot)
        for k in range(16):
            a = k / 16 * 2 * math.pi
            off = 0.008 if k % 2 else -0.008
            limb(P(cx, off, wr), P(cx + math.cos(a) * (wr - 0.024), 0, wr + math.sin(a) * (wr - 0.024)), 0.0014, chrome)
        for k in range(9):          # mudguard over the top of each wheel
            a0, a1 = math.radians(20 + k * 15), math.radians(35 + k * 15)
            limb(P(cx + math.cos(a0) * (wr + 0.018), 0, wr + math.sin(a0) * (wr + 0.018)),
                 P(cx + math.cos(a1) * (wr + 0.018), 0, wr + math.sin(a1) * (wr + 0.018)), 0.012, fm)
    bb = P(-0.02, 0, 0.11)                       # bottom bracket
    seat = P(-0.12, 0, 0.42); head = P(0.2, 0, 0.42); head_lo = P(0.215, 0, 0.33)
    rear, front = P(-wb, 0, wr), P(wb, 0, wr)
    t = 0.011
    limb(bb, seat, t, fm)                         # seat tube
    limb(bb, head_lo, t, fm)                      # low step-through down tube
    limb(P(0.0, 0, 0.16), P(0.2, 0, 0.37), t * 0.85, fm)
    for sg in (-1, 1):
        limb(bb + R @ Vector((0, sg * 0.02, 0)), rear + R @ Vector((0, sg * 0.02, 0)), 0.007, fm)     # chain stays
        limb(seat + R @ Vector((0, sg * 0.02, -0.03)), rear + R @ Vector((0, sg * 0.02, 0)), 0.006, fm)  # seat stays
        limb(head_lo + R @ Vector((0, sg * 0.018, 0)), front + R @ Vector((0, sg * 0.018, 0)), 0.007, fm)  # fork
    limb(head_lo, head, 0.014, fm)                # head tube
    cyl('bike_chainring', bb, 0.05, 0.006, chrome, verts=24, rot=(R @ Matrix.Rotation(math.pi / 2, 3, 'X')).to_euler())
    limb(bb, P(-0.05, 0.04, 0.05), 0.006, chrome); box('bike_pedal', P(-0.05, 0.06, 0.05), (0.05, 0.03, 0.012), rubber, bevel=0)
    limb(bb + R @ Vector((0, 0.025, 0)), rear + R @ Vector((0, 0.025, 0)), 0.004, solid('bike_chain', (0.15, 0.14, 0.13), 0.5, metal=0.8))
    # seat post, sprung saddle
    sp = P(-0.14, 0, 0.5); limb(seat, sp, 0.008, chrome)
    sphere('bike_saddle', sp + R @ Vector((0, 0, 0.015)), 0.06, leather, 16, (1.3, 0.75, 0.3)).rotation_euler = R.to_euler()
    for sg in (-1, 1):
        cyl('bike_spring', sp + R @ Vector((-0.04, sg * 0.025, -0.005)), 0.008, 0.025, chrome, verts=8)
    # stem and swept-back handlebars, turned a little towards the wall
    st = P(0.18, 0, 0.53); limb(head, st, 0.009, chrome)
    turn = Matrix.Rotation(1.2, 3, 'Z')
    hb = lambda x, y, z: st + R @ (turn @ Vector((x, y, z)))
    pts = [hb(0.0, -0.2, 0.0), hb(-0.04, -0.17, 0.01), hb(-0.06, -0.08, 0.0), hb(0.0, 0.0, 0.0), hb(-0.06, 0.08, 0.0), hb(-0.04, 0.17, 0.01), hb(0.0, 0.2, 0.0)]
    for a, b in zip(pts[1:-1], pts[2:-1]):
        limb(a, b, 0.008, chrome)
    for g in (pts[1], pts[-2]):
        limb(g, g + R @ (turn @ Vector((-0.06, 0, -0.005))), 0.012, leather)
    sphere('bike_bell', hb(0.0, 0.05, 0.015), 0.012, chrome, 10)
    sphere('bike_lamp', P(0.25, 0, 0.47), 0.022, chrome, 12, (1.2, 1, 1))
    if basket:
        wick = varied('wicker', (0.5, 0.36, 0.2), 0.08, 0.85, bump=0.4, bump_scale=200.0)
        bc = P(0.31, 0, 0.43)
        bk = box('bike_basket', bc, (0.16, 0.2, 0.12), wick, bevel=0.01, rot=R.to_euler())
        cut(bk, box('bike_basket_in', bc + R @ Vector((0, 0, 0.02)), (0.14, 0.18, 0.12), None, bevel=0, rot=R.to_euler()))
        crust = varied('baguette', (0.72, 0.46, 0.2), 0.08, 0.7, bump=0.3, bump_scale=60.0)
        for k, (dy, tilt) in enumerate(((-0.04, 0.5), (0.02, 0.35), (0.06, 0.6))):
            a = bc + R @ Vector((-0.03, dy, -0.02)); b = bc + R @ Vector((0.05 + 0.02 * k, dy * 1.3, 0.22 + 0.03 * k))
            limb(a, b, 0.018, crust)
            sphere('baguette_end', b, 0.018, crust, 10)
        box('bike_paper', bc + R @ Vector((0, 0, 0.05)), (0.12, 0.16, 0.06), solid('paper_bag', (0.78, 0.7, 0.55), 0.9), bevel=0.004, rot=R.to_euler())


# ---------------------------------------------------------------- the owl
OWL = {}

def owl(p, face_yaw):
    """A small tawny owl, perched. Eyes shut in the main render; the browser
    swaps in crops with them open / glancing left / right / half shut."""
    P, R = _frame(p, face_yaw)
    feath = varied('owl_feather', (0.36, 0.26, 0.17), 0.06, 0.9, bump=0.5, bump_scale=160.0)
    pale = varied('owl_pale', (0.62, 0.52, 0.4), 0.05, 0.9, bump=0.4, bump_scale=200.0)
    dark = solid('owl_dark', (0.16, 0.11, 0.08), 0.85)
    beak = solid('owl_beak', (0.42, 0.38, 0.3), 0.4)
    iris = solid('owl_iris', (0.95, 0.62, 0.12), 0.25, emit=(0.95, 0.55, 0.1), strength=1.6)
    pupil = solid('owl_pupil', (0.01, 0.01, 0.01), 0.1, coat=1.0)
    glint = solid('owl_glint', (1, 1, 1), 0.1, emit=(1, 0.95, 0.9), strength=3.0)
    # local frame: +y = where the owl looks (towards the camera), z up
    sphere('owl_body', P(0, 0, 0.12), 0.1, feath, 24, (0.95, 0.85, 1.25))
    sphere('owl_belly', P(0, 0.035, 0.1), 0.075, pale, 20, (0.9, 0.7, 1.15))
    for k in range(7):  # chest streaks
        sphere('owl_streak', P(-0.04 + (k % 4) * 0.027, 0.1, 0.06 + (k // 4) * 0.05 + (k % 2) * 0.02), 0.009, dark, 8, (0.6, 0.4, 1.8))
    for sg in (-1, 1):
        w = sphere('owl_wing', P(sg * 0.085, -0.01, 0.12), 0.075, feath, 20, (0.35, 0.8, 1.35))
        w.rotation_euler = (R @ Matrix.Rotation(sg * -0.12, 3, 'Y')).to_euler()
        for k in range(3):
            sphere('owl_bar', P(sg * 0.105, 0.01 - k * 0.03, 0.08 + k * 0.035), 0.008, pale, 8, (0.5, 1.5, 0.5))
        for k in range(3):   # talons over the ridge
            limb(P(sg * 0.03 + (k - 1) * 0.012, 0.03, 0.005), P(sg * 0.03 + (k - 1) * 0.014, 0.055, -0.012), 0.005, beak)
    sphere('owl_tail', P(0, -0.07, 0.03), 0.04, feath, 12, (0.8, 1.4, 0.4))
    hc = P(0, 0.01, 0.255)
    sphere('owl_head', hc, 0.09, feath, 24, (1.12, 0.95, 0.9))
    for sg in (-1, 1):
        cyl('owl_tuft', P(sg * 0.06, 0.0, 0.325), 0.022, 0.065, feath, verts=8, r2=0.002, rot=(R @ Matrix.Rotation(sg * -0.35, 3, 'Y')).to_euler())
    face = sphere('owl_face', P(0, 0.07, 0.252), 0.075, pale, 24, (1.2, 0.32, 0.85)); face.rotation_euler = R.to_euler()
    eyes = []
    for sg in (-1, 1):
        ec = P(sg * 0.04, 0.086, 0.26)
        ring = sphere('owl_ring', P(sg * 0.04, 0.084, 0.26), 0.034, dark, 20, (1, 0.32, 1)); ring.rotation_euler = R.to_euler()
        sphere('owl_eye', ec, 0.026, iris, 24)
        pu = sphere('owl_pupil', ec + R @ Vector((0, 0.02, 0)), 0.014, pupil, 16, (1, 0.45, 1)); pu.rotation_euler = R.to_euler()
        gl = sphere('owl_glint', ec + R @ Vector((0.008, 0.025, 0.01)), 0.004, glint, 8)
        lid = sphere('owl_lid', ec, 0.0285, feath, 24)
        lid_line = sphere('owl_lidline', ec + R @ Vector((0, 0.027, -0.002)), 0.021, dark, 16, (1, 0.25, 0.1)); lid_line.rotation_euler = R.to_euler()
        eyes.append({'c': ec, 'pupil': pu, 'glint': gl, 'lid': lid, 'line': lid_line, 'sg': sg})
    cyl('owl_beak', P(0, 0.112, 0.232), 0.012, 0.032, beak, verts=8, r2=0.0, rot=(R @ Matrix.Rotation(math.radians(150), 3, 'X')).to_euler())
    OWL.update({'eyes': eyes, 'R': R, 'head': hc})


def owl_pose(state):
    """closed | open | left | right | half"""
    R = OWL['R']
    for e in OWL['eyes']:
        side = {'left': -1, 'right': 1}.get(state, 0)
        look = R @ Vector((0.012 * side, 0.02 - 0.003 * abs(side), 0))
        e['pupil'].location = e['c'] + look
        e['glint'].location = e['c'] + R @ Vector((0.008, 0.025, 0.01))
        shut = state == 'closed'
        e['lid'].hide_render = not (shut or state == 'half')
        e['line'].hide_render = not shut
        e['glint'].hide_render = shut
        e['pupil'].hide_render = shut
        e['lid'].location = e['c'] + R @ Vector((0, 0, 0.015 if state == 'half' else 0))


def crop_border(sc, cam, pts, pad_px=6):
    """Render border (0..1, Blender's bottom-up) around world points, snapped to whole pixels."""
    from bpy_extras.object_utils import world_to_camera_view
    W, H = sc.render.resolution_x, sc.render.resolution_y
    vs = [world_to_camera_view(sc, cam, Vector(p)) for p in pts]
    x0 = max(0, math.floor(min(v.x for v in vs) * W) - pad_px); x1 = min(W, math.ceil(max(v.x for v in vs) * W) + pad_px)
    y0 = max(0, math.floor(min(v.y for v in vs) * H) - pad_px); y1 = min(H, math.ceil(max(v.y for v in vs) * H) + pad_px)
    return x0, y0, x1, y1


def render_crop(sc, path, box_px, samples, transparent=False):
    W, H = sc.render.resolution_x, sc.render.resolution_y
    x0, y0, x1, y1 = box_px
    r = sc.render
    r.use_border = True; r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = x0 / W, x1 / W
    r.border_min_y, r.border_max_y = y0 / H, y1 / H
    old_t = r.film_transparent; r.film_transparent = transparent
    sc.cycles.samples = samples
    r.filepath = path
    bpy.ops.render.render(write_still=True)
    r.use_border = False; r.use_crop_to_border = False; r.film_transparent = old_t


# ---------------------------------------------------------------- the koi
def koi(name='koi'):
    """A koi about 0.24 long, built along +x with its belly at z=0, origin at
    the middle. Orange and white patches, scales, fins, an eye."""
    m, n, l, b = node_mat('koi_skin')
    tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 3
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB'); e0, e1 = ramp.color_ramp.elements
    e0.position, e1.position = 0.47, 0.53
    e0.color = (0.95, 0.32, 0.06, 1); e1.color = (0.92, 0.9, 0.86, 1)
    l.new(nz.outputs['Fac'], ramp.inputs['Fac']); l.new(ramp.outputs['Color'], b.inputs['Base Color'])
    vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 260.0
    l.new(tc.outputs['Object'], vo.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25; bp.inputs['Distance'].default_value = 0.002
    l.new(vo.outputs['Distance'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.28; b.inputs['Coat Weight'].default_value = 0.7
    fin = solid('koi_fin', (0.95, 0.75, 0.6), 0.4); fin.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.75
    eye = solid('koi_eye', (0.02, 0.02, 0.02), 0.1, coat=1.0)
    parts = []
    body = sphere(name + '_body', (0, 0, 0), 0.12, m, 32, (1.0, 0.3, 0.32)); parts.append(body)
    me = body.data
    for v in me.vertices:     # taper to the tail, flatten the belly a little
        t = (v.co.x / 0.12 + 1) / 2   # 0 tail .. 1 head
        k = 0.45 + 0.55 * math.sin(min(1, t * 1.15) * math.pi / 2)
        v.co.y *= k; v.co.z *= k
        if v.co.z < 0: v.co.z *= 0.85
    tail = sphere(name + '_tail', (-0.15, 0, 0.005), 0.05, fin, 16, (0.6, 0.06, 1.0)); parts.append(tail)
    dor = sphere(name + '_dorsal', (-0.01, 0, 0.035), 0.05, fin, 12, (1.0, 0.05, 0.35)); parts.append(dor)
    for sg in (-1, 1):
        pf = sphere(name + '_pec', (0.05, sg * 0.04, -0.02), 0.025, fin, 10, (1.0, 0.6, 0.08)); pf.rotation_euler = (sg * 0.5, 0.3, sg * 0.4); parts.append(pf)
        parts.append(sphere(name + '_eye', (0.09, sg * 0.022, 0.012), 0.006, eye, 8))
        parts.append(limb(Vector((0.115, sg * 0.006, -0.008)), Vector((0.14, sg * 0.012, -0.02)), 0.0015, fin))   # barbels
    root = bpy.data.objects.new(name, None); link(root)
    for o in parts: o.parent = root
    return root, parts


def koi_frames(sc, cam, out_dir, spots, others, samples=48, n=12):
    """Render a koi jump at each spot: n frames, everything else held out so
    only the fish (and its droplets) remain, on a transparent film."""
    from bpy_extras.object_utils import world_to_camera_view
    root, parts = koi()
    root.scale = (1.3, 1.3, 1.3)
    drop_m = solid('droplet', (0.85, 0.9, 0.95), 0.05, emit=(0.75, 0.8, 0.9), strength=0.35); drop_m.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.6
    for o in others: o.is_holdout = True
    W, H = sc.render.resolution_x, sc.render.resolution_y
    meta = []
    for si, (p0, ang) in enumerate(spots):
        p0 = Vector(p0); d = Vector((math.cos(ang), math.sin(ang), 0))
        L, hgt = 0.5, 0.26
        p1 = p0 + d * L
        pts = [p0 + d * L * s + Vector((0, 0, z)) for s in (0, 0.5, 1) for z in (-0.05, hgt + 0.1)]
        pts += [p0 - Vector((0.15, 0.15, 0)), p1 + Vector((0.15, 0.15, 0))]
        bx = crop_border(sc, cam, pts, 10)
        frames = []
        for fi in range(n):
            s = (fi + 0.5) / n
            pos = p0 + d * L * s + Vector((0, 0, hgt * 4 * s * (1 - s) - 0.03))
            slope = hgt * 4 * (1 - 2 * s) / L
            root.location = pos
            root.rotation_euler = (0, -math.atan(slope), ang)
            for o in parts:   # a little tail swish
                if o.name.startswith('koi_tail'): o.rotation_euler = (0, 0, 0.35 * math.sin(s * 9))
            drops = []
            for k in range(7):     # spray where it leaves and where it lands
                for (q, s0) in ((p0, 0.0), (p1, 0.92)):
                    age = s - s0
                    if 0 <= age < 0.25:
                        a = k / 7 * 6.28 + si
                        r = 0.03 + age * 0.4
                        drops.append(sphere('drop', q + Vector((math.cos(a) * r, math.sin(a) * r, 0.05 + age * 0.5 - age * age * 2.5)), 0.006 + 0.003 * (k % 3), drop_m, 8))
            render_crop(sc, os.path.join(out_dir, 'koi_%d_%02d.png' % (si, fi)), bx, samples, transparent=True)
            for o in drops: bpy.data.objects.remove(o)
            frames.append(fi)
        v0 = world_to_camera_view(sc, cam, p0); v1 = world_to_camera_view(sc, cam, p1)
        meta.append({'box': [bx[0] / W, 1 - bx[3] / H, bx[2] / W, 1 - bx[1] / H], 'n': n,
                     'from': [round(v0.x, 4), round(1 - v0.y, 4)], 'to': [round(v1.x, 4), round(1 - v1.y, 4)]})
    for o in others: o.is_holdout = False
    for o in parts + [root]: bpy.data.objects.remove(o)
    return meta
