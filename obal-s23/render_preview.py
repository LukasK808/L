"""Softvérový renderer náhľadu (numpy z-buffer) – nepotrebuje GPU ani internet."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from colors import COL_BLUE, COL_PURPLE, COL_WHITE

HERE = os.path.dirname(os.path.abspath(__file__))
M = np.load(os.path.join(HERE, ".preview_meshes.npz"))


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0


MAT = {  # farba, lesk
    "case": (hex2rgb("#151515"), 0.18),
    "white": (hex2rgb(COL_WHITE), 0.25),
    "blue": (hex2rgb(COL_BLUE), 0.3),
    "purple": (hex2rgb(COL_PURPLE), 0.3),
    "bezel": (hex2rgb(COL_PURPLE), 0.45),
    "phone": (hex2rgb("#2b2f36"), 0.9),
}


def rot(yaw, pitch, roll=0):
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return Rx @ Ry @ Rz


def render(parts, R, size=(900, 1300), scale=7.0, offsets=None, bg_top="#f3f1fb", bg_bot="#d9d4ee"):
    W, H = size
    img = np.zeros((H, W, 3))
    t = np.linspace(0, 1, H)[:, None, None]
    img[:] = hex2rgb(bg_top) * (1 - t) + hex2rgb(bg_bot) * t
    zbuf = np.full((H, W), -1e9)
    light = np.array([-0.45, 0.55, 0.70]); light /= np.linalg.norm(light)
    fill = np.array([0.6, -0.3, 0.5]); fill /= np.linalg.norm(fill)
    view = np.array([0, 0, 1.0])
    shadow_mask = np.zeros((H, W))
    for name in parts:
        tris = M[name].reshape(-1, 3, 3).copy()
        if offsets and name in offsets:
            tris += np.array(offsets[name])
        col, gloss = MAT[name]
        p = tris @ R.T
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        diff = np.clip(n @ light, 0, 1) * 0.75 + np.clip(n @ fill, 0, 1) * 0.25
        h = light + view; h /= np.linalg.norm(h)
        spec = np.clip(n @ h, 0, 1) ** 40 * gloss
        rim = (1 - np.abs(n @ view)) ** 3 * 0.12
        shade = col[None] * (0.28 + 0.8 * diff[:, None]) + spec[:, None] + rim[:, None]
        shade = np.clip(shade, 0, 1)
        xs = p[..., 0] * scale + W / 2
        ys = -p[..., 1] * scale + H / 2
        zs = p[..., 2]
        for i in range(len(p)):
            x0, x1 = int(max(xs[i].min(), 0)), int(min(xs[i].max() + 1, W))
            y0, y1 = int(max(ys[i].min(), 0)), int(min(ys[i].max() + 1, H))
            if x1 <= x0 or y1 <= y0:
                continue
            ax, ay = xs[i, 0], ys[i, 0]
            bx, by = xs[i, 1], ys[i, 1]
            cx, cy = xs[i, 2], ys[i, 2]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not inside.any():
                continue
            z = w0 * zs[i, 0] + w1 * zs[i, 1] + w2 * zs[i, 2]
            zb = zbuf[y0:y1, x0:x1]
            upd = inside & (z > zb)
            zb[upd] = z[upd]
            img[y0:y1, x0:x1][upd] = shade[i]
            shadow_mask[y0:y1, x0:x1][upd] = 1
    return img, shadow_mask


def to_pil(img, mask, ss):
    # mäkký tieň pod objektom
    W, H = img.shape[1], img.shape[0]
    sh = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28 * ss // 2))
    sh = np.roll(np.asarray(sh) / 255.0, (18 * ss // 2, 14 * ss // 2), (0, 1))
    obj = mask[..., None] > 0
    base = img * (1 - 0.28 * sh[..., None] * (~obj))
    out = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
    return out.resize((W // ss, H // ss), Image.LANCZOS)


SS = 2
deg = np.pi / 180
# 1) zadná strana 3/4 – obal + logo + rámik
R_back = rot(180 * deg + 28 * deg, -14 * deg, 4 * deg)
a, ma = render(["case", "white", "blue", "purple", "bezel"], R_back, size=(820 * SS, 1240 * SS), scale=6.6 * SS)
# 2) predná strana s telefónom
R_front = rot(-30 * deg, -16 * deg, -4 * deg)
b, mb = render(["case", "phone"], R_front, size=(820 * SS, 1240 * SS), scale=6.6 * SS)
# 3) detail kamery
R_cam = rot(180 * deg + 20 * deg, -30 * deg, 0)
c, mc = render(["case", "white", "blue", "purple", "bezel"], R_cam, size=(560 * SS, 560 * SS), scale=13 * SS,
               offsets={k: (-19.5, -45.5, 0) for k in ["case", "white", "blue", "purple", "bezel"]})

A, B, C = to_pil(a, ma, SS), to_pil(b, mb, SS), to_pil(c, mc, SS)

# Zloženie plagátu
PW, PH = 2280, 1420
poster = Image.new("RGB", (PW, PH), "#f3f1fb")
# hlavička v gradiente značky
hdr = np.zeros((150, PW, 3))
tt = np.linspace(0, 1, PW)[None, :, None]
hdr[:] = hex2rgb(COL_BLUE) * (1 - tt) + hex2rgb(COL_PURPLE) * tt
poster.paste(Image.fromarray((hdr * 255).astype(np.uint8)), (0, 0))
poster.paste(A, (20, 165))
poster.paste(B, (820, 165))
poster.paste(C, (1660, 200))
d = ImageDraw.Draw(poster)
fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
fr = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
d.text((40, 30), "Pr1nt1t.sk", font=F(fb, 56), fill="white")
d.text((44, 98), "3D tlačený obal  •  Samsung Galaxy S23  •  návrh v2", font=F(fr, 28), fill="#ece8ff")
d.text((PW - 40, 60), "NÁHĽAD", font=F(fb, 40), fill="white", anchor="ra")

d.text((60, 1385), "Zadná strana – logo vložené vo farbe", font=F(fb, 24), fill="#333", anchor="ls")
d.text((860, 1385), "Predná strana – ochranný okraj nad displejom", font=F(fb, 24), fill="#333", anchor="ls")
d.text((1680, 790), "Detail: vyvýšený rámik kamery", font=F(fb, 24), fill="#333")

# legenda materiálov
y = 860
d.text((1680, y), "Materiály a farby", font=F(fb, 30), fill="#222"); y += 52
for hexc, txt in [("#1a1a1a", "Telo obalu – TPU 95A, čierna"),
                  (COL_WHITE, f"„Pr1nt1t“ – PETG  {COL_WHITE}"),
                  (COL_BLUE, f"„.sk“ – PETG  {COL_BLUE}"),
                  (COL_PURPLE, f"Pásik + rámik kamery – PETG  {COL_PURPLE}")]:
    d.rounded_rectangle((1680, y, 1724, y + 44), 8, fill=hexc, outline="#888", width=2)
    d.text((1740, y + 22), txt, font=F(fr, 23), fill="#222", anchor="lm")
    y += 62
d.text((1680, y + 10), "Telefón: 146,3 × 70,9 × 7,6 mm\nStena 1,6 mm • Okraj +0,8 mm\nRámik kamery +1,4 mm",
       font=F(fr, 22), fill="#555", spacing=8)

out = os.path.join(HERE, "nahlad_obal_S23_Pr1nt1t.png")
poster.save(out)
print(out)
