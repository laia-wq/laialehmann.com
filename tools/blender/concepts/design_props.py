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


def _carbon(name='dt_carbon2'):
    """Carbon fibre plate: a fine twill weave under a glossy coat."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord')
    ck = n.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 900
    ck.inputs['Color1'].default_value = (0.05, 0.05, 0.055, 1); ck.inputs['Color2'].default_value = (0.018, 0.018, 0.02, 1)
    l.new(tc.outputs['Object'], ck.inputs['Vector'])
    l.new(ck.outputs['Color'], b.inputs['Base Color'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.2; bp.inputs['Distance'].default_value = 0.0003
    l.new(ck.outputs['Fac'], bp.inputs['Height']); l.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.32; b.inputs['Coat Weight'].default_value = 0.8; b.inputs['Coat Roughness'].default_value = 0.08
    return m


def _anod(name, col):
    m = solid(name, col, 0.28, metal=1.0)
    return m


def drone_frame(origin, yaw):
    """A 5-inch freestyle quad leaning back against the glass: a true-X
    carbon frame with rounded arm tips, four brushless motors (anodised bells
    over copper windings), tinted tri-blade props, a stack with its little
    boards, a GoPro-style camera in an orange TPU mount on top, the LiPo
    strapped underneath, and a stubby antenna out the back."""
    P, rot = _frame(origin, yaw, math.radians(62))
    carbon = _carbon()
    alu = solid('dt_alu', (0.62, 0.62, 0.64), 0.3, metal=1.0)
    bell = _anod('dt_bell2', (0.62, 0.08, 0.06))
    copper = solid('dt_copper', (0.75, 0.38, 0.18), 0.35, metal=1.0)
    prop = solid('dt_prop2', (0.95, 0.42, 0.06), 0.25); pb = prop.node_tree.nodes['Principled BSDF']
    pb.inputs['Transmission Weight'].default_value = 0.55; pb.inputs['IOR'].default_value = 1.45
    tpu = solid('dt_tpu', (0.95, 0.4, 0.05), 0.6)
    for a in (math.pi / 4, -math.pi / 4):          # the two arm pieces, each one long plate
        b_ = box('dt_arm', P(0, 0, 0), (0.2, 0.016, 0.005), carbon, bevel=0.002, seg=2); b_.rotation_euler = rot(Matrix.Rotation(a, 3, 'Z'))
    for k in range(4):                              # rounded motor mounts at the tips
        a = math.pi / 4 + k * math.pi / 2
        c = cyl('dt_mount', P(0.1 * math.cos(a), 0.1 * math.sin(a), 0), 0.015, 0.005, carbon, verts=24); c.rotation_euler = rot()
    b_ = box('dt_plate', P(0, 0, 0), (0.05, 0.036, 0.005), carbon, bevel=0.003, seg=2); b_.rotation_euler = rot()
    b_ = box('dt_plate', P(0, 0, 0.028), (0.07, 0.036, 0.003), carbon, bevel=0.003, seg=2); b_.rotation_euler = rot()
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = cyl('dt_standoff', P(sx * 0.024, sy * 0.014, 0.014), 0.0025, 0.026, _anod('dt_standoff_b', (0.1, 0.2, 0.6)), verts=6); c.rotation_euler = rot()
    for k, (z, col) in enumerate(((0.008, (0.04, 0.06, 0.18)), (0.016, (0.05, 0.3, 0.12)))):   # ESC and flight controller stack
        b_ = box('dt_fc', P(0, 0, z), (0.03, 0.03, 0.0018), _pcb('dt_pcb%d' % k, col), bevel=0); b_.rotation_euler = rot()
        for j in range(3):
            b_ = box('dt_chip', P(-0.008 + j * 0.008, 0.004 * (j % 2), z + 0.0016), (0.005, 0.005, 0.0012), solid('dt_chip', (0.03, 0.03, 0.03), 0.4), bevel=0); b_.rotation_euler = rot()
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        mp = P(0.1 * math.cos(a), 0.1 * math.sin(a), 0.0)
        R_ = Matrix.Rotation(a + k * 0.7, 3, 'Z')
        up = lambda zz: rot_vec(rot, (0, 0, zz))
        c = cyl('dt_motor', mp + up(0.006), 0.0115, 0.008, alu, verts=24); c.rotation_euler = rot()
        c = cyl('dt_wind', mp + up(0.012), 0.0108, 0.004, copper, verts=24); c.rotation_euler = rot()
        c = cyl('dt_bell', mp + up(0.017), 0.0122, 0.007, bell, verts=24, bevel=0.001); c.rotation_euler = rot()
        c = cyl('dt_shaft', mp + up(0.023), 0.0022, 0.006, alu, verts=10); c.rotation_euler = rot()
        c = cyl('dt_nut', mp + up(0.027), 0.0035, 0.003, solid('dt_nut', (0.1, 0.1, 0.1), 0.4, metal=1), verts=6); c.rotation_euler = rot()
        cyl('dt_hub', mp + up(0.0245), 0.0055, 0.004, prop, verts=16).rotation_euler = rot()
        for j in range(3):             # tri-blade, each blade pitched and swept
            ba = j * 2 * math.pi / 3
            Rb = R_ @ Matrix.Rotation(ba, 3, 'Z')
            for f, (ln, wd) in enumerate(((0.022, 0.012), (0.02, 0.009))):
                off = 0.008 + f * 0.02 + ln / 2 - 0.008
                blade = box('dt_prop', mp + up(0.0245) + rot_vec(rot, tuple(Rb @ Vector((off, 0.002 * f, 0)))), (ln, wd, 0.0012), prop, bevel=0.0005)
                blade.rotation_euler = rot(Rb @ Matrix.Rotation(0.28 - f * 0.08, 3, 'X') @ Matrix.Rotation(0.12 * f, 3, 'Z'))
    # action camera on the top plate, in an orange TPU mount
    b_ = box('dt_tpu', P(0.006, 0, 0.034), (0.034, 0.028, 0.008), tpu, bevel=0.002, seg=2); b_.rotation_euler = rot()
    b_ = box('dt_gopro', P(0.006, 0, 0.05), (0.04, 0.03, 0.026), solid('dt_gopro', (0.05, 0.05, 0.055), 0.45), bevel=0.004, seg=3); b_.rotation_euler = rot()
    c = cyl('dt_glens', P(0.027, 0.006, 0.052), 0.008, 0.005, solid('dt_glass', (0.03, 0.05, 0.08), 0.03, coat=1.0), verts=20); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    c = cyl('dt_glens_ring', P(0.025, 0.006, 0.052), 0.0105, 0.003, solid('dt_gring', (0.15, 0.15, 0.16), 0.3, metal=1), verts=20); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    # FPV camera in the nose, between the plates
    b_ = box('dt_cam', P(0.03, 0, 0.014), (0.014, 0.019, 0.019), solid('dt_cam', (0.06, 0.06, 0.07), 0.4), bevel=0.003); b_.rotation_euler = rot()
    c = cyl('dt_lens', P(0.039, 0, 0.015), 0.0055, 0.006, solid('dt_glass', (0.03, 0.05, 0.08), 0.03, coat=1.0), verts=16); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'Y'))
    # LiPo strapped under the bottom plate, its lead and XT60
    b_ = box('dt_lipo', P(0, 0, -0.016), (0.072, 0.034, 0.024), solid('dt_lipo2', (0.12, 0.12, 0.13), 0.5), bevel=0.004, seg=2); b_.rotation_euler = rot()
    b_ = box('dt_lipo_label', P(0, 0, -0.028), (0.06, 0.03, 0.0008), solid('dt_lipo_lab', (0.92, 0.7, 0.08), 0.5), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_strap', P(0.01, 0, -0.012), (0.013, 0.038, 0.034), solid('dt_strap', (0.08, 0.08, 0.09), 0.95), bevel=0.003); b_.rotation_euler = rot()
    red, blk = solid('dt_wire_r', (0.7, 0.06, 0.05), 0.4), solid('dt_wire_k', (0.03, 0.03, 0.03), 0.4)
    for m_, dy in ((red, -0.003), (blk, 0.003)):
        limb(P(-0.036, dy, -0.014), P(-0.05, dy, -0.004), 0.0016, m_)
        limb(P(-0.05, dy, -0.004), P(-0.034, dy, 0.008), 0.0016, m_)
    b_ = box('dt_xt60', P(-0.05, 0, -0.004), (0.008, 0.016, 0.008), solid('dt_xt60', (0.9, 0.75, 0.1), 0.45), bevel=0.001); b_.rotation_euler = rot()
    # antenna: a short coax out the back to a clear TPU-capped pagoda
    limb(P(-0.03, 0, 0.018), P(-0.05, 0, 0.05), 0.0012, blk)
    cyl('dt_antenna', P(-0.051, 0, 0.056), 0.007, 0.012, solid('dt_ant2', (0.85, 0.9, 0.95), 0.2), verts=16).rotation_euler = rot()


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
    b_ = box('dt_hood', P(0.055, 0, 0.042), (0.06, Wd, 0.026), body, bevel=0.01, seg=5); b_.rotation_euler = rot()
    b_ = box('dt_cab', P(0.012, 0, 0.058), (0.042, Wd - 0.004, 0.058), body, bevel=0.012, seg=5); b_.rotation_euler = rot()
    for sg in (-1, 1):   # cab windows
        b_ = box('dt_win', P(0.014, sg * (Wd / 2 - 0.001), 0.068), (0.03, 0.003, 0.022), solid('dt_win', (0.1, 0.14, 0.18), 0.1), bevel=0.002); b_.rotation_euler = rot()
    b_ = box('dt_win', P(0.034, 0, 0.068), (0.003, Wd - 0.014, 0.022), solid('dt_win', (0.1, 0.14, 0.18), 0.1), bevel=0.002); b_.rotation_euler = rot()
    # the bed
    b_ = box('dt_bed', P(-0.048, 0, 0.034), (0.07, Wd, 0.006), bed_m, bevel=0.002); b_.rotation_euler = rot()
    for sg in (-1, 1):
        b_ = box('dt_bedside', P(-0.048, sg * (Wd / 2 - 0.003), 0.046), (0.07, 0.006, 0.022), bed_m, bevel=0.002); b_.rotation_euler = rot()
    b_ = box('dt_bedside', P(-0.082, 0, 0.046), (0.006, Wd, 0.022), bed_m, bevel=0.002); b_.rotation_euler = rot()
    for (dx, sg) in ((0.055, 1), (0.055, -1), (-0.05, 1), (-0.05, -1)):
        c = cyl('dt_tyre', P(dx, sg * (Wd / 2 + 0.002), 0.017), 0.017, 0.014, tyre, verts=32, bevel=0.003); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
        for j in range(16):   # chunky tread blocks
            aa = j * math.pi / 8
            b_ = box('dt_tread', P(dx + 0.0178 * math.cos(aa), sg * (Wd / 2 + 0.002), 0.017 + 0.0178 * math.sin(aa)), (0.003, 0.012, 0.005), tyre, bevel=0.0008)
            b_.rotation_euler = rot(Matrix.Rotation(-aa, 3, 'Y'))
        c = cyl('dt_hub', P(dx, sg * (Wd / 2 + 0.009), 0.017), 0.008, 0.002, hub, verts=12); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
    for sg in (-1, 1):
        sphere('dt_headlight', P(0.086, sg * 0.024, 0.044), 0.005, solid('dt_hl', (0.95, 0.92, 0.8), 0.2), 8)
    chrome = solid('dt_chrome', (0.85, 0.85, 0.86), 0.12, metal=1.0)
    b_ = box('dt_bumper', P(0.088, 0, 0.028), (0.008, Wd + 0.006, 0.01), chrome, bevel=0.003, seg=3); b_.rotation_euler = rot()
    b_ = box('dt_grille', P(0.0855, 0, 0.042), (0.002, 0.04, 0.014), solid('dt_grille', (0.1, 0.1, 0.11), 0.4, metal=0.6), bevel=0.001); b_.rotation_euler = rot()
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
    """A VR headset, the kind the lab hacks on: a rounded white visor with a
    glossy black front and its four tracking cameras, a grey face cushion,
    the two lenses showing as it sits turned a little to the room, a soft
    strap looped behind, and a bare test board taped to the side."""
    P, rot = _frame(origin, yaw, math.radians(-6))
    shell = varied('dt_vr_shell', (0.86, 0.86, 0.84), 0.02, 0.38)
    front = solid('dt_vr_front', (0.02, 0.02, 0.025), 0.12, coat=1.0)
    foam = varied('dt_foam', (0.2, 0.2, 0.22), 0.04, 0.95, bump=0.6, bump_scale=500)
    lens = solid('dt_vr_lens', (0.02, 0.025, 0.03), 0.02, coat=1.0)
    strap = varied('dt_vr_strap', (0.14, 0.14, 0.16), 0.03, 0.9, bump=0.4, bump_scale=800)
    W_, H_, D_ = 0.16, 0.085, 0.07
    o = box('dt_vr_body', P(0, 0, H_ / 2 + 0.002), (W_, D_, H_), shell, bevel=0.028, seg=6); o.rotation_euler = rot()
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    b_ = box('dt_vr_face', P(0, -D_ / 2 - 0.004, H_ / 2 + 0.002), (W_ - 0.012, 0.008, H_ - 0.012), front, bevel=0.022, seg=6); b_.rotation_euler = rot()
    for sx in (-1, 1):
        for sz in (-1, 1):
            sphere('dt_vr_cam', P(sx * 0.058, -D_ / 2 - 0.0085, H_ / 2 + 0.002 + sz * 0.026), 0.0035, solid('dt_vr_camg', (0.05, 0.06, 0.08), 0.05, coat=1.0), 10, (1, 0.4, 1))
    # the face cushion and the lenses inside it
    b_ = box('dt_vr_gasket', P(0, D_ / 2 + 0.008, H_ / 2), (W_ - 0.02, 0.018, H_ - 0.016), foam, bevel=0.012, seg=4); b_.rotation_euler = rot()
    for sx in (-1, 1):
        c = cyl('dt_vr_lens', P(sx * 0.032, D_ / 2 + 0.0175, H_ / 2 + 0.006), 0.017, 0.002, lens, verts=32); c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
        c = cyl('dt_vr_lensring', P(sx * 0.032, D_ / 2 + 0.017, H_ / 2 + 0.006), 0.0195, 0.0016, solid('dt_vr_ring', (0.08, 0.08, 0.09), 0.4), verts=32)
        c.rotation_euler = rot(Matrix.Rotation(math.pi / 2, 3, 'X'))
    sphere('dt_vr_nose', P(0, D_ / 2 + 0.012, 0.012), 0.016, foam, 12, (1, 0.6, 0.8))
    # the soft strap, looping round behind from both sides to a rear pad
    pts = []
    for k in range(13):
        a = math.pi * k / 12
        pts.append(P(-(W_ / 2 + 0.002) * math.cos(a), D_ / 2 + 0.02 + 0.09 * math.sin(a), H_ / 2 - 0.004 - 0.03 * math.sin(a)))
    for a_, b2 in zip(pts, pts[1:]):
        r_ = box('dt_vr_strap', (a_ + b2) / 2, (0.004, 0.024, (b2 - a_).length * 1.05), strap, bevel=0.0015)
        r_.rotation_euler = (b2 - a_).to_track_quat('Z', 'Y').to_euler()
    b_ = box('dt_vr_pad', P(0, D_ / 2 + 0.11, H_ / 2 - 0.034), (0.05, 0.014, 0.036), strap, bevel=0.006, seg=3); b_.rotation_euler = rot()
    # a bare test board taped to the right side, its ribbon into a port
    side = P(W_ / 2 + 0.004, 0.002, H_ / 2)
    b_ = box('dt_vr_pcb', side, (0.0022, 0.04, 0.032), _pcb('dt_pcb_p', (0.3, 0.08, 0.42)), bevel=0); b_.rotation_euler = rot()
    b_ = box('dt_tape', side + rot_vec(rot, (0.0015, 0, 0.004)), (0.002, 0.05, 0.012), solid('dt_tape', (0.25, 0.45, 0.78), 0.7), bevel=0); b_.rotation_euler = rot()
    r_ = box('dt_ribbon', P(W_ / 2 + 0.002, -0.02, H_ / 2 - 0.012), (0.0015, 0.014, 0.022), solid('dt_ribbon', (0.85, 0.72, 0.4), 0.5), bevel=0)
    r_.rotation_euler = rot(Matrix.Rotation(0.7, 3, 'X'))


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
