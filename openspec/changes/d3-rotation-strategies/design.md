# Design

## Context

Entradas disponibles: la geocerca (rotación actual, riego, ganado), el catálogo de cultivos, la climatología por decena de la celda (probabilidades de helada, calor, lluvia intensa, suelo descubierto, ET0, lluvia), el suelo y la evaluación de aptitud de `d2`. No hay datos de pendiente, de precios ni de plagas observadas. El contrato de salida está en `app/api/schemas/rotations.py`.

## Goals / Non-Goals

**Goals:**
- Siempre al menos tres estrategias comparables, con la actual como línea base.
- Cada afirmación del texto se deriva de una métrica calculada y cita su fuente.
- Respuesta en menos de un segundo.

**Non-Goals:**
- Optimización combinatoria de rotaciones, predicción de rendimiento o cálculo económico real.
- Erosión en toneladas por hectárea (falta pendiente): se usa un índice de exposición.

## Decisions

- **Plantillas en lugar de búsqueda.** Cada plantilla transforma la rotación actual con una intención agronómica clara: (1) `legume`: sustituye un ciclo del cultivo principal por la leguminosa más apta; (2) `cover`: ocupa las temporadas en barbecho con el cultivo de cobertura más apto para esos meses; (3) `drought`: cambia el cultivo principal por el tolerante a sequía más apto; (4) `forage`: añade un forraje, solo si la geocerca declara ganado. Alternativa descartada: enumerar todas las secuencias posibles, que produce resultados difíciles de explicar.
- **Selección del cultivo de cada plantilla** por el mayor puntaje de aptitud de `d2` en el mes de siembra de la temporada, excluyendo `exclude_crops`, cultivos cuyo equipo no está disponible y estados `unsuitable`.
- **Garantía de tres estrategias:** si tras filtrar quedan menos de dos alternativas, se relajan en orden: admitir cultivos `marginal`, y después variar el mes de siembra dentro de la temporada. Una alternativa admitida por relajación lo declara en `risks_local_review`.
- **Simulación por temporadas** sobre `horizon_years` (3 a 5; 4 por defecto), repitiendo la secuencia. Métricas, como media anual:
  - agua: demanda Kc × ET0 y necesidad de riego (reutiliza `app/engines/water.py`), comparada con el límite de riego;
  - nitrógeno: suma de `n_balance_kg_ha` del catálogo;
  - materia orgánica: tendencia `improving`, `stable` o `declining` según el residuo medio y la proporción de tiempo con cobertura;
  - suelo descubierto: días al año sin cultivo;
  - exposición a erosión: suma, sobre las decenas sin cultivo, de la probabilidad de lluvia intensa, normalizada de 0 a 1;
  - ruptura de plagas: de 0 a 5 según cuántas veces se repite la misma familia botánica en temporadas consecutivas;
  - margen: media de `margin_index` si el catálogo lo tiene; si no, la prioridad `income` se excluye del puntaje y se declara en `gaps`.
- **Puntaje por prioridad** de 0 a 5 normalizando cada métrica entre las estrategias comparadas y contra referencias fijas de configuración, para que una sola estrategia no quede siempre en 5. `overall` de 0 a 100 = media ponderada por los pesos del agricultor; con todos los pesos en 0 se usan pesos iguales.
- **Explicación determinista por plantillas.** Cada frase de `why`, `evidence`, `benefits`, `gaps` y `risks_local_review` tiene una condición sobre las métricas y un texto es/en con valores interpolados. `evidence` lleva `claim` y `source_id`. Sin modelo de lenguaje.
- **Vacíos y riesgos mínimos garantizados:** toda estrategia declara la resolución zonal y la falta de análisis de laboratorio en `gaps`, y al menos un riesgo de revisión local (plagas y mercado no se observan desde satélite).
- **Confianza:** la menor de las confianzas de aptitud de sus cultivos; baja si hubo relajación.

## Risks / Trade-offs

- [Coeficientes de nitrógeno y residuo poco precisos] → Están en el catálogo, los revisa SCI y la salida habla de "balance aproximado".
- [La rotación actual es inviable en la zona] → Se muestra igualmente como línea base con su puntaje bajo; no se descarta nunca.
- [Normalizar entre estrategias cambia puntajes al añadir una alternativa] → Las referencias fijas de configuración limitan el efecto; se documenta.
- [Falta de tiempo] → Orden de recorte: quitar la plantilla `forage`, después `drought`, después la métrica de materia orgánica.
