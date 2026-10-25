"""
Joint-by-joint fit validation + assembly-sequence simulation + test-print coupons.

  1) For every mating pair: measured clearance (mm) vs design target, and engaged
     length of the peg/pin/tenon inside its hole/slot.
  2) Seating / functional gaps (bed rests on chassis, wheel-to-arch, rotation gaps).
  3) Assembly sequence: each part is slid in along its real insertion direction,
     step by step, and checked for collisions against everything already installed.
  4) Writes small "fit test" coupons cut from the real parts (stl/fit_test/)
     so the fits can be test-printed before printing the whole truck.

Usage:  python fit_check.py <output_dir>      (needs: trimesh manifold3d numpy rtree)
"""
import os
import sys

import manifold3d as m3d
import numpy as np
import trimesh

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
asm_dir = os.path.join(out, "assembly_stl")
P = {os.path.splitext(f)[0]: trimesh.load(os.path.join(asm_dir, f)) for f in os.listdir(asm_dir)}
lines, ok = [], True


def log(s=""):
    print(s)
    lines.append(s)


def man(tm):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                                 tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def region_points(tm, box, density=60.0):
    """Dense surface samples of `tm` restricted to an axis-aligned box."""
    lo, hi = np.array(box[0::2], float), np.array(box[1::2], float)
    tri = tm.triangles
    # faces whose bounding box overlaps the region (long faces are kept too)
    sel = np.all((tri.min(1) <= hi + 0.5) & (tri.max(1) >= lo - 0.5), axis=1)
    sub = tm.submesh([np.where(sel)[0]], append=True)
    n = min(400000, max(4000, int(sub.area * density)))
    pts, _ = trimesh.sample.sample_surface(sub, n, seed=1)
    pts = np.vstack([pts, sub.vertices])
    return pts[np.all((pts >= lo) & (pts <= hi), axis=1)]


AX = {"x": 0, "y": 1, "z": 2}

# ---------------------------------------------------------------------------
# 1) Mating joints
#    (name, peg part, peg region box, hole part, target clearance, tol, min engage, axis)
# ---------------------------------------------------------------------------
JOINTS = [
    ("Front axle  -> chassis bearing (rotates)", "12_FrontAxle", (63, 73, 14.5, 20.5, 13, 19), "02_Chassis", 0.30, 0.06, 4.5, "y"),
    ("Rear axle   -> chassis bearing (rotates)", "13_RearAxle", (-41, -31, 14.5, 20.5, 13, 19), "02_Chassis", 0.30, 0.06, 4.5, "y"),
    ("Wheel rim   -> axle, D-hole (press fit)", "12_FrontAxle", (63, 73, 20.3, 29.1, 12, 20), "10_WheelRim", 0.05, 0.05, 8.5, "y"),
    ("Tire (TPU)  -> rim (stretch fit)", "11_Tire", (50, 86, 23, 34, -2, 34), "10_WheelRim", 0.00, 0.02, 10.5, "y"),
    ("Cabin pin   -> chassis hole", "14b_PinCabin_R", (55, 60, 14, 20, 21, 25.9), "02_Chassis", 0.10, 0.05, 4.5, "z"),
    ("Cabin pin   -> cabin mount block", "14b_PinCabin_R", (55, 60, 14, 20, 26.1, 30), "01_Cabin", 0.10, 0.05, 3.5, "z"),
    ("Seat tab    -> chassis deck slot", "06_Seat_R", (68.9, 71.1, 3, 17, 23.5, 25.9), "02_Chassis", 0.15, 0.05, 2.0, "z"),
    ("Steering peg-> chassis deck hole", "07_SteeringWheel", (76, 80, 8, 12, 23, 25.9), "02_Chassis", 0.15, 0.05, 1.8, "z"),
    ("Grille      -> cabin front pocket", "05_Grille", (92.98, 93.95, -21, 21, 29, 45), "01_Cabin", 0.15, 0.05, 0.9, "x"),
    ("Mirror peg  -> cabin side hole", "08_Mirror_R", (88, 91, 29.2, 31.95, 58, 62), "01_Cabin", 0.15, 0.05, 1.8, "y"),
    ("Bumper tenon-> chassis rail mortise", "04_FrontBumper", (89.5, 93.95, 15, 20, 19, 25), "02_Chassis", 0.15, 0.05, 4.0, "x"),
    ("Exhaust peg -> chassis rail slot", "09_ExhaustPipe", (47.9, 50.1, 16.4, 18.6, 22.8, 25.9), "02_Chassis", 0.15, 0.05, 3.0, "z"),
    ("Hinge tenon -> chassis rail mortise", "15_BedHinge_R", (-95.1, -90.9, 18.2, 19.95, 19.9, 24.1), "02_Chassis", 0.15, 0.05, 1.7, "y"),
    ("Hinge pin   -> hinge bracket (free)", "14a_PinHinge_R", (-96, -90, 20.25, 23.15, 27, 33), "15_BedHinge_R", 0.15, 0.05, 2.8, "y"),
    ("Hinge pin   -> bed subframe (snug)", "14a_PinHinge_R", (-96, -90, 15.8, 19.45, 27, 33), "03_DumpBed", 0.05, 0.05, 3.5, "y"),
]

