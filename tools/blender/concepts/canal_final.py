"""Canal block v3: rickety bridges, endless canal, varied window life, detailed houseboat. (v2: four old buildings in canal water, each with its own window
style and lived-in windows (curtains, plants, silhouettes, a cat, candles),
old brick, boats of all kinds instead of plank walkways, many kinds of lamps.
Usage: ASSETS=<assets-raw> python canal2.py <out.png> [samples]"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

ARGS = [a for a in sys.argv if not a.startswith('-')]
OUT, SAMPLES = ARGS[-2], int(ARGS[-1])
FONT = os.environ.get('SCRIPT_FONT', '')
MARKER = os.environ.get('MARKER_FONT', '')
GRAFFITI = os.environ.get('GRAFFITI_FONT', '')
sc = reset()
from garden import *
from canal_kit import *
import canal_extras as EX

RG = random.Random(52)
brass_d = solid('brass_d', (0.6, 0.45, 0.22), 0.35, metal=1)
cloths = [(0.55, 0.16, 0.14), (0.75, 0.62, 0.38), (0.3, 0.38, 0.5), (0.72, 0.68, 0.6), (0.36, 0.45, 0.3), (0.62, 0.35, 0.45)]
silhouette_m = solid('silhouette', (0.02, 0.02, 0.02), 0.9)
FLOWERS = [(0.75, 0.12, 0.12), (0.95, 0.92, 0.85), (0.95, 0.8, 0.25), (0.62, 0.45, 0.85), (0.95, 0.55, 0.68), (0.95, 0.5, 0.15), (0.45, 0.6, 0.9)]
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

def camera_hidden(*objs):
    for o in objs:
        o.visible_camera = False   # still shows up in the water's reflection

def _life(W, u, z, w, h, frame):
    """Props just inside a lit window: curtains plus one or two of many small
    signs of life. People only appear in the canal's reflection."""
    inside = -0.05
    if RG.random() < 0.6:
        col = RG.choice(cloths); cw = w * RG.uniform(0.18, 0.32)
        for sg in (-1, 1):
            if RG.random() < 0.85:
                box('curtain', W.P(u + sg * (w / 2 - cw / 2), inside, z + h / 2), W.S(cw, 0.01, h * 0.96), varied('curtain%d' % cloths.index(col), col, 0.06, 0.95), bevel=0)
    if RG.random() < 0.25:   # someone at the window, seen only in the water
        hd = sphere('head', W.P(u + RG.uniform(-w / 5, w / 5), inside - 0.02, z + h * 0.72), 0.06, silhouette_m, 12, (1, 1, 1.15))
        bd = sphere('body', W.P(u + RG.uniform(-w / 6, w / 6), inside - 0.02, z + h * 0.32), 0.11, silhouette_m, 12, (1, 0.6, 1.9))
        camera_hidden(hd, bd)
    picks = RG.sample(['cat', 'plants', 'lamp', 'candle', 'books', 'vase', 'fruit', 'bread', 'wine', 'tea', 'ashtray', 'radio', 'birdcage'], 2 if RG.random() < 0.4 else 1)
    for k, what in enumerate(picks):
        uu = u + (-w / 4 if k == 0 else w / 4) * (1 if len(picks) > 1 else 0) + RG.uniform(-0.03, 0.03)
        sill = W.P(uu, inside, z + 0.02)
        dark = lambda nm, c: solid(nm, c, 0.6)
        if what == 'cat':
            c = W.P(uu, 0.09, z + 0.05)
            fur = solid('cat_fur', RG.choice([(0.3, 0.2, 0.13), (0.5, 0.33, 0.18), (0.42, 0.42, 0.4)]), 0.8)
            sphere('cat_body', c, 0.06, fur, 12, (1.3, 0.8, 0.9) if W.axis == 'y' else (0.8, 1.3, 0.9))
            hdp = c + W.t * 0.08 + Vector((0, 0, 0.06)); sphere('cat_head', hdp, 0.038, fur, 10)
            for sg in (-1, 1):
                cyl('cat_ear', hdp + W.t * sg * 0.02 + Vector((0, 0, 0.035)), 0.014, 0.03, fur, verts=4, r2=0.0)
            limb(c - W.t * 0.07, c - W.t * 0.12 + Vector((0, 0, -0.1)), 0.008, fur)
        elif what == 'plants':
            for q in range(RG.randint(1, 3)):
                p = W.P(uu - 0.08 + q * 0.08, inside, z + 0.02)
                cyl('ipot', p + Vector((0, 0, 0.04)), 0.032, 0.08, varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8), verts=10)
                sphere('ileaves', p + Vector((0, 0, 0.12)), RG.uniform(0.045, 0.07), dark('ileaf_w', (0.14, 0.28, 0.09)), 10, (1, 1, 1.4))
        elif what == 'lamp':
            cyl('lamp_stem', sill + Vector((0, 0, 0.07)), 0.008, 0.14, brass_d, verts=6)
            cyl('lamp_shade', sill + Vector((0, 0, 0.17)), 0.06, 0.08, lamp_glow, verts=14, r2=0.035)
        elif what == 'candle':
            p = W.P(uu, 0.09, z + 0.02)
            cyl('candle', p + Vector((0, 0, 0.04)), 0.015, 0.07, solid('wax', (0.9, 0.85, 0.75), 0.6), verts=8)
            sphere('flame', p + Vector((0, 0, 0.09)), 0.01, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1.0, 0.65, 0.25), strength=30), 6, (1, 1, 1.8))
            L = bpy.data.lights.new('candle', 'POINT'); L.energy = 0.6; L.color = (1, 0.6, 0.25)
            link(bpy.data.objects.new('candle', L)).location = p + Vector((0, 0, 0.1))
        elif what == 'books':
            for q in range(RG.randint(3, 6)):
                box('book', sill + Vector((0, 0, 0.015 + q * 0.024)), W.S(RG.uniform(0.1, 0.14), 0.08, 0.022), varied('ibook%d' % q, RG.choice(cloths), 0.2, 0.7), bevel=0.002)
        elif what == 'vase':
            vc = RG.choice([(0.75, 0.8, 0.85), (0.35, 0.5, 0.6), (0.8, 0.7, 0.5)])
            cyl('vase', sill + Vector((0, 0, 0.06)), 0.03, 0.12, solid('vase%.1f' % vc[0], vc, 0.2), verts=12, r2=0.02)
            fc = RG.choice([(0.95, 0.95, 0.9), (0.95, 0.85, 0.3), (0.6, 0.45, 0.85), (0.95, 0.6, 0.7), (0.95, 0.5, 0.2)])
            for q in range(5):
                a = q / 5 * 6.28
                p = sill + Vector((math.cos(a) * 0.035, 0, 0.17 + 0.03 * math.sin(a * 2))) + W.t * math.sin(a) * 0.02
                limb(sill + Vector((0, 0, 0.1)), p, 0.003, dark('stem', (0.15, 0.25, 0.1)))
                sphere('bloom', p, 0.022, solid('bloom%.2f' % fc[1], fc, 0.5), 8)
        elif what == 'fruit':
            cyl('bowl', sill + Vector((0, 0, 0.02)), 0.06, 0.035, solid('bowl', (0.85, 0.82, 0.75), 0.3), verts=14, r2=0.04)
            for q, fcol in enumerate([(0.85, 0.2, 0.12), (0.9, 0.6, 0.1), (0.5, 0.65, 0.15), (0.85, 0.75, 0.2)]):
                sphere('fruit', sill + Vector((0, 0, 0.05)) + W.t * (q - 1.5) * 0.025, 0.022, solid('fruit%d' % q, fcol, 0.4), 8)
        elif what == 'bread':
            box('board', sill + Vector((0, 0, 0.01)), W.S(0.16, 0.08, 0.015), timber_h, bevel=0.003)
            sphere('loaf', sill + Vector((0, 0, 0.04)), 0.04, solid('bread', (0.7, 0.45, 0.22), 0.7), 10, (1.5, 0.9, 0.7) if W.axis == 'y' else (0.9, 1.5, 0.7))
            box('cheese', sill + Vector((0, 0, 0.03)) + W.t * 0.06, W.S(0.04, 0.03, 0.03), solid('cheese', (0.95, 0.8, 0.35), 0.5), bevel=0.003)
        elif what == 'wine':
            cyl('bottle', sill + Vector((0, 0, 0.09)), 0.022, 0.16, solid('bottle', (0.05, 0.15, 0.08), 0.1), verts=10)
            cyl('bottle_neck', sill + Vector((0, 0, 0.2)), 0.008, 0.06, solid('bottle', (0.05, 0.15, 0.08), 0.1), verts=8)
            cyl('glass', sill + Vector((0, 0, 0.05)) + W.t * 0.06, 0.018, 0.04, solid('wine', (0.35, 0.03, 0.06), 0.1), verts=10)
            cyl('glass_stem', sill + Vector((0, 0, 0.015)) + W.t * 0.06, 0.004, 0.03, solid('glass_c', (0.8, 0.85, 0.85), 0.05), verts=6)
        elif what == 'tea':
            cyl('teapot', sill + Vector((0, 0, 0.05)), 0.04, 0.08, solid('teapot%d' % RG.randint(0, 2), RG.choice([(0.75, 0.2, 0.15), (0.2, 0.35, 0.5), (0.9, 0.88, 0.82)]), 0.3), verts=14)
            limb(sill + Vector((0, 0, 0.05)) + W.t * 0.04, sill + Vector((0, 0, 0.09)) + W.t * 0.08, 0.008, solid('teapot0', (0.75, 0.2, 0.15), 0.3))
            for q in (0.1, 0.15):
                cyl('cup', sill + Vector((0, 0, 0.02)) + W.t * q, 0.017, 0.03, solid('cup', (0.92, 0.9, 0.85), 0.3), verts=10)
        elif what == 'ashtray':
            cyl('ashtray', sill + Vector((0, 0, 0.01)), 0.035, 0.02, solid('ashtray', (0.3, 0.32, 0.34), 0.2, metal=0.6), verts=14)
            a0 = sill + Vector((0, 0, 0.025))
            limb(a0, a0 + W.t * 0.09 + Vector((0, 0, 0.02)), 0.004, solid('holder', (0.05, 0.05, 0.05), 0.3))        # long holder
            limb(a0 + W.t * 0.09 + Vector((0, 0, 0.02)), a0 + W.t * 0.12 + Vector((0, 0, 0.025)), 0.005, solid('cig', (0.92, 0.9, 0.85), 0.6))
            sphere('ember', a0 + W.t * 0.122 + Vector((0, 0, 0.025)), 0.005, solid('ember', (1, 0.4, 0.1), 0.3, emit=(1.0, 0.35, 0.1), strength=20), 6)
            sm = solid('cig_smoke', (0.8, 0.8, 0.8), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.35
            for q in range(5):
                sphere('wisp', a0 + W.t * (0.12 + math.sin(q) * 0.02) + Vector((0, 0, 0.05 + q * 0.035)), 0.01 + q * 0.003, sm, 6)
        elif what == 'radio':
            box('radio', sill + Vector((0, 0, 0.05)), W.S(0.14, 0.07, 0.1), timber_h, bevel=0.01)
            box('radio_dial', sill + Vector((0, 0, 0.06)) + W.n * 0.036, W.S(0.06, 0.005, 0.03), solid('dial', (1, 0.8, 0.5), 0.3, emit=(1, 0.7, 0.4), strength=4), bevel=0)
        elif what == 'birdcage':
            top = sill + Vector((0, 0, 0.32))
            limb(top + Vector((0, 0, 0.1)), top, 0.003, brass_d)
            for q in range(8):
                a = q / 8 * 6.28
                limb(top + Vector((math.cos(a) * 0.01, 0, 0)), top + Vector((math.cos(a) * 0.05, 0, -0.14)) + W.t * math.sin(a) * 0.05, 0.002, brass_d)
            sphere('bird', top - Vector((0, 0, 0.09)), 0.018, solid('bird', (0.95, 0.85, 0.2), 0.5), 8, (1.3, 1, 1))

_LIT = {}
def lit_copy(m, k=0.45):
    """Same material, faintly self-lit: props just inside a bright window are lit
    by the room behind them, not silhouetted against it."""
    if m is None or not m.use_nodes or m.name.startswith(('silhouette', 'flame', 'ember', 'lamp_glow', 'dial')):
        return m
    if m.name in _LIT: return _LIT[m.name]
    c = m.copy(); c.name = m.name + '_lit'
    b = next((n for n in c.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is not None and b.inputs['Emission Strength'].default_value == 0:
        src = b.inputs['Base Color']
        if src.links: c.node_tree.links.new(src.links[0].from_socket, b.inputs['Emission Color'])
        else: b.inputs['Emission Color'].default_value = src.default_value
        b.inputs['Emission Strength'].default_value = k
    _LIT[m.name] = c
    return c

def life(W, u, z, w, h, frame):
    before = set(bpy.data.objects.keys())
    _life(W, u, z, w, h, frame)
    for name in set(bpy.data.objects.keys()) - before:
        o = bpy.data.objects[name]
        if o.type != 'MESH' or not o.visible_camera or o.name.startswith('curtain'): continue
        for slot in o.material_slots:
            slot.material = lit_copy(slot.material)

GLOWS = [glass_glow('g_warm', (1.0, 0.58, 0.26), 6.0), glass_glow('g_cream', (1.0, 0.8, 0.55), 5.0), glass_glow('g_amber', (1.0, 0.48, 0.18), 6.5),
         glass_glow('g_pale', (1.0, 0.9, 0.7), 4.5), glass_glow('g_rose', (1.0, 0.6, 0.5), 5.0), glass_glow('g_cool', (0.8, 0.9, 1.0), 3.5)]
GLOW_W = [5, 4, 3, 3, 1, 1]
ROOM_COLS = [(1, 0.62, 0.32), (1, 0.78, 0.5), (1, 0.52, 0.22), (1, 0.85, 0.65), (1, 0.6, 0.5), (0.8, 0.9, 1.0)]
def pick_glow():
    i = RG.choices(range(len(GLOWS)), GLOW_W)[0]
    return GLOWS[i], ROOM_COLS[i]
# wall areas kept clear of windows (where the patched corridors attach)
KEEPOUT = [ ('x', -2.3, 2.35, 3.15, 2.45, 3.45), ('x', 2.15, 2.75, 3.45, 2.35, 3.35),
            ('y', 1.25, -4.14, -3.54, 1.5, 2.45)]   # the little corridor from the bakery
def blocked(W, u, z, w, h):
    for (ax, pl, u0, u1, z0, z1) in KEEPOUT:
        if ax == W.axis and abs(pl - W.plane) < 0.05 and u + w / 2 > u0 and u - w / 2 < u1 and z + h > z0 and z < z1:
            return True
    return False

def window(W, u, z, w, h, style, lit=True, shutters=None, balcony=False, flowers=False):
    if blocked(W, u, z, w, h):
        return
    gmat, gcol = pick_glow()
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
        # an oriel: a little glazed room hung off the wall on carved brackets,
        # windows on the front and both sides, panelled below, a cornice and a
        # lead roof above. Painted timber, matt and brushy, not lacquer.
        bw, bd = w + 0.22, 0.36
        paint = varied('bay_paint', (0.4, 0.09, 0.07), 0.1, 0.85, bump=0.7, bump_scale=90)
        trim = varied('bay_trim', (0.82, 0.76, 0.64), 0.06, 0.8, bump=0.4, bump_scale=90)
        lead = varied('bay_lead', (0.24, 0.25, 0.27), 0.12, 0.55, bump=0.5, bump_scale=25)
        glass = gmat if lit else dark_win
        zb, zt = z - 0.1, z + h + 0.12          # apron bottom, cornice top
        za, zf = z + 0.06, z + h - 0.02         # glazing from za to zf
        sides = (-1, 1)
        # apron (panelled) and frieze, front and both sides
        box('bay', W.P(u, bd / 2, (zb + za) / 2), W.S(bw, bd, za - zb), paint, bevel=0.01)
        box('bay', W.P(u, bd / 2, (zf + zt) / 2), W.S(bw, bd, zt - zf), paint, bevel=0.01)
        for k in range(3):
            pu = u - bw / 2 + (k + 0.5) * bw / 3
            box('bay_panel', W.P(pu, bd + 0.006, (zb + za) / 2), W.S(bw / 3 - 0.05, 0.012, (za - zb) - 0.06), paint, bevel=0.006)
        for sg in sides:
            box('bay_panel', W.P(u + sg * (bw / 2 + 0.006), bd / 2 + 0.02, (zb + za) / 2), W.S(0.012, bd - 0.1, (za - zb) - 0.06), paint, bevel=0.006)
        # corner posts
        for sg in sides:
            box('bay_post', W.P(u + sg * (bw / 2 - 0.022), bd - 0.022, (za + zf) / 2), W.S(0.05, 0.05, zf - za), paint, bevel=0.006)
            box('bay_post', W.P(u + sg * (bw / 2 - 0.022), 0.03, (za + zf) / 2), W.S(0.05, 0.05, zf - za), paint, bevel=0.006)
        # glazing: front in three lights with a transom, each side in two
        gz = (za + zf) / 2; gh = zf - za; tz = zf - gh * 0.28
        box('bay_glass', W.P(u, bd - 0.02, gz), W.S(bw - 0.06, 0.01, gh), glass, bevel=0)
        for k in range(4):
            box('bay_mull', W.P(u - (bw - 0.06) / 2 + k * (bw - 0.06) / 3, bd - 0.012, gz), W.S(0.028, 0.022, gh), trim, bevel=0.003)
        box('bay_mull', W.P(u, bd - 0.014, tz), W.S(bw - 0.06, 0.016, 0.024), trim, bevel=0.003)
        for sg in sides:
            xs = u + sg * (bw / 2 - 0.02)
            box('bay_glass', W.P(xs, bd / 2 + 0.01, gz), W.S(0.01, bd - 0.1, gh), glass, bevel=0)
            for dd in (0.04, bd / 2 + 0.01, bd - 0.05):
                box('bay_mull', W.P(xs + sg * 0.008, dd, gz), W.S(0.022, 0.028, gh), trim, bevel=0.003)
            box('bay_mull', W.P(xs + sg * 0.008, bd / 2 + 0.01, tz), W.S(0.016, bd - 0.08, 0.024), trim, bevel=0.003)
        # sill all round
        box('bay_sill', W.P(u, bd / 2 + 0.015, za - 0.005), W.S(bw + 0.05, bd + 0.03, 0.03), trim, bevel=0.006)
        # cornice: a crown moulding and a row of little dentils
        box('bay_cornice', W.P(u, bd / 2 + 0.02, zt + 0.015), W.S(bw + 0.08, bd + 0.07, 0.035), trim, bevel=0.008)
        nd = 9
        for k in range(nd):
            box('bay_dentil', W.P(u - bw / 2 + 0.03 + k * (bw - 0.06) / (nd - 1), bd + 0.012, zt - 0.02), W.S(0.018, 0.018, 0.025), trim, bevel=0)
        for sg in sides:
            for k in range(4):
                box('bay_dentil', W.P(u + sg * (bw / 2 + 0.012), 0.05 + k * (bd - 0.1) / 3, zt - 0.02), W.S(0.018, 0.018, 0.025), trim, bevel=0)
        # lead roof, sloping back to the wall, with rolled seams and a finial
        r_ = box('bay_roof', W.P(u, bd / 2 + 0.02, zt + 0.08), W.S(bw + 0.1, bd + 0.1, 0.04), lead, bevel=0.01)
        r_.rotation_euler = (0.32, 0, 0) if W.axis == 'y' else (0, -0.32, 0)
        for k in range(4):
            sq = box('bay_seam', W.P(u - bw / 2 + 0.02 + k * bw / 3, bd / 2 + 0.02, zt + 0.105), W.S(0.014, bd + 0.08, 0.014), lead, bevel=0.005)
            sq.rotation_euler = r_.rotation_euler
        sphere('bay_finial', W.P(u, bd + 0.03, zt + 0.06), 0.022, trim, 12)
        # two carved brackets under it, each three corbelled steps and a drop
        for sg in sides:
            for k, (dd, hh) in enumerate(((0.3, 0.05), (0.22, 0.06), (0.14, 0.07))):
                box('bay_corbel', W.P(u + sg * (bw / 2 - 0.05), dd / 2, zb - 0.025 - k * 0.055), W.S(0.06, dd, hh), paint, bevel=0.008)
            sphere('bay_drop', W.P(u + sg * (bw / 2 - 0.05), 0.31, zb - 0.04), 0.02, trim, 10, (1, 1, 1.4))
        if lit:
            room_light(tuple(W.P(u, -0.3, z + h / 2)), 16, gcol)
            room_light(tuple(W.P(u, 0.18, z + h / 2)), 4, gcol)
        return
    box('pane', W.P(u, rec, z + h / 2), W.S(w, 0.01, h), gmat if lit else dark_win, bevel=0)
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
            fc = RG.choice(FLOWERS); sphere('jflower', tuple(W.P(u - w / 3, 0.15, z + 0.15)), 0.05, solid('fl%.2f%.2f' % fc[:2], fc, 0.6), 8)
    if flowers:
        box('fbox', W.P(u, 0.11, z + 0.03), W.S(w, 0.13, 0.1), timber_h, bevel=0.008)
        for k in range(4):
            fc = RG.choice(FLOWERS); sphere('boxflower', tuple(W.P(u - w / 2 + 0.06 + k * w / 4, 0.11, z + 0.12)), 0.035, solid('fl%.2f%.2f' % fc[:2], fc, 0.6), 8)
        hanging_ivy(tuple(W.P(u, 0.12, z + 0.05)), tuple(W.n), w, 0.4, 4, 'ivy_d', (0.12, 0.22, 0.07))
    if lit:
        life(W, u, z, w, top, fr)
        room_light(tuple(W.P(u, -0.45, z + h / 2)), 14, gcol)

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
    # a panel below, glazing above (the hall light shows through it) -- the
    # light belongs in the door, not floating on the wall over it
    box('door_panel', (du, y0 + 0.05, z0 + 0.3), (0.38, 0.02, 0.36), timber_h, bevel=0.006)
    box('transom', (du, y0 + 0.055, z0 + 0.78), (0.34, 0.01, 0.38), glow, bevel=0)
    for dx in (-0.06, 0.06):
        box('door_bar', (du + dx, y0 + 0.045, z0 + 0.78), (0.018, 0.015, 0.38), timber_h, bevel=0.002)
    box('door_bar', (du, y0 + 0.045, z0 + 0.78), (0.34, 0.015, 0.018), timber_h, bevel=0.002)
    sphere('knob', (du + 0.16, y0 + 0.03, z0 + 0.5), 0.02, brass_d, 8)
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
    gid = (abs(hash((round(u, 3), round(z, 3)))) % 997) / 997.0
    for p, q in zip(pts, pts[1:]):
        limb(p, q, 0.008, nm)['glow_group'] = gid      # the whole tube lights at once
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

def corrugated(name, base):
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 22; wv.inputs['Distortion'].default_value = 0
    l.new(tc.outputs['Object'], wv.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5; l.new(tc.outputs['Object'], nz.inputs['Vector'])
    r = n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = 0.4; r.color_ramp.elements[0].color = (*base, 1)
    r.color_ramp.elements[1].position = 0.7; r.color_ramp.elements[1].color = (0.42, 0.2, 0.1, 1)
    l.new(nz.outputs['Fac'], r.inputs['Fac']); l.new(r.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.8
    l.new(wv.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.6; b.inputs['Metallic'].default_value = 0.4
    return m

def rusty_steel(name, paint=(0.08, 0.12, 0.1)):
    """Old painted steel: paint flaking off to rust in patches, orange runs
    streaking down from seams, a red oxide waterline band and green slime
    right at the water."""
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    pz = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], pz.inputs['Vector'])
    # rust patches
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9; nz.inputs['Detail'].default_value = 10; nz.inputs['Roughness'].default_value = 0.65
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    pr = n.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = 0.5; pr.inputs['From Max'].default_value = 0.6
    l.new(nz.outputs['Fac'], pr.inputs['Value'])
    # runs: noise squashed tall, so it streaks downwards
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (40, 40, 2.5)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    rn = n.new('ShaderNodeTexNoise'); rn.inputs['Scale'].default_value = 3; rn.inputs['Detail'].default_value = 4
    l.new(mp.outputs['Vector'], rn.inputs['Vector'])
    rr = n.new('ShaderNodeMapRange'); rr.inputs['From Min'].default_value = 0.52; rr.inputs['From Max'].default_value = 0.7
    rr.inputs['To Max'].default_value = 0.75
    l.new(rn.outputs['Fac'], rr.inputs['Value'])
    rust_amt = n.new('ShaderNodeMath'); rust_amt.operation = 'MAXIMUM'; rust_amt.use_clamp = True
    l.new(pr.outputs['Result'], rust_amt.inputs[0]); l.new(rr.outputs['Result'], rust_amt.inputs[1])
    rustc = n.new('ShaderNodeValToRGB')
    rustc.color_ramp.elements[0].color = (0.2, 0.07, 0.03, 1); rustc.color_ramp.elements[1].color = (0.45, 0.2, 0.08, 1)
    l.new(nz.outputs['Fac'], rustc.inputs['Fac'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*paint, 1)
    l.new(rust_amt.outputs['Value'], mix.inputs['Factor']); l.new(rustc.outputs['Color'], mix.inputs['B'])
    # waterline: red oxide band, slime below it
    band = n.new('ShaderNodeMapRange'); band.inputs['From Min'].default_value = 0.035; band.inputs['From Max'].default_value = 0.03
    l.new(pz.outputs['Z'], band.inputs['Value'])
    mix2 = n.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.inputs['B'].default_value = (0.32, 0.07, 0.05, 1)
    l.new(band.outputs['Result'], mix2.inputs['Factor']); l.new(mix.outputs['Result'], mix2.inputs['A'])
    slime = n.new('ShaderNodeMapRange'); slime.inputs['From Min'].default_value = 0.012; slime.inputs['From Max'].default_value = 0.0
    l.new(pz.outputs['Z'], slime.inputs['Value'])
    mix3 = n.new('ShaderNodeMix'); mix3.data_type = 'RGBA'; mix3.inputs['B'].default_value = (0.07, 0.1, 0.05, 1)
    l.new(slime.outputs['Result'], mix3.inputs['Factor']); l.new(mix2.outputs['Result'], mix3.inputs['A'])
    l.new(mix3.outputs['Result'], b.inputs['Base Color'])
    rg = n.new('ShaderNodeMapRange'); rg.inputs['To Min'].default_value = 0.5; rg.inputs['To Max'].default_value = 0.95
    l.new(rust_amt.outputs['Value'], rg.inputs['Value']); l.new(rg.outputs['Result'], b.inputs['Roughness'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; bp.inputs['Distance'].default_value = 0.004
    l.new(pr.outputs['Result'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def barge_hull(P, L, W=0.33, deck_mat=None, mat=None):
    """A steel barge hull lofted from cross-sections: a flat transom stern, a
    full body, a pointed bow that sweeps up (sheer) and rakes forward, the
    bilge rounding into a shallow keel. Returns the sheer line (each side)."""
    import bmesh as _bm
    N = 44
    prof = [(1.0, 0.0), (1.0, 0.06), (0.99, 0.13), (0.96, 0.2), (0.88, 0.3), (0.65, 0.55), (0.3, 0.9), (0.0, 1.0)]
    def half(t):
        if t > 0.42: return W * max(0.025, math.sqrt(max(0.0, 1 - ((t - 0.42) / 0.58) ** 2)) ** 0.9)
        if t < -0.5: return W * max(0.42, math.sqrt(max(0.0, 1 - ((-t - 0.5) / 0.56) ** 2)))   # a rounded counter stern
        return W
    sheer = lambda t: 0.19 + 0.1 * max(0.0, (t - 0.3) / 0.7) ** 2 + 0.06 * max(0.0, (-t - 0.55) / 0.45) ** 2
    keel = lambda t: -0.09 + 0.08 * max(0.0, (t - 0.55) / 0.45) ** 2 + 0.06 * max(0.0, (-t - 0.6) / 0.4) ** 2
    me = bpy.data.meshes.new('hull'); bm = _bm.new()
    rings = []
    for i in range(N + 1):
        t = -1 + 2 * i / N
        a_ = t * L / 2 + (0.04 * max(0.0, (t - 0.6) / 0.4) ** 2) * L   # the bow rakes forward at the top
        w, zs, zk = half(t), sheer(t), keel(t)
        ring = []
        for side in (1, -1):
            pts = prof if side == 1 else list(reversed(prof))[:-1] if False else prof
            seq = prof if side == 1 else list(reversed(prof))
            for (fx, fz) in seq:
                if side == -1 and fx == 0.0: continue
                z = zs + (zk - zs) * fz
                along = a_ - (0.04 * max(0.0, (t - 0.6) / 0.4) ** 2) * L * fz
                ring.append(bm.verts.new(P(along, side * w * fx, z)))
        rings.append(ring)
    # ring order: right side top->keel, then left side keel->top
    for i in range(N):
        A, B = rings[i], rings[i + 1]
        for k in range(len(A) - 1):
            bm.faces.new((A[k], A[k + 1], B[k + 1], B[k]))
        f = bm.faces.new((A[-1], A[0], B[0], B[-1])); f.material_index = 1      # deck
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    _bm.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new('hull', me))
    me.materials.append(mat); me.materials.append(deck_mat)
    for p in me.polygons: p.use_smooth = p.material_index == 0
    sheer_pts = {side: [P(-1 * L / 2 + (j / 30) * L + (0.04 * max(0.0, ((-1 + 2 * j / 30) - 0.6) / 0.4) ** 2) * L,
                         side * half(-1 + 2 * j / 30), sheer(-1 + 2 * j / 30)) for j in range(31)] for side in (1, -1)}
    return o, sheer_pts, half, sheer


def houseboat(x, y, a, L=2.2):
    """Old timber barge: planked hull with tar and algae, tongue-and-groove
    cabin with painted trim, framed windows with curtains, a porthole door,
    roof rail with pots, tyre fenders, rope coil, ladder, stove pipe, and a
    'home sweet home' board in cursive."""
    d = Vector((math.cos(a), math.sin(a), 0)); s_ = Vector((-math.sin(a), math.cos(a), 0))
    O = Vector((x, y, 0))
    P = lambda along, side, z: O + d * along + s_ * side + Vector((0, 0, z))
    R_ = (0, 0, a)
    steel = rusty_steel('barge_steel', (0.07, 0.13, 0.11))
    deckm = wood('deckplanks', (0.42, 0.32, 0.22), 5)
    hull, sheer_pts, half, sheer = barge_hull(P, L, 0.33, deckm, steel)
    # rubbing strake and bulwark cap along the sheer, both sides
    rail = varied('strake_iron', (0.12, 0.1, 0.09), 0.1, 0.6)
    for side, pts in sheer_pts.items():
        for zoff, r, m_ in ((-0.0, 0.016, wood('gunwale', (0.45, 0.16, 0.11), 6)), (-0.07, 0.014, rail)):
            cu = bpy.data.curves.new('strake', 'CURVE'); cu.dimensions = '3D'
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for q, pt in zip(sp.points, pts):
                q.co = (*(pt + s_ * side * 0.006 + Vector((0, 0, zoff))), 1)
            cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
            o_ = link(bpy.data.objects.new('strake', cu)); cu.materials.append(m_)
    # rivets along the plating seams on the side that faces the street
    rivet = varied('rivet', (0.16, 0.1, 0.07), 0.15, 0.7)
    for zr in (0.11, 0.045):
        for j in range(34):
            t = -0.95 + 1.8 * j / 33
            if t > 0.8: continue
            sphere('rivet', P(t * L / 2, -(half(t) + 0.002), zr + 0.06 * max(0.0, (t - 0.3) / 0.7) ** 2), 0.0065, rivet, 6)
    for j in range(7):   # vertical seams
        t = -0.85 + j * 0.27
        for k in range(4):
            sphere('rivet', P(t * L / 2, -(half(t) + 0.002), 0.02 + k * 0.04), 0.0065, rivet, 6)
    # hull portholes below the cabin windows
    for k in range(3):
        u = -0.15 - L * 0.3 + 0.25 + k * (L * 0.6 - 0.5) / 2
        tt = 2 * u / L
        pp = P(u, -(half(tt) + 0.004), 0.1)
        cyl('hull_port', pp, 0.03, 0.01, glow, verts=16, rot=(math.pi / 2, 0, a))
        cyl('hull_port_rim', pp - s_ * 0.002, 0.038, 0.008, brass_d, verts=16, rot=(math.pi / 2, 0, a))
    # the bow: two bollards, a hawse pipe with the anchor hung off it, chain over the deck
    for k in (0, 1):
        bp_ = P(L * 0.36 + k * 0.07, 0.0, sheer(0.72) - 0.02)
        cyl('bollard', bp_ + Vector((0, 0, 0.04)), 0.022, 0.08, iron, verts=12)
        cyl('bollard_cap', bp_ + Vector((0, 0, 0.085)), 0.028, 0.012, iron, verts=12)
    hp = P(L * 0.43, -(half(0.86) + 0.004), sheer(0.86) - 0.06)
    cyl('hawse', hp, 0.022, 0.03, iron, verts=12, rot=(math.pi / 2, 0, a))
    an = hp - Vector((0, 0, 0.12)) - s_ * 0.02
    limb(hp, an + Vector((0, 0, 0.06)), 0.005, iron)
    limb(an + Vector((0, 0, 0.06)), an - Vector((0, 0, 0.04)), 0.007, iron)            # shank
    for sg in (-1, 1):
        limb(an - Vector((0, 0, 0.04)), an - Vector((0, 0, 0.01)) + d * sg * 0.045, 0.006, iron)   # arms
        cyl('fluke', an - Vector((0, 0, 0.005)) + d * sg * 0.05, 0.012, 0.02, iron, verts=3, rot=(0, 0, a))
    box('stock', an + Vector((0, 0, 0.05)), (0.09, 0.008, 0.008), iron, bevel=0, rot=R_)
    for k in range(8):   # chain links across the deck to the bollards
        c_ = P(L * 0.43 - k * 0.012, -0.28 + k * 0.035, sheer(0.86) - 0.015)
        cyl('chain', c_, 0.008, 0.004, iron, verts=8, rot=(math.pi / 2 * (k % 2), 0, a))
    # the stern: a rudder blade, its stock and a long iron tiller
    rp = P(-L / 2 - 0.03, 0, 0.0)
    box('rudder', rp + Vector((0, 0, -0.02)), (0.12, 0.015, 0.2), steel, bevel=0.01, rot=R_)
    limb(rp + Vector((0, 0, 0.08)), rp + Vector((0, 0, 0.27)), 0.01, iron)
    limb(rp + Vector((0, 0, 0.26)), rp + Vector((0, 0, 0.29)) + d * 0.35, 0.008, iron)
    sphere('tiller_knob', rp + Vector((0, 0, 0.29)) + d * 0.36, 0.013, wood('gunwale', (0.45, 0.16, 0.11), 6), 8)
    # a cat asleep on the bow deck, curled up
    catf = solid('cat_fur', (0.42, 0.42, 0.4), 0.8)
    cp = P(L * 0.3, 0.14, sheer(0.6) + 0.035)
    sphere('boat_cat', cp, 0.05, catf, 14, (1.3, 1.0, 0.6))
    sphere('boat_cat', cp + d * 0.05 + s_ * 0.02 + Vector((0, 0, 0.012)), 0.03, catf, 12)
    for sg in (-1, 1):
        cyl('boat_cat_ear', cp + d * 0.06 + s_ * (0.02 + sg * 0.014) + Vector((0, 0, 0.04)), 0.009, 0.018, catf, verts=4, r2=0.0)
    limb(cp - d * 0.06, cp - d * 0.02 - s_ * 0.06 + Vector((0, 0, -0.01)), 0.009, catf)
    # a rain barrel at the stern
    bp_ = P(-L * 0.44, 0.12, sheer(-0.88))
    cyl('rain_barrel', bp_ + Vector((0, 0, 0.07)), 0.055, 0.14, wood('barrel', (0.36, 0.24, 0.14), 6), verts=16, r2=0.05)
    for hz in (0.03, 0.11): cyl('barrel_hoop', bp_ + Vector((0, 0, hz)), 0.057, 0.008, iron, verts=16)
    # a short mast at the bow with a faded pennant
    mp_ = P(L * 0.4, 0.0, sheer(0.8) - 0.02)
    limb(mp_, mp_ + Vector((0, 0, 0.55)), 0.01, wood('gunwale', (0.45, 0.16, 0.11), 6))
    pn = box('pennant', mp_ + Vector((0, 0, 0.5)) - d * 0.06, (0.12, 0.004, 0.05), varied('pennant', (0.55, 0.2, 0.15), 0.08, 0.9), bevel=0, rot=(0, 0.1, a))
    # cabin: vertical boards, cream trim, framed windows
    cl, cx = L * 0.6, -0.15
    cabin_w = wood('cabin_boards', (0.36, 0.42, 0.36), 9, axis='Z')
    trim = solid('trim_cream', (0.82, 0.76, 0.62), 0.5)
    box('cabin', P(cx, 0, 0.42), (cl, 0.5, 0.46), cabin_w, bevel=0.012, rot=R_)
    for k in range(int(cl / 0.045)):
        box('board', P(cx - cl / 2 + 0.02 + k * 0.045, -0.252, 0.42), (0.008, 0.006, 0.44), solid('board_gap', (0.1, 0.1, 0.09), 0.8), bevel=0, rot=R_)
    for (za, h_) in ((0.2, 0.025), (0.645, 0.03)):
        box('trimband', P(cx, -0.255, za), (cl + 0.02, 0.012, h_), trim, bevel=0, rot=R_)
    for k in range(3):
        u = cx - cl / 2 + 0.25 + k * (cl - 0.5) / 2
        box('win_frame', P(u, -0.258, 0.45), (0.28, 0.012, 0.235), trim, bevel=0.004, rot=R_)
        box('win_glass', P(u, -0.262, 0.45), (0.235, 0.006, 0.19), glow, bevel=0, rot=R_)
        box('win_mull', P(u, -0.266, 0.45), (0.012, 0.006, 0.19), trim, bevel=0, rot=R_)
        box('win_mull', P(u, -0.266, 0.45), (0.235, 0.006, 0.012), trim, bevel=0, rot=R_)
        col = cloths[(k * 2 + 1) % 6]
        box('curtain', P(u - 0.085, -0.263, 0.45), (0.05, 0.004, 0.19), varied('curtain%d' % ((k * 2 + 1) % 6), col, 0.06, 0.95), bevel=0, rot=R_)
        box('win_box', P(u, -0.285, 0.31), (0.26, 0.05, 0.05), wood('winbox', (0.45, 0.16, 0.11), 6), bevel=0.004, rot=R_)
        for q in range(3):
            fc = FLOWERS[(k * 3 + q) % len(FLOWERS)]
            sphere('wb_flower', P(u - 0.08 + q * 0.08, -0.285, 0.35), 0.022, solid('fl%.2f%.2f' % fc[:2], fc, 0.6), 8)
    room_light(tuple(P(cx, 0, 0.45)), 18)
    # end door with a round porthole
    door = P(cx + cl / 2 + 0.005, 0, 0.4)
    box('door', door, (0.012, 0.2, 0.36), wood('door_red', (0.45, 0.16, 0.11), 6), bevel=0.004, rot=R_)
    cyl('porthole', door + d * 0.01 + Vector((0, 0, 0.07)), 0.045, 0.012, glow, verts=16, rot=(0, math.pi / 2, a))
    cyl('porthole_rim', door + d * 0.008 + Vector((0, 0, 0.07)), 0.055, 0.008, brass_d, verts=16, rot=(0, math.pi / 2, a))
    # roof: tar paper, rail, pots, stove pipe, solar? no: a bucket and a chair
    box('roof', P(cx, 0, 0.67), (cl + 0.08, 0.58, 0.035), corrugated('cabin_roof', (0.2, 0.22, 0.2)), bevel=0.008, rot=R_)
    for k in range(6):
        limb(P(cx - cl / 2 + k * cl / 5, -0.27, 0.69), P(cx - cl / 2 + k * cl / 5, -0.27, 0.8), 0.006, brass_d)
    limb(P(cx - cl / 2, -0.27, 0.8), P(cx + cl / 2, -0.27, 0.8), 0.006, brass_d)
    for k in range(4):
        p = P(cx - cl / 2 + 0.15 + k * 0.26, 0.05, 0.69)
        cyl('rpot', p + Vector((0, 0, 0.04)), 0.04, 0.08, varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8), verts=10)
        sphere('rplant', p + Vector((0, 0, 0.12)), 0.055, solid('rleaf', (0.16, 0.3, 0.1), 0.7), 10, (1, 1, 1.3))
        if k % 2 == 0:
            fc = FLOWERS[k + 2]; sphere('rflower', p + Vector((0.02, 0, 0.17)), 0.02, solid('fl%.2f%.2f' % fc[:2], fc, 0.6), 8)
    sp = P(cx + cl * 0.35, 0.12, 0.69)
    cyl('stove', sp + Vector((0, 0, 0.2)), 0.025, 0.4, iron, verts=8)
    cyl('stove_hat', sp + Vector((0, 0, 0.42)), 0.05, 0.04, iron, verts=8, r2=0.01)
    sm = solid('smoke_c', (0.22, 0.22, 0.24), 0.9)
    for k in range(3):
        sphere('smoke', sp + Vector((k * 0.06, 0, 0.55 + k * 0.15)), 0.05 + k * 0.03, sm, 10)
    # tyre fenders, rope coil, ladder, bow chair and lantern
    for k in range(3):
        ty = cyl('tyre', P(-L * 0.3 + k * L * 0.3, -0.37, 0.09), 0.07, 0.035, solid('tyre', (0.04, 0.04, 0.04), 0.7), verts=20, rot=(math.pi / 2, 0, a)); cut(ty, cyl('ty_hole', P(-L * 0.3 + k * L * 0.3, -0.37, 0.09), 0.035, 0.2, None, verts=14, rot=(math.pi / 2, 0, a)))
        limb(P(-L * 0.3 + k * L * 0.3, -0.36, 0.16), P(-L * 0.3 + k * L * 0.3, -0.34, 0.2), 0.004, varied('rope', (0.6, 0.52, 0.38), 0.05, 0.9))
    cyl('rope_coil', P(L * 0.38, 0.15, 0.2), 0.08, 0.03, varied('rope', (0.6, 0.52, 0.38), 0.05, 0.9), verts=16)
    for k in range(4):
        box('ladder_rung', P(-L * 0.5 - 0.02, -0.15, 0.03 + k * 0.06), (0.012, 0.16, 0.012), iron, bevel=0, rot=R_)
    box('bow_chair', P(L * 0.36, -0.1, 0.24), (0.18, 0.18, 0.03), timber_h, bevel=0.005, rot=(0, 0.25, a))
    lantern(tuple(P(L * 0.47, 0, 0.32)), 0.6)
    hanging_lanterns(tuple(P(-L * 0.45, 0, 0.95)), tuple(P(cx - cl / 2, -0.1, 0.8)), 2, 0.05)
    lr = cyl('lifering', P(0.07, -0.27, 0.45), 0.064, 0.026, varied('ring', (0.85, 0.3, 0.2), 0.05, 0.6), verts=24, rot=(math.pi / 2, 0, a)); cut(lr, cyl('lr_hole', P(0.07, -0.27, 0.45), 0.034, 0.2, None, verts=16, rot=(math.pi / 2, 0, a)))
    # the sign: a big piece of cardboard, lettered in a hurry, propped on the roof
    sb = P(cx - cl * 0.05, -0.2, 0.98)
    card = solid('cardboard', (0.44, 0.32, 0.21), 0.85)
    cb = box('cardboard', sb, (1.62, 0.012, 0.42), card, bevel=0.004, rot=(-0.22, 0, a))
    for k in range(5):  # corrugated edge and a torn corner
        box('card_edge', sb + d * (-0.55 + k * 0.27) + Vector((0, 0, 0.23)), (0.2, 0.014, 0.012), solid('card_dark', (0.45, 0.32, 0.2), 0.9), bevel=0, rot=(-0.22, 0, a))
    tape = solid('tape', (0.85, 0.82, 0.7), 0.4)
    for sg in (-1, 1):
        box('tape', sb + d * sg * 0.5 + Vector((0, 0, 0.18)), (0.1, 0.016, 0.04), tape, bevel=0, rot=(-0.22, 0.6 * sg, a))
        limb(sb + d * sg * 0.45 - Vector((0, 0, 0.22)), sb + d * sg * 0.45 - Vector((0, 0, 0.3)) + s_ * 0.05, 0.006, rope_m if 'rope_m' in globals() else iron)
    text = 'HOME SWEET HOME'
    sz = 0.21; adv = 0.1
    WID = {'M': 1.28, 'W': 1.4, 'E': 0.86, 'T': 0.9, 'H': 1.02, 'O': 1.05, 'S': 0.88, ' ': 0.45}
    scales = [RG.uniform(0.94, 1.14) for ch in text]
    widths = [adv * WID.get(ch, 1.0) * sc_ for ch, sc_ in zip(text, scales)]
    x = -sum(widths) / 2 + widths[0] / 2
    for ch, wch, scl in zip(text, widths, scales):
        if ch != ' ':
            cu = bpy.data.curves.new('home_text', 'FONT'); cu.body = ch
            if MARKER: cu.font = bpy.data.fonts.load(MARKER, check_existing=True)
            cu.size = sz * scl; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.001; cu.shear = RG.uniform(0.05, 0.22)
            t = link(bpy.data.objects.new('home_text', cu)); t.parent = cb
            t.location = (x, -0.008, RG.uniform(-0.022, 0.022))
            t.rotation_euler = (math.pi / 2, RG.uniform(-0.14, 0.14), 0)
            cu.materials.append(solid('marker', (0.04, 0.04, 0.05), 0.6))
        x += wch
    for _ in range(1):  # a scribbled underline
        y0 = RG.uniform(-0.6, 0.4)
        sc_ = box('scribble', cb.location, (1.1, 0.004, 0.012), solid('marker', (0.04, 0.04, 0.05), 0.6), bevel=0)
        sc_.parent = cb; sc_.location = (0.05, -0.009, -0.14); sc_.rotation_euler = (0, RG.uniform(-0.1, 0.1), 0)
    lantern(tuple(sb + d * 0.95 - Vector((0, 0, 0.15))), 0.45)
    return P

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

weathered = wood('weathered', (0.27, 0.23, 0.19), 7)
weathered2 = wood('weathered2', (0.33, 0.27, 0.2), 7)
rusty_sheet = corrugated('rusty_sheet', (0.32, 0.28, 0.24))
rope_m = varied('rope', (0.6, 0.52, 0.38), 0.05, 0.9)

def rickety_bridge(a, b, w=0.55, sag=0.07, z0=0.3):
    """Old footbridge: sagging uneven planks with gaps, a rusty patch,
    crooked posts into the water, rope-and-pole railings."""
    a, b = Vector(a), Vector(b); dvec = b - a; L = dvec.length; ang = math.atan2(dvec.y, dvec.x)
    nrm = Vector((-math.sin(ang), math.cos(ang), 0))
    n = int(L / 0.09)
    for k in range(n):
        t = (k + 0.5) / n
        if RG.random() < 0.08: continue          # missing plank
        c = a + dvec * t
        z = z0 - sag * 4 * t * (1 - t) + RG.uniform(-0.012, 0.012)
        box('plank', (c.x, c.y, z), (L / n - 0.015, w * RG.uniform(0.85, 1.05), 0.03), RG.choice([weathered, weathered2]), bevel=0.004,
            rot=(RG.uniform(-0.05, 0.05), RG.uniform(-0.04, 0.04), ang + RG.uniform(-0.06, 0.06)))
    pc = a + dvec * RG.uniform(0.3, 0.6)
    box('patch', (pc.x, pc.y, z0 - sag + 0.03), (0.22, w * 0.6, 0.008), rusty_sheet, bevel=0, rot=(0, 0.03, ang + 0.2))
    for sg in (-1, 1):
        for t in (0.0, 0.5, 1.0):
            c = a + dvec * t + nrm * sg * (w / 2 + 0.02)
            zt = z0 - sag * 4 * t * (1 - t)
            lean = Vector((RG.uniform(-0.06, 0.06), RG.uniform(-0.06, 0.06), 0))
            limb(Vector((c.x, c.y, -0.2)), Vector((c.x, c.y, zt - 0.02)) + lean * 0.3, 0.035, weathered)   # pile
            limb(Vector((c.x, c.y, zt)), Vector((c.x, c.y, zt + 0.42)) + lean, 0.018, weathered2)           # rail pole
        pts = [a + dvec * t + nrm * sg * (w / 2 + 0.02) + Vector((0, 0, z0 - sag * 4 * t * (1 - t) + 0.38 - 0.06 * 4 * t * (1 - t))) for t in [k / 10 for k in range(11)]]
        for p, q in zip(pts, pts[1:]):
            limb(p, q, 0.007, rope_m)
    # cross bracing under the deck
    for t in (0.25, 0.75):
        c = a + dvec * t
        limb(Vector((c.x, c.y, -0.1)) + nrm * (w / 2), Vector((c.x, c.y, z0 - 0.08)) - nrm * (w / 2), 0.015, weathered)

def makeshift_corridor(a, b, z, w=0.55, h=0.7, legs=True):
    """Patched, sagging skyway: corrugated rusty sheets and odd planks on a
    crooked frame, propped up by struts, a single lit window."""
    a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z)); dvec = b - a; L = dvec.length; ang = math.atan2(dvec.y, dvec.x)
    nrm = Vector((-math.sin(ang), math.cos(ang), 0))
    segs = 3
    for k in range(segs):
        t0, t1 = k / segs, (k + 1) / segs
        c = a + dvec * ((t0 + t1) / 2) - Vector((0, 0, 0.06 * math.sin(math.pi * (t0 + t1) / 2)))
        mat = [rusty_sheet, weathered2, rusty_sheet][k]
        bx = box('cor_seg', c + Vector((0, 0, h / 2)), (L / segs + 0.03, w * RG.uniform(0.92, 1.05), h * RG.uniform(0.9, 1.05)), mat, bevel=0.01,
                 rot=(RG.uniform(-0.04, 0.04), RG.uniform(-0.05, 0.05), ang + RG.uniform(-0.03, 0.03)))
        rf = box('cor_roof', c + Vector((0, 0, h + 0.05)), (L / segs + 0.08, w + 0.16, 0.03), rusty_sheet, bevel=0.005,
                 rot=(RG.uniform(-0.12, 0.12), 0, ang))
        if k == 1:
            p = c - nrm * (w / 2 + 0.005) + Vector((0, 0, h * 0.55))
            box('cor_win', p, (0.16, 0.01, 0.16), glow, bevel=0, rot=(0, 0, ang))
            box('cor_win_f', p - nrm * 0.004, (0.19, 0.008, 0.19), weathered, bevel=0, rot=(0, 0, ang))
    for t in (0.2, 0.8):
        c = a + dvec * t
        limb(c - Vector((0, 0, 0.9)) - nrm * 0.1, c + Vector((0, 0, 0.02)), 0.03, weathered)
    room_light(tuple((a + b) / 2 + Vector((0, 0, h / 2))), 12)

FAR_COL = tuple(float(v) for v in os.environ.get('FAR_COL', '0.6,0.62,0.95').split(','))
FAR_GLOW = float(os.environ.get('FAR_GLOW', '0.02'))
def endless_water(size=80.0):
    """Canal water to the edges of the view, fading into dusk haze far out."""
    m, n, l, b = node_mat('endless_canal')
    tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 7
    l.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.05
    l.new(nz.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    vl = n.new('ShaderNodeVectorMath'); vl.operation = 'LENGTH'; l.new(tc.outputs['Object'], vl.inputs[0])
    fr = n.new('ShaderNodeMapRange'); fr.inputs['From Min'].default_value = 6.0; fr.inputs['From Max'].default_value = 14.0
    l.new(vl.outputs['Value'], fr.inputs['Value'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.012, 0.022, 0.024, 1); mx.inputs['B'].default_value = (0.07, 0.06, 0.08, 1)
    l.new(fr.outputs['Result'], mx.inputs['Factor']); l.new(mx.outputs['Result'], b.inputs['Base Color'])
    rr = n.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.04; rr.inputs['To Max'].default_value = 0.35
    l.new(fr.outputs['Result'], rr.inputs['Value']); l.new(rr.outputs['Result'], b.inputs['Roughness'])
    # Far out the water is just dusk haze: a fixed glow, so the warm sun on the
    # buildings doesn't lift the background. FAR_GLOW sets its brightness.
    em = n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*FAR_COL, 1)
    em.inputs['Strength'].default_value = FAR_GLOW
    ms = n.new('ShaderNodeMixShader'); out = next(x for x in n if x.type == 'OUTPUT_MATERIAL')
    fk = n.new('ShaderNodeMapRange'); fk.inputs['From Min'].default_value = 7.0; fk.inputs['From Max'].default_value = 13.0
    l.new(vl.outputs['Value'], fk.inputs['Value'])
    l.new(fk.outputs['Result'], ms.inputs['Fac']); l.new(b.outputs['BSDF'], ms.inputs[1]); l.new(em.outputs['Emission'], ms.inputs[2])
    l.new(ms.outputs['Shader'], out.inputs['Surface'])
    me = bpy.data.meshes.new('canal'); bm_ = bmesh.new(); bmesh.ops.create_grid(bm_, x_segments=1, y_segments=1, size=size / 2)
    bm_.to_mesh(me); bm_.free(); o = link(bpy.data.objects.new('canal', me)); me.materials.append(m)
    # a dark bed below so the quays don't float
    box('canal_bed', (0, 0, -0.32), (size, size, 0.02), solid('bed', (0.02, 0.025, 0.025), 0.9), bevel=0)
    return o

LAMP_GAS = (1.0, 0.62, 0.28); LAMP_WALL = (1.0, 0.8, 0.5); LAMP_RED = (1.0, 0.5, 0.36); LAMP_GLOBE = (0.92, 0.92, 0.88); LAMP_BOAT = (1.0, 0.5, 0.18)
def emissive(name, col, k=12):
    return solid(name, tuple(min(1, c * 1.0) for c in col), 0.2, emit=col, strength=k)

def gas_lamp(x, y, z0, h=1.2):
    """Fluted cast-iron lamp post: plinth, ribs, collars, ladder crossbar,
    square lantern with corner bars, crown and finial."""
    cyl('gl_plinth', (x, y, z0 + 0.05), 0.11, 0.1, iron, verts=8, bevel=0.01)
    cyl('gl_base', (x, y, z0 + 0.2), 0.075, 0.22, iron, verts=16, r2=0.045)
    cyl('gl_shaft', (x, y, z0 + h / 2 + 0.1), 0.03, h - 0.2, iron, verts=12, r2=0.024)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        limb(Vector((x + math.cos(a) * 0.032, y + math.sin(a) * 0.032, z0 + 0.3)), Vector((x + math.cos(a) * 0.026, y + math.sin(a) * 0.026, z0 + h - 0.1)), 0.006, iron)
    for zz in (z0 + 0.32, z0 + h * 0.6, z0 + h - 0.08):
        cyl('gl_collar', (x, y, zz), 0.045, 0.03, iron, verts=12, bevel=0.005)
    limb(Vector((x - 0.16, y, z0 + h - 0.2)), Vector((x + 0.16, y, z0 + h - 0.2)), 0.008, iron)
    for sg in (-1, 1):
        sphere('gl_bar_end', (x + sg * 0.16, y, z0 + h - 0.2), 0.014, iron, 8)
    hz = z0 + h + 0.15
    cyl('gl_bowl', (x, y, hz - 0.14), 0.07, 0.06, iron, verts=4, r2=0.03, rot=(0, 0, math.pi / 4))
    box('gl_glass', (x, y, hz), (0.13, 0.13, 0.22), emissive('gl_glass_m', LAMP_GAS, 12), bevel=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('gl_corner', (x + sx * 0.068, y + sy * 0.068, hz), (0.014, 0.014, 0.24), iron, bevel=0)
    cyl('gl_roof', (x, y, hz + 0.16), 0.11, 0.1, iron, verts=4, r2=0.02, rot=(0, 0, math.pi / 4))
    sphere('gl_finial', (x, y, hz + 0.23), 0.02, iron, 8)
    L = bpy.data.lights.new('gas', 'POINT'); L.energy = 22; L.color = LAMP_GAS; L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('gas', L)).location = (x, y, hz)

def wall_lantern(W, u, z):
    """Scrolled iron bracket with a caged hexagonal lantern."""
    base = W.P(u, 0.02, z)
    box('wl_plate', base, W.S(0.09, 0.02, 0.18), iron, bevel=0.004)
    pts = [base + W.n * (0.26 * t) + Vector((0, 0, 0.06 + 0.05 * math.sin(math.pi * t))) for t in [k / 8 for k in range(9)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.009, iron)
    curl = [base + W.n * (0.04 + 0.05 * math.cos(t)) + Vector((0, 0, -0.03 + 0.05 * math.sin(t))) for t in [k / 8 * 4.5 for k in range(9)]]
    for p, q in zip(curl, curl[1:]): limb(p, q, 0.006, iron)
    tip = pts[-1]; lp = tip - Vector((0, 0, 0.15))
    limb(tip, tip - Vector((0, 0, 0.05)), 0.004, iron)
    cyl('wl_glass', lp, 0.05, 0.13, emissive('wl_glass_m', LAMP_WALL, 11), verts=6)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        box('wl_bar', lp + Vector((math.cos(a) * 0.052, math.sin(a) * 0.052, 0)), (0.008, 0.008, 0.14), iron, bevel=0)
    cyl('wl_roof', lp + Vector((0, 0, 0.09)), 0.07, 0.05, iron, verts=6, r2=0.015)
    cyl('wl_bottom', lp - Vector((0, 0, 0.08)), 0.055, 0.03, iron, verts=6, r2=0.02)
    sphere('wl_ring', lp + Vector((0, 0, 0.13)), 0.012, iron, 6)
    L = bpy.data.lights.new('wl', 'POINT'); L.energy = 10; L.color = LAMP_WALL
    link(bpy.data.objects.new('wl', L)).location = lp

def lantern_paper_mat(tint):
    """Paper glowing a gentle red, with painted cloud swirls and rings like a Chinese lantern."""
    key = 'cn_paper_%.2f' % tint[1]
    if key in bpy.data.materials: return bpy.data.materials[key]
    m, n, l, b = node_mat(key)
    tc = n.new('ShaderNodeTexCoord')
    wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = 9; wv.inputs['Distortion'].default_value = 7
    l.new(tc.outputs['Object'], wv.inputs['Vector'])
    vo = n.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 14
    l.new(tc.outputs['Object'], vo.inputs['Vector'])
    pat = n.new('ShaderNodeMath'); pat.operation = 'MULTIPLY'
    st = n.new('ShaderNodeMapRange'); st.inputs['From Min'].default_value = 0.55; st.inputs['From Max'].default_value = 0.75
    l.new(wv.outputs['Fac'], st.inputs['Value'])
    ve = n.new('ShaderNodeMapRange'); ve.inputs['From Min'].default_value = 0.0; ve.inputs['From Max'].default_value = 0.04
    l.new(vo.outputs['Distance'], ve.inputs['Value'])
    l.new(st.outputs['Result'], pat.inputs[0]); l.new(ve.outputs['Result'], pat.inputs[1])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (*tint, 1); mx.inputs['B'].default_value = (0.55, 0.08, 0.05, 1)
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    l.new(pat.outputs['Value'], inv.inputs[1]); l.new(inv.outputs['Value'], mx.inputs['Factor'])
    l.new(mx.outputs['Result'], b.inputs['Emission Color']); l.new(mx.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Emission Strength'].default_value = 5.5; b.inputs['Roughness'].default_value = 0.7
    return m

def paper_lantern(p, r=0.1, color=LAMP_RED):
    """Chinese-style lantern: patterned glowing paper, lacquered ribs, gold
    bands top and bottom, red tassel."""
    p = Vector(p)
    sphere('paper', p, r, lantern_paper_mat((color[0], color[1], color[2])), 20, (1, 1, 1.05))
    gold = solid('lantern_gold', (0.8, 0.58, 0.22), 0.3, metal=1.0)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        pts = [p + Vector((math.cos(a) * r * math.sin(t) * 1.01, math.sin(a) * r * math.sin(t) * 1.01, r * 1.05 * math.cos(t))) for t in [q / 8 * math.pi for q in range(9)]]
        for u, v in zip(pts, pts[1:]): limb(u, v, 0.0035, solid('rib', (0.3, 0.06, 0.04), 0.5))
    for sg in (1, -1):
        cyl('lantern_band', p + Vector((0, 0, sg * r * 0.98)), r * 0.42, 0.03, gold, verts=16)
        cyl('lantern_band2', p + Vector((0, 0, sg * r * 1.04)), r * 0.3, 0.02, solid('rib', (0.3, 0.06, 0.04), 0.5), verts=16)
    tm = solid('tassel', (0.7, 0.1, 0.07), 0.8)
    cyl('tassel_knot', p - Vector((0, 0, r * 1.1)), 0.012, 0.025, gold, verts=8)
    for k in range(5):
        a = k / 5 * 2 * math.pi
        limb(p - Vector((0, 0, r * 1.12)), p - Vector((0, 0, r * 1.12 + 0.1)) + Vector((math.cos(a) * 0.01, math.sin(a) * 0.01, 0)), 0.003, tm)
    L = bpy.data.lights.new('pl', 'POINT'); L.energy = 4; L.color = color; L.shadow_soft_size = r
    link(bpy.data.objects.new('pl', L)).location = p

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
    gid = (abs(hash((round(u, 3), round(z, 3)))) % 997) / 997.0
    for p, q in zip(pts, pts[1:]):
        limb(p, q, 0.008, nm)['glow_group'] = gid      # the whole tube lights at once
    L = bpy.data.lights.new('neon', 'POINT'); L.energy = 5; L.color = color
    link(bpy.data.objects.new('neon', L)).location = W.P(u, 0.2, z)

def hanging_sign(W, u, z, col=(0.5, 0.2, 0.15)):
    base = W.P(u, 0.0, z)
    limb(base, base + W.n * 0.45, 0.012, iron)
    for d in (0.08, 0.37):
        limb(base + W.n * d, base + W.n * d - Vector((0, 0, 0.06)), 0.004, iron)
    box('hsign', base + W.n * 0.23 - Vector((0, 0, 0.2)), (0.3, 0.02, 0.24) if W.axis == 'x' else (0.02, 0.3, 0.24), varied('hsign', col, 0.1, 0.7), bevel=0.01)

def emissive(name, col, k=12):
    return solid(name, tuple(min(1, c * 1.0) for c in col), 0.2, emit=col, strength=k)

def gas_lamp(x, y, z0, h=1.2):
    """Fluted cast-iron lamp post: plinth, ribs, collars, ladder crossbar,
    square lantern with corner bars, crown and finial."""
    cyl('gl_plinth', (x, y, z0 + 0.05), 0.11, 0.1, iron, verts=8, bevel=0.01)
    cyl('gl_base', (x, y, z0 + 0.2), 0.075, 0.22, iron, verts=16, r2=0.045)
    cyl('gl_shaft', (x, y, z0 + h / 2 + 0.1), 0.03, h - 0.2, iron, verts=12, r2=0.024)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        limb(Vector((x + math.cos(a) * 0.032, y + math.sin(a) * 0.032, z0 + 0.3)), Vector((x + math.cos(a) * 0.026, y + math.sin(a) * 0.026, z0 + h - 0.1)), 0.006, iron)
    for zz in (z0 + 0.32, z0 + h * 0.6, z0 + h - 0.08):
        cyl('gl_collar', (x, y, zz), 0.045, 0.03, iron, verts=12, bevel=0.005)
    limb(Vector((x - 0.16, y, z0 + h - 0.2)), Vector((x + 0.16, y, z0 + h - 0.2)), 0.008, iron)
    for sg in (-1, 1):
        sphere('gl_bar_end', (x + sg * 0.16, y, z0 + h - 0.2), 0.014, iron, 8)
    hz = z0 + h + 0.15
    cyl('gl_bowl', (x, y, hz - 0.14), 0.07, 0.06, iron, verts=4, r2=0.03, rot=(0, 0, math.pi / 4))
    box('gl_glass', (x, y, hz), (0.13, 0.13, 0.22), emissive('gl_glass_m', LAMP_GAS, 12), bevel=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('gl_corner', (x + sx * 0.068, y + sy * 0.068, hz), (0.014, 0.014, 0.24), iron, bevel=0)
    cyl('gl_roof', (x, y, hz + 0.16), 0.11, 0.1, iron, verts=4, r2=0.02, rot=(0, 0, math.pi / 4))
    sphere('gl_finial', (x, y, hz + 0.23), 0.02, iron, 8)
    L = bpy.data.lights.new('gas', 'POINT'); L.energy = 22; L.color = LAMP_GAS; L.shadow_soft_size = 0.05
    link(bpy.data.objects.new('gas', L)).location = (x, y, hz)

def wall_lantern(W, u, z):
    """Scrolled iron bracket with a caged hexagonal lantern."""
    base = W.P(u, 0.02, z)
    box('wl_plate', base, W.S(0.09, 0.02, 0.18), iron, bevel=0.004)
    pts = [base + W.n * (0.26 * t) + Vector((0, 0, 0.06 + 0.05 * math.sin(math.pi * t))) for t in [k / 8 for k in range(9)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.009, iron)
    curl = [base + W.n * (0.04 + 0.05 * math.cos(t)) + Vector((0, 0, -0.03 + 0.05 * math.sin(t))) for t in [k / 8 * 4.5 for k in range(9)]]
    for p, q in zip(curl, curl[1:]): limb(p, q, 0.006, iron)
    tip = pts[-1]; lp = tip - Vector((0, 0, 0.15))
    limb(tip, tip - Vector((0, 0, 0.05)), 0.004, iron)
    cyl('wl_glass', lp, 0.05, 0.13, emissive('wl_glass_m', LAMP_WALL, 11), verts=6)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        box('wl_bar', lp + Vector((math.cos(a) * 0.052, math.sin(a) * 0.052, 0)), (0.008, 0.008, 0.14), iron, bevel=0)
    cyl('wl_roof', lp + Vector((0, 0, 0.09)), 0.07, 0.05, iron, verts=6, r2=0.015)
    cyl('wl_bottom', lp - Vector((0, 0, 0.08)), 0.055, 0.03, iron, verts=6, r2=0.02)
    sphere('wl_ring', lp + Vector((0, 0, 0.13)), 0.012, iron, 6)
    L = bpy.data.lights.new('wl', 'POINT'); L.energy = 10; L.color = LAMP_WALL
    link(bpy.data.objects.new('wl', L)).location = lp

def hanging_lanterns(a, b, n=4, sag=0.35):
    wire(a, b, sag)
    a, b = Vector(a), Vector(b)
    reds = [(1.0, 0.48, 0.34), (1.0, 0.54, 0.38), (1.0, 0.44, 0.34)]
    for k in range(1, n + 1):
        t = k / (n + 1)
        p = a.lerp(b, t) + Vector((0, 0, -sag * 4 * t * (1 - t) - 0.14))
        limb(p + Vector((0, 0, 0.14)), p + Vector((0, 0, 0.09)), 0.003, iron)
        paper_lantern(tuple(p), 0.065, reds[k % 3])

def globe_post(x, y, z0, h=0.6):
    cyl('gp_base', (x, y, z0 + 0.04), 0.06, 0.08, iron, verts=12, bevel=0.01)
    cyl('gp_post', (x, y, z0 + h / 2), 0.02, h, iron, verts=8)
    cyl('gp_collar', (x, y, z0 + h - 0.01), 0.04, 0.04, brass_d, verts=12, r2=0.03)
    sphere('gp_globe', (x, y, z0 + h + 0.07), 0.065, emissive('gp_glass', LAMP_GLOBE, 8), 16)
    cyl('gp_band', (x, y, z0 + h + 0.07), 0.067, 0.012, brass_d, verts=16)
    L = bpy.data.lights.new('gp', 'POINT'); L.energy = 6; L.color = LAMP_GLOBE
    link(bpy.data.objects.new('gp', L)).location = (x, y, z0 + h + 0.07)

def lantern(loc, s=1.0):
    """Boat / hand lantern: caged glass, handle, warm orange."""
    x, y, z = loc
    cyl('hl_base', (x, y, z - 0.08 * s), 0.07 * s, 0.03 * s, iron, verts=12)
    cyl('hl_glass', (x, y, z), 0.055 * s, 0.14 * s, emissive('hl_glass_m', LAMP_BOAT, 12), verts=12)
    for k in range(4):
        a = k / 4 * 2 * math.pi
        box('hl_bar', (x + math.cos(a) * 0.058 * s, y + math.sin(a) * 0.058 * s, z), (0.01 * s, 0.01 * s, 0.15 * s), iron, bevel=0)
    cyl('hl_top', (x, y, z + 0.09 * s), 0.07 * s, 0.04 * s, iron, verts=12, r2=0.03 * s)
    for k in range(7):
        a = math.pi * k / 6
        limb(Vector((x - 0.05 * s * math.cos(a) * 0 + 0.05 * s * math.cos(a), y, z + 0.11 * s + 0.06 * s * math.sin(a))),
             Vector((x + 0.05 * s * math.cos(a + math.pi / 6), y, z + 0.11 * s + 0.06 * s * math.sin(a + math.pi / 6))), 0.004 * s, iron) if k < 6 else None
    L = bpy.data.lights.new('hl', 'POINT'); L.energy = 6 * s; L.color = LAMP_BOAT
    link(bpy.data.objects.new('hl', L)).location = (x, y, z)

CLOTH_COLS = [(0.7, 0.66, 0.58), (0.45, 0.16, 0.14), (0.24, 0.3, 0.42), (0.62, 0.52, 0.3), (0.85, 0.82, 0.76), (0.35, 0.42, 0.32), (0.6, 0.38, 0.45)]
def garment(p, ang, kind, col):
    m = varied('garment%.2f' % col[0], col, 0.06, 0.95, bump=0.05, bump_scale=120)
    R_ = (0, 0, ang)
    d = Vector((math.cos(ang), math.sin(ang), 0))
    if kind == 'shirt':
        box('g_body', p - Vector((0, 0, 0.13)), (0.16, 0.01, 0.22), m, bevel=0, rot=R_)
        for sg in (-1, 1):
            box('g_sleeve', p + d * sg * 0.1 - Vector((0, 0, 0.06)), (0.07, 0.01, 0.1), m, bevel=0, rot=(0, sg * 0.5, ang))
        box('g_collar', p - Vector((0, 0, 0.02)), (0.06, 0.012, 0.02), m, bevel=0, rot=R_)
    elif kind == 'trousers':
        box('g_waist', p - Vector((0, 0, 0.03)), (0.15, 0.01, 0.05), m, bevel=0, rot=R_)
        for sg in (-1, 1):
            box('g_leg', p + d * sg * 0.04 - Vector((0, 0, 0.2)), (0.065, 0.01, 0.3), m, bevel=0, rot=(0, sg * 0.06, ang))
    elif kind == 'dress':
        c = cyl('g_dress', p - Vector((0, 0, 0.17)), 0.12, 0.3, m, verts=4, r2=0.05)
        c.scale = (1, 0.08, 1); c.rotation_euler = (0, 0, ang + math.pi / 4)
    elif kind == 'socks':
        for sg in (-1, 1):
            box('g_sock', p + d * sg * 0.03 - Vector((0, 0, 0.06)), (0.035, 0.01, 0.1), m, bevel=0, rot=R_)
            box('g_foot', p + d * (sg * 0.03 + 0.025) - Vector((0, 0, 0.11)), (0.05, 0.01, 0.03), m, bevel=0, rot=R_)
    else:  # towel / sheet folded over the line
        box('g_towel', p - Vector((0, 0, 0.14)), (0.2, 0.012, 0.28), m, bevel=0.004, rot=(0.05, 0, ang))
    for sg in (-1, 1):  # pegs
        box('peg', p + d * sg * 0.05, (0.012, 0.012, 0.035), timber_h, bevel=0, rot=R_)

def laundry(a, b):
    a, b = Vector(a), Vector(b)
    wire(a, b, 0.15)
    ang = math.atan2(b.y - a.y, b.x - a.x)
    kinds = ['shirt', 'trousers', 'towel', 'dress', 'socks', 'shirt']
    n = 6
    for k in range(n):
        t = (k + 0.7) / (n + 0.4)
        p = a.lerp(b, t) + Vector((0, 0, -0.15 * 4 * t * (1 - t)))
        garment(p, ang, kinds[k % len(kinds)], RG.choice(CLOTH_COLS))

def worn_poster(W, u, z, w, h):
    """Faded, layered, slightly torn posters: muted colours, grime, a printed block."""
    base = RG.choice([(0.7, 0.62, 0.45), (0.55, 0.3, 0.25), (0.45, 0.5, 0.55), (0.75, 0.7, 0.6), (0.5, 0.45, 0.35)])
    m = varied('poster_%.2f' % base[0], base, 0.25, 0.9, bump=0.1, bump_scale=60)
    b = box('poster', W.P(u, 0.008, z), W.S(w, 0.004, h), m, bevel=0)
    b.rotation_euler.rotate_axis('Y' if W.axis == 'y' else 'X', RG.uniform(-0.05, 0.05))
    ink = solid('poster_ink%d' % RG.randint(0, 3), RG.choice([(0.15, 0.12, 0.1), (0.5, 0.15, 0.12), (0.12, 0.2, 0.3), (0.3, 0.25, 0.1)]), 0.8)
    box('poster_print', W.P(u, 0.011, z + h * 0.15), W.S(w * 0.7, 0.002, h * 0.35), ink, bevel=0)
    for k in range(3):
        box('poster_line', W.P(u - w * 0.1, 0.011, z - h * 0.18 - k * 0.04), W.S(w * RG.uniform(0.3, 0.6), 0.002, 0.015), ink, bevel=0)
    if RG.random() < 0.6:  # torn scrap of an older poster underneath
        box('poster_scrap', W.P(u + w * 0.45, 0.006, z - h * 0.35), W.S(w * 0.35, 0.003, h * 0.3), varied('poster_old', (0.6, 0.55, 0.45), 0.2, 0.9), bevel=0,
            rot=(0, 0, 0)).rotation_euler.rotate_axis('Y' if W.axis == 'y' else 'X', 0.3)

def graffiti(W, u, z, text, col, size=0.18, ang=0.0):
    cu = bpy.data.curves.new('tag', 'FONT'); cu.body = text
    if GRAFFITI: cu.font = bpy.data.fonts.load(GRAFFITI, check_existing=True)
    cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.0005
    t = link(bpy.data.objects.new('tag', cu))
    t.location = W.P(u, 0.012, z)
    t.rotation_euler = (math.pi / 2, ang, 0) if W.axis == 'y' else (math.pi / 2, ang, math.pi / 2)
    cu.materials.append(solid('spray_%.2f' % col[0], col, 0.7))
    for k in range(RG.randint(2, 5)):  # paint drips
        box('drip', W.P(u + RG.uniform(-size * 1.5, size * 1.5), 0.011, z - size * 0.5 - 0.04), W.S(0.006, 0.002, RG.uniform(0.03, 0.09)),
            solid('spray_%.2f' % col[0], col, 0.7), bevel=0)

def pigeon(x, y, z, a):
    g = varied('pigeon', (0.42, 0.42, 0.46), 0.15, 0.7)
    sphere('pg_body', (x, y, z + 0.03), 0.03, g, 10, (1.4, 0.9, 0.9)).rotation_euler.z = a
    sphere('pg_head', (x + math.cos(a) * 0.035, y + math.sin(a) * 0.035, z + 0.06), 0.016, g, 8)

def trash(x, y, z):
    cyl('bin', (x + 0.45, y, z + 0.18), 0.12, 0.36, solid('bin_metal', (0.25, 0.28, 0.26), 0.5, metal=0.5), verts=16)
    cyl('bin_lid', (x + 0.45, y, z + 0.38), 0.13, 0.03, solid('bin_metal', (0.25, 0.28, 0.26), 0.5, metal=0.5), verts=16, rot=(0.25, 0, 0))

def quay_ladder(x, y, ang, top=0.28):
    for k in range(5):
        p = Vector((x, y, top - 0.05 - k * 0.08))
        limb(p + Vector((math.cos(ang), math.sin(ang), 0)) * 0.08, p - Vector((math.cos(ang), math.sin(ang), 0)) * 0.08, 0.008, rustm)
    for sg in (-1, 1):
        q = Vector((x, y, 0)) + Vector((math.cos(ang), math.sin(ang), 0)) * sg * 0.08
        limb(q + Vector((0, 0, -0.15)), q + Vector((0, 0, top + 0.18)), 0.01, rustm)

def gable_end(x, y0, y1, z0, rise, mat, oculus=True, side=1):
    """Fill the triangle under a gable roof (ridge along x) on the +x end, with a round window."""
    cy_ = (y0 + y1) / 2
    me = bpy.data.meshes.new('gable'); bm_ = bmesh.new()
    vs = [bm_.verts.new(v) for v in ((x, y0, z0), (x, y1, z0), (x, cy_, z0 + rise))]
    bm_.faces.new(vs); bm_.to_mesh(me); bm_.free()
    o = link(bpy.data.objects.new('gable', me)); me.materials.append(mat)
    sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.12; sl.offset = -side
    if oculus:
        r = rise * 0.2; c = Vector((x + side * 0.015, cy_, z0 + rise * 0.38))
        gmat, gcol = pick_glow()
        cyl('oculus_glass', c, r, 0.02, gmat, verts=28, rot=(0, math.pi / 2, 0))
        ring = cyl('oculus_frame', c + Vector((side * 0.01, 0, 0)), r + 0.04, 0.04, quay, verts=32, rot=(0, math.pi / 2, 0))
        cut(ring, cyl('oculus_hole', c, r, 0.2, None, verts=28, rot=(0, math.pi / 2, 0)))
        for a in (0.0, math.pi / 2):
            b = box('oculus_bar', c + Vector((side * 0.02, 0, 0)), (0.02, 2 * r, 0.02), solid('frame_arch', (0.16, 0.22, 0.18), 0.55), bevel=0)
            b.rotation_euler = (a, 0, 0)
        for k in range(10):  # brick ring
            a = k / 10 * 2 * math.pi
            box('oculus_brick', c + Vector((side * 0.01, math.cos(a) * (r + 0.07), math.sin(a) * (r + 0.07))), (0.04, 0.06, 0.09), varied('voussoir', (0.42, 0.24, 0.17), 0.12, 0.85), bevel=0.005).rotation_euler = (a + math.pi / 2, 0, 0)
        room_light(tuple(c - Vector((side * 0.4, 0, 0))), 10, gcol)
        if RG.random() < 0.7:  # a plant silhouette in the round window
            sphere('oc_plant', c - Vector((side * 0.03, 0, r * 0.45)), r * 0.45, lit_copy(solid('ileaf_o', (0.14, 0.28, 0.09), 0.7)), 10, (0.4, 1, 0.8))

def big_flower_pot(p, colour=(0.96, 0.62, 0.72)):
    """A big terracotta pot overflowing with peony-like blooms."""
    x, y, z = p
    pm = varied('big_pot', (0.6, 0.32, 0.2), 0.08, 0.75, bump=0.2)
    cyl('big_pot', (x, y, z + 0.17), 0.13, 0.34, pm, verts=24, r2=0.18, bevel=0.01)
    cyl('big_pot_rim', (x, y, z + 0.34), 0.2, 0.05, pm, verts=24, bevel=0.01)
    leaf = leaf_mesh('peony_leaf', (0.2, 0.4, 0.12))
    for _ in range(140):
        v = Vector((RG.gauss(0, 1), RG.gauss(0, 1), abs(RG.gauss(0, 1)) * 0.8)).normalized() * RG.uniform(0.08, 0.26)
        o = link(bpy.data.objects.new('pl_leaf', leaf)); o.location = Vector((x, y, z + 0.38)) + v
        o.rotation_euler = (RG.uniform(0, 6.28), RG.uniform(0, 6.28), RG.uniform(0, 6.28)); s_ = RG.uniform(1.6, 2.3); o.scale = (s_, s_, s_)
    for k in range(7):
        a = k / 7 * 2 * math.pi + RG.uniform(-0.3, 0.3)
        c = Vector((x + math.cos(a) * RG.uniform(0.06, 0.2), y + math.sin(a) * RG.uniform(0.06, 0.2), z + 0.45 + RG.uniform(0, 0.14)))
        col = colour if k % 3 else (0.98, 0.9, 0.9)
        pm_ = solid('peony_%.2f' % col[1], col, 0.5)
        pm_.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.2
        for layer, (rr, nn) in enumerate(((0.065, 9), (0.048, 7), (0.03, 5))):
            for q in range(nn):
                b = q / nn * 2 * math.pi + layer * 0.4
                pe = sphere('peony_petal', c + Vector((math.cos(b) * rr * 0.7, math.sin(b) * rr * 0.7, layer * 0.018)), rr * 0.55, pm_, 10, (1, 0.7, 0.45))
                pe.rotation_euler = (0, -0.6 + layer * 0.3, b)
        sphere('peony_heart', c + Vector((0, 0, 0.05)), 0.018, solid('peony_heart', (0.98, 0.8, 0.4), 0.5), 8)

def leafy_pot(p, kind='leafy'):
    x, y, z = p
    pm = varied('ipot', (0.5, 0.28, 0.18), 0.15, 0.8)
    cyl('lp_pot', (x, y, z + 0.12), 0.12, 0.24, pm, verts=20, r2=0.14, bevel=0.01)
    cyl('lp_soil', (x, y, z + 0.23), 0.12, 0.02, solid('soil', (0.13, 0.09, 0.06), 0.95), verts=16)
    if kind == 'lavender':
        stem = solid('lav_stem', (0.35, 0.45, 0.3), 0.7); tip = solid('lav_tip', (0.55, 0.42, 0.82), 0.6)
        for _ in range(26):
            a, r = RG.uniform(0, 6.28), RG.uniform(0, 0.09)
            b0 = Vector((x + math.cos(a) * r, y + math.sin(a) * r, z + 0.24))
            top = b0 + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, RG.uniform(0.25, 0.38)))
            limb(b0, top, 0.004, stem)
            sphere('lav', top, 0.016, tip, 6, (1, 1, 3.0))
    else:  # broad glossy leaves fanning out
        lm = varied('broad_leaf', (0.22, 0.42, 0.14), 0.15, 0.35)
        for k in range(11):
            a = k / 11 * 2 * math.pi + RG.uniform(-0.2, 0.2)
            tilt = RG.uniform(0.5, 1.0)
            c = Vector((x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, z + 0.32 + RG.uniform(0, 0.15)))
            limb(Vector((x, y, z + 0.24)), c, 0.006, solid('lav_stem', (0.35, 0.45, 0.3), 0.7))
            lf = sphere('broad_leaf', c + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.02)), 0.08, lm, 12, (1.0, 0.45, 0.06))
            lf.rotation_euler = (0, -tilt * 0.6, a)

# ---- overrides: candle-lit lamps, safer rickety bridges, distinct round windows
CANDLE_COL = (1.0, 0.6, 0.26)
def lamp_glass():
    if 'lamp_clear' in bpy.data.materials: return bpy.data.materials['lamp_clear']
    m, n, l, b = node_mat('lamp_clear')
    b.inputs['Base Color'].default_value = (0.95, 0.9, 0.78, 1); b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.12; b.inputs['IOR'].default_value = 1.45
    return m

def candle(p, h=0.07, r=0.014, energy=12):
    p = Vector(p)
    cyl('candle_wax', p + Vector((0, 0, h / 2)), r, h, solid('wax', (0.9, 0.85, 0.75), 0.6), verts=10)
    sphere('candle_drip', p + Vector((r * 0.7, 0, h * 0.8)), r * 0.35, solid('wax', (0.9, 0.85, 0.75), 0.6), 6, (1, 1, 1.6))
    fl = p + Vector((0, 0, h + 0.012))
    sphere('flame', fl, 0.007, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1.0, 0.68, 0.28), strength=60), 8, (1, 1, 2.0))
    L = bpy.data.lights.new('candle', 'POINT'); L.energy = energy; L.color = CANDLE_COL; L.shadow_soft_size = 0.04
    link(bpy.data.objects.new('candle', L)).location = fl

def gas_lamp(x, y, z0, h=1.2):
    cyl('gl_plinth', (x, y, z0 + 0.05), 0.11, 0.1, iron, verts=8, bevel=0.01)
    cyl('gl_base', (x, y, z0 + 0.2), 0.075, 0.22, iron, verts=16, r2=0.045)
    cyl('gl_shaft', (x, y, z0 + h / 2 + 0.1), 0.03, h - 0.2, iron, verts=12, r2=0.024)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        limb(Vector((x + math.cos(a) * 0.032, y + math.sin(a) * 0.032, z0 + 0.3)), Vector((x + math.cos(a) * 0.026, y + math.sin(a) * 0.026, z0 + h - 0.1)), 0.006, iron)
    for zz in (z0 + 0.32, z0 + h * 0.6, z0 + h - 0.08):
        cyl('gl_collar', (x, y, zz), 0.045, 0.03, iron, verts=12, bevel=0.005)
    limb(Vector((x - 0.16, y, z0 + h - 0.2)), Vector((x + 0.16, y, z0 + h - 0.2)), 0.008, iron)
    hz = z0 + h + 0.15
    cyl('gl_floor', (x, y, hz - 0.11), 0.075, 0.02, iron, verts=4, rot=(0, 0, math.pi / 4))
    cyl('gl_bowl', (x, y, hz - 0.14), 0.07, 0.05, iron, verts=4, r2=0.03, rot=(0, 0, math.pi / 4))
    box('gl_glass', (x, y, hz), (0.13, 0.13, 0.22), lamp_glass(), bevel=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('gl_corner', (x + sx * 0.068, y + sy * 0.068, hz), (0.014, 0.014, 0.24), iron, bevel=0)
    cyl('gl_roof', (x, y, hz + 0.16), 0.11, 0.1, iron, verts=4, r2=0.02, rot=(0, 0, math.pi / 4))
    sphere('gl_finial', (x, y, hz + 0.23), 0.02, iron, 8)
    candle((x, y, hz - 0.1), 0.1, 0.02, 32)

def wall_lantern(W, u, z):
    base = W.P(u, 0.02, z)
    box('wl_plate', base, W.S(0.09, 0.02, 0.18), iron, bevel=0.004)
    pts = [base + W.n * (0.26 * t) + Vector((0, 0, 0.06 + 0.05 * math.sin(math.pi * t))) for t in [k / 8 for k in range(9)]]
    for p, q in zip(pts, pts[1:]): limb(p, q, 0.009, iron)
    curl = [base + W.n * (0.04 + 0.05 * math.cos(t)) + Vector((0, 0, -0.03 + 0.05 * math.sin(t))) for t in [k / 8 * 4.5 for k in range(9)]]
    for p, q in zip(curl, curl[1:]): limb(p, q, 0.006, iron)
    tip = pts[-1]; lp = tip - Vector((0, 0, 0.15))
    limb(tip, tip - Vector((0, 0, 0.05)), 0.004, iron)
    cyl('wl_glass', lp, 0.05, 0.13, lamp_glass(), verts=6)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        box('wl_bar', lp + Vector((math.cos(a) * 0.052, math.sin(a) * 0.052, 0)), (0.008, 0.008, 0.14), iron, bevel=0)
    cyl('wl_roof', lp + Vector((0, 0, 0.09)), 0.07, 0.05, iron, verts=6, r2=0.015)
    cyl('wl_bottom', lp - Vector((0, 0, 0.075)), 0.055, 0.02, iron, verts=6)
    candle(lp - Vector((0, 0, 0.065)), 0.06, 0.012, 15)

def lantern(loc, s=1.0):
    x, y, z = loc
    cyl('hl_base', (x, y, z - 0.08 * s), 0.07 * s, 0.03 * s, iron, verts=12)
    cyl('hl_glass', (x, y, z), 0.055 * s, 0.14 * s, lamp_glass(), verts=12)
    for k in range(4):
        a = k / 4 * 2 * math.pi
        box('hl_bar', (x + math.cos(a) * 0.058 * s, y + math.sin(a) * 0.058 * s, z), (0.01 * s, 0.01 * s, 0.15 * s), iron, bevel=0)
    cyl('hl_top', (x, y, z + 0.09 * s), 0.07 * s, 0.04 * s, iron, verts=12, r2=0.03 * s)
    candle((x, y, z - 0.065 * s), 0.06 * s, 0.012 * s, 6 * s)

QUAYS = [(-4.85, -2.0, 0.85, 4.15), (-1.15, 2.35, 1.6, 4.15), (2.85, 4.85, -0.3, 4.15), (-4.85, -2.55, -3.4, 0.25)]
def on_quay(p, pad=0.02):
    return any(x0 - pad <= p.x <= x1 + pad and y0 - pad <= p.y <= y1 + pad for (x0, x1, y0, y1) in QUAYS)

def rickety_bridge(a, b, w=0.55, sag=0.06, z0=0.37):
    """Footbridge resting on top of the quay coping at both ends, posts only in
    the water: uneven planks, a missing one, a rusty patch, a broken rail."""
    a, b = Vector(a), Vector(b); dvec = b - a; ang = math.atan2(dvec.y, dvec.x)
    a = a - dvec.normalized() * 0.12; b = b + dvec.normalized() * 0.12      # ends rest on the stone
    dvec = b - a; L = dvec.length
    nrm = Vector((-math.sin(ang), math.cos(ang), 0))
    n = int(L / 0.085)
    for k in range(n):
        t = (k + 0.5) / n
        if 0.2 < t < 0.8 and RG.random() < 0.1: continue
        c = a + dvec * t
        z = z0 - sag * 4 * t * (1 - t) + RG.uniform(-0.01, 0.01)
        box('plank', (c.x, c.y, z), (L / n - 0.014, w * RG.uniform(0.82, 1.05), 0.028), RG.choice([weathered, weathered2]), bevel=0.004,
            rot=(RG.uniform(-0.06, 0.06), RG.uniform(-0.04, 0.04), ang + RG.uniform(-0.08, 0.08)))
    for side in (-1, 1):  # stringers under the planks
        p0 = a + nrm * side * w * 0.35 + Vector((0, 0, z0 - 0.04)); p1 = b + nrm * side * w * 0.35 + Vector((0, 0, z0 - 0.04))
        mid = (p0 + p1) / 2 - Vector((0, 0, sag))
        limb(p0, mid, 0.018, weathered); limb(mid, p1, 0.018, weathered)
    pc = a + dvec * 0.45
    box('patch', (pc.x, pc.y, z0 - sag + 0.025), (0.2, w * 0.55, 0.008), rusty_sheet, bevel=0, rot=(0, 0.04, ang + 0.25))
    for sg in (-1, 1):
        rail_ts = [t for t in (0.22, 0.5, 0.78)]
        tops = []
        for t in rail_ts:
            c = a + dvec * t + nrm * sg * (w / 2 + 0.02)
            if on_quay(c): continue
            zt = z0 - sag * 4 * t * (1 - t)
            lean = Vector((RG.uniform(-0.07, 0.07), RG.uniform(-0.07, 0.07), 0))
            limb(Vector((c.x, c.y, -0.25)), Vector((c.x, c.y, zt - 0.03)), 0.03, weathered)            # pile in the water
            top = Vector((c.x, c.y, zt + RG.uniform(0.3, 0.42))) + lean
            limb(Vector((c.x, c.y, zt)), top, 0.016, weathered2); tops.append(top)
        for p, q in zip(tops, tops[1:]):
            if sg == 1 and RG.random() < 0.5:  # a broken rope rail hanging loose
                limb(p, p + (q - p) * 0.4 - Vector((0, 0, 0.18)), 0.006, rope_m)
            else:
                limb(p, q - Vector((0, 0, 0.03)), 0.006, rope_m)

def gable_end(x, y0, y1, z0, rise, mat, style='sun', side=1):
    """Fill the gable triangle; 'sun' = round window with a carved sunburst,
    'lunette' = half-moon window with leaded, etched glass."""
    cy_ = (y0 + y1) / 2
    me = bpy.data.meshes.new('gable'); bm_ = bmesh.new()
    vs = [bm_.verts.new(v) for v in ((x, y0, z0), (x, y1, z0), (x, cy_, z0 + rise))]
    bm_.faces.new(vs); bm_.to_mesh(me); bm_.free()
    o = link(bpy.data.objects.new('gable', me)); me.materials.append(mat)
    sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.12; sl.offset = -side
    gmat, gcol = pick_glow()
    stone_f = varied('oculus_stone', (0.55, 0.52, 0.47), 0.05, 0.8)
    if style == 'sun':
        r = rise * 0.2; c = Vector((x + side * 0.015, cy_, z0 + rise * 0.36))
        cyl('oculus_glass', c, r, 0.02, etched_glass('etch_sun', gcol, 'sun'), verts=40, rot=(0, math.pi / 2, 0))
        ring = cyl('oculus_frame', c + Vector((side * 0.01, 0, 0)), r + 0.05, 0.05, stone_f, verts=40, rot=(0, math.pi / 2, 0))
        cut(ring, cyl('oculus_hole', c, r, 0.2, None, verts=40, rot=(0, math.pi / 2, 0)))
        for k in range(12):  # sunburst spokes
            a = k / 12 * 2 * math.pi
            p = c + Vector((side * 0.02, math.cos(a) * r * 0.5, math.sin(a) * r * 0.5))
            b_ = box('spoke', p, (0.015, r, 0.012), solid('frame_arch', (0.16, 0.22, 0.18), 0.55), bevel=0); b_.rotation_euler = (a, 0, 0)
        cyl('hub', c + Vector((side * 0.025, 0, 0)), r * 0.22, 0.02, stone_f, verts=20, rot=(0, math.pi / 2, 0))
        for k in range(4):  # keystones
            a = k / 4 * 2 * math.pi
            box('oculus_key', c + Vector((side * 0.015, math.cos(a) * (r + 0.08), math.sin(a) * (r + 0.08))), (0.05, 0.08, 0.11), stone_f, bevel=0.006).rotation_euler = (a + math.pi / 2, 0, 0)
    else:
        r = rise * 0.3; c = Vector((x + side * 0.015, cy_, z0 + rise * 0.12))
        me2 = bpy.data.meshes.new('lunette'); bm2 = bmesh.new()
        ctr = bm2.verts.new(c); ring_v = [bm2.verts.new(c + Vector((0, math.cos(t) * r, math.sin(t) * r))) for t in [k / 24 * math.pi for k in range(25)]]
        for p, q in zip(ring_v, ring_v[1:]): bm2.faces.new((ctr, p, q))
        bm2.to_mesh(me2); bm2.free(); me2.materials.append(etched_glass('etch_leaf', gcol, 'leaded'))
        link(bpy.data.objects.new('lunette', me2))
        arc = [c + Vector((side * 0.02, math.cos(t) * (r + 0.03), math.sin(t) * (r + 0.03))) for t in [k / 16 * math.pi for k in range(17)]]
        for p, q in zip(arc, arc[1:]): limb(p, q, 0.03, stone_f)
        limb(c + Vector((side * 0.02, -r - 0.05, -0.02)), c + Vector((side * 0.02, r + 0.05, -0.02)), 0.025, stone_f)   # sill
        for k in range(1, 5):  # fan mullions
            t = k / 5 * math.pi
            limb(c + Vector((side * 0.025, 0, 0)), c + Vector((side * 0.025, math.cos(t) * r, math.sin(t) * r)), 0.008, solid('frame_casement', (0.25, 0.17, 0.12), 0.55))
    room_light(tuple(Vector((x - side * 0.4, cy_, z0 + rise * 0.3))), 10, gcol)

def etched_glass(name, col, pattern):
    """Glowing glass with an etched, colourless pattern: dark lines over the light."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    if pattern == 'sun':
        wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = 18; wv.inputs['Distortion'].default_value = 0
        l.new(tc.outputs['Object'], wv.inputs['Vector']); src = wv.outputs['Fac']
        lo, hi = 0.85, 0.95
    else:
        vo = n.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 9
        l.new(tc.outputs['Object'], vo.inputs['Vector']); src = vo.outputs['Distance']
        lo, hi = 0.0, 0.035
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = lo; mr.inputs['From Max'].default_value = hi
    l.new(src, mr.inputs['Value'])
    if pattern == 'sun':
        inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; l.new(mr.outputs['Result'], inv.inputs[1]); fac = inv.outputs['Value']
    else:
        fac = mr.outputs['Result']
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.06, 0.05, 0.045, 1); mx.inputs['B'].default_value = (*col, 1)
    l.new(fac, mx.inputs['Factor']); l.new(mx.outputs['Result'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 4.5; b.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1)
    return m


# ------------------------------------------------------------------ roof and gable details
def ring_of(c, r, z, rr, mat, n=28, name='hoop'):
    pts = [Vector((c[0] + math.cos(k / n * 2 * math.pi) * r, c[1] + math.sin(k / n * 2 * math.pi) * r, z)) for k in range(n + 1)]
    for p, q in zip(pts, pts[1:]): limb(p, q, rr, mat)

def water_tank(tx, ty, tz):
    """An old timber water tank on a little stand: staves of slightly different
    wood bound with rusty hoops, a stepped shingle lid with a hatch and a
    weathervane, a ladder up the side and a pipe down to the roof."""
    stand = timber
    for (dx, dy) in ((-0.22, -0.22), (0.22, -0.22), (0.22, 0.22), (-0.22, 0.22)):
        box('tank_leg', (tx + dx, ty + dy, tz + 0.13), (0.06, 0.06, 0.26), stand, bevel=0.005)
    for sg in (-1, 1):
        limb(Vector((tx - 0.22, ty + sg * 0.22, tz + 0.03)), Vector((tx + 0.22, ty + sg * 0.22, tz + 0.22)), 0.012, stand)
        limb(Vector((tx + sg * 0.22, ty - 0.22, tz + 0.22)), Vector((tx + sg * 0.22, ty + 0.22, tz + 0.03)), 0.012, stand)
    box('tank_deck', (tx, ty, tz + 0.28), (0.66, 0.66, 0.04), timber_h, bevel=0.006)
    R, z0, H = 0.3, tz + 0.3, 0.7
    cyl('tank_core', (tx, ty, z0 + H / 2), R - 0.012, H, solid('tank_dark', (0.09, 0.06, 0.04), 0.9), verts=24)
    staves = [varied('tank_stave%d' % i, c, 0.07, 0.75, bump=0.3) for i, c in enumerate(((0.36, 0.25, 0.16), (0.31, 0.21, 0.14), (0.4, 0.29, 0.19), (0.28, 0.2, 0.14)))]
    NS = 32
    for k in range(NS):
        a = k / NS * 2 * math.pi
        box('tank_stave', (tx + math.cos(a) * R, ty + math.sin(a) * R, z0 + H / 2 + RG.uniform(-0.008, 0.008)),
            (0.024, 2 * math.pi * R / NS * 0.93, H + RG.uniform(-0.01, 0.01)), staves[RG.randrange(4)], bevel=0.003, rot=(0, 0, a))
    rust = varied('hoop_rust', (0.3, 0.15, 0.08), 0.15, 0.6)
    for hz in (0.1, 0.38, 0.64, 0.92):
        ring_of((tx, ty), R + 0.014, z0 + hz * H, 0.009, rust)
    # a plain conical roof, like the old rooftop tanks: a thin overhanging
    # eave, straight planked sides with battens down the seams, a zinc cap
    shingle = varied('tank_shingle', (0.26, 0.19, 0.14), 0.1, 0.85, bump=0.4, bump_scale=60)
    zt = z0 + H
    RL, HL = R + 0.05, 0.26
    cyl('tank_eave', (tx, ty, zt + 0.012), RL + 0.01, 0.024, timber_h, verts=32)
    cone = cyl('tank_lid', (tx, ty, zt + 0.024 + HL / 2), RL, HL, shingle, verts=16, r2=0.015)
    cone.data.polygons.foreach_set('use_smooth', [False] * len(cone.data.polygons))
    for k in range(16):
        a = (k + 0.5) / 16 * 2 * math.pi
        a0 = Vector((tx + math.cos(a) * RL * 0.985, ty + math.sin(a) * RL * 0.985, zt + 0.03))
        a1 = Vector((tx + math.cos(a) * 0.03, ty + math.sin(a) * 0.03, zt + 0.024 + HL - 0.02))
        limb(a0, a1, 0.006, timber_h)
    cyl('tank_cap', (tx, ty, zt + HL + 0.01), 0.04, 0.04, solid('ch_zinc', (0.32, 0.33, 0.34), 0.45, metal=0.8), verts=12, r2=0.015)
    box('tank_hatch', (tx + 0.13, ty - 0.13, zt + 0.1), (0.1, 0.09, 0.025), timber_h, bevel=0.004, rot=(0.5, -0.5, -0.785))
    # weathervane
    vp = Vector((tx, ty, zt + HL + 0.02))
    limb(vp, vp + Vector((0, 0, 0.2)), 0.006, iron)
    sphere('vane_ball', vp + Vector((0, 0, 0.05)), 0.014, solid('brass_v', (0.7, 0.5, 0.25), 0.35, metal=1.0), 8)
    box('vane_arrow', vp + Vector((0.02, 0, 0.17)), (0.16, 0.006, 0.012), iron, bevel=0, rot=(0, 0, 0.5))
    box('vane_tail', vp + Vector((-0.04, -0.03, 0.17)), (0.04, 0.004, 0.05), iron, bevel=0, rot=(0, 0, 0.5))
    # ladder up the side that faces the street
    la = -0.75; d = Vector((math.cos(la), math.sin(la), 0)); tng = Vector((-d.y, d.x, 0))
    base = Vector((tx, ty, tz + 0.3)) + d * (R + 0.05)
    for sg in (-1, 1):
        limb(base + tng * 0.07 * sg, base + tng * 0.07 * sg + Vector((0, 0, H + 0.12)), 0.009, iron)
    for k in range(8):
        limb(base - tng * 0.07 + Vector((0, 0, 0.08 + k * 0.095)), base + tng * 0.07 + Vector((0, 0, 0.08 + k * 0.095)), 0.006, iron)
    # outlet pipe down through the stand and off across the roof
    pa = 2.3; pd = Vector((math.cos(pa), math.sin(pa), 0))
    p0 = Vector((tx, ty, z0 + 0.06)) + pd * (R + 0.02)
    p1 = Vector((p0.x, p0.y, tz + 0.03)); p2 = p1 + pd * 0.5
    for a_, b_ in ((p0, p1), (p1, p2)):
        limb(a_, b_, 0.018, iron)
    cyl('pipe_flange', tuple(p0), 0.03, 0.02, iron, verts=12)
    cyl('tank_valve', tuple(p1 + Vector((0, 0, 0.1))), 0.025, 0.03, solid('valve_red', (0.5, 0.1, 0.08), 0.5, metal=0.4), verts=10)

def louvre(c, w, h):
    """A small louvred attic vent on a gable facing +x."""
    dark = solid('vent_dark', (0.04, 0.03, 0.03), 0.9)
    box('vent_back', c + Vector((-0.005, 0, 0)), (0.01, w, h), dark, bevel=0)
    fr = solid('vent_frame', (0.22, 0.16, 0.12), 0.7)
    for dz in (-h / 2, h / 2):
        box('vent_frame', c + Vector((0.012, 0, dz)), (0.03, w + 0.03, 0.025), fr, bevel=0.003)
    for dy in (-w / 2, w / 2):
        box('vent_frame', c + Vector((0.012, dy, 0)), (0.03, 0.025, h), fr, bevel=0.003)
    n = max(3, int(h / 0.035))
    for k in range(n):
        z = -h / 2 + (k + 0.6) * h / (n + 0.2)
        box('vent_slat', c + Vector((0.012, 0, z)), (0.035, w, 0.01), fr, bevel=0, rot=(0, -0.6, 0))

def timbered_gable(x, y0, y1, ztop, z0, rise, mat):
    """Close the blue house's gable and make something of it: old timber framing
    over the plaster, two louvred vents, a hoist beam with a pulley and rope
    (as canal houses have, for getting furniture in), carved bargeboards with
    little drops, a pendant at the apex, and a pigeon on the beam."""
    yc = (y0 + y1) / 2; hw = (y1 - y0) / 2
    me = bpy.data.meshes.new('gableC'); bm_ = bmesh.new()
    vs = [bm_.verts.new(v) for v in ((x, y0, z0), (x, y1, z0), (x, yc, z0 + rise))]
    bm_.faces.new(vs); bm_.to_mesh(me); bm_.free()
    o = link(bpy.data.objects.new('gableC', me)); me.materials.append(mat)
    sl = o.modifiers.new('sol', 'SOLIDIFY'); sl.thickness = 0.1; sl.offset = -1
    box('gableC_band', (x - 0.05, yc, (ztop + z0) / 2), (0.1, y1 - y0, z0 - ztop + 0.01), mat, bevel=0)
    oak = varied('gable_oak', (0.2, 0.14, 0.1), 0.1, 0.8, bump=0.3)
    X = x + 0.018
    zr = lambda y: z0 + rise * (1 - abs(y - yc) / hw)      # roof line above y
    box('gable_tie', (X, yc, z0 + 0.04), (0.04, y1 - y0, 0.08), oak, bevel=0.006)
    for sg in (-1, 1):
        limb(Vector((X, yc + sg * (hw - 0.06), z0 + 0.06)), Vector((X, yc, z0 + rise - 0.05)), 0.03, oak)      # rafters' faces
        qy = yc + sg * 0.95
        limb(Vector((X, qy, z0 + 0.06)), Vector((X, qy, zr(qy) - 0.05)), 0.026, oak)                          # queen posts
        oy = yc + sg * 1.4
        limb(Vector((X, qy, z0 + 0.08)), Vector((X, oy, zr(oy) - 0.04)), 0.022, oak)                           # brace in the outer panel
        louvre(Vector((x + 0.005, yc + sg * 0.48, z0 + 0.3)), 0.24, 0.2)
    limb(Vector((X, yc, z0 + 0.06)), Vector((X, yc, z0 + 0.62)), 0.03, oak)                                     # king post
    # hoist beam and pulley
    hz = z0 + 0.72
    box('hoist_beam', (x + 0.26, yc, hz), (0.6, 0.085, 0.1), oak, bevel=0.01)
    box('hoist_cap', (x + 0.565, yc, hz), (0.02, 0.1, 0.12), oak, bevel=0.004)
    pz = hz - 0.13; px = x + 0.48
    limb(Vector((px, yc, hz - 0.05)), Vector((px, yc, pz + 0.04)), 0.006, iron)
    cyl('hoist_pulley', (px, yc, pz), 0.04, 0.02, solid('pulley_wood', (0.35, 0.24, 0.15), 0.6), verts=20, rot=(math.pi / 2, 0, 0))
    cyl('hoist_axle', (px, yc, pz), 0.012, 0.05, iron, verts=8, rot=(math.pi / 2, 0, 0))
    rope = solid('hoist_rope', (0.55, 0.46, 0.34), 0.9)
    limb(Vector((px - 0.04, yc, pz)), Vector((px - 0.045, yc, z0 - 0.15)), 0.006, rope)
    limb(Vector((px + 0.04, yc, pz)), Vector((px + 0.045, yc, z0 - 0.42)), 0.006, rope)
    hk = Vector((px + 0.045, yc, z0 - 0.42))
    for k in range(5):     # an iron hook at the end
        t0, t1 = k / 5 * math.pi, (k + 1) / 5 * math.pi
        limb(hk + Vector((0.02 * (1 - math.cos(t0)), 0, -0.02 - 0.025 * math.sin(t0))), hk + Vector((0.02 * (1 - math.cos(t1)), 0, -0.02 - 0.025 * math.sin(t1))), 0.005, iron)
    limb(hk, hk + Vector((0, 0, -0.02)), 0.005, iron)
    pigeon(x + 0.36, yc, hz + 0.05, math.pi * 0.85)
    # carved bargeboards under both rakes, with drops; a pendant at the apex
    bx = x + 0.15 - 0.012
    L = math.hypot(hw + 0.15, rise); th = math.atan2(rise, hw + 0.15)
    for sg in (-1, 1):
        mid = Vector((bx, yc + sg * (hw + 0.15) / 2, z0 + rise / 2 - 0.055))
        box('bargeboard', mid, (0.025, L, 0.07), oak, bevel=0.005, rot=(-sg * th, 0, 0))
        for k in range(1, 11):
            t = k / 11
            yy = yc + sg * (hw + 0.15) * t
            zz = z0 + rise * (1 - t) - 0.1
            sphere('barge_drop', (bx, yy, zz), 0.016, oak, 8, (1, 1, 1.5))
    limb(Vector((bx, yc, z0 + rise - 0.02)), Vector((bx, yc, z0 + rise - 0.2)), 0.02, oak)
    sphere('apex_drop', (bx, yc, z0 + rise - 0.22), 0.03, oak, 10, (1, 1, 1.4))

def pulley_basket(a, b, t=0.4):
    """A rope pulley strung between two neighbours' windows, with a wicker
    basket clipped on: the bakery sends the bread across."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized(); side = Vector((-d.y, d.x, 0)).normalized()
    rope = solid('pulley_rope', (0.6, 0.52, 0.4), 0.9)
    wood = solid('pulley_wood', (0.35, 0.24, 0.15), 0.6)
    wa, wb = a + d * 0.08, b - d * 0.08
    for wall, wc in ((a, wa), (b, wb)):
        limb(wall - d * 0.02, wc, 0.01, iron)                           # bracket
        c = cyl('pulley_wheel', tuple(wc), 0.045, 0.018, wood, verts=20)
        c.rotation_euler = side.to_track_quat('Z', 'Y').to_euler()
    def run(dz, sag):
        pts = [wa.lerp(wb, s) + Vector((0, 0, dz - sag * 4 * s * (1 - s))) for s in [k / 12 for k in range(13)]]
        for p, q in zip(pts, pts[1:]): limb(p, q, 0.005, rope)
        return pts
    top = run(0.045, 0.06); run(-0.045, 0.1)
    hp = wa.lerp(wb, t) + Vector((0, 0, 0.045 - 0.06 * 4 * t * (1 - t)))
    limb(hp, hp + Vector((0, 0, -0.07)), 0.004, iron)
    bc = hp + Vector((0, 0, -0.15))
    wick = varied('wicker', (0.58, 0.42, 0.22), 0.1, 0.9, bump=0.6, bump_scale=120.0)
    cyl('basket', tuple(bc), 0.065, 0.1, wick, verts=20, r2=0.08)
    ring_of((bc.x, bc.y), 0.082, bc.z + 0.05, 0.007, wick, n=20, name='basket_rim')
    arc = [bc + side * (0.08 * math.cos(s)) + Vector((0, 0, 0.05 + 0.08 * math.sin(s))) for s in [k / 10 * math.pi for k in range(11)]]
    for p, q in zip(arc, arc[1:]): limb(p, q, 0.005, wick)
    sphere('basket_cloth', tuple(bc + Vector((0, 0, 0.045))), 0.07, solid('cloth_check', (0.72, 0.22, 0.2), 0.85), 12, (1, 1, 0.3))
    for (o, tilt) in ((-0.025, 0.5), (0.02, 0.3)):
        s_ = sphere('baguette', tuple(bc + d * o + Vector((0, 0, 0.09))), 0.018, solid('bread', (0.7, 0.45, 0.22), 0.7), 10, (1, 1, 5.5))
        s_.rotation_euler = (tilt, 0.25, math.atan2(d.y, d.x))
    sphere('pulley_bell', tuple(wa + Vector((0, 0, -0.08))), 0.02, solid('brass_b', (0.75, 0.55, 0.25), 0.3, metal=1.0), 10, (1, 1, 1.2))
    limb(wa + Vector((0, 0, -0.02)), wa + Vector((0, 0, -0.065)), 0.003, iron)

def wall_shrine(W, u, z):
    """A little street shrine set into the wall: an arched niche painted sky
    blue with gold stars, a small pale figure, votive candles burning in red
    glass, a jam jar of flowers, a tin canopy and a stone shelf on brackets."""
    stone = varied('shrine_stone', (0.74, 0.7, 0.62), 0.06, 0.85, bump=0.6, bump_scale=60)
    sky = varied('shrine_sky', (0.16, 0.3, 0.55), 0.06, 0.9)
    gold = solid('shrine_gold', (0.85, 0.65, 0.25), 0.35, metal=0.9)
    rot_w = (math.pi / 2, 0, 0) if W.axis == 'y' else (0, math.pi / 2, 0)
    w, h, d = 0.26, 0.34, 0.09
    cut(W.obj, box('shrine_cut', W.P(u, 0, z + h / 2), W.S(w, d * 2, h), None, bevel=0))
    cut(W.obj, cyl('shrine_cut', W.P(u, 0, z + h), w / 2, d * 2, None, verts=24, rot=rot_w))
    box('shrine_back', W.P(u, -d, z + h / 2), W.S(w, 0.01, h), sky, bevel=0)
    cyl('shrine_back', W.P(u, -d, z + h), w / 2, 0.01, sky, verts=24, rot=rot_w)
    for k in range(7):
        a = 0.4 + k * 0.33
        sphere('shrine_star', W.P(u + 0.09 * math.cos(a) * (1 if k % 2 else 0.6), -d + 0.008, z + h + 0.07 * math.sin(a) - 0.02 * (k % 3)), 0.006, gold, 6)
    # stone surround: jambs, an arched head of little blocks, a keystone
    for sg in (-1, 1):
        box('shrine_jamb', W.P(u + sg * (w / 2 + 0.025), 0.015, z + h / 2), W.S(0.05, 0.04, h), stone, bevel=0.006)
    for k in range(9):
        a = math.pi * k / 8
        box('shrine_arch', W.P(u + (w / 2 + 0.025) * math.cos(a), 0.015, z + h + (w / 2 + 0.025) * math.sin(a)), W.S(0.045, 0.04, 0.035), stone, bevel=0.005)
    box('shrine_key', W.P(u, 0.02, z + h + w / 2 + 0.03), W.S(0.04, 0.05, 0.06), stone, bevel=0.006)
    # the shelf, on two brackets
    box('shrine_shelf', W.P(u, 0.03, z - 0.015), W.S(w + 0.14, 0.13, 0.03), stone, bevel=0.006)
    for sg in (-1, 1):
        box('shrine_bracket', W.P(u + sg * 0.09, 0.03, z - 0.06), W.S(0.03, 0.09, 0.07), stone, bevel=0.008)
    # the figure: robe, a veiled head, a faint halo
    fig = varied('shrine_figure', (0.86, 0.84, 0.8), 0.03, 0.7)
    cyl('shrine_robe', W.P(u, -d + 0.04, z + 0.1), 0.045, 0.2, fig, verts=16, r2=0.025)
    sphere('shrine_head', W.P(u, -d + 0.04, z + 0.225), 0.022, fig, 12)
    sphere('shrine_veil', W.P(u, -d + 0.035, z + 0.23), 0.026, varied('shrine_veil', (0.5, 0.6, 0.78), 0.04, 0.8), 12, (1, 1, 1.15))
    cyl('shrine_halo', W.P(u, -d + 0.018, z + 0.24), 0.035, 0.004, gold, verts=20, rot=rot_w)
    # votives in red glass on the shelf, and a jar of flowers
    for du_ in (-0.1, -0.06, 0.07):
        p = W.P(u + du_, 0.04, z)
        cyl('votive', p + Vector((0, 0, 0.025)), 0.014, 0.05, solid('votive_glass', (0.7, 0.08, 0.06), 0.1, emit=(1.0, 0.25, 0.1), strength=3.0), verts=12)
        sphere('flame', p + Vector((0, 0, 0.06)), 0.006, solid('flame', (1, 0.8, 0.4), 0.3, emit=(1.0, 0.68, 0.28), strength=60), 8, (1, 1, 2.0))
    L = bpy.data.lights.new('candle', 'POINT'); L.energy = 2.5; L.color = (1.0, 0.55, 0.3); L.shadow_soft_size = 0.02
    link(bpy.data.objects.new('candle', L)).location = W.P(u - 0.06, 0.08, z + 0.08)
    jp = W.P(u + 0.11, 0.04, z)
    cyl('shrine_jar', jp + Vector((0, 0, 0.03)), 0.018, 0.06, solid('jar_glass', (0.7, 0.8, 0.75), 0.05), verts=12)
    for k in range(5):
        a = k * 1.3
        tip = jp + Vector((0.025 * math.cos(a), 0.02 * math.sin(a), 0.1 + 0.02 * (k % 2)))
        limb(jp + Vector((0, 0, 0.05)), tip, 0.0025, solid('stem', (0.15, 0.25, 0.1), 0.6))
        sphere('shrine_bloom', tip, 0.012, solid('shrine_bloom%d' % (k % 2), ((0.95, 0.85, 0.3), (0.9, 0.95, 0.92))[k % 2], 0.6), 8)
    # a small tin canopy over it
    cv_ = box('shrine_canopy', W.P(u, 0.09, z + h + w / 2 + 0.1), W.S(w + 0.16, 0.2, 0.015), solid('ch_zinc', (0.32, 0.33, 0.34), 0.45, metal=0.8), bevel=0.003)
    cv_.rotation_euler = (0.35, 0, 0) if W.axis == 'y' else (0, -0.35, 0)


# ------------------------------------------------------------------ stage
GROUPS_EXTRA = {}
endless_water()
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
gable_end(-2.3, 1.25, 3.95, topA + 0.1, 1.2, oldbrick, 'sun')
gable_roof('roofD', -3.72, -1.47, 1.75, 2.85, topD + 0.1, 0.75, tile_mat('rt_old', (0.42, 0.22, 0.15)), over=0.15)
gable_end(-2.85, -2.9, -0.05, topD + 0.1, 0.75, oldbrick2, 'lunette')
# C's roof: ridge along y — build as gable on a rotated footprint by swapping: use a mansard-ish hip of boxes
gable_roof('roofC', 3.875, 2.05, 1.55, 3.7, topC + 0.1, 0.9, slate, over=0.15)
_b = set(bpy.data.objects.keys()); timbered_gable(4.65, 0.2, 3.9, topC, topC + 0.1, 0.9, plaster_o); GROUPS_EXTRA['gableC'] = set(bpy.data.objects.keys()) - _b
def chimney(style, x, y, z, h, wall):
    """Six kinds of chimney, so the roofline isn't one stack repeated. Each
    is built of its own house's wall (same colour, same brick or plaster), so
    it reads as part of the building. Returns where the smoke leaves it."""
    potm = varied('pot_c', (0.45, 0.25, 0.16), 0.1, 0.8)
    potm2 = varied('pot_c2', (0.55, 0.36, 0.24), 0.1, 0.8)
    stone = varied('ch_stone', (0.55, 0.52, 0.47), 0.08, 0.9, bump=0.6, bump_scale=40)
    render_ = varied('ch_render', (0.72, 0.66, 0.56), 0.08, 0.9, bump=0.5, bump_scale=60)
    zinc = solid('ch_zinc', (0.32, 0.33, 0.34), 0.45, metal=0.8)
    rust_ = varied('ch_rust', (0.36, 0.18, 0.09), 0.15, 0.85)
    top = z + h
    if style == 'corbel':          # tall brick stack, stepped brick cap, three mismatched pots
        box('chimney', (x, y, z + h / 2), (0.3, 0.3, h), wall, bevel=0.01)
        box('ch_band', (x, y, top - 0.12), (0.36, 0.36, 0.05), wall, bevel=0.005)
        box('ch_band', (x, y, top - 0.04), (0.4, 0.4, 0.06), wall, bevel=0.005)
        for k, (dx, ph, pr, m) in enumerate(((-0.1, 0.2, 0.04, potm), (0.0, 0.28, 0.035, potm2), (0.1, 0.14, 0.045, potm))):
            cyl('ch_pot', (x + dx, y, top + ph / 2), pr, ph, m, verts=12, r2=pr * 0.8)
            cyl('ch_pot_rim', (x + dx, y, top + ph), pr * 1.15, 0.025, m, verts=12)
        return Vector((x, y, top + 0.3))
    if style == 'hood':            # stone stack with a slab hood on four little piers
        box('chimney', (x, y, z + h / 2), (0.3, 0.26, h), wall, bevel=0.012)
        box('ch_band', (x, y, top - 0.03), (0.34, 0.3, 0.05), wall, bevel=0.005)
        for dx in (-0.11, 0.11):
            for dy in (-0.09, 0.09):
                box('ch_pier', (x + dx, y + dy, top + 0.07), (0.05, 0.05, 0.14), wall, bevel=0.004)
        box('ch_slab', (x, y, top + 0.16), (0.38, 0.34, 0.04), stone, bevel=0.008)
        return Vector((x, y, top + 0.12))
    if style == 'flue':            # tin stovepipe through a flashing collar, a conical rain cap, guy wires
        box('ch_stack', (x, y, z + 0.14), (0.24, 0.24, 0.28), wall, bevel=0.01)
        box('ch_band', (x, y, z + 0.29), (0.28, 0.28, 0.04), wall, bevel=0.005)
        cyl('ch_collar', (x, y, z + 0.33), 0.08, 0.05, zinc, verts=16, r2=0.06)
        cyl('chimney', (x, y, z + h / 2), 0.055, h, zinc, verts=16)
        for f in (0.3, 0.62): cyl('ch_joint', (x, y, z + h * f), 0.06, 0.02, rust_, verts=16)
        cyl('ch_cap', (x, y, top + 0.1), 0.13, 0.07, zinc, verts=16, r2=0.01)
        for a in (0.0, 2.1, 4.2):
            limb(Vector((x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), top - 0.1)),
                 Vector((x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), z + 0.01)), 0.0025, iron)
        return Vector((x, y, top + 0.06))
    if style == 'cowl':            # short brick stack with a turning metal cowl
        box('chimney', (x, y, z + h / 2), (0.26, 0.26, h), wall, bevel=0.01)
        box('ch_band', (x, y, top - 0.03), (0.31, 0.31, 0.05), wall, bevel=0.005)
        cyl('ch_pot', (x, y, top + 0.08), 0.05, 0.16, potm2, verts=12)
        sphere('ch_cowl', (x, y, top + 0.2), 0.08, zinc, 16, (1, 1, 0.8))
        c = cyl('ch_cowl_mouth', (x - 0.06, y - 0.06, top + 0.2), 0.05, 0.08, zinc, verts=12)
        c.rotation_euler = (math.pi / 2, 0, math.radians(-45))
        cyl('ch_vane', (x, y, top + 0.31), 0.004, 0.08, iron, verts=6)
        return Vector((x - 0.08, y - 0.08, top + 0.2))
    if style == 'rendered':        # plastered chimney, a brick string course, two pots, a pigeon
        box('chimney', (x, y, z + h / 2), (0.3, 0.3, h), wall, bevel=0.012)
        box('ch_band', (x, y, top - 0.2), (0.32, 0.32, 0.06), wall, bevel=0.004)
        box('ch_cap', (x, y, top - 0.02), (0.36, 0.36, 0.04), stone, bevel=0.006)
        for k in range(2):
            cyl('ch_pot', (x - 0.07 + k * 0.14, y, top + 0.09), 0.045, 0.18, potm, verts=12, r2=0.035)
        sphere('pigeon', (x + 0.13, y - 0.1, top + 0.05), 0.035, solid('pigeon_g', (0.45, 0.46, 0.5), 0.7), 10, (1.3, 0.9, 0.9))
        sphere('pigeon', (x + 0.17, y - 0.12, top + 0.09), 0.02, solid('pigeon_g', (0.45, 0.46, 0.5), 0.7), 8)
        return Vector((x - 0.07, y, top + 0.2))
    # 'oven': the bakery's broad chimney, a little pitched roof over arched vents
    box('chimney', (x, y, z + h / 2), (0.42, 0.3, h), wall, bevel=0.01)
    box('ch_band', (x, y, top - 0.02), (0.46, 0.34, 0.04), wall, bevel=0.004)
    for dx in (-0.17, 0.17):
        box('ch_pier', (x + dx, y, top + 0.1), (0.07, 0.3, 0.2), wall, bevel=0.005)
    box('ch_pier', (x, y, top + 0.1), (0.06, 0.3, 0.2), wall, bevel=0.005)
    for sg in (-1, 1):
        r_ = box('ch_roof', (x, y + sg * 0.09, top + 0.25), (0.5, 0.21, 0.025), tile_mat('rt_old', (0.42, 0.22, 0.15)), bevel=0.004)
        r_.rotation_euler = (sg * 0.5, 0, 0)
    return Vector((x, y, top + 0.18))


for style, (x, y, z, h), wall in zip(('corbel', 'hood', 'flue', 'cowl', 'rendered', 'oven'),
                               ((-4.1, 3.4, topA + 0.6, 1.2), (-2.9, 1.8, topA + 0.5, 1.0), (-0.4, 3.6, topB + 0.1, 0.8), (1.5, 3.7, topB + 0.1, 0.7),
                                (4.3, 3.2, topC + 0.4, 0.9), (-4.2, -0.6, topD + 0.3, 0.8)),
                               (oldbrick, oldbrick, plaster_g, plaster_g, plaster_o, oldbrick2)):
    sp = chimney(style, x, y, z, h, wall)
    sm = solid('smoke_c', (0.22, 0.22, 0.24), 0.9); sm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.4
    for k in range(4):
        sphere('smoke', (sp.x + k * 0.1, sp.y + k * 0.04, sp.z + 0.27 + k * 0.22), 0.09 + k * 0.045, sm, 12)
# B roof clutter
box('B_roofwall', (0.6, 3.15, topB + 0.2), (3.1, 1.8, 0.3), plaster_g, bevel=0.01)
_b = set(bpy.data.objects.keys()); water_tank(1.6, 2.9, topB + 0.35); GROUPS_EXTRA['tank'] = set(bpy.data.objects.keys()) - _b
for k in range(3):
    pot((-0.6 + k * 0.35, 2.45, topB + 0.35), 0.1, 0.18, None)
    sphere('roof_plant', (-0.6 + k * 0.35, 2.45, topB + 0.6), 0.1, solid('rleaf', (0.16, 0.3, 0.1), 0.7), 10)
for x in (-0.85, 0.55):
    box('roof_post', (x, 2.42, topB + 0.75), (0.05, 0.05, 0.8), timber, bevel=0.004)
hanging_lanterns((-0.85, 2.42, topB + 1.13), (0.55, 2.42, topB + 1.13), 3, 0.1)
# a small roof garden: planter boxes of flowers, a bench, a watering can
rg_z = topB + 0.35
for (cx, cy, w_, d_) in ((0.45, 3.72, 0.9, 0.3), (-0.62, 3.0, 0.3, 0.6)):
    box('roof_planter', (cx, cy, rg_z + 0.1), (w_, d_, 0.2), timber_h, bevel=0.01)
    box('roof_soil', (cx, cy, rg_z + 0.2), (w_ - 0.05, d_ - 0.05, 0.01), solid('soil', (0.13, 0.09, 0.06), 0.95), bevel=0)
    for _ in range(int(w_ * d_ * 120)):
        px, py = cx + RG.uniform(-w_ / 2 + 0.04, w_ / 2 - 0.04), cy + RG.uniform(-d_ / 2 + 0.04, d_ / 2 - 0.04)
        h_ = RG.uniform(0.08, 0.22)
        limb(Vector((px, py, rg_z + 0.2)), Vector((px, py, rg_z + 0.2 + h_)), 0.004, solid('stem', (0.15, 0.25, 0.1), 0.6))
        fc = RG.choice(FLOWERS)
        sphere('roof_bloom', (px, py, rg_z + 0.2 + h_), RG.uniform(0.018, 0.03), solid('fl%.2f%.2f' % fc[:2], fc, 0.6), 8)
    for _ in range(int(w_ * d_ * 40)):
        sphere('roof_leaf', (cx + RG.uniform(-w_ / 2 + 0.05, w_ / 2 - 0.05), cy + RG.uniform(-d_ / 2 + 0.05, d_ / 2 - 0.05), rg_z + 0.24), 0.035,
               solid('rleaf', (0.16, 0.3, 0.1), 0.7), 8, (1, 1, 0.7))
box('roof_bench', (0.35, 3.2, rg_z + 0.15), (0.6, 0.2, 0.04), timber_h, bevel=0.006)
for dx in (0.1, 0.6):
    box('roof_bench_leg', (dx, 3.2, rg_z + 0.07), (0.04, 0.18, 0.14), timber, bevel=0)
cyl('watering_can', (0.95, 3.05, rg_z + 0.06), 0.05, 0.12, solid('can', (0.35, 0.45, 0.4), 0.4, metal=0.6), verts=14)
limb(Vector((1.0, 3.05, rg_z + 0.06)), Vector((1.11, 3.05, rg_z + 0.14)), 0.008, solid('can', (0.35, 0.45, 0.4), 0.4, metal=0.6))
# shopfronts: B (neon), D (bakery glow with awning), C hanging sign
cut(B, box('shopc', (-0.56, 2.25, 0.85), (0.75, 0.6, 1.0), None, bevel=0))
box('shop_glass', (-0.56, 2.33, 0.85), (0.75, 0.01, 1.0), glow, bevel=0)
for k in range(5):
    cyl('shop_jar', (-0.85 + k * 0.14, 2.3, 0.45), 0.035, 0.1, solid('jar%d' % (k % 3), [(0.8, 0.5, 0.3), (0.5, 0.6, 0.4), (0.8, 0.75, 0.5)][k % 3], 0.3), verts=10)
neon_sign(BF, -0.56, 1.5, 0.6, (1.0, 0.35, 0.45))
_aw_green, _aw_cream = (0.2, 0.33, 0.27), (0.9, 0.84, 0.7)
_aw_img = EX._img('awning_stripes', 64, 32, lambda x, y: _aw_green if (x // 8) % 2 == 0 else _aw_cream)
_aw_m, _n, _l, _bsdf = node_mat('awning_cloth')
_t = _n.new('ShaderNodeTexImage'); _t.image = _aw_img; _t.interpolation = 'Closest'
_l.new(_t.outputs['Color'], _bsdf.inputs['Base Color']); _bsdf.inputs['Roughness'].default_value = 0.85; _bsdf.inputs['Sheen Weight'].default_value = 0.3
_ac = Vector((-3.72 + 0.43, -3.15, 1.45)); _ar = Matrix.Rotation(0.4, 3, 'X')
_aw = [(_ac + _ar @ Vector((sx * 0.45, sy * 0.25, 0))) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
EX._quad('awning_d', _aw, [(0, 0), (1, 0), (1, 1), (0, 1)], _aw_m)
_front = (_aw[0] + _aw[1]) / 2
_val_m = solid('awning_valance', _aw_green, 0.8)
box('awning_valance', _front + Vector((0, -0.003, -0.05)), (0.9, 0.008, 0.1), _val_m, bevel=0)
for k in range(9):     # scallops along the bottom, alternating colours
    c = cyl('awning_scallop', _front + Vector((-0.4 + k * 0.1, -0.004, -0.1)), 0.05, 0.008, solid('awning_cream', _aw_cream, 0.8) if k % 2 else _val_m, verts=20, rot=(math.pi / 2, 0, 0))
    cut(c, box('scallop_cut', _front + Vector((-0.4 + k * 0.1, -0.004, -0.05)), (0.12, 0.05, 0.1), None, bevel=0))
cu = bpy.data.curves.new('awning_word', 'FONT'); cu.body = 'boulangerie'
if MARKER: cu.font = bpy.data.fonts.load(MARKER, check_existing=True)
cu.size = 0.062; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.001
_w = link(bpy.data.objects.new('awning_word', cu)); _w.location = _front + Vector((0.03, -0.009, -0.048)); _w.rotation_euler = (math.pi / 2, 0, 0)
cu.materials.append(solid('awning_paint', (0.94, 0.86, 0.66), 0.6))
for sg in (-1, 1):     # a painted wheat sprig either side of the word
    base_ = _front + Vector((sg * 0.37 + 0.03 * sg, -0.009, -0.075))
    limb(base_, base_ + Vector((-sg * 0.02, 0, 0.055)), 0.0025, solid('awning_paint', (0.94, 0.86, 0.66), 0.6))
    for j in range(4):
        q = base_ + Vector((-sg * 0.005 * j, 0, 0.018 + j * 0.011))
        for side in (-1, 1):
            sphere('wheat_grain', q + Vector((side * 0.006, 0, 0)), 0.0055, solid('awning_paint', (0.94, 0.86, 0.66), 0.6), 6, (0.6, 0.3, 1.2)).rotation_euler = (0, side * 0.5, 0)
cut(D, box('shopd', (-4.16, -2.9, 0.85), (0.7, 0.6, 1.0), None, bevel=0))
box('shopd_glass', (-4.16, -2.82, 0.85), (0.7, 0.01, 1.0), glow, bevel=0)
for k in range(4):
    sphere('bread', (-4.4 + k * 0.16, -2.86, 0.5), 0.05, solid('bread', (0.7, 0.45, 0.22), 0.7), 10, (1.4, 0.8, 0.7))
hanging_sign(CS, 1.2, 1.55, (0.25, 0.3, 0.4))
hanging_sign(DS, -1.0, 1.5, (0.5, 0.25, 0.15))
# bridges: curved stone ones and covered skybridges
rickety_bridge((-2.0, 1.25, 0), (-1.15, 2.0, 0))
rickety_bridge((2.35, 2.2, 0), (2.85, 2.2, 0), w=0.5)
rickety_bridge((-3.7, 0.25, 0), (-3.7, 0.85, 0), w=0.5)
makeshift_corridor((-2.3, 2.75), (-0.95, 2.8), 2.6)
makeshift_corridor((2.15, 3.1), (3.1, 3.1), 2.5, w=0.5)
_b = set(bpy.data.objects.keys()); makeshift_corridor((-3.84, -0.05), (-3.84, 1.25), 1.64, w=0.32, h=0.5); GROUPS_EXTRA['corridor'] = set(bpy.data.objects.keys()) - _b
_b = set(bpy.data.objects.keys()); wall_shrine(AF, -3.38, 1.72); GROUPS_EXTRA['shrine'] = set(bpy.data.objects.keys()) - _b
import design_props as DP
_b = set(bpy.data.objects.keys()); DP.place_all(sc); GROUPS_EXTRA['design'] = set(bpy.data.objects.keys()) - _b
import zoom_props as ZP
_b = set(bpy.data.objects.keys()); ZP.place_all(sc, ZP.STREET_DIR); GROUPS_EXTRA['zoomprops'] = set(bpy.data.objects.keys()) - _b
# lamps of every kind
for (x, y) in ((-2.25, 1.0), (-0.95, 1.8), (2.6, 1.85), (3.05, -0.15), (-2.7, -3.25)):
    gas_lamp(x, y, 0.28)
for (W, u, z) in ((AF, -3.05, 2.65), (CS, 0.9, 1.4), (CS, 2.6, 2.5), (DF, -3.3, 1.35), (DS, -2.3, 2.4), (BF, 1.3, 1.45)):
    wall_lantern(W, u, z)
for p in ((-2.25, 1.55, 0.28), (2.95, 2.45, 0.28), (-3.35, 0.95, 0.28)):
    globe_post(p[0], p[1], p[2])
hanging_lanterns((-2.3, 1.3, 3.3), (3.1, 0.25, 3.0), 6, 0.6)
hanging_lanterns((-2.85, -0.5, 2.2), (-2.3, 1.3, 2.6), 3, 0.2)
laundry((-2.3, 1.4, 3.75), (-0.95, 2.3, 3.5))
laundry((2.15, 2.4, 3.45), (3.1, 2.2, 3.3))
_b = set(bpy.data.objects.keys()); pulley_basket((-2.84, -0.12, 1.72), (-2.62, 1.24, 1.55)); GROUPS_EXTRA['pulley'] = set(bpy.data.objects.keys()) - _b
wire((-4.6, 1.2, 4.3), (-0.95, 2.2, 3.7), 0.5)
wire((-2.85, -2.8, 3.2), (3.1, 0.3, 3.4), 0.9)
crates(-4.3, 0.95, 0.28); crates(3.3, -0.1, 0.28)
# bicycle against B
bw = Vector((1.5, 2.12, 0.42))
for dx in (-0.22, 0.22):
    cyl('bike_wheel', tuple(bw + Vector((dx, 0, 0))), 0.16, 0.02, iron, verts=24, rot=(math.pi / 2, 0, 0))
limb(bw + Vector((-0.22, 0, 0)), bw + Vector((0.0, 0, 0.18)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
limb(bw + Vector((0.22, 0, 0)), bw + Vector((0.0, 0, 0.18)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
limb(bw + Vector((0.0, 0, 0.18)), bw + Vector((0.2, 0, 0.3)), 0.01, varied('bikeframe', (0.5, 0.15, 0.12), 0.05, 0.4))
# an old town bike leaning on the bakery's canal side, baguettes in the basket
_b = set(bpy.data.objects.keys()); EX.bicycle((-2.615, -1.0, 0.341), math.pi / 2, -0.12, iron); GROUPS_NEW = {'bike': set(bpy.data.objects.keys()) - _b}
# washing strung low across from the bakery to the tall house
_b = set(bpy.data.objects.keys())
# long banners on poles off the walls
EX.banner((3.02, -0.18, 1.16), (-1, -1, 0), 'floral', h=0.36)      # on the lamp post at C's corner
EX.banner((-0.98, 1.77, 1.16), (-1, -1, 0), 'stars', h=0.36)       # on the lamp post at B's corner
EX.banner((-2.84, -1.0, 2.95), (1, 0, 0), 'fan', h=0.48)          # bakery's canal side, between windows, above the hanging sign
GROUPS_NEW['banners'] = set(bpy.data.objects.keys()) - _b
# a small owl on the corner house's ridge, eyes shut (the browser opens them)
_b = set(bpy.data.objects.keys()); bpy.context.view_layer.update()
_hit = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((4.42, 2.05, 20.0)), Vector((0, 0, -1)))
_rz = _hit[1].z if _hit[0] else topC + 1.0
EX.owl((4.42, 2.05, _rz - 0.004), -3 * math.pi / 4, s=0.82); EX.owl_pose('closed'); GROUPS_NEW['owl'] = set(bpy.data.objects.keys()) - _b
_b = set(bpy.data.objects.keys())
# boats instead of plank walkways
rowboat(5.45, 1.7, 1.5, 0.9, None, col=(0.42, 0.3, 0.2))
GROUPS_NEW['side_boat'] = set(bpy.data.objects.keys()) - _b
HB = houseboat(0.6, -1.0, 0.35, 2.3)
rowboat(-1.3, -2.7, 0.6, 1.0, 'flowers', col=(0.2, 0.3, 0.35))
rowboat(3.7, -1.6, -0.4, 1.0, 'crates')
rowboat(-1.6, 0.25, 0.2, 0.85, None, col=(0.45, 0.25, 0.18))
rowboat(2.2, 0.9, 1.4, 0.8, None, lantern_pole=False, col=(0.3, 0.35, 0.28))
gondola(2.0, -3.3, -0.15, 1.6)
for (px, py, bx, by) in ((-2.3, 0.6, -1.85, 0.3), (2.75, -0.5, 3.4, -1.4), (-1.1, 1.45, 0.0, -0.6)):
    cyl('mooring', (px, py, 0.15), 0.05, 0.42, timber, verts=10); cyl('mooring_cap', (px, py, 0.37), 0.06, 0.04, iron, verts=10)
    moor((px, py, 0.15), (bx, by, 0.14))
ivy_patch((-2.35, 1.6, 0.3), (1, 0, 0), 1.0, 2.6, 500, 'ivy_d', (0.12, 0.22, 0.07))
ivy_patch((4.67, 0.6, 0.3), (1, 0, 0), 0.7, 1.8, 300, 'ivy_d', (0.12, 0.22, 0.07))
big_flower_pot((0.2, 1.95, 0.28))
leafy_pot((-3.0, 1.0, 0.28), 'leafy')
leafy_pot((-3.2, -3.2, 0.28), 'lavender')

# controlled clutter: posters, graffiti, pigeons, rubbish, ladders, a fishing line
for (W, u, z, w, h) in ((AF, -2.75, 0.75, 0.3, 0.42), (AF, -2.48, 0.62, 0.22, 0.3), (BF, 1.75, 0.75, 0.28, 0.4), (DF, -3.3, 0.7, 0.26, 0.38),
                        (DS, -1.7, 0.8, 0.3, 0.42), (CS, 1.9, 0.7, 0.26, 0.36), (AS, 1.9, 0.72, 0.3, 0.42)):
    worn_poster(W, u, z, w, h)
graffiti(AF, -4.25, 0.55, 'noor', (0.75, 0.75, 0.72), 0.16, 0.05)
graffiti(DS, -2.4, 0.5, 'hush', (0.55, 0.2, 0.22), 0.17, -0.04)
graffiti(CS, 3.3, 0.52, 'K!', (0.3, 0.42, 0.55), 0.2, 0.0)
graffiti(BF, 0.95, 0.5, 'mira', (0.62, 0.52, 0.28), 0.14, 0.06)
for (x, y, z, a) in ((-3.0, 3.2, topA + 1.25, 0.4), (-3.25, 3.0, topA + 1.22, 2.0), (0.3, 2.3, topB + 0.36, 1.0), (0.9, 2.3, topB + 0.36, 3.0), (3.6, 0.15, topC + 0.12, 1.5)):
    pigeon(x, y, z, a)
_b = set(bpy.data.objects.keys()); trash(-4.4, -3.13, 0.28); GROUPS_BIN = set(bpy.data.objects.keys()) - _b   # bin at x -3.95: clear of the chair, the lavender and the lamp
# an old kitchen chair someone carried out to sit by the water, a cat asleep on it
def old_chair(x, y, z, a):
    R = Matrix.Rotation(a, 3, 'Z'); O = Vector((x, y, z))
    P = lambda dx, dy, dz: O + R @ Vector((dx, dy, dz))
    wood = varied('chair_wood', (0.36, 0.22, 0.13), 0.1, 0.75)
    paint = solid('chair_paint', (0.3, 0.38, 0.33), 0.8)   # flaking green paint on the seat
    for (dx, dy) in ((-0.1, -0.1), (0.1, -0.1), (-0.1, 0.1), (0.1, 0.1)):
        limb(P(dx, dy, 0.0), P(dx * 1.05, dy * 1.05, 0.25), 0.012, wood)
    for dz in (0.08,):
        limb(P(-0.1, -0.1, dz), P(-0.1, 0.1, dz), 0.006, wood); limb(P(0.1, -0.1, dz), P(0.1, 0.1, dz), 0.006, wood)
    box('chair_seat', P(0, 0, 0.26), (0.24, 0.24, 0.025), paint, bevel=0.006).rotation_euler = (0, 0, a)
    for dx in (-0.1, 0.1):
        limb(P(dx, 0.11, 0.26), P(dx, 0.14, 0.58), 0.011, wood)
    for dz in (0.38, 0.47, 0.56):
        limb(P(-0.1, 0.125 + (dz - 0.26) * 0.09, dz), P(0.1, 0.125 + (dz - 0.26) * 0.09, dz), 0.007, wood)
    fur = solid('cat_fur_c', (0.48, 0.32, 0.18), 0.85)
    c = P(0.0, -0.01, 0.31)
    sphere('chair_cat', c, 0.075, fur, 12, (1.25, 1.0, 0.55))
    sphere('chair_cat_head', P(0.07, -0.05, 0.32), 0.035, fur, 10)
    for sg in (-1, 1):
        cyl('chair_cat_ear', P(0.08 + sg * 0.012, -0.05 + sg * 0.012, 0.355), 0.01, 0.022, fur, verts=4, r2=0.0)
    for k in range(6):   # tail curled round the front
        t0, t1 = k / 6 * 2.4, (k + 1) / 6 * 2.4
        limb(P(-0.08 * math.cos(t0), -0.08 * math.sin(t0) - 0.02, 0.29), P(-0.08 * math.cos(t1), -0.08 * math.sin(t1) - 0.02, 0.29), 0.012, fur)
old_chair(-4.5, -3.12, 0.28, 0.35)
cyl('mailbox', (1.95, 2.2, 0.62), 0.07, 0.24, solid('mailbox', (0.5, 0.12, 0.1), 0.5), verts=14, rot=(math.pi / 2, 0, 0))
for (x, y, a) in ((-2.0, 2.6, 0.0), (2.85, 1.2, math.pi), (-2.6, -1.6, 0.0), (-4.85 + 0.0, 2.0, 0.0)):
    quay_ladder(x, y, a + math.pi / 2)
cyl('outflow', (-2.0, 3.6, 0.15), 0.05, 0.25, rustm, verts=10, rot=(0, math.pi / 2, 0))
for k in range(4):
    sphere('drip', (-1.85, 3.6, 0.1 - k * 0.035), 0.008, solid('drip', (0.7, 0.8, 0.85), 0.05), 6)
limb(Vector((-2.35, 1.25, 1.75)), Vector((-1.3, 0.2, 2.1)), 0.004, timber_h)          # a fishing rod out of a window
limb(Vector((-1.3, 0.2, 2.1)), Vector((-1.25, 0.15, 0.0)), 0.0015, solid('line', (0.8, 0.8, 0.8), 0.3))
sphere('bobber', (-1.25, 0.15, 0.01), 0.015, solid('bobber', (0.85, 0.15, 0.1), 0.4), 8)
# a few paper lanterns let float on the canal
_b = set(bpy.data.objects.keys())
for (x, y, yaw, kind) in ((-1.95, -1.45, 0.3, 'floral'), (1.55, -2.2, -0.4, 'stars'), (-0.5, -2.4, 0.9, 'fan'), (3.05, -2.75, 0.1, 'dots')):
    EX.floating_lantern((x, y, -0.008), yaw, kind)
GROUPS_NEW['lanterns'] = set(bpy.data.objects.keys()) - _b

if os.environ.get('SPOTS'):
    # what sits on these bits of wall (to find clear spots for banners and lines)
    bpy.context.view_layer.update()
    for label, lo_, hi_ in (('Af2', (-4.5, 0.5, 2.6), (-2.4, 1.35, 3.7)), ('Af3', (-4.5, 0.5, 3.75), (-2.4, 1.35, 4.9))):
        print('SPOTS', label)
        for o in sc.objects:
            if o.type != 'MESH' or o.hide_render or o.name.split('.')[0] in ('A', 'B', 'C', 'D', 'quay', 'canal'): continue
            cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
            a = [min(c[i] for c in cs) for i in range(3)]; b = [max(c[i] for c in cs) for i in range(3)]
            if all(b[i] > lo_[i] and a[i] < hi_[i] for i in range(3)) and max(b[i] - a[i] for i in range(3)) < 2.5:
                print('   ', o.name.split('.')[0], [round(v, 2) for v in a], [round(v, 2) for v in b])
if os.environ.get('CHECK'):
    # does anything new touch something it shouldn't? (bounding boxes, a few mm slack)
    GROUPS_NEW['bin'] = GROUPS_BIN
    GROUPS_NEW.update(GROUPS_EXTRA)
    bpy.context.view_layer.update()
    def bb(o):
        cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])
    ignore = ('quay', 'canal', 'canal_bed', 'cobble', 'kerb', 'roofC', 'C', 'D', 'gable')
    for g, names in GROUPS_NEW.items():
        objs = [bpy.data.objects[n] for n in names if n in bpy.data.objects and bpy.data.objects[n].type == 'MESH' and not bpy.data.objects[n].hide_render]
        if not objs: continue
        lo = Vector([min(bb(o)[0][i] for o in objs) for i in range(3)]); hi = Vector([max(bb(o)[1][i] for o in objs) for i in range(3)])
        hits = []
        others_bb = [(o, bb(o)) for o in sc.objects if not (o.name in names or o.type != 'MESH' or o.hide_render or o.name.split('.')[0] in ignore or o.name.startswith(ignore))]
        for q in objs:
            qa, qb = bb(q)
            for o, (a, b) in others_bb:
                depth = min(min(qb[i], b[i]) - max(qa[i], a[i]) for i in range(3))
                if depth > 0.006:
                    hits.append('%s~%s(%.3f)@%s' % (q.name.split('.')[0], o.name.split('.')[0], depth, tuple(round(v, 2) for v in (qa + qb) / 2)))
        for o in objs:
            pass
        if g == 'bike':
            for o in sc.objects:
                if o.type == 'MESH' and not o.hide_render and o.name.split('.')[0] in ('sill', 'wc', 'door', 'shopd', 'poster', 'pane', 'ladder', 'rung'):
                    a, b = bb(o)
                    if b.x > -2.95 and a.x < -2.5 and a.z < 1.3 and -3.0 < a.y < 0.3: print('  near', o.name, [round(v, 2) for v in a], [round(v, 2) for v in b])
        print('CHECK', g, [round(v, 2) for v in lo], [round(v, 2) for v in hi], 'touches:', sorted(set(hits)))
lighting(sc, sun_rot=(math.radians(76), 0, math.radians(-40)), sun_energy=1.9, sun_color=(1.0, 0.64, 0.42),
         bg_top=(0.05, 0.07, 0.13), bg_bottom=(0.35, 0.24, 0.24), hdri_strength=0.13)
# The canal mirrors the sky: keep what it reflects at the old, darker dusk level,
# while the walls take the brighter late sun and sky.
_wn = sc.world.node_tree.nodes; _wl = sc.world.node_tree.links
_lp = _wn.new('ShaderNodeLightPath'); _mr = _wn.new('ShaderNodeMapRange')
_mr.inputs['To Min'].default_value = 0.13; _mr.inputs['To Max'].default_value = float(os.environ.get('GLOSSY_WORLD', '0.08'))
_wl.new(_lp.outputs['Is Glossy Ray'], _mr.inputs['Value']); _wl.new(_mr.outputs['Result'], _wn['Background'].inputs['Strength'])
# ...and the low sun lights the buildings, not the water (light linking).
_ns = bpy.data.collections.new('no_sun')
for _nm in ('canal', 'canal_bed'):
    if _nm in bpy.data.objects: _ns.objects.link(bpy.data.objects[_nm])
_sun = next(o for o in sc.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
_sun.light_linking.receiver_collection = _ns
for _co in _ns.collection_objects: _co.light_linking.link_state = 'EXCLUDE'
cam = iso_camera(sc, (-0.1, 0.4, 2.4), 15.5, res=(int(os.environ.get('RES_X', 1400)), int(os.environ.get('RES_Y', 1050))))
if os.environ.get('LIST_PANES'):
    # every window's glass and where it lands in the street render
    from bpy_extras.object_utils import world_to_camera_view
    import json as _json
    bpy.context.view_layer.update()
    rows = []
    for o in sc.objects:
        if o.type == 'MESH' and not o.hide_render and o.name.split('.')[0] in ('pane', 'bay_glass', 'shop_glass', 'win_glass', 'hull_port'):
            lo = [min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)]
            hi = [max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)]
            c = Vector([(a + b) / 2 for a, b in zip(lo, hi)])
            v = world_to_camera_view(sc, cam, c)
            rows.append({'n': o.name, 'c': [round(x, 2) for x in c], 'px': [round(v.x, 4), round(1 - v.y, 4)]})
    _json.dump(rows, open(os.environ['LIST_PANES'], 'w'))
    print('PANES', len(rows))
if os.environ.get('ZOOM_INDEX'):
    # where each zoom's windows sit in the street render (for the browser's click areas)
    from bpy_extras.object_utils import world_to_camera_view
    import json as _json
    import zoom_props as ZP
    bpy.context.view_layer.update()
    uvv = lambda p: (lambda v: [round(v.x, 5), round(1 - v.y, 5)])(world_to_camera_view(sc, cam, p))
    def quad(c, t, w, h):
        return [uvv(c + t * (sa * w / 2) + Vector((0, 0, sz * h / 2))) for sa, sz in ((-1, 1), (1, 1), (1, -1), (-1, -1))]
    idx = {}
    for zid, spec in list(ZP.ZOOMS.items()) + [('shop', {'glass': [(-0.56, 2.33, 0.85)]}), ('design', {'glass': [(u, 1.33, 4.31) for u in (-4.2167, -3.45, -2.6833)]})]:
        qs = []
        for gp in spec['glass']:
            g = ZP.find_glass(sc, gp)
            if g is None: continue
            c, t, n, w, h = ZP.frame_of(g, ZP.STREET_DIR)
            qs.append(quad(c, t, w + 0.1, h + 0.1))
        idx[zid] = qs
    _json.dump(idx, open(os.environ['ZOOM_INDEX'], 'w'))
    print('ZOOM INDEX', {k: len(v) for k, v in idx.items()})
if os.environ.get('PROBE_PX'):
    # what the street camera sees at these pixels (x,y from the top-left)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    fr = cam.data.view_frame(scene=sc); mw = cam.matrix_world
    W_, H_ = sc.render.resolution_x, sc.render.resolution_y
    dv = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    for xy in os.environ['PROBE_PX'].split(';'):
        px, py = map(float, xy.split(','))
        u_, v_ = px / W_, py / H_
        q = fr[3].lerp(fr[0], u_).lerp(fr[2].lerp(fr[1], u_), v_)
        o_ = mw @ q - dv * 60
        hits = []
        for _ in range(4):
            ok, loc, nrm, idx, ob, _m = sc.ray_cast(dg, o_, dv)
            if not ok: break
            o_ = loc + dv * 1e-4
            if ob.hide_render: continue
            hits.append('%s(%.2f,%.2f,%.2f)' % (ob.name, loc.x, loc.y, loc.z))
        print('PX', xy, ' -> '.join(hits))
SMOKE = []
if os.environ.get('NO_SMOKE'):
    # The browser animates the chimney smoke, so take the baked puffs out and
    # remember where each plume starts (its lowest puff), in 0..1 screen space.
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    puffs = [o for o in sc.objects if o.name.startswith('smoke')]
    for o in puffs:
        p = o.matrix_world.translation
        lower = [q for q in puffs if q is not o and (q.matrix_world.translation.xy - p.xy).length < 0.45 and q.matrix_world.translation.z < p.z - 0.05]
        if not lower:
            v = world_to_camera_view(sc, cam, p)
            SMOKE.append({'x': round(v.x, 4), 'y': round(1 - v.y, 4), 'r': round(max(o.dimensions) / 2 / 15.5, 5)})
        o.hide_render = True
import window_closeup as WCU
WCU.shop_squirrel(sc)
if os.environ.get('CLOSEUP') == 'shop':
    WCU.shop_window(sc, cam, globals())
if os.environ.get('CLOSEUP') == 'design':
    WCU.design_windows(sc, cam, globals())
if os.environ.get('CLOSEUP') not in (None, '', 'shop', 'design'):
    WCU.zoom_generic(sc, cam, globals(), os.environ['CLOSEUP'])
if os.environ.get('NO_RENDER'):
    render = lambda *a, **k: None
# what glows, noted before the lights-off pass zeroes every emission
def glows(m):
    if m is None or not m.use_nodes: return False
    for nd in m.node_tree.nodes:
        if nd.type == 'BSDF_PRINCIPLED' and (nd.inputs['Emission Strength'].default_value > 0 or nd.inputs['Emission Strength'].links): return True
        if nd.type == 'EMISSION' and nd.inputs['Strength'].default_value > 0: return True
    return False
GLOWING = {o.name for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT') and o.name != 'canal' and any(glows(sl.material) for sl in o.material_slots)}
WEB_ONLY = bool(os.environ.get('WEB_ONLY'))
if os.environ.get('QCROP'):
    # a quick render of just one box of the street, for checking details
    q = [float(v) for v in os.environ['QCROP'].split(',')]
    pts = [Vector((x, y, z)) for x in (q[0], q[3]) for y in (q[1], q[4]) for z in (q[2], q[5])]
    EX.render_crop(sc, OUT, EX.crop_border(sc, cam, pts, 10), SAMPLES)
    sys.exit(0)
if os.environ.get('SHOP_PATCH'):
    # Re-render only the box round the shop window (lit, then lights off), to
    # paste into an existing street render: used when only that window changed.
    import json as _json
    PD = os.environ['SHOP_PATCH']; os.makedirs(PD, exist_ok=True)
    pts = [Vector((x, y, z)) for x in (-0.98, -0.18) for y in (1.95, 2.4) for z in (0.3, 1.4)]
    pbox = EX.crop_border(sc, cam, pts, 10)
    EX.render_crop(sc, os.path.join(PD, 'lit.png'), pbox, SAMPLES)
    for o in sc.objects:
        if o.type == 'LIGHT' and o.data.type != 'SUN': o.data.energy = 0.0
    for m in bpy.data.materials:
        if m.name == 'endless_canal': continue
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Emission Strength'].default_value = 0.0
                    for l in list(n.inputs['Emission Strength'].links): m.node_tree.links.remove(l)
                if n.type == 'EMISSION': n.inputs['Strength'].default_value = 0.0
    EX.render_crop(sc, os.path.join(PD, 'off.png'), pbox, SAMPLES)
    _json.dump({'box': pbox, 'size': [sc.render.resolution_x, sc.render.resolution_y]}, open(os.path.join(PD, 'box.json'), 'w'))
    print('SHOP PATCH', pbox)
    sys.exit(0)
if not WEB_ONLY and not os.environ.get('OFF_ONLY'):
    render(sc, OUT, SAMPLES)
if os.environ.get('CROPS'):
    # close-up test crops (full resolution) of the newest details
    for nm, (c, r) in {'bike': ((-2.7, -1.0, 0.7), 0.7), 'bin': ((-4.1, -3.1, 0.5), 0.6), 'wash': ((-2.65, 0.5, 2.0), 0.9),
                       'boat': ((5.45, 1.7, 0.2), 0.7), 'owl': (tuple(EX.OWL['head']), 0.3)}.items():
        c = Vector(c)
        EX.render_crop(sc, os.path.join(os.environ['CROPS'], nm + '.png'), EX.crop_border(sc, cam, [c + Vector((dx, dy, dz)) for dx in (-r, r) for dy in (-r, r) for dz in (-r, r)]), SAMPLES)
EXTRAS = os.environ.get('EXTRAS_OUT', '')
if EXTRAS:
    os.makedirs(EXTRAS, exist_ok=True)
    import json as _json
    hc = EX.OWL['head']
    obox = EX.crop_border(sc, cam, [hc + Vector((dx, dy, dz)) for dx in (-0.1, 0.1) for dy in (-0.1, 0.1) for dz in (-0.06, 0.08)], 4)
    for st in os.environ.get('OWL_STATES', 'closed,open,left,right,half').split(','):
        EX.owl_pose(st)
        EX.render_crop(sc, os.path.join(EXTRAS, 'owl_' + st + '.png'), obox, SAMPLES)
    EX.owl_pose('closed')
    W_, H_ = sc.render.resolution_x, sc.render.resolution_y
    others = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.hide_render]
    koi = [] if True else EX.koi_frames(sc, cam, EXTRAS, [((-1.75, -1.35, 0.0), 0.75), ((2.35, -2.15, 0.0), 0.8)], others, samples=int(os.environ.get('KOI_SAMPLES', 64)))
    _json.dump({'owl': {'box': [obox[0] / W_, 1 - obox[3] / H_, obox[2] / W_, 1 - obox[1] / H_], 'states': ['closed', 'open', 'left', 'right', 'half']}, 'koi': koi},
               open(os.path.join(EXTRAS, 'extras.json'), 'w'))
if os.environ.get('OFF_OUT') and not WEB_ONLY:
    # Same scene with every lamp, candle, window and sign switched off.
    for o in sc.objects:
        if o.type == 'LIGHT' and o.data.type != 'SUN':
            o.data.energy = 0.0
    for m in bpy.data.materials:
        if m.name == 'endless_canal': continue   # the far haze isn't a lamp
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Emission Strength'].default_value = 0.0
                    for l in list(n.inputs['Emission Strength'].links):
                        m.node_tree.links.remove(l)
                if n.type == 'EMISSION':
                    n.inputs['Strength'].default_value = 0.0
    render(sc, os.environ['OFF_OUT'], SAMPLES)
if SMOKE and os.environ.get('SMOKE_JSON'):
    import json
    json.dump(SMOKE, open(os.environ['SMOKE_JSON'], 'w'))
WEB = os.environ.get('WEB_OUT', '')
if WEB:
    import json
    from bpy_extras.object_utils import world_to_camera_view
    os.makedirs(WEB, exist_ok=True)
    W2, H2 = 1400, 1050
    # 1) lights to flicker: candles, lanterns, globes (not the room fill lights)
    lights = []
    for o in sc.objects:
        if o.type == 'LIGHT' and o.data.type == 'POINT' and not o.name.startswith(('room',)):
            v = world_to_camera_view(sc, cam, o.matrix_world.translation)
            if 0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0:
                lights.append({'x': round(v.x, 4), 'y': round(1 - v.y, 4), 'k': o.name.split('.')[0],
                               'c': [round(c, 3) for c in o.data.color], 'e': round(o.data.energy, 2)})
    # 2) masks: holdout everything except one group, render alpha
    GROUPS = {
        'tall': lambda c: -4.9 < c.x < -1.95 and 0.8 < c.y < 4.2,
        'shop': lambda c: -1.2 < c.x < 2.4 and 1.55 < c.y < 4.2,
        'corner': lambda c: 2.8 < c.x < 4.9 and -0.35 < c.y < 4.2,
        'bakery': lambda c: -4.9 < c.x < -2.5 and -3.45 < c.y < 0.3,
        'boat': lambda c: (lambda q: abs(q.x) < 1.35 and abs(q.y) < 0.6)(Matrix.Rotation(-0.35, 3, 'Z') @ (c - Vector((0.6, -1.0, c.z)))),
    }
    geo = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.hide_render]
    def centre(o):
        bb = [o.matrix_world @ Vector(b) for b in o.bound_box]
        return sum(bb, Vector()) / 8
    centres = {o.name: centre(o) for o in geo}
    sc.render.film_transparent = True
    sc.cycles.samples = 6; sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = W2, H2
    def mask(name, pick):
        for o in geo:
            o.is_holdout = not pick(o)
        render(sc, os.path.join(WEB, 'mask_' + name + '.png'), 6)
    canal = bpy.data.objects['canal']
    white = solid('mask_white', (1, 1, 1), 1.0, emit=(1, 1, 1), strength=1)
    keep = list(canal.data.materials); canal.data.materials.clear(); canal.data.materials.append(white)
    mask('water', lambda o: o is canal)
    canal.data.materials.clear(); [canal.data.materials.append(m) for m in keep]
    for g, f in GROUPS.items():
        mask(g, lambda o, f=f: f(centres[o.name]) and o is not canal)
    # 3) switch-on order: every glowing thing (window panes, flames, signs) gets
    # its own random grey; the browser spreads it to the light around it.
    # Each glowing thing emits (its random grey, 1, 0); everything else is
    # matt black, the water a mirror, no lamps, no sky. So a pixel's red/green
    # is the switch-on moment of whatever lights it, directly or in reflection.
    dm, dn, dl, db = node_mat('delay_id')
    oi = dn.new('ShaderNodeObjectInfo'); comb = dn.new('ShaderNodeCombineColor'); dem = dn.new('ShaderNodeEmission')
    dl.new(oi.outputs['Random'], comb.inputs['Red']); comb.inputs['Green'].default_value = 1.0; comb.inputs['Blue'].default_value = 0.0
    dl.new(comb.outputs['Color'], dem.inputs['Color'])
    dl.new(dem.outputs['Emission'], next(x for x in dn if x.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    black = solid('delay_black', (0, 0, 0), 1.0)
    mirror = solid('delay_mirror', (0, 0, 0), 0.03, metal=1.0)
    mirror.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1, 1, 1, 1)
    saved = {}
    for o in geo:
        saved[o.name] = [sl.material for sl in o.material_slots]
        m_ = dm if o.name in GLOWING else mirror if o is canal else black
        if o.name in GLOWING and o.get('glow_group') is not None:
            # pieces of one sign share one moment, so it never comes on in bits
            gk = 'delay_g%.4f' % o['glow_group']
            m_ = solid(gk, (0, 0, 0), 1.0, emit=(o['glow_group'], 1.0, 0.0), strength=1.0)
        for sl in o.material_slots: sl.material = m_
        o.is_holdout = False
    lights_e = {o.name: o.data.energy for o in sc.objects if o.type == 'LIGHT'}
    for o in sc.objects:
        if o.type == 'LIGHT': o.data.energy = 0.0
    world = sc.world; sc.world = None
    sc.render.film_transparent = False
    vt = sc.view_settings.view_transform; sc.view_settings.view_transform = 'Raw'
    depth = sc.render.image_settings.color_depth; sc.render.image_settings.color_depth = '16'
    render(sc, os.path.join(WEB, 'delay.png'), 16)
    sc.view_settings.view_transform = vt; sc.render.image_settings.color_depth = depth
    sc.world = world
    for o in sc.objects:
        if o.type == 'LIGHT': o.data.energy = lights_e[o.name]
    for name, mats in saved.items():
        for sl, m in zip(bpy.data.objects[name].material_slots, mats): sl.material = m
    print('DELAY objects', len(saved))
    for o in geo:
        o.is_holdout = False
    json.dump({'size': [W2, H2], 'lights': lights, 'groups': list(GROUPS)}, open(os.path.join(WEB, 'scene.json'), 'w'), separators=(',', ':'))
    print('WEB EXPORT', len(lights), 'lights')
elif os.environ.get('BOAT_CLOSEUP'):
    # close-up of the houseboat and its sign
    cam.data.type = 'PERSP'; cam.data.lens = 50
    tgt = HB(-0.1, -0.2, 0.55)
    cam.location = tgt + Vector((1.1, -2.6, 1.15))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    render(sc, OUT.replace('.png', '_boat.png'), SAMPLES)
