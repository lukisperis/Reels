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


def musica(dur, estilo="misterio", bpm_latido=70, acorde_seg=4.0):
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


SFX = {"whoosh": whoosh, "zumbido": zumbido_movil, "tic": tic, "boom": boom, "riser": riser, "golpe": golpe}