log("== 1) Joint-by-joint fit check ==")
log("%-42s %10s %10s %10s  %s" % ("joint", "target", "measured", "engaged", "result"))
for name, peg, box, hole, target, tol, min_eng, axis in JOINTS:
    pts = region_points(P[peg], box)
    hm = P[hole]
    _, dist, _ = trimesh.proximity.closest_point(hm, pts)
    inside = hm.contains(pts)
    interf = dist[inside].max() if inside.any() and dist[inside].max() > 0.01 else 0.0
    clear = dist.min() if not interf else -interf
    near = pts[dist <= target + tol + 0.1]
    eng = np.ptp(near[:, AX[axis]]) if len(near) else 0.0
    good = (abs(clear - target) <= tol) and eng >= min_eng and not interf
    ok &= good
    log("%-42s %8.2fmm %8.2fmm %8.1fmm  %s" % (name, target, clear, eng, "PASS" if good else "FAIL"))

# ---------------------------------------------------------------------------
# 2) Seating contacts and functional gaps
# ---------------------------------------------------------------------------
log("\n== 2) Seating and functional gaps ==")
GAPS = [
    ("Bed subframe rests on chassis rails", "03_DumpBed", (-80, 40, 15.5, 19.5, 25.9, 26.5), "02_Chassis", 0.0, 0.02),
    ("Cabin rests on chassis deck", "01_Cabin", (52, 94, -21, 21, 25.9, 26.5), "02_Chassis", 0.0, 0.02),
    ("Wheel hub boss to bearing block (side play)", "10_WheelRim", (60, 76, 20.2, 20.5, 10, 22), "02_Chassis", 0.30, 0.05),
    ("Bed floor above hinge (tip clearance)", "15_BedHinge_R", (-97, -89, 20, 24, 32, 34), "03_DumpBed", 0.60, 0.05),
    ("Hinge bracket to bed subframe (side)", "15_BedHinge_R", (-97, -89, 20.1, 20.4, 18, 31), "03_DumpBed", 0.70, 0.05),
]
for name, a, box, b, target, tol in GAPS:
    pts = region_points(P[a], box)
    _, dist, _ = trimesh.proximity.closest_point(P[b], pts)
    g = dist.min()
    good = abs(g - target) <= tol
    ok &= good
    log("%-46s target %.2f  measured %.2f mm  %s" % (name, target, g, "PASS" if good else "FAIL"))
# minimum running clearance of all 6 tires to every non-wheel part
tires = [k for k in P if k.startswith("11_")]
others = trimesh.util.concatenate([P[k] for k in P if not k.startswith(("10_", "11_", "12_", "13_"))])
tmin = min(trimesh.proximity.closest_point(others, P[t].sample(6000, seed=2))[1].min() for t in tires)
good = tmin >= 0.5
ok &= good
log("%-46s >= 0.50     measured %.2f mm  %s" % ("Tires free-running (min gap to body)", tmin, "PASS" if good else "FAIL"))

# ---------------------------------------------------------------------------
# 3) Assembly sequence (sweep along insertion direction)
# ---------------------------------------------------------------------------
log("\n== 3) Assembly sequence simulation (sweep, step 0.25 mm) ==")
M = {k: man(v) for k, v in P.items()}
installed = ["02_Chassis"]


def wheel(r, t):
    return M[r] + M[t]


def sweep(label, moving, direction, dist, against, subset=None):
    global ok
    d = np.array(direction, float)
    worst, at = 0.0, 0.0
    targets = [M[k] for k in (subset or against)]
    for s in np.arange(dist, -1e-9, -0.25):
        mv = moving.translate(tuple(d * s))
        for t in targets:
            v = (mv ^ t).volume()
            if v > worst:
                worst, at = v, s
    good = worst < 0.01
    ok &= good
    log("%-52s %s" % (label, "PASS" if good else "BLOCKED (%.3f mm3 at %.1f mm)" % (worst, at)))


