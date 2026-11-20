"""
Export the world's vegetation as real 3D meshes for the browser (replaces
the flat impostor cards).

  veg/veg.glb      one mesh per unique plant shape, LOD0 (detailed, capped
                   at ~40k triangles) and LOD1 (~10%, for distant views);
                   Z-up, materials are placeholders named slot0, slot1...
  veg/*.png        each plant material's final colour (Blender's node
                   graph, including the autumn recolour ramps, baked flat
                   through a UV-space plane) with the leaf cut-out in alpha
  veg.json         prototypes (geometry + per-slot material), materials,
                   and every instance's full transform

Usage: python export_veg.py <world.blend> <out-dir> [--fast]
"""
import bpy, sys, os, json, math, hashlib
import numpy as np

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
BLEND, OUT = ARGS[-2], ARGS[-1]
FAST = '--fast' in sys.argv
VD = os.path.join(OUT, 'veg')
os.makedirs(VD, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1 if FAST else 4
scene.cycles.use_denoising = False

VEG_TAGS = {'tree', 'maple', 'flower', 'grass', 'fern', 'weed', 'groundcover', 'garden', 'shrub', 'leafy_tree'}
LOD0_MAX = 40000
LOD1_FRAC = 0.15
LOD1_MIN_TRIS = 8000

veg = [o for o in scene.objects if o.type == 'MESH' and (o.get('tag') or '') in VEG_TAGS]
sources = {}
for o in veg:
    sources.setdefault(o.data.name, o)
print('veg objects', len(veg), 'prototypes', len(sources), flush=True)

def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

# ------------------------------------------------------------------ material colour bake
def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)

def principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None

def to_emission(nt, out_socket):
    """Route the principled Base Color (whatever feeds it) into an Emission
    shader wired to `out_socket`. Returns False if no principled found."""
    P = principled(nt)
    if not P:
        return False
    E = nt.nodes.new('ShaderNodeEmission')
    bc = P.inputs['Base Color']
    if bc.is_linked:
        nt.links.new(bc.links[0].from_socket, E.inputs['Color'])
    else:
        E.inputs['Color'].default_value = bc.default_value
    nt.links.new(E.outputs['Emission'], out_socket)
    return True

def out_node(nt):
    outs = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL']
    act = [n for n in outs if n.is_active_output]
    return (act or outs)[0]

def images(nt):
    return [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]

def img_array(im, size):
    if tuple(im.size) != (size, size):
        im = im.copy(); im.scale(size, size)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], im.channels)
    return a

ATTR_NAMES = set()
for o in sources.values():
    for m in o.data.materials:
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'ATTRIBUTE' and n.attribute_name != 'UVMap':
                    ATTR_NAMES.add(n.attribute_name)

# A unit plane whose geometry *is* UV space: baking a material onto it
# captures the texture's final colour everywhere, no overlap issues.
pm = bpy.data.meshes.new('uvplane')
pm.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
uv = pm.uv_layers.new(name='UVMap')
for li, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
    uv.data[li].uv = (u, v)
for nm in ATTR_NAMES:
    a = pm.color_attributes.new(nm, 'BYTE_COLOR', 'CORNER')
    for d in a.data:
        d.color = (1, 1, 1, 1)
plane = bpy.data.objects.new('uvplane', pm)
plane.location = (50, 50, 50)
scene.collection.objects.link(plane)

materials = {}  # material name -> {'tex': file | None, 'color': [...], 'alpha': bool, 'vc': bool}

def bake_material(m):
    key = m.name
    if key in materials:
        return key
    nt = m.node_tree
    vc = any(n.type == 'ATTRIBUTE' and n.attribute_name == 'leaf_col' for n in nt.nodes) if nt else False
    imgs = images(nt) if nt else []
    if not imgs:
        P = principled(nt) if nt else None
        c = list(P.inputs['Base Color'].default_value)[:3] if P else [0.5, 0.5, 0.5]
        materials[key] = {'tex': None, 'color': [round(float(x), 4) for x in lin2srgb(np.array(c))], 'alpha': False, 'vc': vc}
        return key
    size = min(1024, max(max(i.image.size[0], i.image.size[1]) for i in imgs))
    if FAST:
        size = min(size, 256)
    mb = m.copy()
    bnt = mb.node_tree
    # Attribute nodes reading the UV map by name don't resolve on the bake
    # plane: swap them for a real UV Map node.
    for n in [n for n in bnt.nodes if n.type == 'ATTRIBUTE' and n.attribute_name == 'UVMap']:
        uvn = bnt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
        for out_name in ('Vector', 'Color'):
            for l in list(n.outputs[out_name].links):
                bnt.links.new(uvn.outputs['UV'], l.to_socket)
    out = out_node(bnt)
    ok = to_emission(bnt, out.inputs['Surface'])
    if not ok:
        src = out.inputs['Surface'].links[0].from_node if out.inputs['Surface'].is_linked else None
        if src is not None and src.type == 'GROUP':
            g = src.node_tree.copy(); src.node_tree = g
            gout = [n for n in g.nodes if n.type == 'GROUP_OUTPUT'][0]
            sock = [s for s in gout.inputs if s.type == 'SHADER'][0]
            ok = to_emission(g, sock)
    if not ok:
        print('  !! no principled in', key, flush=True)
    img = bpy.data.images.new('bake_' + key, size, size, alpha=True, float_buffer=True)
    t = bnt.nodes.new('ShaderNodeTexImage'); t.image = img
    bnt.nodes.active = t
    plane.data.materials.clear(); plane.data.materials.append(mb)
    bpy.ops.object.select_all(action='DESELECT')
    plane.select_set(True); bpy.context.view_layer.objects.active = plane
    bpy.ops.object.bake(type='EMIT', margin=0, use_clear=True)
    rgb = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)[..., :3]
    # Alpha: a dedicated *_alpha / opacity image, else an image's own alpha.
    alpha = None
    for n in imgs:
        nm = n.image.name.lower()
        if 'alpha' in nm or 'opacity' in nm:
            alpha = img_array(n.image, size)[..., 0]; break
    if alpha is None:
        for n in imgs:
            if n.outputs['Alpha'].is_linked:
                alpha = img_array(n.image, size)[..., 3]; break
    has_alpha = alpha is not None and float(alpha.min()) < 0.5
    if alpha is None:
        alpha = np.ones((size, size), np.float32)
    rgba = np.concatenate([lin2srgb(rgb), alpha[..., None]], -1)
    fn = ''.join(ch if ch.isalnum() else '_' for ch in key) + '.png'
    sv = bpy.data.images.new(fn, size, size, alpha=True)
    sv.pixels.foreach_set(rgba.reshape(-1).astype(np.float32))
    sv.filepath_raw = os.path.join(VD, fn); sv.file_format = 'PNG'; sv.save()
    bpy.data.images.remove(sv); bpy.data.images.remove(img)
    bpy.data.materials.remove(mb)
    materials[key] = {'tex': fn, 'alpha': has_alpha, 'vc': vc}
    print('  baked', key, size, 'alpha' if has_alpha else '', flush=True)
    return key

