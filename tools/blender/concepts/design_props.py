"""Three things on the sills of the tall house's top-floor windows, one per
design team. Each is what a student team actually has lying around: built by
hand, a bit scrappy, not a product.

  WARG            a small quadcopter frame (carbon arms, motors, a flight
                  controller stack, a yellow LiPo on a velcro strap), leaning
                  against the glass so you see it face on
  MedTechResolve  a toy pickup truck with a camera module zip-tied to its cab
                  roof, ribbon cable down to a little board taped in the bed
  Reality Labs    a 3D-printed headset prototype: orange PLA with layer lines,
                  a bare green board screwed to the front, an IMU breakout and
                  a ribbon cable, foam gasket, a strip of painter's tape

All names start with 'dt_' so the close-up can tell them from the street's
own window props.
"""
import math
import bpy
from mathutils import Vector, Matrix
from kit import solid, varied, node_mat, box, cyl, sphere, link
from canal_extras import limb

# floor 3 of the tall house, its three arched windows (left to right)
A_FACE_Y = 1.25
SILL_Z = 3.98
WIN_U = (-4.2167, -3.45, -2.6833)
WIN_W, WIN_H = 0.42, 0.667
TEAMS = ('warg', 'medtechresolve', 'wrl')


def _frame(origin, yaw=0.0, tilt=0.0):
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'X')
    O = Vector(origin)
    return (lambda x, y, z: O + R @ Vector((x, y, z))), (lambda m=Matrix.Identity(3): (R @ m).to_euler())


