"""
Build the globe's interior in Blender, layer by layer, the way a real
terrarium is built: soil/gravel bowl -> terrain & mountain -> water ->
rocks -> trees -> ferns -> moss. Then render a Cycles reference.

Run: bvenv/bin/python build.py <assets-raw dir> <out dir> [render|export|both]
Blender is Z-up; the sphere centre is the origin; inner glass radius 0.972.
"""
import bpy, bmesh, sys, os, glob, math, random
from mathutils import Vector, noise, Matrix

ASSETS, OUT = sys.argv[-3], sys.argv[-2]
MODE = sys.argv[-1]
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'textures')

os.makedirs(OUT, exist_ok=True)
random.seed(9)

INNER = 0.972
DEPTH = 0.55
GROUND = -DEPTH
EDGE = math.sqrt(INNER * INNER - DEPTH * DEPTH)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------------------------------------------------------- heightfield
def fbm(x, y, z, oct=4):
    a, f, s = 0.5, 1.0, 0.0
    for _ in range(oct):
        s += a * noise.noise(Vector((x * f, y * f, z * f)))
        a *= 0.5
        f *= 2.03
    return s

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def poly_dist(px, py, pts):
    best = 1e9
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy or 1
        u = max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / l2))
        dx, dy = ax + vx * u - px, ay + vy * u - py
        best = min(best, dx * dx + dy * dy)
    return math.sqrt(best)

def catmull(pts, n):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out

# Layout in (x, y) with y = depth axis (+y is the back). Camera looks toward +y.
M = (-0.16, 0.42)
FALL_X = 0.02
POOL = (0.04, 0.06)
STREAM = catmull([POOL, (0.16, -0.1), (0.12, -0.3), (0.28, -0.5), (0.24, -0.72)], 12)
STEPS = catmull([(-0.24, -0.72), (-0.2, -0.46), (-0.1, -0.24), (-0.05, -0.08)], 4)
PEAKS = [(M[0], M[1], 0.7, 0.42), (M[0] - 0.26, M[1] - 0.06, 0.48, 0.3), (M[0] + 0.3, M[1] + 0.02, 0.52, 0.32)]

def mountain_h(x, y):
    h = 0.0
    for px, py, ph, pr in PEAKS:
        r = math.hypot(x - px, (y - py) * 1.1) / pr
        if r < 1:
            h = max(h, ph * (1 - r ** 1.4) ** 1.15)
    if h <= 0:
        return 0.0
    ridged = 1 - abs(fbm(x * 6 + 7, 1, y * 6, 4)) * 2
    h *= 0.85 + ridged * 0.22
    step = 0.05
    q = math.floor(h / step) * step
    h = q + ((h - q) / step) ** 4 * step
    notch = math.exp(-((x - FALL_X) ** 2) / 0.0012) * smoothstep(-0.36, -0.14, -y)
    return max(0.0, h * (1 - notch * 0.25))

def ground_at(x, y):
    r = math.hypot(x, y) / EDGE
    edge = max(0.0, 1 - min(1.0, r) ** 6)
    h = 0.03 + fbm(x * 3.5, 0.5, y * 3.5) * 0.04
    h += mountain_h(x, y)
    sd = poly_dist(x, y, STREAM)
    h -= 0.03 * math.exp(-(sd * sd) / 0.0025)
    h -= 0.035 * math.exp(-((x - POOL[0]) ** 2 + (y - POOL[1]) ** 2) / 0.008)
    z = GROUND + h * edge
    zmax = math.sqrt(max(0.0, INNER * INNER * 0.9 - x * x - y * y))
    return min(z, zmax)

def slope_at(x, y, e=0.01):
    return math.hypot(ground_at(x + e, y) - ground_at(x - e, y), ground_at(x, y + e) - ground_at(x, y - e)) / (2 * e)

# ---------------------------------------------------------------- materials
def img(name, colorspace):
    path = os.path.join(TEX, name + '.webp')
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im

