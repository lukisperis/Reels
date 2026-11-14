"""Proceso de voz Chatterbox (se ejecuta con .venv-voz). Lee peticiones JSON por stdin, una por línea."""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
import soundfile as sf  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(4)
from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402

modelo = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
print(json.dumps({"listo": True, "sr": modelo.sr}), flush=True)
for linea in sys.stdin:
    p = json.loads(linea)
    try:
        torch.manual_seed(p.get("semilla", 7))
        w = modelo.generate(p["texto"], language_id="es", audio_prompt_path=p.get("ref"),
                            exaggeration=p.get("exageracion", 0.5), cfg_weight=p.get("cfg", 0.5),
                            temperature=p.get("temperatura", 0.8))
        sf.write(p["salida"], w.squeeze(0).numpy(), modelo.sr)
        print(json.dumps({"ok": True}), flush=True)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}), flush=True)
