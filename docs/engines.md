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

**Escenarios.** Los parámetros `delta_t_c` y `delta_p_pct` se aceptan pero todavía no cambian el
resultado; los aplicará el motor de escenarios (`d4`).
