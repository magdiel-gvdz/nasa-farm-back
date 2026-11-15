# Motores agronómicos

Los motores son deterministas: la misma entrada con la misma versión de datos da la misma salida.
No usan modelos estadísticos. Sus umbrales y pesos están en
[`config/engine.yaml`](../config/engine.yaml), que la API valida al arrancar; son decisiones de
diseño que revisa el rol científico (SCI), no hechos científicos. Para cambiar un parámetro basta
editar ese archivo en un pull request.

Todos los datos son **zonales**: describen la celda de 9 km donde cae la geocerca, no la parcela.

## Aptitud de un cultivo (`GET /fields/{id}/suitability`)

Responde "¿puedo sembrar este cultivo en este mes?" con un puntaje de 0 a 100, un estado y una
razón por factor. Código: `app/engines/suitability.py` y `app/engines/water.py`.

### Ciclo del cultivo

- La siembra se supone el día 1 del mes.
- La duración es el punto medio de `cycle_days` del catálogo. El ciclo ocupa
  `duración ÷ 10.14` decenas (36 decenas por año), redondeado, y puede cruzar el fin de año.
- La ventana de cosecha va de la siembra más el ciclo más corto a la siembra más el ciclo más largo.

### Factor helada (`frost`) — fuente `nasa_power`

Se toma la decena del ciclo con mayor probabilidad de helada (`frost_prob`: fracción de años con
al menos un día de Tmin < 0 °C).

| Parámetro | Valor | Significado |
|---|---|---|
| `suitability.frost.warn_prob` | 0.2 | Desde esta probabilidad el factor es `warn` |
| `suitability.frost.bad_prob` | 0.5 | Desde esta probabilidad el factor es `bad` |

Si el cultivo es `frost_tolerant` se usa la probabilidad de helada fuerte (`frost_m2_prob`,
Tmin < −2 °C) y el factor nunca pasa de `warn`: un cultivo tolerante no queda excluido por helada.

### Factor calor (`heat`) — fuente `nasa_power`

Se mira la floración, que ocupa la parte del ciclo indicada por la ventana. DATA publica la
probabilidad de superar 30, 32, 35 y 38 °C; se usa el umbral más cercano a `heat_critical_c` del
cultivo (en empate, el más bajo) y el detalle dice cuál se usó. Se toma la decena de la floración
con mayor probabilidad.

| Parámetro | Valor | Significado |
|---|---|---|
| `suitability.heat.flowering_window` | 0.55-0.65 | Parte del ciclo en la que ocurre la floración |
| `suitability.heat.warn_prob` | 0.3 | Desde esta probabilidad el factor es `warn` |
| `suitability.heat.bad_prob` | 0.6 | Desde esta probabilidad el factor es `bad` |

### Factor agua (`water`) — fuente `nasa_power`

```
demanda        = Σ decenas del ciclo ( Kc de la etapa × ET0 mediana de la decena )
lluvia efectiva = effective_rain_fraction × Σ lluvia mediana de la decena
déficit        = demanda − lluvia efectiva − riego disponible     (mínimo 0)
```

La ET0 es la de referencia de Hargreaves-Samani (FAO-56) que calcula DATA. El Kc cambia por etapa
según los coeficientes del catálogo (FAO-56). El riego es `irrigation.max_mm_per_year` de la
geocerca; si no se declaró riego se evalúa en temporal (riego 0) y el detalle lo dice; si se
declaró riego sin cantidad, se supone que cubre lo que falta y el detalle pide confirmarlo.
La lluvia mediana por decena es una estimación conservadora en zonas donde llueve pocos días.

| Parámetro | Valor | Significado |
|---|---|---|
| `suitability.water.effective_rain_fraction` | 0.8 | Fracción de la lluvia que aprovecha el cultivo |
| `suitability.water.stage_fractions.ini` | 0.2 | Parte del ciclo con Kc inicial |
| `suitability.water.stage_fractions.mid` | 0.5 | Parte del ciclo con Kc medio |
| `suitability.water.stage_fractions.end` | 0.3 | Parte del ciclo con Kc final |
| `suitability.water.warn_deficit_fraction` | 0.10 | Déficit ÷ demanda desde el que el factor es `warn` |
| `suitability.water.bad_deficit_fraction` | 0.25 | Déficit ÷ demanda desde el que el factor es `bad` |

