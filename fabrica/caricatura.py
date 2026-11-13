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
            tirantes=False, granos=0)

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
        boca = "habla"
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
    elif est == "rapado":
        L.d.chord([(cx - 140) * K, (cy - 165) * K, (cx + 140) * K, (cy + 60) * K], 180, 360, fill=pc + (110,))


def _destello(L, x, y, r):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.35
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    L.poli(pts, (255, 255, 255), ol=False)


def _brazos(accion, p, sl, sr, grosor):
    """Devuelve [(puntos_brazo_izq), (puntos_brazo_der)] y si lleva objeto."""
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
    brazos = _brazos(accion, p, sl, sr, gb)
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
    if p["mancha"]:
        L.elipse((cx + 10, top + 120, cx + 70, top + 165), (170, 120, 60, 200), ol=False)
        L.elipse((cx - 60, top + 190, cx - 25, top + 215), (170, 120, 60, 200), ol=False)
    # cuello de camiseta
    L.d.chord([(cx - 45) * K, (top - 30) * K, (cx + 45) * K, (top + 40) * K], 0, 180, fill=p["piel"], outline=OUT,
              width=OL)
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
SUELO = {"dormitorio": 1720, "espejo": 1800, "rayos": 1760, "gimnasio": 1720, "parque": 1740, "movil": 1900,
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
         round(fase * 8) / 8 if accion == "correr" else 0)
    if k not in _spr_cache:
        if len(_spr_cache) > 400:
            _spr_cache.clear()
        _spr_cache[k] = dibujar_personaje(p, expr, accion, boca, parp, mirada, k[-1])
    return _spr_cache[k]


def componer(plano, personajes, t_local, t_abs, hablando, cache):
    """Dibuja el plano completo (sin cámara) y devuelve imagen RGBA 1080x1920."""
    nombre = plano.get("fondo", "dormitorio")
    base = fondo(nombre, plano.get("variante", 0)).convert("RGBA")
    if nombre == "movil":
        base = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(10))).enhance(0.55)
    frame = base.copy()
    suelo = plano.get("suelo", SUELO.get(nombre, 1720))
    for c in plano.get("personajes", []):
        pid = c["id"]
        p = {**personajes[pid], **c.get("cambios", {})}
        habla = c.get("habla") and hablando
        parp = (t_abs * 1.0 + hash(pid) % 7) % 3.7 < 0.12
        mirada = tuple(c.get("mirada", (0, 0)))
        spr = sprite(pid, p, c.get("expresion", "neutro"), c.get("accion", "quieto"), bool(habla), parp, mirada,
                     t_local * 1.8)
        esc = c.get("escala", 1.0)
        # respiración / rebote
        rebote = 1 + 0.015 * math.sin(t_abs * 3 + hash(pid) % 5)
        if c.get("salto"):
            rebote += 0.05 * abs(math.sin(t_local * 9))
        sw, sh = int(SW * esc), int(SH * esc * rebote)
        spr2 = spr.resize((sw, sh), Image.BILINEAR)
        rot = c.get("rot", 0)
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
