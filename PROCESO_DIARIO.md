# Proceso diario (lo sigue Claude cada mañana)

Objetivo: dejar **un episodio nuevo listo para subir** en `entregas/<serie>/dia-XX/`.

## 0. Preparar
```bash
./setup.sh          # instala Piper + voces (si no están)
```

## 1. Investigar qué funciona hoy (10 min máx.)
- Busca en la web tendencias recientes de Shorts/TikTok/Reels de **historias en serie**, "parte 2",
  finales interactivos, misterio, romance, terror suave, "qué harías tú".
- Apunta en `tendencias/AAAA-MM-DD.md`: 3–5 hallazgos concretos (formatos, ganchos, sonidos, temas) con
  enlace a la fuente, y **qué vas a aplicar hoy** en el episodio.

## 2. Leer el estado de la serie
- `series/<serie>/biblia.md` (personajes, arco, secreto, reglas de estilo).
- `series/<serie>/decisiones.md` → qué opción ganó ayer. Si está _pendiente_, elige la opción más
  dramática, márcala como "(elegida por defecto)" y avísalo en el resumen.
- El último `dia-XX.json` como referencia de formato.

## 3. Escribir `series/<serie>/dia-XX.json`
- Mismo esquema que `dia-01.json`. Campos clave por escena: `texto`, `voz`, `imagenes`, `pantalla`,
  `mensaje`, `efecto` (`flash`, `shake`), `sfx` (`golpe`, `boom`, `tic`, `zumbido`, `whoosh`, `riser`).
- 13–18 escenas, 45–70 s en total. Empieza con "Votasteis X." + consecuencia inmediata.
- 1 imagen por cada 2–4 s de voz; prompts en inglés, concretos, usando `{LEO}`, `{ALBA}`, `{DANI}`…
- Termina con `eleccion` (A/B) y rellena `publicar` (títulos, descripción, hashtags, comentario fijado).
- Actualiza `biblia.md` (marca el día como publicado) y añade la nueva fila en `decisiones.md`.

## 4. Generar y revisar
```bash
python -m fabrica.generar series/<serie>/dia-XX.json
```
- Extrae 6–8 fotogramas con ffmpeg y míralos: textos legibles, nada tapado, imágenes coherentes.
  Si una imagen sale mal, cambia su `seed` o el prompt y vuelve a generar.

## 5. Entregar
- `git add` de `series/`, `tendencias/` y `entregas/<serie>/dia-XX/` → commit → push.
- Resumen final en el chat: título, duración, la decisión del final y si el voto fue "por defecto".

## Cuando una serie termina
Proponer 3 conceptos nuevos de serie interactiva (distintos entre sí: p. ej. supervivencia, romance,
misterio, terror suave, "vida en 30 días") basados en las tendencias, elegir el mejor y crear
`series/<nueva>/biblia.md` antes del episodio 1.
