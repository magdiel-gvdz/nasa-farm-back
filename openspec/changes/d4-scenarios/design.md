# Design

## Context

Los motores leen climatología por decena (probabilidades y medianas sobre 2016-2025). DATA calcula esos indicadores en su job `gold_build` con funciones de pandas compatibles con Python 3.9, a partir de la serie diaria con temperaturas ajustadas por altura. La API puede obtener esa misma serie (`c4`). Los umbrales están en el archivo de configuración de DATA.

## Goals / Non-Goals

**Goals:**
- Que el escenario cero y gold den lo mismo, para que las diferencias mostradas se deban solo al escenario.
- Respuesta en menos de 2 segundos para una celda.

**Non-Goals:**
- Proyecciones climáticas, cambios de variabilidad o de estacionalidad: el escenario es un desplazamiento uniforme.
- Recalcular humedad del suelo (SMAP) o NDVI: se mantienen los históricos y se declara.

## Decisions

- **Recalcular con las mismas funciones que DATA.** Si el módulo de indicadores de DATA es accesible, se incorpora tal cual (copiado con su versión anotada) en lugar de reescribirlo. Si no lo es, se implementan en `app/engines/indicators.py` las definiciones de `docs/fuentes_de_datos.md` §8 y la prueba de paridad decide si son válidas.
- **Transformación:** `delta_t_c` se suma a máximas, mínimas y medias ajustadas; `delta_p_pct` multiplica la lluvia diaria. La ET0 se recalcula con Hargreaves-Samani sobre las temperaturas modificadas.
- **Indicadores recalculados:** heladas, días de calor por umbral, lluvia, lluvia intensa, racha seca, ET0 y balance lluvia menos ET0, y sus probabilidades por decena. Estrés hídrico por humedad del suelo y suelo descubierto se toman de gold sin cambios.
- **Los motores no saben de escenarios.** Reciben un objeto de climatología; el escenario solo decide cuál se les pasa. Evita duplicar reglas.
- **Caché** de climatologías recalculadas por celda, versión de datos, `delta_t_c` y `delta_p_pct`, con los deltas redondeados a 0.5 °C y 5 %, y un máximo de 256 entradas. Los controles del frontend se mueven en esos pasos.
- **Paridad como contrato:** con deltas en cero, las probabilidades recalculadas deben coincidir con gold dentro de una tolerancia de 0.1 (un año de diferencia sobre diez) por decena. Si la paridad falla y no hay tiempo de corregir, la respuesta de escenario se expresa como diferencia aplicada sobre gold.
- **Límites:** `delta_t_c` de −2 a +5 y `delta_p_pct` de −50 a +50.

## Risks / Trade-offs

- [La serie diaria de respaldo (POWER en vivo) no coincide exactamente con la de DATA] → La prueba de paridad se ejecuta con el origen activo y la respuesta informa el origen de la serie.
- [Recalcular 10 años diarios por petición es lento] → Operaciones vectorizadas y caché; medir con la celda de demostración.
- [El usuario interpreta el escenario como predicción] → Texto fijo en la respuesta: "escenario hipotético, no pronóstico".
