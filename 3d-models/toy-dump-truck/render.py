"""Onizleme gorselleri: blender --background dump_truck.blend --python render.py -- <cikti_klasoru>"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "."
img_dir = os.path.join(out, "renders")
os.makedirs(img_dir, exist_ok=True)
scene = bpy.context.scene
asm = bpy.data.collections["Assembly"]
plate = bpy.data.collections["Print_Plate"]

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.93, 0.95, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

floor_mat = bpy.data.materials.new("floor")
floor_mat.diffuse_color = (0.85, 0.85, 0.86, 1)
floor_mat.use_nodes = True
floor_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.82, 1)
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, -0.01))
floor = bpy.context.active_object
floor.data.materials.append(floor_mat)

for name, loc, energy, size in (("key", (250, -300, 400), 4.0e6, 200), ("fill", (-300, 250, 250), 1.6e6, 300),
                                ("rim", (-50, 400, 150), 1.0e6, 150)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = (Vector((0, 0, 30)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(lo)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def look(loc, target, lens=50, ortho=None):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.type = "PERSP"
        cam_data.lens = lens


def shot(fname):
    scene.render.filepath = os.path.join(img_dir, fname)
    bpy.ops.render.render(write_still=True)


def show(asm_on, plate_on):
    for o in asm.objects:
        o.hide_render = not asm_on
    for o in plate.objects:
        o.hide_render = not plate_on


# 1) montajli, on 3/4
show(True, False)
look((300, -330, 190), (5, 0, 35), lens=55)
shot("01_assembled_front.png")

# 2) damper kaldirilmis, arka 3/4
pivot = Vector((-93, 0, 30))
tip = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-45), 4, "Y") @ Matrix.Translation(-pivot)
moving = [o for o in asm.objects if o.name.startswith("03_") or o.name.startswith("14a_")]
for o in moving:
    o.matrix_world = tip
look((-330, -300, 230), (-10, 0, 45), lens=50)
shot("02_bed_tipped_rear.png")
for o in moving:
    o.matrix_world = Matrix.Identity(4)

# 3) patlatilmis gorunus
offsets = {"01_": (0, 0, 70), "03_": (0, 0, 120), "14a_": (0, 0, 120), "04_": (40, 0, 0), "05_": (60, 0, 40),
           "06_": (0, 0, 40), "07_": (0, 0, 45), "08_": (0, 0, 70), "09_": (0, 0, 70), "15_": (0, 0, 60),
           "14b_": (0, 0, 35)}
for o in asm.objects:
    d = Vector((0, 0, 0))
    for k, v in offsets.items():
        if o.name.startswith(k):
            d = Vector(v)
    if o.name.startswith(("10_", "11_")):
        side = 1 if sum(v.co.y for v in o.data.vertices[:20]) > 0 else -1
        d = Vector((0, side * (45 if o.name.startswith("11_") else 25), 0))
    if o.name.startswith(("08_", "15_", "14a_")):
        side = 1 if o.data.vertices[0].co.y > 0 else -1
        d += Vector((0, side * 25, 0))
    o.matrix_world = Matrix.Translation(d)
look((360, -420, 330), (0, 0, 70), lens=42)
shot("03_exploded.png")
for o in asm.objects:
    o.matrix_world = Matrix.Identity(4)

# 4) baski tablasi (tum parcalar baski yonunde)
show(False, True)
xs = [v.co.x for o in plate.objects for v in o.data.vertices]
ys = [v.co.y for o in plate.objects for v in o.data.vertices]
cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
look((cx + 120, cy - 420, 380), (cx, cy, 0), lens=48)
shot("04_print_layout.png")
print("renders ->", img_dir)
