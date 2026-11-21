"""Canal block v2: four old buildings in canal water, each with its own window
style and lived-in windows (curtains, plants, silhouettes, a cat, candles),
old brick, boats of all kinds instead of plank walkways, many kinds of lamps.
Usage: ASSETS=<assets-raw> python canal2.py <out.png> [samples]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

ARGS = [a for a in sys.argv if not a.startswith('-')]
OUT, SAMPLES = ARGS[-2], int(ARGS[-1])
sc = reset()
from garden import *
from canal_kit import *

RG = random.Random(52)
brass_d = solid('brass_d', (0.6, 0.45, 0.22), 0.35, metal=1)
cloths = [(0.55, 0.16, 0.14), (0.75, 0.62, 0.38), (0.3, 0.38, 0.5), (0.72, 0.68, 0.6), (0.36, 0.45, 0.3), (0.62, 0.35, 0.45)]
silhouette_m = solid('silhouette', (0.02, 0.02, 0.02), 0.9)
lamp_glow = solid('lamp_glow', (1, 0.85, 0.6), 0.3, emit=(1.0, 0.62, 0.28), strength=10)

def old_bricks(name, base, soot=0.35, scale=5.5):
    """Brick that lies flat on every wall (box-projected by face normal), with
    per-brick colour variation and soot creeping down from the top."""
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord'); geo = n.new('ShaderNodeNewGeometry')
    pos = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], pos.inputs['Vector'])
    nrm = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], nrm.inputs['Vector'])
    ab = n.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; l.new(nrm.outputs['X'], ab.inputs[0])
    gt = n.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5; l.new(ab.outputs['Value'], gt.inputs[0])
    mixu = n.new('ShaderNodeMix'); mixu.data_type = 'FLOAT'
    l.new(gt.outputs['Value'], mixu.inputs['Factor']); l.new(pos.outputs['X'], mixu.inputs['A']); l.new(pos.outputs['Y'], mixu.inputs['B'])
    comb = n.new('ShaderNodeCombineXYZ'); l.new(mixu.outputs['Result'], comb.inputs['X']); l.new(pos.outputs['Z'], comb.inputs['Y'])
    br = n.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = scale
    br.inputs['Mortar Size'].default_value = 0.018; br.inputs['Brick Width'].default_value = 0.5; br.inputs['Row Height'].default_value = 0.18
    br.inputs['Color1'].default_value = (*base, 1); br.inputs['Color2'].default_value = (*[c * 0.7 for c in base], 1)
    br.inputs['Mortar'].default_value = (0.32, 0.3, 0.27, 1)
    l.new(comb.outputs['Vector'], br.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; l.new(tc.outputs['Object'], nz.inputs['Vector'])
    st = n.new('ShaderNodeMapRange'); st.inputs['From Min'].default_value = 0.35; st.inputs['From Max'].default_value = 0.75
    l.new(nz.outputs['Fac'], st.inputs['Value'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (0.06, 0.05, 0.05, 1)
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = soot
    l.new(st.outputs['Result'], mul.inputs[0]); l.new(mul.outputs['Value'], mx.inputs['Factor'])
    l.new(br.outputs['Color'], mx.inputs['A']); l.new(mx.outputs['Result'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    l.new(br.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.88
    return m

# ------------------------------------------------------------------ windows with lives behind them
class Wall:
    """A facade: origin on the wall plane, outward normal n, tangent t."""
    def __init__(s, obj, axis, plane):
        s.obj = obj
        s.n = Vector((0, -1, 0)) if axis == 'y' else Vector((1, 0, 0))
        s.t = Vector((1, 0, 0)) if axis == 'y' else Vector((0, 1, 0))
        s.axis, s.plane = axis, plane
    def P(s, u, out, z):
        return (Vector((u, s.plane, z)) if s.axis == 'y' else Vector((s.plane, u, z))) + s.n * out
    def S(s, along, thick, up):
        return (along, thick, up) if s.axis == 'y' else (thick, along, up)

def life(W, u, z, w, h, frame):
    """Props just inside a lit window, dark against the glow: a person, a cat,
    plants, curtains, a lamp, a candle, books."""
    r = RG.random()
    inside = -0.05
    if RG.random() < 0.6:   # curtains, often half drawn
        col = RG.choice(cloths); cw = w * RG.uniform(0.18, 0.32)
        for sg in (-1, 1):
            if RG.random() < 0.85:
                box('curtain', W.P(u + sg * (w / 2 - cw / 2), inside, z + h / 2), W.S(cw, 0.01, h * 0.96), varied('curtain%d' % cloths.index(col), col, 0.06, 0.95), bevel=0)
    if r < 0.22:            # someone standing at the window
        sphere('head', W.P(u + RG.uniform(-w / 5, w / 5), inside - 0.02, z + h * 0.72), 0.06, silhouette_m, 12, (1, 1, 1.15))
        sphere('body', W.P(u + RG.uniform(-w / 6, w / 6), inside - 0.02, z + h * 0.32), 0.11, silhouette_m, 12, (1, 0.6, 1.9))
    elif r < 0.38:          # a cat on the outside sill
        c = W.P(u + RG.uniform(-w / 4, w / 4), 0.09, z + 0.05)
        sphere('cat_body', c, 0.06, silhouette_m, 12, (1.3, 0.8, 0.9) if W.axis == 'y' else (0.8, 1.3, 0.9))
        hd = c + W.t * 0.08 + Vector((0, 0, 0.06))
        sphere('cat_head', hd, 0.038, silhouette_m, 10)
        for sg in (-1, 1):
            cyl('cat_ear', hd + W.t * sg * 0.02 + Vector((0, 0, 0.035)), 0.014, 0.03, silhouette_m, verts=4, r2=0.0)
        limb(c - W.t * 0.07, c - W.t * 0.12 + Vector((0, 0, -0.1)), 0.008, silhouette_m)
    elif r < 0.6:           # potted plants on the inner sill
        for k in range(RG.randint(1, 3)):
            p = W.P(u - w / 3 + k * w / 3, inside, z + 0.02)
            cyl('ipot', p + Vector((0, 0, 0.04)), 0.035, 0.08, varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8), verts=10)
            sphere('ileaves', p + Vector((0, 0, 0.13)), RG.uniform(0.05, 0.08), solid('ileaf', (0.06, 0.1, 0.04), 0.7), 10, (1, 1, 1.3))
    elif r < 0.75:          # a table lamp with its shade
        p = W.P(u + RG.uniform(-w / 4, w / 4), inside, z + 0.02)
        cyl('lamp_stem', p + Vector((0, 0, 0.07)), 0.008, 0.14, silhouette_m, verts=6)
        cyl('lamp_shade', p + Vector((0, 0, 0.17)), 0.06, 0.08, lamp_glow, verts=14, r2=0.035)
    elif r < 0.88:          # a candle on the outer sill
        p = W.P(u, 0.09, z + 0.02)
        cyl('candle', p + Vector((0, 0, 0.04)), 0.015, 0.07, solid('wax', (0.9, 0.85, 0.75), 0.6), verts=8)
        sphere('flame', p + Vector((0, 0, 0.09)), 0.01, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1.0, 0.65, 0.25), strength=30), 6, (1, 1, 1.8))
        L = bpy.data.lights.new('candle', 'POINT'); L.energy = 0.6; L.color = (1, 0.6, 0.25)
        link(bpy.data.objects.new('candle', L)).location = p + Vector((0, 0, 0.1))
    else:                   # stacked books
        p = W.P(u + w / 4, inside, z + 0.02)
        for k in range(4):
            box('book', p + Vector((0, 0, 0.015 + k * 0.025)), W.S(0.12, 0.08, 0.022), varied('ibook%d' % k, RG.choice(cloths), 0.2, 0.7), bevel=0.002)

def window(W, u, z, w, h, style, lit=True, shutters=None, balcony=False, flowers=False):
    """Window styles: 'sash' (2x2), 'arch' (tall, arched), 'casement' (3x3 small
    panes), 'bay' (projecting box). Cut, pane, frame, sill, then life."""
    obj = W.obj
    if style == 'arch':
        r = w / 2
        cut(obj, box('wc', W.P(u, 0, z + (h - r) / 2), W.S(w, 0.9, h - r), None, bevel=0))
        cy_ = cyl('wct', W.P(u, 0, z + h - r), r, 0.9, None, verts=24, rot=(math.pi / 2, 0, 0) if W.axis == 'y' else (0, math.pi / 2, 0))
        cut(obj, cy_)
    elif style != 'bay':
        cut(obj, box('wc', W.P(u, 0, z + h / 2), W.S(w, 0.9, h), None, bevel=0))
    fr = solid('frame_' + style, {'sash': (0.78, 0.74, 0.66), 'arch': (0.16, 0.22, 0.18), 'casement': (0.25, 0.17, 0.12), 'bay': (0.32, 0.12, 0.1)}[style], 0.55)
    rec = -0.08
    if style == 'bay':
        bw, bd = w + 0.2, 0.32
        box('bay', W.P(u, bd / 2, z + h / 2), W.S(bw, bd, h + 0.25), fr, bevel=0.015)
        box('bay_roof', W.P(u, bd / 2 + 0.02, z + h + 0.18), W.S(bw + 0.1, bd + 0.12, 0.06), varied('bay_roofm', (0.18, 0.19, 0.22), 0.1, 0.6), bevel=0.01)
        box('bay_glass', W.P(u, bd + 0.005, z + h / 2 + 0.02), W.S(w, 0.01, h * 0.8), glow if lit else dark_win, bevel=0)
        for k in range(4):
            box('bay_mull', W.P(u - w / 2 + k * w / 3, bd + 0.012, z + h / 2 + 0.02), W.S(0.025, 0.02, h * 0.82), fr, bevel=0)
        if lit:
            room_light(tuple(W.P(u, -0.3, z + h / 2)), 16)
        return
    box('pane', W.P(u, rec, z + h / 2), W.S(w, 0.01, h), glow if lit else dark_win, bevel=0)
    t = 0.028
    top = h - (w / 2 if style == 'arch' else 0)
    cols, rows = {'sash': (2, 2), 'arch': (2, 3), 'casement': (3, 3)}[style]
    for k in range(cols + 1):
        box('mull', W.P(u - w / 2 + k * w / cols, rec + 0.01, z + top / 2), W.S(t, 0.025, top), fr, bevel=0)
    for k in range(rows + 1):
        box('mull', W.P(u, rec + 0.01, z + k * top / rows), W.S(w, 0.025, t), fr, bevel=0)
    if style == 'arch':
        box('mull', W.P(u, rec + 0.01, z + top + w / 4), W.S(t, 0.025, w / 2), fr, bevel=0)
    # sill and lintel: stone on brick, timber on plaster
    box('sill', W.P(u, 0.05, z - 0.03), W.S(w + 0.12, 0.12, 0.05), quay, bevel=0.008)
    if style != 'arch':
        box('lintel', W.P(u, 0.02, z + h + 0.06), W.S(w + 0.14, 0.06, 0.12), quay if style == 'sash' else timber_h, bevel=0.008)
    else:
        for k in range(9):  # brick voussoirs round the arch
            a = math.pi * k / 8
            box('voussoir', W.P(u + math.cos(a) * (w / 2 + 0.05), 0.02, z + top + math.sin(a) * (w / 2 + 0.05)), W.S(0.06, 0.05, 0.12),
                varied('voussoir', (0.42, 0.24, 0.17), 0.12, 0.85), bevel=0.005).rotation_euler.rotate_axis('Y' if W.axis == 'y' else 'X', -(a - math.pi / 2) if W.axis == 'y' else (a - math.pi / 2))
    if shutters:
        for sg in (-1, 1):
            b = box('shutter', W.P(u + sg * (w * 0.75 + 0.02), 0.03, z + top / 2), W.S(w / 2, 0.03, top), shutters, bevel=0.005)
            for k in range(int(top / 0.06)):
                box('louvre', W.P(u + sg * (w * 0.75 + 0.02), 0.05, z + 0.04 + k * 0.06), W.S(w / 2 - 0.04, 0.012, 0.025), shutters, bevel=0)
    if balcony:
        box('juliet', W.P(u, 0.14, z + 0.02), W.S(w + 0.2, 0.24, 0.04), quay, bevel=0.006)
        for k in range(int((w + 0.2) / 0.06) + 1):
            box('jbar', W.P(u - (w + 0.2) / 2 + k * 0.06, 0.25, z + 0.2), W.S(0.01, 0.01, 0.34), iron, bevel=0)
        box('jrail', W.P(u, 0.25, z + 0.37), W.S(w + 0.2, 0.02, 0.02), iron, bevel=0)
        if RG.random() < 0.6:
            cyl('jpot', tuple(W.P(u - w / 3, 0.15, z + 0.08)), 0.04, 0.08, varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8), verts=10)
            sphere('jgeranium', tuple(W.P(u - w / 3, 0.15, z + 0.15)), 0.05, solid('geranium', (0.75, 0.12, 0.12), 0.6), 8)
    if flowers:
        box('fbox', W.P(u, 0.11, z + 0.03), W.S(w, 0.13, 0.1), timber_h, bevel=0.008)
        for k in range(4):
            sphere('geranium', tuple(W.P(u - w / 2 + 0.06 + k * w / 4, 0.11, z + 0.12)), 0.035, solid('geranium', (0.75, 0.12, 0.12), 0.6), 8)
        hanging_ivy(tuple(W.P(u, 0.12, z + 0.05)), tuple(W.n), w, 0.4, 4, 'ivy_d', (0.12, 0.22, 0.07))
    if lit:
        life(W, u, z, w, top, fr)
        room_light(tuple(W.P(u, -0.45, z + h / 2)), 14)

def building(name, x0, x1, y0, y1, z0, floors, fh, mat, style, fcols, scols, lit_p=0.65, shutters=None, shop=None):
    Wd, Dp = x1 - x0, y1 - y0
    H = floors * fh
    o = box(name, ((x0 + x1) / 2, (y0 + y1) / 2, z0 + H / 2), (Wd, Dp, H), mat, bevel=0.02)
    F, S = Wall(o, 'y', y0), Wall(o, 'x', x1)
    w = min(0.5, Wd / fcols * 0.55); ws = min(0.45, Dp / scols * 0.5)
    for f in range(floors):
        z = z0 + f * fh + 0.25
        for k in range(fcols):
            u = x0 + (k + 0.5) * Wd / fcols
            if f == 0 and (k == fcols // 2 or (shop and k == shop)): continue
            st = 'bay' if (style == 'mixed' and f == 1 and k == 0) else ('casement' if style == 'mixed' else style)
            window(F, u, z, w, fh * 0.58, st, RG.random() < lit_p, shutters, balcony=(f >= 1 and RG.random() < 0.3), flowers=(f >= 1 and RG.random() < 0.25))
        for k in range(scols):
            u = y0 + (k + 0.5) * Dp / scols
            window(S, u, z, ws, fh * 0.58, 'casement' if style == 'mixed' else style, RG.random() < lit_p, shutters if RG.random() < 0.5 else None)
        if f > 0:
            box('string', ((x0 + x1) / 2, y0 - 0.03, z0 + f * fh), (Wd + 0.04, 0.08, 0.06), quay, bevel=0.006)
            box('string', (x1 + 0.03, (y0 + y1) / 2, z0 + f * fh), (0.08, Dp + 0.04, 0.06), quay, bevel=0.006)
    du = x0 + (fcols // 2 + 0.5) * Wd / fcols
    cut(o, box('dc', (du, y0, z0 + 0.6), (0.55, 0.6, 1.1), None, bevel=0))
    box('door', (du, y0 + 0.08, z0 + 0.55), (0.5, 0.05, 1.05), timber, bevel=0.01)
    for k in range(2):
        box('door_panel', (du, y0 + 0.05, z0 + 0.3 + k * 0.45), (0.38, 0.02, 0.36), timber_h, bevel=0.006)
    sphere('knob', (du + 0.16, y0 + 0.03, z0 + 0.55), 0.02, brass_d, 8)
    box('transom', (du, y0 - 0.02, z0 + 1.22), (0.5, 0.02, 0.12), glow, bevel=0)
    box('step', (du, y0 - 0.15, z0 + 0.04), (0.7, 0.3, 0.08), quay, bevel=0.01)
    box('cornice', ((x0 + x1) / 2, (y0 + y1) / 2, z0 + H + 0.05), (Wd + 0.16, Dp + 0.16, 0.1), quay, bevel=0.01)
    for k in range(int(Wd / 0.3)):
        box('bracket', (x0 + 0.15 + k * 0.3, y0 - 0.05, z0 + H - 0.04), (0.05, 0.1, 0.1), quay, bevel=0.005)
    cyl('drain', (x1 - 0.06, y0 - 0.06, z0 + H / 2), 0.035, H, rustm, verts=10)
    cyl('drain_head', (x1 - 0.06, y0 - 0.06, z0 + H - 0.1), 0.06, 0.12, rustm, verts=10)
    room_light(((x0 + x1) / 2, (y0 + y1) / 2, z0 + H / 2), 40)
    return o, z0 + H, F, S

# ------------------------------------------------------------------ lamps
def wall_lantern(W, u, z):
    base = W.P(u, 0.02, z)
    box('wl_plate', base, W.S(0.08, 0.02, 0.14), iron, bevel=0.003)
    tip = base + W.n * 0.22 + Vector((0, 0, 0.08))
    limb(base, tip, 0.012, iron)
    limb(base + Vector((0, 0, -0.08)), base + W.n * 0.15 + Vector((0, 0, 0.06)), 0.008, iron)
    lp = tip - Vector((0, 0, 0.12))
    cyl('wl_glass', lp, 0.045, 0.12, solid('gaslight', (1, 0.85, 0.55), 0.2, emit=(1.0, 0.68, 0.32), strength=12), verts=6)
    cyl('wl_hat', lp + Vector((0, 0, 0.08)), 0.06, 0.05, iron, verts=6, r2=0.015)
    L = bpy.data.lights.new('wl', 'POINT'); L.energy = 10; L.color = (1, 0.66, 0.32)
    link(bpy.data.objects.new('wl', L)).location = lp

def hanging_lanterns(a, b, n=4, sag=0.35):
    wire(a, b, sag)
    a, b = Vector(a), Vector(b)
    cols = [(1.0, 0.55, 0.25), (0.95, 0.4, 0.3), (1.0, 0.75, 0.4)]
    for k in range(1, n + 1):
        t = k / (n + 1)
        p = a.lerp(b, t) + Vector((0, 0, -sag * 4 * t * (1 - t) - 0.12))
        paper_lantern(tuple(p), 0.07, cols[k % 3])

def globe_post(x, y, z0, h=0.55):
    cyl('gp_post', (x, y, z0 + h / 2), 0.02, h, iron, verts=8)
    sphere('gp_globe', (x, y, z0 + h + 0.06), 0.06, solid('globe_w', (1, 0.95, 0.85), 0.2, emit=(1.0, 0.8, 0.55), strength=9), 14)
    L = bpy.data.lights.new('gp', 'POINT'); L.energy = 6; L.color = (1, 0.8, 0.55)
    link(bpy.data.objects.new('gp', L)).location = (x, y, z0 + h + 0.06)

def neon_sign(W, u, z, text_w=0.6, color=(1.0, 0.35, 0.45)):
    nm = solid('neon_' + str(color), color, 0.3, emit=color, strength=14)
    box('neon_back', W.P(u, 0.03, z), W.S(text_w + 0.12, 0.02, 0.26), solid('sign', (0.12, 0.1, 0.08), 0.6), bevel=0.01)
    pts = [W.P(u - text_w / 2 + text_w * t, 0.05, z + 0.06 * math.sin(t * 14)) for t in [k / 16 for k in range(17)]]
    for p, q in zip(pts, pts[1:]):
        limb(p, q, 0.008, nm)
    L = bpy.data.lights.new('neon', 'POINT'); L.energy = 5; L.color = color
    link(bpy.data.objects.new('neon', L)).location = W.P(u, 0.2, z)

def hanging_sign(W, u, z, col=(0.5, 0.2, 0.15)):
    base = W.P(u, 0.0, z)
    limb(base, base + W.n * 0.45, 0.012, iron)
    for d in (0.08, 0.37):
        limb(base + W.n * d, base + W.n * d - Vector((0, 0, 0.06)), 0.004, iron)
    box('hsign', base + W.n * 0.23 - Vector((0, 0, 0.2)), (0.3, 0.02, 0.24) if W.axis == 'x' else (0.02, 0.3, 0.24), varied('hsign', col, 0.1, 0.7), bevel=0.01)

# ------------------------------------------------------------------ boats
def rowboat(x, y, a, L=1.0, cargo=None, lantern_pole=True, col=(0.32, 0.24, 0.17)):
    hm = varied('hull_%.2f' % col[0], col, 0.1, 0.6, bump=0.2)
    hull = sphere('boat', (x, y, 0.06), 0.5, hm, 28, (L, 0.32, 0.22)); hull.rotation_euler.z = a
    cut(hull, box('boat_cut', (x, y, 0.3), (2.5, 1.5, 0.4), None, bevel=0))
    cut(hull, sphere('boat_in', (x, y, 0.1), 0.46, None, 20, (L * 0.95, 0.27, 0.2)))
    d = Vector((math.cos(a), math.sin(a), 0)); s_ = Vector((-math.sin(a), math.cos(a), 0))
    box('gunwale', (x, y, 0.11), (L * 0.95, 0.03, 0.02), timber_h, bevel=0, rot=(0, 0, a))
    for k in (-0.22, 0.18):
        box('boat_seat', Vector((x, y, 0.1)) + d * k * L, (0.06, 0.28, 0.03), timber, bevel=0.005, rot=(0, 0, a))
    for sg in (-1, 1):  # oars resting
        limb(Vector((x, y, 0.13)) + s_ * sg * 0.14 - d * 0.1, Vector((x, y, 0.06)) + s_ * sg * 0.45 + d * 0.35, 0.012, timber_h)
    if lantern_pole:
        stern = Vector((x, y, 0.1)) - d * 0.42 * L
        limb(stern, stern + Vector((0, 0, 0.45)), 0.01, iron)
        limb(stern + Vector((0, 0, 0.45)), stern + Vector((0, 0, 0.45)) + d * 0.12, 0.008, iron)
        lantern(tuple(stern + Vector((0, 0, 0.3)) + d * 0.12), 0.55)
    if cargo == 'flowers':
        for k in range(6):
            p = Vector((x, y, 0.13)) + d * RG.uniform(-0.25, 0.25) * L + s_ * RG.uniform(-0.08, 0.08)
            cyl('bucket', p, 0.04, 0.07, iron, verts=10)
            sphere('bunch', p + Vector((0, 0, 0.07)), 0.05, solid('bunch%d' % (k % 3), [(0.9, 0.4, 0.5), (0.95, 0.85, 0.4), (0.9, 0.9, 0.85)][k % 3], 0.6), 8)
    elif cargo == 'crates':
        for k in range(2):
            box('bcrate', Vector((x, y, 0.18)) + d * (0.05 + k * 0.22), (0.18, 0.18, 0.15), timber, bevel=0.008, rot=(0, 0, a))
        cyl('bsack', tuple(Vector((x, y, 0.15)) - d * 0.15), 0.08, 0.14, varied('sack', (0.6, 0.52, 0.38), 0.05, 0.9), verts=12, bevel=0.03)
    return hull

def houseboat(x, y, a, L=2.2):
    """Long barge with a lit cabin, plants on the roof and a stove pipe."""
    hm = varied('barge', (0.12, 0.22, 0.18), 0.08, 0.5, bump=0.2)
    d = Vector((math.cos(a), math.sin(a), 0)); s_ = Vector((-math.sin(a), math.cos(a), 0))
    box('barge_hull', (x, y, 0.06), (L, 0.62, 0.22), hm, bevel=0.06, rot=(0, 0, a))
    box('barge_rub', (x, y, 0.17), (L + 0.02, 0.64, 0.03), varied('rubrail', (0.5, 0.18, 0.12), 0.05, 0.5), bevel=0.01, rot=(0, 0, a))
    cab = box('cabin', Vector((x, y, 0.42)) - d * 0.15, (L * 0.62, 0.5, 0.45), timber_h, bevel=0.015, rot=(0, 0, a))
    box('cabin_roof', Vector((x, y, 0.67)) - d * 0.15, (L * 0.66, 0.58, 0.05), hm, bevel=0.01, rot=(0, 0, a))
    for k in range(4):
        p = Vector((x, y, 0.45)) - d * 0.15 + d * (k - 1.5) * L * 0.14 - s_ * 0.255
        box('cab_win', p, (0.16, 0.01, 0.16), glow, bevel=0, rot=(0, 0, a))
        if RG.random() < 0.6:
            box('cab_curtain', p + s_ * 0.004 + d * 0.05, (0.05, 0.01, 0.16), varied('curtain%d' % (k % 6), cloths[k % 6], 0.06, 0.95), bevel=0, rot=(0, 0, a))
    room_light(tuple(Vector((x, y, 0.45)) - d * 0.15), 18)
    for k in range(4):  # roof garden pots
        p = Vector((x, y, 0.72)) - d * 0.15 + d * (k - 1.5) * L * 0.14
        cyl('rpot', p + Vector((0, 0, 0.04)), 0.045, 0.08, varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8), verts=10)
        sphere('rplant', p + Vector((0, 0, 0.12)), 0.06, solid('rleaf', (0.16, 0.3, 0.1), 0.7), 10)
    sp = Vector((x, y, 0.7)) - d * 0.15 + d * L * 0.25
    cyl('stove', sp + Vector((0, 0, 0.2)), 0.025, 0.4, iron, verts=8)
    cyl('stove_hat', sp + Vector((0, 0, 0.42)), 0.05, 0.04, iron, verts=8, r2=0.01)
    sm = solid('smoke_c', (0.22, 0.22, 0.24), 0.9)
    for k in range(3):
        sphere('smoke', sp + Vector((k * 0.06, 0, 0.55 + k * 0.15)), 0.05 + k * 0.03, sm, 10)
    bow = Vector((x, y, 0.2)) + d * L * 0.4
    box('deck_chair', bow, (0.2, 0.2, 0.04), timber_h, bevel=0.01, rot=(0, 0.3, a))
    lantern(tuple(bow + d * 0.2 + Vector((0, 0, 0.1))), 0.6)
    hanging_lanterns(tuple(Vector((x, y, 0.95)) - d * L * 0.3), tuple(Vector((x, y, 0.8)) + d * L * 0.4), 3, 0.08)
    ring = cyl('lifering', tuple(Vector((x, y, 0.42)) - d * 0.15 + d * L * 0.25 - s_ * 0.27), 0.08, 0.03, varied('ring', (0.85, 0.3, 0.2), 0.05, 0.6), verts=16,
               rot=(math.pi / 2, 0, a))

def gondola(x, y, a, L=1.6):
    gm = solid('gondola', (0.03, 0.03, 0.035), 0.3)
    d = Vector((math.cos(a), math.sin(a), 0))
    h = sphere('gondola', (x, y, 0.07), 0.5, gm, 28, (L, 0.22, 0.18)); h.rotation_euler.z = a
    cut(h, box('g_cut', (x, y, 0.28), (3.5, 1.2, 0.3), None, bevel=0))
    for sg in (-1, 1):  # curled ends
        e = Vector((x, y, 0.12)) + d * sg * L * 0.48
        limb(e, e + d * sg * 0.12 + Vector((0, 0, 0.28)), 0.02, gm)
    box('g_seat', (x, y, 0.15), (0.4, 0.26, 0.06), varied('g_cushion', (0.5, 0.12, 0.12), 0.05, 0.9), bevel=0.02, rot=(0, 0, a))
    e = Vector((x, y, 0.4)) + d * L * 0.55
    lantern(tuple(e), 0.55)

def moor(post, boat_pt):
    limb(Vector(post) + Vector((0, 0, 0.25)), Vector(boat_pt), 0.006, varied('rope', (0.6, 0.52, 0.38), 0.05, 0.9))

# ------------------------------------------------------------------ stage
diorama_base(0, 0, 10.0, 8.6, canal_water(), z=0.0)
oldbrick = old_bricks('old_bricks', (0.42, 0.22, 0.15), 0.45)
oldbrick2 = old_bricks('old_bricks_y', (0.5, 0.36, 0.26), 0.35, 6.0)

quay_block(-4.85, -2.0, 0.85, 4.15)     # A
quay_block(-1.15, 2.35, 1.6, 4.15)      # B
quay_block(2.85, 4.85, -0.3, 4.15)      # C (moved right)
quay_block(-4.85, -2.55, -3.4, 0.25)    # D (new, left)

A, topA, AF, AS = building('A', -4.6, -2.3, 1.25, 3.95, 0.28, 4, 1.15, oldbrick, 'arch', 3, 3, 0.6, varied('sh_green', (0.16, 0.24, 0.2), 0.1, 0.6))
B, topB, BF, BS = building('B', -0.95, 2.15, 2.25, 4.05, 0.28, 3, 1.2, plaster_g, 'sash', 4, 2, 0.65, varied('sh_red', (0.35, 0.14, 0.12), 0.1, 0.6), shop=0)
C, topC, CF, CS = building('C', 3.1, 4.65, 0.2, 3.9, 0.28, 3, 1.1, plaster_o, 'mixed', 2, 4, 0.7, varied('sh_blue', (0.18, 0.22, 0.3), 0.1, 0.6))
D, topD, DF, DS = building('D', -4.6, -2.85, -2.9, -0.05, 0.28, 3, 1.05, oldbrick2, 'casement', 2, 3, 0.65, None, shop=0)
gable_roof('roofA', -3.45, 2.6, 2.3, 2.7, topA + 0.1, 1.2, slate, over=0.15)
gable_roof('roofD', -3.72, -1.47, 1.75, 2.85, topD + 0.1, 0.75, tile_mat('rt_old', (0.42, 0.22, 0.15)), over=0.15)
# C's roof: ridge along y — build as gable on a rotated footprint by swapping: use a mansard-ish hip of boxes
gable_roof('roofC', 3.875, 2.05, 1.55, 3.7, topC + 0.1, 0.9, slate, over=0.15)
for (x, y, z, h) in ((-4.1, 3.4, topA + 0.6, 1.2), (-2.9, 1.8, topA + 0.5, 1.0), (-0.4, 3.6, topB + 0.1, 0.8), (1.5, 3.7, topB + 0.1, 0.7),
                     (4.3, 3.2, topC + 0.4, 0.9), (-4.2, -0.6, topD + 0.3, 0.8)):
    box('chimney', (x, y, z + h / 2), (0.28, 0.28, h), oldbrick, bevel=0.01)
    for k in range(2):
        cyl('ch_pot', (x - 0.06 + k * 0.12, y, z + h + 0.08), 0.045, 0.16, varied('pot_c', (0.45, 0.25, 0.16), 0.1, 0.8), verts=10)
    sm = solid('smoke_c', (0.22, 0.22, 0.24), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.4
    for k in range(4):
        sphere('smoke', (x + k * 0.1, y + k * 0.04, z + h + 0.35 + k * 0.22), 0.09 + k * 0.045, sm, 12)
# B roof clutter
box('B_roofwall', (0.6, 3.15, topB + 0.2), (3.1, 1.8, 0.3), plaster_g, bevel=0.01)
cyl('water_tank', (1.6, 2.9, topB + 0.85), 0.32, 0.9, timber, verts=20)
cyl('tank_roof', (1.6, 2.9, topB + 1.4), 0.36, 0.25, iron, verts=20, r2=0.02)
for k in range(4):
    a = k / 4 * 2 * math.pi + 0.5
    limb(Vector((1.6 + math.cos(a) * 0.25, 2.9 + math.sin(a) * 0.25, topB + 0.35)), Vector((1.6 + math.cos(a) * 0.3, 2.9 + math.sin(a) * 0.3, topB + 0.05)), 0.02, iron)
for k in range(3):
    pot((-0.6 + k * 0.35, 2.45, topB + 0.35), 0.1, 0.18, None)
    sphere('roof_plant', (-0.6 + k * 0.35, 2.45, topB + 0.6), 0.1, solid('rleaf', (0.16, 0.3, 0.1), 0.7), 10)
hanging_lanterns((-0.85, 2.4, topB + 0.6), (0.5, 2.4, topB + 0.55), 3, 0.1)
# shopfronts: B (neon), D (bakery glow with awning), C hanging sign
cut(B, box('shopc', (-0.56, 2.25, 0.85), (0.75, 0.6, 1.0), None, bevel=0))
box('shop_glass', (-0.56, 2.33, 0.85), (0.75, 0.01, 1.0), glow, bevel=0)
for k in range(5):
    cyl('shop_jar', (-0.85 + k * 0.14, 2.3, 0.45), 0.035, 0.1, solid('jar%d' % (k % 3), [(0.8, 0.5, 0.3), (0.5, 0.6, 0.4), (0.8, 0.75, 0.5)][k % 3], 0.3), verts=10)
neon_sign(BF, -0.56, 1.5, 0.6, (1.0, 0.35, 0.45))
box('awning_d', (-3.72 + 0.43, -3.15, 1.45), (0.9, 0.5, 0.03), varied('awning_d2', (0.25, 0.35, 0.3), 0.05, 0.9), bevel=0, rot=(0.4, 0, 0))
cut(D, box('shopd', (-4.16, -2.9, 0.85), (0.7, 0.6, 1.0), None, bevel=0))
box('shopd_glass', (-4.16, -2.82, 0.85), (0.7, 0.01, 1.0), glow, bevel=0)
for k in range(4):
    sphere('bread', (-4.4 + k * 0.16, -2.86, 0.5), 0.05, solid('bread', (0.7, 0.45, 0.22), 0.7), 10, (1.4, 0.8, 0.7))
hanging_sign(CS, 1.2, 1.55, (0.25, 0.3, 0.4))
hanging_sign(DS, -1.0, 1.5, (0.5, 0.25, 0.15))
fire_escape(0.6, 1.8, 2.25, [1.45, 2.65])
# bridges: curved stone ones and covered skybridges
arch_bridge((-2.0, 1.25, 0), (-1.15, 2.0, 0))
arch_bridge((2.35, 2.2, 0), (2.85, 2.2, 0), w=0.6, h=0.22)
arch_bridge((-3.7, 0.25, 0), (-3.7, 0.85, 0), w=0.6, h=0.2)
skybridge((-2.3, 2.75), (-0.95, 2.8), 2.6)
skybridge((2.15, 3.1), (3.1, 3.1), 2.5, w=0.55)
skybridge((-3.7, -0.05), (-3.7, 1.25), 2.35, w=0.5)
# lamps of every kind
for (x, y) in ((-2.25, 1.0), (-0.95, 1.8), (2.6, 1.85), (3.05, -0.15), (-2.7, -3.25)):
    gas_lamp(x, y, 0.28)
for (W, u, z) in ((AF, -3.85, 1.5), (AF, -3.05, 2.65), (CS, 0.9, 1.4), (CS, 2.6, 2.5), (DF, -3.3, 1.35), (DS, -2.3, 2.4), (BF, 1.3, 1.45)):
    wall_lantern(W, u, z)
for p in ((-1.6, 1.6, 0.6), (2.6, 2.2, 0.53), (-3.7, 0.55, 0.5)):
    globe_post(p[0] - 0.25, p[1], p[2])
hanging_lanterns((-2.3, 1.3, 3.3), (3.1, 0.25, 3.0), 6, 0.6)
hanging_lanterns((-2.85, -0.5, 2.2), (-2.3, 1.3, 2.6), 3, 0.2)
laundry((-2.3, 1.4, 3.75), (-0.95, 2.3, 3.5))
laundry((2.15, 2.4, 3.45), (3.1, 2.2, 3.3))
wire((-4.6, 1.2, 4.3), (-0.95, 2.2, 3.7), 0.5)
wire((-2.85, -2.8, 3.2), (3.1, 0.3, 3.4), 0.9)
crates(-4.3, 0.95, 0.28); crates(3.3, -0.1, 0.28)
for (x, z, col) in ((-4.1, 0.9, (0.75, 0.6, 0.35)), (-3.75, 1.0, (0.6, 0.2, 0.18))):
    poster(x, 1.24, z, 0.28, 0.4, col)
# bicycle against B
bw = Vector((1.5, 2.12, 0.42))
for dx in (-0.22, 0.22):
    cyl('bike_wheel', tuple(bw + Vector((dx, 0, 0))), 0.16, 0.02, iron, verts=24, rot=(math.pi / 2, 0, 0))
limb(bw + Vector((-0.22, 0, 0)), bw + Vector((0.0, 0, 0.18)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
limb(bw + Vector((0.22, 0, 0)), bw + Vector((0.0, 0, 0.18)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
limb(bw + Vector((0.0, 0, 0.18)), bw + Vector((0.2, 0, 0.3)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
# boats instead of plank walkways
houseboat(0.6, -1.0, 0.35, 2.3)
rowboat(-1.3, -2.7, 0.6, 1.0, 'flowers', col=(0.2, 0.3, 0.35))
rowboat(3.7, -1.6, -0.4, 1.0, 'crates')
rowboat(-1.6, 0.25, 0.2, 0.85, None, col=(0.45, 0.25, 0.18))
rowboat(2.2, 0.9, 1.4, 0.8, None, lantern_pole=False, col=(0.3, 0.35, 0.28))
gondola(2.0, -3.3, -0.15, 1.6)
for (px, py, bx, by) in ((-2.3, 0.6, -1.85, 0.3), (2.75, -0.5, 3.4, -1.4), (-1.1, 1.45, 0.0, -0.6)):
    cyl('mooring', (px, py, 0.15), 0.05, 0.42, timber, verts=10); cyl('mooring_cap', (px, py, 0.37), 0.06, 0.04, iron, verts=10)
    moor((px, py, 0.15), (bx, by, 0.14))
for k in range(18):
    x, y = RG.uniform(-2.2, 2.6), RG.uniform(-4.0, 1.2)
    cyl('pad', (x, y, 0.005), RG.uniform(0.05, 0.09), 0.006, varied('pad_d', (0.12, 0.24, 0.08), 0.3, 0.4), verts=14)
ivy_patch((-2.35, 1.6, 0.3), (1, 0, 0), 1.0, 2.6, 500, 'ivy_d', (0.12, 0.22, 0.07))
ivy_patch((4.67, 0.6, 0.3), (1, 0, 0), 0.7, 1.8, 300, 'ivy_d', (0.12, 0.22, 0.07))
for (x, y) in ((-3.0, 1.0), (0.2, 1.9), (-3.2, -3.2)):
    pot((x, y, 0.28), 0.14, 0.26, 'fern_02', 0.4)

lighting(sc, sun_rot=(math.radians(78), 0, math.radians(-40)), sun_energy=0.6, sun_color=(0.55, 0.62, 0.85),
         bg_top=(0.05, 0.07, 0.13), bg_bottom=(0.35, 0.24, 0.24), hdri_strength=0.08)
iso_camera(sc, (-0.1, 0.4, 2.6), 13.6)
render(sc, OUT, SAMPLES)