### Factor suelo (`soil`) — fuente `soilgrids`

Compara el pH de la capa de 0-5 cm con el rango `ph` del cultivo. Dentro del rango es `ok`; fuera
por menos de la tolerancia es `warn`; fuera por más es `bad`. Una textura difícil baja un `ok` a
`warn`. El pH y la textura son estimaciones de SoilGrids para la zona, no un análisis de suelo.

| Parámetro | Valor | Significado |
|---|---|---|
| `suitability.soil.ph_tolerance` | 0.5 | Unidades de pH fuera del rango a partir de las que es `bad`; desde la mitad es `warn` |
| `suitability.soil.difficult_textures` | sand, loamy sand, clay, silty clay, sandy clay | Clases texturales USDA que complican el manejo del agua |

### Puntaje y estado

Cada factor recibe un puntaje de 0 a 100: 100 sin riesgo, `score_at_warn` justo en el umbral de
`warn`, `score_at_bad` en el de `bad` y 0 en el peor caso, con tramos lineales. El puntaje final es
la media ponderada de los factores conocidos.

| Parámetro | Valor | Significado |
|---|---|---|
| `suitability.weights.frost` | 0.30 | Peso de la helada |
| `suitability.weights.heat` | 0.20 | Peso del calor |
| `suitability.weights.water` | 0.30 | Peso del agua |
| `suitability.weights.soil` | 0.20 | Peso del suelo |
| `suitability.score_at_warn` | 70 | Puntaje de un factor en el umbral de `warn` |
| `suitability.score_at_bad` | 30 | Puntaje de un factor en el umbral de `bad` |
| `suitability.status_cuts.suitable` | 70 | Puntaje mínimo de `suitable` |
| `suitability.status_cuts.marginal` | 40 | Puntaje mínimo de `marginal`; por debajo es `unsuitable` |
| `suitability.exclusive_factors` | frost | Factores que, en `bad`, descartan el cultivo |
| `suitability.exclusive_score_cap` | 39 | Puntaje máximo cuando un factor excluyente es `bad` |

**Datos faltantes.** Si falta el dato de un factor, queda como `unknown`, no entra en la media y la
confianza baja a `low`. La confianza nunca es `high`: los datos son de la zona, no de la parcela.


## Rotaciones (`POST /fields/{id}/rotations`)

Compara la rotación actual de la geocerca con alternativas y explica en qué se basa cada una.
Código: `app/engines/rotation/` (`candidates.py`, `simulate.py`, `score.py`, `explain.py`). La
geocerca debe declarar `current_rotation` con al menos un cultivo; si no, la respuesta es
`422 current_rotation_required`.

### Rotación actual

Se normaliza a años completos con dos temporadas (`spring_summer` y `fall_winter`); una temporada
sin cultivo es barbecho. El cultivo principal es el que tiene más ciclos. La rotación actual se
muestra siempre como línea base, aunque no sea apta en la zona.

| Parámetro | Valor | Significado |
|---|---|---|
| `rotation.planting_months.spring_summer` | 5 | Mes de siembra por defecto en primavera-verano |
| `rotation.planting_months.fall_winter` | 10 | Mes de siembra por defecto en otoño-invierno |
| `rotation.season_windows.spring_summer` | 3-7 | Meses entre los que se puede mover la siembra |
| `rotation.season_windows.fall_winter` | 9-11 | Meses entre los que se puede mover la siembra |

### Plantillas

Cada alternativa sale de una plantilla que transforma la rotación actual con una intención clara.
No se enumeran todas las secuencias posibles.

