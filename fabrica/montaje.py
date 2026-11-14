"""Montaje: convierte un episodio (JSON) en un MP4 vertical 1080x1920 con subtítulos dinámicos."""
import math
import re
import subprocess
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from . import SR, W, H, FPS
from . import voz, sonido, imagenes

FUENTE = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FUENTE_2 = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
COLOR_VOZ = {"narrador": (255, 225, 77), "futuro": (110, 231, 255), "chica": (255, 120, 190), "chico": (140, 255, 140)}
Y_SUB = 1180          # centro vertical de los subtítulos (zona segura de TikTok/Reels/Shorts)
_fuentes = {}


def fuente(tam, ruta=FUENTE):
    k = (tam, ruta)
    if k not in _fuentes:
        _fuentes[k] = ImageFont.truetype(ruta, tam)
    return _fuentes[k]


def facil(x):
    return 1 - (1 - min(max(x, 0), 1)) ** 3


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
def texto_img(lineas, tam, colores=None, borde=9, ruta=FUENTE, sombra=True):
    """lineas: lista de listas de palabras. colores: dict índice_palabra->color. Devuelve RGBA."""
    f = fuente(tam, ruta)
    esp = int(tam * 0.28)
    alto_l = int(tam * 1.12)
    anchos = [sum(f.getlength(w) for w in l) + esp * (len(l) - 1) for l in lineas]
    ancho = int(max(anchos) + borde * 2 + 20)
    alto = int(alto_l * len(lineas) + borde * 2 + 20)
    im = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = 0
    for li, l in enumerate(lineas):
        x = (ancho - anchos[li]) / 2
        y = borde + 10 + li * alto_l
        for w in l:
            col = (colores or {}).get(k, (255, 255, 255))
            if sombra:
                d.text((x + 5, y + 7), w, font=f, fill=(0, 0, 0, 150), stroke_width=borde, stroke_fill=(0, 0, 0, 150))
            d.text((x, y), w, font=f, fill=col, stroke_width=borde, stroke_fill=(0, 0, 0))
            x += f.getlength(w) + esp
            k += 1
    return im


def partir_lineas(palabras, tam, ancho_max=920, ruta=FUENTE):
    f = fuente(tam, ruta)
    lineas, act = [], []
    for w in palabras:
        prueba = act + [w]
        if act and f.getlength(" ".join(prueba)) > ancho_max:
            lineas.append(act)
            act = [w]
        else:
            act = prueba
    if act:
        lineas.append(act)
    return lineas


def pegar_centrado(fondo, capa, cx, cy, escala=1.0, alfa=1.0):
    if escala != 1.0:
        capa = capa.resize((max(1, int(capa.width * escala)), max(1, int(capa.height * escala))), Image.BILINEAR)
    if alfa < 1.0:
        a = capa.getchannel("A").point(lambda v: int(v * alfa))
        capa = capa.copy()
        capa.putalpha(a)
    fondo.alpha_composite(capa, (int(cx - capa.width / 2), int(cy - capa.height / 2)))


def caja_redondeada(ancho, alto, color, radio=40, borde=None):
    im = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, ancho - 1, alto - 1), radio, fill=color, outline=borde, width=6 if borde else 0)
    return im


# ---------------------------------------------------------------------------
# Subtítulos tipo "karaoke" (2-3 palabras, la actual resaltada)
# ---------------------------------------------------------------------------
def agrupar(palabras, max_pal=3, max_car=16):
    grupos, act = [], []
    for p in palabras:
        act.append(p)
        texto = " ".join(x[0] for x in act)
        if len(act) >= max_pal or len(texto) >= max_car or re.search(r"[.,!?…:;]$", p[0]):
            grupos.append(act)
            act = []
    if act:
        grupos.append(act)
    return grupos


