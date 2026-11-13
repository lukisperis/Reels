"""Uso:  python -m fabrica.generar series/cartas-del-futuro/dia-01.json [--rapido]

Crea entregas/<serie>/dia-XX/ con video.mp4, portada.jpg, publicar.md y guion.txt.
"""
import json
import sys
import time
from pathlib import Path
from . import RAIZ
from .montaje import construir


def publicar_md(ep, dur):
    p = ep["publicar"]
    tags = " ".join(p["hashtags"])
    el = ep["eleccion"]
    return f"""# {ep['serie_titulo']} — Día {ep['episodio']}/{ep['total']}

Duración: {dur:.0f} s · Formato 1080x1920 · Listo para YouTube Shorts, TikTok e Instagram Reels.

## YouTube Shorts
**Título:** {p['titulo_youtube']}

**Descripción:**
{p['descripcion']}

{tags}

## TikTok
**Texto:** {p['titulo_tiktok']} {tags}

## Instagram Reels
**Texto:** {p['titulo_tiktok']}

{p['descripcion']}

{tags}

## Comentario fijado (publícalo tú y fíjalo)
{p['comentario_fijado']}

## Encuesta (Stories de Instagram / comunidad de YouTube)
{el['pregunta']}
- A) {el['A']}
- B) {el['B']}

## Checklist al subir
- [ ] Portada: `portada.jpg` (en TikTok/Reels elige el fotograma de portada o súbela).
- [ ] Marca "contenido generado con IA" (YouTube: *Contenido alterado o sintético*; TikTok: *Etiqueta de contenido de IA*).
- [ ] Añade el vídeo a la lista/playlist de la serie.
- [ ] Mañana: apunta en `series/{ep['serie']}/decisiones.md` qué opción ganó (A o B).
"""


def guion_txt(ep):
    out = [f"{ep['serie_titulo']} — Día {ep['episodio']}: {ep['titulo']}", ""]
    for i, e in enumerate(ep["escenas"], 1):
        out.append(f"[{i:02d}] ({e.get('voz', 'narrador')}) {e['texto']}")
    el = ep["eleccion"]
    out += ["", f"FINAL: {el['pregunta']}", f"  A) {el['A']}", f"  B) {el['B']}", f"  {el['cta']}"]
    return "\n".join(out) + "\n"


def main():
    ruta = Path(sys.argv[1])
    rapido = "--rapido" in sys.argv
    ep = json.loads(ruta.read_text(encoding="utf-8"))
    carpeta = RAIZ / "entregas" / ep["serie"] / f"dia-{ep['episodio']:02d}"
    t = time.time()
    video, dur = construir(ep, carpeta, rapido)
    (carpeta / "publicar.md").write_text(publicar_md(ep, dur), encoding="utf-8")
    (carpeta / "guion.txt").write_text(guion_txt(ep), encoding="utf-8")
    print(f"\nListo en {time.time() - t:.0f}s → {carpeta}")


if __name__ == "__main__":
    main()