| Plantilla | Qué hace |
|---|---|
| `legume` | Sustituye el último ciclo del cultivo principal por la leguminosa más apta. Si el cultivo principal solo tiene un ciclo, la rotación se alarga al doble para alternar |
| `cover` | Ocupa las temporadas en barbecho con el cultivo de cobertura más apto para esos meses |
| `drought` | Cambia el cultivo principal, en todos sus ciclos, por el tolerante a sequía más apto |
| `forage` | Ocupa el barbecho con el forraje más apto. Solo si la geocerca declara ganado |
| `diversify` | Último recurso: alterna el cultivo principal con el cultivo permitido más apto de otra familia |
| `rest` | Relleno: deja un ciclo en barbecho. Solo aparece si las restricciones no dejan otra alternativa |

El cultivo de cada plantilla es el de mayor puntaje de aptitud en el mes de siembra de la
temporada. Nunca se eligen cultivos de `exclude_crops` ni cultivos cuyo equipo no esté en
`constraints.equipment` (si la lista va vacía no se restringe por equipo).

### Orden de relajación

Siempre hay al menos dos alternativas además de la actual. Si no las hay, la búsqueda se relaja en
este orden y la alternativa admitida lo declara en `risks_local_review` y queda con confianza `low`:

1. Solo cultivos `suitable` en el mes de siembra por defecto.
2. Se admiten cultivos `marginal`.
3. Se mueve el mes de siembra dentro de la ventana de la temporada.
4. Se admite cualquier cultivo permitido, aunque sea `unsuitable`.
5. Plantilla `diversify` y, si aún faltan, plantillas `rest`.

Se devuelven la actual y las mejores `max_strategies − 1` alternativas por puntaje global.

### Métricas

La secuencia se repite sobre `horizon_years` y cada métrica es la media anual.

| Métrica | Cálculo |
|---|---|
| `water_demand_mm_per_year` | Suma de la demanda de cada ciclo (Kc por etapa × ET0 mediana), como en aptitud |
| `irrigation_need_mm_per_year` | Suma de lo que la lluvia efectiva no cubre en cada ciclo. Si supera el límite de riego se declara como riesgo con los milímetros que faltan |
| `n_balance_kg_ha_per_year` | Suma de `n_balance_kg_ha` del catálogo. Es un balance aproximado |
| `bare_soil_days_per_year` | Decenas sin cultivo × 10.14 días |
| `erosion_exposure_index` | De 0 a 1: probabilidad de lluvia intensa de las decenas sin cultivo dividida entre la de todo el año. No son toneladas por hectárea: falta la pendiente |
| `om_trend` | Índice = 0.3 × rastrojo medio (`low` 0, `medium` 0.5, `high` 1) + 0.7 × fracción del tiempo con cultivo |
| `pest_break_score` | De 0 a 5: fracción de cambios de cultivo en los que cambia la familia botánica. Repetir siempre la misma familia da 0 |
| `gross_margin_index` | Media de `margin_index` de los cultivos; `null` si alguno no lo tiene |

| Parámetro | Valor | Significado |
|---|---|---|
| `rotation.om_trend.improving_from` | 0.6 | Índice desde el que la tendencia es `improving` |
| `rotation.om_trend.stable_from` | 0.4 | Índice desde el que es `stable`; por debajo, `declining` |

### Puntajes

Cada prioridad va de 0 a 5 y se calcula contra referencias fijas, de modo que añadir o quitar una
alternativa no cambia el puntaje de las demás.

| Prioridad | Cálculo |
|---|---|
| `save_water` | 5 con 0 mm de riego; 0 en la referencia de riego |
| `income` | Proporcional a `gross_margin_index`; `null` si no hay margen, y entonces no entra en el puntaje y se declara en `gaps` |
| `soil_health` | Media de cuatro puntajes: nitrógeno, suelo descubierto, exposición a erosión y tendencia de materia orgánica (1, 3 o 5) |
| `forage` | Ciclos de cultivos forrajeros por año |
| `pest_break` | Igual a `pest_break_score` |
| `low_labor` | 5 con un ciclo por año; 0 en el máximo de ciclos |

