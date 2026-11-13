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

## Serie activa: *La boda de mi ex* (30 días, dibujos animados)
Tito tiene 30 días para llegar irreconocible a la boda de su ex. El público decide cada paso de su
glow up. Ver `series/la-boda-de-mi-ex/biblia.md`. Los personajes se dibujan por código
(`fabrica/caricatura.py`), así que son idénticos en todos los episodios.

En pausa: *Cartas del futuro* (estilo cine, `series/cartas-del-futuro/`).

**Tu única tarea diaria:** subir el vídeo y apuntar qué ganó (A o B) en
`series/la-boda-de-mi-ex/decisiones.md` (o decírmelo en el chat).

## Generar a mano
```bash
./setup.sh
python -m fabrica.generar series/cartas-del-futuro/dia-01.json
```
El proceso automático que sigue Claude cada día está en `PROCESO_DIARIO.md`.

## Piezas
- `fabrica/voz.py` — voces **Kokoro** (locales, gratis; Piper de respaldo) + **faster-whisper**, que
  escucha la voz generada para sincronizar los subtítulos palabra a palabra y comprobar que se entiende
  (informe en `entregas/.../_revision_voz.txt`).
- `fabrica/imagenes.py` — imágenes vía pollinations.ai + etalonaje. Opcional: **ComfyUI** en tu PC con
  GPU (`COMFYUI_URL=http://IP:8188 COMFYUI_CKPT=modelo.safetensors`) para más calidad.
- `fabrica/caricatura.py` — personajes y fondos de dibujos animados (poses, expresiones, boca que
  habla, onomatopeyas, estadísticas, móvil). Fuentes Anton y Luckiest Guy en `fabrica/fuentes/`.
- `fabrica/sonido.py` — música y efectos sintetizados (sin derechos de autor).
- `fabrica/montaje.py` — zoom/paneo, cortes con "punch", subtítulos karaoke, tarjeta final A/B.

## Skills y herramientas añadidas
- `.claude/skills/` — skills de Anthropic (skill-creator, canvas-design, algorithmic-art, frontend-design,
  theme-factory, etc.) y la skill de **explainroo** (vídeos explicativos con `npx --yes explainroo`).
  Se cargan solas en las sesiones de Claude Code de este repositorio.
- faster-whisper, Kokoro y Piper se instalan con `./setup.sh` (no hace falta copiar sus repositorios).