class Subtitulos:
    def __init__(self, ruta=FUENTE, tam=96, y=None):
        self.grupos = []   # (t_ini, t_fin, palabras[(w,t0,t1)], color)
        self.cache = {}
        self.ruta, self.tam, self.y = ruta, tam, y or Y_SUB

    def anadir(self, palabras, color):
        gs = agrupar(palabras)
        for i, g in enumerate(gs):
            fin = gs[i + 1][0][1] if i + 1 < len(gs) else g[-1][2] + 0.35
            self.grupos.append((g[0][1], fin, g, color))

    def dibujar(self, frame, t):
        for gi, (a, b, g, color) in enumerate(self.grupos):
            if a <= t < b:
                actual = max([i for i, p in enumerate(g) if p[1] <= t] or [0])
                clave = (gi, actual)
                if clave not in self.cache:
                    ws = [re.sub(r"[.,;:]+$", "", p[0]).upper() for p in g]
                    lineas = partir_lineas(ws, self.tam, 940, self.ruta)
                    self.cache[clave] = texto_img(lineas, self.tam, {actual: color}, ruta=self.ruta)
                pop = 0.82 + 0.18 * facil((t - a) / 0.09)
                pegar_centrado(frame, self.cache[clave], W / 2, self.y, pop)
                return


# ---------------------------------------------------------------------------
# Construcción del episodio
# ---------------------------------------------------------------------------
def _prompt(ep, p):
    for k, v in ep.get("personajes", {}).items():
        p = p.replace("{" + k + "}", v)
    return f"{p}, {ep.get('estilo_visual', 'cinematic film still')}"


def _mezclar(pista, clip, t, gan=1.0):
    i = int(t * SR)
    if i >= len(pista) or i < 0:
        return
    j = min(len(pista), i + len(clip))
    pista[i:j] += clip[: j - i] * gan


