"""
PR1NT 1T! (pr1nt1t.sk) – 3D tlačený obal pre Samsung Galaxy S23
Generuje STL súbory pre viacfarebnú tlač (TPU čierne telo + PLA/PETG farebné vložky).

Súradnice (pohľad spredu na displej): X = šírka (+X = strana s tlačidlami),
Y = dĺžka (+Y = horná hrana), Z = hrúbka (Z=0 je zadná strana telefónu, +Z = displej).

Spustenie:  pip install manifold3d shapely matplotlib numpy
            python3 generate_case.py
"""
import numpy as np
from manifold3d import Manifold, CrossSection, JoinType, FillRule, Mesh, set_circular_segments
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import affinity
import os

set_circular_segments(72)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(OUT, exist_ok=True)

# ---------------- Rozmery telefónu Galaxy S23 (mm) ----------------
PH_W, PH_L, PH_T = 70.9, 146.3, 7.6
PH_R = 9.0          # polomer rohov v pôdoryse
PH_EDGE = 1.0       # zaoblenie hrán rámu

# ---------------- Parametre obalu ----------------
CLR = 0.20          # vôľa medzi telefónom a TPU (TPU sa natiahne)
WALL = 1.6          # hrúbka bočnej steny
BACK = 1.6          # hrúbka zadnej steny
LIP = 0.8           # o koľko prečnieva okraj nad displej (ochrana pri položení)
LIP_IN = 1.0        # o koľko zasahuje okraj dovnútra cez displej
INLAY = 0.6         # hĺbka farebných vložiek loga (3 vrstvy po 0.2 mm)

# Farby značky (z webu pr1nt1t.sk)
from colors import COL_WHITE, COL_YELLOW, COL_BLACK

# Fotoaparáty (zo zadnej strany vľavo hore => v našich súradniciach +X)
TOP = PH_L / 2
CAM_X = PH_W / 2 - 16.0
CAM_Y = [TOP - 15.0, TOP - 27.6, TOP - 40.2]
CAM_D = 10.6
FLASH = (CAM_X - 12.6, TOP - 15.0, 4.6)


def rrect(w, l, r, d=0.0):
    """Zaoblený obdĺžnik (stred v 0) zväčšený o offset d."""
    base = CrossSection.square([w - 2 * r, l - 2 * r], center=True)
    return base.offset(r + d, JoinType.Round)


def rounded_block(w, l, r, d, z0, z1, rb, rt, n=8):
    """Hranol so zaoblenými spodnými (rb) a hornými (rt) hranami – hull tenkých plátov."""
    slabs = []
    eps = 0.01
    for i in range(n + 1):
        a = np.pi / 2 * i / n
        if rb > 0:
            z = z0 + rb - rb * np.cos(a)
            off = d - rb + rb * np.sin(a)
            slabs.append(rrect(w, l, r, off).extrude(eps).translate([0, 0, z]))
        if rt > 0:
            z = z1 - rt + rt * np.cos(a) - eps
            off = d - rt + rt * np.sin(a)
            slabs.append(rrect(w, l, r, off).extrude(eps).translate([0, 0, z]))
    if rb == 0:
        slabs.append(rrect(w, l, r, d).extrude(eps).translate([0, 0, z0]))
    if rt == 0:
        slabs.append(rrect(w, l, r, d).extrude(eps).translate([0, 0, z1 - eps]))
    return Manifold.batch_hull(slabs)


def pill(cx, cy, length, width):
    """Ovál (stadium) orientovaný pozdĺž Y."""
    c = CrossSection.circle(width / 2)
    return CrossSection.batch_hull([c.translate([cx, cy - (length - width) / 2]),
                                    c.translate([cx, cy + (length - width) / 2])])


def slot_x(y0, y1, zc, h, x0, x1):
    """Zaoblený výrez cez stenu v smere X (bočné tlačidlá)."""
    r = h / 2
    cyl = Manifold.cylinder(x1 - x0, r).rotate([0, 90, 0]).translate([x0, 0, zc])
    return Manifold.batch_hull([cyl.translate([0, y0 + r, 0]), cyl.translate([0, y1 - r, 0])])


