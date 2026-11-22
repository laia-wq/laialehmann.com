"""A stuffed-toy squirrel: not a squirrel, a squirrel *toy*.

Pillowy sewn panels (soft rounded shapes that crease where they're stitched
together), short velvety plush fabric with sheen, a cream felt tummy and
muzzle patch, round felt ears with pink lining, shiny plastic safety eyes,
an embroidered nose and mouth, a fat stuffed tube of a tail curling up the
back, stubby legs sticking straight out in front (how plush toys sit), a
white satin tag sewn into its side, and a felt sunflower seed held between
its paws.
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix
from kit import solid, node_mat, link, sphere, cyl


def plush_fabric(name, color, pile=1.0):
    """Short-pile plush fabric: fine fibre bump, a brushed nap that streaks one
    way, slightly matted patches, soft sheen at grazing angles."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    # fibres: very fine noise, stretched along the nap (local z)
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 0.25)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    fib = n.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 2600; fib.inputs['Detail'].default_value = 4
    fib.inputs['Roughness'].default_value = 0.7
    l.new(mp.outputs['Vector'], fib.inputs['Vector'])
    # matted patches where the pile lies a different way
    mat_ = n.new('ShaderNodeTexNoise'); mat_.inputs['Scale'].default_value = 420; mat_.inputs['Detail'].default_value = 5; mat_.inputs['Roughness'].default_value = 0.65
    l.new(tc.outputs['Object'], mat_.inputs['Vector'])
    h = n.new('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'
    l.new(mat_.outputs['Fac'], h.inputs[0]); h.inputs[1].default_value = 0.9; l.new(fib.outputs['Fac'], h.inputs[2])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.9 * pile; bp.inputs['Distance'].default_value = 0.004
    l.new(h.outputs['Value'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    # colour: fibre tips lighter, matted patches a little darker
    cr = n.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.65
    cr.inputs['To Min'].default_value = 0.78; cr.inputs['To Max'].default_value = 1.12
    l.new(fib.outputs['Fac'], cr.inputs['Value'])
    cm = n.new('ShaderNodeMapRange'); cm.inputs['From Min'].default_value = 0.3; cm.inputs['From Max'].default_value = 0.7; cm.inputs['To Min'].default_value = 0.72; cm.inputs['To Max'].default_value = 1.12
    l.new(mat_.outputs['Fac'], cm.inputs['Value'])
    k = n.new('ShaderNodeMath'); k.operation = 'MULTIPLY'
    l.new(cr.outputs['Result'], k.inputs[0]); l.new(cm.outputs['Result'], k.inputs[1])
    sc = n.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs[0].default_value = color
    l.new(k.outputs['Value'], sc.inputs['Scale'])
    l.new(sc.outputs['Vector'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.95
    b.inputs['Sheen Weight'].default_value = 1.0 * pile; b.inputs['Sheen Roughness'].default_value = 0.45
    b.inputs['Sheen Tint'].default_value = (1, 0.96, 0.9, 1)
    b.inputs['Subsurface Weight'].default_value = 0.04
    return m


def _fuzz(o, s, density=520000, length=0.0065):
    """Short fibres standing off the fabric, so the outline reads as fuzzy."""
    bpy.context.view_layer.update()
    area = sum(p.area for p in o.data.polygons) * max(o.scale) ** 2
    md = o.modifiers.new('fuzz', 'PARTICLE_SYSTEM'); ps = md.particle_system.settings
    ps.type = 'HAIR'; ps.count = max(200, int(area * density)); ps.hair_length = length * s
    ps.use_advanced_hair = False
    ps.render_type = 'PATH'; ps.display_step = 2; ps.render_step = 3
    ps.root_radius = 0.5; ps.tip_radius = 0.0; ps.radius_scale = 0.0004 * s
    ps.material = 1
    ps.child_type = 'NONE'
    ps.use_hair_bspline = False


def _soft(name, loc, r, mat, scale=(1, 1, 1), rot=None, seg=40):
    """A stuffed panel: a smooth, slightly squashed ball."""
    o = sphere(name, loc, r, mat, seg, scale)
    if rot is not None: o.rotation_euler = rot
    sub = o.modifiers.new('smooth', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    return o


def _stitches(name, pts, mat, r=0.0016, on=()):
    """Little thread stitches along a seam (every other gap), pulled down onto
    the surface of the panels they join so they sink into the fabric."""
    if on:
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = [(o.evaluated_get(dg), o.matrix_world, o.matrix_world.inverted()) for o in on]
        def snap(p):
            best = None
            for e, mw, mi in ev:
                ok, loc, nrm, _ = e.closest_point_on_mesh(mi @ p)
                if not ok: continue
                w = mw @ loc
                if best is None or (w - p).length < (best[0] - p).length:
                    best = (w, (mw.to_3x3() @ nrm).normalized())
            return best[0] + best[1] * r * 0.25 if best else p
        pts = [snap(p) for p in pts]
    for i in range(0, len(pts) - 1, 2):
        a, b = pts[i], pts[i + 1]
        d = b - a
        c = cyl(name, (a + b) / 2, r, d.length, mat, verts=6)
        c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()


def _tube(name, pts, radii, mat):
    """A stuffed tube along points (the tail): a bevelled curve with taper."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp_, p, r in zip(sp.bezier_points, pts, radii):
        bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'; bp_.radius = r
    cu.bevel_depth = 1.0; cu.bevel_resolution = 8; cu.resolution_u = 16; cu.use_fill_caps = True
    o = link(bpy.data.objects.new(name, cu)); cu.materials.append(mat)
    return o


def plush_squirrel(origin, yaw, s=1.0, body_col=(0.6, 0.22, 0.06)):
    """Build the toy. Returns a function mapping local points (x right,
    y forward, z up; about 0.3 tall) to world, for placing things."""
    R = Matrix.Rotation(yaw, 3, 'Z'); O = Vector(origin)
    P = lambda x, y, z: O + R @ (Vector((x, y, z)) * s)
    rot = lambda m=Matrix.Identity(3): (R @ m).to_euler()
    fur = plush_fabric('plush_orange', body_col)
    cream = plush_fabric('plush_cream', (0.93, 0.84, 0.68), 0.8)
    pink = plush_fabric('plush_pink', (0.88, 0.58, 0.55), 0.5)
    thread = solid('plush_thread', (0.2, 0.08, 0.05), 0.7)
    seam = solid('plush_seam_thread', (0.48, 0.22, 0.09), 0.8)
    eye = solid('safety_eye', (0.01, 0.01, 0.012), 0.04, coat=1.0)
    eye.node_tree.nodes['Principled BSDF'].inputs['Coat Roughness'].default_value = 0.02
    # body: a pear-shaped pillow, sitting, leaning back a touch
    body = _soft('plush_body', P(0, 0, 0.085), 0.08 * s, fur, (0.95, 0.85, 1.12), rot(Matrix.Rotation(-0.12, 3, 'X')))
    tummy = _soft('plush_tummy', P(0, 0.052, 0.08), 0.052 * s, cream, (0.82, 0.32, 1.0), rot(Matrix.Rotation(-0.12, 3, 'X')))
    _stitches('plush_seam', [P(0.044 * math.cos(a), 0.065 + 0.006 * math.sin(a) ** 2, 0.08 + 0.05 * math.sin(a)) for a in [k / 28 * 2 * math.pi for k in range(29)]], seam, on=(tummy,))
    # head: big and round, a little wider than tall, a seam across the crown
    hc = P(0, 0.01, 0.215)
    head = _soft('plush_head', hc, 0.072 * s, fur, (1.08, 0.98, 0.95))
    _stitches('plush_seam', [P(0.073 * math.cos(a), 0.01 + 0.0, 0.215 + 0.068 * math.sin(a)) for a in [math.pi * k / 26 for k in range(27)]], seam, on=(head,))
    muzzle = _soft('plush_muzzle', P(0, 0.066, 0.198), 0.03 * s, cream, (1.05, 0.75, 0.82))
    # neck seam where head meets body
    _stitches('plush_seam', [P(0.055 * math.cos(a), 0.01 + 0.05 * math.sin(a), 0.155) for a in [k / 30 * 2 * math.pi for k in range(31)]], seam, on=(head, body))
    furry = [body, tummy, head, muzzle]
    # ears: round felt discs with pink lining, a little tufty pinch at the top
    for sg in (-1, 1):
        ec = P(sg * 0.045, -0.005, 0.272)
        tilt = Matrix.Rotation(sg * -0.35, 3, 'Y') @ Matrix.Rotation(-0.15, 3, 'X')
        furry.append(_soft('plush_ear', ec + R @ (tilt @ Vector((0, 0, 0.012))) * s, 0.03 * s, fur, (0.85, 0.32, 1.55), rot(tilt)))
        _soft('plush_ear_in', ec + R @ (tilt @ Vector((0, 0.008, 0.006))) * s, 0.02 * s, pink, (0.8, 0.25, 1.35), rot(tilt))
        tip = ec + R @ (tilt @ Vector((0, 0, 0.06))) * s
        tip = ec + R @ (tilt @ Vector((0, 0, 0.05))) * s
        furry.append(_soft('plush_tuft', tip, 0.012 * s, fur, (0.9, 0.6, 1.4), rot(tilt)))
    # plastic safety eyes, set into the head, each with a highlight
    for sg in (-1, 1):
        ep = P(sg * 0.033, 0.072, 0.232)
        e = sphere('plush_eye', ep, 0.013 * s, eye, 24, (1, 0.6, 1)); e.rotation_euler = rot()
        sphere('plush_eye_hi', P(sg * 0.033 + 0.004, 0.08, 0.238), 0.0028 * s, solid('eye_hi', (1, 1, 1), 0.05, emit=(1, 1, 1), strength=2.5), 8)
    # embroidered nose (a satin-stitch triangle) and a little stitched smile
    for k in range(6):
        w = 0.013 * (1 - k / 7)
        a, b = P(-w, 0.098, 0.208 - k * 0.0022), P(w, 0.098, 0.208 - k * 0.0022)
        c = cyl('plush_nose', (a + b) / 2, 0.0016 * s, (b - a).length, thread, verts=6); c.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    for sg in (-1, 1):
        pts = [P(sg * 0.012 * t, 0.095 - 0.006 * t * t, 0.19 - 0.008 * math.sin(t * math.pi)) for t in [k / 6 for k in range(7)]]
        for a, b in zip(pts, pts[1:]):
            c = cyl('plush_mouth', (a + b) / 2, 0.0012 * s, (b - a).length, thread, verts=6); c.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    # arms: stubby, curving in to hold the seed together
    for sg in (-1, 1):
        furry.append(_soft('plush_arm', P(sg * 0.05, 0.05, 0.11), 0.026 * s, fur, (0.7, 1.4, 0.75), rot(Matrix.Rotation(sg * 0.55, 3, 'Z') @ Matrix.Rotation(0.5, 3, 'X'))))
        furry.append(_soft('plush_paw', P(sg * 0.018, 0.085, 0.118), 0.016 * s, cream, (1, 1, 0.9)))
    # legs: straight out in front, soles with a felt paw pad
    for sg in (-1, 1):
        furry.append(_soft('plush_leg', P(sg * 0.045, 0.06, 0.03), 0.032 * s, fur, (0.85, 1.45, 0.8)))
        _soft('plush_sole', P(sg * 0.047, 0.11, 0.032), 0.022 * s, cream, (1.0, 0.25, 1.15), rot(Matrix.Rotation(0.1, 3, 'X')))
    # the tail: a fat stuffed tube curling up behind and out to one side, its
    # cream tip level with the cheek so it stays clear of the ears
    tp = [P(0.03, -0.07, 0.04), P(0.1, -0.1, 0.08), P(0.155, -0.1, 0.15), P(0.175, -0.08, 0.21), P(0.168, -0.05, 0.248), P(0.142, -0.03, 0.252)]
    tail = _tube('plush_tail', tp, [0.035 * s, 0.05 * s, 0.056 * s, 0.05 * s, 0.038 * s, 0.026 * s], fur)
    bpy.context.view_layer.update()
    tm = bpy.data.meshes.new_from_object(tail.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tail)
    tail = link(bpy.data.objects.new('plush_tail', tm))
    for pg in tm.polygons: pg.use_smooth = True
    tip = _soft('plush_tail_tip', tp[-1] + R @ Vector((-0.004, 0.006, -0.002)) * s, 0.028 * s, cream, (1, 1, 0.9))
    furry += [tail, tip]
    if s >= 0.3:
        for o in furry: _fuzz(o, s)
    # a white satin tush tag sewn into the side seam
    tg = P(0.075, -0.03, 0.05)
    t = cyl('plush_tag', tg, 0.012 * s, 0.035 * s, solid('satin_tag', (0.95, 0.94, 0.9), 0.25), verts=4)
    t.scale = (1, 0.08, 1); t.rotation_euler = rot(Matrix.Rotation(0.2, 3, 'Y') @ Matrix.Rotation(math.pi / 4, 3, 'Z'))
    # a felt sunflower seed held between the paws: dark with cream stripes
    sm, sn, sl, sb = node_mat('felt_seed')
    stc = sn.new('ShaderNodeTexCoord'); swv = sn.new('ShaderNodeTexWave'); swv.wave_type = 'BANDS'; swv.bands_direction = 'X'
    swv.inputs['Scale'].default_value = 2.5
    sl.new(stc.outputs['Object'], swv.inputs['Vector'])
    sr = sn.new('ShaderNodeValToRGB'); sr.color_ramp.elements[0].position = 0.42; sr.color_ramp.elements[1].position = 0.58
    sr.color_ramp.elements[0].color = (0.06, 0.05, 0.05, 1); sr.color_ramp.elements[1].color = (0.88, 0.84, 0.74, 1)
    sl.new(swv.outputs['Fac'], sr.inputs['Fac']); sl.new(sr.outputs['Color'], sb.inputs['Base Color'])
    sb.inputs['Roughness'].default_value = 0.9; sb.inputs['Sheen Weight'].default_value = 0.6
    seed = _soft('plush_seed', P(0, 0.097, 0.128), 0.02 * s, sm, (0.6, 0.45, 1.05), rot(Matrix.Rotation(0.2, 3, 'Y')))
    return P
