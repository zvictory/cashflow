"""
Oyuncak Damperli Kamyon - 3D baskiya hazir parametrik Blender modeli
====================================================================

Calistirma (Blender 4.2+ / 5.x):
    blender --background --python dump_truck.py -- <cikti_klasoru>
veya Blender icinde Scripting sekmesinde "Run Script".

Birim: milimetre (1 Blender birimi = 1 mm). Olcek: 200 x 70 x 80 mm.
Eksenler: +X = kamyonun onu, +Y = sag taraf, +Z = yukari, zemin z = 0.

Her parca once MONTAJ konumunda modellenir, sonra BASKI yonune cevrilir
(tablaya oturan duz yuz z = 0) ve ayri STL olarak disari aktarilir.
"""

import math
import os
import struct
import sys

import bpy  # noqa: I001  (bpy once yuklenmeli)
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Parametreler (mm)
# ---------------------------------------------------------------------------
FIT = 0.15          # gecme toleransi (her yuzde) - pim/tirnak/yuva
PIN_D = 3.0         # pim capi
AXLE_D = 5.0        # aks capi
AXLE_FLAT = 2.1     # aksin alt duzlugu (merkezden), tablaya duz oturmasi icin
AXLE_BEARING_D = 5.6  # sasi yatak deligi (aks serbest doner)
WHEEL_R = 16.0      # lastik dis yaricapi
RIM_R = 10.0        # jant yaricapi = lastik ic yaricapi (TPU sikma gecme)
AXLE_Z = 16.0       # aks yuksekligi
AXLES_X = {"front": 68.0, "rear1": -36.0, "rear2": -70.0}
PIVOT = (-93.0, 30.0)  # damper mafsal ekseni (x, z)

SEG = 64

# ---------------------------------------------------------------------------
# Yardimci geometri fonksiyonlari
# ---------------------------------------------------------------------------

def _link(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=bm.verts)
    return _link(name, bm)


def _axis_matrix(axis):
    # create_cone eksen Z boyuncadir; istenen eksene dondur
    if axis == "z":
        return Matrix.Identity(4)
    if axis == "y":
        return Matrix.Rotation(-math.pi / 2, 4, "X")
    return Matrix.Rotation(math.pi / 2, 4, "Y")


