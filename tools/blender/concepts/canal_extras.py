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

def _feather_material():
    """Tawny owl plumage: warm brown, darker mottling and streaks, paler
    underneath (by which way the surface faces), soft sheen."""
    name = 'owl_plumage'
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Normal'], sep.inputs['Vector'])
    sepo = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sepo.inputs['Vector'])
    under = n.new('ShaderNodeMapRange'); under.inputs['From Min'].default_value = 0.0; under.inputs['From Max'].default_value = 0.07
    l.new(sepo.outputs['Y'], under.inputs['Value'])
    base = n.new('ShaderNodeMix'); base.data_type = 'RGBA'
    base.inputs['A'].default_value = (0.5, 0.34, 0.2, 1); base.inputs['B'].default_value = (0.72, 0.6, 0.45, 1)
    l.new(under.outputs['Result'], base.inputs['Factor'])
    # streaks down the chest (stretched noise) and blotchy mottling
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (90, 90, 18)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    st = n.new('ShaderNodeTexNoise'); st.inputs['Detail'].default_value = 4
    l.new(mp.outputs['Vector'], st.inputs['Vector'])
    stc = n.new('ShaderNodeMapRange'); stc.inputs['From Min'].default_value = 0.55; stc.inputs['From Max'].default_value = 0.7
    l.new(st.outputs['Fac'], stc.inputs['Value'])
    streak = n.new('ShaderNodeMix'); streak.data_type = 'RGBA'
    l.new(stc.outputs['Result'], streak.inputs['Factor']); l.new(base.outputs['Result'], streak.inputs['A'])
    streak.inputs['B'].default_value = (0.16, 0.1, 0.06, 1)
    mot = n.new('ShaderNodeTexVoronoi'); mot.inputs['Scale'].default_value = 70
    l.new(tc.outputs['Object'], mot.inputs['Vector'])
    mc = n.new('ShaderNodeMapRange'); mc.inputs['From Min'].default_value = 0.0; mc.inputs['From Max'].default_value = 0.35
    mc.inputs['To Min'].default_value = 0.35; mc.inputs['To Max'].default_value = 0.0
    l.new(mot.outputs['Distance'], mc.inputs['Value'])
    mott = n.new('ShaderNodeMix'); mott.data_type = 'RGBA'
    l.new(mc.outputs['Result'], mott.inputs['Factor']); l.new(streak.outputs['Result'], mott.inputs['A'])
    mott.inputs['B'].default_value = (0.75, 0.66, 0.52, 1)
    headz = n.new('ShaderNodeMapRange'); headz.inputs['From Min'].default_value = 0.19; headz.inputs['From Max'].default_value = 0.22
    l.new(sepo.outputs['Z'], headz.inputs['Value'])
    facing = n.new('ShaderNodeMapRange'); facing.inputs['From Min'].default_value = 0.07; facing.inputs['From Max'].default_value = 0.09
    l.new(sepo.outputs['Y'], facing.inputs['Value'])
    disc = n.new('ShaderNodeMath'); disc.operation = 'MULTIPLY'
    l.new(headz.outputs['Result'], disc.inputs[0]); l.new(facing.outputs['Result'], disc.inputs[1])
    ringf = n.new('ShaderNodeMapRange'); ringf.inputs['From Min'].default_value = 0.05; ringf.inputs['From Max'].default_value = 0.068
    l.new(sepo.outputs['Y'], ringf.inputs['Value'])
    ringb = n.new('ShaderNodeMath'); ringb.operation = 'SUBTRACT'
    l.new(ringf.outputs['Result'], ringb.inputs[0]); l.new(facing.outputs['Result'], ringb.inputs[1])
    ring = n.new('ShaderNodeMath'); ring.operation = 'MULTIPLY'
    l.new(ringb.outputs['Value'], ring.inputs[0]); l.new(headz.outputs['Result'], ring.inputs[1])
    withring = n.new('ShaderNodeMix'); withring.data_type = 'RGBA'
    l.new(ring.outputs['Value'], withring.inputs['Factor']); l.new(mott.outputs['Result'], withring.inputs['A'])
    withring.inputs['B'].default_value = (0.22, 0.14, 0.08, 1)
    face = n.new('ShaderNodeMix'); face.data_type = 'RGBA'
    l.new(disc.outputs['Value'], face.inputs['Factor']); l.new(withring.outputs['Result'], face.inputs['A'])
    face.inputs['B'].default_value = (0.8, 0.7, 0.56, 1)
    l.new(face.outputs['Result'], b.inputs['Base Color'])
    fz = n.new('ShaderNodeTexNoise'); fz.inputs['Scale'].default_value = 600; fz.inputs['Detail'].default_value = 3
    l.new(tc.outputs['Object'], fz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.002
    l.new(fz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.8
    b.inputs['Sheen Weight'].default_value = 0.9; b.inputs['Sheen Roughness'].default_value = 0.35
    return m


def _metaball_mesh(name, mb, loc, rot, mat):
    """Build a metaball object, then bake it to a real mesh (hair needs one)."""
    tmp = link(bpy.data.objects.new(name + '_mb', mb))
    tmp.location = loc; tmp.rotation_euler = rot
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    for p in me.polygons: p.use_smooth = True
    me.materials.clear(); me.materials.append(mat)
    return o


def _fluff(o, count, length, mat, seed=0):
    """Short soft hair over a mesh: fluffy down and feather edges."""
    ps = o.modifiers.new('fluff', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.type = 'HAIR'; st.count = count; st.hair_length = length
    # the same short down everywhere, lying back and down like feathers
    st.use_advanced_hair = True
    st.normal_factor = length * 0.8; st.object_align_factor = (0, -length * 0.25, -length * 0.55)
    st.tangent_factor = 0.0; st.factor_random = length * 0.12
    st.child_type = 'INTERPOLATED'; st.rendered_child_count = 9; st.child_percent = 9
    st.child_radius = 0.12; st.clump_factor = 0.25; st.clump_shape = -0.3
    st.roughness_1 = length * 0.18; st.roughness_endpoint = length * 0.12
    st.root_radius = 0.0007; st.tip_radius = 0.0; st.radius_scale = 1.0
    st.use_hair_bspline = True
    ps.seed = seed
    return ps


OWL = {}

def owl(p, face_yaw, s=1.5):
    """A small tawny owl, perched: a soft feathered body (metaballs baked to
    a mesh, then a coat of short fluff), a pale heart-shaped facial disc with a
    dark rim, big amber eyes with large pupils and a catch light, a hooked
    beak, ear tufts, barred wings and talons over the ridge. Eyes shut in the
    main render; the browser swaps in crops with them open."""
    R = Matrix.Rotation(face_yaw, 3, 'Z'); O = Vector(p)
    P = lambda x, y, z: O + R @ (Vector((x, y, z)) * s)
    plum = _feather_material()
    pale = varied('owl_pale', (0.6, 0.48, 0.35), 0.04, 0.9, bump=0.5, bump_scale=300)
    rim = varied('owl_rim', (0.3, 0.2, 0.12), 0.04, 0.85, bump=0.4, bump_scale=300)
    beak = solid('owl_beak', (0.45, 0.4, 0.3), 0.35, coat=0.4)
    iris = solid('owl_iris', (0.98, 0.62, 0.08), 0.2, emit=(0.95, 0.5, 0.05), strength=0.35, coat=1.0)
    pupil = solid('owl_pupil', (0.004, 0.004, 0.004), 0.05, coat=1.0)
    glint = solid('owl_glint', (1, 1, 1), 0.05, emit=(1, 0.97, 0.92), strength=5.0)
    # body: one soft shape (local frame: +y = where it looks, z up)
    mb = bpy.data.metaballs.new('owlbody'); mb.resolution = 0.004; mb.render_resolution = 0.004; mb.threshold = 0.6
    def ball(c, r, size=None, stiff=2.0):
        e = mb.elements.new(); e.co = Vector(c); e.radius = r; e.stiffness = stiff
        if size: e.type = 'ELLIPSOID'; e.size_x, e.size_y, e.size_z = size
    ball((0, 0.0, 0.11), 0.11, (0.9, 0.85, 1.15))          # body
    ball((0, 0.03, 0.08), 0.085, (0.85, 0.7, 1.0))         # belly
    ball((0, 0.005, 0.255), 0.1, (1.12, 0.95, 0.9), 2.4)   # head, big and round
    for sg in (-1, 1):
        ball((sg * 0.07, -0.015, 0.12), 0.075, (0.4, 0.85, 1.25), 1.6)   # folded wings
        ball((sg * 0.03, 0.03, 0.01), 0.03, (0.9, 1.0, 0.6), 1.4)       # feathered feet
    ball((0, -0.07, 0.03), 0.045, (0.6, 1.2, 0.4), 1.4)                  # tail
    for sg in (-1, 1):
        ball((sg * 0.058, -0.005, 0.33), 0.03, (0.75, 0.6, 1.3), 1.4)   # soft ear tufts
    body = _metaball_mesh('owl_body', mb, O, (0, 0, face_yaw), plum)
    body.scale = (s, s, s)
    bpy.data.metaballs.remove(mb)
    _fluff(body, 4200, 0.0085 * s, plum, seed=3)
    # a few pale bars across each folded wing
    for sg in (-1, 1):
        for k in range(4):
            q = P(sg * 0.085, 0.0 - 0.006 * k, 0.16 - k * 0.03)
            sphere('owl_bar', q, 0.009 * s, pale, 10, (0.35, 1.3, 0.5))
    # eyes: big amber irises, large pupils, a catch light, lids for shut
    eyes = []
    E = 1.32      # eyes a size up: rounder, more owlish
    for sg in (-1, 1):
        ec = P(sg * 0.043, 0.082, 0.262)
        eye = sphere('owl_eye', ec, 0.024 * E * s, iris, 32, (1, 0.42, 1)); eye.rotation_euler = R.to_euler()
        rg = sphere('owl_eye_rim', ec - R @ Vector((0, 0.002, 0)) * E * s, 0.0265 * E * s, solid('owl_eyerim', (0.1, 0.065, 0.04), 0.7), 24, (1, 0.4, 1)); rg.rotation_euler = R.to_euler()
        pu = sphere('owl_pupil', ec + R @ Vector((0, 0.0085, 0)) * E * s, 0.0155 * E * s, pupil, 24, (1, 0.28, 1)); pu.rotation_euler = R.to_euler()
        gl = sphere('owl_glint', ec + R @ Vector((0.007, 0.012, 0.009)) * E * s, 0.0042 * E * s, glint, 10)
        lid = sphere('owl_lid', ec + R @ Vector((0, 0.001, 0)) * E * s, 0.0255 * E * s, plum, 32, (1.03, 0.3, 1.03)); lid.rotation_euler = R.to_euler()
        line = sphere('owl_lidline', ec + R @ Vector((0, 0.006, -0.004)) * E * s, 0.019 * E * s, solid('owl_crease', (0.07, 0.045, 0.03), 0.7), 16, (1, 0.35, 0.16)); line.rotation_euler = R.to_euler()
        # half-open: just the lower half of the eye (iris and pupil), cut flat across the top
        cutter = box('owl_halfcut', ec + Vector((0, 0, 0.03 * s)), (0.2 * s, 0.2 * s, 0.06 * s), None, bevel=0)
        cutter.hide_render = True; cutter.hide_viewport = True
        halves = []
        for src, nm in ((eye, 'owl_eye_low'), (pu, 'owl_pupil_low'), (rg, 'owl_rim_low')):
            hv = src.copy(); hv.data = src.data.copy(); hv.name = nm; link(hv)
            bo = hv.modifiers.new('half', 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cutter
            hv.hide_render = True; halves.append(hv)
        eyes.append({'c': ec, 'pupil': pu, 'glint': gl, 'lid': lid, 'line': line, 'eye': eye, 'rim': rg, 'halves': halves, 'sg': sg})
    # hooked beak
    bk0 = P(0, 0.1, 0.245)
    b_ = cyl('owl_beak', bk0 + R @ Vector((0, 0.008, -0.01)) * s, 0.009 * s, 0.03 * s, beak, verts=10, r2=0.0)
    b_.rotation_euler = (R @ Matrix.Rotation(math.radians(155), 3, 'X')).to_euler()
    # talons over the ridge
    for sg in (-1, 1):
        for k in range(3):
            a = P(sg * 0.03 + (k - 1) * 0.011, 0.045, 0.0); b2 = P(sg * 0.03 + (k - 1) * 0.013, 0.065, -0.018)
            t = cyl('owl_talon', (a + b2) / 2, 0.003 * s, (b2 - a).length, solid('owl_talon', (0.12, 0.1, 0.09), 0.3, coat=0.5), verts=6, r2=0.0005)
            t.rotation_euler = (b2 - a).to_track_quat('Z', 'Y').to_euler()
    OWL.update({'eyes': eyes, 'R': R, 'head': P(0, 0.01, 0.26), 's': s * E})


def owl_pose(state):
    """closed | open | left | right | half"""
    R, s = OWL['R'], OWL['s']
    for e in OWL['eyes']:
        side = {'left': -1, 'right': 1}.get(state, 0)
        e['pupil'].location = e['c'] + R @ Vector((0.009 * side, 0.0085 - 0.001 * abs(side), 0)) * s
        e['glint'].location = e['c'] + R @ Vector((0.007, 0.012, 0.009)) * s
        shut = state == 'closed'
        half = state == 'half'
        e['lid'].hide_render = True
        e['eye'].hide_render = shut or half; e['rim'].hide_render = shut or half
        for hv in e['halves']: hv.hide_render = not half
        e['line'].hide_render = not shut
        e['glint'].hide_render = shut or half
        e['pupil'].hide_render = shut or half
        e['lid'].location = e['c'] + R @ Vector((0, 0.001, 0.013 if state == 'half' else 0)) * s


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


# ---------------------------------------------------------------- patterned cloth
def _img(name, w, h, fn):
    """A small texture drawn pixel by pixel: fn(x, y) -> (r, g, b), y from the top."""
    img = bpy.data.images.new(name, w, h)
    px = [0.0] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            c = fn(x, h - 1 - y)
            i = (y * w + x) * 4
            px[i] = c[0]; px[i + 1] = c[1]; px[i + 2] = c[2]; px[i + 3] = 1.0
    img.pixels = px
    return img


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _soft(d, r, w=0.9):
    """1 inside a radius, 0 outside, with a soft pixel edge."""
    return max(0.0, min(1.0, (r - d) / w + 0.5))


PATTERNS = {}
def pattern(kind, w=64, h=128):
    """Cloth patterns for bunting and banners: florals, stars, chevrons,
    dots, ticking stripes, a scalloped fan."""
    if kind in PATTERNS: return PATTERNS[kind]
    cream, navy, gold, rose, sage, rust, ink = (0.92, 0.86, 0.72), (0.1, 0.14, 0.28), (0.85, 0.65, 0.25), (0.75, 0.35, 0.38), (0.45, 0.58, 0.45), (0.65, 0.28, 0.15), (0.12, 0.1, 0.1)
    def floral(x, y):
        cx, cy = (x % 32) - 16, (y % 32) - 16
        ox, oy = ((x + 16) % 32) - 16, ((y + 16) % 32) - 16
        d = math.hypot(cx, cy); a = math.atan2(cy, cx)
        petal = _soft(d, 7 + 3 * math.cos(a * 5), 1.2)
        c = _lerp(navy, rose, petal); c = _lerp(c, gold, _soft(d, 2.6))
        leaf = _soft(math.hypot(ox * 0.6, oy * 1.4), 3.5)
        return _lerp(c, sage, leaf * (1 - petal))
    def stars(x, y):
        cx, cy = (x % 24) - 12, (y % 24) - 12
        d = math.hypot(cx, cy); a = math.atan2(cy, cx)
        star = _soft(d, 3.0 + 2.2 * (0.5 + 0.5 * math.cos(a * 5)) ** 3, 0.8)
        moon = _soft(math.hypot(((x + 12) % 48) - 24, ((y + 30) % 48) - 24), 6) * (1 - _soft(math.hypot(((x + 14) % 48) - 24 + 3, ((y + 30) % 48) - 24 - 2), 6))
        return _lerp(_lerp(navy, gold, star), cream, moon)
    def chevron(x, y):
        v = (y + abs((x % 16) - 8)) % 16
        return rust if v < 5 else cream if v < 8 else gold if v < 10 else cream
    def dots(x, y):
        cx, cy = (x % 14) - 7, (y % 14) - 7
        ox, oy = ((x + 7) % 14) - 7, ((y + 7) % 14) - 7
        return _lerp(sage, cream, max(_soft(math.hypot(cx, cy), 2.6), _soft(math.hypot(ox, oy), 1.4)))
    def ticking(x, y):
        m = x % 16
        return navy if m in (2, 3) else rust if m == 9 else cream
    def fan(x, y):
        cx, cy = (x % 20) - 10, (y % 14)
        r = math.hypot(cx, cy + 4)
        band = int(r / 3) % 2
        return _lerp(rose if band else cream, gold, _soft(abs(r - 13), 0.8))
    fn = {'floral': floral, 'stars': stars, 'chevron': chevron, 'dots': dots, 'ticking': ticking, 'fan': fan}[kind]
    img = _img('pat_' + kind, w, h, fn)
    m, n, l, b = node_mat('cloth_' + kind)
    t = n.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Linear'
    l.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85; b.inputs['Sheen Weight'].default_value = 0.4
    b.inputs['Subsurface Weight'].default_value = 0.15     # cloth glows a little when lamps are behind it
    PATTERNS[kind] = m
    return m


def _quad(name, pts, uvs, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], [], [tuple(range(len(pts)))])
    uv = me.uv_layers.new()
    for i, c in enumerate(uvs): uv.data[i].uv = c
    o = link(bpy.data.objects.new(name, me)); me.materials.append(mat)
    sol = o.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.003
    return o


def bunting(a, b, n, kinds, sag=0.18, drop=0.13, string=None):
    """A string of pennants across a gap, each flag a different pattern."""
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, k / 40) + Vector((0, 0, -sag * 4 * (k / 40) * (1 - k / 40))) for k in range(41)]
    sm = string or solid('bunting_string', (0.85, 0.8, 0.7), 0.8)
    for p, q in zip(pts, pts[1:]):
        d = q - p
        c = cyl('bunting_string', (p + q) / 2, 0.0025, d.length, sm, verts=5)
        c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    for k in range(n):
        t0 = (k + 0.15) / n; t1 = (k + 0.85) / n
        p0 = a.lerp(b, t0) + Vector((0, 0, -sag * 4 * t0 * (1 - t0)))
        p1 = a.lerp(b, t1) + Vector((0, 0, -sag * 4 * t1 * (1 - t1)))
        tip = (p0 + p1) / 2 + Vector((0, 0, -drop))
        _quad('pennant', [p0, p1, tip], [(0, 1), (1, 1), (0.5, 0)], pattern(kinds[k % len(kinds)]))


def banner(top, along, kind, w=0.22, h=0.6, pole=None):
    """A long cloth banner hung from a short pole sticking out of a wall:
    `top` is where the pole meets the wall, `along` the way it sticks out."""
    top = Vector(top); along = Vector(along).normalized()
    pm = pole or solid('banner_pole', (0.2, 0.16, 0.1), 0.5, metal=0.4)
    end = top + along * (w + 0.06)
    c = cyl('banner_pole', (top + end) / 2, 0.008, (end - top).length, pm, verts=8)
    c.rotation_euler = (end - top).to_track_quat('Z', 'Y').to_euler()
    sphere('banner_finial', end, 0.016, solid('brass_f', (0.8, 0.6, 0.3), 0.3, metal=1.0), 8)
    p0 = top + along * 0.04; p1 = p0 + along * w
    dn = Vector((0, 0, -h))
    # swallowtail bottom
    _quad('banner', [p0, p1, p1 + dn, (p0 + p1) / 2 + dn * 0.86, p0 + dn], [(0, 1), (1, 1), (1, 0), (0.5, 0.14), (0, 0)], pattern(kind))
    box('banner_hem', (p0 + p1) / 2 + Vector((0, 0, -0.008)), (max(abs(p1.x - p0.x), 0.01), max(abs(p1.y - p0.y), 0.01), 0.016), solid('hem', (0.75, 0.6, 0.3), 0.6), bevel=0)


# ---------------------------------------------------------------- floating lanterns
def floating_lantern(p, yaw=0.0, kind='floral', s=1.0, energy=7.0):
    """A paper lantern let float on the canal: a little cedar raft, a tapered
    paper body on a light wooden frame with a pattern pressed into the paper,
    a candle inside. Warm and soft."""
    p = Vector(p); R = Matrix.Rotation(yaw, 3, 'Z')
    P = lambda x, y, z: p + R @ (Vector((x, y, z)) * s)
    cedar = solid('lantern_raft', (0.45, 0.28, 0.16), 0.6)
    frame = solid('lantern_frame', (0.32, 0.2, 0.12), 0.5)
    # raft of four slats with cross-pieces
    for k in range(4):
        box('raft_slat', P(-0.075 + k * 0.05, 0, 0.012), (0.045 * s, 0.2 * s, 0.018 * s), cedar, bevel=0.003, rot=R.to_euler())
    for sg in (-1, 1):
        box('raft_cross', P(0, sg * 0.07, 0.025), (0.2 * s, 0.02 * s, 0.012 * s), cedar, bevel=0.002, rot=R.to_euler())
    # thin translucent paper in a soft colour: it doesn't glow by itself, the
    # candle inside shines through it (so the lantern and the light it throws
    # on the water are one colour, and it's brightest nearest the flame)
    tint = {'floral': (1.0, 0.6, 0.5), 'stars': (1.0, 0.8, 0.46), 'fan': (1.0, 0.68, 0.4), 'dots': (0.95, 0.66, 0.72)}.get(kind, (1.0, 0.72, 0.45))
    m, n, l, b = node_mat('lantern_paper_' + kind)
    out = next(x for x in n if x.type == 'OUTPUT_MATERIAL')
    tc = n.new('ShaderNodeTexCoord')
    fib = n.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 60; fib.inputs['Detail'].default_value = 6
    l.new(tc.outputs['UV'], fib.inputs['Vector'])
    fm_ = n.new('ShaderNodeMapRange'); fm_.inputs['To Min'].default_value = 0.85; fm_.inputs['To Max'].default_value = 1.0
    l.new(fib.outputs['Fac'], fm_.inputs['Value'])
    col = n.new('ShaderNodeVectorMath'); col.operation = 'SCALE'; col.inputs[0].default_value = tint
    l.new(fm_.outputs['Result'], col.inputs['Scale'])
    tr = n.new('ShaderNodeBsdfTranslucent'); l.new(col.outputs['Vector'], tr.inputs['Color'])
    b.inputs['Roughness'].default_value = 0.9; l.new(col.outputs['Vector'], b.inputs['Base Color'])
    mix = n.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = 0.25
    l.new(tr.outputs['BSDF'], mix.inputs[1]); l.new(b.outputs['BSDF'], mix.inputs[2])
    l.new(mix.outputs['Shader'], out.inputs['Surface'])
    m['candlelit'] = True
    zb, zt, rb, rt = 0.035, 0.24, 0.07, 0.085
    for k in range(4):     # four tapered paper panels with UVs
        a0 = k * math.pi / 2 + math.pi / 4; a1 = a0 + math.pi / 2
        c0b = P(math.cos(a0) * rb, math.sin(a0) * rb, zb); c1b = P(math.cos(a1) * rb, math.sin(a1) * rb, zb)
        c1t = P(math.cos(a1) * rt, math.sin(a1) * rt, zt); c0t = P(math.cos(a0) * rt, math.sin(a0) * rt, zt)
        _quad('lantern_paper', [c0b, c1b, c1t, c0t], [(0, 0), (1, 0), (1, 1), (0, 1)], m)
        # frame: corner posts and rims
        cyl('lantern_post', (c0b + c0t) / 2, 0.004 * s, (c0t - c0b).length, frame, verts=6).rotation_euler = (c0t - c0b).to_track_quat('Z', 'Y').to_euler()
        for (u, v) in ((c0b, c1b), (c0t, c1t)):
            cyl('lantern_rim', (u + v) / 2, 0.004 * s, (v - u).length, frame, verts=6).rotation_euler = (v - u).to_track_quat('Z', 'Y').to_euler()
    # a little paper cap and a loop of string to lift it by
    cyl('lantern_cap', P(0, 0, zt + 0.012), rt * 1.05 * s, 0.02 * s, frame, verts=4, r2=rt * 0.6 * s, rot=(0, 0, yaw + math.pi / 4))
    for sg in (-1, 1):
        a = P(sg * 0.03, 0, zt + 0.02); bb = P(0, 0, zt + 0.07)
        cyl('lantern_loop', (a + bb) / 2, 0.0015 * s, (bb - a).length, frame, verts=4).rotation_euler = (bb - a).to_track_quat('Z', 'Y').to_euler()
    # the candle inside
    cyl('lantern_candle', P(0, 0, zb + 0.03), 0.015 * s, 0.06 * s, solid('wax', (0.9, 0.85, 0.75), 0.6), verts=10)
    sphere('flame', P(0, 0, zb + 0.072), 0.008 * s, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1.0, 0.68, 0.28), strength=60), 8, (1, 1, 2.0))
    L = bpy.data.lights.new('candle', 'POINT'); L.energy = energy * 1.6; L.color = (1.0, 0.72, 0.42); L.shadow_soft_size = 0.012
    link(bpy.data.objects.new('candle', L)).location = P(0, 0, zb + 0.08)