def slot_y(x0, x1, zc, h, y0, y1):
    r = h / 2
    cyl = Manifold.cylinder(y1 - y0, r).rotate([-90, 0, 0]).translate([0, y0, zc])
    return Manifold.batch_hull([cyl.translate([x0 + r, 0, 0]), cyl.translate([x1 - r, 0, 0])])


def text_cs(txt, size, font="DejaVu Sans", weight="bold"):
    """Text -> shapely geometria (even-odd), mierka v mm."""
    fp = FontProperties(family=font, weight=weight)
    tp = TextPath((0, 0), txt, size=size, prop=fp)
    geom = None
    for poly in tp.to_polygons():
        if len(poly) < 3:
            continue
        p = Polygon(poly).buffer(0)
        geom = p if geom is None else geom.symmetric_difference(p)
    return geom


def shp_to_cs(geom):
    polys = []
    gs = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    for g in gs:
        g = orient(g, 1.0)
        polys.append(np.array(g.exterior.coords[:-1]))
        for h in g.interiors:
            polys.append(np.array(h.coords[:-1]))
    return CrossSection(polys, FillRule.EvenOdd)


# ================= TELO OBALU (TPU) =================
Z_BACK = -CLR - BACK
Z_TOP = PH_T + CLR + LIP
outer = rounded_block(PH_W, PH_L, PH_R, CLR + WALL, Z_BACK, Z_TOP, rb=1.6, rt=0.9)
cavity = rounded_block(PH_W, PH_L, PH_R, CLR, -CLR, PH_T + CLR, rb=PH_EDGE, rt=PH_EDGE + 0.3)
opening = rrect(PH_W, PH_L, PH_R, -LIP_IN).extrude(5).translate([0, 0, PH_T - 1.0])
case = outer - cavity - opening

# Fotoaparáty – ovál cez všetky 3 šošovky
cam_len = (CAM_Y[0] - CAM_Y[2]) + CAM_D + 2.0
cam_w = CAM_D + 2.0
cam_cy = (CAM_Y[0] + CAM_Y[2]) / 2
cam_cut = pill(CAM_X, cam_cy, cam_len, cam_w)
BEZ_SPIGOT = 1.2      # hrúbka „čapu“ rámika, ktorý ide do otvoru v TPU
cam_hole = cam_cut.offset(BEZ_SPIGOT, JoinType.Round)
case -= cam_hole.extrude(10).translate([0, 0, Z_BACK - 2])
# Blesk
case -= Manifold.cylinder(10, FLASH[2] / 2).translate([FLASH[0], FLASH[1], Z_BACK - 2])

# Bočné tlačidlá (+X): hlasitosť + power
zc = PH_T / 2
case -= slot_x(TOP - 62, TOP - 24, zc, 4.6, PH_W / 2 - 1, PH_W / 2 + 5)
# Spodok: USB-C, reproduktor, mikrofón, SIM
BOT = -PH_L / 2
case -= slot_y(-24, 24, zc, 4.2, BOT - 5, BOT + 1)
case -= slot_y(-6.5, 6.5, zc, 6.8, BOT - 5, BOT + 1)
# Vrchný mikrofón
case -= Manifold.cylinder(6, 1.0).rotate([-90, 0, 0]).translate([-8.0, TOP - 1, zc])

# ================= LOGO „PR1NT 1T!“ podľa webu pr1nt1t.sk =================
# „PR1NT“ biela (rovné písmo), „1T!“ žltá kurzíva – Barlow Condensed Bold.
# Text sa číta zo zadnej strany => zrkadlíme X.
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
def text_font(txt, size, fname):
    tp = TextPath((0, 0), txt, size=size, prop=FontProperties(fname=os.path.join(FONT_DIR, fname)))
    geom = None
    for poly in tp.to_polygons():
        if len(poly) < 3:
            continue
        q = Polygon(poly).buffer(0)
        geom = q if geom is None else geom.symmetric_difference(q)
    return geom

