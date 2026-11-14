# Proceso diario (lo sigue Claude cada mañana)

Objetivo: dejar **un episodio nuevo listo para subir** en `entregas/<serie>/dia-XX/`.

## Serie activa: `la-boda-de-mi-ex` (estilo dibujos animados)
`cartas-del-futuro` (estilo cine con imágenes IA) está **en pausa** tras el día 1: no la continúes salvo
que el usuario lo pida.

## 0. Preparar
```bash
./setup.sh          # instala Kokoro, faster-whisper, Piper y voces (si no están)
```

## 1. Investigar qué funciona hoy (10 min máx.)
- Busca en la web tendencias recientes de Shorts/TikTok/Reels: series animadas de **glow up**, retos
  de "X días", historias donde el público decide, humor animado.
- Apunta en `tendencias/AAAA-MM-DD.md`: 3–5 hallazgos concretos con enlace a la fuente y **qué vas a
  aplicar hoy**.

## 2. Leer el estado de la serie
- `series/<serie>/biblia.md` (personajes, glow up, arco, reglas).
- `series/<serie>/decisiones.md` → apunta lo que ha dicho el usuario que ganó. Si no lo ha dicho,
  pregúntaselo antes de escribir el episodio.
- El último `dia-XX.json`: copia `personajes`, `voces` y aplica los cambios de glow up acumulados.

## 3. Escribir `series/<serie>/dia-XX.json`
Mismo esquema que `dia-01.json`. 11–16 escenas, 35–60 s. Empieza con "Votasteis X." + consecuencia.

**Escena (estilo cartoon):** `texto`, `voz` (`narrador` o el id de un personaje con voz en `voces`),
`efecto` (`shake`, `flash`), `sfx`, `pausa` y un `plano`:
- `fondo`: `bar`, `dormitorio`, `movil`, `rayos` (+`variante` 0–3 = amarillo/azul/rosa/verde), `espejo`,
  `gimnasio`, `parque`, `calle`, `plano`.
- `zoom`, `zoom_fin`, `foco` [x, y] (0–1): cámara. Cambia de encuadre en cada escena.
- `personajes`: lista de `{id, x, y, escala, expresion, accion, habla, rot, cambios, …}`
  - `expresion`: neutro, feliz, triste, sorpresa, decidido, enfadado, cansado, asco, enamorado, dolor,
    chulo, llorar, esfuerzo, euforia.
  - `accion`: quieto, jugar, movil, arriba, celebrar, musculo, cruzados, señalar, manos_cara, correr.
  - personajes: `bigote`, `gafas`, `arrugas`, `traje` (color), `corbata`, `cadena`, `botones`,
    `bolsillo`, `barba`, `granos`, `ojeras`, `mancha`; peinados: greñas, corto, degradado, tupe,
    largo, calvo, engominado, rizos, rapado.
  - extras: `habla` (mueve la boca con su voz), `salto`, `temblor`, `entra` (izquierda/derecha),
    `olor`, `moscas`, `sudor`, `lagrimas`, `estrellas`, `rot` (82–88 = tumbado; usa `escala` 0.85).
- `onomatopeya`: `{texto, en, sfx, x, y, rot}` · `movil`: `{de, titulo, avatares, lineas}` ·
  `stats`: `{"FÍSICO": [antes, después], …}` · `dinero`: [antes, después] (+`dinero_y`; la meta va en
  `meta` del episodio) · `dia`: true (letrero DÍA X/30). En el plano de `stats`
  no pongas personajes (se taparían).
- `sfx` disponibles: `pop`, `ding`, `boing`, `catacrac`, `fracaso`, `golpe`, `boom`, `whoosh`,
  `riser`, `tic`, `zumbido`.

**Estilo cine** (series con `imagenes`): ver `series/cartas-del-futuro/dia-01.json`.

Termina con `eleccion` (A/B), `avance` (cierre "MAÑANA · DÍA N+1" con silueta y gancho:
`{"texto": "Mañana, día tres. Suscríbete para no perdértelo.", "pregunta": "TEXTO CORTO…", "personaje": "RAMIRO", "suscribete": true}`; escribe los
números en letra en `texto`), `portada_plano` y `publicar`.

**Expresividad automática:** quien tiene `"habla": true` gesticula, se balancea y mueve boca y cejas
según el volumen; todos reaccionan según su `expresion` (saltan, tiemblan, se encogen) y se miran
entre sí. Usa `expresion` distinta en cada plano para que se note. Actualiza `biblia.md` (historial y glow up)
y añade la fila nueva en `decisiones.md`.

## 4. Generar y revisar
```bash
python -m fabrica.generar series/<serie>/dia-XX.json
```
- Lee `entregas/<serie>/dia-XX/_revision_voz.txt`: si alguna frase sale "REVISAR", reescríbela
  (números en letra, frases más cortas, sin siglas) y vuelve a generar.
- Extrae 8–10 fotogramas con ffmpeg y míralos: nada cortado ni tapado (subtítulos a y≈1330,
  onomatopeyas arriba), personajes enteros, encuadres variados. Corrige y regenera.

## 5. Entregar
- `git add` de `series/`, `tendencias/` y `entregas/<serie>/dia-XX/` → commit → push.
- Resumen final en el chat: título, duración, decisión del final y si el voto fue "por defecto".

## Cuando una serie termina
Proponer 3 conceptos nuevos de serie interactiva (distintos entre sí), elegir el mejor, crear
`series/<nueva>/biblia.md` y cambiar la "Serie activa" de arriba antes del episodio 1.
