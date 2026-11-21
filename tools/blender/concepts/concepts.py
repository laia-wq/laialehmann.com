"""Quick concept renders of three house ideas.
Usage: ASSETS=<assets-raw> python concepts.py <out-dir> <1|2|3>"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import *

OUT, WHICH = sys.argv[-2], sys.argv[-1]

def townhouse():
    sc = reset()
    diorama_base(0, 0, 7.0, 6.0, cobbles('cobble', (0.58, 0.52, 0.46), 7))
    cream, ochre = stucco('stucco_cream', (0.86, 0.78, 0.66)), stucco('stucco_ochre', (0.85, 0.6, 0.42))
    stone = varied('sill', (0.75, 0.7, 0.62), 0.08, 0.8)
    blue = varied('shutter', (0.22, 0.38, 0.45), 0.08, 0.55)
    # two volumes: tall cream house at the back, lower ochre wing on the left
    A = box('houseA', (0.6, 1.0, 1.9), (3.6, 2.8, 3.8), cream, bevel=0.06)
    B = box('houseB', (-2.0, 0.3, 1.2), (2.2, 2.6, 2.4), ochre, bevel=0.06)
    for x in (-0.5, 0.6, 1.7):
        window(A, (x, -0.4, 2.4), 0.6, 1.0, side=-1, arched=True, sill_mat=stone, shutters=blue)
    window(A, (0.0, -0.4, 0.0), 0.9, 1.7, side=-1, arched=True)  # arched door
    window(A, (1.5, -0.4, 0.5), 0.7, 1.0, side=-1, sill_mat=stone)
    window(B, (-2.0, -1.0, 0.5), 0.7, 1.0, side=-1, sill_mat=stone, shutters=blue)
    window(B, (-3.1, 0.6, 0.5), 0.6, 0.9, axis='x', side=-1, sill_mat=stone)
    gable_roof('roofA', 0.6, 1.0, 3.6, 2.8, 3.8, 1.0, tile_mat('tiles', (0.66, 0.3, 0.18)))
    # roof terrace on the wing: parapet, railing, pots
    for y in (-1.0, 1.6):
        box('parapet', (-2.0, y, 2.5), (2.3, 0.14, 0.22), ochre, bevel=0.03)
    box('parapet', (-3.1, 0.3, 2.5), (0.14, 2.7, 0.22), ochre, bevel=0.03)
    for i in range(4):
        pot((-2.8 + i * 0.5, -0.75, 2.42), 0.13, 0.22, ['shrub_03', 'fern_02', 'shrub_sorrel_01', 'weed_plant_02'][i], 0.45)
    string_lights((-3.0, -0.95, 2.95), (-0.25, -0.95, 3.0), 0.2, 9)
    # courtyard: well, table, lanterns, string lights, pots
    cyl('well', (-1.5, -2.0, 0.35), 0.45, 0.7, varied('well_stone', (0.62, 0.58, 0.52), 0.15, 0.85, bump=0.4), verts=28, bevel=0.03)
    cyl('well_water', (-1.5, -2.0, 0.66), 0.36, 0.04, solid('water', (0.05, 0.12, 0.13), 0.05))
    wd = wood('beam', (0.4, 0.25, 0.14))
    for dx in (-0.4, 0.4):
        box('post', (-1.5 + dx, -2.0, 1.0), (0.08, 0.08, 1.3), wd)
    box('well_roof', (-1.5, -2.0, 1.7), (1.1, 0.6, 0.06), wd, rot=(0.25, 0, 0))
    cyl('table', (1.6, -1.6, 0.42), 0.4, 0.05, wd, verts=28)
    cyl('table_leg', (1.6, -1.6, 0.2), 0.05, 0.4, wd)
    for a in (0, 2.1, 4.2):
        box('stool', (1.6 + math.cos(a) * 0.65, -1.6 + math.sin(a) * 0.65, 0.22), (0.26, 0.26, 0.44), wd, bevel=0.02)
    string_lights((-0.9, -0.38, 3.2), (3.2, -2.7, 1.8), 0.45, 12)
    string_lights((-3.0, -1.0, 2.4), (3.2, -2.7, 1.8), 0.5, 14)
    lantern((0.0, -0.55, 2.0), 1.2); lantern((-2.0, -1.15, 1.95), 1.0)
    for p, n in [((2.9, -0.6, 0), 'shrub_sorrel_01'), ((-3.0, -2.5, 0), 'fern_02'), ((0.9, -0.7, 0), 'shrub_03'), ((-0.8, -0.65, 0), 'weed_plant_02')]:
        pot(p, 0.2, 0.32, n, 0.7)
    plant('shrub_02', (3.0, 2.4, 0), 1.6)
    ivy_patch((-0.9, -0.42, 0), (0, -1, 0), 0.9, 2.6, 900, 'ivy', (0.2, 0.36, 0.08))
    hanging_ivy((1.5, -0.45, 3.7), (0, -1, 0), 1.6, 1.4, 10, 'ivy2', (0.28, 0.42, 0.1))
    hanging_ivy((-2.0, -1.1, 2.45), (0, -1, 0), 1.6, 1.0, 8, 'ivy2', (0.28, 0.42, 0.1))
    for p in [(0.6, 1.0, 1.5), (-2.0, 0.3, 1.0), (0.6, 1.0, 3.0)]:
        room_light(p, 90)
    lighting(sc)
    iso_camera(sc, (0, 0, 1.4), 9.6)
    return sc

def boathouse():
    sc = reset()
    water = solid('lake', (0.04, 0.12, 0.13), 0.06)
    diorama_base(0, 0, 7.0, 6.0, water, edge_mat=varied('rock', (0.45, 0.43, 0.4), 0.2, 0.85, bump=0.4))
    box('shore', (-2.4, 0.8, 0.08), (2.4, 4.5, 0.3), cobbles('pebbles', (0.6, 0.56, 0.5), 11), bevel=0.08)
    cedar = wood('cedar', (0.55, 0.32, 0.18), 9, axis='Z')
    trim = varied('trim', (0.16, 0.26, 0.2), 0.05, 0.5)
    shingle = tile_mat('shingles', (0.24, 0.22, 0.22))
    deck = wood('deck', (0.5, 0.36, 0.24), 5)
    # house on stilts over the water
    for x in (-0.4, 1.2, 2.8):
        for y in (-0.2, 1.6):
            cyl('stilt', (x, y, -0.1), 0.08, 0.7, deck)
    box('platform', (1.2, 0.5, 0.28), (4.2, 3.4, 0.14), deck, bevel=0.02)
    H = box('house', (1.2, 0.9, 1.45), (3.4, 2.4, 2.2), cedar, bevel=0.04)
    window(H, (0.4, -0.3, 0.75), 0.9, 1.1, side=-1, frame_mat=trim)
    window(H, (1.9, -0.3, 0.75), 1.1, 1.3, side=-1, frame_mat=trim)
    window(H, (2.9, 0.9, 0.8), 0.7, 1.0, axis='x', side=1, frame_mat=trim)
    gable_roof('roof', 1.2, 0.9, 3.4, 2.4, 2.55, 1.15, shingle)
    # dock + canoe + lanterns
    box('dock', (1.6, -1.8, 0.24), (1.0, 1.8, 0.08), deck, bevel=0.01)
    for y in (-1.2, -2.5):
        for x in (1.15, 2.05):
            cyl('dock_post', (x, y, 0.2), 0.05, 0.6, deck)
    lantern((2.05, -2.5, 0.6), 0.9); lantern((1.15, -2.5, 0.6), 0.9)
    can = sphere('canoe', (3.0, -2.0, 0.1), 0.5, varied('canoe', (0.65, 0.22, 0.12), 0.05, 0.4), 24, (1.0, 0.22, 0.12))
    can.rotation_euler = (0, 0, 0.35)
    # greenhouse annex on the shore
    gx, gy = -2.3, 1.3
    fr = solid('greenhouse_frame', (0.92, 0.92, 0.88), 0.4)
    gl = solid('greenhouse_glass', (0.85, 0.95, 0.92), 0.05); gl.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0.92
    box('gh_base', (gx, gy, 0.35), (1.8, 1.6, 0.3), varied('gh_brick', (0.55, 0.28, 0.2), 0.1, 0.8), bevel=0.02)
    box('gh_glass', (gx, gy, 1.0), (1.76, 1.56, 1.0), gl, bevel=0)
    for k in range(5):
        x = gx - 0.88 + k * 0.44
        box('gh_bar', (x, gy - 0.79, 1.0), (0.03, 0.03, 1.0), fr, bevel=0)
        box('gh_bar', (x, gy + 0.79, 1.0), (0.03, 0.03, 1.0), fr, bevel=0)
    box('gh_rim', (gx, gy, 1.52), (1.86, 1.66, 0.05), fr, bevel=0.01)
    gable_roof('gh_roof', gx, gy, 1.8, 1.6, 1.52, 0.55, gl, over=0.04, thick=0.01)
    for i in range(4):
        plant(['fern_02', 'flower_gazania', 'shrub_sorrel_01', 'nettle_plant'][i], (gx - 0.6 + i * 0.4, gy + R.uniform(-0.4, 0.4), 0.5), 0.5)
    room_light((gx, gy, 1.2), 40, (1, 0.85, 0.6))
    # trees and plants on the shore
    plant('shrub_04', (-3.0, -0.6, 0.2), 1.6); plant('shrub_02', (-2.0, -1.0, 0.2), 1.1)
    plant('fern_02', (-1.4, 2.6, 0.2), 0.6); plant('shrub_03', (-3.1, 2.6, 0.2), 1.0)
    for i in range(6): plant('grass_medium_01', (-3.2 + R.uniform(0, 1.6), R.uniform(-2.2, 2.8), 0.22), 0.3)
    string_lights((-0.45, -0.32, 1.6), (2.05, -2.5, 0.95), 0.25, 10)
    room_light((1.2, 0.9, 1.2), 120)
    lighting(sc, sun_rot=(math.radians(62), 0, math.radians(-30)), sun_energy=2.6, sun_color=(1.0, 0.7, 0.5),
             bg_top=(0.32, 0.45, 0.55), bg_bottom=(0.82, 0.75, 0.7))
    iso_camera(sc, (0, -0.2, 1.0), 9.4)
    return sc

def observatory():
    sc = reset()
    diorama_base(0, 0, 7.0, 6.0, cobbles('flag', (0.62, 0.6, 0.55), 4.5))
    stone = bricks('stone', (0.66, 0.62, 0.55), 2.2)
    lime = stucco('lime', (0.88, 0.84, 0.76))
    copper = varied('copper', (0.32, 0.55, 0.48), 0.06, 0.4, bump=0.15)
    # round tower with a dome, small cottage wing
    T = cyl('tower', (1.0, 0.8, 1.9), 1.15, 3.8, stone, verts=48, bevel=0.03)
    for ang, z in [(-1.2, 0.5), (-0.6, 2.2), (-1.9, 2.2)]:
        x, y = 1.0 + math.cos(ang) * 1.15, 0.8 + math.sin(ang) * 1.15
        c = box('tw_cut', (x, y, z + 0.55), (0.6, 0.6, 1.1), None, bevel=0, rot=(0, 0, ang))
        cut(T, c)
        p = box('tw_glow', (1.0 + math.cos(ang) * 1.05, 0.8 + math.sin(ang) * 1.05, z + 0.55), (0.05, 0.5, 1.0), glass_glow(), bevel=0, rot=(0, 0, ang))
    cyl('tower_rim', (1.0, 0.8, 3.85), 1.25, 0.14, varied('rim', (0.7, 0.66, 0.6), 0.05, 0.8), verts=48, bevel=0.02)
    dome = sphere('dome', (1.0, 0.8, 3.9), 1.1, copper, 48, (1, 1, 0.85))
    slit = box('slit', (1.0, -0.1, 4.5), (0.35, 1.0, 1.6), None, bevel=0); cut(dome, slit)
    cyl('scope', (1.0, 0.2, 4.5), 0.09, 1.2, solid('brass', (0.75, 0.55, 0.25), 0.3, metal=1), verts=16, rot=(0.7, 0, 0))
    W = box('cottage', (-1.7, 0.3, 0.9), (2.6, 2.2, 1.8), lime, bevel=0.05)
    window(W, (-2.3, -0.8, 0.45), 0.6, 0.85, side=-1, sill_mat=varied('sill', (0.7, 0.66, 0.6), 0.05, 0.8), shutters=varied('sh', (0.5, 0.2, 0.15), 0.05, 0.6))
    window(W, (-1.2, -0.8, 0.0), 0.8, 1.5, side=-1, arched=True)
    gable_roof('roof', -1.7, 0.3, 2.6, 2.2, 1.8, 0.9, tile_mat('tiles', (0.6, 0.28, 0.17)))
    cyl('chimney', (-2.5, 0.8, 2.6), 0.2, 0.9, stone, verts=12)
    # spiral-ish stair, garden, lanterns, string lights
    for i in range(7):
        a = -2.6 + i * 0.28
        box('step', (1.0 + math.cos(a) * 1.45, 0.8 + math.sin(a) * 1.45, 0.08 + i * 0.16), (0.5, 0.32, 0.12), varied('stepstone', (0.6, 0.56, 0.5), 0.12, 0.85), bevel=0.02, rot=(0, 0, a))
    lantern((-0.4, -1.0, 0.0 + 1.6), 1.0); lantern((2.4, -0.6, 1.6), 1.0)
    string_lights((-0.45, -0.9, 1.75), (2.2, -2.6, 1.3), 0.35, 11)
    string_lights((-2.95, -0.85, 1.8), (2.2, -2.6, 1.3), 0.45, 13)
    for p, n in [((2.7, -2.2, 0), 'shrub_03'), ((-3.0, -2.4, 0), 'shrub_sorrel_01'), ((-0.3, -2.4, 0), 'fern_02')]:
        pot(p, 0.22, 0.34, n, 0.7)
    for i in range(10):
        plant(R.choice(['flower_gazania', 'periwinkle_plant', 'weed_plant_02']), (R.uniform(-3, -0.6), R.uniform(-2.2, -1.2), 0), 0.35)
    plant('shrub_04', (3.0, 2.2, 0), 1.8); plant('shrub_02', (-3.0, 2.3, 0), 1.3)
    ivy_patch((0.2, -0.05, 0), (-0.6, -0.8, 0), 0.9, 2.8, 900, 'ivy', (0.2, 0.36, 0.08))
    room_light((1.0, 0.8, 1.0), 100); room_light((1.0, 0.8, 2.8), 100); room_light((-1.7, 0.3, 0.9), 80)
    lighting(sc, bg_top=(0.24, 0.3, 0.48), bg_bottom=(0.82, 0.68, 0.62), sun_color=(1.0, 0.72, 0.5), sun_energy=2.6)
    iso_camera(sc, (0, 0, 1.6), 10.0)
    return sc

sc = {'1': townhouse, '2': boathouse, '3': observatory}[WHICH]()
os.makedirs(OUT, exist_ok=True)
render(sc, os.path.join(OUT, f'concept_{WHICH}.png'), samples=48)