def triplanar_mat(name, diff, nor, scale, extra=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True  # noqa
    nt = m.node_tree
    N = nt.nodes
    bsdf = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    t = N.new('ShaderNodeTexImage'); t.image = img(diff, 'sRGB'); t.projection = 'BOX'; t.projection_blend = 0.3
    nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    tn = N.new('ShaderNodeTexImage'); tn.image = img(nor, 'Non-Color'); tn.projection = 'BOX'; tn.projection_blend = 0.3
    nt.links.new(mp.outputs['Vector'], tn.inputs['Vector'])
    nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = 0.9
    return m, nt, t, bsdf

def terrain_material():
    """Rock on steep slopes, moss on gentle ones, pebbles in the stream bed (vertex colour)."""
    m, nt, rock, bsdf = triplanar_mat('terrain', 'mossy_rock_diff', 'mossy_rock_nor', 2.2)
    N = nt.nodes
    tc = [n for n in N if n.type == 'TEX_COORD'][0]
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3, 3, 3)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    moss = N.new('ShaderNodeTexImage'); moss.image = img('aerial_grass_rock_diff', 'sRGB'); moss.projection = 'BOX'; moss.projection_blend = 0.3
    nt.links.new(mp.outputs['Vector'], moss.inputs['Vector'])
    # Push the scanned ground toward saturated moss greens.
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Hue'].default_value = 0.56; hsv.inputs['Saturation'].default_value = 1.5; hsv.inputs['Value'].default_value = 0.85
    nt.links.new(moss.outputs['Color'], hsv.inputs['Color'])
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Normal'], sep.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.62; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.82; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(ramp.outputs['Color'], mix.inputs['Factor'])
    nt.links.new(rock.outputs['Color'], mix.inputs[6])
    nt.links.new(hsv.outputs['Color'], mix.inputs[7])
    # Pebbles where the vertex colour 'bed' is set.
    peb = N.new('ShaderNodeTexImage'); peb.image = img('ganges_river_pebbles_diff', 'sRGB'); peb.projection = 'BOX'
    mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (9, 9, 9)
    nt.links.new(tc.outputs['Object'], mp2.inputs['Vector']); nt.links.new(mp2.outputs['Vector'], peb.inputs['Vector'])
    attr = N.new('ShaderNodeAttribute'); attr.attribute_name = 'bed'
    mix2 = N.new('ShaderNodeMix'); mix2.data_type = 'RGBA'
    nt.links.new(attr.outputs['Fac'], mix2.inputs['Factor'])
    nt.links.new(mix.outputs[2], mix2.inputs[6]); nt.links.new(peb.outputs['Color'], mix2.inputs[7])
    nt.links.new(mix2.outputs[2], bsdf.inputs['Base Color'])
    return m

