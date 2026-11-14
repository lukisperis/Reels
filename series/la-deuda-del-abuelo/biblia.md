# La deuda del abuelo — Biblia de la serie

**Formato:** dibujos animados (`"estilo": "cartoon"`), 30 episodios de 35–50 s. El público decide qué
hace Leo al final de cada episodio (A/B en comentarios). Se hace **a demanda**: cuando el usuario da el
resultado de la votación, se produce el siguiente día.

**Premisa:** el abuelo Paco debe **10.000 €** a Don Ramiro, el hombre más rico del barrio. Si no paga
en 30 días, Ramiro se queda con el **Bar Paco** (abierto desde 1985, la vida del abuelo). Leo, su nieto
de 17 años, tiene 3,20 € y promete conseguir el dinero.

## Voz (desde el día 2, estilo del vídeo de referencia)
UNA sola voz para todo (narrador y personajes): Chatterbox con `mls_8882`, `exageracion` 0.65,
`cfg` 0.35, `tono` 0.85 (más grave). Copiar el bloque `voces` de `dia-02.json`.

## Personajes (copiar `personajes` y `voces` del día 1 en cada episodio)
- **LEO** — 17 años, rizos, sudadera verde con bolsillo. Ingenioso, cabezota, buen corazón. Voz `LEO`.
- **ABUELO (Paco)** — calvo con canas a los lados, bigote, gafas, rebeca marrón. Tierno, orgulloso,
  no quiere que Leo se meta en líos. Voz `ABUELO`.
- **DON RAMIRO** — traje morado, corbata dorada, cadena de oro, bigote, pelo engominado. El villano
  cómico: tacaño, chulo, siempre aparece cuando a Leo le va bien. Voz `RAMIRO`.
- Secundarios que se pueden crear con el mismo sistema: Nerea (mejor amiga de Leo, lista, con gafas),
  el Chino (vecino del bazar), la madre de Leo, el sobrino pijo de Ramiro.

## Reglas
- **Contador de dinero**: cada episodio muestra `dinero: [antes, después]` con el saldo real de Leo.
  Llevar la cuenta en el historial de abajo. Hay días que gana, días que pierde (¡drama!).
- Gancho en el primer segundo: "Votasteis A/B." + resultado más sorprendente o gracioso.
- Cada decisión tiene consecuencias visibles; las dos opciones deben ser tentadoras y con riesgo.
- Ramiro intenta sabotear a Leo cada pocos episodios.
- Nada ilegal ni peligroso presentado como buena idea: si Leo hace algo turbio, sale mal.

## Arco (orientativo, se adapta a los votos)
- Días 1–7: primeros intentos (vender cosas, trabajos raros), errores y primeros 500 €.
- Días 8–15: un negocio que funciona (p. ej. el propio bar se pone de moda en redes) → Ramiro lo sabotea.
- Días 16–23: gran oportunidad arriesgada (concurso, torneo, apuesta con Ramiro).
- Días 24–29: el secreto: por qué el abuelo pidió el préstamo (para pagar algo de Leo de pequeño).
- **Día 30:** ¿llega Leo a 10.000 €? El final depende de los votos acumulados.

## Historial
| Día | Título | Decisión al final | Dinero de Leo |
|-----|--------|-------------------|---------------|
| 1 | Treinta días | A vende todo / B trabaja para Ramiro → **ganó B** | 3,20 € |
| 2 | Trabajando para el enemigo | Lava 7 coches por 100 € y Ramiro le descuenta 90 €. Descubre el PROYECTO PARKING: demoler el Bar Paco el 14 de diciembre. A contárselo al abuelo / B seguir espiando | 13,20 € |
