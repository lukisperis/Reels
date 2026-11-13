# La boda de mi ex — Biblia de la serie

**Formato:** dibujos animados planos (estilo cartoon, `"estilo": "cartoon"`), 30 episodios diarios de
35–60 s. Humor + "glow up" + decisiones del público. Cada episodio acaba con A/B; lo más votado pasa
en el siguiente.

**Premisa:** Tito (31) recibe la invitación de boda de su ex, Vanesa, que se casa el **13 de diciembre**
con Brandon, entrenador personal de 120 kg de músculo. Tito juega a la consola, come pizza fría y no se
ducha. Decide presentarse en la boda **irreconocible**. Tiene 30 días.

## Personajes (definidos en `personajes` del JSON — copiar tal cual en cada episodio)
- **TITO** — protagonista, torpe pero entrañable. Voz `TITO` (Kokoro em_santa). Empieza: greñas, barba
  de 3 días, ojeras, granos, camiseta amarilla manchada, pijama rojo, cuerpo `flaco`.
- **BRANDON** — el novio. Chulo, sonrisa con destello, siempre haciendo músculo. Rival cómico.
- **VANESA** — la ex. Simpática, no es la mala; aparece por mensajes y redes.
- Secundarios que se pueden añadir (mismo sistema de parámetros): la madre de Tito, el entrenador del
  gimnasio, el peluquero, la vecina cotilla.

## Glow up: cómo cambia Tito
Los cambios se aplican en `personajes.TITO` del episodio (y se mantienen en los siguientes):
- `estilo_pelo`: greñas → corto → degradado · `barba`: 0.7 → 0 · `barba_completa`: true (si lo eligen)
- `ojeras`, `granos`, `mancha`: se van quitando · `cuerpo`: flaco → normal → atletico
- `camiseta`/`pantalon`: ropa nueva (colores) · `gafas`: true/false
- Las estadísticas (`stats` en un plano) suben según lo que haga: FÍSICO, ESTILO, AUTOESTIMA (0–100).
  Día 1: FÍSICO 4 · ESTILO 2 · AUTOESTIMA 3.

## Estructura de cada episodio
1. Gancho (0–2 s): "Votasteis X." + la consecuencia más graciosa o el fracaso.
2. 2–3 situaciones cómicas con onomatopeyas (`¡CATACRAC!`, `¡ZAS!`, `¡BOING!`), efectos y Brandon
   apareciendo para presumir.
3. Un pequeño avance real (stats que suben, un cambio visible en Tito).
4. Plano con `"dia": true` + `stats`.
5. Decisión A/B: dos opciones graciosas y tentadoras.

## Arco (orientativo, se adapta a los votos)
- Días 1–7: el desastre inicial (gimnasio, peluquería, dieta, primera carrera).
- Días 8–15: primeras mejoras + Brandon se entera y lo provoca.
- Días 16–23: la cita con alguien nuevo / el traje / clases de baile para la boda.
- Días 24–29: recaída y remontada, ensayo general.
- **Día 30 (13 de diciembre): la boda.** Final según los votos acumulados.

## Historial
- Día 1 ✅ La invitación — final: A gimnasio / B cortarse las greñas.