SIZE = 10.0
main = text_font("PR1NT", SIZE, "BarlowCondensed-Bold.ttf")
accent = text_font("1T!", SIZE, "BarlowCondensed-BoldItalic.ttf")
ACCENT_EXTRA_SKEW = 12.0   # extra sklon „1T!“ v stupňoch (navyše ku kurzíve fontu)
accent = affinity.skew(accent, xs=ACCENT_EXTRA_SKEW, origin=(0, 0))
accent = affinity.translate(accent, main.bounds[2] + 0.22 * SIZE - accent.bounds[0], 0)
full = unary_union([main, accent])
minx, miny, maxx, maxy = full.bounds
target_w = 60.0   # šírka loga v mm (zadná strana má ~74 mm)
s = target_w / (maxx - minx)
LOGO_Y = 0.0      # stred zadnej strany
def place(g):
    g = affinity.translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    g = affinity.scale(g, -s, s, origin=(0, 0))       # zrkadlenie pre zadnú stranu
    return affinity.translate(g, 0, LOGO_Y)
main_p = place(main)
accent_p = place(accent)

def inlay(geom):
    return shp_to_cs(geom).extrude(INLAY).translate([0, 0, Z_BACK])

logo_white = inlay(main_p)
logo_yellow = inlay(accent_p)
case = case - logo_white - logo_yellow

# ================= Rámik fotoaparátu (PETG žltý, samostatný diel) =================
BEZ_H = 1.4   # o koľko vystúpi nad zadnú stranu obalu (ochrana šošoviek)
bez_outer = cam_cut.offset(BEZ_SPIGOT + 2.0, JoinType.Round)
flange = (bez_outer - cam_cut).extrude(BEZ_H).translate([0, 0, Z_BACK - BEZ_H])
spigot = (cam_hole - cam_cut).extrude(BACK - 0.05).translate([0, 0, Z_BACK])
bezel = flange + spigot
# jemné zaoblenie hornej hrany rámika – zošikmenie vnútra
chamf = Manifold.batch_hull([
    cam_cut.offset(0.6, JoinType.Round).extrude(0.01).translate([0, 0, Z_BACK - BEZ_H - 0.01]),
    cam_cut.extrude(0.01).translate([0, 0, Z_BACK - BEZ_H + 0.6])])
bezel -= chamf

# Atrapa telefónu (iba pre náhľad)
phone = rounded_block(PH_W, PH_L, PH_R, 0, 0, PH_T, rb=PH_EDGE, rt=PH_EDGE)


def save_stl(man, name):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    path = os.path.join(OUT, name)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    data = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"] = n
    data["v"] = tri
    with open(path, "wb") as f:
        f.write(b"PR1NT 1T! Galaxy S23 case".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(data.tobytes())
    print(f"{name:32s} {len(t):7d} tri  vol {man.volume()/1000:6.2f} cm3")
    return v, t


PARTS = {
    "01_obal_TPU_cierny.stl": (case, COL_BLACK),
    "02_logo_PR1NT_biela.stl": (logo_white, COL_WHITE),
    "03_logo_1T_zlta_f3c927.stl": (logo_yellow, COL_YELLOW),
    "04_ramik_kamery_zlta_f3c927.stl": (bezel, COL_YELLOW),
}

if __name__ == "__main__":
    for name, (m, _) in PARTS.items():
        save_stl(m, name)
    np.savez_compressed(os.path.join(OUT, "..", ".preview_meshes.npz"),
                        **{k: np.concatenate([np.asarray(m.to_mesh().vert_properties)[:, :3][np.asarray(m.to_mesh().tri_verts)].reshape(-1, 9)])
                           for k, m in [("case", case), ("white", logo_white), ("yellow", logo_yellow),
                                        ("bezel", bezel), ("phone", phone)]})
