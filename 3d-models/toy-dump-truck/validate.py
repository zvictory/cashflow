"""
Baski oncesi dogrulama:
  1) Her STL su gecirmez (manifold), tutarli normal, pozitif hacim
  2) Montajda parcalar arasi cakisma (kesisim hacmi ~0 olmali)
  3) Damper 0..45 derece kalkarken cakisma
  4) Baski yonunde 45 dereceden dik sarkma / kopru analizi
  5) Toplam olculer

Kullanim:  python validate.py <cikti_klasoru>
Gerekli:   pip install trimesh manifold3d numpy
"""
import itertools
import math
import os
import sys

import manifold3d as m3d
import numpy as np
import trimesh

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
stl_dir = os.path.join(out, "stl")
asm_dir = os.path.join(out, "assembly_stl")
ok = True
lines = []


def log(s=""):
    print(s)
    lines.append(s)


def to_manifold(tm):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                                 tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


# 1) STL butunlugu ------------------------------------------------------------
log("== 1) STL butunlugu (baski dosyalari) ==")
for f in sorted(os.listdir(stl_dir)):
    tm = trimesh.load(os.path.join(stl_dir, f))
    man = to_manifold(tm)
    good = tm.is_watertight and tm.is_winding_consistent and tm.volume > 0 and man.status() == m3d.Error.NoError
    ok &= good
    log("%-26s %s  hacim=%7.0f mm3  ucgen=%6d  zmin=%.2f" % (
        f, "OK " if good else "HATA", tm.volume, len(tm.faces), tm.bounds[0][2]))

# 2) Montaj cakismasi ---------------------------------------------------------
log("\n== 2) Montaj cakisma testi (kesisim hacmi, mm3) ==")
parts = {os.path.splitext(f)[0]: trimesh.load(os.path.join(asm_dir, f)) for f in sorted(os.listdir(asm_dir))}
mans = {k: to_manifold(v) for k, v in parts.items()}
TOL = 0.05  # mm3 - temas eden yuzeylerden kaynakli sayisal gurultu
worst = 0.0
for a, b in itertools.combinations(sorted(parts), 2):
    if not parts[a].bounds is None:
        ba, bb = parts[a].bounds, parts[b].bounds
        if np.any(ba[1] < bb[0]) or np.any(bb[1] < ba[0]):
            continue
    v = (mans[a] ^ mans[b]).volume()
    worst = max(worst, v)
    if v > TOL:
        ok = False
        log("CAKISMA %-20s x %-20s %.3f" % (a, b, v))
log("En buyuk kesisim: %.4f mm3 (esik %.2f)" % (worst, TOL))

allm = trimesh.util.concatenate(list(parts.values()))
ext = allm.bounds[1] - allm.bounds[0]
log("\nMontaj olculeri (aynalar dahil): %.1f x %.1f x %.1f mm" % tuple(ext))
no_mir = trimesh.util.concatenate([v for k, v in parts.items() if not k.startswith("08_")])
ext2 = no_mir.bounds[1] - no_mir.bounds[0]
log("Montaj olculeri (aynalar haric): %.1f x %.1f x %.1f mm" % tuple(ext2))

# 3) Damper devirme -----------------------------------------------------------
log("\n== 3) Damper devirme testi (mafsal x=-93, z=30) ==")
moving = [k for k in parts if k.startswith("03_") or k.startswith("14a_")]
static = [k for k in parts if k not in moving and not k.startswith("15_")]
hinges = [k for k in parts if k.startswith("15_")]
for deg in (10, 20, 30, 40, 45, 50):
    R = trimesh.transformations.rotation_matrix(math.radians(-deg), [0, 1, 0], [-93, 0, 30])
    # +X ucu yukari kalksin: Y ekseni etrafinda negatif aci
    bed = parts["03_DumpBed"].copy()
    bed.apply_transform(R)
    if bed.bounds[1][2] < parts["03_DumpBed"].bounds[1][2]:
        R = trimesh.transformations.rotation_matrix(math.radians(deg), [0, 1, 0], [-93, 0, 30])
        bed = parts["03_DumpBed"].copy()
        bed.apply_transform(R)
    mb = to_manifold(bed)
    hits = []
    for k in static + hinges:
        v = (mb ^ mans[k]).volume()
        if v > TOL:
            hits.append("%s(%.2f)" % (k, v))
    if deg <= 45 and hits:
        ok = False
    log("%2d derece: %s" % (deg, "temiz" if not hits else "cakisma: " + ", ".join(hits)))

# 4) Sarkma analizi ---------------------------------------------------------
log("\n== 4) Sarkma analizi (baski yonunde, tabla z=0 haric) ==")
log("%-26s %12s %12s   %s" % ("dosya", ">45deg mm2", "kopru mm2", "en buyuk kopru bolgesi"))
for f in sorted(os.listdir(stl_dir)):
    tm = trimesh.load(os.path.join(stl_dir, f))
    n = tm.face_normals
    c = tm.triangles_center
    a = tm.area_faces
    above = c[:, 2] > 0.05
    down = n[:, 2] < -math.cos(math.radians(45)) - 1e-3
    flat = n[:, 2] < -0.999
    over = above & down & ~flat
    bridge = above & flat
    # en buyuk kopru bolgesi (yatay, asagi bakan yuzey kumesi) ve olculeri
    big = "-"
    if bridge.any():
        sub = tm.submesh([np.where(bridge)[0]], append=True)
        comp = max(sub.split(only_watertight=False), key=lambda c: c.area)
        ex = comp.bounds[1] - comp.bounds[0]
        big = "%.1f x %.1f @z=%.1f" % (ex[0], ex[1], comp.bounds[0][2])
    log("%-26s %12.1f %12.1f   %s" % (f, a[over].sum(), a[bridge].sum(), big))

log("\nSONUC: %s" % ("TUM TESTLER GECTI" if ok else "SORUN VAR"))
with open(os.path.join(out, "validation_report.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
sys.exit(0 if ok else 1)
