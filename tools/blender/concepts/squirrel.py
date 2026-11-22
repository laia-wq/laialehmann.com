"""Red squirrels for the Squirrels and Seeds room.

Each squirrel is one soft body built from metaballs (so the haunches, chest,
head and tail melt into each other like fur, instead of looking like stacked
spheres), plus crisp separate parts: tufted ears, glossy eyes with a catch
light, nose, whiskers, claws. Poses are a handful of named points in the
squirrel's own frame (x right, y forward, z up, metres, about 0.4 tall
sitting) so they can sit, stand, reach, type, carry or curl up asleep.
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion
from kit import solid, node_mat, link, sphere, cyl

_FAM = [0]


def fur_material(name='sq_fur', back=(0.3, 0.1, 0.035), belly=(0.9, 0.82, 0.68)):
    """Red-brown on the back, cream on the chest and muzzle (chosen by which
    way the surface faces in the squirrel's own frame), with fine streaky
    fur bump, colour flecks and sheen so it reads soft."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Normal'], sep.inputs['Vector'])
    # belly: surfaces facing forward and a little down
    fw = n.new('ShaderNodeMapRange'); fw.inputs['From Min'].default_value = 0.35; fw.inputs['From Max'].default_value = 0.8
    l.new(sep.outputs['Y'], fw.inputs['Value'])
    up = n.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = 0.75; up.inputs['From Max'].default_value = 0.2
    l.new(sep.outputs['Z'], up.inputs['Value'])
    mul0 = n.new('ShaderNodeMath'); mul0.operation = 'MULTIPLY'
    l.new(fw.outputs['Result'], mul0.inputs[0]); l.new(up.outputs['Result'], mul0.inputs[1])
    sepo = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sepo.inputs['Vector'])
    front = n.new('ShaderNodeMapRange'); front.inputs['From Min'].default_value = -0.02; front.inputs['From Max'].default_value = 0.03
    l.new(sepo.outputs['Y'], front.inputs['Value'])
    mul1 = n.new('ShaderNodeMath'); mul1.operation = 'MULTIPLY'
    l.new(mul0.outputs['Value'], mul1.inputs[0]); l.new(front.outputs['Result'], mul1.inputs[1])
    # only a strip down the middle: chest, belly, chin (limbs and face stay red)
    ax = n.new('ShaderNodeMath'); ax.operation = 'ABSOLUTE'; l.new(sepo.outputs['X'], ax.inputs[0])
    mid = n.new('ShaderNodeMapRange'); mid.inputs['From Min'].default_value = 0.028; mid.inputs['From Max'].default_value = 0.045
    mid.inputs['To Min'].default_value = 1.0; mid.inputs['To Max'].default_value = 0.0
    l.new(ax.outputs['Value'], mid.inputs['Value'])
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    l.new(mul1.outputs['Value'], mul.inputs[0]); l.new(mid.outputs['Result'], mul.inputs[1])
    # streaky fur: noise stretched along z, for colour flecks and bump
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (420, 420, 90)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Detail'].default_value = 6; nz.inputs['Roughness'].default_value = 0.7
    l.new(mp.outputs['Vector'], nz.inputs['Vector'])
    col = n.new('ShaderNodeMix'); col.data_type = 'RGBA'
    col.inputs['A'].default_value = (*back, 1); col.inputs['B'].default_value = (*belly, 1)
    l.new(mul.outputs['Value'], col.inputs['Factor'])
    fleck = n.new('ShaderNodeMix'); fleck.data_type = 'RGBA'; fleck.blend_type = 'MULTIPLY'
    fr = n.new('ShaderNodeMapRange'); fr.inputs['To Min'].default_value = 0.0; fr.inputs['To Max'].default_value = 0.45
    l.new(nz.outputs['Fac'], fr.inputs['Value'])
    l.new(fr.outputs['Result'], fleck.inputs['Factor']); l.new(col.outputs['Result'], fleck.inputs['A'])
    fleck.inputs['B'].default_value = (0.55, 0.45, 0.4, 1)
    l.new(fleck.outputs['Result'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.45; bp.inputs['Distance'].default_value = 0.003
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.75
    b.inputs['Sheen Weight'].default_value = 0.8; b.inputs['Sheen Roughness'].default_value = 0.4
    b.inputs['Sheen Tint'].default_value = (1.0, 0.85, 0.7, 1)
    b.inputs['Subsurface Weight'].default_value = 0.08
    return m


EYE = None
def _mats():
    return {
        'eye': solid('sq_eye', (0.01, 0.008, 0.008), 0.05, coat=1.0),
        'glint': solid('sq_glint', (1, 1, 1), 0.1, emit=(1, 0.97, 0.92), strength=6.0),
        'ring': solid('sq_eyering', (0.62, 0.48, 0.36), 0.8),
        'nose': solid('sq_nose', (0.25, 0.12, 0.1), 0.35, coat=0.5),
        'whisker': solid('sq_whisker', (0.1, 0.08, 0.07), 0.5),
        'claw': solid('sq_claw', (0.15, 0.12, 0.1), 0.4),
        'ear_in': solid('sq_ear_in', (0.4, 0.2, 0.14), 0.7),
    }


def _ball(mb, p, r, stiff=2.0, kind='BALL', size=None, along=None):
    e = mb.elements.new()
    e.type = kind; e.co = p; e.radius = r; e.stiffness = stiff
    if size: e.size_x, e.size_y, e.size_z = size
    if along is not None and along.length > 1e-6:
        e.rotation = Vector((1, 0, 0)).rotation_difference(along.normalized())
    return e


def _capsule(mb, a, b, r, stiff=2.0):
    d = b - a
    e = _ball(mb, (a + b) / 2, r, stiff, 'CAPSULE', along=d)
    e.size_x = d.length / 2
    return e


def _rod(name, a, b, r, mat):
    d = b - a
    c = cyl(name, (a + b) / 2, r, max(d.length, 1e-4), mat, verts=6, r2=r * 0.4)
    c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return c


POSES = {
    # sitting up on its haunches, paws together at the chest (holding something)
    'sit':   dict(pelvis=(0, 0, 0.075), chest=(0, 0.02, 0.2), head=(0, 0.045, 0.3), look=(0, 1, -0.05),
                  hands=((-0.025, 0.08, 0.17), (0.025, 0.08, 0.17)), feet=((-0.045, 0.06, 0.012), (0.045, 0.06, 0.012)),
                  tail='up'),
    # sitting, paws forward and down onto a keyboard / desk
    'type':  dict(pelvis=(0, 0, 0.075), chest=(0, 0.035, 0.19), head=(0, 0.07, 0.28), look=(0, 1, -0.45),
                  hands=((-0.035, 0.13, 0.1), (0.04, 0.135, 0.1)), feet=((-0.045, 0.06, 0.012), (0.045, 0.06, 0.012)),
                  tail='up'),
    # up on its hind legs, both arms stretched up (putting a jar on a shelf)
    'reach': dict(pelvis=(0, 0, 0.13), chest=(0, 0.02, 0.27), head=(0, 0.035, 0.37), look=(0, 0.8, 0.6),
                  hands=((-0.035, 0.07, 0.47), (0.035, 0.07, 0.47)), feet=((-0.04, 0.03, 0.012), (0.04, 0.03, 0.012)),
                  tail='back'),
    # standing, one paw holding a clipboard at the chest, the other with a pencil
    'check': dict(pelvis=(0, 0, 0.12), chest=(0, 0.015, 0.26), head=(0, 0.04, 0.36), look=(0.1, 1, -0.4),
                  hands=((-0.04, 0.075, 0.22), (0.035, 0.08, 0.25)), feet=((-0.04, 0.03, 0.012), (0.04, 0.03, 0.012)),
                  tail='up'),
    # walking upright, arms wrapped round something big in front
    'carry': dict(pelvis=(0, 0, 0.12), chest=(0, -0.01, 0.255), head=(0, 0.01, 0.36), look=(0, 1, 0.1),
                  hands=((-0.07, 0.1, 0.2), (0.07, 0.1, 0.2)), feet=((-0.04, -0.03, 0.012), (0.045, 0.07, 0.03)),
                  tail='back'),
    # curled up asleep, tail over the nose
    'sleep': dict(pelvis=(-0.03, -0.02, 0.07), chest=(0.02, 0.04, 0.075), head=(0.07, 0.06, 0.07), look=(0.6, -0.3, -0.5),
                  hands=((0.07, 0.11, 0.03), (0.09, 0.09, 0.03)), feet=((-0.02, 0.06, 0.02), (0.0, 0.07, 0.02)),
                  tail='curl', eyes_shut=True),
}


def _tail_points(style, pelvis):
    p0 = Vector(pelvis) + Vector((0, -0.07, -0.02))
    pts = []
    N = 22
    for k in range(N):
        t = k / (N - 1)
        if style == 'up':        # the classic question-mark tail up the back
            pts.append(p0 + Vector((0.01 * math.sin(t * 3), -0.07 * math.sin(t * 2.2) - 0.01, 0.42 * t - 0.03)) +
                       Vector((0, 0.06 * max(0, t - 0.75) * 4, 0)))
        elif style == 'back':    # streaming out behind, curling up at the end
            pts.append(p0 + Vector((0, -0.28 * t, 0.06 + 0.22 * t * t)))
        else:                    # curled round the body
            a = -math.pi * 0.6 - t * math.pi * 1.25
            pts.append(Vector(pelvis) + Vector((0.03 + 0.1 * math.cos(a), 0.03 + 0.1 * math.sin(a), 0.03 + 0.07 * math.sin(t * math.pi))))
    return pts


def squirrel(origin, yaw=0.0, pose='sit', scale=1.0, name=None, back=(0.3, 0.1, 0.035)):
    """Make one squirrel; returns (objects, frame) where frame(x,y,z) maps
    the squirrel's local point to world (use it to place props in its paws)."""
    _FAM[0] += 1
    nm = name or 'sq%c' % (64 + _FAM[0])   # distinct metaball family per squirrel
    P = POSES[pose] if isinstance(pose, str) else pose
    R = Matrix.Rotation(yaw, 3, 'Z'); O = Vector(origin)
    W = lambda v: O + R @ (Vector(v) * scale)
    M = _mats()
    fur = fur_material('sq_fur_%.2f' % back[0], back)
    mb = bpy.data.metaballs.new(nm)
    mb.resolution = 0.006; mb.render_resolution = 0.0035; mb.threshold = 0.6
    pel, che, hd = Vector(P['pelvis']), Vector(P['chest']), Vector(P['head'])
    look = Vector(P['look']).normalized()
    # torso and haunches
    _capsule(mb, pel, che, 0.068, 2.2)
    _ball(mb, pel + Vector((0, -0.01, -0.005)), 0.095, 2.0, 'ELLIPSOID', (1.0, 1.0, 0.85))
    for sg in (-1, 1):
        _ball(mb, pel + Vector((sg * 0.05, 0.015, -0.02)), 0.07, 2.0, 'ELLIPSOID', (0.7, 1.1, 0.9))     # thighs
    _ball(mb, che + Vector((0, 0.02, -0.02)), 0.06, 1.8)                                              # chest ruff
    # neck and head, with muzzle and cheeks pointing where it looks
    _capsule(mb, che, hd, 0.045, 1.6)
    _ball(mb, hd, 0.07, 2.4, 'ELLIPSOID', (1.0, 1.05, 0.95))
    mz = hd + look * 0.058 + Vector((0, 0, -0.014))
    _ball(mb, mz, 0.034, 2.2, 'ELLIPSOID', (0.9, 1.15, 0.85), along=look)
    side = Vector((-look.y, look.x, 0)).normalized() if abs(look.z) < 0.99 else Vector((1, 0, 0))
    for sg in (-1, 1):
        _ball(mb, hd + look * 0.025 + side * sg * 0.032 + Vector((0, 0, -0.015)), 0.036, 1.8)           # cheeks
    # arms: shoulder → elbow (bent outwards) → paw
    for sg, hand in zip((-1, 1), P['hands']):
        sh = che + Vector((sg * 0.04, 0.015, 0.0))
        hand = Vector(hand)
        el = (sh + hand) / 2 + Vector((sg * 0.03, -0.01, -0.02))
        _capsule(mb, sh, el, 0.026, 2.0); _capsule(mb, el, hand, 0.021, 2.0)
        _ball(mb, hand, 0.022, 2.0)
    # hind feet: long, flat
    for sg, foot in zip((-1, 1), P['feet']):
        foot = Vector(foot)
        heel = pel + Vector((sg * 0.055, -0.01, -0.05))
        _capsule(mb, heel, foot + Vector((0, 0, 0.005)), 0.024, 2.0)
        _ball(mb, foot + Vector((0, 0.015, 0)), 0.024, 2.0, 'ELLIPSOID', (0.7, 1.5, 0.5))
    # the tail: big and fluffy, with a lumpy outline
    pts = _tail_points(P['tail'], P['pelvis'])
    for k, p in enumerate(pts):
        t = k / (len(pts) - 1)
        r = 0.045 + 0.06 * math.sin(min(1, t * 1.25) * math.pi * 0.92)
        _ball(mb, p, r, 1.3)
        if k % 2 == 0:
            for j in range(4):   # soft fluff round the edge (small, low stiffness: no lumps)
                a = k * 1.3 + j * math.pi / 2
                _ball(mb, p + Vector((math.cos(a), 0.5 * math.sin(a), 0.6 * math.sin(a))) * r * 0.5, r * 0.45, 0.7)
    body = link(bpy.data.objects.new(nm, mb))
    body.location = O; body.rotation_euler = (0, 0, yaw); body.scale = (scale,) * 3
    mb.materials.append(fur)
    objs = [body]
    # crisp parts in world space
    def frame(v): return W(v)
    up = Vector((0, 0, 1))
    for sg in (-1, 1):
        # ears: upright, a little splayed, with a tuft
        eb = hd + side * sg * 0.036 + Vector((0, -0.01, 0.052))
        et = eb + side * sg * 0.012 + Vector((0, -0.006, 0.042))
        e = cyl('sq_ear', W(eb + (et - eb) / 2), 0.016 * scale, 0.045 * scale, fur, verts=10, r2=0.004 * scale)
        e.rotation_euler = (R @ (et - eb)).to_track_quat('Z', 'Y').to_euler()
        e.scale = (1, 0.45, 1); objs.append(e)
        ei = cyl('sq_ear_in', W(eb + (et - eb) / 2 + look * 0.005), 0.011 * scale, 0.035 * scale, M['ear_in'], verts=10, r2=0.003 * scale)
        ei.rotation_euler = e.rotation_euler; ei.scale = (1, 0.3, 1); objs.append(ei)
        for j in range(4):
            tip = et + Vector((0.004 * (j - 1.5), -0.002 * j, 0.02 + 0.006 * (j % 2)))
            objs.append(_rod('sq_tuft', W(et - Vector((0, 0, 0.005))), W(tip), 0.003 * scale, fur))
        # eyes: big, glossy, a pale ring, a catch light
        ep = hd + look * 0.047 + side * sg * 0.033 + Vector((0, 0, 0.014))
        if P.get('eyes_shut'):
            objs.append(_rod('sq_lid', W(ep - side * 0.008), W(ep + side * 0.008), 0.0025 * scale, M['eye']))
        else:
            objs.append(sphere('sq_eyering', W(ep - look * 0.004), 0.0145 * scale, M['ring'], 12))
            objs.append(sphere('sq_eye', W(ep + look * 0.001), 0.014 * scale, M['eye'], 16))
            objs.append(sphere('sq_glint', W(ep + look * 0.013 + Vector((0, 0, 0.005)) + side * sg * -0.003), 0.0032 * scale, M['glint'], 8))
        # whiskers
        for j in range(3):
            a = mz + look * 0.02 + side * sg * 0.012
            b = a + side * sg * 0.06 + look * 0.01 + Vector((0, 0, 0.012 * (j - 1)))
            objs.append(_rod('sq_whisker', W(a), W(b), 0.0007 * scale, M['whisker']))
    objs.append(sphere('sq_nose', W(mz + look * 0.032 + Vector((0, 0, 0.006))), 0.008 * scale, M['nose'], 10))
    for hand in P['hands']:
        for j in range(3):
            h = Vector(hand); objs.append(_rod('sq_claw', W(h + look * 0.012 + side * 0.006 * (j - 1)), W(h + look * 0.022 + side * 0.007 * (j - 1) + Vector((0, 0, -0.008))), 0.0018 * scale, M['claw']))
    return objs, frame
