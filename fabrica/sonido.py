"""Música y efectos generados por código (sin derechos de autor, sin descargas)."""
import numpy as np
from . import SR

rng = np.random.default_rng(7)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _filtro(a, lo=None, hi=None):
    f = np.fft.rfft(a)
    fr = np.fft.rfftfreq(len(a), 1 / SR)
    if lo:
        f[fr < lo] = 0
    if hi:
        f *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(f, len(a)).astype(np.float32)


def _env(n, ataque=0.01, caida=0.3):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / max(caida, 1e-4))
    return e.astype(np.float32)


def _nota(hz):
    return 440.0 * 2 ** ((hz - 69) / 12)


# --- Música -----------------------------------------------------------------
PROGRESIONES = {
    # notas MIDI de cada acorde
    "misterio": [[45, 52, 57, 60], [41, 48, 53, 57], [38, 45, 50, 53], [40, 47, 52, 56]],  # Am F Dm E
    "tension":  [[45, 52, 57, 60], [46, 53, 58, 62], [45, 52, 57, 60], [44, 51, 56, 59]],
    "esperanza": [[48, 55, 60, 64], [43, 50, 55, 59], [45, 52, 57, 60], [41, 48, 53, 57]],
}


def musica_comedia(dur, bpm=112):
    """Base alegre tipo dibujos: bajo saltarín, acordes en staccato y charles."""
    t = _t(dur)
    out = np.zeros_like(t, dtype=np.float32)
    negra = 60 / bpm
    prog = [[48, 52, 55], [53, 57, 60], [55, 59, 62], [48, 52, 55]]  # C F G C
    bajos = [36, 41, 43, 36]
    nota_len = int(0.16 * SR)
    env = _env(nota_len, 0.003, 0.07)
    tt = np.arange(nota_len) / SR
    paso = 0
    for s0 in np.arange(0, dur, negra / 2):
        compas = int(s0 / (negra * 4)) % 4
        i0 = int(s0 * SR)
        i1 = min(len(out), i0 + nota_len)
        if i0 >= len(out):
            break
        if paso % 2 == 0:  # bajo en cada negra, alternando tónica/quinta
            f = _nota(bajos[compas] + (7 if paso % 4 == 2 else 0))
            b = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env * 0.5
            out[i0:i1] += b[: i1 - i0]
        else:  # acorde staccato a contratiempo
            ac = sum(np.sin(2 * np.pi * _nota(n + 12) * tt) for n in prog[compas]) / 3
            out[i0:i1] += (ac * env * 0.28)[: i1 - i0]
        # charles
        nh = int(0.03 * SR)
        h = rng.standard_normal(nh) * _env(nh, 0.0005, 0.008) * 0.12
        out[i0:min(len(out), i0 + nh)] += h[: min(len(out), i0 + nh) - i0]
        paso += 1
    fade = int(0.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.max(np.abs(out)) + 1e-6)


def musica(dur, estilo="misterio", bpm_latido=70, acorde_seg=4.0):
    if estilo == "comedia":
        return musica_comedia(dur)
    t = _t(dur)
    out = np.zeros_like(t, dtype=np.float32)
    prog = PROGRESIONES.get(estilo, PROGRESIONES["misterio"])
    n_ac = int(np.ceil(dur / acorde_seg))
    fade = int(0.8 * SR)
    for i in range(n_ac):
        a, b = int(i * acorde_seg * SR), int(min(dur, (i + 1) * acorde_seg + 0.8) * SR)
        if a >= len(t):
            break
        seg = t[a:b] - t[a]
        pad = np.zeros_like(seg)
        for k, n in enumerate(prog[i % len(prog)]):
            f = _nota(n)
            for h, g in ((1, 1.0), (2, 0.35), (3, 0.12)):
                det = 1 + 0.002 * (h + k)
                pad += g * np.sin(2 * np.pi * f * h * det * seg + k)
        env = np.minimum(1, seg / 0.8) * np.minimum(1, (seg[-1] - seg + 1e-3) / 0.8)
        out[a:a + len(seg)] += (pad * env * 0.06).astype(np.float32)
    # bajo drone
    out += 0.08 * np.sin(2 * np.pi * 55 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.1 * t))
    # latido
    if bpm_latido:
        periodo = 60 / bpm_latido
        golpe = np.sin(2 * np.pi * 52 * _t(0.25)) * _env(int(0.25 * SR), 0.004, 0.07)
        for s in np.arange(0, dur, periodo):
            for off, g in ((0, 0.5), (0.22, 0.32)):
                i0 = int((s + off) * SR)
                i1 = min(len(out), i0 + len(golpe))
                if i0 < len(out):
                    out[i0:i1] += g * golpe[: i1 - i0]
    out = _filtro(out, hi=2500)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.max(np.abs(out)) + 1e-6)


# --- Efectos ----------------------------------------------------------------
def whoosh(dur=0.45):
    n = int(dur * SR)
    ruido = rng.standard_normal(n).astype(np.float32)
    ruido = _filtro(ruido, lo=300, hi=4000)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return ruido * env * 0.5


def zumbido_movil():
    partes = []
    for _ in range(2):
        tt = _t(0.32)
        b = np.sign(np.sin(2 * np.pi * 165 * tt)) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * tt))
        partes += [_filtro(b.astype(np.float32), hi=900) * 0.6, np.zeros(int(0.12 * SR), np.float32)]
    return np.concatenate(partes)