# ------------------------------------------------------------------ geometry
def geom_key(me):
    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get('co', co)
    h = hashlib.md5(np.round(co[:600], 4).tobytes()).hexdigest()[:10]
    return f'{len(me.vertices)}_{len(me.polygons)}_{len(me.materials)}_{h}'

slot_mats = [bpy.data.materials.new(f'slot{i}') for i in range(8)]
geoms = {}       # key -> {'lod0': name, 'lod1': name, 'tris': [..], 'h': height}
protos = []      # index -> {'geom': key, 'mats': [...]}
proto_index = {}
export_objs = []

def fix_uv(me):
    """Some assets store UVs as a FLOAT_VECTOR corner attribute; glTF needs a UV layer."""
    if len(me.uv_layers):
        return
    a = me.attributes.get('UVMap')
    if a is None:
        return
    d = np.empty(len(me.loops) * 3, dtype=np.float32); a.data.foreach_get('vector', d)
    me.attributes.remove(a)
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', d.reshape(-1, 3)[:, :2].reshape(-1))

def make_lod(src_me, name, target):
    me = src_me.copy(); me.name = name
    fix_uv(me)
    for ca in list(me.color_attributes):
        if ca.name != 'leaf_col':
            me.color_attributes.remove(ca)
    if 'leaf_col' in me.color_attributes:
        me.color_attributes.active_color = me.color_attributes['leaf_col']
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    n = len(me.materials)
    me.materials.clear()
    for i in range(n):
        me.materials.append(slot_mats[i])
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    t = tris(me)
    if target < t:
        md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = target / t; md.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        nm = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        o.modifiers.clear(); o.data = nm; nm.name = name
    return o, tris(o.data)

for i, (dname, src) in enumerate(sources.items()):
    k = geom_key(src.data)
    if k not in geoms:
        t = tris(src.data)
        gid = f'g{len(geoms)}'
        o0, t0 = make_lod(src.data, gid, min(t, LOD0_MAX))
        export_objs.append(o0)
        entry = {'id': gid, 'tris': [t0], 'lod1': None}
        if t >= LOD1_MIN_TRIS:
            o1, t1 = make_lod(src.data, gid + '_lod1', int(t * LOD1_FRAC))
            export_objs.append(o1); entry['lod1'] = gid + '_lod1'; entry['tris'].append(t1)
        geoms[k] = entry
        print('geom', gid, t, '->', entry['tris'], flush=True)
    proto_index[dname] = len(protos)
    protos.append({'geom': geoms[k]['id'], 'mats': [m.name if m else None for m in src.data.materials], 'tag': src.get('tag') or ''})

# Material bakes: hide everything else so Cycles doesn't rebuild the whole
# 16M-triangle scene for every little texture.
was = {o.name: o.hide_render for o in scene.objects}
for o in scene.objects:
    o.hide_render = o is not plane
for src in sources.values():
    for m in src.data.materials:
        if m:
            bake_material(m)
for o in scene.objects:
    o.hide_render = was.get(o.name, False)
plane.hide_render = True

bpy.ops.object.select_all(action='DESELECT')
for o in export_objs:
    o.location = (0, 0, 0)
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(VD, 'veg.glb'), use_selection=True, export_format='GLB',
                          export_apply=False, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_vertex_color='ACTIVE',
                          export_all_vertex_colors=False, export_yup=False)

instances = []
for o in veg:
    m = o.matrix_world
    loc, rot, sc = m.decompose()
    instances.append([proto_index[o.data.name],
                      *[round(v, 4) for v in loc], *[round(v, 4) for v in (rot.x, rot.y, rot.z, rot.w)],
                      *[round(v, 4) for v in sc]])

json.dump({
    'geoms': {e['id']: {'lod1': e['lod1'], 'tris': e['tris']} for e in geoms.values()},
    'protos': protos,
    'materials': materials,
    'instances': instances,
}, open(os.path.join(OUT, 'veg.json'), 'w'), separators=(',', ':'))
print('EXPORTED', len(geoms), 'geoms', len(protos), 'protos', len(materials), 'materials', len(instances), 'instances',
      'tris@lod0', sum(geoms_t['tris'][0] for geoms_t in geoms.values()), flush=True)
