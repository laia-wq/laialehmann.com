"""
Turn the Blender world (world.blend from build_world.py) into web assets:

  public/world/static.glb      every solid thing (terrain, rock, buildings,
                               bridges, cave, well...) merged and UV-packed,
                               with Cycles lighting baked into textures
  public/world/static_*.webp   the baked lightmaps
  public/world/water.glb       lake, pond, stream and waterfall sheets
                               (the site shades these live)
  public/world/cards_*.webp    vegetation impostor atlases (each plant
                               rendered from two sides with transparency)
  public/world/world.json      every plant instance, glow light, mist plume,
                               plus a heightmap for the snow

Usage: python export_web.py <world.blend> <out-dir> [--fast]
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
BLEND, OUT = ARGS[-2], ARGS[-1]
FAST = '--fast' in sys.argv
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'

VEG_TAGS = {'tree', 'maple', 'flower', 'grass', 'fern', 'weed', 'groundcover', 'garden', 'shrub', 'leafy_tree'}
WATER_PREFIX = ('water_', 'waterfall')
SKIP_PREFIX = ('mist', 'foam', 'spring_')

def tag(o):
    return o.get('tag') or ''

# ------------------------------------------------------------------ glows, mist, heightmap
glows = []
for o in scene.objects:
    if o.type == 'LIGHT' and o.data.type == 'POINT':
        c = o.data.color
        glows.append({'p': list(o.matrix_world.translation), 'c': [c.r, c.g, c.b], 'e': o.data.energy,
                      'k': o.name.split('.')[0]})
mists = []
for o in scene.objects:
    if o.name.startswith('mist'):
        mists.append({'p': list(o.matrix_world.translation), 's': list(o.scale), 'n': o.name})

def ground_z(x, y, terrain, depsgraph):
    hit, loc, *_ = scene.ray_cast(depsgraph, Vector((x, y, 2.0)), Vector((0, 0, -1)))
    return loc.z if hit else None

terrain = bpy.data.objects['terrain']
dg = bpy.context.evaluated_depsgraph_get()
# Heightmap over the disc, terrain only (temporarily hide everything else).
hidden = []
for o in scene.objects:
    if o is not terrain and o.type == 'MESH' and not o.hide_get():
        o.hide_viewport = True; hidden.append(o)
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
HM = 128
EXT = 0.86
hmap = []
for j in range(HM):
    row = []
    for i in range(HM):
        x = -EXT + 2 * EXT * i / (HM - 1); y = -EXT + 2 * EXT * j / (HM - 1)
        z = ground_z(x, y, terrain, dg)
        row.append(round(z, 4) if z is not None else None)
    hmap.append(row)
for o in hidden:
    o.hide_viewport = False
bpy.context.view_layer.update()

# ------------------------------------------------------------------ vegetation impostors
veg = [o for o in scene.objects if o.type == 'MESH' and tag(o) in VEG_TAGS]
sources = {}
for o in veg:
    sources.setdefault(o.data.name, o)

card_scene = bpy.data.scenes.new('cards')
card_scene.render.engine = 'CYCLES'; card_scene.cycles.device = 'CPU'
card_scene.cycles.samples = 8 if FAST else 24; card_scene.cycles.use_denoising = True
card_scene.render.film_transparent = True
card_scene.view_settings.view_transform = 'Standard'
cw = bpy.data.worlds.new('card_world'); card_scene.world = cw; cw.use_nodes = True
cw.node_tree.nodes['Background'].inputs['Color'].default_value = (1.0, 0.75, 0.68, 1)
cw.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
for nm in ('sun', 'sky_fill'):
    if nm in bpy.data.objects:
        card_scene.collection.objects.link(bpy.data.objects[nm])
cam_d = bpy.data.cameras.new('card_cam'); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new('card_cam', cam_d); card_scene.collection.objects.link(cam); card_scene.camera = cam

def bbox_local(o):
    vs = [Vector(c) for c in o.bound_box]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return mn, mx

cards = []  # one per source per view
CELL = {'tree': (192, 384), 'small': (128, 128)}
tmp_files = []
for idx, (dname, src) in enumerate(sources.items()):
    kind = 'tree' if tag(src) in ('tree', 'maple') else 'small'
    t = bpy.data.objects.new('card_tmp', src.data)
    card_scene.collection.objects.link(t)
    co = np.empty(len(src.data.vertices) * 3, dtype=np.float32); src.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mn, mx = Vector(co.min(0)), Vector(co.max(0))
    W, H = CELL[kind]
    entry = {'src': dname, 'kind': kind, 'views': []}
    for view in range(2):
        if view == 0:
            hmin, hmax = mn.x, mx.x
        else:
            hmin, hmax = mn.y, mx.y
        w, h = max(hmax - hmin, 1e-4), max(mx.z - mn.z, 1e-4)
        # Ortho scale spans the larger render dimension.
        if H >= W:
            ortho = max(h, w * H / W) * 1.02; fh = ortho; fw = ortho * W / H
        else:
            ortho = max(w, h * W / H) * 1.02; fw = ortho; fh = ortho * H / W
        cam_d.ortho_scale = ortho
        cx = (hmin + hmax) / 2; cz = (mn.z + mx.z) / 2
        if view == 0:
            cam.location = (cx, mn.y - 5, cz); cam.rotation_euler = (math.pi / 2, 0, 0)
        else:
            cam.location = (mx.x + 5, cx, cz); cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
        cam_d.clip_end = 20
        card_scene.render.resolution_x, card_scene.render.resolution_y = W, H
        fp = os.path.join(OUT, f'_card_{idx}_{view}.png')
        card_scene.render.filepath = fp
        bpy.ops.render.render(write_still=True, scene=card_scene.name)
        tmp_files.append(fp)
        entry['views'].append({'file': fp, 'cx': cx, 'cz': cz, 'fw': fw, 'fh': fh})
    entry['kind'] = kind
    cards.append(entry)
    card_scene.collection.objects.unlink(t); bpy.data.objects.remove(t)
    print('card', idx, len(sources), dname, flush=True)

# Pack atlases.
def load_png(fp):
    im = bpy.data.images.load(fp)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im)
    return a

def save_webp(arr, path):
    h, w, _ = arr.shape
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    im.pixels.foreach_set(arr.reshape(-1).astype(np.float32))
    im.filepath_raw = path.replace('.webp', '.png'); im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    return path.replace('.webp', '.png')

atlases = {}
for kind, (W, H) in CELL.items():
    items = [(ci, vi) for ci, c in enumerate(cards) if c['kind'] == kind for vi in range(2)]
    if not items:
        continue
    cols = max(1, int(4096 // W)) if kind == 'tree' else 16
    rows = math.ceil(len(items) / cols)
    A = np.zeros((rows * H, cols * W, 4), dtype=np.float32)
    for n, (ci, vi) in enumerate(items):
        r, c = divmod(n, cols)
        px = load_png(cards[ci]['views'][vi]['file'])
        # numpy rows go bottom-up in Blender pixel order; keep that order consistently.
        A[r * H:(r + 1) * H, c * W:(c + 1) * W] = px
        v = cards[ci]['views'][vi]
        v['uv'] = [c * W / A.shape[1], r * H / A.shape[0], W / A.shape[1], H / A.shape[0]]
        v['atlas'] = kind
    atlases[kind] = save_webp(A, os.path.join(OUT, f'cards_{kind}.webp'))
for fp in tmp_files:
    os.remove(fp)

src_index = {c['src']: i for i, c in enumerate(cards)}
instances = []
for o in veg:
    loc = o.matrix_world.translation
    instances.append([src_index[o.data.name], round(loc.x, 4), round(loc.y, 4), round(loc.z, 4),
                      round(o.matrix_world.to_scale().x, 4), round(o.matrix_world.to_euler().z, 3)])

# ------------------------------------------------------------------ static geometry + lightmaps
def collect_static():
    objs = []
    for o in scene.objects:
        if o.hide_render or o.type not in ('MESH', 'CURVE'):
            continue
        if tag(o) in VEG_TAGS or o.name.startswith(WATER_PREFIX) or o.name.startswith(SKIP_PREFIX) or tag(o) == 'fairy':
            continue
        if o.name == 'terrain':
            continue
        objs.append(o)
    return objs

def make_real(objs, name):
    """Duplicate, apply modifiers / convert curves, join into one mesh."""
    bpy.ops.object.select_all(action='DESELECT')
    dups = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        if not me.polygons:
            continue
        me.transform(o.matrix_world)
        d = bpy.data.objects.new(name + '_part', me)
        scene.collection.objects.link(d)
        dups.append(d)
    for d in dups:
        d.select_set(True)
    bpy.context.view_layer.objects.active = dups[0]
    bpy.ops.object.join()
    j = bpy.context.object; j.name = name
    return j

def bake(obj, size, uv_name, path, samples):
    img = bpy.data.images.new(os.path.basename(path), size, size, alpha=False, float_buffer=False)
    for m in obj.data.materials:
        if not m:
            continue
        m.use_nodes = True
        n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; n.name = '__bake'
        m.node_tree.nodes.active = n
    obj.data.uv_layers.active = obj.data.uv_layers[uv_name]
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    scene.cycles.samples = samples
    scene.render.bake.margin = 4
    # Mist volumes would fog the bake; hide them.
    for o in scene.objects:
        if o.name.startswith(('mist', 'foam')):
            o.hide_render = True
    bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'EMIT'})
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    return img

def single_material(obj, img_path, name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img_path)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    obj.data.materials.clear(); obj.data.materials.append(m)
    for p in obj.data.polygons:
        p.material_index = 0

stat = collect_static()
S = make_real(stat, 'static')
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003)
bpy.ops.object.mode_set(mode='OBJECT')
uvn = S.data.uv_layers.active.name
LM = 1024 if FAST else 2048
bake(S, LM, uvn, os.path.join(OUT, 'static_bake.png'), 4 if FAST else 16)
for o in stat:
    o.hide_render = True  # avoid double-occluding the terrain bake? keep visible instead
    o.hide_render = False

# Terrain bake on its planar UV.
T = make_real([terrain], 'terrain_bake')
for uv in T.data.uv_layers:
    pass
if 'UVMap' not in T.data.uv_layers:
    T.data.uv_layers.new(name='UVMap')
# soil has no planar UV: give everything a fresh smart-projected atlas for the soil part only would be complex;
# instead re-project planar UVs for all vertices of the joined mesh.
EDGE = max(abs(v.co.x) for v in T.data.vertices)
uvl = T.data.uv_layers['UVMap']
for poly in T.data.polygons:
    for li in poly.loop_indices:
        co = T.data.vertices[T.data.loops[li].vertex_index].co
        uvl.data[li].uv = (co.x / (2 * EDGE) + 0.5, co.y / (2 * EDGE) + 0.5)
terrain.hide_render = True
TM = 1024 if FAST else 2048
bake(T, TM, 'UVMap', os.path.join(OUT, 'terrain_bake.png'), 4 if FAST else 16)

single_material(S, os.path.join(OUT, 'static_bake.png'), 'static_baked')
single_material(T, os.path.join(OUT, 'terrain_bake.png'), 'terrain_baked')

def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format='GLB', export_apply=True,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT',
                              export_image_format='AUTO', export_yup=True)

export([S, T], os.path.join(OUT, 'static.glb'))
water = [o for o in scene.objects if o.type == 'MESH' and o.name.startswith(WATER_PREFIX)]
for o in water:
    o.data.materials.clear()
export(water, os.path.join(OUT, 'water.glb'))

json.dump({
    'cards': [{'kind': c['kind'], 'views': [{k: v[k] for k in ('cx', 'cz', 'fw', 'fh', 'uv')} for v in c['views']]} for c in cards],
    'instances': instances,
    'glows': glows,
    'mists': mists,
    'heightmap': {'n': HM, 'ext': EXT, 'z': hmap},
}, open(os.path.join(OUT, 'world.json'), 'w'), separators=(',', ':'))
print('EXPORTED', len(cards), 'cards', len(instances), 'instances', len(glows), 'glows')