def tic():
    n = int(0.05 * SR)
    return (rng.standard_normal(n) * _env(n, 0.0005, 0.006) * 0.7).astype(np.float32)


def boom():
    tt = _t(1.6)
    s = np.sin(2 * np.pi * (60 * np.exp(-tt * 1.5) + 30) * tt) * _env(len(tt), 0.003, 0.5)
    r = _filtro(rng.standard_normal(len(tt)).astype(np.float32), hi=600) * _env(len(tt), 0.002, 0.15)
    return (s * 0.9 + r * 0.4).astype(np.float32)


def riser(dur=1.8):
    tt = _t(dur)
    r = _filtro(rng.standard_normal(len(tt)).astype(np.float32), lo=500, hi=6000)
    tono = np.sin(2 * np.pi * (200 + 900 * (tt / dur) ** 2) * tt)
    env = (tt / dur) ** 2
    return ((r * 0.35 + tono * 0.15) * env).astype(np.float32)


def golpe():
    """Impacto corto para 'punch' de texto."""
    tt = _t(0.35)
    return (np.sin(2 * np.pi * 90 * tt) * _env(len(tt), 0.001, 0.08) * 0.8).astype(np.float32)


def ding():
    tt = _t(0.9)
    return ((np.sin(2 * np.pi * 1760 * tt) + 0.5 * np.sin(2 * np.pi * 2637 * tt)) * _env(len(tt), 0.002, 0.25) * 0.5).astype(np.float32)


def pop():
    tt = _t(0.12)
    return (np.sin(2 * np.pi * (300 + 900 * tt / 0.12) * tt) * _env(len(tt), 0.001, 0.04) * 0.7).astype(np.float32)


def boing():
    tt = _t(0.6)
    f = 180 + 120 * np.sin(2 * np.pi * 9 * tt) * np.exp(-tt * 4)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(tt), 0.003, 0.3) * 0.7).astype(np.float32)


def catacrac():
    partes = [boom() * 0.8]
    for i in range(4):
        n = int(0.09 * SR)
        r = _filtro(rng.standard_normal(n).astype(np.float32), lo=800, hi=5000) * _env(n, 0.001, 0.03)
        partes.append(np.pad(r, (int(i * 0.07 * SR), 0)))
    m = max(len(p) for p in partes)
    return sum(np.pad(p, (0, m - len(p))) for p in partes).astype(np.float32)


def trombon_triste():
    """'Wah wah wah waaah' de fracaso."""
    out = []
    for i, (n, d) in enumerate(((58, 0.35), (57, 0.35), (56, 0.35), (55, 1.0))):
        tt = _t(d)
        f = _nota(n) * (1 + (0.02 * np.sin(2 * np.pi * 6 * tt) if i == 3 else 0))
        x = sum(np.sin(2 * np.pi * f * h * tt) / h for h in range(1, 6))
        out.append(_filtro((x * _env(len(tt), 0.02, d * 0.8)).astype(np.float32), hi=1500) * 0.35)
    return np.concatenate(out)


def kaching():
    """Caja registradora."""
    tt = _t(0.9)
    camp = sum(np.sin(2 * np.pi * f * tt) for f in (2093, 2637, 3136)) / 3 * _env(len(tt), 0.002, 0.3)
    n = int(0.08 * SR)
    clic = np.pad(_filtro(rng.standard_normal(n).astype(np.float32), lo=1500) * _env(n, 0.001, 0.02), (0, len(tt) - n))
    return (np.pad(camp[:-int(0.08 * SR)] * 0.6, (int(0.08 * SR), 0)) + clic * 0.5).astype(np.float32)


def brillo():
    """Destellos ascendentes (cambio a mejor)."""
    out = np.zeros(int(1.0 * SR), np.float32)
    for i, f in enumerate((1568, 1976, 2349, 2637, 3136)):
        tt = _t(0.4)
        nota = np.sin(2 * np.pi * f * tt) * _env(len(tt), 0.002, 0.12) * 0.35
        i0 = int(i * 0.07 * SR)
        out[i0:i0 + len(nota)] += nota[: len(out) - i0]
    return out


def bocina():
    """Error / nota 0 sobre 10."""
    tt = _t(0.55)
    x = np.sign(np.sin(2 * np.pi * 110 * tt)) * 0.5 + np.sign(np.sin(2 * np.pi * 116 * tt)) * 0.5
    return (_filtro(x.astype(np.float32), hi=1200) * _env(len(tt), 0.005, 0.5) * 0.45).astype(np.float32)


def puf():
    """Nube de humo."""
    n = int(0.6 * SR)
    r = _filtro(rng.standard_normal(n).astype(np.float32), lo=150, hi=1800)
    return (r * _env(n, 0.01, 0.2) * 0.8).astype(np.float32)


def flash_camara():
    n = int(0.25 * SR)
    r = _filtro(rng.standard_normal(n).astype(np.float32), lo=2000) * _env(n, 0.001, 0.03)
    return np.concatenate([r, r * 0.6]).astype(np.float32) * 0.7


SFX = {"kaching": kaching, "brillo": brillo, "bocina": bocina, "puf": puf, "camara": flash_camara,
       "ding": ding, "pop": pop, "boing": boing, "catacrac": catacrac, "fracaso": trombon_triste,
       "whoosh": whoosh, "zumbido": zumbido_movil, "tic": tic, "boom": boom, "riser": riser, "golpe": golpe}
