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
    for (cx, cz, sx, sz) in ((x0 - 0.02, (z0 + z1) / 2, 0.045, h + 0.08), (x1 + 0.02, (z0 + z1) / 2, 0.045, h + 0.08), (xc, z1 + 0.02, w + 0.08, 0.045)):
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
                                 (xc, sz1 - top_rail / 2, w, top_rail), (xc, sz0 + bot_rail / 2, w, bot_rail)):
            box('sash', (cx, yb, cz), (sx, 0.035, sz), paint, bevel=0.005)
        # inner ovolo moulding round the glass
        gz0, gz1 = sz0 + bot_rail, sz1 - top_rail
        for (cx, cz, sx, sz) in ((x0 + st + 0.004, (gz0 + gz1) / 2, 0.008, gz1 - gz0), (x1 - st - 0.004, (gz0 + gz1) / 2, 0.008, gz1 - gz0),
                                 (xc, gz1 - 0.004, w - 2 * st, 0.008), (xc, gz0 + 0.004, w - 2 * st, 0.008)):
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

    # the stuffed toy squirrel on the sill, holding its felt seed
    import plush
    plush.plush_squirrel(Vector((xc + w * 0.2, yf - 0.05, z0 - 0.005)), math.radians(-165), 0.95)

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
