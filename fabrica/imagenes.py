"""Imágenes generadas por IA (pollinations.ai) con caché y etalonaje cinematográfico."""
import hashlib
import time
import urllib.parse
import urllib.request
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
from . import CACHE, W, H

MARGEN = 1.14  # imagen algo mayor que el vídeo para poder hacer zoom/paneo


def _url(prompt, seed):
    q = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{q}?width=1080&height=1920&nologo=true&seed={seed}&model=flux"


def descargar(prompt, seed=1, reintentos=4):
    CACHE.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(f"{prompt}|{seed}".encode()).hexdigest()[:16]
    ruta = CACHE / f"img_{h}.jpg"
    if ruta.exists() and ruta.stat().st_size > 5000:
        return ruta
    err = None
    for i in range(reintentos):
        try:
            req = urllib.request.Request(_url(prompt, seed), headers={"User-Agent": "reels-fabrica/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                datos = r.read()
            if len(datos) > 5000:
                ruta.write_bytes(datos)
                return ruta
        except Exception as e:  # noqa: BLE001
            err = e
        time.sleep(4 * (i + 1))
    print(f"  ! imagen no disponible ({err}); uso fondo de reserva")
    return None


def _reserva(seed):
    g = np.linspace(0, 1, H)[:, None]
    rgb = np.stack([20 + 30 * g, 25 + 20 * g, 40 + 25 * g], -1) * np.ones((1, W, 1))
    return Image.fromarray(rgb.astype(np.uint8))


def etalonar(img):
    """Recorta logo, ajusta a 9:16 y da look de película (contraste, teal & orange)."""
    w, h = img.size
    img = img.crop((0, 0, w, int(h * 0.94)))  # quita marca de agua inferior
    w, h = img.size
    objetivo = W / H
    if w / h > objetivo:
        nw = int(h * objetivo)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / objetivo)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.convert("RGB").resize((int(W * MARGEN), int(H * MARGEN)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2.2, percent=90, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.08)
    a = np.asarray(img).astype(np.float32) / 255
    lum = a.mean(-1, keepdims=True)
    sombras = np.array([0.0, 0.05, 0.08]) * (1 - lum)   # sombras hacia azul verdoso
    luces = np.array([0.06, 0.02, -0.03]) * lum          # luces hacia naranja
    a = np.clip(a + sombras + luces, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8))


def obtener(prompt, seed=1):
    ruta = descargar(prompt, seed)
    img = Image.open(ruta) if ruta else _reserva(seed)
    return etalonar(img)


def capas_pelicula(n=1):
    """Viñeta precalculada (RGBA) para dar profundidad cinematográfica."""
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    alfa = (np.clip((d - 0.5) / 0.95, 0, 1) ** 1.6 * 210).astype(np.uint8)
    rgba = np.dstack([np.zeros_like(alfa)] * 3 + [alfa])
    return [Image.fromarray(rgba, "RGBA")]


def desenfocar_oscuro(img):
    i = img.resize((W, H)).filter(ImageFilter.GaussianBlur(28))
    i = ImageEnhance.Brightness(i).enhance(0.35)
    return i