def simple_mat(name, color, rough=0.8, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True  # noqa
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m

# ---------------------------------------------------------------- layer 1: soil & gravel bowl
def build_soil():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=160, ring_count=64, radius=INNER)
    o = bpy.context.object; o.name = 'soil'
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > GROUND + 0.002], context='VERTS')
    bm.to_mesh(o.data); bm.free()
    m = bpy.data.materials.new('soil'); m.use_nodes = True  # noqa
    nt = m.node_tree; N = nt.nodes; b = N['Principled BSDF']
    # Strata: dark loam over pale gravel, wavy boundary.
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.08
    nt.links.new(nz.outputs['Fac'], mul.inputs[0]); nt.links.new(sep.outputs['Z'], add.inputs[0]); nt.links.new(mul.outputs[0], add.inputs[1])
    ramp = N.new('ShaderNodeValToRGB')
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.62, 0.57, 0.5, 1)
    e[1].position = 0.12; e[1].color = (0.16, 0.09, 0.045, 1)
    e3 = e.new(0.06); e3.color = (0.35, 0.32, 0.28, 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -INNER; mr.inputs['From Max'].default_value = GROUND
    nt.links.new(add.outputs[0], mr.inputs['Value'])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
    nt.links.new(mr.outputs['Result'], inv.inputs[1])
    # 1 at bottom -> 0 at top; ramp 0 = top loam, use reversed
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    vor = N.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 140
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.5
    nt.links.new(ramp.outputs['Color'], mix.inputs[6]); nt.links.new(vor.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.95
    o.data.materials.append(m)
    # The ramp should be loam at the top (Result≈1) and gravel at the bottom (Result≈0):
    e[0].color = (0.6, 0.55, 0.48, 1); e[0].position = 0.0
    e3.position = 0.45; e3.color = (0.42, 0.38, 0.33, 1)
    e[1].position = 0.55; e[1].color = (0.15, 0.085, 0.04, 1)
    return o

# ---------------------------------------------------------------- layer 2: terrain + mountain
def build_terrain():
    RINGS, SEG = 140, 360
    verts, faces, bed = [(0, 0, ground_at(0, 0))], [], [0.0]
    for i in range(1, RINGS + 1):
        rr = (i / RINGS) ** 0.9 * EDGE
        for j in range(SEG):
            a = j / SEG * math.tau
            x, y = math.cos(a) * rr, math.sin(a) * rr
            verts.append((x, y, ground_at(x, y)))
            sd = poly_dist(x, y, STREAM)
            pd = math.hypot(x - POOL[0], y - POOL[1])
            bed.append(max(min(1, max(0, 1 - sd / 0.055)), min(1, max(0, 1 - pd / 0.11))))
    for j in range(SEG):
        faces.append((0, 1 + j, 1 + (j + 1) % SEG))
    for i in range(1, RINGS):
        for j in range(SEG):
            a = 1 + (i - 1) * SEG + j
            b = 1 + (i - 1) * SEG + (j + 1) % SEG
            faces.append((a, a + SEG, b + SEG, b))
    me = bpy.data.meshes.new('terrain')
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    attr = me.color_attributes.new('bed', 'FLOAT_COLOR', 'POINT')
    for i, v in enumerate(bed):
        attr.data[i].color = (v, v, v, 1)
    o = bpy.data.objects.new('terrain', me)
    scene.collection.objects.link(o)
    o.data.materials.append(terrain_material())
    return o

# ---------------------------------------------------------------- layer 3: water + waterfall
def build_water():
    mats = []
    wm = bpy.data.materials.new('water'); wm.use_nodes = True  # noqa
    b = wm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.03, 0.06, 0.055, 1)
    b.inputs['Roughness'].default_value = 0.02
    b.inputs['Transmission Weight'].default_value = 0.6
    b.inputs['IOR'].default_value = 1.33
    # Pool
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=0.1, fill_type='NGON', location=(POOL[0], POOL[1], ground_at(*POOL) + 0.022))
    pool = bpy.context.object; pool.name = 'pool'; pool.data.materials.append(wm)
    # Stream ribbon
    verts, faces = [], []
    pts = catmull(STREAM, 4)
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[min(len(pts) - 1, i + 1)]; bx, by = pts[max(0, i - 1)]
        tx, ty = ax - bx, ay - by; tl = math.hypot(tx, ty) or 1
        w = 0.03 + math.sin(i * 0.4) * 0.006
        z = max(ground_at(x, y) + 0.008, GROUND + 0.004)
        for s in (-1, 1):
            verts.append((x - ty / tl * w * s, y + tx / tl * w * s, z))
        if i:
            a = (i - 1) * 2
            faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('stream'); me.from_pydata(verts, [], faces)
    st = bpy.data.objects.new('stream', me); scene.collection.objects.link(st); me.materials.append(wm)
    # Waterfall: ribbon down the notch, white streaky emission+translucent.
    fm = bpy.data.materials.new('waterfall'); fm.use_nodes = True  # noqa
    nt = fm.node_tree; N = nt.nodes; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (30, 3, 1)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
    wave = N.new('ShaderNodeTexNoise'); wave.inputs['Scale'].default_value = 3; wave.inputs['Detail'].default_value = 6
    nt.links.new(mp.outputs['Vector'], wave.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[1].position = 0.6
    nt.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Alpha'])
    b.inputs['Base Color'].default_value = (0.9, 0.96, 1.0, 1)
    b.inputs['Roughness'].default_value = 0.2
    b.inputs['Emission Color'].default_value = (0.8, 0.9, 0.95, 1)
    b.inputs['Emission Strength'].default_value = 0.4
    verts, faces, uvs = [], [], []
    FS = 40
    top, bottom = 0.34, POOL[1] + 0.05
    for i in range(FS + 1):
        t = i / FS
        y = top + (bottom - top) * t
        w = 0.018 + t * 0.022
        z = ground_at(FALL_X, y) + 0.012
        for s in (-1, 1):
            verts.append((FALL_X + s * w, y - 0.006, z))
            uvs.append((s * 0.5 + 0.5, t))
        if i:
            a = (i - 1) * 2
            faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('waterfall'); me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    fo = bpy.data.objects.new('waterfall', me); scene.collection.objects.link(fo); me.materials.append(fm)
    return [pool, st, fo]

# ---------------------------------------------------------------- asset helpers
def append(blend_glob, names):
    f = glob.glob(os.path.join(ASSETS, blend_glob))[0]
    with bpy.data.libraries.load(f, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names or any(n.startswith(x) for x in names if x.endswith('*'))]
    out = {}
    for o in dst.objects:
        if o is None:
            continue
        # Keep out of the scene; used as instance sources.
        o.matrix_world = Matrix.Identity(4)
        out[o.name] = o
    bpy.ops.file.make_paths_absolute()
    return out

def place(src, loc, scale, rot_z, name=None, tilt=0.0):
    o = bpy.data.objects.new(name or src.name, src.data)  # linked duplicate (instancing)
    o.location = loc
    o.rotation_euler = (random.uniform(-tilt, tilt), random.uniform(-tilt, tilt), rot_z)
    o.scale = (scale, scale, scale)
    scene.collection.objects.link(o)
    return o

def free(x, y, clear_stream=0.06, max_slope=0.4):
    if math.hypot(x, y) > EDGE * 0.93:
        return False
    if poly_dist(x, y, STREAM) < clear_stream or math.hypot(x - POOL[0], y - POOL[1]) < 0.12:
        return False
    if poly_dist(x, y, STEPS) < 0.04:
        return False
    return slope_at(x, y) < max_slope

# ---------------------------------------------------------------- layer 4: rocks
def build_rocks():
    rocks = []
    for setname in ('rock_moss_set_01', 'rock_moss_set_02'):
        path = os.path.join(ASSETS, setname, setname + '.gltf')
        bpy.ops.import_scene.gltf(filepath=path)
        for o in bpy.context.selected_objects:
            if o.type != 'MESH':
                continue
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
            bpy.ops.mesh.separate(type='LOOSE')
            for p in bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = p
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                if len(p.data.polygons) > 300:
                    rocks.append(p)
                p.location = (50, 50, 0)  # park the sources far away
    out = []
    def put(x, y, size, flat):
        src = random.choice(rocks)
        s = size / max(src.dimensions.x, src.dimensions.y)
        o = place(src, (x, y, 0), s, random.uniform(0, math.tau), 'rock')
        o.scale.z *= flat
        o.location.z = ground_at(x, y) + src.dimensions.z * s * flat * 0.25
        out.append(o)
    for (x, y) in STEPS:
        put(x + random.uniform(-0.005, 0.005), y, random.uniform(0.045, 0.058), 0.4)
    for bx, by in [(-0.12, 0.12), (0.16, 0.1), (-0.09, -0.03), (0.13, -0.04), (0.06, 0.17)]:
        put(POOL[0] + bx, POOL[1] + by, random.uniform(0.05, 0.09), 0.8)
    for x, y in STREAM[3::4]:
        put(x + random.choice((-0.05, 0.05)), y, random.uniform(0.025, 0.045), 0.6)
    return out

# ---------------------------------------------------------------- layer 5: trees
def build_trees():
    firs = append('fir_tree_01/blend/*.blend', ['fir_tree_01_a_LOD1', 'fir_tree_01_b_LOD1', 'fir_tree_01_c_LOD1'])
    saplings = append('fir_sapling/blend/*.blend', ['fir_sapling_a', 'fir_sapling_b', 'fir_sapling_c'])
    srcs = list(firs.values()); saps = list(saplings.values())
    placed = []
    tries = 0
    while len(placed) < 70 and tries < 6000:
        tries += 1
        a = random.uniform(0, math.tau); rr = math.sqrt(random.random()) * EDGE * 0.92
        x, y = math.cos(a) * rr, math.sin(a) * rr
        back = max(0, min(1.3, 0.5 + y))
        if random.random() > back * 0.9:
            continue
        if abs(x - FALL_X) < 0.16 and -0.05 < y < 0.42:
            continue
        if not free(x, y, 0.07, 0.9):
            continue
        if any(math.hypot(x - px, y - py) < 0.045 for px, py, _ in placed):
            continue
        z = ground_at(x, y) - 0.005
        h = 0.14 + random.random() * 0.2 + back * 0.08
        top_lim = math.sqrt(max(0, INNER * INNER * 0.86 - x * x - y * y))
        h = min(h, top_lim - z)
        if h < 0.07:
            continue
        if (h < 0.2 or random.random() < 0.4) and saps:
            src = random.choice(saps)
        else:
            src = random.choice(srcs)
        s = h / src.dimensions.z
        place(src, (x, y, z), s, random.uniform(0, math.tau), 'tree', tilt=0.04)
        placed.append((x, y, h))
    return placed

# ---------------------------------------------------------------- layer 6: ferns & moss
def build_ground_cover():
    ferns = append('fern_02/blend/*.blend', ['fern_02*'])
    srcs = [o for o in ferns.values() if o.type == 'MESH']
    n = 0
    for _ in range(600):
        if n >= 26 or not srcs:
            break
        a = random.uniform(0, math.tau); rr = math.sqrt(random.random()) * EDGE * 0.9
        x, y = math.cos(a) * rr, math.sin(a) * rr
        near_water = poly_dist(x, y, STREAM) < 0.12 or math.hypot(x - POOL[0], y - POOL[1]) < 0.2
        if not free(x, y, 0.05, 0.5) or (not near_water and random.random() < 0.6):
            continue
        src = random.choice(srcs)
        s = random.uniform(0.05, 0.08) / max(src.dimensions.x, src.dimensions.y)
        place(src, (x, y, ground_at(x, y) - 0.002), s, random.uniform(0, math.tau), 'fern')
        n += 1

def build_moss(terrain):
    """Moss as a short hair system on the terrain, densest on gentle slopes."""
    me = terrain.data
    vg = terrain.vertex_groups.new(name='moss')
    for v in me.vertices:
        x, y, _ = v.co
        s = slope_at(x, y)
        bed = poly_dist(x, y, STREAM) < 0.05 or math.hypot(x - POOL[0], y - POOL[1]) < 0.1
        w = 0.0 if bed else max(0.0, min(1.0, (0.7 - s) / 0.5))
        w *= 0.6 + 0.4 * max(0, fbm(x * 9, 3, y * 9) + 0.5)
        vg.add([v.index], w, 'REPLACE')
    ps = terrain.modifiers.new('moss', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.type = 'HAIR'
    st.count = 60000
    st.hair_length = 0.014
    st.emit_from = 'FACE'
    st.use_advanced_hair = True
    st.use_rotations = True
    st.factor_random = 0.003
    st.brownian_factor = 0.0
    st.radius_scale = 1.0
    st.root_radius = 0.0011
    st.tip_radius = 0.0002
    st.length_random = 0.6
    st.child_type = 'INTERPOLATED'
    st.rendered_child_count = 8
    st.child_radius = 0.01
    st.clump_factor = 0.4
    ps.vertex_group_density = 'moss'
    ps.vertex_group_length = 'moss'
    mm = bpy.data.materials.new('moss'); mm.use_nodes = True  # noqa
    nt = mm.node_tree; N = nt.nodes
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    hair = N.new('ShaderNodeBsdfHairPrincipled')
    hair.parametrization = 'COLOR'
    info = N.new('ShaderNodeHairInfo')
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.03, 0.08, 0.01, 1)
    ramp.color_ramp.elements[1].color = (0.32, 0.5, 0.06, 1)
    nt.links.new(info.outputs['Intercept'], ramp.inputs['Fac'])
    # Colour variation by position (yellow and rust patches).
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
    tc = N.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    pal = N.new('ShaderNodeValToRGB')
    pe = pal.color_ramp.elements
    pe[0].position = 0.35; pe[0].color = (1, 1, 1, 1)
    pe[1].position = 0.7; pe[1].color = (1.6, 1.15, 0.4, 1)
    rust = pal.color_ramp.elements.new(0.78); rust.color = (1.4, 0.5, 0.15, 1)
    nt.links.new(nz.outputs['Fac'], pal.inputs['Fac'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    nt.links.new(ramp.outputs['Color'], mul.inputs[6]); nt.links.new(pal.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], hair.inputs['Color'])
    hair.inputs['Roughness'].default_value = 0.6
    nt.links.new(hair.outputs['BSDF'], N['Material Output'].inputs['Surface'])
    terrain.data.materials.append(mm)
    st.material = len(terrain.data.materials)

# ---------------------------------------------------------------- lighting + camera + render
def setup_render(hdri):
    w = bpy.data.worlds.new('w'); scene.world = w; w.use_nodes = True
    nt = w.node_tree
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdri)
    bg = nt.nodes['Background']; bg.inputs['Strength'].default_value = 0.45
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    # Camera sees plain warm paper; everything else is lit by the HDRI.
    lp = nt.nodes.new('ShaderNodeLightPath')
    paper = nt.nodes.new('ShaderNodeBackground'); paper.inputs['Color'].default_value = (0.86, 0.82, 0.75, 1); paper.inputs['Strength'].default_value = 1.0
    mixs = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mixs.inputs['Fac'])
    nt.links.new(bg.outputs['Background'], mixs.inputs[1]); nt.links.new(paper.outputs['Background'], mixs.inputs[2])
    nt.links.new(mixs.outputs['Shader'], nt.nodes['World Output'].inputs['Surface'])
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 6.0; sun.color = (1.0, 0.78, 0.5); sun.angle = math.radians(2)
    so = bpy.data.objects.new('sun', sun); scene.collection.objects.link(so)
    # Low, from the back-left, matching the web scene's golden key.
    so.rotation_euler = (math.radians(68), 0, math.radians(-140))
    cam = bpy.data.cameras.new('cam'); cam.lens = 50
    co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co)
    co.location = (0.0, -2.9, 0.55)
    look = Vector((0, 0.05, -0.2))
    co.rotation_euler = (look - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    cam.dof.use_dof = True; cam.dof.focus_distance = 2.9; cam.dof.aperture_fstop = 2.8
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(os.environ.get('SAMPLES', 48))
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = int(os.environ.get('RES', 1000)), int(int(os.environ.get('RES', 1000)) * 0.8)
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4

if __name__ == '__main__':
    soil = build_soil()
    terrain = build_terrain()
    build_water()
    build_rocks()
    trees = build_trees()
    build_ground_cover()
    build_moss(terrain)
    setup_render(os.path.join(ASSETS, 'hdri', 'sunset_forest_2k.hdr'))
    missing = [i.filepath for i in bpy.data.images if i.source == 'FILE' and not os.path.exists(bpy.path.abspath(i.filepath))]
    print('trees', len(trees), 'missing images', missing[:5])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'interior.blend'))
    if MODE in ('render', 'both'):
        scene.render.filepath = os.path.join(OUT, 'reference.png')
        bpy.ops.render.render(write_still=True)
        print('rendered')
