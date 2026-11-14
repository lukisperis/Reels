"""Voces neuronales en español, 100% locales.

- Motor principal: Kokoro (kokoro-onnx), más natural.  Respaldo: Piper.
- Tiempos por palabra: faster-whisper escucha la voz generada y marca cuándo se dice cada palabra,
  así los subtítulos van exactamente sincronizados. También avisa si la voz pronunció algo raro.
"""
import difflib
import re
import unicodedata
import numpy as np
from . import SR, VOCES_DIR

# Reparto de voces. Cambia aquí el "casting" de la serie.
VOCES = {
    "narrador": dict(motor="kokoro", voz="em_alex", velocidad=1.08, efecto=None),
    "futuro":   dict(motor="kokoro", voz="em_santa", velocidad=0.98, efecto="eco"),
    "chica":    dict(motor="kokoro", voz="ef_dora", velocidad=1.05, efecto=None),
    "chico":    dict(motor="piper", modelo="es_ES-sharvard-medium", speaker=0, ritmo=0.90, efecto=None),
}

_cache = {}


# ---------------------------------------------------------------------------
# Utilidades de audio
# ---------------------------------------------------------------------------
def _remuestrear(a, sr_in, sr_out):
    if sr_in == sr_out:
        return a.astype(np.float32)
    x = np.arange(0, len(a), sr_in / sr_out)
    return np.interp(x, np.arange(len(a)), a).astype(np.float32)


def _recortar_silencio(a, sr, umbral=0.01, margen=0.03):
    idx = np.where(np.abs(a) > umbral)[0]
    if len(idx) == 0:
        return a
    m = int(margen * sr)
    return a[max(0, idx[0] - m): idx[-1] + m]


def _eco(a):
    out = np.copy(a)
    for ms, g in ((70, 0.32), (150, 0.2), (260, 0.12)):
        d = int(SR * ms / 1000)
        out[d:] += g * a[:-d]
    f = np.fft.rfft(out)
    freqs = np.fft.rfftfreq(len(out), 1 / SR)
    f[freqs < 180] *= 0.3
    out = np.fft.irfft(f, len(out)).astype(np.float32)
    return out / (np.max(np.abs(out)) + 1e-6) * 0.9


# ---------------------------------------------------------------------------
# Motores de voz
# ---------------------------------------------------------------------------
def _kokoro(texto, cfg):
    if "kokoro" not in _cache:
        from kokoro_onnx import Kokoro
        _cache["kokoro"] = Kokoro(str(VOCES_DIR / "kokoro-v1.0.onnx"), str(VOCES_DIR / "voices-v1.0.bin"))
    a, sr = _cache["kokoro"].create(texto, voice=cfg["voz"], speed=cfg["velocidad"], lang="es")
    return _remuestrear(_recortar_silencio(np.asarray(a, np.float32), sr), sr, SR)


def _chatterbox(texto, cfg):
    """Voz Chatterbox Multilingual (muy natural). Corre en .venv-voz como proceso aparte; guarda caché."""
    import hashlib
    import json
    import subprocess
    import soundfile as sf
    from . import CACHE, RAIZ
    ref = cfg.get("ref")
    ref_path = str(RAIZ / "fabrica" / "voces_ref" / f"{ref}.wav") if ref else None
    clave = json.dumps([texto, ref, cfg.get("exageracion", 0.5), cfg.get("cfg", 0.5), cfg.get("semilla", 7)])
    destino = CACHE / "tts" / (hashlib.sha1(clave.encode()).hexdigest()[:20] + ".wav")
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        if "chatterbox" not in _cache:
            proc = subprocess.Popen([str(RAIZ / ".venv-voz" / "bin" / "python"), str(RAIZ / "fabrica" / "chatterbox_worker.py")],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            while True:
                linea = proc.stdout.readline()
                if not linea:
                    raise RuntimeError("Chatterbox no arrancó (¿falta .venv-voz? ejecuta ./setup.sh)")
                if linea.startswith("{") and json.loads(linea).get("listo"):
                    break
            _cache["chatterbox"] = proc
        proc = _cache["chatterbox"]
        proc.stdin.write(json.dumps({"texto": texto, "ref": ref_path, "salida": str(destino),
                                     "exageracion": cfg.get("exageracion", 0.5), "cfg": cfg.get("cfg", 0.5),
                                     "semilla": cfg.get("semilla", 7)}) + "\n")
        proc.stdin.flush()
        while True:
            r = proc.stdout.readline()
            if not r:
                raise RuntimeError("Chatterbox se cerró")
            if r.startswith("{"):
                r = json.loads(r)
                break
        if not r.get("ok"):
            raise RuntimeError(r.get("error"))
    a, sr = sf.read(str(destino), dtype="float32")
    return _remuestrear(_recortar_silencio(a, sr), sr, SR)


def _piper(texto, cfg):
    from piper import PiperVoice, SynthesisConfig
    k = "piper:" + cfg["modelo"]
    if k not in _cache:
        _cache[k] = PiperVoice.load(str(VOCES_DIR / f"{cfg['modelo']}.onnx"))
    v = _cache[k]
    tono = cfg.get("tono", 1.0)          # >1 más agudo (joven), <1 más grave (mayor)
    sc = SynthesisConfig(speaker_id=cfg.get("speaker"), length_scale=cfg.get("ritmo", 0.9) * tono,
                         noise_scale=cfg.get("expresividad", 0.75), noise_w_scale=0.85)
    a = np.concatenate([c.audio_float_array for c in v.synthesize(texto, sc)])
    sr = v.config.sample_rate
    # cambio de tono manteniendo la duración: se sintetiza más lento y se reproduce más rápido
    return _remuestrear(_recortar_silencio(a, sr), sr * tono, SR)


# ---------------------------------------------------------------------------
# Alineación palabra a palabra con faster-whisper
# ---------------------------------------------------------------------------
def _norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def _whisper():
    if "whisper" not in _cache:
        try:
            from faster_whisper import WhisperModel
            _cache["whisper"] = WhisperModel("small", device="cpu", compute_type="int8",
                                             download_root=str(VOCES_DIR / "whisper"))
        except Exception as e:  # noqa: BLE001
            print(f"  ! faster-whisper no disponible ({e}); uso tiempos estimados")
            _cache["whisper"] = None
    return _cache["whisper"]


_UNID = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis "
         "diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco "
         "veintiséis veintisiete veintiocho veintinueve").split()
