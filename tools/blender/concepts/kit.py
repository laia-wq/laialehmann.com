"""
Small modelling kit for the house concept renders: bevelled boxes with
boolean openings, procedural stucco / wood / stone / tile materials, tiled
roofs, glowing windows, string lights, pots and plants (Poly Haven CC0).
"""
import bpy, bmesh, math, random, glob, os
from mathutils import Vector, Matrix

ASSETS = os.environ.get('ASSETS', '')
R = random.Random(7)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    return sc

def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o

# ------------------------------------------------------------------ materials
_M = {}
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']

def solid(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, coat=0.0):
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    _M[name] = m
    return m

def _noise_bump(n, l, b, scale, strength, detail=6):
    tc = n.new('ShaderNodeTexCoord')
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    return tc, nz

def stucco(name, color, dirt=(0.55, 0.45, 0.38)):
    """Hand-plastered wall: soft blotchy colour, fine bump, darker toward the ground."""
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc, nz = _noise_bump(n, l, b, 18, 0.12)
    big = n.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 2.2; big.inputs['Detail'].default_value = 3
    l.new(tc.outputs['Object'], big.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 0.9 for c in color], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * 1.04) for c in color], 1)
    l.new(big.outputs['Fac'], ramp.inputs['Fac'])
    # grime near the base (object-space z)
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs['Vector'])
    gr = n.new('ShaderNodeMapRange'); gr.inputs['From Min'].default_value = 0.0; gr.inputs['From Max'].default_value = 0.18
    l.new(sep.outputs['Z'], gr.inputs['Value'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['B'].default_value = (*dirt, 1)
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    l.new(gr.outputs['Result'], inv.inputs[1])
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.45
    l.new(inv.outputs['Value'], mul.inputs[0])
    l.new(mul.outputs['Value'], mix.inputs['Factor']); l.new(ramp.outputs['Color'], mix.inputs['A'])
    l.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    _M[name] = m
    return m

def varied(name, base, spread=0.12, rough=0.6, bump=0.0, bump_scale=30.0):
    """Per-object random tint (tiles, planks, stones, pots)."""
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    oi = n.new('ShaderNodeObjectInfo')
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[max(0, c * (1 - spread)) for c in base], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * (1 + spread)) for c in base], 1)
    l.new(oi.outputs['Random'], ramp.inputs['Fac'])
    l.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if bump:
        _noise_bump(n, l, b, bump_scale, bump)
    _M[name] = m
    return m