| Parámetro | Valor | Significado |
|---|---|---|
| `rotation.references.irrigation_mm` | 1000 | Necesidad de riego anual que vale 0 en `save_water` |
| `rotation.references.n_balance_low_kg_ha` | −150 | Balance de nitrógeno que vale 0 |
| `rotation.references.n_balance_high_kg_ha` | 50 | Balance de nitrógeno que vale 5 |
| `rotation.references.forage_cycles_per_year` | 1 | Ciclos de forraje por año que valen 5 |
| `rotation.references.max_cycles_per_year` | 3 | Ciclos por año que valen 0 en `low_labor` |
| `rotation.references.margin_index` | 1.5 | Índice de margen que vale 5 en `income` |

`overall` (0 a 100) es la media de las prioridades ponderada por los pesos de 0 a 5 del agricultor,
multiplicada por 20. Con todos los pesos en cero se usan pesos iguales. `recommended_id` es la
estrategia con mayor `overall`; en empate gana la rotación actual.

### Explicación

Cada frase de `why`, `evidence`, `benefits`, `gaps` y `risks_local_review` sale de una regla: una
condición sobre las métricas y un texto es/en con los valores interpolados. No interviene ningún
modelo de lenguaje. Toda estrategia declara en `gaps` la resolución zonal y la falta de análisis de
laboratorio, y en `risks_local_review` que plagas, enfermedades y mercado no se observan desde
satélite. Cada `evidence` lleva un valor calculado y un `source_id` de `/sources`.

**Confianza.** `low` si hubo relajación o si algún cultivo tiene un factor de aptitud desconocido;
si no, `medium`.

## Escenarios (`delta_t_c`, `delta_p_pct`)

Código: `app/engines/scenario.py` y `app/engines/indicators.py`. Los motores no saben de
escenarios: reciben una climatología, y el escenario solo decide cuál.

- **Transformación.** `delta_t_c` se suma a las temperaturas diarias ajustadas por altura (máxima,
  mínima y media); `delta_p_pct` multiplica la lluvia diaria. Es un desplazamiento uniforme, no una
  proyección climática: no cambia la variabilidad ni la estacionalidad.
- **Se recalcula**, por año y decena sobre la ventana de los indicadores publicados (2016-2025):
  heladas (Tmin < 0 °C) y heladas fuertes (< −2 °C), días de calor sobre 30, 32, 35 y 38 °C,
  lluvia, días de lluvia intensa (> 25 mm) y ET0 de Hargreaves-Samani (FAO-56, ecuaciones 21 y 52)
  con las temperaturas desplazadas. De ahí salen las probabilidades por decena, los percentiles de
  lluvia, la mediana de ET0 y las decenas vulnerables.
- **No se recalcula** y se toma de los datos publicados (`scenario.not_recomputed`):
  `soil_moisture`, `water_stress`, `bare_soil`, `wind` y `soil`.
- **Paridad.** Con ambos cambios en cero, las probabilidades recalculadas deben coincidir con las
  publicadas por DATA con una diferencia máxima de 0.1 por decena (un año de diez). Con escenario
  cero, la API no recalcula: usa la climatología publicada, así que el resultado es idéntico.
- **Caché.** Climatologías por celda, versión de datos y escenario redondeado a 0.5 °C y 5 %, hasta
  256 entradas.
- **Límites.** `delta_t_c` de −2 a +5 °C y `delta_p_pct` de −50 a +50 %.

## Pruebas de los motores

`tests/engines/test_agronomy_cases.py` reúne casos agronómicos con resultado evidente (sin
heladas, heladas todo el invierno, calor extremo, sin lluvia, suelo alcalino) construidos con
`tests/engines/builders.py`, y compara la matriz de aptitud y las rotaciones de las dos geocercas
de demostración con las instantáneas de `tests/engines/snapshots/`. Un cambio en
`config/engine.yaml`, en el catálogo o en las reglas hace fallar esas instantáneas. Si el cambio es
intencionado, se regeneran y se revisa el diff en el PR:

```powershell
.\.venv\Scripts\python.exe -m tests.engines.test_agronomy_cases
```