_DEC = "_ _ _ treinta cuarenta cincuenta sesenta setenta ochenta noventa".split()
_CEN = ("_ ciento doscientos trescientos cuatrocientos quinientos seiscientos setecientos ochocientos "
        "novecientos").split()


def _numero_es(n):
    """Número a palabras en español (0–9999), suficiente para horas, fechas y cantidades."""
    if n < 30:
        return _UNID[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEC[d] + (f" y {_UNID[u]}" if u else "")
    if n == 100:
        return "cien"
    if n < 1000:
        c, r = divmod(n, 100)
        return _CEN[c] + (f" {_numero_es(r)}" if r else "")
    if n < 10000:
        m, r = divmod(n, 1000)
        return ("mil" if m == 1 else f"{_UNID[m]} mil") + (f" {_numero_es(r)}" if r else "")
    return ""


def _expandir_numero(palabra, t0, t1):
    """Whisper escribe '47'; el guion dice 'cuarenta y siete'. Lo pasamos a palabras repartiendo el tiempo."""
    m = re.fullmatch(r"(\W*)(\d+)(\W*)", palabra)
    if not m:
        return [(palabra, t0, t1)]
    ws = _numero_es(int(m.group(2))).split()
    if not ws:
        return [(palabra, t0, t1)]
    n = len(ws)
    return [(w, t0 + (t1 - t0) * i / n, t0 + (t1 - t0) * (i + 1) / n) for i, w in enumerate(ws)]


def _tiempos_estimados(palabras, dur):
    pesos = [len(_norm(w)) + 2 + (3 if re.search(r"[,;:.!?…]$", w) else 0) for w in palabras]
    tot, acc, out = sum(pesos), 0, []
    for w, p in zip(palabras, pesos):
        out.append((w, dur * acc / tot, dur * (acc + p) / tot))
        acc += p
    return out


def alinear(audio, texto):
    """Devuelve [(palabra_del_guion, t_ini, t_fin)] usando lo que Whisper oye en el audio."""
    palabras = texto.split()
    dur = len(audio) / SR
    m = _whisper()
    if m is None:
        return _tiempos_estimados(palabras, dur), None
    a16 = _remuestrear(audio, SR, 16000)
    segs, _ = m.transcribe(a16, language="es", word_timestamps=True)
    oidas = []
    for s in segs:
        for w in (s.words or []):
            oidas += _expandir_numero(w.word.strip(), w.start, w.end)
    if not oidas:
        return _tiempos_estimados(palabras, dur), ""
    a = [_norm(w) for w in palabras]
    b = [_norm(w[0]) for w in oidas]
    tiempos = [None] * len(palabras)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tiempos[i1 + k] = (oidas[j1 + k][1], oidas[j1 + k][2])
        elif op == "replace" and j2 > j1:
            t0, t1 = oidas[j1][1], oidas[j2 - 1][2]
            for k in range(i2 - i1):
                tiempos[i1 + k] = (t0 + (t1 - t0) * k / (i2 - i1), t0 + (t1 - t0) * (k + 1) / (i2 - i1))
    # rellenar huecos interpolando entre vecinos conocidos
    est = _tiempos_estimados(palabras, dur)
    for i in range(len(palabras)):
        if tiempos[i] is None:
            prev = next((tiempos[j][1] for j in range(i - 1, -1, -1) if tiempos[j]), 0.0)
            nxt = next((tiempos[j][0] for j in range(i + 1, len(palabras)) if tiempos[j]), dur)
            tiempos[i] = (prev, max(prev + 0.05, min(nxt, prev + (est[i][2] - est[i][1]))))
    oido = " ".join(w[0] for w in oidas)
    return [(w, t[0], t[1]) for w, t in zip(palabras, tiempos)], oido


def sintetizar(texto, voz="narrador"):
    """Devuelve (audio float32 @44.1k, [(palabra, t_ini, t_fin), ...], texto_oido_por_whisper)."""
    cfg = VOCES[voz]
    try:
        motor = {"kokoro": _kokoro, "piper": _piper, "chatterbox": _chatterbox}[cfg["motor"]]
        audio = motor(texto, cfg)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {cfg['motor']} falló ({e}); uso Piper")
        audio = _piper(texto, dict(modelo="es_ES-davefx-medium", ritmo=0.86))
    audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.92
    palabras, oido = alinear(audio, texto)   # alinear antes del eco: Whisper oye mejor la voz limpia
    if cfg["efecto"] == "eco":
        audio = _eco(audio)
    return audio.astype(np.float32), palabras, oido
