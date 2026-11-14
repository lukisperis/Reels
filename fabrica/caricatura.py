"""Dibujos animados planos (estilo cartoon vectorial) generados por código.

Los personajes se dibujan con formas simples y contorno grueso, así son SIEMPRE iguales en todos
los episodios y se pueden animar: parpadeo, boca al hablar, poses, expresiones y cambios de
"glow up" (cuerpo, pelo, barba, ropa) que se van aplicando día a día.
"""
import math
import random
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from . import W, H

K = 2                       # supersampling para bordes suaves
OUT = (28, 24, 40)          # color del contorno
OL = 9                      # grosor del contorno (a escala K)
SW, SH = 600, 1150          # tamaño del sprite de personaje (1x)
FUENTES = Path(__file__).parent / "fuentes"
F_CARTOON = str(FUENTES / "LuckiestGuy.woff")
F_TITULAR = str(FUENTES / "Anton.woff")


def fuente(ruta, tam):
    return _fuente(ruta, int(tam))


@lru_cache(maxsize=64)
def _fuente(ruta, tam):
    return ImageFont.truetype(ruta, tam)


def _osc(c, f=0.8):
    return tuple(int(v * f) for v in c[:3])


# ---------------------------------------------------------------------------
# Primitivas con contorno
# ---------------------------------------------------------------------------
class Lienzo:
    def __init__(self, w, h, fondo=(0, 0, 0, 0)):
        self.im = Image.new("RGBA", (w * K, h * K), fondo)
        self.d = ImageDraw.Draw(self.im)

    def _s(self, v):
        return [x * K for x in v]

    def elipse(self, box, fill, ol=True):
        self.d.ellipse(self._s(box), fill=fill, outline=OUT if ol else None, width=OL if ol else 0)

    def rect(self, box, fill, r=20, ol=True):
        self.d.rounded_rectangle(self._s(box), r * K, fill=fill, outline=OUT if ol else None, width=OL if ol else 0)

    def poli(self, pts, fill, ol=True):
        self.d.polygon([(x * K, y * K) for x, y in pts], fill=fill, outline=OUT if ol else None,
                       width=OL if ol else 0)

    def linea(self, pts, color=OUT, ancho=6, redondo=True):
        p = [(x * K, y * K) for x, y in pts]
        self.d.line(p, fill=color, width=int(ancho * K), joint="curve")
        if redondo:
            r = ancho * K / 2
            for x, y in (p[0], p[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def miembro(self, pts, ancho, color):
        """Brazo/pierna: tubo con contorno."""
        self.linea(pts, OUT, ancho + 2 * OL / K)
        self.linea(pts, color, ancho)

    def texto(self, xy, txt, tam, color, ruta=F_TITULAR, anchor="mm", borde=0, borde_color=OUT):
        self.d.text((xy[0] * K, xy[1] * K), txt, font=fuente(ruta, tam * K), fill=color, anchor=anchor,
                    stroke_width=int(borde * K), stroke_fill=borde_color)

    def final(self, escala=1.0):
        w, h = self.im.size
        return self.im.resize((max(1, int(w / K * escala)), max(1, int(h / K * escala))), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Personajes
# ---------------------------------------------------------------------------
BASE = dict(piel=(246, 196, 150), pelo=(70, 45, 30), estilo_pelo="corto", barba=0.0, barba_completa=False,
            camiseta=(80, 140, 230), pantalon=(50, 60, 110), zapatos=(240, 240, 240), suela=(230, 120, 40),
            cuerpo="normal", ojeras=False, mancha=False, chica=False, labios=(220, 80, 110), gafas=False,
            tirantes=False, granos=0, bigote=False, traje=None, corbata=(200, 40, 50), cadena=False,
            botones=False, bolsillo=False, arrugas=False)

CUERPOS = {  # ancho torso arriba, ancho cintura, grosor brazo, grosor pierna
    "flaco": (170, 165, 32, 40), "normal": (220, 215, 42, 50), "gordo": (270, 330, 50, 60),
    "atletico": (270, 200, 52, 54), "musculoso": (340, 220, 72, 62), "chica": (180, 160, 32, 40),
}

EXPRESIONES = {  # cejas, ojos, boca
    "neutro": ("planas", "normal", "neutro"), "feliz": ("arriba", "normal", "sonrisa"),
    "triste": ("tristes", "normal", "triste"), "sorpresa": ("muy_arriba", "pequenos", "o"),
    "decidido": ("enfado", "normal", "apretada"), "enfadado": ("enfado", "pequenos", "mueca"),
    "cansado": ("planas", "cansado", "neutro"), "asco": ("una", "normal", "mueca"),
    "enamorado": ("arriba", "corazon", "sonrisa"), "dolor": ("tristes", "x", "o"),
    "chulo": ("una", "normal", "brillo"), "llorar": ("tristes", "cerrados", "triste"),
    "esfuerzo": ("enfado", "cerrados", "mueca"), "euforia": ("muy_arriba", "cerrados", "sonrisa"),
}


def _cabeza(L, p, expr, boca_abierta, parpadeo, mirada):
    cx, cy = 300, 360
    piel = p["piel"]
    cejas, ojos, boca = EXPRESIONES.get(expr, EXPRESIONES["neutro"])
    if parpadeo and ojos not in ("x", "corazon"):
        ojos = "cerrados"
    if boca_abierta:
        boca = "habla" if boca_abierta == 1 else "o"
        if boca_abierta == 2 and cejas == "planas":
            cejas = "arriba"
        elif boca_abierta == 2 and cejas == "arriba":
            cejas = "muy_arriba"
    # orejas
    for ox in (cx - 140, cx + 140):
        L.elipse((ox - 28, cy - 5, ox + 28, cy + 55), piel)
    # cara
    L.rect((cx - 140, cy - 165, cx + 140, cy + 170), piel, r=120)
    # coloretes
    for ox in (cx - 85, cx + 85):
        L.elipse((ox - 30, cy + 55, ox + 30, cy + 85), (255, 150, 150, 120) if not p["chica"] else (255, 120, 140, 160),
                 ol=False)
    # barba de 3 días / barba
    rnd = random.Random(7)
    if p["barba"] > 0:
        for _ in range(int(140 * p["barba"])):
            a = rnd.uniform(0.15, 0.85) * math.pi
            r = rnd.uniform(0.55, 1.0)
            x = cx + math.cos(a) * 125 * r
            y = cy + 70 + math.sin(a) * 95 * r
            L.elipse((x - 3, y - 3, x + 3, y + 3), _osc(p["pelo"], 0.8), ol=False)
    if p["barba_completa"]:
        L.poli([(cx - 135, cy + 40), (cx - 120, cy + 140), (cx - 50, cy + 190), (cx + 50, cy + 190),
                (cx + 120, cy + 140), (cx + 135, cy + 40), (cx + 70, cy + 110), (cx - 70, cy + 110)], p["pelo"])
    # granos
    for i in range(p["granos"]):
        x, y = cx - 100 + (i * 73) % 200, cy - 80 + (i * 41) % 60
        L.elipse((x - 7, y - 7, x + 7, y + 7), (230, 90, 90), ol=False)
    # ojos
    for k, ox in enumerate((cx - 55, cx + 55)):
        if ojos == "cerrados":
            L.linea([(ox - 30, cy + 2), (ox, cy + 14), (ox + 30, cy + 2)], OUT, 8)
        elif ojos == "x":
            L.linea([(ox - 22, cy - 22), (ox + 22, cy + 22)], OUT, 9)
            L.linea([(ox + 22, cy - 22), (ox - 22, cy + 22)], OUT, 9)
        else:
            L.elipse((ox - 34, cy - 40, ox + 34, cy + 40), (255, 255, 255))
            if ojos == "corazon":
                L.poli([(ox, cy + 26), (ox - 26, cy - 2), (ox - 20, cy - 20), (ox, cy - 10), (ox + 20, cy - 20),
                        (ox + 26, cy - 2)], (235, 50, 80), ol=False)
            else:
                pr = 9 if ojos == "pequenos" else 15
                px, py = ox + mirada[0] * 10, cy + 6 + mirada[1] * 10
                L.elipse((px - pr, py - pr, px + pr, py + pr), OUT, ol=False)
                L.elipse((px - pr + 4, py - pr + 3, px - pr + 11, py - pr + 10), (255, 255, 255), ol=False)
            if ojos == "cansado":
                L.d.chord([(ox - 36) * K, (cy - 42) * K, (ox + 36) * K, (cy + 42) * K], 180, 360, fill=piel)
                L.linea([(ox - 34, cy), (ox + 34, cy)], OUT, 7)
            if p["chica"]:
                for dx in (-28, -16, -4) if k == 0 else (4, 16, 28):
                    L.linea([(ox + dx, cy - 36), (ox + dx * 1.3, cy - 54)], OUT, 5)
        if p["ojeras"]:
            L.d.arc([(ox - 30) * K, (cy + 25) * K, (ox + 30) * K, (cy + 60) * K], 20, 160, fill=(150, 90, 160),
                    width=6 * K)
    if p["gafas"]:
        for ox in (cx - 55, cx + 55):
            L.d.rounded_rectangle([(ox - 48) * K, (cy - 38) * K, (ox + 48) * K, (cy + 38) * K], 14 * K,
                                  outline=OUT, width=10 * K)
        L.linea([(cx - 7, cy - 5), (cx + 7, cy - 5)], OUT, 9)
    # cejas
    cejas_pts = {
        "planas": [((-85, -62), (-25, -62)), ((25, -62), (85, -62))],
        "arriba": [((-85, -70), (-25, -78)), ((25, -78), (85, -70))],
        "muy_arriba": [((-85, -88), (-25, -98)), ((25, -98), (85, -88))],
        "tristes": [((-85, -58), (-25, -80)), ((25, -80), (85, -58))],
        "enfado": [((-85, -80), (-22, -55)), ((22, -55), (85, -80))],
        "una": [((-85, -62), (-25, -62)), ((25, -90), (85, -76))],
    }[cejas]
    for (a, b) in cejas_pts:
        L.linea([(cx + a[0], cy + a[1]), (cx + b[0], cy + b[1])], _osc(p["pelo"], 0.7) if p["pelo"] != OUT else OUT, 13)
    # nariz
    L.d.arc([(cx - 18) * K, (cy + 30) * K, (cx + 18) * K, (cy + 62) * K], 200, 340, fill=_osc(piel, 0.65), width=7 * K)
    if p["arrugas"]:
        for dy in (-125, -108):
            L.d.arc([(cx - 70) * K, (cy + dy) * K, (cx + 70) * K, (cy + dy + 30) * K], 200, 340, fill=_osc(piel, 0.7), width=5 * K)
    # boca
    by = cy + 105
    roja = (150, 30, 50)
    if boca == "neutro":
        L.linea([(cx - 32, by), (cx + 32, by - 3)], OUT, 8)
    elif boca == "apretada":
        L.linea([(cx - 38, by), (cx + 38, by)], OUT, 9)
    elif boca == "triste":
        L.d.arc([(cx - 40) * K, (by - 5) * K, (cx + 40) * K, (by + 40) * K], 200, 340, fill=OUT, width=8 * K)
    elif boca in ("sonrisa", "brillo"):
        L.d.chord([(cx - 60) * K, (by - 40) * K, (cx + 60) * K, (by + 45) * K], 0, 180, fill=roja, outline=OUT,
                  width=OL)
        L.d.rectangle([(cx - 48) * K, (by + 2) * K, (cx + 48) * K, (by + 18) * K], fill=(255, 255, 255))
        if boca == "brillo":
            _destello(L, cx + 50, by + 10, 22)
    elif boca in ("o", "habla"):
        rx, ry = (26, 34) if boca == "o" else (24, 20)
        L.elipse((cx - rx, by - ry + 8, cx + rx, by + ry + 8), roja)
        L.elipse((cx - rx * 0.6, by + ry * 0.2 + 8, cx + rx * 0.6, by + ry + 4), (235, 100, 110), ol=False)
    elif boca == "mueca":
        L.rect((cx - 50, by - 16, cx + 50, by + 18), (255, 255, 255), r=8)
        for dx in (-25, 0, 25):
            L.linea([(cx + dx, by - 14), (cx + dx, by + 16)], OUT, 4, redondo=False)
        L.linea([(cx - 48, by + 1), (cx + 48, by + 1)], OUT, 4, redondo=False)
    if p["bigote"]:
        bc = p.get("color_bigote", p["pelo"])
        L.poli([(cx - 75, by - 12), (cx - 55, by - 38), (cx - 10, by - 42), (cx, by - 32), (cx + 10, by - 42),
                (cx + 55, by - 38), (cx + 75, by - 12), (cx + 35, by - 22), (cx, by - 18), (cx - 35, by - 22)], bc)
    if p["chica"] and boca in ("neutro", "apretada"):
        L.elipse((cx - 26, by - 10, cx + 26, by + 10), p["labios"])
    # pelo delante
    est = p["estilo_pelo"]
    pc = p["pelo"]
    if est == "greñas":
        L.poli([(150, 330), (140, 230), (175, 170), (230, 140), (300, 128), (370, 140), (430, 175), (455, 240),
                (455, 330), (430, 300), (420, 250), (395, 280), (370, 230), (330, 262), (300, 220), (260, 262),
                (230, 225), (200, 280), (180, 250), (172, 300)], pc)
        L.poli([(145, 300), (125, 420), (150, 470), (168, 360)], pc)
        L.poli([(455, 300), (475, 420), (450, 470), (432, 360)], pc)
    elif est == "corto":
        L.poli([(162, 300), (165, 230), (210, 170), (300, 150), (390, 170), (435, 230), (438, 300), (405, 245),
                (330, 230), (250, 240), (195, 260)], pc)
    elif est == "degradado":
        L.poli([(165, 290), (175, 215), (220, 170), (300, 150), (380, 170), (425, 215), (435, 290), (400, 225),
                (300, 200), (200, 225)], pc)
        L.poli([(220, 175), (260, 120), (330, 110), (380, 150), (300, 185)], pc)
    elif est == "tupe":
        L.poli([(165, 290), (170, 220), (205, 150), (260, 90), (350, 80), (420, 120), (440, 200), (435, 290),
                (400, 220), (300, 205), (200, 230)], pc)
    elif est in ("largo", "melena"):
        L.poli([(160, 330), (165, 225), (220, 165), (300, 150), (380, 165), (440, 225), (440, 330), (400, 240),
                (330, 215), (300, 250), (260, 215), (200, 245)], pc)
    elif est == "calvo":
        for lado in (-1, 1):
            x0 = cx + lado * 140
            L.poli([(x0, cy - 80), (x0 + lado * 18, cy - 40), (x0 + lado * 10, cy + 10), (x0 - lado * 22, cy + 20),
                    (x0 - lado * 25, cy - 60)], pc)
        L.d.arc([(cx - 60) * K, (cy - 150) * K, (cx - 10) * K, (cy - 110) * K], 200, 300, fill=(255, 255, 255), width=6 * K)
    elif est == "engominado":
        L.poli([(160, 300), (162, 220), (200, 165), (300, 140), (400, 165), (440, 220), (440, 300), (420, 240),
                (300, 215), (180, 240)], pc)
        for dx in (-50, 0, 50):
            L.linea([(cx + dx - 30, 175), (cx + dx + 30, 170)], _osc(pc, 1.6) if max(pc) < 150 else (255, 255, 255), 5)
    elif est == "rizos":
        for i, (x, y) in enumerate(((175, 260), (200, 195), (255, 160), (320, 150), (385, 170), (425, 220), (430, 285),
                                    (300, 175), (230, 215), (360, 210))):
            L.elipse((x - 48, y - 45, x + 48, y + 45), pc)
    elif est == "rapado":
        L.d.chord([(cx - 140) * K, (cy - 165) * K, (cx + 140) * K, (cy + 60) * K], 180, 360, fill=pc + (110,))


def _destello(L, x, y, r):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.35
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    L.poli(pts, (255, 255, 255), ol=False)


def _brazos(accion, p, sl, sr, grosor, fase=0.0):
    """Devuelve [(puntos_brazo_izq), (puntos_brazo_der)] y si lleva objeto."""
    if accion == "gesto":
        a = math.sin(fase * 2 * math.pi)
        return [[sl, (sl[0] - 15, 690), (sl[0] - 8, 800)],
                [sr, (sr[0] + 100, 610 - 20 * a), (sr[0] + 85 + 30 * a, 500 - 50 * a)]]
    if accion == "jugar":
        return [[sl, (sl[0] - 20, 690), (260, 725)], [sr, (sr[0] + 20, 690), (340, 725)]]
    if accion == "movil":
        return [[sl, (sl[0] - 15, 690), (sl[0] - 5, 800)], [sr, (sr[0] + 40, 690), (sr[0] - 40, 560)]]
    if accion in ("arriba", "celebrar"):
        return [[sl, (sl[0] - 70, 450), (sl[0] - 80, 340)], [sr, (sr[0] + 70, 450), (sr[0] + 80, 340)]]
    if accion == "musculo":
        return [[sl, (sl[0] - 110, 570), (sl[0] - 95, 430)], [sr, (sr[0] + 110, 570), (sr[0] + 95, 430)]]
    if accion == "cruzados":
        return [[sl, (sl[0] - 15, 680), (sr[0] - 10, 660)], [sr, (sr[0] + 15, 680), (sl[0] + 10, 640)]]
    if accion == "señalar":
        return [[sl, (sl[0] - 15, 690), (sl[0] - 5, 800)], [sr, (sr[0] + 90, 560), (sr[0] + 200, 540)]]
    if accion == "manos_cara":
        return [[sl, (sl[0] - 30, 640), (240, 470)], [sr, (sr[0] + 30, 640), (360, 470)]]
    return [[sl, (sl[0] - 15, 690), (sl[0] - 8, 800)], [sr, (sr[0] + 15, 690), (sr[0] + 8, 800)]]


def dibujar_personaje(p, expr="neutro", accion="quieto", boca_abierta=False, parpadeo=False,
                      mirada=(0, 0), fase=0.0):
    p = {k: tuple(v) if isinstance(v, list) else v for k, v in {**BASE, **p}.items()}
    L = Lienzo(SW, SH)
    cuerpo = "chica" if p["chica"] and p["cuerpo"] == "normal" else p["cuerpo"]
    ta, tc, gb, gp = CUERPOS[cuerpo]
    cx = 300
    top, cintura = 540, 830
    # pelo largo por detrás (antes que el cuerpo)
    if p["estilo_pelo"] in ("largo", "melena"):
        L.poli([(150, 330), (170, 200), (300, 160), (430, 200), (450, 330), (440, 600), (160, 600)], p["pelo"])
    # piernas
    sep = gp * 0.8
    if accion == "correr":
        a = math.sin(fase * 2 * math.pi) * 0.5
        piernas = [[(cx - sep, cintura - 20), (cx - sep + math.sin(a) * 180, cintura + 230)],
                   [(cx + sep, cintura - 20), (cx + sep - math.sin(a) * 180, cintura + 230)]]
    else:
        piernas = [[(cx - sep, cintura - 20), (cx - sep - 5, 1060)], [(cx + sep, cintura - 20), (cx + sep + 5, 1060)]]
    for pts in piernas:
        L.miembro(pts, gp, p["pantalon"] if not p["chica"] else p["piel"])
        x, y = pts[-1]
        L.elipse((x - 55, y - 15, x + 55, y + 45), p["zapatos"])
        L.rect((x - 55, y + 28, x + 55, y + 45), p["suela"], r=8)
    # brazos (detrás del torso en los hombros)
    sl, sr = (cx - ta / 2 + 18, top + 40), (cx + ta / 2 - 18, top + 40)
    brazos = _brazos(accion, p, sl, sr, gb, fase)
    manga = p["camiseta"] if not p["tirantes"] else p["piel"]
    delante = accion in ("jugar", "cruzados", "manos_cara", "movil")

    def pintar_brazos():
        for pts in brazos:
            _brazo(pts)

    def _brazo(pts):
        L.miembro(pts, gb, p["piel"])
        if not p["tirantes"]:
            L.miembro([pts[0], ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)], gb + 10, manga)
        if accion == "musculo":
            mx, my = (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2 - 20
            L.elipse((mx - gb * 0.75, my - gb * 0.7, mx + gb * 0.75, my + gb * 0.5), p["piel"])

    if not delante:
        pintar_brazos()
    # cuello
    L.rect((cx - 40, top - 60, cx + 40, top + 20), p["piel"], r=10)
    # torso
    falda = p["chica"]
    bajo = cintura + (80 if falda else 0)
    ancho_bajo = tc + (90 if falda else 0)
    L.poli([(cx - ta / 2, top + 20), (cx - ta / 2 + 25, top), (cx + ta / 2 - 25, top), (cx + ta / 2, top + 20),
            (cx + ancho_bajo / 2, bajo), (cx - ancho_bajo / 2, bajo)], p["camiseta"])
    if p["cuerpo"] in ("atletico", "musculoso"):
        L.d.arc([(cx - 100) * K, (top + 40) * K, (cx - 5) * K, (top + 150) * K], 20, 160, fill=_osc(p["camiseta"], 0.75), width=6 * K)
        L.d.arc([(cx + 5) * K, (top + 40) * K, (cx + 100) * K, (top + 150) * K], 20, 160, fill=_osc(p["camiseta"], 0.75), width=6 * K)
        for yy in (top + 180, top + 225):
            L.linea([(cx - 35, yy), (cx + 35, yy)], _osc(p["camiseta"], 0.75), 5)
    if p["cuerpo"] == "gordo":
        L.d.arc([(cx - 110) * K, (bajo - 140) * K, (cx + 110) * K, (bajo + 10) * K], 30, 150, fill=_osc(p["camiseta"], 0.75), width=6 * K)
    if p["traje"]:
        tc_ = p["traje"]
        L.poli([(cx - 45, top), (cx, top + 170), (cx + 45, top)], (250, 250, 250))
        L.poli([(cx - 14, top + 25), (cx + 14, top + 25), (cx + 10, top + 150), (cx, top + 175), (cx - 10, top + 150)],
               p["corbata"])
        L.poli([(cx - 45, top), (cx - 5, top + 175), (cx - 70, top + 60)], tc_)
        L.poli([(cx + 45, top), (cx + 5, top + 175), (cx + 70, top + 60)], tc_)
    if p["botones"]:
        L.linea([(cx, top + 30), (cx, bajo)], _osc(p["camiseta"], 0.7), 5, redondo=False)
        for yy in range(top + 70, int(bajo) - 20, 70):
            L.elipse((cx + 10, yy - 10, cx + 30, yy + 10), (240, 220, 180))
    if p["bolsillo"]:
        L.rect((cx - 70, bajo - 120, cx + 70, bajo - 40), _osc(p["camiseta"], 0.88), r=16)
    if p["cadena"]:
        L.d.arc([(cx - 70) * K, (top - 60) * K, (cx + 70) * K, (top + 110) * K], 20, 160, fill=(250, 200, 40), width=10 * K)
        L.elipse((cx - 16, top + 95, cx + 16, top + 127), (250, 200, 40))
    if p["mancha"]:
        L.elipse((cx + 10, top + 120, cx + 70, top + 165), (170, 120, 60, 200), ol=False)
        L.elipse((cx - 60, top + 190, cx - 25, top + 215), (170, 120, 60, 200), ol=False)
    # cuello de camiseta
    if not p["traje"]:
        L.d.chord([(cx - 45) * K, (top - 30) * K, (cx + 45) * K, (top + 40) * K], 0, 180, fill=p["piel"],
                  outline=OUT, width=OL)
    if delante:
        pintar_brazos()
    # manos y objetos
    for pts in brazos:
        x, y = pts[-1]
        L.elipse((x - gb * 0.75, y - gb * 0.75, x + gb * 0.75, y + gb * 0.75), p["piel"])
    if accion == "jugar":
        L.rect((cx - 90, 700, cx + 90, 760), (45, 45, 55), r=28)
        L.elipse((cx + 30, 715, cx + 50, 735), (230, 60, 80), ol=False)
        L.elipse((cx - 55, 715, cx - 35, 735), (90, 200, 120), ol=False)
    if accion == "movil":
        x, y = brazos[1][-1]
        L.rect((x - 35, y - 75, x + 35, y + 55), (35, 35, 45), r=12)
        L.rect((x - 26, y - 64, x + 26, y + 40), (120, 200, 255), r=6, ol=False)
    # cabeza
    _cabeza(L, p, expr, boca_abierta, parpadeo, mirada)
    return L.final()


# ---------------------------------------------------------------------------
# Fondos
# ---------------------------------------------------------------------------
SUELO = {"despacho": 1700, "garaje": 1780, "bar": 1700, "dormitorio": 1720, "espejo": 1800, "rayos": 1760, "gimnasio": 1720, "parque": 1740, "movil": 1900,
         "calle": 1740, "plano": 1760}


def _pared_rayas(L, color, y1):
    L.d.rectangle([0, 0, W * K, y1 * K], fill=color)
    for x in range(0, W, 90):
        L.d.rectangle([x * K, 0, (x + 45) * K, y1 * K], fill=_osc(color, 0.92))


def _suelo_madera(L, y0, color=(150, 95, 60)):
    L.d.rectangle([0, y0 * K, W * K, H * K], fill=color)
    for i, y in enumerate(range(y0, H, 70)):
        L.d.line([0, y * K, W * K, y * K], fill=_osc(color, 0.8), width=4 * K)
        for x in range((i % 2) * 120, W, 240):
            L.d.line([x * K, y * K, x * K, (y + 70) * K], fill=_osc(color, 0.8), width=4 * K)


@lru_cache(maxsize=16)
def fondo(nombre, variante=0):
    L = Lienzo(W, H, (255, 255, 255, 255))
    if nombre in ("dormitorio", "movil"):
        _pared_rayas(L, (82, 70, 150), 1340)
        _suelo_madera(L, 1340)
        # ventana con luna
        L.rect((620, 280, 1000, 760), (25, 30, 80), r=6)
        for sx, sy in ((680, 340), (900, 330), (760, 450), (950, 520), (700, 620), (840, 690), (650, 520)):
            L.elipse((sx - 5, sy - 5, sx + 5, sy + 5), (255, 255, 230), ol=False)
        L.elipse((850, 360, 950, 460), (255, 240, 170), ol=False)
        L.elipse((820, 345, 920, 445), (25, 30, 80), ol=False)
        L.linea([(810, 280), (810, 760)], OUT, 12)
        L.linea([(620, 520), (1000, 520)], OUT, 12)
        L.rect((590, 250, 660, 820), (60, 160, 120), r=10)
        L.rect((960, 250, 1030, 820), (60, 160, 120), r=10)
        L.rect((570, 230, 1050, 260), (120, 80, 50), r=8)
        # póster de pizza
        L.rect((90, 330, 380, 720), (255, 200, 60), r=8)
        L.poli([(235, 400), (140, 640), (330, 640)], (250, 170, 60))
        L.poli([(235, 400), (150, 615), (320, 615)], (255, 220, 120), ol=False)
        for px, py in ((235, 520), (200, 585), (270, 580)):
            L.elipse((px - 20, py - 20, px + 20, py + 20), (210, 60, 50), ol=False)
        L.texto((235, 680), "PIZZA LOVER", 40, OUT)
        # escritorio con ordenador
        L.rect((40, 1150, 470, 1190), (130, 85, 55), r=8)
        L.rect((70, 1190, 100, 1450), (110, 70, 45), r=6)
        L.rect((410, 1190, 440, 1450), (110, 70, 45), r=6)
        L.rect((90, 880, 420, 1110), (40, 40, 55), r=14)
        L.rect((110, 900, 400, 1090), (120, 70, 220), r=6, ol=False)
        for i, hgt in enumerate((60, 120, 90, 150, 110)):
            L.d.rectangle([(130 + i * 55) * K, (1080 - hgt) * K, (165 + i * 55) * K, 1080 * K], fill=(90, 240, 170))
        L.rect((230, 1110, 280, 1150), (40, 40, 55), r=4)
        # cama
        L.rect((690, 1180, 1100, 1500), (230, 110, 60), r=30)
        L.rect((720, 1150, 900, 1250), (250, 250, 250), r=30)
        L.rect((680, 1450, 1100, 1530), (120, 80, 50), r=10)
        # caja de pizza y latas
        L.poli([(380, 1800), (620, 1780), (650, 1850), (400, 1880)], (215, 170, 110))
        L.rect((800, 1760, 850, 1850), (220, 60, 60), r=10)
        L.rect((870, 1790, 920, 1860), (60, 160, 230), r=10)
        # alfombra
        L.elipse((220, 1620, 860, 1820), (190, 80, 90), ol=False)
    elif nombre == "bar":
        L.d.rectangle([0, 0, W * K, H * K], fill=(235, 150, 80))
        for x in range(0, W, 100):
            L.d.rectangle([x * K, 0, (x + 50) * K, 1150 * K], fill=(225, 140, 72))
        L.rect((90, 120, 990, 330), (120, 40, 40), r=24)
        L.texto((540, 200), "BAR PACO", 120, (255, 220, 120), F_CARTOON, borde=6)
        L.texto((540, 295), "DESDE 1985", 44, (255, 240, 200), F_TITULAR)
        for fila, y in enumerate((520, 760)):
            L.rect((60, y, 1020, y + 30), (120, 75, 45), r=6)
            for i in range(9):
                x = 110 + i * 105
                col = [(70, 140, 70), (150, 50, 50), (230, 190, 80), (60, 90, 160)][(i + fila) % 4]
                L.rect((x - 22, y - 150, x + 22, y), col, r=10)
                L.rect((x - 9, y - 195, x + 9, y - 145), col, r=4)
                L.rect((x - 16, y - 95, x + 16, y - 55), (245, 235, 210), r=3, ol=False)
        L.d.rectangle([0, 1150 * K, W * K, H * K], fill=(110, 70, 45))
        for x in range(0, W, 120):
            L.d.line([x * K, 1150 * K, x * K, H * K], fill=(90, 55, 35), width=5 * K)
        L.rect((-20, 1500, W + 20, 1560), (150, 95, 60), r=10)
        L.d.rectangle([0, 1560 * K, W * K, H * K], fill=(95, 60, 40))
        for x in range(60, W, 240):
            L.rect((x, 1600, x + 120, 1900), (120, 78, 50), r=12)
    elif nombre == "despacho":
        L.d.rectangle([0, 0, W * K, H * K], fill=(95, 55, 120))
        for x in range(0, W, 110):
            L.d.rectangle([x * K, 0, (x + 55) * K, 1250 * K], fill=(105, 62, 132))
        # cuadro dorado con la "R"
        L.rect((340, 200, 740, 640), (230, 180, 50), r=10)
        L.rect((375, 235, 705, 605), (60, 30, 80), r=6)
        L.texto((540, 430), "R", 260, (240, 200, 60), F_CARTOON, borde=6)
        # caja fuerte
        L.rect((790, 760, 1040, 1150), (130, 135, 150), r=16)
        L.elipse((860, 880, 970, 990), (90, 95, 110))
        L.linea([(915, 935), (950, 905)], OUT, 8)
        L.rect((800, 1150, 1030, 1190), (90, 95, 110), r=6)
        # billetes
        for i, (x, y) in enumerate(((80, 1080), (150, 1050), (110, 1010), (200, 1090))):
            L.rect((x, y, x + 150, y + 60), (90, 180, 90), r=6)
            L.elipse((x + 55, y + 12, x + 95, y + 48), (60, 140, 60), ol=False)
        L.d.rectangle([0, 1250 * K, W * K, H * K], fill=(140, 30, 50))
        for y in range(1250, H, 90):
            L.d.line([0, y * K, W * K, y * K], fill=(120, 25, 42), width=4 * K)
        # mesa delante
        L.rect((-20, 1560, W + 20, 1640), (80, 45, 25), r=10)
        L.rect((40, 1640, 140, H + 20), (70, 40, 22), r=6)
        L.rect((940, 1640, 1040, H + 20), (70, 40, 22), r=6)
        L.rect((700, 1470, 790, 1560), (230, 180, 50), r=8)
        L.poli([(660, 1480), (830, 1480), (790, 1400), (700, 1400)], (250, 220, 120))
    elif nombre == "garaje":
        L.d.rectangle([0, 0, W * K, H * K], fill=(180, 185, 195))
        for y in range(120, 1100, 160):
            L.d.line([0, y * K, W * K, y * K], fill=(160, 165, 175), width=6 * K)
        L.rect((80, 140, 1000, 300), (40, 40, 50), r=20)
        L.texto((540, 222), "GARAJE RAMIRO", 84, (240, 200, 60), F_CARTOON)
        L.d.rectangle([0, 1100 * K, W * K, H * K], fill=(110, 112, 120))
        for x in range(-200, W, 260):
            L.d.line([x * K, H * K, (x + 400) * K, 1100 * K], fill=(100, 102, 110), width=6 * K)
        # coche de lujo
        L.poli([(120, 1080), (300, 900), (720, 890), (900, 1060), (1010, 1090), (1010, 1300), (70, 1300), (70, 1120)],
               (220, 40, 50))
        L.poli([(330, 920), (500, 915), (500, 1060), (230, 1065)], (150, 210, 240))
        L.poli([(530, 915), (700, 912), (840, 1060), (530, 1060)], (150, 210, 240))
        L.rect((930, 1150, 1010, 1200), (255, 240, 150), r=10)
        for x in (250, 830):
            L.elipse((x - 105, 1210, x + 105, 1420), (35, 35, 40))
            L.elipse((x - 50, 1265, x + 50, 1365), (200, 200, 210))
    elif nombre == "espejo":
        L.d.rectangle([0, 0, W * K, H * K], fill=(170, 220, 230))
        for x in range(0, W, 120):
            L.d.line([x * K, 0, x * K, H * K], fill=(140, 195, 210), width=5 * K)
        for y in range(0, H, 120):
            L.d.line([0, y * K, W * K, y * K], fill=(140, 195, 210), width=5 * K)
        L.rect((-20, 1700, W + 20, H + 20), (240, 240, 245), r=0)
    elif nombre == "rayos":
        c1, c2 = [((255, 200, 50), (255, 160, 30)), ((90, 170, 255), (60, 130, 240)),
                  ((240, 80, 120), (210, 50, 100)), ((120, 220, 120), (80, 190, 90))][variante % 4]
        L.d.rectangle([0, 0, W * K, H * K], fill=c1)
        cx, cy = W / 2 * K, H * 0.42 * K
        for i in range(24):
            a0, a1 = i * 2 * math.pi / 24, (i + 0.5) * 2 * math.pi / 24
            L.d.polygon([(cx, cy), (cx + math.cos(a0) * 4000, cy + math.sin(a0) * 4000),
                         (cx + math.cos(a1) * 4000, cy + math.sin(a1) * 4000)], fill=c2)
    elif nombre == "gimnasio":
        _pared_rayas(L, (200, 205, 215), 1300)
        L.d.rectangle([0, 1300 * K, W * K, H * K], fill=(70, 70, 80))
        L.rect((60, 300, 1020, 900), (210, 235, 245), r=10)
        L.texto((540, 220), "GYM", 120, (230, 60, 60), F_CARTOON, borde=6)
        for i in range(5):
            x = 150 + i * 190
            L.rect((x - 15, 1000, x + 15, 1200), (90, 90, 100), r=6)
            L.elipse((x - 55, 1150, x + 55, 1250), (40, 40, 50))
        L.rect((80, 1180, 1000, 1220), (110, 110, 120), r=8)
    elif nombre == "parque":
        L.d.rectangle([0, 0, W * K, H * K], fill=(130, 200, 250))
        L.elipse((120, 220, 360, 330), (255, 255, 255), ol=False)
        L.elipse((650, 300, 950, 410), (255, 255, 255), ol=False)
        for x in (80, 330, 760, 1000):
            L.rect((x - 25, 900, x + 25, 1300), (120, 80, 50), r=8)
            L.elipse((x - 170, 620, x + 170, 1000), (70, 170, 80))
        L.d.rectangle([0, 1250 * K, W * K, H * K], fill=(110, 190, 90))
        L.poli([(420, 1250), (660, 1250), (1000, H), (80, H)], (230, 200, 140), ol=False)
    elif nombre == "calle":
        L.d.rectangle([0, 0, W * K, H * K], fill=(150, 210, 250))
        for i, (x, w_, h_) in enumerate(((0, 300, 900), (280, 260, 1100), (520, 300, 800), (800, 300, 1000))):
            col = [(240, 160, 120), (120, 150, 210), (250, 210, 120), (170, 120, 200)][i]
            L.rect((x, 1350 - h_, x + w_, 1360), col, r=4)
            for wy in range(1350 - h_ + 60, 1300, 140):
                for wx in range(x + 40, x + w_ - 60, 90):
                    L.rect((wx, wy, wx + 50, wy + 70), (255, 250, 210), r=4)
        L.d.rectangle([0, 1350 * K, W * K, H * K], fill=(190, 190, 195))
    else:  # plano: color liso
        L.d.rectangle([0, 0, W * K, H * K], fill=(250, 220, 90))
    img = L.final().convert("RGB")
    return img


def tarjeta_movil(datos, personajes):
    """Pantalla de móvil gigante con un mensaje/invitación. datos: titulo, lineas, de, avatares."""
    L = Lienzo(W, H)
    L.rect((150, 260, 930, 1760), (30, 30, 40), r=90)
    L.rect((185, 330, 895, 1690), (250, 247, 245), r=40, ol=False)
    L.rect((410, 290, 670, 315), (60, 60, 70), r=12, ol=False)
    L.rect((185, 330, 895, 500), (70, 190, 120), r=40, ol=False)
    L.d.rectangle([185 * K, 440 * K, 895 * K, 500 * K], fill=(70, 190, 120))
    L.texto((540, 420), datos.get("de", ""), 64, (255, 255, 255), F_TITULAR)
    y = 600
    if datos.get("titulo"):
        L.texto((540, y), datos["titulo"], 92, (235, 70, 110), F_CARTOON, borde=4, borde_color=(255, 255, 255))
        y += 120
    img = L.final()
    # avatares (cabezas de personajes)
    av = datos.get("avatares", [])
    for i, pid in enumerate(av):
        spr = dibujar_personaje(personajes[pid], "feliz" if pid != "BRANDON" else "chulo")
        cabeza = spr.crop((120, 120, 480, 560)).resize((260, 317), Image.LANCZOS)
        x = 540 - (len(av) * 280) // 2 + i * 280 + 10
        img.alpha_composite(cabeza, (int(x), int(y)))
    if av:
        y += 340
    L2 = Lienzo(W, H)
    for linea in datos.get("lineas", []):
        tam = 64 if len(linea) < 18 else 52
        L2.texto((540, y + 30), linea, tam, OUT, F_TITULAR)
        y += tam + 34
    img.alpha_composite(L2.final())
    return img


# ---------------------------------------------------------------------------
# Elementos animados encima
# ---------------------------------------------------------------------------
def onomatopeya(txt, color=(255, 220, 40)):
    f = fuente(F_CARTOON, 170 * K)
    w = int(f.getlength(txt) / K) + 120
    L = Lienzo(w, 300)
    cx, cy = w / 2, 150
    pts = []
    for i in range(22):
        a = i * 2 * math.pi / 22
        r = (w / 2 - 10) if i % 2 == 0 else (w / 2 - 70)
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * min(r, 140) * 0.95))
    L.poli(pts, (255, 255, 255))
    L.texto((cx, cy + 10), txt, 150, color, F_CARTOON, borde=9)
    return L.final()


def estrellas(t):
    L = Lienzo(400, 200)
    for i in range(4):
        a = t * 4 + i * math.pi / 2
        x, y = 200 + math.cos(a) * 150, 100 + math.sin(a) * 50
        pts = [(x + math.cos(j * math.pi / 5 - math.pi / 2) * (28 if j % 2 == 0 else 12),
                y + math.sin(j * math.pi / 5 - math.pi / 2) * (28 if j % 2 == 0 else 12)) for j in range(10)]
        L.poli(pts, (255, 220, 40))
    return L.final()


def olor(t, ancho=520, alto=900):
    L = Lienzo(ancho, alto)
    for i, x0 in enumerate((40, ancho - 60, 90, ancho - 110)):
        y0 = alto - 150 - (i % 2) * 250 - ((t * 120 + i * 60) % 260)
        pts = [(x0 + math.sin((y0 - k * 18) / 30 + t * 4) * 18, y0 - k * 18) for k in range(12)]
        L.linea(pts, (120, 200, 80), 10)
    return L.final()


def moscas(t, cx, cy):
    out = []
    for i in range(3):
        a = t * (3 + i) + i * 2
        out.append((cx + math.cos(a) * (180 + i * 30), cy + math.sin(a * 1.3) * 120))
    return out


def gotas(t):
    L = Lienzo(360, 200)
    for i, x in enumerate((40, 320)):
        y = 40 + ((t * 200 + i * 70) % 140)
        L.poli([(x, y - 30), (x - 14, y + 6), (x, y + 18), (x + 14, y + 6)], (120, 200, 255))
    return L.final()


def lagrimas(t):
    L = Lienzo(360, 400)
    for x in (95, 265):
        L.rect((x - 16, 0, x + 16, 260 + 40 * math.sin(t * 8)), (110, 190, 255), r=16)
    return L.final()


def panel_stats(stats, prog):
    """Tarjeta de estadísticas tipo videojuego. stats: {"FÍSICO": [antes, despues], ...}"""
    n = len(stats)
    L = Lienzo(900, 140 + n * 120)
    L.rect((10, 10, 890, 130 + n * 120), (30, 30, 45, 235), r=40)
    L.texto((450, 75), "ESTADÍSTICAS", 64, (255, 220, 40), F_CARTOON)
    colores = [(90, 220, 120), (90, 170, 255), (255, 120, 170), (255, 170, 60)]
    for i, (nom, v) in enumerate(stats.items()):
        a, b = (v if isinstance(v, (list, tuple)) else (0, v))
        val = a + (b - a) * prog
        y = 150 + i * 120
        L.texto((60, y + 30), nom, 50, (255, 255, 255), F_TITULAR, anchor="lm")
        L.rect((360, y + 5, 760, y + 55), (60, 60, 80), r=25, ol=False)
        if val > 0:
            L.rect((360, y + 5, 360 + 400 * max(val, 4) / 100, y + 55), colores[i % 4], r=25, ol=False)
        L.texto((830, y + 30), f"{int(round(val))}", 54, (255, 255, 255), F_TITULAR)
    return L.final()


def _euros(v):
    entero = int(v)
    cent = int(round((v - entero) * 100))
    if cent == 100:
        entero, cent = entero + 1, 0
    return f"{entero:,}".replace(",", ".") + f",{cent:02d} €"


def panel_dinero(desde, hasta, meta, prog):
    """Contador de dinero tipo videojuego con barra hacia la meta."""
    val = desde + (hasta - desde) * prog
    L = Lienzo(900, 330)
    L.rect((10, 10, 890, 320), (25, 30, 40, 240), r=40)
    L.elipse((50, 50, 170, 170), (250, 200, 40))
    L.texto((110, 112), "€", 80, (180, 120, 10), F_CARTOON)
    color = (110, 230, 120) if val >= 0 else (240, 80, 80)
    L.texto((530, 112), _euros(val), 104, color, F_CARTOON, borde=4)
    L.rect((50, 210, 850, 260), (60, 60, 80), r=25, ol=False)
    frac = max(0.0, min(1.0, val / meta))
    if frac > 0:
        L.rect((50, 210, 50 + max(50, 800 * frac), 260), (110, 230, 120), r=25, ol=False)
    L.texto((450, 293), f"META: {_euros(meta)[:-5]} €", 40, (255, 255, 255), F_TITULAR)
    return L.final()


def boton_suscribete():
    L = Lienzo(800, 190)
    L.rect((10, 10, 790, 180), (230, 30, 40), r=40)
    L.texto((440, 98), "SUSCRÍBETE", 96, (255, 255, 255), F_CARTOON, borde=4, borde_color=(120, 0, 10))
    # campana
    L.poli([(70, 140), (85, 110), (85, 70), (110, 45), (140, 45), (165, 70), (165, 110), (180, 140)], (255, 210, 60))
    L.elipse((112, 135, 138, 160), (255, 210, 60))
    return L.final()


# ---------------------------------------------------------------------------
# Interfaz tipo videojuego (marcador superior) y elementos de estilo
# ---------------------------------------------------------------------------
def hud(dias, etiqueta_barra, porcentaje, dinero, lugar, pop_dias=0.0, pop_dinero=0.0):
    """Marcador fijo arriba: días restantes, barra de progreso, dinero y lugar."""
    L = Lienzo(W, 300)
    # calendario
    L.rect((30, 20, 170, 160), (30, 30, 42, 235), r=24)
    L.rect((30, 20, 170, 62), (230, 60, 70), r=24, ol=False)
    L.d.rectangle([30 * K, 44 * K, 170 * K, 62 * K], fill=(230, 60, 70))
    L.texto((100, 42), "DÍAS", 30, (255, 255, 255), F_TITULAR)
    L.texto((100, 112), str(dias), int(70 * (1 + 0.25 * pop_dias)), (255, 255, 255), F_CARTOON)
    # barra de progreso
    L.rect((190, 20, 1050, 120), (30, 30, 42, 235), r=24)
    L.texto((220, 52), etiqueta_barra, 36, (255, 255, 255), F_CARTOON, anchor="lm")
    pct = f"{porcentaje:.1f}%" if porcentaje < 10 else f"{int(porcentaje)}%"
    L.texto((1025, 52), pct, 40, (255, 120, 140), F_CARTOON, anchor="rm")
    L.rect((220, 82, 1020, 104), (70, 70, 90), r=11, ol=False)
    if porcentaje > 0:
        L.rect((220, 82, 220 + max(22, 800 * min(1, porcentaje / 100)), 104), (255, 90, 120), r=11, ol=False)
    # dinero
    L.rect((30, 180, 400, 260), (30, 30, 42, 235), r=40)
    L.elipse((44, 192, 100, 248), (250, 200, 40))
    L.texto((72, 221), "€", 36, (170, 110, 10), F_CARTOON)
    col = (255, 255, 255) if pop_dinero == 0 else ((120, 240, 130) if pop_dinero > 0 else (255, 90, 90))
    L.texto((250, 221), _euros(dinero), int(46 * (1 + 0.2 * abs(pop_dinero))), col, F_CARTOON)
    # lugar
    if lugar:
        f = fuente(F_CARTOON, 46 * K)
        ancho = int(f.getlength(lugar) / K) + 60
        L.rect((1050 - ancho, 180, 1050, 260), (30, 30, 42, 235), r=20)
        L.texto((1050 - ancho / 2, 222), lugar, 46, (255, 210, 60), F_CARTOON)
    return L.final()


def ticket(datos, n_lineas, sello):
    """Ticket de compra/pago con líneas que van apareciendo y sello opcional."""
    lineas = datos["lineas"][:n_lineas]
    alto = 200 + 62 * len(datos["lineas"]) + 120
    L = Lienzo(470, alto + 30)
    pts = [(10, 10), (460, 10), (460, alto)]
    for i in range(12):
        x = 460 - i * 37.5
        pts += [(x - 18.75, alto + 18), (x - 37.5, alto)]
    pts += [(10, alto)]
    L.poli(pts, (252, 250, 244))
    L.rect((10, 10, 460, 80), (230, 60, 70), r=0, ol=False)
    L.texto((235, 47), datos.get("titulo", "TICKET"), 40, (255, 255, 255), F_CARTOON)
    y = 125
    for nombre, precio in lineas:
        L.texto((40, y), nombre, 36, (60, 60, 70), F_TITULAR, anchor="lm")
        col = (220, 50, 60) if precio.strip().startswith("-") else (40, 40, 50)
        L.texto((430, y), precio, 36, col, F_TITULAR, anchor="rm")
        y += 62
    if n_lineas >= len(datos["lineas"]) and datos.get("total"):
        L.linea([(40, y - 20), (430, y - 20)], (150, 150, 160), 3)
        L.texto((40, y + 25), "TOTAL", 44, OUT, F_CARTOON, anchor="lm")
        L.texto((430, y + 25), datos["total"], 48, OUT, F_CARTOON, anchor="rm")
    img = L.final()
    if sello:
        S = Lienzo(360, 140)
        S.d.rounded_rectangle([10 * K, 10 * K, 350 * K, 130 * K], 18 * K, outline=(220, 40, 50), width=10 * K)
        S.texto((180, 72), sello, 64, (220, 40, 50), F_CARTOON)
        st = S.final().rotate(14, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(st, (int(img.width / 2 - st.width / 2), int(alto * 0.12)))
    return img


def humo(t):
    """Nube de humo que tapa el centro y se disipa (transición de cambio)."""
    L = Lienzo(W, H)
    rnd = random.Random(3)
    alfa = int(255 * max(0, 1 - t / 0.7))
    if alfa <= 0:
        return None
    for i in range(16):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0, 320)
        r = rnd.uniform(130, 230) * (1 + t * 1.2)
        x = W / 2 + math.cos(a) * (r0 + t * 260)
        y = H * 0.55 + math.sin(a) * (r0 * 1.3 + t * 260)
        tono = rnd.choice([(215, 210, 200), (190, 185, 175), (235, 232, 225)])
        L.elipse((x - r, y - r, x + r, y + r), tono + (alfa,), ol=False)
    return L.final()


def brillos(t, ancho=600, alto=900):
    L = Lienzo(ancho, alto)
    rnd = random.Random(5)
    for i in range(7):
        x, y = rnd.uniform(40, ancho - 40), rnd.uniform(40, alto - 200)
        fase = (t * 2.2 + i / 7) % 1
        r = 26 * math.sin(fase * math.pi)
        if r > 2:
            pts = [(x + math.cos(j * math.pi / 4) * (r if j % 2 == 0 else r * 0.3),
                    y + math.sin(j * math.pi / 4) * (r if j % 2 == 0 else r * 0.3)) for j in range(8)]
            L.poli(pts, (255, 255, 255), ol=False)
    return L.final()


def pensamiento(cabeza_img):
    """Bocadillo de pensamiento con la cabeza de otro personaje dentro."""
    L = Lienzo(460, 420)
    for (x, y, r) in ((60, 390, 16), (100, 345, 26)):
        L.elipse((x - r, y - r, x + r, y + r), (255, 255, 255))
    for (x, y, r) in ((170, 170, 110), (290, 140, 120), (340, 230, 95), (200, 250, 100), (260, 210, 130)):
        L.elipse((x - r, y - r, x + r, y + r), (255, 255, 255), ol=False)
    img = L.final()
    cab = cabeza_img.resize((230, 280), Image.LANCZOS)
    img.alpha_composite(cab, (140, 40))
    return img


def tarjeta_opcion(letra, texto, color):
    L = Lienzo(420, 440)
    L.rect((10, 10, 410, 430), color, r=40)
    L.elipse((150, 40, 270, 160), (255, 255, 255))
    L.texto((210, 102), letra, 90, color, F_CARTOON)
    palabras = texto.upper().split()
    lineas, act = [], ""
    for w in palabras:
        if len(act + " " + w) > 13 and act:
            lineas.append(act)
            act = w
        else:
            act = (act + " " + w).strip()
    lineas.append(act)
    y = 230 - (len(lineas) - 1) * 25
    for l in lineas[:3]:
        L.texto((210, y), l, 46, (255, 255, 255), F_CARTOON, borde=3)
        y += 52
    L.texto((210, 395), "¿MAÑANA?", 34, (255, 255, 255), F_TITULAR)
    return L.final()


def letrero_dia(dia, total):
    L = Lienzo(700, 330)
    L.rect((20, 20, 680, 310), (255, 220, 40), r=50)
    L.texto((350, 170), f"DÍA {dia}", 190, OUT, F_CARTOON)
    L.texto((600, 270), f"/{total}", 60, OUT, F_TITULAR)
    return L.final()


# ---------------------------------------------------------------------------
# Composición de un plano
# ---------------------------------------------------------------------------
_spr_cache = {}


def sprite(pid, p, expr, accion, boca, parp, mirada, fase):
    k = (pid, tuple(sorted((a, str(b)) for a, b in p.items())), expr, accion, boca, parp, mirada,
         round((fase % 1.0) * 8) / 8 if accion in ("correr", "gesto") else 0)
    if k not in _spr_cache:
        if len(_spr_cache) > 400:
            _spr_cache.clear()
        _spr_cache[k] = dibujar_personaje(p, expr, accion, boca, parp, mirada, k[-1])
    return _spr_cache[k]


def componer(plano, personajes, t_local, t_abs, hablando, cache, energia=0.0):
    """Dibuja el plano completo (sin cámara) y devuelve imagen RGBA 1080x1920."""
    nombre = plano.get("fondo", "dormitorio")
    base = fondo(nombre, plano.get("variante", 0)).convert("RGBA")
    if nombre == "movil":
        base = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(10))).enhance(0.55)
    frame = base.copy()
    suelo = plano.get("suelo", SUELO.get(nombre, 1720))
    chars = plano.get("personajes", [])
    for c in chars:
        pid = c["id"]
        p = {**personajes[pid], **c.get("cambios", {})}
        nivel = int(hablando) if c.get("habla") else 0
        en_s = energia if c.get("habla") else 0.0
        expr = c.get("expresion", "neutro")
        accion = c.get("accion", "quieto")
        if accion == "quieto" and c.get("habla") and en_s > 0.15:
            accion = "gesto"          # gesticula con la mano mientras habla
        parp = (t_abs * 1.0 + hash(pid) % 7) % 3.7 < 0.12
        mirada = c.get("mirada")
        if mirada is None:            # mira al otro personaje; si está triste, mira al suelo
            otros = [o for o in chars if o is not c]
            dx = (otros[0].get("x", 0.5) - c.get("x", 0.5)) if otros else 0
            mirada = (1.0 if dx > 0.05 else -1.0 if dx < -0.05 else 0.0, 0.8 if expr in ("triste", "llorar") else 0.0)
        mirada = tuple(mirada)
        spr = sprite(pid, p, expr, accion, nivel, parp, mirada, t_local * 1.8)
        esc = c.get("escala", 1.0)
        # --- movimiento expresivo ---
        rot = c.get("rot", 0)
        rebote = 1 + 0.015 * math.sin(t_abs * 3 + hash(pid) % 5)          # respiración
        if c.get("salto"):
            rebote += 0.05 * abs(math.sin(t_local * 9))
        elif expr in ("sorpresa", "euforia") and not rot:
            rebote += 0.06 * abs(math.sin(t_local * 10)) * math.exp(-t_local / 0.9)
        if not rot:
            if expr in ("enfadado", "esfuerzo"):
                rot += 1.6 * math.sin(t_abs * 38)
            elif expr in ("triste", "llorar"):
                rot += -2.5 + 0.8 * math.sin(t_abs * 2)
                rebote -= 0.02
            elif expr in ("feliz", "enamorado", "chulo", "euforia"):
                rot += 2.5 * math.sin(t_abs * 4 + hash(pid) % 5)
            rot += 2.2 * en_s * math.sin(t_abs * 7)                         # vaivén al hablar
        rebote += 0.035 * en_s * abs(math.sin(t_abs * 13))                  # golpe de énfasis
        rebote += 0.09 * math.exp(-t_local / 0.12) * math.cos(t_local * 26)  # "pop" al entrar en plano
        ancho = 1 - (rebote - 1) * 0.6                                      # estirar y encoger
        sw, sh = int(SW * esc * ancho), int(SH * esc * rebote)
        spr2 = spr.resize((sw, sh), Image.BILINEAR)
        if c.get("temblor"):
            rot += 3 * math.sin(t_abs * 40)
        if rot:
            spr2 = spr2.rotate(rot, resample=Image.BICUBIC, expand=True)
        x = int(c.get("x", 0.5) * W - spr2.width / 2)
        y = int(c.get("y", suelo) - spr2.height + (c.get("bajar", 0)))
        if c.get("entra"):  # entra desde un lado
            d = max(0, 1 - t_local / 0.35)
            x += int((W if c["entra"] == "derecha" else -W) * d * d)
        frame.alpha_composite(spr2, (x, y))
        cabeza = (x + spr2.width / 2, y + 360 * esc)
        if c.get("olor"):
            o = olor(t_abs)
            o = o.resize((int(o.width * esc), int(o.height * esc)))
            frame.alpha_composite(o, (int(x + spr2.width / 2 - o.width / 2), int(y + 250 * esc)))
        if c.get("moscas"):
            for mx, my in moscas(t_abs, cabeza[0], cabeza[1]):
                ImageDraw.Draw(frame).ellipse((mx - 9, my - 9, mx + 9, my + 9), fill=OUT)
        if c.get("sudor"):
            g = gotas(t_abs)
            frame.alpha_composite(g, (int(cabeza[0] - 180), int(cabeza[1] - 200 * esc)))
        if c.get("lagrimas"):
            g = lagrimas(t_abs).resize((int(360 * esc), int(400 * esc)))
            frame.alpha_composite(g, (int(cabeza[0] - g.width / 2), int(cabeza[1] + 30 * esc)))
        if c.get("brillos"):
            b = brillos(t_abs).resize((int(600 * esc), int(900 * esc)))
            frame.alpha_composite(b, (int(x + spr2.width / 2 - b.width / 2), int(y + 40 * esc)))
        if c.get("piensa"):
            k = ("piensa", c["piensa"])
            if k not in cache:
                otro = dibujar_personaje(personajes[c["piensa"]], "feliz")
                cache[k] = pensamiento(otro.crop((120, 120, 480, 560)))
            pb = cache[k]
            e2 = min(1, t_local / 0.25)
            pb2 = pb.resize((max(1, int(pb.width * e2)), max(1, int(pb.height * e2))))
            frame.alpha_composite(pb2, (int(min(W - pb2.width, cabeza[0] + 60 * esc)), int(max(0, cabeza[1] - 330 * esc - pb2.height / 2))))
        if c.get("estrellas"):
            e = estrellas(t_abs)
            frame.alpha_composite(e, (int(cabeza[0] - 200), int(cabeza[1] - 280 * esc)))
    if nombre == "espejo":
        k = ("marco_espejo",)
        if k not in cache:
            L = Lienzo(W, H)
            L.d.ellipse([140 * K, 200 * K, 940 * K, 1650 * K], outline=(200, 150, 60), width=60 * K)
            L.d.ellipse([140 * K, 200 * K, 940 * K, 1650 * K], outline=OUT, width=8 * K)
            L.d.ellipse([200 * K, 260 * K, 880 * K, 1590 * K], outline=OUT, width=8 * K)
            m = Image.new("L", (W * K, H * K), 255)
            ImageDraw.Draw(m).ellipse([170 * K, 230 * K, 910 * K, 1620 * K], fill=0)
            capa = Image.new("RGBA", (W * K, H * K), (170, 220, 230, 255))
            for x in range(0, W, 120):
                ImageDraw.Draw(capa).line([x * K, 0, x * K, H * K], fill=(140, 195, 210), width=5 * K)
            capa.putalpha(m)
            capa.alpha_composite(L.im)
            for i in range(2):
                ImageDraw.Draw(capa).line([(330 + i * 60) * K, 500 * K, (480 + i * 60) * K, 330 * K],
                                          fill=(255, 255, 255, 140), width=18 * K)
            cache[k] = capa.resize((W, H), Image.LANCZOS)
        frame.alpha_composite(cache[k])
    if plano.get("movil"):
        k = ("movil", id(plano))
        if k not in cache:
            cache[k] = tarjeta_movil(plano["movil"], personajes)
        d = max(0, 1 - t_local / 0.3)
        frame.alpha_composite(cache[k], (0, int(H * d * d)))
    return frame