def wood(name, color, scale=6.0, rough=0.55, axis='X'):
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    mp = n.new('ShaderNodeMapping')
    if axis == 'Z': mp.inputs['Rotation'].default_value = (0, math.pi / 2, 0)
    mp.inputs['Scale'].default_value = (1, 14, 14)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 6
    wv.inputs['Detail'].default_value = 4
    l.new(mp.outputs['Vector'], wv.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 0.72 for c in color], 1)
    ramp.color_ramp.elements[1].color = (*color, 1)
    l.new(wv.outputs['Fac'], ramp.inputs['Fac'])
    oi = n.new('ShaderNodeObjectInfo')
    hsv = n.new('ShaderNodeHueSaturation')
    l.new(ramp.outputs['Color'], hsv.inputs['Color'])
    vm = n.new('ShaderNodeMapRange'); vm.inputs['To Min'].default_value = 0.85; vm.inputs['To Max'].default_value = 1.12
    l.new(oi.outputs['Random'], vm.inputs['Value']); l.new(vm.outputs['Result'], hsv.inputs['Value'])
    l.new(hsv.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.15
    l.new(wv.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough
    _M[name] = m
    return m

def cobbles(name, color, scale=9.0, mortar=(0.3, 0.27, 0.24)):
    """Voronoi cobblestones with dark mortar and per-stone tint."""
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    vo = n.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = scale
    vc = n.new('ShaderNodeTexVoronoi'); vc.inputs['Scale'].default_value = scale
    l.new(tc.outputs['Object'], vo.inputs['Vector']); l.new(tc.outputs['Object'], vc.inputs['Vector'])
    edge = n.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = 0.0; edge.inputs['From Max'].default_value = 0.09
    l.new(vo.outputs['Distance'], edge.inputs['Value'])
    tint = n.new('ShaderNodeValToRGB')
    tint.color_ramp.elements[0].color = (*[c * 0.75 for c in color], 1)
    tint.color_ramp.elements[1].color = (*[min(1, c * 1.15) for c in color], 1)
    sep = n.new('ShaderNodeSeparateColor'); l.new(vc.outputs['Color'], sep.inputs['Color'])
    l.new(sep.outputs['Red'], tint.inputs['Fac'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*mortar, 1)
    l.new(edge.outputs['Result'], mix.inputs['Factor']); l.new(tint.outputs['Color'], mix.inputs['B'])
    l.new(mix.outputs['Result'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.7; bp.inputs['Distance'].default_value = 0.02
    l.new(edge.outputs['Result'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.8
    _M[name] = m
    return m

def bricks(name, color, scale=4.0, mortar=(0.62, 0.58, 0.52)):
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    br = n.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = scale
    br.inputs['Mortar Size'].default_value = 0.025; br.inputs['Brick Width'].default_value = 0.6; br.inputs['Row Height'].default_value = 0.28
    br.inputs['Color1'].default_value = (*color, 1); br.inputs['Color2'].default_value = (*[c * 0.78 for c in color], 1)
    br.inputs['Mortar'].default_value = (*mortar, 1)
    l.new(tc.outputs['Object'], br.inputs['Vector'])
    l.new(br.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5
    l.new(br.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.85
    _M[name] = m
    return m

def glass_glow(name='window_glow', color=(1.0, 0.62, 0.28), strength=4.0):
    """A lit window seen from outside: warm glow with a gradient, like a lamp inside."""
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 1.0 for c in color], 1)
    ramp.color_ramp.elements[1].color = (*[c * 0.55 for c in color], 1)
    l.new(sep.outputs['Z'], ramp.inputs['Fac'])
    l.new(ramp.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = strength
    b.inputs['Base Color'].default_value = (0.05, 0.04, 0.03, 1)
    b.inputs['Roughness'].default_value = 0.08
    _M[name] = m
    return m

# ------------------------------------------------------------------ geometry
def box(name, loc, size, mat, bevel=0.02, seg=3, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.location = loc; o.rotation_euler = rot
    if mat: me.materials.append(mat)
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
        md.harden_normals = False
    for p in me.polygons: p.use_smooth = True
    return o

def cyl(name, loc, r, h, mat, verts=24, r2=None, bevel=0.0, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    if mat: me.materials.append(mat)
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
    for p in me.polygons: p.use_smooth = True
    return o

def sphere(name, loc, r, mat, seg=16, scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.scale = scale
    if mat: me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return o

def cut(target, cutter):
    """Boolean-difference `cutter` out of `target` (cutter hidden)."""
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cutter
    cutter.hide_render = True; cutter.hide_viewport = True
    bev = target.modifiers.get('bev')
    if bev:  # keep the bevel after every boolean
        target.modifiers.move(list(target.modifiers).index(bev), len(target.modifiers) - 1)
    return target

def arch_cutter(name, loc, w, h, depth, axis='y'):
    """Cutter for an arched opening: rectangle + half-round top. Opening faces ±axis."""
    rect = box(name + '_r', (loc[0], loc[1], loc[2] + (h - w / 2) / 2), (w, depth, h - w / 2) if axis == 'y' else (depth, w, h - w / 2), None, bevel=0)
    rot = (math.pi / 2, 0, 0) if axis == 'y' else (0, math.pi / 2, 0)
    top = cyl(name + '_t', (loc[0], loc[1], loc[2] + h - w / 2), w / 2, depth, None, verts=32, rot=rot)
    return rect, top

def window(wall, centre, w, h, axis='y', side=1, arched=False, frame_mat=None, sill_mat=None, shutters=None, glow=True, depth=0.5):
    """Cut a window into `wall` and dress it: recessed glowing pane, frame with
    mullions, sill, optional shutters. `axis` is the wall normal axis, `side` its sign."""
    x, y, z = centre
    if arched:
        a, b = arch_cutter('wc', (x, y, z), w, h, depth, axis)
        cut(wall, a); cut(wall, b)
    else:
        c = box('wc', (x, y, z + h / 2), (w, depth, h) if axis == 'y' else (depth, w, h), None, bevel=0)
        cut(wall, c)
    off = Vector((0, -side * 0.06, 0)) if axis == 'y' else Vector((-side * 0.06, 0, 0))
    pane_size = (w, 0.02, h) if axis == 'y' else (0.02, w, h)
    pane = box('pane', Vector((x, y, z + h / 2)) + off, pane_size, glass_glow() if glow else solid('dark_glass', (0.05, 0.07, 0.08), 0.05), bevel=0)
    fm = frame_mat or solid('frame', (0.42, 0.26, 0.16), 0.5)
    t = 0.035
    def fbox(dx, dz, sx, sz):
        p = Vector((x, y, z)) + off * 0.7 + (Vector((dx, 0, dz)) if axis == 'y' else Vector((0, dx, dz)))
        s = (sx, 0.05, sz) if axis == 'y' else (0.05, sx, sz)
        box('frame', p, s, fm, bevel=0.006, seg=1)
    top = h - (w / 2 if arched else 0)
    fbox(-w / 2 + t / 2, top / 2, t, top); fbox(w / 2 - t / 2, top / 2, t, top)
    fbox(0, top / 2, t * 0.7, top); fbox(0, top * 0.55, w, t * 0.7)
    fbox(0, t / 2, w, t)
    if not arched: fbox(0, h - t / 2, w, t)
    if sill_mat:
        so = Vector((0, side * 0.05, 0)) if axis == 'y' else Vector((side * 0.05, 0, 0))
        box('sill', Vector((x, y, z - 0.03)) + so, (w + 0.14, 0.2, 0.06) if axis == 'y' else (0.2, w + 0.14, 0.06), sill_mat, bevel=0.012)
    if shutters:
        for sgn in (-1, 1):
            so = Vector((0, side * 0.04, 0)) if axis == 'y' else Vector((side * 0.04, 0, 0))
            p = Vector((x, y, z + h / 2)) + so + (Vector((sgn * (w * 0.75 + 0.03), 0, 0)) if axis == 'y' else Vector((0, sgn * (w * 0.75 + 0.03), 0)))
            s = (w / 2, 0.035, h * 0.98) if axis == 'y' else (0.035, w / 2, h * 0.98)
            sh = box('shutter', p, s, shutters, bevel=0.008, seg=1)
            # louvres
            for k in range(int(h / 0.07)):
                lp = p + Vector((0, 0, -h / 2 + 0.05 + k * 0.07)) + (Vector((0, side * 0.02, 0)) if axis == 'y' else Vector((side * 0.02, 0, 0)))
                box('louvre', lp, (w / 2 * 0.86, 0.015, 0.03) if axis == 'y' else (0.015, w / 2 * 0.86, 0.03), shutters, bevel=0.004, seg=1)
    return pane

def tiled_roof(name, x0, x1, y0, y1, z0, ridge_z, mat, along='x', tile_w=0.16, tile_l=0.26, overhang=0.18):
    """Gabled roof of half-round terracotta tiles. Ridge runs along `along`."""
    tile = bpy.data.meshes.new('tile')
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=10, radius1=tile_w * 0.55, radius2=tile_w * 0.5, depth=tile_l)
    # keep upper half → half-round tile
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -1e-4], context='VERTS')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.018)
    bm.to_mesh(tile); bm.free()
    for p in tile.polygons: p.use_smooth = True
    tile.materials.append(mat)
    under = solid('roof_under', (0.35, 0.2, 0.14), 0.8)
    objs = []
    if along == 'x':
        span_lo, span_hi, mid = y0 - overhang, y1 + overhang, (y0 + y1) / 2
        L0, L1 = x0 - overhang, x1 + overhang
    else:
        span_lo, span_hi, mid = x0 - overhang, x1 + overhang, (x0 + x1) / 2
        L0, L1 = y0 - overhang, y1 + overhang
    half = (span_hi - span_lo) / 2
    rise = ridge_z - z0
    ang = math.atan2(rise, half)
    slope_len = math.hypot(half, rise)
    for sgn in (-1, 1):
        # deck under the tiles
        dl = (L1 - L0, slope_len, 0.05) if along == 'x' else (slope_len, L1 - L0, 0.05)
        cx = (L0 + L1) / 2 if along == 'x' else mid + sgn * half / 2
        cy = mid + sgn * half / 2 if along == 'x' else (L0 + L1) / 2
        rot = (sgn * ang, 0, 0) if along == 'x' else (0, -sgn * ang, 0)
        box(name + '_deck', (cx, cy, z0 + rise / 2 - 0.04), dl, under, bevel=0.01, rot=rot)
        nrow = int(slope_len / (tile_l * 0.8))
        ncol = int((L1 - L0) / tile_w)
        for i in range(ncol):
            for j in range(nrow):
                for flip in (0, 1):  # under (concave) and over (convex) courses
                    if flip and i == ncol - 1: continue
                    t = (j + 0.5) / nrow
                    d = half * (1 - t)
                    zz = z0 + rise * t + 0.02 + (0.03 if flip else 0)
                    u = L0 + (i + 0.5 + 0.5 * flip) * tile_w
                    o = link(bpy.data.objects.new('tile', tile))
                    if along == 'x':
                        o.location = (u, mid + sgn * d, zz)
                        o.rotation_euler = Matrix.Rotation(sgn * ang, 4, 'X').to_euler()
                        o.rotation_euler.rotate(Matrix.Rotation(math.pi / 2, 4, 'X').to_euler())
                        base = (math.pi / 2 + sgn * ang if sgn > 0 else -math.pi / 2 + sgn * ang)
                        o.rotation_euler = (math.pi / 2 - sgn * (math.pi / 2 - ang) * 0 + (sgn * ang), 0, 0)
                        o.rotation_euler = (math.pi / 2 + sgn * ang if True else 0, (0 if flip else math.pi), 0)
                        o.rotation_euler.rotate_axis('Y', math.pi / 2)
                    else:
                        o.location = (mid + sgn * d, u, zz)
                        o.rotation_euler = (0, math.pi / 2 - sgn * ang, 0)
                        o.rotation_euler.rotate_axis('Z', (0 if not flip else math.pi) + math.pi / 2)
                    o.rotation_euler.z += R.uniform(-0.04, 0.04)
                    objs.append(o)
    # ridge cap
    rl = L1 - L0
    cap = cyl(name + '_ridge', ((L0 + L1) / 2, mid, ridge_z + 0.05) if along == 'x' else (mid, (L0 + L1) / 2, ridge_z + 0.05),
              tile_w * 0.7, rl, mat, verts=14, rot=(0, math.pi / 2, 0) if along == 'x' else (math.pi / 2, 0, 0))
    return objs

def catenary(a, b, sag, n=24):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, t) + Vector((0, 0, -sag * 4 * t * (1 - t))) for t in (i / (n - 1) for i in range(n))]

def string_lights(a, b, sag=0.35, bulbs=12, color=(1.0, 0.78, 0.45)):
    pts = catenary(a, b, sag, 40)
    cu = bpy.data.curves.new('wire', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.006
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (*q, 1)
    o = link(bpy.data.objects.new('wire', cu)); cu.materials.append(solid('wire', (0.05, 0.05, 0.05), 0.5))
    bm = solid('bulb', (1, 0.9, 0.7), 0.3, emit=color, strength=18)
    for i in range(bulbs):
        t = (i + 0.5) / bulbs
        p = catenary(a, b, sag, 2)[0].lerp(Vector(b), t) + Vector((0, 0, -sag * 4 * t * (1 - t) - 0.04))
        sphere('bulb', p, 0.035, bm, seg=10)

def lantern(loc, s=1.0):
    metal = solid('lantern_metal', (0.06, 0.05, 0.045), 0.4, metal=0.8)
    x, y, z = loc
    box('lantern_cap', (x, y, z + 0.16 * s), (0.16 * s, 0.16 * s, 0.04 * s), metal, bevel=0.01)
    cyl('lantern_top', (x, y, z + 0.2 * s), 0.08 * s, 0.06 * s, metal, verts=4, r2=0.01)
    box('lantern_glow', (x, y, z + 0.05 * s), (0.11 * s, 0.11 * s, 0.18 * s), solid('lantern_glass', (1, 0.8, 0.5), 0.2, emit=(1.0, 0.65, 0.3), strength=14), bevel=0.004)
    for dx in (-1, 1):
        for dy in (-1, 1):
            box('lantern_post', (x + dx * 0.065 * s, y + dy * 0.065 * s, z + 0.05 * s), (0.015 * s, 0.015 * s, 0.2 * s), metal, bevel=0)
    box('lantern_base', (x, y, z - 0.06 * s), (0.14 * s, 0.14 * s, 0.03 * s), metal, bevel=0.008)
    L = bpy.data.lights.new('lantern_l', 'POINT'); L.energy = 18 * s; L.color = (1, 0.62, 0.3); L.shadow_soft_size = 0.05
    lo = link(bpy.data.objects.new('lantern_l', L)); lo.location = (x, y, z + 0.05 * s)

def room_light(loc, energy=60, color=(1, 0.66, 0.36), size=0.3):
    L = bpy.data.lights.new('room', 'POINT'); L.energy = energy; L.color = color; L.shadow_soft_size = size
    o = link(bpy.data.objects.new('room', L)); o.location = loc
    return o

# ------------------------------------------------------------------ plants
_LIB = {}
def asset(name):
    if name in _LIB: return _LIB[name]
    f = glob.glob(os.path.join(ASSETS, name, 'blend', '*.blend'))[0]
    with bpy.data.libraries.load(f, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    objs = [o for o in dst.objects if o and o.type == 'MESH']
    for o in objs:
        o.matrix_world = Matrix.Identity(4); o.parent = None
    _LIB[name] = objs
    return objs

def plant(name, loc, height, rot=None, pick=None, tilt=0.0):
    # skip flat helper meshes (ground cards, decals) that would scale up hugely
    objs = [o for o in asset(name) if o.dimensions.z > 0.25 * max(o.dimensions.x, o.dimensions.y, 1e-4)] or asset(name)
    src = objs[pick % len(objs)] if pick is not None else R.choice(objs)
    o = link(bpy.data.objects.new(name, src.data))
    d = src.dimensions
    s = height / max(d.z, 0.35 * max(d.x, d.y), 1e-4)
    o.scale = (s, s, s)
    o.location = loc
    o.rotation_euler = (R.uniform(-tilt, tilt), R.uniform(-tilt, tilt), R.uniform(0, 6.28) if rot is None else rot)
    return o

def pot(loc, r=0.16, h=0.26, plant_name='shrub_03', plant_h=0.5, mat=None):
    m = mat or varied('terracotta_pot', (0.62, 0.3, 0.17), 0.12, 0.75, bump=0.1)
    x, y, z = loc
    cyl('pot', (x, y, z + h / 2), r * 0.78, h, m, verts=24, r2=r, bevel=0.01)
    cyl('pot_rim', (x, y, z + h - 0.015), r * 1.08, 0.05, m, verts=24, bevel=0.01)
    cyl('soil', (x, y, z + h - 0.03), r * 0.95, 0.02, solid('soil', (0.12, 0.08, 0.05), 0.9), verts=20)
    if plant_name:
        plant(plant_name, (x, y, z + h - 0.04), plant_h)

LEAF = {}
def leaf_mesh(color_name='ivy', color=(0.16, 0.32, 0.08)):
    if color_name in LEAF: return LEAF[color_name]
    me = bpy.data.meshes.new('leaf')
    bm = bmesh.new()
    # a small cupped heart-ish leaf
    pts = [(0, 0, 0), (0.035, 0.03, 0.006), (0.03, 0.065, 0.01), (0, 0.085, 0.004), (-0.03, 0.065, 0.01), (-0.035, 0.03, 0.006)]
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    bm.to_mesh(me); bm.free()
    m = varied('leaf_' + color_name, color, 0.35, 0.55)
    m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.0
    me.materials.append(m)
    LEAF[color_name] = me
    return me

def ivy_patch(origin, normal, width, height, density=600, color_name='ivy', color=(0.16, 0.32, 0.08), droop=0.0):
    """Leaves scattered over a wall rectangle (origin = bottom centre), thicker at the bottom."""
    me = leaf_mesh(color_name, color)
    n = Vector(normal).normalized()
    side = Vector((0, 0, 1)).cross(n).normalized()
    for i in range(density):
        u = R.uniform(-0.5, 0.5)
        v = R.random() ** (1.4 if droop == 0 else 0.6)
        if droop: v = 1 - v
        # ragged outline: narrower toward the top
        if abs(u) > 0.5 * (1 - 0.6 * (v if droop == 0 else 1 - v)) + R.uniform(-0.08, 0.08): continue
        p = Vector(origin) + side * u * width + Vector((0, 0, v * height)) + n * R.uniform(0.01, 0.07)
        o = link(bpy.data.objects.new('leaf', me))
        o.location = p
        o.rotation_euler = (R.uniform(0.6, 2.2), R.uniform(-0.6, 0.6), math.atan2(n.y, n.x) + math.pi / 2 + R.uniform(-1, 1))
        s = R.uniform(0.7, 1.4); o.scale = (s, s, s)

def hanging_ivy(top, normal, width, length, strands=10, color_name='ivy', color=(0.16, 0.32, 0.08)):
    me = leaf_mesh(color_name, color)
    n = Vector(normal).normalized(); side = Vector((0, 0, 1)).cross(n).normalized()
    for s in range(strands):
        u = R.uniform(-0.5, 0.5) * width
        L = length * R.uniform(0.4, 1.0)
        k = int(L / 0.03)
        for j in range(k):
            t = j / max(1, k - 1)
            p = Vector(top) + side * (u + math.sin(t * 6 + s) * 0.03) + n * (0.03 + 0.04 * math.sin(t * 3 + s)) - Vector((0, 0, t * L))
            for _ in range(2):
                o = link(bpy.data.objects.new('leaf', me))
                o.location = p + Vector((R.uniform(-0.02, 0.02), R.uniform(-0.02, 0.02), 0))
                o.rotation_euler = (R.uniform(1.4, 2.8), R.uniform(-0.6, 0.6), math.atan2(n.y, n.x) + math.pi / 2 + R.uniform(-1.2, 1.2))
                sc = R.uniform(0.7, 1.2) * (1 - 0.3 * t); o.scale = (sc, sc, sc)

# ------------------------------------------------------------------ stage, light, camera
def diorama_base(cx, cy, sx, sy, top_mat, z=0.0, thick=0.35, edge_mat=None):
    em = edge_mat or varied('base_stone', (0.55, 0.5, 0.45), 0.18, 0.8, bump=0.3)
    box('base', (cx, cy, z - thick / 2 - 0.02), (sx, sy, thick), em, bevel=0.04)
    top = box('ground', (cx, cy, z - 0.02), (sx - 0.02, sy - 0.02, 0.04), top_mat, bevel=0.01)
    # chunky edge blocks along the front edges
    for i in range(int(sx / 0.42)):
        x = cx - sx / 2 + 0.21 + i * 0.42
        box('edge', (x + R.uniform(-0.02, 0.02), cy - sy / 2 + 0.02, z - 0.08), (0.4, 0.14, 0.2 + R.uniform(-0.03, 0.03)), em, bevel=0.03)
    for i in range(int(sy / 0.42)):
        y = cy - sy / 2 + 0.21 + i * 0.42
        box('edge', (cx - sx / 2 + 0.02, y + R.uniform(-0.02, 0.02), z - 0.08), (0.14, 0.4, 0.2 + R.uniform(-0.03, 0.03)), em, bevel=0.03)
    return top

def lighting(sc, sun_rot=(math.radians(52), 0, math.radians(-38)), sun_energy=3.2, sun_color=(1.0, 0.82, 0.62),
             bg_top=(0.45, 0.62, 0.62), bg_bottom=(0.78, 0.85, 0.78), hdri_strength=0.35):
    S = bpy.data.lights.new('sun', 'SUN'); S.energy = sun_energy; S.color = sun_color; S.angle = math.radians(6)
    so = link(bpy.data.objects.new('sun', S)); so.rotation_euler = sun_rot
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    n, l = w.node_tree.nodes, w.node_tree.links
    bg = n['Background']
    hdr = glob.glob(os.path.join(ASSETS, 'hdri', '*.hdr'))
    env = n.new('ShaderNodeTexEnvironment')
    if hdr: env.image = bpy.data.images.load(hdr[0])
    l.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = hdri_strength
    # camera sees a soft gradient backdrop
    lp = n.new('ShaderNodeLightPath')
    grad_bg = n.new('ShaderNodeBackground')
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Window'], sep.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*bg_bottom, 1); ramp.color_ramp.elements[1].color = (*bg_top, 1)
    l.new(sep.outputs['Y'], ramp.inputs['Fac']); l.new(ramp.outputs['Color'], grad_bg.inputs['Color'])
    mix = n.new('ShaderNodeMixShader')
    l.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac']); l.new(bg.outputs['Background'], mix.inputs[1]); l.new(grad_bg.outputs['Background'], mix.inputs[2])
    l.new(mix.outputs['Shader'], n['World Output'].inputs['Surface'])

def iso_camera(sc, target, scale, yaw=45, pitch=58, res=(1400, 1050)):
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = scale; cd.clip_end = 200
    cam = link(bpy.data.objects.new('cam', cd)); sc.camera = cam
    yawr, pr = math.radians(yaw), math.radians(pitch)
    d = Vector((math.sin(yawr) * math.sin(pr), -math.cos(yawr) * math.sin(pr), math.cos(pr)))
    cam.location = Vector(target) + d * 40
    cam.rotation_euler = (pr, 0, yawr)
    sc.render.resolution_x, sc.render.resolution_y = res
    return cam

def render(sc, path, samples=96):
    sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def tile_mat(name, color):
    if name in _M: return _M[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    br = n.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 0.16; br.inputs['Row Height'].default_value = 0.22; br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Color1'].default_value = (*color, 1); br.inputs['Color2'].default_value = (*[c * 0.8 for c in color], 1)
    br.inputs['Mortar'].default_value = (*[c * 0.35 for c in color], 1)
    l.new(tc.outputs['UV'], br.inputs['Vector'])
    wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.inputs['Scale'].default_value = 1.0
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6.25, 0.0, 0)
    l.new(tc.outputs['UV'], mp.inputs['Vector']); l.new(mp.outputs['Vector'], wv.inputs['Vector'])
    mx = n.new('ShaderNodeMath'); mx.operation = 'ADD'
    l.new(br.outputs['Fac'], mx.inputs[0]); l.new(wv.outputs['Fac'], mx.inputs[1])
    l.new(br.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.9; bp.inputs['Distance'].default_value = 0.05
    l.new(mx.outputs['Value'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.7
    _M[name] = m
    return m

def gable_roof(name, cx, cy, lx, ly, z0, rise, mat, over=0.2, thick=0.08):
    """Gabled roof with ridge along x; UVs in metres so tile texture keeps scale."""
    hx, hy = lx / 2 + over, ly / 2 + over
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    for sgn in (-1, 1):
        a = Vector((cx - hx, cy + sgn * hy, z0)); b_ = Vector((cx + hx, cy + sgn * hy, z0))
        c = Vector((cx + hx, cy, z0 + rise)); d = Vector((cx - hx, cy, z0 + rise))
        vs = [bm.verts.new(p) for p in (a, b_, c, d)]
        f = bm.faces.new(vs if sgn < 0 else vs[::-1])
        sl = math.hypot(hy, rise)
        for lp, (u, v) in zip(f.loops, ([(0, 0), (2 * hx, 0), (2 * hx, sl), (0, sl)] if sgn < 0 else [(0, sl), (2 * hx, sl), (2 * hx, 0), (0, 0)])):
            lp[uv].uv = (u, v)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); me.materials.append(mat)
    so = o.modifiers.new('sol', 'SOLIDIFY'); so.thickness = thick; so.offset = -1
    cyl(name + '_ridge', (cx, cy, z0 + rise + 0.03), 0.09, 2 * hx, mat, verts=12, rot=(0, math.pi / 2, 0))
    return o
