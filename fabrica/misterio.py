"""Estilo MISTERIO "expediente noir": tinta negra, papel envejecido y rojo. Cámaras de seguridad,
recortes de periódico, listas a máquina, mirillas, polaroids. Narración en segunda persona.

Cada escena tiene un `plano` con `vista`: portal, papel, periodico, camara, movil, puerta, mirilla,
foto, tablero. La cámara, subtítulos y audio los pone montaje.py.
"""
import glob
import math
import random
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
from . import W, H
from .caricatura import Lienzo, K, fuente

F_UI = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
F_NEGRA = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
_maq = glob.glob("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf") or \
    glob.glob("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf") or \
    glob.glob("/usr/share/fonts/truetype/jetbrains-mono/*.ttf")
F_MAQ = _maq[0] if _maq else F_UI
_serif = glob.glob("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
F_PERIODICO = _serif[0] if _serif else F_NEGRA

TINTA = (14, 13, 14)
PAPEL = (228, 220, 200)
PAPEL2 = (205, 196, 172)
ROJO = (196, 28, 36)
GRIS = (110, 108, 104)
CCTV = (150, 162, 150)


def T(L, xy, txt, tam, color, ruta=F_UI, anchor="mm"):
    L.d.text((xy[0] * K, xy[1] * K), txt, font=fuente(ruta, tam * K), fill=color, anchor=anchor)


def R(L, box, fill, r=0, borde=None, ancho=4):
    L.d.rounded_rectangle([v * K for v in box], r * K, fill=fill, outline=borde, width=int(ancho * K) if borde else 0)


def E(L, box, fill, borde=None, ancho=4):
    L.d.ellipse([v * K for v in box], fill=fill, outline=borde, width=int(ancho * K) if borde else 0)


def P(L, pts, fill, borde=None, ancho=4):
    L.d.polygon([(x * K, y * K) for x, y in pts], fill=fill, outline=borde, width=int(ancho * K) if borde else 0)


def Lin(L, pts, color=TINTA, ancho=5):
    L.d.line([(x * K, y * K) for x, y in pts], fill=color, width=int(ancho * K))


def _partir(texto, n):
    out, act = [], ""
    for w in texto.split():
        if len(act) + len(w) + 1 > n and act:
            out.append(act)
            act = w
        else:
            act = (act + " " + w).strip()
    return out + ([act] if act else [])


@lru_cache(maxsize=1)
def textura_papel():
    """Grano de papel + viñeta (se aplica encima de todo)."""
    rnd = random.Random(2)
    g = Image.effect_noise((W // 2, H // 2), 40).resize((W, H)).convert("L")
    yy = [abs(y - H / 2) / (H / 2) for y in range(H)]
    vin = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(vin)
    for i in range(40):
        a = int(6 * i)
        d.rectangle((i * 6, i * 9, W - i * 6, H - i * 9), outline=max(0, 230 - a), width=7)
    vin = vin.filter(ImageFilter.GaussianBlur(40))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capa.putalpha(vin.point(lambda v: int(v * 0.85)))
    ruido = Image.merge("RGBA", (g, g, g, g.point(lambda v: int(abs(v - 128) * 0.18))))
    capa.alpha_composite(ruido)
    _ = rnd, yy
    return capa


# ---------------------------------------------------------------------------
# Escenarios estáticos
# ---------------------------------------------------------------------------
@lru_cache(maxsize=32)
def escenario(vista):
    L = Lienzo(W, H, (20, 18, 18, 255))
    if vista == "portal":
        R(L, (0, 0, W, H), (24, 22, 22))
        for fila in range(5):
            for col in range(3):
                x, y = 110 + col * 300, 420 + fila * 240
                R(L, (x, y, x + 260, y + 200), (40, 38, 38), 4, PAPEL2, 5)
                R(L, (x + 30, y + 30, x + 230, y + 55), TINTA, 3)
                T(L, (x + 130, y + 135), f"{fila + 1}º{'ABC'[col]}", 38, PAPEL2, F_MAQ)
        x, y = 410, 900
        R(L, (x, y, x + 260, y + 200), (30, 10, 12), 4, ROJO, 7)
        R(L, (x + 30, y - 70, x + 230, y + 80), PAPEL, 3)
        P(L, [(x + 30, y - 70), (x + 130, y + 5), (x + 230, y - 70)], PAPEL2)
        E(L, (x + 112, y - 5, x + 148, y + 31), ROJO)       # lacre
    elif vista == "papel":
        R(L, (0, 0, W, H), (34, 28, 26))
        rnd = random.Random(1)
        for _ in range(30):
            y = rnd.uniform(0, H)
            Lin(L, [(0, y), (W, y + rnd.uniform(-20, 20))], (40, 33, 30), 4)
    elif vista == "periodico":
        R(L, (0, 0, W, H), (34, 28, 26))
    elif vista == "camara":
        R(L, (0, 0, W, H), (10, 12, 10))
        R(L, (30, 380, 1050, 1380), (60, 66, 60), 4)
        # calle vista desde arriba
        P(L, [(30, 1380), (1050, 1380), (760, 760), (320, 760)], (78, 84, 78))
        for i in range(6):
            y = 800 + i * 100
            Lin(L, [(540, y), (540, y + 50)], (130, 136, 130), 8 + i * 2)
        R(L, (30, 380, 320, 1380), (44, 48, 44))
        R(L, (760, 380, 1050, 1380), (44, 48, 44))
        for y in range(440, 1300, 170):
            R(L, (80, y, 200, y + 110), (30, 34, 30), 2)
            R(L, (840, y, 960, y + 110), (30, 34, 30), 2)
        R(L, (800, 1000, 960, 1250), (20, 22, 20), 2, (130, 136, 130), 4)   # tu portal
        T(L, (880, 980), "14", 34, (170, 176, 170), F_MAQ)
        E(L, (120, 600, 260, 740), (190, 196, 180))    # farola
    elif vista == "movil":
        R(L, (0, 0, W, H), (16, 14, 14))
    elif vista == "puerta":
        R(L, (0, 0, W, H), (22, 20, 20))
        R(L, (0, 1520, W, H), (14, 12, 12))
        R(L, (290, 480, 790, 1520), (44, 36, 32), 4, PAPEL2, 6)
        for (a, b) in ((540, 820), (900, 1440)):
            R(L, (340, a, 740, b), None, 4, (70, 60, 54), 6)
        E(L, (690, 1040, 726, 1076), (160, 140, 90))
        E(L, (522, 600, 558, 636), TINTA, PAPEL2, 4)     # mirilla
        R(L, (700, 1110, 718, 1180), (120, 100, 70), 6)  # cerrojo
    elif vista == "mirilla":
        R(L, (0, 0, W, H), (4, 4, 4))
    elif vista == "foto":
        R(L, (0, 0, W, H), (34, 28, 26))
    elif vista == "tablero":
        R(L, (0, 0, W, H), (120, 84, 56))
        rnd = random.Random(3)
        for _ in range(900):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            E(L, (x, y, x + 6, y + 6), (104, 72, 48))
    return L.final().convert("RGBA")


# ---------------------------------------------------------------------------
# Piezas animadas
# ---------------------------------------------------------------------------
def _hoja_lista(nombres, tachados, revelados, ultimo_rojo, titulo="LISTA"):
    L = Lienzo(820, 1150)
    P(L, [(20, 30), (800, 18), (806, 1130), (14, 1140)], PAPEL)
    T(L, (410, 120), titulo, 66, TINTA, F_MAQ)
    for i in range(min(revelados, len(nombres))):
        y = 260 + i * 118
        rojo = ultimo_rojo and i == len(nombres) - 1
        T(L, (100, y), f"{i + 1}. {nombres[i]}", 52 if not rojo else 66, ROJO if rojo else TINTA,
          F_MAQ if not rojo else F_NEGRA, "lm")
    for i, p in tachados:
        y = 260 + i * 118
        Lin(L, [(85, y + 6), (85 + 650 * p, y - 4)], ROJO, 13)
    return L.final()


def _periodico(datos):
    L = Lienzo(900, 1100)
    P(L, [(10, 20), (890, 10), (880, 1090), (20, 1080)], (222, 214, 190))
    T(L, (450, 90), datos.get("cabecera", "EL DIARIO DEL BARRIO"), 40, TINTA, F_PERIODICO)
    Lin(L, [(60, 130), (840, 130)], TINTA, 4)
    T(L, (450, 160), datos.get("fecha", ""), 24, GRIS, F_MAQ)
    for i, l in enumerate(_partir(datos.get("titular", "").upper(), 20)):
        T(L, (450, 250 + i * 72), l, 62, TINTA, F_PERIODICO)
    y0 = 250 + len(_partir(datos.get("titular", ""), 20)) * 72 + 30
    R(L, (60, y0, 470, y0 + 440), (150, 144, 128))
    E(L, (190, y0 + 60, 340, y0 + 210), (90, 86, 78))
    R(L, (150, y0 + 200, 380, y0 + 400), (90, 86, 78), 60)
    T(L, (265, y0 + 470), datos.get("pie", ""), 24, TINTA, F_MAQ)
    rnd = random.Random(5)
    for i in range(18):
        y = y0 + i * 30
        Lin(L, [(500, y), (500 + rnd.uniform(240, 340), y)], (120, 114, 100), 8)
    for i in range(6):
        y = y0 + 540 + i * 30
        Lin(L, [(60, y), (60 + rnd.uniform(600, 780), y)], (120, 114, 100), 8)
    return L.final().rotate(-3, expand=True, resample=Image.BICUBIC)


def _cctv(datos, t, tl):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    if datos.get("figura") and tl >= datos.get("figura_en", 0):
        p = min(1, (tl - datos.get("figura_en", 0)) / datos.get("figura_dur", 4))
        x = 380 + 300 * p
        y = 820 + 360 * p
        s = 0.6 + 0.6 * p
        d.ellipse((x - 22 * s, y - 120 * s, x + 22 * s, y - 76 * s), fill=(8, 8, 8, 255))
        d.rounded_rectangle((x - 34 * s, y - 80 * s, x + 34 * s, y + 40 * s), int(14 * s), fill=(8, 8, 8, 255))
    for y in range(380, 1380, 6):
        d.line((30, y, 1050, y), fill=(0, 0, 0, 40))
    f = fuente(F_MAQ, 38)
    d.text((60, 400), datos.get("cam", "CAM 02"), font=f, fill=(230, 230, 220))
    if int(t * 2) % 2 == 0:
        d.ellipse((880, 408, 906, 434), fill=(220, 30, 30))
    d.text((915, 400), "REC", font=f, fill=(230, 230, 220))
    seg = int(datos.get("segundo", 0) + tl)
    d.text((60, 1320), f"{datos.get('fecha', '15/11')}  {datos.get('hora', '03:14')}:{seg:02d}", font=f, fill=(230, 230, 220))
    return capa


def _movil(datos, tl):
    L = Lienzo(W, H)
    R(L, (230, 330, 850, 1600), (6, 6, 6), 70, (60, 56, 52), 8)
    R(L, (262, 372, 818, 1558), (14, 12, 12), 46)
    T(L, (540, 470), datos.get("de", "Número oculto"), 42, PAPEL, F_NEGRA)
    T(L, (540, 520), datos.get("hora", ""), 26, GRIS, F_MAQ)
    y = 620
    for texto, en in datos.get("mensajes", []):
        if tl < en:
            break
        lineas = _partir(texto, 20)
        alto = 40 + 52 * len(lineas)
        R(L, (300, y, 780, y + alto), (36, 32, 32), 22, ROJO, 3)
        for j, l in enumerate(lineas):
            T(L, (330, y + 46 + j * 52), l, 38, PAPEL, F_MAQ, "lm")
        y += alto + 30
    if datos.get("escribiendo") and tl >= datos["escribiendo"]:
        n = int(tl * 3) % 4
        R(L, (300, y, 450, y + 70), (36, 32, 32), 22)
        for i in range(3):
            E(L, (330 + i * 36, y + 25, 350 + i * 36, y + 45), PAPEL if i < n else GRIS)
    return L.final()


def _mirilla(datos, tl):
    """Vista a través de la mirilla: pasillo deformado en un círculo."""
    L = Lienzo(W, H)
    R(L, (0, 0, W, H), (4, 4, 4))
    cx, cy, r = 540, 900, 470
    E(L, (cx - r, cy - r, cx + r, cy + r), (60, 54, 46))
    # pasillo en perspectiva
    P(L, [(cx - 300, cy - 360), (cx + 300, cy - 360), (cx + 120, cy - 60), (cx - 120, cy - 60)], (80, 72, 60))
    P(L, [(cx - 300, cy + 360), (cx + 300, cy + 360), (cx + 120, cy + 60), (cx - 120, cy + 60)], (40, 34, 28))
    R(L, (cx - 120, cy - 60, cx + 120, cy + 60), (24, 22, 20))
    luz = 1 if not datos.get("parpadeo") else (1 if math.sin(tl * 19) > -0.4 else 0.25)
    E(L, (cx - 40, cy - 330, cx + 40, cy - 300), tuple(int(v * luz) for v in (255, 230, 170)))
    if datos.get("figura"):
        E(L, (cx - 26, cy - 40, cx + 26, cy + 10), (6, 6, 6))
        R(L, (cx - 40, cy + 8, cx + 40, cy + 60), (6, 6, 6), 14)
    img = L.final()
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(30))
    negro = Image.new("RGBA", (W, H), (4, 4, 4, 255))
    negro.paste(img, (0, 0), m)
    return negro


def _foto(datos):
    L = Lienzo(800, 960)
    R(L, (20, 20, 780, 940), (236, 232, 222), 4)
    R(L, (60, 60, 740, 740), (16, 16, 18))
    tipo = datos.get("tipo", "ventana")
    if tipo == "ventana":
        R(L, (180, 160, 620, 700), (30, 30, 34))
        R(L, (230, 220, 570, 560), (60, 56, 50), 2, (90, 86, 80), 8)
        Lin(L, [(400, 220), (400, 560)], (90, 86, 80), 8)
        E(L, (330, 430, 420, 520), (20, 20, 22))    # alguien dormido
    else:
        R(L, (160, 200, 640, 740), (30, 30, 36))
        R(L, (310, 460, 490, 740), (10, 10, 12), 4, (200, 170, 110), 4)
    T(L, (400, 850), datos.get("texto", ""), 54, ROJO, F_NEGRA)
    return L.final().rotate(-5, expand=True, resample=Image.BICUBIC)


def _glitch(img, tl, fuerza=1.0):
    if tl > 0.45:
        return img
    rnd = random.Random(int(tl * 60))
    out = img.copy()
    for _ in range(int(8 * fuerza)):
        y = rnd.randint(0, H - 60)
        h = rnd.randint(10, 60)
        dx = rnd.randint(-60, 60)
        out.paste(img.crop((0, y, W, y + h)), (dx, y))
    r, g, b, a = out.split()
    r = r.transform(out.size, Image.AFFINE, (1, 0, -8, 0, 1, 0))
    return Image.merge("RGBA", (r, g, b, a))


# ---------------------------------------------------------------------------
# Composición
# ---------------------------------------------------------------------------
def componer(pl, tl, t, cache):
    vista = pl.get("vista", "papel")
    frame = escenario(vista).copy()
    if vista == "papel":
        lista = pl["lista"]
        nombres = lista["nombres"]
        if "revelar" in lista:
            ini, paso = lista["revelar"]
            revelados = int(max(0, min(len(nombres), (tl - ini) / paso + 1)))
        else:
            revelados = len(nombres)
        tach = [(i, 1.0) for i in lista.get("tachados", [])]
        tach += [(i, max(0.0, min(1.0, (tl - en) / 0.5))) for i, en in lista.get("tachar", []) if tl >= en]
        k = ("lista", revelados, tuple((i, round(p, 2)) for i, p in tach))
        if k not in cache:
            cache[k] = _hoja_lista(nombres, tach, revelados, lista.get("ultimo_rojo", True))
        h = cache[k]
        frame.alpha_composite(h, (int(W / 2 - h.width / 2), 480))
    elif vista == "periodico":
        k = ("periodico", id(pl))
        if k not in cache:
            cache[k] = _periodico(pl.get("periodico", {}))
        frame.alpha_composite(cache[k], (int(W / 2 - cache[k].width / 2), 420))
    elif vista == "camara":
        frame.alpha_composite(_cctv(pl.get("camara", {}), t, tl))
    elif vista == "movil":
        frame.alpha_composite(_movil(pl.get("movil", {}), tl))
    elif vista == "puerta":
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.rectangle((290, 1514, 790, 1530), fill=(255, 210, 140, 230))
        d.polygon([(290, 1530), (790, 1530), (960, 1720), (120, 1720)], fill=(255, 210, 140, 40))
        if pl.get("pies"):
            for x in (440, 580):
                d.rectangle((x, 1512, x + 60, 1532), fill=(6, 6, 6, 255))
        if pl.get("papel_bajo") is not None:
            p = min(1, max(0, (tl - pl["papel_bajo"]) / 1.4))
            d.polygon([(470, 1530), (610, 1530), (630 + 20 * p, 1530 + 170 * p), (450 - 20 * p, 1530 + 170 * p)],
                      fill=(236, 232, 222, 255))
        frame.alpha_composite(capa.filter(ImageFilter.GaussianBlur(2)))
    elif vista == "mirilla":
        frame = _mirilla(pl.get("mirilla", {}), tl)
    elif vista == "foto":
        k = ("foto", id(pl))
        if k not in cache:
            cache[k] = _foto(pl.get("foto", {}))
        frame.alpha_composite(cache[k], (int(W / 2 - cache[k].width / 2), 440))
    if pl.get("glitch"):
        frame = _glitch(frame, tl)
    return frame


def acabado(frame):
    frame.alpha_composite(textura_papel())
    return frame


# ---------------------------------------------------------------------------
# Interfaz: sello de la serie y contador
# ---------------------------------------------------------------------------
def sello(serie, parte, contador_txt, contador_val, total, pop=0.0):
    L = Lienzo(W, 230)
    R(L, (36, 30, 480, 150), None, 6, ROJO, 6)
    T(L, (258, 75), serie.upper(), 46, ROJO, F_NEGRA)
    T(L, (258, 122), f"PARTE {parte}", 30, ROJO, F_MAQ)
    if contador_txt:
        T(L, (1040, 50), contador_txt, 26, PAPEL2, F_MAQ, "rm")
        T(L, (1040, 118), f"{contador_val}/{total}", int(76 * (1 + 0.3 * pop)), ROJO, F_NEGRA, "rm")
    return L.final().rotate(0)


def tarjeta_final(serie, parte, pregunta, a, b, sub_a, sub_b, fase_a, fase_b, cta):
    L = Lienzo(W, H)
    R(L, (0, 0, W, H), (10, 9, 9, 235))
    P(L, [(110, 420), (980, 400), (990, 1460), (100, 1480)], PAPEL)
    T(L, (545, 500), f"{serie.upper()} · PARTE {parte}", 34, ROJO, F_MAQ)
    for i, l in enumerate(_partir(pregunta.upper(), 16)):
        T(L, (545, 610 + i * 90), l, 82, TINTA, F_NEGRA)
    y = 800
    for letra, txt, sub, fase in (("A", a, sub_a, fase_a), ("B", b, sub_b, fase_b)):
        if fase > 0:
            R(L, (170, y, 250, y + 80), None, 6, TINTA, 6)
            T(L, (210, y + 42), letra, 50, ROJO, F_NEGRA)
            T(L, (290, y + 30), txt, 50, TINTA, F_MAQ, "lm")
            T(L, (290, y + 85), sub, 30, GRIS, F_MAQ, "lm")
        y += 220
    if cta > 0:
        T(L, (545, 1300), "COMENTA  A  O  B", 56, ROJO, F_NEGRA)
        T(L, (545, 1370), f"lo más votado decide la parte {parte + 1}", 28, GRIS, F_MAQ)
    return L.final()


def cierre(parte_sig, t):
    """Pantalla final: SUSCRÍBETE PARA LA PARTE N."""
    L = Lienzo(W, H)
    R(L, (0, 0, W, H), (8, 7, 7, 245))
    T(L, (540, 620), "SUSCRÍBETE", 110, PAPEL, F_NEGRA)
    T(L, (540, 740), "PARA VER LA", 60, PAPEL2, F_MAQ)
    T(L, (540, 900), f"PARTE {parte_sig}", int(170 * (1 + 0.04 * math.sin(t * 5))), ROJO, F_NEGRA)
    R(L, (300, 1080, 780, 1220), ROJO, 60)
    T(L, (540, 1150), "SUSCRIBIRME", 52, (255, 255, 255), F_NEGRA)
    fase = (t % 1.3) / 1.3
    r = 70 - 35 * min(1, fase / 0.3)
    E(L, (720 - r, 1170 - r, 720 + r, 1170 + r), None, (255, 255, 255, int(200 * (1 - fase))), 8)
    return L.final()
