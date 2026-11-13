# Reels — fábrica de historias interactivas

Genera cada día un vídeo vertical (1080x1920) **listo para subir** a YouTube Shorts, TikTok e
Instagram Reels: guion, voz neuronal en español, imágenes IA, música y efectos propios, subtítulos
dinámicos y un final interactivo A/B que decide el siguiente episodio.

## Dónde están los vídeos
`entregas/<serie>/dia-XX/`
- `video.mp4` → súbelo tal cual.
- `portada.jpg` → miniatura/portada.
- `publicar.md` → títulos, descripción, hashtags y comentario fijado para cada red.
- `guion.txt` → el guion en texto.

## Serie actual: *Cartas del futuro* (10 días)
Leo recibe cada mañana una carta escrita por él mismo dentro de 10 días. Tú (la audiencia) decides
qué hace. Ver `series/cartas-del-futuro/biblia.md`.

**Tu única tarea diaria:** subir el vídeo y apuntar qué ganó (A o B) en
`series/cartas-del-futuro/decisiones.md` (o decírmelo en el chat).

## Generar a mano
```bash
./setup.sh
python -m fabrica.generar series/cartas-del-futuro/dia-01.json
```
El proceso automático que sigue Claude cada día está en `PROCESO_DIARIO.md`.

## Piezas
- `fabrica/voz.py` — voces Piper (locales, gratis).
- `fabrica/imagenes.py` — imágenes vía pollinations.ai + etalonaje.
- `fabrica/sonido.py` — música y efectos sintetizados (sin derechos de autor).
- `fabrica/montaje.py` — zoom/paneo, cortes con "punch", subtítulos karaoke, tarjeta final A/B.