sweep("1. Axles slide through bearings (from +Y side)", M["12_FrontAxle"], (0, 1, 0), 45, installed)
sweep("   rear axle 1", M["13_RearAxle"], (0, 1, 0), 45, installed)
sweep("   rear axle 2", M["13_RearAxle_2"], (0, 1, 0), 45, installed)
installed += ["12_FrontAxle", "13_RearAxle", "13_RearAxle_2"]
# tires onto rims (from the inner side), then wheels onto axle ends
rims = sorted(k for k in P if k.startswith("10_"))
pairs = [(r, r.replace("10_WheelRim", "11_Tire")) for r in rims]
for i, (r, t) in enumerate(pairs, 1):
    side = 1 if P[r].centroid[1] > 0 else -1
    sweep("2. Tire onto rim, wheel %d (%s)" % (i, "right" if side > 0 else "left"), M[t], (0, -side, 0), 12, [r])
for i, (r, t) in enumerate(pairs, 1):
    side = 1 if P[r].centroid[1] > 0 else -1
    sweep("3. Wheel %d onto axle end (%s)" % (i, "right" if side > 0 else "left"), wheel(r, t), (0, side, 0), 14, installed)
installed += [k for p in pairs for k in p]
for k in ("06_Seat_R", "06_Seat_L", "07_SteeringWheel", "14b_PinCabin_R", "14b_PinCabin_L"):
    sweep("4. %s down into deck" % k, M[k], (0, 0, 1), 12, installed)
    installed.append(k)
sweep("5. Grille into cabin pocket (from front)", M["05_Grille"], (1, 0, 0), 6, ["01_Cabin"])
sweep("6. Cabin (+grille) lowered onto pins", M["01_Cabin"] + M["05_Grille"], (0, 0, 1), 45, installed)
installed += ["01_Cabin", "05_Grille"]
sweep("7. Right mirror into cabin", M["08_Mirror_R"], (0, 1, 0), 8, installed)
sweep("   Left mirror into cabin", M["08_Mirror_L"], (0, -1, 0), 8, installed)
sweep("8. Front bumper onto rail ends", M["04_FrontBumper"], (1, 0, 0), 8, installed)
sweep("9. Exhaust peg into rail slot", M["09_ExhaustPipe"], (0, 0, 1), 8, installed)
installed += ["08_Mirror_R", "08_Mirror_L", "04_FrontBumper", "09_ExhaustPipe"]
sweep("10. Right hinge into rail mortise", M["15_BedHinge_R"], (0, 1, 0), 6, installed)
sweep("    Left hinge into rail mortise", M["15_BedHinge_L"], (0, -1, 0), 6, installed)
installed += ["15_BedHinge_R", "15_BedHinge_L"]
sweep("11. Dump bed lowered between hinges", M["03_DumpBed"], (0, 0, 1), 40, installed)
installed.append("03_DumpBed")
sweep("12. Right hinge pin through hinge + bed", M["14a_PinHinge_R"], (0, 1, 0), 12, installed)
sweep("    Left hinge pin through hinge + bed", M["14a_PinHinge_L"], (0, -1, 0), 12, installed)

# ---------------------------------------------------------------------------
# 4) Fit-test coupons cut from the real parts
# ---------------------------------------------------------------------------
log("\n== 4) Fit-test coupons (stl/fit_test/) ==")
cdir = os.path.join(out, "stl", "fit_test")
os.makedirs(cdir, exist_ok=True)
FLIP = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])


def coupon(fname, part, box, rot=None):
    lo, hi = np.array(box[0::2]), np.array(box[1::2])
    cut = M[part] ^ m3d.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
    mesh = cut.to_mesh()
    tm = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts)
    if rot is not None:
        tm.apply_transform(rot)
    tm.apply_translation(-np.r_[tm.bounds.mean(0)[:2], tm.bounds[0][2]])
    tm.export(os.path.join(cdir, fname))
    log("%-34s %5.1f x %5.1f x %5.1f mm  watertight=%s" % (fname, *tm.extents, tm.is_watertight))


coupon("T1_chassis_rear_crop.stl", "02_Chassis", (-101, -62, -30, 30, 9, 27), FLIP)
coupon("T2_chassis_front_crop.stl", "02_Chassis", (46, 95, -22, 22, 9, 27), FLIP)
coupon("T3_bed_pivot_crop.stl", "03_DumpBed", (-101, -80, -34, 34, 25, 40))
log("Print with T1-T3: 15_bed_hinge_right, 14a_pin_hinge (x1), 13_rear_axle (x1),")
log("10_wheel_rim (x1), 11_tire (x1), 14b_pin_cabin (x1), 06_seat (x1), 07_steering_wheel,")
log("04_front_bumper, 09_exhaust_pipe  -> tests every fit type before the full print.")

log("\nRESULT: %s" % ("ALL JOINTS AND ASSEMBLY STEPS PASS" if ok else "PROBLEMS FOUND"))
with open(os.path.join(out, "fit_report.txt"), "w") as f:
    f.write("\n".join(lines) + "\n")
sys.exit(0 if ok else 1)
