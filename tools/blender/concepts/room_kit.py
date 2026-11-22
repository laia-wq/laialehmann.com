"""Shared pieces for the project rooms: a dollhouse cutaway (floor plus the two
far walls, seen from the same corner as the canal), chalk/painted lettering,
little screens drawn pixel by pixel, and the web export (hotspot masks +
scene.json), mirroring canal_final.py so the browser can treat a room exactly
like the street."""
import os, math, json
import bpy
from mathutils import Vector
from kit import solid, varied, wood, box, cyl, sphere, cut, node_mat, link, iso_camera, render

MARKER = os.environ.get('MARKER_FONT', '')


def shell(w, d, h, wall_mat, floor_mat, trim_mat):
    """Floor w×d (x from 0, y from 0) and the two far walls (x=0 and y=d),
    with a wainscot rail and skirting."""
    box('floor', (w / 2, d / 2, -0.04), (w, d, 0.08), floor_mat, bevel=0)
    box('wall_w', (-0.06, d / 2, h / 2), (0.12, d + 0.12, h), wall_mat, bevel=0)
    box('wall_n', (w / 2, d + 0.06, h / 2), (w + 0.12, 0.12, h), wall_mat, bevel=0)
    for (loc, size) in (((0.012, d / 2, 0.06), (0.025, d, 0.12)), ((w / 2, d - 0.012, 0.06), (w, 0.025, 0.12))):
        box('skirting', loc, size, trim_mat, bevel=0.004)
    for (loc, size) in (((0.015, d / 2, 0.85), (0.03, d, 0.04)), ((w / 2, d - 0.015, 0.85), (w, 0.03, 0.04))):
        box('dado_rail', loc, size, trim_mat, bevel=0.006)
    # cut faces of the dollhouse: a neat dark edge where the walls stop
    edge = solid('cut_edge', (0.1, 0.08, 0.07), 0.9)
    box('cut_w', (-0.06, -0.005, h / 2), (0.125, 0.012, h), edge, bevel=0)
    box('cut_n', (w + 0.005, d + 0.06, h / 2), (0.012, 0.125, h), edge, bevel=0)
    box('cut_f1', (w / 2, -0.005, -0.04), (w, 0.012, 0.085), edge, bevel=0)
    box('cut_f2', (w + 0.005, d / 2, -0.04), (0.012, d, 0.085), edge, bevel=0)


def label(text, loc, size, mat, rot=(math.pi / 2, 0, 0), align='CENTER', font=None, extrude=0.0015, name='label'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = text
    f = font or MARKER
    if f: cu.font = bpy.data.fonts.load(f, check_existing=True)
    cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'; cu.extrude = extrude
    o = link(bpy.data.objects.new(name, cu)); o.location = loc; o.rotation_euler = rot
    cu.materials.append(mat)
    return o


def screen_image(name, w, h, draw):
    """A tiny screen texture, drawn by `draw(px, w, h)` into an RGBA float list
    (row 0 = bottom). Returned as an emissive material."""
    img = bpy.data.images.new(name, w, h)
    px = [0.0] * (w * h * 4)
    draw(px, w, h)
    img.pixels = px
    m, n, l, b = node_mat(name)
    t = n.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Closest'
    l.new(t.outputs['Color'], b.inputs['Base Color']); l.new(t.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 1.6; b.inputs['Roughness'].default_value = 0.2
    return m


def rect(px, w, h, x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            i = (y * w + x) * 4
            px[i:i + 4] = [c[0], c[1], c[2], 1.0]


def plane_with(name, loc, size, mat, rot):
    """A flat quad (for screens and pictures) with UVs 0..1."""
    me = bpy.data.meshes.new(name)
    sx, sy = size[0] / 2, size[1] / 2
    me.from_pydata([(-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[i].uv = c
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    return o


class Group:
    """Collects the objects made inside a `with` block under one hotspot."""
    all = {}
    def __init__(self, name): self.name = name
    def __enter__(self): self.before = set(bpy.data.objects.keys())
    def __exit__(self, *a):
        Group.all.setdefault(self.name, set()).update(set(bpy.data.objects.keys()) - self.before)


def export_web(sc, cam, out, size=(1400, 1050)):
    """Hotspot masks (one per Group) + scene.json with the room's lights."""
    from bpy_extras.object_utils import world_to_camera_view
    os.makedirs(out, exist_ok=True)
    lights = []
    for o in sc.objects:
        if o.type == 'LIGHT' and o.data.type == 'POINT':
            v = world_to_camera_view(sc, cam, o.matrix_world.translation)
            if 0 <= v.x <= 1 and 0 <= v.y <= 1:
                lights.append({'x': round(v.x, 4), 'y': round(1 - v.y, 4), 'k': o.name.split('.')[0], 'c': [round(c, 3) for c in o.data.color], 'e': round(o.data.energy, 2)})
    geo = [o for o in sc.objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.hide_render]
    r = sc.render
    r.film_transparent = True; sc.cycles.use_denoising = False
    r.resolution_x, r.resolution_y = size
    names = list(Group.all)
    for g in names:
        keep = Group.all[g]
        for o in geo: o.is_holdout = o.name not in keep
        render(sc, os.path.join(out, 'mask_' + g + '.png'), 6)
    for o in geo: o.is_holdout = False
    json.dump({'size': list(size), 'lights': lights, 'groups': names}, open(os.path.join(out, 'scene.json'), 'w'), separators=(',', ':'))
    print('ROOM EXPORT', names, len(lights), 'lights')
