"""Close-up of the corner shop's front window, for the browser's zoom.

The street keeps its simple window; here that one window is rebuilt in full:
a painted, moulded box-sash frame (two sashes, glazing bars, putty, horns),
old wavy glass in front of frosted glass glowing warm, a brass sash lock and
lift rings, a weathered stone sill with the plush squirrel on it.

Renders, into CLOSE_OUT:
  fly_000..fly_NNN.png  the camera swinging from the street's angle round to
                        face the window straight on (CLOSE_FRAMES, CLOSE_FW x CLOSE_FH)
  shop.png              the straight-on still (RES_X x RES_Y)
  pane.png              the glass alone (alpha), for masking the shadow play
  closeup.json          where the glass is in the still, where the window is on
                        the street, and the first frame's framing (for the hand-over)
"""
import os, sys, math, json
import bpy
from mathutils import Vector, Matrix
from kit import solid, varied, box, cyl, sphere, node_mat, link, render
from canal_extras import limb
import squirrel as SQ


def _bb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])


def painted_wood(name, paint, wood=(0.34, 0.22, 0.13)):
    """Paint over timber: brush-mark bump, a few chips showing the wood."""
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    chip = n.new('ShaderNodeTexNoise'); chip.inputs['Scale'].default_value = 38; chip.inputs['Detail'].default_value = 8; chip.inputs['Roughness'].default_value = 0.65
    l.new(tc.outputs['Object'], chip.inputs['Vector'])
    cm = n.new('ShaderNodeMapRange'); cm.inputs['From Min'].default_value = 0.7; cm.inputs['From Max'].default_value = 0.72
    l.new(chip.outputs['Fac'], cm.inputs['Value'])
    grain_map = n.new('ShaderNodeMapping'); grain_map.inputs['Scale'].default_value = (4, 4, 90)
    l.new(tc.outputs['Object'], grain_map.inputs['Vector'])
    grain = n.new('ShaderNodeTexWave'); grain.wave_type = 'RINGS'; grain.inputs['Scale'].default_value = 3; grain.inputs['Distortion'].default_value = 6
    l.new(grain_map.outputs['Vector'], grain.inputs['Vector'])
    woodc = n.new('ShaderNodeMix'); woodc.data_type = 'RGBA'; woodc.inputs['A'].default_value = (*wood, 1); woodc.inputs['B'].default_value = (wood[0] * 0.6, wood[1] * 0.6, wood[2] * 0.6, 1)
    l.new(grain.outputs['Fac'], woodc.inputs['Factor'])
    dirt = n.new('ShaderNodeTexNoise'); dirt.inputs['Scale'].default_value = 6
    l.new(tc.outputs['Object'], dirt.inputs['Vector'])
    pc = n.new('ShaderNodeMix'); pc.data_type = 'RGBA'; pc.blend_type = 'MULTIPLY'
    dm = n.new('ShaderNodeMapRange'); dm.inputs['To Min'].default_value = 0.0; dm.inputs['To Max'].default_value = 0.25
    l.new(dirt.outputs['Fac'], dm.inputs['Value'])
    l.new(dm.outputs['Result'], pc.inputs['Factor']); pc.inputs['A'].default_value = (*paint, 1); pc.inputs['B'].default_value = (0.55, 0.5, 0.42, 1)
    col = n.new('ShaderNodeMix'); col.data_type = 'RGBA'
    l.new(cm.outputs['Result'], col.inputs['Factor']); l.new(pc.outputs['Result'], col.inputs['A']); l.new(woodc.outputs['Result'], col.inputs['B'])
    l.new(col.outputs['Result'], b.inputs['Base Color'])
    brush_map = n.new('ShaderNodeMapping'); brush_map.inputs['Scale'].default_value = (300, 300, 20)
    l.new(tc.outputs['Object'], brush_map.inputs['Vector'])
    brush = n.new('ShaderNodeTexNoise'); brush.inputs['Detail'].default_value = 4
    l.new(brush_map.outputs['Vector'], brush.inputs['Vector'])
    hb = n.new('ShaderNodeMath'); hb.operation = 'ADD'
    l.new(brush.outputs['Fac'], hb.inputs[0]); l.new(cm.outputs['Result'], hb.inputs[1])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25; bp.inputs['Distance'].default_value = 0.0015
    l.new(hb.outputs['Value'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    rr = n.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.45; rr.inputs['To Max'].default_value = 0.8
    l.new(cm.outputs['Result'], rr.inputs['Value']); l.new(rr.outputs['Result'], b.inputs['Roughness'])
    return m


def old_glass():
    """Old drawn glass: clear but faintly wavy, with a soft reflection."""
    m, n, l, b = node_mat('old_glass')
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3, 3, 26)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4; nz.inputs['Detail'].default_value = 2
    l.new(mp.outputs['Vector'], nz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    # thin and see-through: a faint sheen and reflections, no lens effects
    b.inputs['Base Color'].default_value = (0.9, 0.95, 0.94, 1)
    b.inputs['Alpha'].default_value = 0.12; b.inputs['Roughness'].default_value = 0.03; b.inputs['Coat Weight'].default_value = 1.0
    return m


def frosted_glow():
    """Frosted (hammered) glass with the shop's warm light behind it."""
    m, n, l, b = node_mat('frosted_glow')
    tc = n.new('ShaderNodeTexCoord')
    vo = n.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 140
    l.new(tc.outputs['Object'], vo.inputs['Vector'])
    gl = n.new('ShaderNodeMapRange'); gl.inputs['To Min'].default_value = 0.42; gl.inputs['To Max'].default_value = 0.3
    l.new(vo.outputs['Distance'], gl.inputs['Value'])
    grad = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], grad.inputs['Vector'])
    gz = n.new('ShaderNodeMapRange'); gz.inputs['To Min'].default_value = 0.8; gz.inputs['To Max'].default_value = 1.15
    l.new(grad.outputs['Z'], gz.inputs['Value'])
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    l.new(gl.outputs['Result'], mul.inputs[0]); l.new(gz.outputs['Result'], mul.inputs[1])
    b.inputs['Base Color'].default_value = (0.6, 0.45, 0.3, 1); b.inputs['Emission Color'].default_value = (1.0, 0.64, 0.34, 1)
    l.new(mul.outputs['Value'], b.inputs['Emission Strength'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6; bp.inputs['Distance'].default_value = 0.002
    l.new(vo.outputs['Distance'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.25
    return m


def _shop_pane(sc):
    near = lambda pre: min((o for o in sc.objects if o.name.startswith(pre) and o.type == 'MESH'),
                           key=lambda o: (o.matrix_world.translation - Vector((-0.56, 2.3, 0.88))).length)
    return _bb(near('pane'))


def shop_squirrel(sc):
    """The plush squirrel on the shop window's sill, off to the right, its tail
    curling up into the window. Called for the street render and the close-up
    alike, so the zoom never makes it appear. The pot plants that sat inside
    this window go (the squirrel replaces them)."""
    bpy.context.view_layer.update()
    plo, phi = _shop_pane(sc)
    x0, x1, z0, z1 = plo.x, phi.x, plo.z, phi.z
    w = x1 - x0; xc = (x0 + x1) / 2; yf = 2.25
    for o in sc.objects:
        if o.type != 'MESH' or o.name.split('.')[0] not in ('ipot', 'ileaves'): continue
        c = o.matrix_world.translation
        if x0 - 0.12 < c.x < x1 + 0.12 and 2.1 < c.y < 2.6 and z0 - 0.15 < c.z < z1: o.hide_render = True
    import plush
    plush.plush_squirrel(Vector((xc + w * 0.3, yf - 0.078, z0 - 0.005)), math.radians(-170), 0.68)


def shop_window(sc, street_cam, G):
    out = os.environ['CLOSE_OUT']; os.makedirs(out, exist_ok=True)
    SAMPLES = G['SAMPLES']; quay = G['quay']
    bpy.context.view_layer.update()
    near = lambda pre: min((o for o in sc.objects if o.name.startswith(pre) and o.type == 'MESH'),
                           key=lambda o: (o.matrix_world.translation - Vector((-0.56, 2.3, 0.88))).length)
    pane0 = near('pane'); plo, phi = _bb(pane0)
    x0, x1, z0, z1 = plo.x, phi.x, plo.z, phi.z
    w, h = x1 - x0, z1 - z0; xc = (x0 + x1) / 2
    yf = 2.25                         # the wall's face
    yp = plo.y                        # where the glass was
    # take out the street's simple window (pane, bars, sill, lintel) and what was behind it
    for o in list(sc.objects):
        if o.type != 'MESH': continue
        c = o.matrix_world.translation
        if x0 - 0.12 < c.x < x1 + 0.12 and 2.1 < c.y < 2.5 and z0 - 0.15 < c.z < z1 + 0.2:
            if o.name.split('.')[0] in ('shop_glass', 'shop_jar', 'pane', 'mull', 'sill', 'lintel', 'ipot', 'ileaves', 'curtain', 'candle', 'flame', 'book', 'vase', 'bloom', 'stem', 'bowl', 'fruit', 'lamp_stem', 'lamp_shade', 'cat_body', 'cat_head'):
                o.hide_render = True
    # the next window's left shutter overlaps this one's right shutter: drop it here
    for o in sc.objects:
        if o.type == 'MESH' and o.name.split('.')[0] in ('shutter', 'louvre'):
            lo, hi = _bb(o)
            if x1 + 0.06 < lo.x < x1 + 0.5 and hi.y < 2.26 and hi.z > z0 and lo.z < z1: o.hide_render = True
    for o in sc.objects:     # the umbrella leaning by the door would poke into the close-up
        if o.name.startswith('umbrella'): o.hide_render = True
    paint = painted_wood('sash_paint', (0.86, 0.82, 0.72))
    frame_paint = painted_wood('frame_paint', (0.78, 0.74, 0.64))
    brass = solid('sash_brass', (0.8, 0.6, 0.3), 0.25, metal=1.0)
    putty = varied('putty', (0.7, 0.66, 0.58), 0.04, 0.85, bump=0.6, bump_scale=400)
    stone = varied('sill_stone', (0.62, 0.58, 0.52), 0.06, 0.9, bump=0.8, bump_scale=60)
    # the street's shop opening was cut wider than this window: wall it up behind
    # the glass so nothing shows through gaps (shutter leaves, frame corners)
    box('window_backing', (xc, yp + 0.07, (z0 + z1) / 2), (w + 0.9, 0.03, h + 0.6), G['plaster_g'], bevel=0)
    # box frame lining the opening, from the wall face back to the glass
    d = yp - yf + 0.02
    for (cx, cz, sx, sz) in ((x0 - 0.02, (z0 + z1) / 2, 0.045, h), (x1 + 0.02, (z0 + z1) / 2, 0.045, h), (xc, z1 + 0.02, w + 0.085, 0.045)):
        box('box_frame', (cx, yf + d / 2, cz), (sx, d, sz), frame_paint, bevel=0.004)
    # stone sill: chamfered, weathered, sticking out a little
    box('sill_stone', (xc, yf - 0.035, z0 - 0.03), (w + 0.16, 0.16, 0.05), stone, bevel=0.01)
    box('sill_drip', (xc, yf - 0.105, z0 - 0.058), (w + 0.16, 0.012, 0.008), stone, bevel=0.002)
    box('lintel_stone', (xc, yf - 0.01, z1 + 0.09), (w + 0.18, 0.05, 0.12), stone, bevel=0.008)
    # two sashes: the top one a little further back, overlapping at the meeting rails
    st, rail, mr, bar = 0.032, 0.036, 0.042, 0.011
    zm = (z0 + z1) / 2
    glass = old_glass(); frost = frosted_glow()
    for (sz0, sz1, yb) in ((z0, zm + mr / 2, yp - 0.03), (zm - mr / 2, z1, yp - 0.005)):
        top_rail = rail if sz1 >= z1 - 1e-6 else mr
        bot_rail = rail + 0.012 if sz0 <= z0 + 1e-6 else mr
        for (cx, cz, sx, sz) in ((x0 + st / 2, (sz0 + sz1) / 2, st, sz1 - sz0), (x1 - st / 2, (sz0 + sz1) / 2, st, sz1 - sz0),
                                 (xc, sz1 - top_rail / 2, w - 2 * st, top_rail), (xc, sz0 + bot_rail / 2, w - 2 * st, bot_rail)):
            box('sash', (cx, yb, cz), (sx, 0.035, sz), paint, bevel=0.005)
        # inner ovolo moulding round the glass
        gz0, gz1 = sz0 + bot_rail, sz1 - top_rail
        for (cx, cz, sx, sz) in ((x0 + st + 0.004, (gz0 + gz1) / 2, 0.008, gz1 - gz0), (x1 - st - 0.004, (gz0 + gz1) / 2, 0.008, gz1 - gz0),
                                 (xc, gz1 - 0.004, w - 2 * st - 0.016, 0.008), (xc, gz0 + 0.004, w - 2 * st - 0.016, 0.008)):
            box('sash_mould', (cx, yb - 0.02, cz), (sx, 0.01, sz), paint, bevel=0.003)
        box('glazing_bar', (xc, yb - 0.006, (gz0 + gz1) / 2), (bar, 0.024, gz1 - gz0), paint, bevel=0.003)
        # glass, then frosted glass glowing just behind it
        box('sash_glass', (xc, yb + 0.004, (gz0 + gz1) / 2), (w - 2 * st, 0.004, gz1 - gz0), glass, bevel=0)
        box('sash_frost', (xc, yb + 0.012, (gz0 + gz1) / 2), (w - 2 * st + 0.01, 0.003, gz1 - gz0 + 0.01), frost, bevel=0)
        # putty fillets along every pane edge
        for half in (-1, 1):
            px0 = xc + (half - 1) * (w - 2 * st) / 4 + (bar / 2 if half > 0 else 0); px1 = px0 + (w - 2 * st) / 2 - bar / 2
            pcx = (px0 + px1) / 2
            for (cx, cz, sx, sz) in ((pcx, gz1 - 0.003, px1 - px0, 0.005), (pcx, gz0 + 0.003, px1 - px0, 0.005),
                                     (px0 + 0.003, (gz0 + gz1) / 2, 0.005, gz1 - gz0), (px1 - 0.003, (gz0 + gz1) / 2, 0.005, gz1 - gz0)):
                box('putty', (cx, yb - 0.001, cz), (sx, 0.006, sz), putty, bevel=0.0015)
        if sz1 >= z1 - 1e-6:   # horns on the upper sash
            for sx_ in (x0 + st / 2, x1 - st / 2):
                box('sash_horn', (sx_, yb, sz0 - 0.022), (st * 0.8, 0.03, 0.045), paint, bevel=0.008)
    # brass sash lock on the meeting rails, two lift rings on the bottom rail
    lk = Vector((xc, yp - 0.055, zm + 0.006))
    cyl('lock_base', lk, 0.016, 0.006, brass, verts=20, rot=(math.pi / 2, 0, 0))
    cyl('lock_cam', lk + Vector((0.008, -0.004, 0.006)), 0.011, 0.004, brass, verts=20, rot=(math.pi / 2, 0, 0))
    limb(lk + Vector((0.004, -0.006, 0.006)), lk + Vector((0.03, -0.008, 0.012)), 0.003, brass)
    sphere('lock_knob', lk + Vector((0.032, -0.009, 0.013)), 0.005, brass, 10)
    for dx in (-w * 0.28, w * 0.28):
        p = Vector((xc + dx, yp - 0.05, z0 + 0.022))
        cyl('lift_plate', p, 0.009, 0.003, brass, verts=16, rot=(math.pi / 2, 0, 0))
        ring = cyl('lift_ring', p + Vector((0, -0.004, -0.012)), 0.011, 0.003, brass, verts=24, rot=(math.pi / 2, 0, 0))
        hole = cyl('lift_ring_hole', p + Vector((0, -0.004, -0.012)), 0.0085, 0.02, None, verts=24, rot=(math.pi / 2, 0, 0))
        from kit import cut
        cut(ring, hole)

    # the stuffed toy squirrel on the sill (built with the street, so it's
    # there the whole way in)

    # ---- the camera: from the street's angle round to straight on
    T = Vector((xc, yp, (z0 + z1) / 2 + 0.02))
    d0 = Vector((math.sin(math.radians(45)) * math.sin(math.radians(58)), -math.cos(math.radians(45)) * math.sin(math.radians(58)), math.cos(math.radians(58))))
    d1 = Vector((0.0, -1.0, 0.1)).normalized()
    W0, W1 = 1.55, float(os.environ.get('CLOSE_W', '1.3'))
    cd = bpy.data.cameras.new('closecam'); cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 300
    ccam = link(bpy.data.objects.new('closecam', cd)); sc.camera = ccam
    ease = lambda t: t * t * (3 - 2 * t)
    def place(t):
        e = ease(t)
        dirv = d0.lerp(d1, e).normalized()
        lens = math.exp(math.log(420) + (math.log(42) - math.log(420)) * e)
        width = W0 + (W1 - W0) * e
        cd.lens = lens
        ccam.location = T + dirv * (width * lens / 36)
        ccam.rotation_euler = (T - ccam.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    # where the first frame's centre sits on the street (for the browser's hand-over)
    meta = {'street_target': (lambda v: [round(v.x, 5), round(1 - v.y, 5)])(world_to_camera_view(sc, street_cam, T)),
            'scale': W0 / 15.5, 'aspect': round((w - 2 * st) / (z1 - z0 - 2 * rail), 4)}
    r = sc.render
    n_frames = int(os.environ.get('CLOSE_FRAMES', '30'))
    fw, fh = int(os.environ.get('CLOSE_FW', '960')), int(os.environ.get('CLOSE_FH', '720'))
    fx, fy = int(os.environ.get('RES_X', 2400)), int(os.environ.get('RES_Y', 1800))
    if n_frames:
        r.resolution_x, r.resolution_y = fw, fh
        for k in range(n_frames):
            place(k / (n_frames - 1))
            render(sc, os.path.join(out, 'fly_%03d.png' % k), int(os.environ.get('FLY_SAMPLES', '40')))
    meta['frames'] = n_frames
    # the straight-on still
    place(1.0)
    r.resolution_x, r.resolution_y = fx, fy
    # the glass of both sashes, as one rectangle in the still
    gx0, gx1 = x0 + st, x1 - st
    gzb, gzt = z0 + rail + 0.012, z1 - rail
    corners = {'tl': Vector((gx0, yp - 0.03, gzt)), 'tr': Vector((gx1, yp - 0.03, gzt)), 'bl': Vector((gx0, yp - 0.03, gzb))}
    meta['pane'] = {k: (lambda v: [round(v.x, 5), round(1 - v.y, 5)])(world_to_camera_view(sc, ccam, p)) for k, p in corners.items()}
    meta['aspect'] = round((gx1 - gx0) / (gzt - gzb), 4)
    json.dump(meta, open(os.path.join(out, 'closeup.json'), 'w'))
    if os.environ.get('PROBE'):
        dg = bpy.context.evaluated_depsgraph_get()
        fr = ccam.data.view_frame(scene=sc)
        mw = ccam.matrix_world
        for uv in os.environ['PROBE'].split(';'):
            u, v = map(float, uv.split(','))
            # view_frame: 0 top-right, 1 bottom-right, 2 bottom-left, 3 top-left
            top = fr[3].lerp(fr[0], u); bot = fr[2].lerp(fr[1], u); q = top.lerp(bot, v)
            o = mw.translation.copy(); d = ((mw @ q) - o).normalized()
            hits = []
            for _ in range(12):
                ok, loc, nrm, idx, ob, _m = sc.ray_cast(dg, o, d)
                if not ok: hits.append('NONE'); break
                o = loc + d * 1e-4
                if ob.hide_render: continue
                hits.append('%s@(%.3f,%.3f,%.3f)' % (ob.name, loc.x, loc.y, loc.z))
            print('PROBE', u, v, ' -> '.join(hits))
        for ob in sc.objects:
            if ob.type == 'MESH' and not ob.hide_render and ob.name.split('.')[0] in ('shutter', 'louvre', 'curtain', 'mull', 'pane', 'sash'):
                lo, hi = _bb(ob)
                if hi.x > x0 - 0.8 and lo.x < x1 + 0.8 and lo.y < 2.6 and hi.y > 2.0 and hi.z > z0 - 0.3 and lo.z < z1 + 0.3:
                    print('BB', ob.name, tuple(round(c, 3) for c in lo), tuple(round(c, 3) for c in hi))
        print('WIN', x0, x1, z0, z1, yp)
        sys.exit(0)
    if not os.environ.get('SKIP_STILL'):
        render(sc, os.path.join(out, 'shop.png'), SAMPLES)
    # the frosted glass alone, for masking the shadow play
    geo = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT', 'META') and not o.hide_render]
    for o in geo:
        if o.name.startswith('sash_glass'): o.hide_render = True
        o.is_holdout = not o.name.startswith('sash_frost')
    r.film_transparent = True; sc.cycles.use_denoising = False
    r.resolution_x, r.resolution_y = fx // 2, fy // 2
    render(sc, os.path.join(out, 'pane.png'), 4)
    print('CLOSEUP DONE', meta)
    sys.exit(0)


# ---------------------------------------------------------------- the design teams' windows
def design_windows(sc, street_cam, G):
    """The tall house's top floor: three arched windows in a row, each with
    a design team's thing on its sill and frosted glass someone moves behind.
    The camera swings round from the street to face all three; the browser
    then lets you pick one. Writes fly frames, design.png, one glass mask per
    window (pane_0..2.png) and closeup.json with each window's glass corners."""
    import design_props as DP
    out = os.environ['CLOSE_OUT']; os.makedirs(out, exist_ok=True)
    SAMPLES = G['SAMPLES']
    bpy.context.view_layer.update()
    yf, yp = DP.A_FACE_Y, DP.A_FACE_Y + 0.08
    w, h = DP.WIN_W, DP.WIN_H
    r = w / 2; z0 = DP.SILL_Z; zs = z0 + h - r
    st, bar = 0.03, 0.012
    paint = painted_wood('frame_green', (0.17, 0.24, 0.2))
    lining = painted_wood('lining_cream', (0.74, 0.7, 0.6))
    frost = frosted_glow()
    rot_y = (math.pi / 2, 0, 0)
    # take out the street's simple glazing and what was behind it
    for o in list(sc.objects):
        if o.type != 'MESH' or o.name.startswith('dt_'): continue
        lo, hi = _bb(o); c = (lo + hi) / 2
        for u in DP.WIN_U:
            if abs(c.x - u) < w / 2 + 0.02 and yf + 0.03 < c.y < yf + 0.8 and z0 - 0.02 < c.z < z0 + h + 0.05:
                if o.name.split('.')[0] not in ('A', 'shutter', 'louvre'):
                    o.hide_render = True
    def arc(name, u, zc, rad, y, depth, thick, mat, n=16):
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            p0 = Vector((u + rad * math.cos(a0), y, zc + rad * math.sin(a0)))
            p1 = Vector((u + rad * math.cos(a1), y, zc + rad * math.sin(a1)))
            m_ = (p0 + p1) / 2; L = (p1 - p0).length * 1.08
            b_ = box(name, m_, (L, depth, thick), mat, bevel=0.002)
            b_.rotation_euler = (0, -((a0 + a1) / 2 + math.pi / 2), 0)
    # neighbouring windows' shutters overlap where they meet: keep one of each pair
    shs = [(o, *_bb(o)) for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.name.split('.')[0] == 'shutter']
    shs = [t for t in shs if t[1].z > z0 - 0.3 and t[2].z < z0 + h + 0.3 and t[2].y < yf + 0.01]
    gone = []
    for i, (a, alo, ahi) in enumerate(shs):
        for b, blo, bhi in shs[i + 1:]:
            if b in gone or a in gone: continue
            if min(ahi.x, bhi.x) - max(alo.x, blo.x) > 0.02:
                gone.append(b if blo.x > alo.x else a)
    for g in gone:
        glo, ghi = _bb(g); g.hide_render = True
        for o in sc.objects:
            if o.type == 'MESH' and o.name.split('.')[0] == 'louvre':
                lo, hi = _bb(o)
                if abs(lo.x - glo.x) < 0.03 and abs(hi.x - ghi.x) < 0.03 and glo.z - 0.01 < lo.z < ghi.z: o.hide_render = True
    print('DESIGN shutters dropped', [g.name for g in gone])
    # the shutters are open louvres over nothing: give each a board behind
    shut = solid('dw_shutter_back', (0.12, 0.16, 0.13), 0.8)
    for o in list(sc.objects):
        if o.type == 'MESH' and not o.hide_render and o.name.split('.')[0] == 'shutter':
            lo, hi = _bb(o)
            if lo.z > z0 - 0.3 and hi.z < z0 + h + 0.3 and hi.y < yf + 0.01 and DP.WIN_U[0] - 0.6 < lo.x < DP.WIN_U[2] + 0.6:
                box('dw_shutter_back', ((lo.x + hi.x) / 2, hi.y + 0.002, (lo.z + hi.z) / 2), (hi.x - lo.x - 0.01, 0.004, hi.z - lo.z - 0.01), shut, bevel=0)
    panes = []
    for k, u in enumerate(DP.WIN_U):
        # reveal lining, from the wall face back to the frame
        dl = yp - yf
        for sg in (-1, 1):
            box('dw_lining', (u + sg * (w / 2 - 0.006), yf + dl / 2, (z0 + zs) / 2), (0.012, dl, zs - z0), lining, bevel=0)
        arc('dw_lining', u, zs, r - 0.006, yf + dl / 2, dl, 0.012, lining, 18)
        # the frame: stiles, an arched head, a transom at the springing line, a bottom rail
        yb = yp - 0.012
        for sg in (-1, 1):
            box('dw_stile', (u + sg * (w / 2 - st / 2), yb, (z0 + zs) / 2), (st, 0.03, zs - z0), paint, bevel=0.004)
        arc('dw_head', u, zs, r - st / 2, yb, 0.03, st, paint, 18)
        box('dw_transom', (u, yb - 0.002, zs), (w - 0.01, 0.034, st), paint, bevel=0.004)
        box('dw_rail', (u, yb, z0 + 0.025), (w, 0.03, 0.05), paint, bevel=0.004)
        # two casement leaves meeting in the middle, each with a glazing bar and two cross bars
        box('dw_meet', (u, yb - 0.004, (z0 + 0.05 + zs) / 2), (0.034, 0.036, zs - z0 - 0.05), paint, bevel=0.004)
        gw = (w - 2 * st - 0.034) / 2
        for sg in (-1, 1):
            cx = u + sg * (0.017 + gw / 2)
            box('dw_bar', (cx, yb - 0.006, (z0 + 0.05 + zs) / 2), (bar, 0.016, zs - z0 - 0.05), paint, bevel=0.002)
            for f in (1 / 3, 2 / 3):
                box('dw_bar', (cx, yb - 0.006, z0 + 0.05 + (zs - z0 - 0.05) * f), (gw, 0.016, bar), paint, bevel=0.002)
            # a small brass handle on each leaf
            sphere('dw_knob', (u + sg * 0.03, yb - 0.03, (z0 + zs) / 2), 0.008, G['brass_d'] if 'brass_d' in G else paint, 10)
        # fanlight: three spokes from the middle of the transom
        for a in (math.pi / 4, math.pi / 2, 3 * math.pi / 4):
            p0 = Vector((u, yb - 0.006, zs)); p1 = p0 + Vector((math.cos(a), 0, math.sin(a))) * (r - st)
            b_ = box('dw_bar', (p0 + p1) / 2, (bar, 0.016, (p1 - p0).length), paint, bevel=0.002)
            b_.rotation_euler = (0, -(a - math.pi / 2), 0)
        # frosted glass, lit from behind: a rectangle and the arch above it
        box('sash_frost%d' % k, (u, yp + 0.004, (z0 + 0.05 + zs) / 2), (w - 2 * st + 0.01, 0.003, zs - z0 - 0.05 + 0.01), frost, bevel=0)
        cyl('sash_frost%d' % k, (u, yp + 0.005, zs), r - st + 0.005, 0.003, frost, verts=40, rot=rot_y)
        panes.append({'tl': Vector((u - (w / 2 - st), yp, zs + r - st)), 'tr': Vector((u + (w / 2 - st), yp, zs + r - st)),
                      'bl': Vector((u - (w / 2 - st), yp, z0 + 0.05)), 'aspect': (w - 2 * st) / (zs + r - st - z0 - 0.05)})
    # ---- the camera: from the street's angle round to straight on, all three windows in view
    T = Vector((DP.WIN_U[1], yp, z0 + h / 2 + 0.02))
    d0 = Vector((math.sin(math.radians(45)) * math.sin(math.radians(58)), -math.cos(math.radians(45)) * math.sin(math.radians(58)), math.cos(math.radians(58))))
    d1 = Vector((0.0, -1.0, 0.3)).normalized()
    W0, W1 = 2.6, float(os.environ.get('CLOSE_W', '2.4'))
    cd = bpy.data.cameras.new('closecam'); cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 300
    ccam = link(bpy.data.objects.new('closecam', cd)); sc.camera = ccam
    ease = lambda t: t * t * (3 - 2 * t)
    def place(t):
        e = ease(t)
        dirv = d0.lerp(d1, e).normalized()
        lens = math.exp(math.log(420) + (math.log(50) - math.log(420)) * e)
        width = W0 + (W1 - W0) * e
        cd.lens = lens
        ccam.location = T + dirv * (width * lens / 36)
        ccam.rotation_euler = (T - ccam.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    uvv = lambda cam, p: (lambda v: [round(v.x, 5), round(1 - v.y, 5)])(world_to_camera_view(sc, cam, p))
    meta = {'street_target': uvv(street_cam, T), 'scale': W0 / 15.5}
    rr = sc.render
    n_frames = int(os.environ.get('CLOSE_FRAMES', '30'))
    fw, fh = int(os.environ.get('CLOSE_FW', '1440')), int(os.environ.get('CLOSE_FH', '1080'))
    fx, fy = int(os.environ.get('RES_X', 2400)), int(os.environ.get('RES_Y', 1800))
    if n_frames:
        rr.resolution_x, rr.resolution_y = fw, fh
        for k in range(n_frames):
            place(k / (n_frames - 1))
            render(sc, os.path.join(out, 'fly_%03d.png' % k), int(os.environ.get('FLY_SAMPLES', '16')))
    meta['frames'] = n_frames
    place(1.0)
    rr.resolution_x, rr.resolution_y = fx, fy
    meta['panes'] = [{'tl': uvv(ccam, p['tl']), 'tr': uvv(ccam, p['tr']), 'bl': uvv(ccam, p['bl']), 'aspect': round(p['aspect'], 4),
                      'team': DP.TEAMS[k]} for k, p in enumerate(panes)]
    json.dump(meta, open(os.path.join(out, 'closeup.json'), 'w'))
    if os.environ.get('PROBE'):
        dg = bpy.context.evaluated_depsgraph_get(); fr = ccam.data.view_frame(scene=sc); mw = ccam.matrix_world
        for uv in os.environ['PROBE'].split(';'):
            u_, v_ = map(float, uv.split(','))
            q = fr[3].lerp(fr[0], u_).lerp(fr[2].lerp(fr[1], u_), v_)
            o_ = mw.translation.copy(); d_ = ((mw @ q) - o_).normalized(); hits = []
            for _ in range(8):
                ok, loc, nrm, idx, ob, _m = sc.ray_cast(dg, o_, d_)
                if not ok: hits.append('NONE'); break
                o_ = loc + d_ * 1e-4
                if ob.hide_render: continue
                hits.append('%s@(%.3f,%.3f,%.3f)' % (ob.name, loc.x, loc.y, loc.z))
            print('PROBE', uv, ' -> '.join(hits))
        sys.exit(0)
    if not os.environ.get('SKIP_STILL'):
        render(sc, os.path.join(out, 'design.png'), SAMPLES)
    geo = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT', 'META') and not o.hide_render]
    rr.film_transparent = True; sc.cycles.use_denoising = False
    rr.resolution_x, rr.resolution_y = fx // 2, fy // 2
    for k in range(len(DP.WIN_U)):
        for o in geo:
            o.is_holdout = not o.name.startswith('sash_frost%d' % k)
        render(sc, os.path.join(out, 'pane_%d.png' % k), 4)
    print('DESIGN CLOSEUP DONE', meta)
    sys.exit(0)


# ---------------------------------------------------------------- any other window zoom
def zoom_generic(sc, street_cam, G, zid):
    """A zoom described in zoom_props.ZOOMS: one or more windows, each found by
    the street's glass nearest a point. Their glass becomes frosted and lit
    (with a proper frame where the street's was simple), the camera swings
    from the street round to face them, and each window gets its own mask."""
    import zoom_props as ZP
    spec = ZP.ZOOMS[zid]
    out = os.environ['CLOSE_OUT']; os.makedirs(out, exist_ok=True)
    SAMPLES = G['SAMPLES']
    bpy.context.view_layer.update()
    frost = frosted_glow()
    paint = painted_wood('zoom_frame', spec.get('paint', (0.8, 0.76, 0.66)))
    d0 = ZP.STREET_DIR
    wins = []
    for k, gp in enumerate(spec['glass']):
        g = ZP.find_glass(sc, gp)
        c, t, n, w, h = ZP.frame_of(g, d0)
        wins.append((g, c, t, n, w, h))
    # clear the street's glazing and whatever was behind it
    keep = ('A', 'B', 'C', 'D', 'shutter', 'louvre', 'bay', 'bay_mull', 'bay_post', 'bay_panel', 'bay_sill', 'bay_cornice', 'bay_dentil', 'bay_roof',
            'win_frame', 'win_mull', 'win_box', 'wb_flower', 'trimband', 'cabin', 'board', 'roof', 'hull', 'sill', 'string', 'voussoir', 'lintel')
    for g, c, t, n, w, h in wins:
        g.hide_render = True
        for o in list(sc.objects):
            if o.type not in ('MESH', 'CURVE') or o.name.startswith(('zp_', 'dt_', 'plush')) or o is g: continue
            lo, hi = ZP._bb(o); q = (lo + hi) / 2 - c
            along, depth = q.dot(t), -q.dot(n)
            if abs(along) < w / 2 + 0.01 and -0.03 < depth < 0.9 and abs(q.z) < h / 2 + 0.01:
                base = o.name.split('.')[0]
                if base in ('mull', 'curtain', 'pane', 'win_glass', 'bay_glass') or (depth > 0.004 and base not in keep):
                    o.hide_render = True
    panes = []
    rot_for = lambda n: (math.pi / 2, 0, math.atan2(n.y, n.x) + math.pi / 2)
    for k, (g, c, t, n, w, h) in enumerate(wins):
        P = lambda a, z, o_=0.0: c + t * a + Vector((0, 0, z)) - n * o_
        yaw = math.atan2(t.y, t.x)
        def bx(name, a, z, o_, sa, sz, sd, mat, bev=0.003):
            b_ = box(name, P(a, z, o_), (sa, sd, sz), mat, bevel=bev); b_.rotation_euler = (0, 0, yaw); return b_
        st = min(0.03, w * 0.08)
        top = h / 2
        if spec.get('arch'):
            r = w / 2; zs = h / 2 - r; top = zs
        if spec.get('frame', True):
            for sg in (-1, 1):
                bx('zf_stile', sg * (w / 2 - st / 2), (top - h / 2) / 2, -0.012, st, top + h / 2, 0.03, paint)
            bx('zf_rail', 0, -h / 2 + 0.025, -0.012, w, 0.05, 0.03, paint)
            bx('zf_rail', 0, top - st / 2, -0.012, w, st, 0.03, paint)
            bx('zf_meet', 0, (top - h / 2) / 2 + 0.012, -0.01, 0.03, top + h / 2 - 0.05, 0.034, paint)
            gw = (w - 2 * st - 0.03) / 2
            for sg in (-1, 1):
                ca = sg * (0.015 + gw / 2)
                bx('zf_bar', ca, (top - h / 2) / 2 + 0.012, -0.004, 0.012, top + h / 2 - 0.05, 0.016, paint)
                for f in (1 / 3, 2 / 3):
                    bx('zf_bar', ca, -h / 2 + 0.05 + (top + h / 2 - 0.05) * f, -0.004, gw, 0.012, 0.016, paint)
            if spec.get('arch'):
                for j in range(18):
                    a0, a1 = math.pi * j / 18, math.pi * (j + 1) / 18; am = (a0 + a1) / 2
                    rr = r - st / 2
                    b_ = box('zf_head', P(rr * math.cos(am), zs + rr * math.sin(am), -0.012), ((a1 - a0) * rr * 1.08, 0.03, st), paint, bevel=0.002)
                    b_.rotation_euler = Matrix.Rotation(yaw, 3, 'Z').to_euler() if False else (0, 0, 0)
                    b_.rotation_euler = (Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-(am + math.pi / 2), 3, 'Y')).to_euler()
                for a in (math.pi / 4, math.pi / 2, 3 * math.pi / 4):
                    p0 = P(0, zs, -0.004); p1 = p0 + (t * math.cos(a) + Vector((0, 0, math.sin(a)))) * (r - st)
                    b_ = box('zf_bar', (p0 + p1) / 2, (0.012, 0.016, (p1 - p0).length), paint, bevel=0.002)
                    b_.rotation_euler = (p1 - p0).to_track_quat('Z', 'Y').to_euler()
        # frosted glass, lit from behind
        fo = -spec.get('frost_out', -0.004)
        if spec.get('frame', True):
            fr = box('sash_frost%d' % k, P(0, (top - h / 2) / 2 + 0.012, fo), (w - 2 * st + 0.01, 0.003, top + h / 2 - 0.02), frost, bevel=0)
        else:
            fr = box('sash_frost%d' % k, P(0, 0, fo), (w, 0.003, h), frost, bevel=0)
        fr.rotation_euler = (0, 0, yaw)
        if spec.get('arch'):
            cyl('sash_frost%d' % k, P(0, zs, 0.005), r - st + 0.005, 0.003, frost, verts=40, rot=rot_for(n))
        if not spec.get('frame', True): st = 0.0
        zt = h / 2 - st
        panes.append({'tl': P(-(w / 2 - st), zt), 'tr': P(w / 2 - st, zt), 'bl': P(-(w / 2 - st), -h / 2 + (0.05 if spec.get('frame', True) else 0.0)),
                      'aspect': (w - 2 * st) / (zt + h / 2 - (0.05 if spec.get('frame', True) else 0.0)), 'team': spec['teams'][k]})
    # ---- the camera
    T = sum((c for _, c, *_ in wins), Vector()) / len(wins)
    nm = sum((n for *_, n, w, h in [(x[0], x[1], x[2], x[3], x[4], x[5]) for x in wins]), Vector())
    nm = wins[0][3].copy()
    if spec.get('side') and len(wins) > 1: nm = (wins[0][3] + wins[1][3] * spec['side']).normalized()
    d1 = (nm + Vector((0, 0, spec.get('elev', 0.12)))).normalized()
    W0, W1 = spec['W0'], spec['W1']
    cd = bpy.data.cameras.new('closecam'); cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 300
    ccam = link(bpy.data.objects.new('closecam', cd)); sc.camera = ccam
    ease = lambda x: x * x * (3 - 2 * x)
    def place(x):
        e = ease(x)
        dirv = d0.lerp(d1, e).normalized()
        lens = math.exp(math.log(420) + (math.log(50) - math.log(420)) * e)
        width = W0 + (W1 - W0) * e
        cd.lens = lens
        ccam.location = T + dirv * (width * lens / 36)
        ccam.rotation_euler = (T - ccam.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    uvv = lambda cam, p: (lambda v: [round(v.x, 5), round(1 - v.y, 5)])(world_to_camera_view(sc, cam, p))
    meta = {'street_target': uvv(street_cam, T), 'scale': W0 / 15.5,
            'street_quads': [[uvv(street_cam, c + t * (sa * w / 2) + Vector((0, 0, sz * h / 2))) for sa, sz in ((-1, 1), (1, 1), (1, -1), (-1, -1))]
                             for _, c, t, n, w, h in wins]}
    rr = sc.render
    n_frames = int(os.environ.get('CLOSE_FRAMES', '30'))
    fw, fh = int(os.environ.get('CLOSE_FW', '1440')), int(os.environ.get('CLOSE_FH', '1080'))
    fx, fy = int(os.environ.get('RES_X', 2400)), int(os.environ.get('RES_Y', 1800))
    if n_frames:
        rr.resolution_x, rr.resolution_y = fw, fh
        for j in range(n_frames):
            place(j / (n_frames - 1))
            render(sc, os.path.join(out, 'fly_%03d.png' % j), int(os.environ.get('FLY_SAMPLES', '16')))
    meta['frames'] = n_frames
    place(1.0)
    rr.resolution_x, rr.resolution_y = fx, fy
    meta['panes'] = [{'tl': uvv(ccam, p['tl']), 'tr': uvv(ccam, p['tr']), 'bl': uvv(ccam, p['bl']), 'aspect': round(p['aspect'], 4), 'team': p['team']} for p in panes]
    json.dump(meta, open(os.path.join(out, 'closeup.json'), 'w'))
    if not os.environ.get('SKIP_STILL'):
        render(sc, os.path.join(out, zid + '.png'), SAMPLES)
    geo = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT', 'META') and not o.hide_render]
    rr.film_transparent = True; sc.cycles.use_denoising = False
    rr.resolution_x, rr.resolution_y = fx // 2, fy // 2
    names = ['pane'] if len(wins) == 1 else ['pane_%d' % k for k in range(len(wins))]
    for k, nm_ in enumerate(names):
        for o in geo:
            o.is_holdout = not o.name.startswith('sash_frost%d' % k)
        render(sc, os.path.join(out, nm_ + '.png'), 4)
    print('ZOOM DONE', zid, meta)
    sys.exit(0)
