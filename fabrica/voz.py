"""Voces neuronales en español (Piper, 100% local) con tiempos aproximados por palabra."""
import re
import numpy as np
from . import SR, VOCES_DIR

# Reparto de voces. Cambia aquí el "casting" de la serie.
VOCES = {
    "narrador": dict(modelo="es_ES-davefx-medium", speaker=None, ritmo=0.86, efecto=None),
    "futuro":   dict(modelo="es_ES-carlfm-x_low", speaker=None, ritmo=0.95, efecto="eco"),
    "chico":    dict(modelo="es_ES-sharvard-medium", speaker=0, ritmo=0.90, efecto=None),
    "chica":    dict(modelo="es_ES-sharvard-medium", speaker=1, ritmo=0.90, efecto=None),
}

_cargadas = {}


def _voz(modelo):
    if modelo not in _cargadas:
        from piper import PiperVoice
        _cargadas[modelo] = PiperVoice.load(str(VOCES_DIR / f"{modelo}.onnx"))
    return _cargadas[modelo]


def _frases(texto):
    partes = re.split(r"(?<=[.!?…])\s+", texto.strip())
    return [p for p in partes if p]


def _recortar_silencio(a, umbral=0.01, margen=0.03, sr=22050):
    idx = np.where(np.abs(a) > umbral)[0]
    if len(idx) == 0:
        return a
    m = int(margen * sr)
    return a[max(0, idx[0] - m): idx[-1] + m]


def _a_44k(a):
    # 22050 -> 44100 por interpolación lineal
    x = np.arange(len(a) * 2) / 2.0
    return np.interp(x, np.arange(len(a)), a).astype(np.float32)


def _eco(a):
    out = np.copy(a)
    for ms, g in ((70, 0.32), (150, 0.2), (260, 0.12)):
        d = int(SR * ms / 1000)
        out[d:] += g * a[:-d]
    # leve "radio": quita graves por FFT
    f = np.fft.rfft(out)
    freqs = np.fft.rfftfreq(len(out), 1 / SR)
    f[freqs < 180] *= 0.3
    out = np.fft.irfft(f, len(out)).astype(np.float32)
    return out / (np.max(np.abs(out)) + 1e-6) * 0.9


def sintetizar(texto, voz="narrador", pausa_frase=0.18):
    """Devuelve (audio float32 @44.1k, [(palabra, t_ini, t_fin), ...])."""
    from piper import SynthesisConfig
    cfg = VOCES[voz]
    v = _voz(cfg["modelo"])
    sc = SynthesisConfig(speaker_id=cfg["speaker"], length_scale=cfg["ritmo"])
    trozos, palabras, t = [], [], 0.0
    for frase in _frases(texto):
        audio = np.concatenate([c.audio_float_array for c in v.synthesize(frase, sc)])
        audio = _recortar_silencio(audio, sr=v.config.sample_rate)
        audio = _a_44k(audio)
        dur = len(audio) / SR
        ws = frase.split()
        pesos = [len(re.sub(r"\W", "", w)) + 2 + (3 if re.search(r"[,;:]$", w) else 0) for w in ws]
        tot = sum(pesos)
        acc = 0
        for w, p in zip(ws, pesos):
            palabras.append((w, t + dur * acc / tot, t + dur * (acc + p) / tot))
            acc += p
        trozos.append(audio)
        trozos.append(np.zeros(int(pausa_frase * SR), np.float32))
        t += dur + pausa_frase
    audio = np.concatenate(trozos[:-1]) if trozos else np.zeros(1, np.float32)
    if cfg["efecto"] == "eco":
        audio = _eco(audio)
    audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.92
    return audio.astype(np.float32), palabras