def construir(ep, carpeta, rapido=False):
    carpeta.mkdir(parents=True, exist_ok=True)
    revision = []   # control de calidad: lo que Whisper oyó vs. el guion
    cartoon = ep.get("estilo") == "cartoon"
    for nombre_voz, cfg in ep.get("voces", {}).items():
        voz.VOCES[nombre_voz] = {"efecto": None, **cfg}
    print("1/4 Voces…")
    bloques, t = [], 0.0
    for esc in ep["escenas"]:
        audio, pal, oido = voz.sintetizar(esc["texto"], esc.get("voz", "narrador"))
        revision.append((esc["texto"], oido))
        dur = len(audio) / SR + esc.get("pausa", 0.22)
        bloques.append(dict(esc=esc, audio=audio, pal=[(w, a + t, b + t) for w, a, b in pal], t0=t, dur=dur))
        t += dur
    # Final interactivo
    el = ep["eleccion"]
    t_final = t
    partes_final = {}
    t += 0.25
    claves = ["pregunta", "A", "B", "cta"] + (["avance"] if ep.get("avance") else [])
    for clave in claves:
        if clave == "avance":
            texto = ep["avance"]["texto"]
            t += 0.35                       # pausa antes del avance
        else:
            texto = el[clave] if clave in ("pregunta", "cta") else f"{clave}: {el[clave]}"
        audio, pal, oido = voz.sintetizar(texto, "narrador")
        revision.append((texto, oido))
        partes_final[clave] = dict(audio=audio, t0=t, pal=[(w, a + t, b + t) for w, a, b in pal])
        t += len(audio) / SR + 0.35
    total = t + 1.6

    print("2/4 Imágenes…")
    clips = []
    k = 0
    cache = {}
    if cartoon:
        from . import caricatura
        for i, b in enumerate(bloques):
            clips.append(dict(plano=b["esc"]["plano"], t0=b["t0"], t1=b["t0"] + b["dur"], bloque=b, i=i))
        ult = clips[-1]
        img_final = caricatura.componer(ult["plano"], ep["personajes"], 1.0, 1.0, False, cache).convert("RGB")
        fondo_final = imagenes.desenfocar_oscuro(img_final.resize((int(W * imagenes.MARGEN), int(H * imagenes.MARGEN))))
    for b in ([] if cartoon else bloques):
        ims = b["esc"].get("imagenes", [])
        if not ims:
            ims = [clips[-1]["fuente"]] if clips else ["dark cinematic room"]
        n = len(ims)
        for i, spec in enumerate(ims):
            prompt, seed = (spec, 1000 + k) if isinstance(spec, str) else (spec["prompt"], spec.get("seed", 1000 + k))
            print(f"   · {prompt[:70]}")
            img = imagenes.obtener(_prompt(ep, prompt), seed)
            clips.append(dict(fuente=spec, img=img, t0=b["t0"] + b["dur"] * i / n,
                              t1=b["t0"] + b["dur"] * (i + 1) / n, mov=k % 4))
            k += 1
    if not cartoon:
        fondo_final = imagenes.desenfocar_oscuro(clips[-1]["img"])

    print("3/4 Audio…")
    n = int(total * SR) + SR
    pista_voz = np.zeros(n, np.float32)
    pista_sfx = np.zeros(n, np.float32)
    for b in bloques:
        _mezclar(pista_voz, b["audio"], b["t0"])
        for s in b["esc"].get("sfx", []):
            nombre, en, g = (s, 0, 0.7) if isinstance(s, str) else (s["nombre"], s.get("en", 0), s.get("vol", 0.7))
            _mezclar(pista_sfx, sonido.SFX[nombre](), b["t0"] + en, g)
    for c in clips[1:]:
        _mezclar(pista_sfx, sonido.whoosh(0.35), c["t0"] - 0.12, 0.22)
    if cartoon:
        for c in clips:
            o = c["plano"].get("onomatopeya")
            if o:
                _mezclar(pista_sfx, sonido.SFX[o.get("sfx", "golpe")](), c["t0"] + o.get("en", 0), 0.9)
    for p in partes_final.values():
        _mezclar(pista_voz, p["audio"], p["t0"])
    _mezclar(pista_sfx, sonido.riser(1.6), t_final - 1.6, 0.5)
    _mezclar(pista_sfx, sonido.boom(), t_final, 0.9)
    _mezclar(pista_sfx, sonido.golpe(), partes_final["A"]["t0"], 0.6)
    _mezclar(pista_sfx, sonido.golpe(), partes_final["B"]["t0"], 0.6)
    if "avance" in partes_final:
        _mezclar(pista_sfx, sonido.whoosh(0.5), partes_final["avance"]["t0"] - 0.35, 0.6)
        _mezclar(pista_sfx, sonido.ding(), partes_final["avance"]["t0"] - 0.1, 0.5)
    mus = sonido.musica(total + 1, ep.get("musica", "misterio"), ep.get("latido_bpm", 72))
    mus = np.pad(mus, (0, max(0, n - len(mus))))[:n]
    curva = np.where(np.arange(n) / SR < t_final, 0.16, 0.26).astype(np.float32)
    # silencio dramático antes del final
    hueco = (np.arange(n) / SR > t_final - 1.7) & (np.arange(n) / SR < t_final)
    curva[hueco] = 0.05
    mezcla = pista_voz * 1.0 + pista_sfx + mus * curva
    mezcla = mezcla[: int(total * SR)]
    mezcla = mezcla / (np.max(np.abs(mezcla)) + 1e-6) * 0.95
    wav = carpeta / "_audio.wav"
    sf.write(wav, mezcla, SR)

    print("4/4 Vídeo…")
    if cartoon:
        from . import caricatura
        subs = Subtitulos(caricatura.F_TITULAR, 110, 1330)
        sobres = _sobres_voz(bloques)
    else:
        subs = Subtitulos()
    for b in bloques:
        subs.anadir(b["pal"], COLOR_VOZ.get(b["esc"].get("voz", "narrador"), (255, 225, 77)))
    subs_final = Subtitulos()
    subs_final.anadir(partes_final["cta"]["pal"], COLOR_VOZ["narrador"])
    capas = [] if cartoon else imagenes.capas_pelicula()
    titulo = ep.get("serie_titulo", "").upper()
    insignia = texto_img([[f"DÍA {ep['episodio']}/{ep['total']}"]], 46, {0: (255, 225, 77)}, borde=5, ruta=FUENTE_2)
    nombre_serie = texto_img([[titulo]], 34, borde=4, ruta=FUENTE_2) if titulo else None
    gancho = ep.get("gancho")
    gancho_img = texto_img(partir_lineas(gancho.upper().split(), 88, 900), 88, {}, borde=9) if gancho else None

    salida = carpeta / "video.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast" if rapido else "medium",
         "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", "-shortest", str(salida)],
        stdin=subprocess.PIPE)
    nf = int(total * FPS)
    rng = np.random.default_rng(1)
    for fi in range(nf):
        t = fi / FPS
        if t < t_final:
            c = next((c for c in clips if c["t0"] <= t < c["t1"]), clips[-1])
            if cartoon:
                frame = _plano_cartoon(c, t, ep, sobres, cache, rng)
            else:
                frame = _encuadre(c, t, bloques, rng)
        else:
            frame = _final(fondo_final, t - t_final, total - t_final)
        frame = frame.convert("RGBA")
        if capas:
            frame.alpha_composite(capas[fi % len(capas)])
        if t < t_final:
            _superposiciones(frame, t, bloques, cache)
            subs.dibujar(frame, t)
            if gancho_img is not None and t < 2.6:
                pegar_centrado(frame, gancho_img, W / 2, 1600 if cartoon else 600, 0.8 + 0.2 * facil(t / 0.15), min(1, (2.6 - t) / 0.25))
        else:
            _tarjeta_final(frame, t, ep, partes_final, cache)
        # destello
        for b in bloques:
            if "flash" in b["esc"].get("efecto", []) and 0 <= t - b["t0"] < 0.25:
                a = int(220 * (1 - (t - b["t0"]) / 0.25))
                frame.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
        if 0 <= t - t_final < 0.3:
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (t - t_final) / 0.3)))))
        # cabecera: insignia + barra de progreso
        frame.alpha_composite(insignia, (40, 200))
        if nombre_serie:
            frame.alpha_composite(nombre_serie, (40 + insignia.width - 6, 200 + (insignia.height - nombre_serie.height) // 2))
        d = ImageDraw.Draw(frame)
        d.rectangle((0, 0, W, 9), fill=(0, 0, 0, 160))
        d.rectangle((0, 0, int(W * t / total), 9), fill=(255, 225, 77, 255))
        ff.stdin.write(frame.convert("RGB").tobytes())
        if fi % (FPS * 5) == 0:
            print(f"   {t:5.1f}s / {total:.1f}s")
    ff.stdin.close()
    ff.wait()
    wav.unlink(missing_ok=True)
    if cartoon:
        pp = ep.get("portada_plano", clips[0]["plano"])
        img_p = caricatura.componer(pp, ep["personajes"], 1.0, 1.0, False, {}).convert("RGB")
        _portada(img_p, ep, carpeta / "portada.jpg")
    else:
        _portada(clips[0]["img"], ep, carpeta / "portada.jpg")
    _informe_voz(revision, carpeta / "_revision_voz.txt")
    return salida, total


def _informe_voz(revision, ruta):
    import difflib
    lineas, malas = [], 0
    for guion, oido in revision:
        if oido is None:
            continue
        r = difflib.SequenceMatcher(None, voz._norm(guion), voz._norm(oido)).ratio()
        marca = "OK " if r > 0.85 else "REVISAR"
        malas += r <= 0.85
        lineas.append(f"[{marca}] {r:.0%}\n  guion: {guion}\n  oído:  {oido}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"   Control de voz: {len(lineas) - malas}/{len(lineas)} frases entendidas bien por Whisper")


def _sobres_voz(bloques):
    """Por bloque: (volumen por fotograma, volumen suavizado) para mover boca y cuerpo."""
    out = []
    for b in bloques:
        a = np.abs(b["audio"])
        paso = SR // FPS
        n = len(a) // paso + 1
        env = np.array([a[i * paso:(i + 1) * paso].mean() if i * paso < len(a) else 0 for i in range(n)])
        env = env / (env.max() + 1e-6)
        suave = np.convolve(env, np.ones(7) / 7, mode="same")
        suave = np.clip(suave / (suave.max() + 1e-6) * 1.3, 0, 1)
        out.append((env, suave))
    return out


def _plano_cartoon(c, t, ep, sobres, cache, rng):
    from . import caricatura
    pl = c["plano"]
    b = c["bloque"]
    tl = t - c["t0"]
    idx = int(tl * FPS)
    crudo, suave = sobres[c["i"]]
    nivel = 0
    if idx < len(crudo):
        nivel = 2 if crudo[idx] > 0.6 else 1 if crudo[idx] > 0.2 else 0
    energia = float(suave[idx]) if idx < len(suave) else 0.0
    img = caricatura.componer(pl, ep["personajes"], tl, t, nivel, cache, energia)
    # cámara
    z0 = pl.get("zoom", 1.0)
    z1 = pl.get("zoom_fin", z0 * 1.06)
    p = min(1, tl / max(0.1, c["t1"] - c["t0"]))
    z = z0 + (z1 - z0) * facil(p) + 0.07 * math.exp(-tl / 0.12)
    fx, fy = pl.get("foco", (0.5, 0.5))
    if "shake" in b["esc"].get("efecto", []) and tl < 0.6:
        amp = 22 * (1 - tl / 0.6)
        fx += rng.uniform(-amp, amp) / W
        fy += rng.uniform(-amp, amp) / H
    rw, rh = W / z, H / z
    cx = min(max(fx * W, rw / 2), W - rw / 2)
    cy = min(max(fy * H, rh / 2), H - rh / 2)
    frame = img.transform((W, H), Image.AFFINE, (rw / W, 0, cx - rw / 2, 0, rh / H, cy - rh / 2), Image.BILINEAR)
    # elementos de interfaz (no se mueven con la cámara)
    o = pl.get("onomatopeya")
    if o and tl >= o.get("en", 0):
        k = ("ono", o["texto"])
        if k not in cache:
            cache[k] = caricatura.onomatopeya(o["texto"], tuple(o.get("color", (255, 220, 40))))
        dt = tl - o.get("en", 0)
        esc = (0.4 + 0.6 * facil(dt / 0.12)) * (1 + 0.04 * math.sin(dt * 12))
        capa = cache[k].rotate(o.get("rot", -8), resample=Image.BICUBIC, expand=True)
        if capa.width * esc > 1040:
            esc *= 1040 / (capa.width * esc)
        pegar_centrado(frame, capa, W * o.get("x", 0.5), H * o.get("y", 0.2), esc)
    st = pl.get("stats")
    if st:
        prog = facil(max(0, tl - 0.3) / 1.2)
        pan = caricatura.panel_stats(st, prog)
        pegar_centrado(frame, pan, W / 2, 900, 0.85 + 0.15 * facil(tl / 0.2))
    dn = pl.get("dinero")
    if dn:
        prog = facil(max(0, tl - 0.3) / 1.0)
        pan = caricatura.panel_dinero(dn[0], dn[1], ep.get("meta", 10000), prog)
        pegar_centrado(frame, pan, W / 2, pl.get("dinero_y", 900 if pl.get("dia") else 560),
                       0.85 + 0.15 * facil(tl / 0.2))
    if pl.get("dia"):
        k = ("dia",)
        if k not in cache:
            cache[k] = caricatura.letrero_dia(ep["episodio"], ep["total"])
        pegar_centrado(frame, cache[k], W / 2, 420,
                       (0.5 + 0.5 * facil(tl / 0.15)) * (1 + 0.03 * math.sin(tl * 7)))
    return frame


def _encuadre(c, t, bloques, rng):
    img = c["img"]
    bw, bh = img.size
    p = (t - c["t0"]) / max(1e-3, c["t1"] - c["t0"])
    mov = c["mov"]
    z = 1.0 + 0.10 * (p if mov in (0, 2) else 1 - p)          # acercar / alejar
    z += 0.08 * math.exp(-(t - c["t0"]) / 0.12)                  # "punch" al cortar
    rw, rh = bw / z / 1.0, bh / z / 1.0
    rw, rh = min(rw, bw), min(rh, bh)
    cx, cy = bw / 2, bh / 2
    holg_x, holg_y = (bw - rw) / 2, (bh - rh) / 2
    if mov == 2:
        cy += holg_y * (0.8 - 1.6 * p)
    elif mov == 3:
        cx += holg_x * (-0.8 + 1.6 * p)
    for b in bloques:
        if "shake" in b["esc"].get("efecto", []) and 0 <= t - b["t0"] < 0.7:
            amp = 18 * (1 - (t - b["t0"]) / 0.7)
            cx += rng.uniform(-amp, amp)
            cy += rng.uniform(-amp, amp)
    cx = min(max(cx, rw / 2), bw - rw / 2)
    cy = min(max(cy, rh / 2), bh - rh / 2)
    coef = (rw / W, 0, cx - rw / 2, 0, rh / H, cy - rh / 2)
    return img.transform((W, H), Image.AFFINE, coef, Image.BILINEAR)


def _superposiciones(frame, t, bloques, cache):
    for bi, b in enumerate(bloques):
        esc = b["esc"]
        if not (b["t0"] <= t < b["t0"] + b["dur"]):
            continue
        dt = t - b["t0"]
        if esc.get("pantalla"):
            k = ("pantalla", bi)
            if k not in cache:
                cache[k] = texto_img([[esc["pantalla"]]], 210, {0: (255, 255, 255)}, borde=12)
            pulso = 1 + 0.04 * math.sin(dt * 9)
            pegar_centrado(frame, cache[k], W / 2, 640, (0.7 + 0.3 * facil(dt / 0.12)) * pulso)
        if esc.get("mensaje"):
            k = ("msg", bi)
            if k not in cache:
                cache[k] = _burbuja(esc["mensaje"])
            entra = facil((dt - 0.15) / 0.2)
            if entra > 0:
                pegar_centrado(frame, cache[k], W / 2, 620 + 60 * (1 - entra), 0.9 + 0.1 * entra, entra)


def _burbuja(msg):
    f_n = fuente(40, FUENTE_2)
    f_t = fuente(54, FUENTE_2)
    lineas = partir_lineas(msg["texto"].split(), 54, 760, FUENTE_2)
    alto = 150 + 70 * len(lineas)
    im = caja_redondeada(900, alto, (245, 245, 245, 245), 46)
    d = ImageDraw.Draw(im)
    d.ellipse((40, 36, 110, 106), fill=(255, 120, 190))
    d.text((75, 71), msg["de"][0].upper(), font=fuente(40, FUENTE), fill="white", anchor="mm")
    d.text((130, 50), msg["de"], font=f_n, fill=(20, 20, 20))
    d.text((860, 56), msg.get("hora", "ahora"), font=fuente(30, FUENTE_2), fill=(120, 120, 120), anchor="ra")
    for i, l in enumerate(lineas):
        d.text((48, 130 + i * 70), " ".join(l), font=f_t, fill=(25, 25, 25))
    return im


def _final(fondo, dt, dur):
    z = 1.0 + 0.05 * dt / max(dur, 1)
    bw, bh = fondo.size
    rw, rh = bw / z, bh / z
    coef = (rw / W, 0, (bw - rw) / 2, 0, rh / H, (bh - rh) / 2)
    return fondo.transform((W, H), Image.AFFINE, coef, Image.BILINEAR)


def _avance(frame, t, ep, partes, cache):
    """Cierre: 'MAÑANA · DÍA N' con silueta misteriosa y una pregunta que engancha."""
    from . import caricatura
    av = ep["avance"]
    dt = t - (partes["avance"]["t0"] - 0.3)
    frame.alpha_composite(Image.new("RGBA", (W, H), (14, 8, 28, int(238 * min(1, dt / 0.3)))))
    if "av_sil" not in cache:
        spr = caricatura.dibujar_personaje(ep["personajes"][av.get("personaje", "LEO")], "neutro")
        al = spr.getchannel("A")
        sil = Image.new("RGBA", spr.size, (0, 0, 0, 255))
        sil.putalpha(al)
        glow = Image.new("RGBA", spr.size, (255, 225, 77, 255))
        glow.putalpha(al.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(10)))
        base = Image.new("RGBA", spr.size, (0, 0, 0, 0))
        base.alpha_composite(glow)
        base.alpha_composite(sil)
        cache["av_sil"] = base
        cache["av_q"] = texto_img([["?"]], 380, {0: (255, 225, 77)}, borde=14, ruta=caricatura.F_CARTOON)
        cache["av_m"] = texto_img([["MAÑANA"]], 100, {0: (255, 255, 255)}, borde=10, ruta=caricatura.F_CARTOON)
        cache["av_d"] = caricatura.letrero_dia(ep["episodio"] + 1, ep["total"])
        if av.get("pregunta"):
            cache["av_p"] = texto_img(partir_lineas(av["pregunta"].upper().split(), 84, 900), 84, {}, borde=9)
    sil = cache["av_sil"]
    esc = 0.72
    pegar_centrado(frame, sil, W / 2, 1790 - sil.height * esc / 2, esc, min(1, dt / 0.4))
    pegar_centrado(frame, cache["av_q"], W / 2, 1370, (1 + 0.06 * math.sin(dt * 6)) * (0.6 + 0.4 * facil(dt / 0.3)),
                   min(1, dt / 0.3))
    pegar_centrado(frame, cache["av_m"], W / 2, 350, 0.7 + 0.3 * facil(dt / 0.25), min(1, dt / 0.2))
    pegar_centrado(frame, cache["av_d"], W / 2, 600,
                   0.9 * (0.7 + 0.3 * facil((dt - 0.1) / 0.25)) * (1 + 0.03 * math.sin(dt * 7)), min(1, dt / 0.2))
    if "av_p" in cache and dt > 0.35:
        pegar_centrado(frame, cache["av_p"], W / 2, 900, 0.8 + 0.2 * facil((dt - 0.35) / 0.15))
    if av.get("suscribete"):
        t_s = av.get("suscribete_en", 1.2)
        if dt > t_s:
            if "av_sub" not in cache:
                cache["av_sub"] = caricatura.boton_suscribete()
            ds = dt - t_s
            pulso = (0.6 + 0.4 * facil(ds / 0.2)) * (1 + 0.06 * abs(math.sin(ds * 5)))
            pegar_centrado(frame, cache["av_sub"], W / 2, 1640, pulso)
            # dedo que pulsa (círculo que se encoge al tocar)
            fase = (ds % 1.2) / 1.2
            r = int(70 - 35 * min(1, fase / 0.3))
            a = int(200 * (1 - fase))
            ImageDraw.Draw(frame).ellipse((W / 2 + 230 - r, 1660 - r, W / 2 + 230 + r, 1660 + r),
                                          outline=(255, 255, 255, a), width=8)


def _tarjeta_final(frame, t, ep, partes, cache):
    if "avance" in partes and t >= partes["avance"]["t0"] - 0.3:
        _avance(frame, t, ep, partes, cache)
        return
    el = ep["eleccion"]
    p = partes["pregunta"]
    if t >= p["t0"] - 0.1:
        if "preg" not in cache:
            cache["preg"] = texto_img(partir_lineas(el.get("titulo", el["pregunta"]).upper().split(), 92, 940), 92,
                                      {}, borde=10)
        pegar_centrado(frame, cache["preg"], W / 2, 470, 0.8 + 0.2 * facil((t - p["t0"]) / 0.12))
    for i, (clave, color) in enumerate((("A", (230, 57, 70, 255)), ("B", (40, 120, 255, 255)))):
        pa = partes[clave]
        if t < pa["t0"] - 0.05:
            continue
        k = ("op", clave)
        if k not in cache:
            caja = caja_redondeada(940, 230, color, 48, (255, 255, 255, 255))
            d = ImageDraw.Draw(caja)
            d.ellipse((30, 45, 170, 185), fill=(255, 255, 255))
            d.text((100, 115), clave, font=fuente(96), fill=color[:3], anchor="mm")
            ls = partir_lineas(el[clave].upper().split(), 54, 700)
            y0 = 115 - 33 * len(ls)
            for j, l in enumerate(ls):
                d.text((200, y0 + j * 66), " ".join(l), font=fuente(54), fill="white")
            cache[k] = caja
        dt = t - pa["t0"]
        rebote = 1 + 0.12 * math.exp(-dt / 0.08) * math.cos(dt * 30)
        pegar_centrado(frame, cache[k], W / 2, 800 + i * 280, rebote)
    c = partes["cta"]
    if t >= c["t0"] and "cta" not in cache:
        cache["cta"] = texto_img([["COMENTA", "A", "o", "B"]], 104, {1: (230, 57, 70), 3: (40, 120, 255)}, borde=10)
    if t >= c["t0"]:
        pegar_centrado(frame, cache["cta"], W / 2, 1360, 1 + 0.05 * math.sin((t - c["t0"]) * 8))
        if "cta2" not in cache:
            cache["cta2"] = texto_img([f"LO MÁS VOTADO PASA EN EL DÍA {ep['episodio'] + 1}".split()], 50,
                                      {6: (255, 225, 77), 7: (255, 225, 77)}, borde=6, ruta=FUENTE_2)
        pegar_centrado(frame, cache["cta2"], W / 2, 1490, min(1, (t - c["t0"]) / 0.3) * 0.2 + 0.8)


def _portada(img, ep, ruta):
    base = img.resize((W, H)).convert("RGBA")
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(max(0, (y - H * 0.35) / (H * 0.65)) * 230))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    sombra.putalpha(grad.resize((W, H)))
    base.alpha_composite(sombra)
    txt = ep.get("portada", ep.get("gancho", ep["titulo"])).upper()
    ls = partir_lineas(txt.split(), 120, 960)
    col = {i: (255, 225, 77) for i in range(len(txt.split())) if i >= len(txt.split()) - 2}
    capa = texto_img(ls, 120, col, borde=12)
    pegar_centrado(base, capa, W / 2, 1250)
    dia = texto_img([[f"DÍA {ep['episodio']}"]], 140, {0: (255, 225, 77)}, borde=12)
    pegar_centrado(base, dia, W / 2, 1620)
    base.convert("RGB").save(ruta, quality=92)