def _pcb(name='dt_pcb', col=(0.05, 0.32, 0.12)):
    """Solder mask with copper traces and silkscreen specks."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    v = n.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 220
    l.new(tc.outputs['Object'], v.inputs['Vector'])
    r = n.new('ShaderNodeMapRange'); r.inputs['From Min'].default_value = 0.0; r.inputs['From Max'].default_value = 0.05
    l.new(v.outputs['Distance'], r.inputs['Value'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (0.55, 0.45, 0.2, 1); mix.inputs['B'].default_value = (*col, 1)
    l.new(r.outputs['Result'], mix.inputs['Factor']); l.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.35; b.inputs['Coat Weight'].default_value = 0.3
    return m


def _layered(name, col):
    """3D-printed plastic: fine horizontal layer lines."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    w = n.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'; w.inputs['Scale'].default_value = 900
    w.inputs['Distortion'].default_value = 0.3
    l.new(tc.outputs['Object'], w.inputs['Vector'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.0004
    l.new(w.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = 0.55
    return m


def drone_frame(origin, yaw):
    """A 5-inch quad leaning back against the glass, arms in an X."""
    P, rot = _frame(origin, yaw, math.radians(62))       # leaning back against the glass, top facing out
    carbon = varied('dt_carbon', (0.035, 0.035, 0.04), 0.03, 0.35, bump=0.5, bump_scale=900)
    alu = solid('dt_alu', (0.6, 0.6, 0.62), 0.3, metal=1.0)
    bell = solid('dt_bell', (0.55, 0.08, 0.06), 0.3, metal=0.8)
    prop = solid('dt_prop', (0.95, 0.45, 0.08), 0.35)
    for a in (math.pi / 4, -math.pi / 4):
        b_ = box('dt_arm', P(0, 0.0, 0.0), (0.22, 0.02, 0.005), carbon, bevel=0.002)
        b_.rotation_euler = rot(Matrix.Rotation(a, 3, 'Z'))
    for z in (0.0, 0.026):
        b_ = box('dt_plate', P(0, 0, z), (0.06, 0.05, 0.003), carbon, bevel=0.001); b_.rotation_euler = rot()
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = cyl('dt_standoff', P(sx * 0.022, sy * 0.017, 0.013), 0.0025, 0.026, alu, verts=6); c.rotation_euler = rot()
    b_ = box('dt_fc', P(0, 0, 0.012), (0.032, 0.032, 0.002), _pcb(), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_esc', P(0, 0, 0.006), (0.034, 0.034, 0.002), _pcb('dt_pcb_b', (0.05, 0.08, 0.2)), bevel=0); b_.rotation_euler = rot()
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        mp = P(0.078 * math.cos(a), 0.078 * math.sin(a), 0.0)
        R_ = Matrix.Rotation(a, 3, 'Z')
        c = cyl('dt_motor', mp + rot_vec(rot, (0, 0, 0.009)), 0.012, 0.014, alu, verts=16); c.rotation_euler = rot()
        c = cyl('dt_bell', mp + rot_vec(rot, (0, 0, 0.017)), 0.0125, 0.006, bell, verts=16); c.rotation_euler = rot()
        for sg in (-1, 1):   # two-blade prop, a little pitched
            blade = box('dt_prop', mp + rot_vec(rot, (0, 0, 0.022)) + rot_vec(rot, tuple(R_ @ Vector((sg * 0.03, 0, 0)))), (0.055, 0.011, 0.0015), prop, bevel=0.0008)
            blade.rotation_euler = rot(R_ @ Matrix.Rotation(sg * 0.18, 3, 'X'))
    # the battery on top, strapped down, its lead looping to the stack
    b_ = box('dt_lipo', P(0, 0, 0.042), (0.07, 0.032, 0.022), solid('dt_lipo', (0.92, 0.72, 0.08), 0.5), bevel=0.003); b_.rotation_euler = rot()
    b_ = box('dt_lipo_label', P(0, 0, 0.0535), (0.04, 0.026, 0.001), solid('dt_label', (0.08, 0.08, 0.09), 0.5), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_strap', P(0.008, 0, 0.042), (0.012, 0.036, 0.026), solid('dt_strap', (0.06, 0.06, 0.07), 0.9), bevel=0.002); b_.rotation_euler = rot()
    red, blk = solid('dt_wire_r', (0.7, 0.06, 0.05), 0.4), solid('dt_wire_k', (0.03, 0.03, 0.03), 0.4)
    for m_, dy in ((red, -0.004), (blk, 0.004)):
        limb(P(-0.035, dy, 0.042), P(-0.05, dy, 0.03), 0.0018, m_)
        limb(P(-0.05, dy, 0.03), P(-0.03, dy, 0.015), 0.0018, m_)
    cyl('dt_xt60', P(-0.05, 0, 0.03), 0.004, 0.012, solid('dt_xt60', (0.9, 0.75, 0.1), 0.5), verts=6).rotation_euler = rot()
    # a camera at the nose and a VTX antenna at the tail
    b_ = box('dt_cam', P(0.034, 0, 0.016), (0.016, 0.018, 0.016), solid('dt_cam', (0.05, 0.05, 0.06), 0.4), bevel=0.002); b_.rotation_euler = rot()
    c = cyl('dt_lens', P(0.044, 0, 0.016), 0.006, 0.006, solid('dt_glass', (0.05, 0.08, 0.12), 0.05, coat=1.0), verts=12)
    c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    limb(P(-0.03, 0, 0.026), P(-0.055, 0, 0.07), 0.0015, blk)
    sphere('dt_antenna', P(-0.056, 0, 0.074), 0.006, solid('dt_ant', (0.1, 0.1, 0.12), 0.6), 8)


def rot_vec(rot, v):
    """Rotate a local offset by the frame's rotation (rot() gives an Euler)."""
    return rot().to_matrix() @ Vector(v)


def toy_truck(origin, yaw):
    """A plastic toy pickup with a camera module zip-tied to the cab roof."""
    P, rot = _frame(origin, yaw)
    body = varied('dt_truck', (0.62, 0.1, 0.08), 0.05, 0.4)
    bed_m = varied('dt_truck_bed', (0.85, 0.7, 0.2), 0.05, 0.5)
    tyre = solid('dt_tyre', (0.03, 0.03, 0.03), 0.8)
    hub = solid('dt_hub', (0.85, 0.85, 0.82), 0.4)
    L, Wd = 0.17, 0.075
    b_ = box('dt_chassis', P(0, 0, 0.022), (L, Wd, 0.016), solid('dt_chassis', (0.12, 0.12, 0.13), 0.6), bevel=0.003); b_.rotation_euler = rot()
    b_ = box('dt_hood', P(0.055, 0, 0.042), (0.06, Wd, 0.026), body, bevel=0.008); b_.rotation_euler = rot()
    b_ = box('dt_cab', P(0.012, 0, 0.058), (0.042, Wd - 0.004, 0.058), body, bevel=0.008); b_.rotation_euler = rot()
    for sg in (-1, 1):   # cab windows
        b_ = box('dt_win', P(0.014, sg * (Wd / 2 - 0.001), 0.068), (0.03, 0.003, 0.022), solid('dt_win', (0.1, 0.14, 0.18), 0.1), bevel=0.002); b_.rotation_euler = rot()
    b_ = box('dt_win', P(0.034, 0, 0.068), (0.003, Wd - 0.014, 0.022), solid('dt_win', (0.1, 0.14, 0.18), 0.1), bevel=0.002); b_.rotation_euler = rot()
    # the bed
    b_ = box('dt_bed', P(-0.048, 0, 0.034), (0.07, Wd, 0.006), bed_m, bevel=0.002); b_.rotation_euler = rot()
    for sg in (-1, 1):
        b_ = box('dt_bedside', P(-0.048, sg * (Wd / 2 - 0.003), 0.046), (0.07, 0.006, 0.022), bed_m, bevel=0.002); b_.rotation_euler = rot()
    b_ = box('dt_bedside', P(-0.082, 0, 0.046), (0.006, Wd, 0.022), bed_m, bevel=0.002); b_.rotation_euler = rot()
    for (dx, sg) in ((0.055, 1), (0.055, -1), (-0.05, 1), (-0.05, -1)):
        c = cyl('dt_tyre', P(dx, sg * (Wd / 2 + 0.002), 0.017), 0.017, 0.014, tyre, verts=20); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
        c = cyl('dt_hub', P(dx, sg * (Wd / 2 + 0.009), 0.017), 0.008, 0.002, hub, verts=12); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
    for sg in (-1, 1):
        sphere('dt_headlight', P(0.086, sg * 0.024, 0.044), 0.005, solid('dt_hl', (0.95, 0.92, 0.8), 0.2), 8)
    # the camera module on the roof: a little board, a lens barrel, zip ties
    b_ = box('dt_cam_pcb', P(0.012, 0, 0.0905), (0.028, 0.028, 0.0025), _pcb(), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_cam_block', P(0.018, 0, 0.097), (0.012, 0.012, 0.01), solid('dt_cam', (0.05, 0.05, 0.06), 0.4), bevel=0.001); b_.rotation_euler = rot()
    c = cyl('dt_lens', P(0.03, 0, 0.098), 0.0055, 0.012, solid('dt_cam', (0.05, 0.05, 0.06), 0.4), verts=14); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    c = cyl('dt_glass', P(0.0365, 0, 0.098), 0.004, 0.001, solid('dt_glass', (0.05, 0.08, 0.12), 0.05, coat=1.0), verts=14); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    zip_ = solid('dt_zip', (0.92, 0.92, 0.9), 0.4)
    for dx in (0.002, 0.024):
        b_ = box('dt_zip', P(dx, 0, 0.088), (0.003, Wd - 0.002, 0.002), zip_, bevel=0); b_.rotation_euler = rot()
        for sg in (-1, 1):
            b_ = box('dt_zip', P(dx, sg * (Wd / 2 - 0.001), 0.074), (0.003, 0.002, 0.03), zip_, bevel=0); b_.rotation_euler = rot()
    # ribbon cable down to a small board and a power bank taped into the bed
    rib = solid('dt_ribbon', (0.85, 0.72, 0.4), 0.5)
    pts = [P(-0.002, 0, 0.09), P(-0.016, 0, 0.088), P(-0.03, 0, 0.07), P(-0.04, 0, 0.05)]
    for a, b2 in zip(pts, pts[1:]):
        r_ = box('dt_ribbon', (a + b2) / 2, (0.003, 0.012, (b2 - a).length), rib, bevel=0)
        r_.rotation_euler = (b2 - a).to_track_quat('Z', 'Y').to_euler()
    b_ = box('dt_sbc', P(-0.045, 0, 0.041), (0.05, 0.032, 0.003), _pcb(), bevel=0); b_.rotation_euler = rot()
    for k in range(4):
        b_ = box('dt_chip', P(-0.055 + k * 0.01, 0.006 * (k % 2), 0.0435), (0.006, 0.006, 0.002), solid('dt_chip', (0.03, 0.03, 0.03), 0.4), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_tape', P(-0.045, 0, 0.044), (0.012, Wd + 0.004, 0.0015), solid('dt_tape', (0.25, 0.45, 0.78), 0.7), bevel=0); b_.rotation_euler = rot()


def vr_headset(origin, yaw):
    """A student-built headset: a chunky printed shell, a bare board on the
    front, a purple IMU breakout, a ribbon cable, a foam gasket, an elastic
    strap, and a strip of blue tape holding something together."""
    P, rot = _frame(origin, yaw, math.radians(-12))
    shell = _layered('dt_pla', (0.88, 0.42, 0.12))
    foam = varied('dt_foam', (0.08, 0.08, 0.09), 0.04, 0.95, bump=0.6, bump_scale=500)
    W_, H_, D_ = 0.14, 0.07, 0.06
    b_ = box('dt_shell', P(0, 0, H_ / 2), (W_, D_, H_), shell, bevel=0.012); b_.rotation_euler = rot()
    b_ = box('dt_nose', P(0, -D_ / 2 - 0.004, 0.012), (0.03, 0.012, 0.024), shell, bevel=0.006); b_.rotation_euler = rot()   # the nose notch cut out below
    b_ = box('dt_gasket', P(0, D_ / 2 + 0.008, H_ / 2), (W_ - 0.008, 0.016, H_ - 0.006), foam, bevel=0.007); b_.rotation_euler = rot()
    # the front: a green board on four screws
    b_ = box('dt_front_pcb', P(0, -D_ / 2 - 0.002, H_ / 2 + 0.004), (0.085, 0.003, 0.045), _pcb(), bevel=0); b_.rotation_euler = rot()
    screw = solid('dt_screw', (0.7, 0.7, 0.72), 0.3, metal=1.0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = cyl('dt_screw', P(sx * 0.036, -D_ / 2 - 0.0045, H_ / 2 + 0.004 + sz * 0.017), 0.0028, 0.002, screw, verts=8)
            c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
    b_ = box('dt_soc', P(-0.012, -D_ / 2 - 0.005, H_ / 2 + 0.006), (0.016, 0.003, 0.016), solid('dt_chip', (0.03, 0.03, 0.03), 0.4), bevel=0.001); b_.rotation_euler = rot()
    for k in range(5):
        b_ = box('dt_hdr', P(0.016 + k * 0.0045, -D_ / 2 - 0.006, H_ / 2 + 0.02), (0.002, 0.004, 0.006), solid('dt_hdr', (0.75, 0.62, 0.25), 0.3, metal=1.0), bevel=0)
        b_.rotation_euler = rot()
    # IMU breakout, purple, hanging on its ribbon over the edge of the shell
    b_ = box('dt_imu', P(0.05, -D_ / 2 - 0.006, 0.016), (0.02, 0.0025, 0.016), _pcb('dt_pcb_p', (0.3, 0.08, 0.42)), bevel=0); b_.rotation_euler = rot()
    rib = solid('dt_ribbon', (0.85, 0.72, 0.4), 0.5)
    r_ = box('dt_ribbon', P(0.03, -D_ / 2 - 0.006, 0.03), (0.022, 0.002, 0.008), rib, bevel=0); r_.rotation_euler = rot(Matrix.Rotation(0.6, 3, 'Y'))
    # blue painter's tape across one corner, and the elastic strap trailing off the back
    b_ = box('dt_tape', P(-0.055, -D_ / 2 - 0.001, H_ - 0.01), (0.04, 0.004, 0.012), solid('dt_tape', (0.25, 0.45, 0.78), 0.7), bevel=0)
    b_.rotation_euler = rot(Matrix.Rotation(0.6, 3, 'Y'))
    strap = solid('dt_strapv', (0.12, 0.12, 0.14), 0.9)
    for sx in (-1, 1):
        pts = [P(sx * (W_ / 2), D_ / 2, H_ / 2), P(sx * (W_ / 2 + 0.01), D_ / 2 + 0.04, H_ / 2 - 0.02), P(sx * (W_ / 2 + 0.005), D_ / 2 + 0.07, 0.004)]
        for a, b2 in zip(pts, pts[1:]):
            r_ = box('dt_strap', (a + b2) / 2, (0.003, 0.022, (b2 - a).length), strap, bevel=0)
            r_.rotation_euler = (b2 - a).to_track_quat('Z', 'Y').to_euler()


def place_all(sc):
    """Clear what sat on those three sills and put the team things there."""
    bpy.context.view_layer.update()
    for o in list(sc.objects):
        if o.type not in ('MESH', 'CURVE') or o.name.startswith('dt_'): continue
        cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
        c = sum(cs, Vector()) / 8
        for u in WIN_U:
            # anything on the sill or standing in the reveal in front of the glass
            if abs(c.x - u) < WIN_W / 2 + 0.1 and 0.95 < c.y < A_FACE_Y + 0.078 and SILL_Z - 0.01 < c.z < SILL_Z + 0.35:
                if o.name.split('.')[0] not in ('sill', 'shutter', 'louvre', 'voussoir', 'string', 'A', 'mull', 'pane', 'wc', 'wct'):
                    o.hide_render = True
    # all three windows lit (each will have someone behind it)
    panes = []
    for o in sc.objects:
        if o.type == 'MESH' and o.name.split('.')[0] == 'pane':
            c = o.matrix_world.translation
            if any(abs(c.x - u) < 0.05 for u in WIN_U) and SILL_Z - 0.02 < c.z - 0.3 < SILL_Z + 0.1 and abs(c.y - (A_FACE_Y + 0.08)) < 0.02:
                panes.append(o)
    def emits(o):
        m = o.active_material
        return m is not None and m.use_nodes and any(nd.type == 'BSDF_PRINCIPLED' and nd.inputs['Emission Strength'].default_value > 0 for nd in m.node_tree.nodes)
    lit = next((o for o in panes if emits(o)), None)
    if lit is not None:
        for o in panes:
            if not emits(o):
                o.active_material = lit.active_material
                c = o.matrix_world.translation
                L = bpy.data.lights.new('room', 'POINT'); L.energy = 16; L.color = (1.0, 0.78, 0.5)
                link(bpy.data.objects.new('room', L)).location = (c.x, c.y + 0.4, c.z)
    print('DESIGN panes', [o.name for o in panes], 'lit from', lit.name if lit else None)
    drone_frame((WIN_U[0] - 0.07, A_FACE_Y - 0.01, SILL_Z + 0.105), 0.0)
    toy_truck((WIN_U[1] - 0.11, A_FACE_Y - 0.035, SILL_Z), math.radians(-150))
    vr_headset((WIN_U[2] + 0.1, A_FACE_Y - 0.06, SILL_Z + 0.002), math.radians(-12))