def frustum(name, axis, c, r0, r1, a0, a1, seg=SEG):
    """Eksen boyunca a0..a1 araliginda, a0'da r0, a1'de r1 yaricapli kesik koni.
    c = diger iki koordinat (axis x->(y,z), y->(x,z), z->(x,y))."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r0, radius2=r1, depth=a1 - a0)
    bmesh.ops.translate(bm, vec=(0, 0, (a0 + a1) / 2), verts=bm.verts)
    bm.transform(_axis_matrix(axis))
    if axis == "x":
        off = (0, c[0], c[1])
    elif axis == "y":
        off = (c[0], 0, c[1])
    else:
        off = (c[0], c[1], 0)
    bmesh.ops.translate(bm, vec=off, verts=bm.verts)
    return _link(name, bm)


def cyl(name, axis, c, r, a0, a1, seg=SEG):
    return frustum(name, axis, c, r, r, a0, a1, seg)


def prism(name, pts, plane, a0, a1):
    """2B poligonu (pts) bir duzlemde cizip dik eksende a0..a1 arasinda uzatir.
    plane: 'xz' (Y boyunca), 'yz' (X boyunca), 'xy' (Z boyunca)."""
    def p3(u, v, a):
        if plane == "xz":
            return (u, a, v)
        if plane == "yz":
            return (a, u, v)
        return (u, v, a)
    bm = bmesh.new()
    bot = [bm.verts.new(p3(u, v, a0)) for u, v in pts]
    top = [bm.verts.new(p3(u, v, a1)) for u, v in pts]
    bm.faces.new(bot)
    bm.faces.new(list(reversed(top)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    return _link(name, bm)


def d_profile(r, flat, cu=0.0, cv=0.0, n=48):
    """Alt tarafi v = cv - flat seviyesinde kesilmis daire (D kesit)."""
    pts = []
    # kesilen yayin disindaki acilar
    a0 = -math.pi / 2 + math.acos(flat / r)
    a1 = 3 * math.pi / 2 - math.acos(flat / r)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def _bool(target, operands, op):
    for o in operands:
        m = target.modifiers.new("b", "BOOLEAN")
        m.operation = op
        m.solver = "MANIFOLD"
        m.object = o
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    for o in operands:
        d = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(d)
    return target


def union(t, *ops):
    return _bool(t, list(ops), "UNION")


def diff(t, *ops):
    return _bool(t, list(ops), "DIFFERENCE")


def mirror_y(src, name):
    me = src.data.copy()
    me.transform(Matrix.Scale(-1, 4, (0, 1, 0)))
    me.flip_normals()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def duplicate(src, name, matrix=None):
    me = src.data.copy()
    if matrix is not None:
        me.transform(matrix)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def rot_about(axis, angle, center):
    c = Vector(center)
    return Matrix.Translation(c) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-c)


# ---------------------------------------------------------------------------
# 1. KABIN (alti acik kabuk, tavani tablaya gelecek sekilde basilir)
# ---------------------------------------------------------------------------

def make_cabin():
    X0, X1, W, Z0, Z1 = 52.0, 94.0, 32.0, 22.0, 72.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(X1 - X0, 2 * W, Z1 - Z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((X0 + X1) / 2, 0, (Z0 + Z1) / 2), verts=bm.verts)
    edges = []
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co
        top = abs(a.z - Z1) < 1e-6 and abs(b.z - Z1) < 1e-6
        front_vert = (abs(a.x - X1) < 1e-6 and abs(b.x - X1) < 1e-6
                      and abs(abs(a.y) - W) < 1e-6 and abs(a.y - b.y) < 1e-6)
        if top or front_vert:
            edges.append(e)
    bmesh.ops.bevel(bm, geom=edges, offset=3.0, offset_type="OFFSET",
                    segments=4, profile=0.5, affect="EDGES", clamp_overlap=True)
    cab = _link("01_Cabin", bm)

    # ic bosluk (cidar 2 mm, tavan 2 mm) + sasi kanali
    diff(cab,
         box("cav", 54, 92, -30, 30, 15, 70),
         box("chan", 40, 100, -21.3, 21.3, 15, 26))

    # teker kemer kutulari (45 derece pahli ust -> desteksiz baski)
    tub_r = prism("tubR", [(21.5, 22), (30.5, 22), (30.5, 44.5), (21.5, 35.5)], "yz", 53.5, 86)
    tub_l = mirror_y(tub_r, "tubL")
    # arka montaj bloklari (pim delikli, 45 derece pah)
    mb_r = prism("mbR", [(53.5, 26), (61, 26), (61, 33), (53.5, 40.5)], "xz", 13, 21)
    mb_l = mirror_y(mb_r, "mbL")
    # gosterge paneli (egimli ust yuzey)
    dash = prism("dash", [(84, 26), (92.5, 26), (92.5, 46.5), (84, 38)], "xz", -21, 21)
    union(cab, tub_r, tub_l, mb_r, mb_l, dash)

    cuts = []
    # teker kemerleri
    ax = AXLES_X["front"]
    cuts.append(cyl("archR", "y", (ax, AXLE_Z), WHEEL_R + 2.0, 21.3, 40))
    cuts.append(cyl("archL", "y", (ax, AXLE_Z), WHEEL_R + 2.0, -40, -21.3))
    # on cam (orta dikmeli, iki parca -> kopru < 26 mm)
    cuts.append(box("wsR", 89, 98, 1.5, 27, 48, 68))
    cuts.append(box("wsL", 89, 98, -27, -1.5, 48, 68))
    # yan camlar
    cuts.append(box("swR", 66, 86, 27, 36, 48, 66))
    cuts.append(box("swL", 66, 86, -36, -27, 48, 66))
    # arka cam
    cuts.append(box("rw", 48, 56, -12, 12, 54, 64))
    # izgara yuvasi (1.2 mm derin cep)
    g = FIT
    cuts.append(box("grillePocket", 92.8, 96, -20 - g, 20 + g, 30 - g, 44 + g))
    # ayna tirnak delikleri (2.0 x 2.5 tirnak + tolerans)
    for s in (1, -1):
        cuts.append(box("mirHole%d" % s, 89.5 - 1.25 - g, 89.5 + 1.25 + g,
                        min(s * 29, s * 34), max(s * 29, s * 34), 60 - 1 - g, 60 + 1 + g))
    # montaj pim delikleri
    for s in (1, -1):
        cuts.append(cyl("pinH%d" % s, "z", (57.5, s * 17), PIN_D / 2 + 0.1, 25, 32))
    # kapi cizgileri (0.6 mm oluk)
    for s in (1, -1):
        y0, y1 = (31.4, 33) if s > 0 else (-33, -31.4)
        cuts.append(box("dT%d" % s, 62, 88, y0, y1, 68.4, 69.0))
        cuts.append(box("dF%d" % s, 87.4, 88, y0, y1, 26, 69.0))
        cuts.append(box("dB%d" % s, 62, 62.6, y0, y1, 34, 69.0))
        cuts.append(box("dH%d" % s, 66, 71, y0, y1, 43, 44.2))   # kapi kolu
    # tavan oluklari
    for x in (60, 68, 76, 84):
        cuts.append(box("roofG%d" % x, x - 0.5, x + 0.5, -24, 24, 71.4, 73))
    diff(cab, *cuts)
    return cab


# ---------------------------------------------------------------------------
# 2. SASI (ters cevrilerek basilir: ust yuzey z=26 tablaya)
# ---------------------------------------------------------------------------

def make_chassis():
    ch = box("02_Chassis", -100, 94, 15, 20, 18, 26)
    parts = [box("railL", -100, 94, -20, -15, 18, 26)]
    parts.append(box("deck", 52, 94, -21, 21, 24, 26))
    parts.append(box("rearBar", -100, -97, -28, 28, 14, 26))
    for x in (-54, -18, 10, 40):
        parts.append(box("cm%d" % x, x - 2, x + 2, -15.5, 15.5, 20, 26))
    for name, x in AXLES_X.items():
        for s in (1, -1):
            parts.append(box("bb%s%d" % (name, s), x - 5, x + 5,
                             min(15 * s, 20 * s), max(15 * s, 20 * s), 10, 18.5))
    # yakit deposu / aku kutusu (pahli alt kenar)
    tank_r = prism("tankR", [(19.5, 26), (29, 26), (29, 17), (26, 14), (19.5, 14)], "yz", -12, 34)
    tank_l = mirror_y(tank_r, "tankL")
    parts += [tank_r, tank_l]
    parts.append(cyl("tankCap", "y", (24, 21.5), 2.2, 28.5, 30))
    union(ch, *parts)

    g = FIT
    cuts = []
    for name, x in AXLES_X.items():
        cuts.append(cyl("bear%s" % name, "y", (x, AXLE_Z), AXLE_BEARING_D / 2, -22, 22))
    # on tampon tirnak yuvalari
    for s in (1, -1):
        cuts.append(box("bmM%d" % s, 89.3, 95, s * 17.5 - 1.25 - g, s * 17.5 + 1.25 + g,
                        22 - 2 - g, 22 + 2 + g))
    # damper mafsal braketi tirnak yuvalari (ray dis yuzu)
    for s in (1, -1):
        y0, y1 = (17.9, 21) if s > 0 else (-21, -17.9)
        cuts.append(box("hgM%d" % s, -95 - g, -91 + g, y0, y1, 20 - g, 24 + g))
    # kabin pim delikleri
    for s in (1, -1):
        cuts.append(cyl("cabPin%d" % s, "z", (57.5, s * 17), PIN_D / 2 + 0.1, 20, 27))
    # koltuk tirnak yuvalari
    for s in (1, -1):
        cuts.append(box("seatS%d" % s, 69 - g, 71 + g, s * 10 - 6.5 - g, s * 10 + 6.5 + g, 23, 27))
    # direksiyon mili deligi
    cuts.append(cyl("steerH", "z", (78, 10), 1.0 + g, 22, 27))
    # egzoz tirnak yuvasi
    cuts.append(box("exhS", 49 - 1 - g, 49 + 1 + g, 17.5 - 1 - g, 17.5 + 1 + g, 22.5, 27))
    # stop lambalari
    for s in (1, -1):
        cuts.append(box("tl%d" % s, -101, -99.4, min(s * 20, s * 27), max(s * 20, s * 27), 19, 23))
    # depo kapagi cizgileri
    for s in (1, -1):
        for x in (-2, 24):
            cuts.append(box("tg%d%d" % (s, x), x - 0.4, x + 0.4,
                            min(s * 28.4, s * 30), max(s * 28.4, s * 30), 15, 25))
    diff(ch, *cuts)
    return ch


# ---------------------------------------------------------------------------
# 3. DAMPER KASASI (taban asagi basilir)
# ---------------------------------------------------------------------------

def make_bed():
    outer = [(-33, 76), (33, 76), (33, 43.5), (24, 34.5), (24, 34), (-24, 34), (-24, 34.5), (-33, 43.5)]
    bed = prism("03_DumpBed", outer, "yz", -100, 46)
    cav = [(-31, 80), (31, 80), (31, 44.33), (22.67, 36), (-22.67, 36), (-31, 44.33)]
    diff(bed, prism("cav", cav, "yz", -98, 44))

    parts = []
    # ust kenar dudagi
    for s in (1, -1):
        parts.append(box("lip%d" % s, -100, 46, min(s * 32.5, s * 34), max(s * 32.5, s * 34), 74, 76))
    # dikey nervurler
    for x in (-88, -70, -52, -34, -16, 2, 20, 38):
        for s in (1, -1):
            parts.append(box("rib%d%d" % (x, s), x - 0.75, x + 0.75,
                             min(s * 32.5, s * 34), max(s * 32.5, s * 34), 46, 74.5))
    # arka kapak yatay nervurleri (kasa icinde kalir, 200 mm boyu bozmaz)
    # on alin + kabin koruma siperi (45 derece alt yuzey)
    parts.append(box("head", 44, 46, -33, 33, 75, 80))
    parts.append(prism("canopy", [(45.5, 69), (46, 69), (55, 78), (56, 78), (56, 80), (45.5, 80)],
                       "xz", -33, 33))
    # alt sasi kirisleri (45 derece yan yuzeyler -> destek gerektirmez)
    for s in (1, -1):
        trap = [(15.5, 26), (19.5, 26), (19.5, 30), (24, 34.5), (7, 34.5)]
        if s < 0:
            trap = [(-u, v) for u, v in reversed(trap)]
        parts.append(prism("sfW%d" % s, trap, "yz", -88, 45))
        parts.append(box("sfR%d" % s, -93, -87.5, min(s * 15.5, s * 19.5), max(s * 15.5, s * 19.5), 26, 34.5))
        parts.append(cyl("sfC%d" % s, "y", PIVOT, 4.0, min(s * 15.5, s * 19.5), max(s * 15.5, s * 19.5)))
    union(bed, *parts)

    cuts = [cyl("pivotHole", "y", PIVOT, PIN_D / 2 + 0.05, -21, 21)]
    # arka kapak yatay oluklari
    for z in (50, 62):
        cuts.append(box("rg%d" % z, -101, -99.4, -28, 28, z - 0.5, z + 0.5))
    diff(bed, *cuts)
    return bed


# ---------------------------------------------------------------------------
# 4-9. KUCUK PARCALAR
# ---------------------------------------------------------------------------

def make_bumper():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(6, 64, 11), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(97, 0, 21.5), verts=bm.verts)
    edges = [e for e in bm.edges
             if all(abs(v.co.x - 100) < 1e-6 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=edges, offset=1.5, offset_type="OFFSET", segments=3,
                    profile=0.5, affect="EDGES", clamp_overlap=True)
    bp = _link("04_FrontBumper", bm)
    tenons = [box("ten%d" % s, 89.5, 94.2, s * 17.5 - 1.25, s * 17.5 + 1.25, 20, 24) for s in (1, -1)]
    union(bp, *tenons)
    cuts = []
    for s in (1, -1):
        cuts.append(box("hl%d" % s, 99.2, 101, min(s * 21, s * 29), max(s * 21, s * 29), 19.5, 24))
        cuts.append(box("fog%d" % s, 99.4, 101, min(s * 22, s * 27), max(s * 22, s * 27), 17.5, 18.5))
    cuts.append(box("plate", 99.4, 101, -9, 9, 18.5, 23))
    for z in (25.2,):
        cuts.append(box("bg", 99.5, 101, -16, 16, z - 0.4, z + 0.4))
    diff(bp, *cuts)
    return bp


def make_grille():
    gr = box("05_Grille", 92.8, 93.6, -20, 20, 30, 44)
    parts = []
    parts.append(box("fT", 93.4, 94.8, -20, 20, 42.5, 44))
    parts.append(box("fB", 93.4, 94.8, -20, 20, 30, 31.5))
    parts.append(box("fR", 93.4, 94.8, 18.5, 20, 30, 44))
    parts.append(box("fL", 93.4, 94.8, -20, -18.5, 30, 44))
    parts.append(box("fM", 93.4, 94.6, -0.6, 0.6, 30, 44))
    for z in (33.5, 36, 38.5, 41):
        parts.append(box("sl%d" % int(z * 10), 93.4, 94.6, -19, 19, z - 0.6, z + 0.6))
    union(gr, *parts)
    return gr


def make_seat(side):
    s = 1 if side == "R" else -1
    pts = [(63.5, 26), (76, 26), (76, 31.5), (68.5, 31.5), (67.5, 46), (63.5, 46)]
    seat = prism("06_Seat_" + side, pts, "xz", s * 10 - 6.5, s * 10 + 6.5)
    # alt tirnak ayri kutu (esdogrusal noktali profil hatali ucgenlenmesin)
    union(seat, box("tab", 69, 71, s * 10 - 6.5, s * 10 + 6.5, 23.5, 26.3))
    # oturak/sirt oluklari (sadece gorsel)
    diff(seat, box("sg1", 70, 76.5, s * 10 - 0.4, s * 10 + 0.4, 30.9, 32),
         box("sg2", 63, 64.1, s * 10 - 0.4, s * 10 + 0.4, 30, 45))
    return seat


def make_steering():
    cx, cy, z0, z1 = 78.0, 10.0, 44.0, 45.6
    st = cyl("07_SteeringWheel", "z", (cx, cy), 5.5, z0, z1)
    diff(st, cyl("in", "z", (cx, cy), 4.4, z0 - 1, z1 + 1))
    parts = [cyl("hub", "z", (cx, cy), 1.8, z0, z1)]
    for k in range(3):
        a = math.radians(90 + 120 * k)
        sp = box("sp%d" % k, 0, 4.9, -0.6, 0.6, z0, z1)
        sp.data.transform(Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(a, 4, "Z"))
        parts.append(sp)
    parts.append(cyl("col", "z", (cx, cy), 1.25, 26, z0 + 0.2))
    parts.append(cyl("peg", "z", (cx, cy), 1.0, 23, 26.2))
    union(st, *parts)
    return st


def make_mirror(side):
    # sag ayna (y>0) cizilir, sol ayna aynalanir
    x0, x1 = 89.5 - 1.25, 89.5 + 1.25
    m = box("08_Mirror_R", x0, x1, 29.2, 32.2, 59, 61)
    union(m,
          box("arm", x0, x1, 32, 36, 59, 61),
          box("drop", x0, x1, 34.5, 36, 50, 61),
          box("head", x0, x1, 34, 37.5, 40, 52))
    if side == "L":
        l = mirror_y(m, "08_Mirror_L")
        bpy.data.objects.remove(m)
        return l
    return m


def make_exhaust():
    x0, x1 = 47.0, 51.0
    ex = box("09_ExhaustPipe", x0, x1, 15.5, 27, 26, 29)
    union(ex,
          box("peg", 48, 50, 16.5, 18.5, 22.8, 26.2),
          box("pipe", x0, x1, 25, 29, 26, 62),
          box("elbow", x0, x1, 25, 33, 58, 62),
          box("guard", x0 - 0.01, x1 + 0.01, 29, 30, 34, 52))
    # isi kalkani delikleri
    diff(ex, *[box("hs%d" % z, x0 - 1, x1 + 1, 28.9, 31, z, z + 1.2) for z in (37, 41, 45, 49)])
    return ex


# ---------------------------------------------------------------------------
# 10-13. JANT, LASTIK, AKSLAR (sag tekerlek y>0 icin cizilir)
# ---------------------------------------------------------------------------

def make_rim(x):
    c = (x, AXLE_Z)
    rim = cyl("10_WheelRim", "y", c, RIM_R, 23, 34.2, seg=80)
    union(rim,
          cyl("flange", "y", c, 11.25, 34.0, 35, seg=80),
          cyl("boss", "y", c, 4.0, 20.3, 23.1))
    cuts = [frustum("dish", "y", c, 7.0, 8.6, 33.4, 35.05)]
    # bijon somun yuvalari
    for k in range(6):
        a = 2 * math.pi * k / 6
        cuts.append(cyl("lug%d" % k, "y", (x + 4.8 * math.cos(a), AXLE_Z + 4.8 * math.sin(a)),
                        0.7, 32.6, 33.5, seg=16))
    cuts.append(prism("dhole", d_profile(AXLE_D / 2 + 0.05, AXLE_FLAT + 0.05, x, AXLE_Z), "xz", 20.0, 29.3))
    diff(rim, *cuts)
    return rim


def make_tire(x):
    # taban halka + 2 sira kaydirmali radyal dis (lug); siralar arasinda 0.4 mm oluk.
    n = 20
    t = cyl("11_Tire", "y", (x, AXLE_Z), 15.3, 23, 34, seg=80)
    lugs = []
    w = 2 * math.pi * WHEEL_R / n * 0.45
    for row, (y0, y1, ph) in enumerate(((23.2, 28.3, 0.0), (28.7, 33.8, 0.5))):
        for k in range(n):
            a = 2 * math.pi * (k + ph) / n
            lug = box("lug%d_%d" % (row, k), 14.8, WHEEL_R, y0, y1, -w / 2, w / 2)
            # yerel X = radyal yon -> Y ekseni etrafinda donerek XZ duzleminde yerlestir
            lug.data.transform(Matrix.Translation((x, 0, AXLE_Z)) @ Matrix.Rotation(-a, 4, "Y"))
            lugs.append(lug)
    union(t, *lugs)
    diff(t, cyl("bore", "y", (x, AXLE_Z), RIM_R, 22, 35, seg=80))
    return t


def make_axle(name, x):
    return prism(name, d_profile(AXLE_D / 2, AXLE_FLAT, x, AXLE_Z), "xz", -29, 29)


# ---------------------------------------------------------------------------
# 14-15. PIMLER, DAMPER MAFSALI
# ---------------------------------------------------------------------------

def make_hinge(side):
    px, pz = PIVOT
    prof = [(px - 3.4, 18), (px + 3.4, 18), (px + 3.4, pz)]
    for i in range(1, 24):
        a = math.pi * i / 24
        prof.append((px + 3.4 * math.cos(a), pz + 3.4 * math.sin(a)))
    prof.append((px - 3.4, pz))
    h = prism("15_BedHinge_R", prof, "xz", 20.2, 23.2)
    union(h, box("tenon", -95, -91, 18.2, 20.5, 20, 24))
    diff(h, cyl("hole", "y", PIVOT, PIN_D / 2 + 0.15, 19, 24))
    if side == "L":
        l = mirror_y(h, "15_BedHinge_L")
        bpy.data.objects.remove(h)
        return l
    return h


def make_hinge_pin(side):
    p = cyl("14a_PinHinge_R", "y", PIVOT, PIN_D / 2, 15.8, 23.4, seg=32)
    union(p, cyl("head", "y", PIVOT, 2.75, 23.3, 24.5, seg=32))
    if side == "L":
        l = mirror_y(p, "14a_PinHinge_L")
        bpy.data.objects.remove(p)
        return l
    return p


def make_cabin_pin(s):
    p = cyl("14b_PinCabin_%s" % ("R" if s > 0 else "L"), "z", (57.5, s * 17), PIN_D / 2, 21, 30, seg=32)
    # uca pah: kolay gecme
    return p


# ---------------------------------------------------------------------------
# Montaj ve baski yonleri
# ---------------------------------------------------------------------------

RX = lambda deg: Matrix.Rotation(math.radians(deg), 4, "X")
RY = lambda deg: Matrix.Rotation(math.radians(deg), 4, "Y")

# dosya adi, adet, baski rotasyonu, malzeme notu
PRINT_SPEC = {
    "01_Cabin": ("01_cabin.stl", 1, RX(180), "red"),
    "02_Chassis": ("02_chassis.stl", 1, RX(180), "black"),
    "03_DumpBed": ("03_dump_bed.stl", 1, Matrix.Identity(4), "yellow"),
    "04_FrontBumper": ("04_front_bumper.stl", 1, RY(90), "black"),
    "05_Grille": ("05_grille.stl", 1, RY(-90), "black"),
    "06_Seat_R": ("06_seat_x2.stl", 2, RX(90), "black"),
    "07_SteeringWheel": ("07_steering_wheel.stl", 1, RX(180), "black"),
    "08_Mirror_R": ("08_mirror_right.stl", 1, RY(90), "black"),
    "08_Mirror_L": ("08_mirror_left.stl", 1, RY(90), "black"),
    "09_ExhaustPipe": ("09_exhaust_pipe.stl", 1, RY(90), "black"),
    "10_WheelRim": ("10_wheel_rim_x6.stl", 6, RX(-90), "gray"),
    "11_Tire": ("11_tire_x6_TPU.stl", 6, RX(90), "tire"),
    "12_FrontAxle": ("12_front_axle.stl", 1, Matrix.Identity(4), "black"),
    "13_RearAxle": ("13_rear_axle_x2.stl", 2, Matrix.Identity(4), "black"),
    "14a_PinHinge_R": ("14a_pin_hinge_x2.stl", 2, RX(-90), "gray"),
    "14b_PinCabin_R": ("14b_pin_cabin_x2.stl", 2, Matrix.Identity(4), "gray"),
    "15_BedHinge_R": ("15_bed_hinge_right.stl", 1, RX(-90), "black"),
    "15_BedHinge_L": ("15_bed_hinge_left.stl", 1, RX(90), "black"),
}

COLORS = {
    "red": (0.80, 0.06, 0.03, 1), "yellow": (0.95, 0.70, 0.02, 1),
    "black": (0.035, 0.035, 0.04, 1), "gray": (0.55, 0.56, 0.58, 1),
    "tire": (0.015, 0.015, 0.015, 1),
}


def write_stl(ob, path, matrix=None):
    me = ob.data.copy()
    if matrix is not None:
        me.transform(matrix)
    me.calc_loop_triangles()
    tris = me.loop_triangles
    with open(path, "wb") as f:
        f.write(b"Toy dump truck - units: mm".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            n = t.normal
            f.write(struct.pack("<3f", n.x, n.y, n.z))
            for vi in t.vertices:
                v = me.vertices[vi].co
                f.write(struct.pack("<3f", v.x, v.y, v.z))
            f.write(b"\0\0")
    bpy.data.meshes.remove(me)


def print_matrix(ob, rot):
    me = ob.data.copy()
    me.transform(rot)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    bpy.data.meshes.remove(me)
    t = Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs)))
    return t @ rot, (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.45 if name != "tire" else 0.8
    m.diffuse_color = rgba
    return m


def build(out_dir):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"

    src = {}
    src["01_Cabin"] = make_cabin()
    src["02_Chassis"] = make_chassis()
    src["03_DumpBed"] = make_bed()
    src["04_FrontBumper"] = make_bumper()
    src["05_Grille"] = make_grille()
    src["06_Seat_R"] = make_seat("R")
    src["06_Seat_L"] = make_seat("L")
    src["07_SteeringWheel"] = make_steering()
    src["08_Mirror_R"] = make_mirror("R")
    src["08_Mirror_L"] = make_mirror("L")
    src["09_ExhaustPipe"] = make_exhaust()
    src["15_BedHinge_R"] = make_hinge("R")
    src["15_BedHinge_L"] = make_hinge("L")
    src["14a_PinHinge_R"] = make_hinge_pin("R")
    src["14a_PinHinge_L"] = make_hinge_pin("L")
    src["14b_PinCabin_R"] = make_cabin_pin(1)
    src["14b_PinCabin_L"] = make_cabin_pin(-1)
    src["12_FrontAxle"] = make_axle("12_FrontAxle", AXLES_X["front"])
    src["13_RearAxle"] = make_axle("13_RearAxle", AXLES_X["rear1"])
    src["13_RearAxle_2"] = make_axle("13_RearAxle_2", AXLES_X["rear2"])

    fx = AXLES_X["front"]
    rim = make_rim(fx)
    rim.name = "10_WheelRim"
    tire = make_tire(fx)
    tire.name = "11_Tire"
    src["10_WheelRim"] = rim
    src["11_Tire"] = tire
    # diger 5 tekerlek: kopya + (sol taraf icin Z etrafinda 180 derece)
    k = 0
    for name, x in AXLES_X.items():
        for s in (1, -1):
            if name == "front" and s == 1:
                continue
            k += 1
            m = Matrix.Translation((x - fx, 0, 0))
            if s < 0:
                m = rot_about("Z", math.pi, (x, 0, 0)) @ m
            src["10_WheelRim_%d" % k] = duplicate(rim, "10_WheelRim_%d" % k, m)
            src["11_Tire_%d" % k] = duplicate(tire, "11_Tire_%d" % k, m)

    # --- koleksiyonlar ve malzemeler
    asm = bpy.data.collections.new("Assembly")
    plate = bpy.data.collections.new("Print_Plate")
    scene.collection.children.link(asm)
    scene.collection.children.link(plate)
    mats = {k: material(k, v) for k, v in COLORS.items()}

    def color_of(name):
        for key, spec in PRINT_SPEC.items():
            if name.startswith(key[:5]):
                return spec[3]
        return "black"

    for name, ob in src.items():
        scene.collection.objects.unlink(ob)
        asm.objects.link(ob)
        ob.data.materials.clear()
        ob.data.materials.append(mats[color_of(name)])
        for p in ob.data.polygons:
            p.use_smooth = False

    # --- STL disa aktarma (baski yonunde) + baski tablasi yerlesimi
    stl_dir = os.path.join(out_dir, "stl")
    asm_dir = os.path.join(out_dir, "assembly_stl")
    os.makedirs(stl_dir, exist_ok=True)
    os.makedirs(asm_dir, exist_ok=True)
    report = []
    cursor_x, cursor_y, row_h = 0.0, 0.0, 0.0
    for key, (fname, qty, rot, _) in PRINT_SPEC.items():
        ob = src[key]
        mat, size = print_matrix(ob, rot)
        write_stl(ob, os.path.join(stl_dir, fname), mat)
        report.append((fname, qty, size))
        if cursor_x + size[0] > 420:
            cursor_x, cursor_y, row_h = 0.0, cursor_y + row_h + 12, 0.0
        cp = duplicate(ob, "PRINT_" + key,
                       Matrix.Translation((cursor_x + size[0] / 2, -400 - cursor_y - size[1] / 2, 0)) @ mat)
        plate.objects.link(cp)
        cp.data.materials.clear()
        cp.data.materials.append(mats[PRINT_SPEC[key][3]])
        cursor_x += size[0] + 12
        row_h = max(row_h, size[1])
    for name, ob in src.items():
        write_stl(ob, os.path.join(asm_dir, name + ".stl"))

    with open(os.path.join(out_dir, "parts_report.txt"), "w") as f:
        f.write("dosya;adet;X;Y;Z (mm, baski yonunde)\n")
        for fname, qty, s in report:
            f.write("%s;%d;%.1f;%.1f;%.1f\n" % (fname, qty, *s))

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "dump_truck.blend"))
    return src


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0] if argv else os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))
    build(out)
    print("OK ->", out)
