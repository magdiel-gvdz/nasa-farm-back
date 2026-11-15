# Field Shift — Contrato de la API

> Para el equipo de frontend y para quien implemente un endpoint del backend.
> El documento formal es [`contracts/openapi.json`](../contracts/openapi.json) (también en `GET /openapi.json` y `GET /docs` de cada entorno). Esta página explica lo que el esquema no dice.

## Resumen

- Base: `{VITE_API_URL}/api/v1`. `GET /health` y `GET /ready` quedan en la raíz.
- Todas las claves JSON van en `snake_case`. Los cuerpos de petición rechazan claves desconocidas con `422`.
- Los datos son **zonales**: describen la celda de 9 km donde cae la geocerca, no la parcela.
- Todos los endpoints calculan con los datos del proveedor activo; ninguno devuelve ya una respuesta fija. El encabezado `X-Fieldshift-Mock: 1` queda reservado para marcar una respuesta fija si un endpoint nuevo la necesita.

| Endpoint | Estado |
|---|---|
| `POST`, `GET`, `PATCH`, `DELETE /fields` | Real |
| `GET /sources` | Real: fuentes del proveedor de datos activo |
| `GET /crops` | Real: catálogo de `data/crops.yaml` (ver [crop-catalog.md](crop-catalog.md)) |
| `GET /fields/{id}/profile` | Real: se calcula con los datos del proveedor activo |
| `GET /fields/{id}/suitability` | Real: motor de aptitud (ver [engines.md](engines.md)); admite escenario con `delta_t_c` y `delta_p_pct` |
| `POST /fields/{id}/rotations` | Real: motor de rotaciones (ver [engines.md](engines.md)); admite escenario en `scenario` |
| `GET /fields/{id}/greenhouse` | Real: riesgo de viento para invernaderos (ver [engines.md](engines.md)) |

## Diferencias respecto a `backend-handoff.md` §6

1. **Calendario de riesgos en 36 decenas.** `climate.risk_calendar` tiene 36 elementos con `decade` de 1 a 36 (días 1-10, 11-20 y 21 a fin de cada mes), no 52 semanas. Cada decena trae `vulnerable` y `vulnerable_reasons`.
2. **Perfil síncrono.** `GET /fields/{id}/profile` responde `200` con `status: "ready"` en una sola llamada. No hay `202`, ni progreso por fuente, ni `profile:refresh`. `POST /fields` devuelve `profile_status: "ready"`.
3. **Secciones sin dato en `null`.** Lo que el MVP no tiene va como `null` y se nombra en `gaps`: `climate.light`, `terrain.slope_pct`, `water.groundwater`, `land_use` y `hazards.hail`. El frontend debe tratar como anulable cualquier sección marcada así en el esquema.
4. **`erosion_exposure_index` en lugar de `erosion_t_ha_per_year`.** Es un índice (decenas descubiertas × probabilidad de lluvia intensa), no toneladas por hectárea. `gross_margin_index` puede ser `null`.
5. **Error `out_of_region`.** Solo hay datos para cuatro zonas de Coahuila. Fuera de ellas `POST /fields` y `PATCH /fields/{id}` responden `422`. La geocerca devuelve además `cell_id`, `zone_id` y `cell_assignment`.

Otros ajustes menores: los umbrales de helada son 0 °C y −2 °C (`threshold_c`, `severe_threshold_c`), los días de calor se cuentan sobre 30, 35 y 38 °C, `Source` trae `id`, `name`, `organization`, `product`, `url`, `resolution`, `period`, `license` y `data_class` (`observation`, `model`, `derived`, `estimate` o `synthetic`; esta última marca datos de prueba, que es lo que sirve la API mientras `DATA_PROVIDER` sea `fixture`) y cada cultivo incluye `heat_critical_c`. Cada cultivo trae además lo que usa el motor de rotaciones (`n_balance_kg_ha`, `residue`, `root_depth`, `equipment`, `margin_index`, que puede ser `null`) y su procedencia (`source_id`, `reviewed`); mientras `reviewed` sea `false` los valores son iniciales y no están revisados por el rol científico.

## Perfil de la zona

`GET /fields/{id}/profile` describe la celda de 9 km asignada a la geocerca. Trae `data_version`
(la versión de DATA con la que se calculó; `fixture` con datos sintéticos) y `computed_at`. Si los
datos activos no incluyen la celda de la geocerca responde `503 data_unavailable`.

**Probabilidad mensual.** En `climate.frost.by_month`, `prob_any_frost` es la fracción de años con
al menos una helada en cualquiera de las decenas del mes. Si en 4 de 10 años heló en marzo, vale
`0.4`, aunque en esos años helara en varias decenas. No se obtiene sumando ni promediando las
probabilidades por decena de `climate.risk_calendar`, que responden a otra pregunta: la fracción de
años con el evento en esa decena concreta.

**Umbrales.** `climate.frost.threshold_c` (0 °C), `severe_threshold_c` (−2 °C),
`climate.heat.thresholds_c` (30, 32, 35 y 38 °C) y `climate.rain.heavy_rain_threshold_mm` (25 mm) son
los valores con los que DATA cuenta los eventos. El calendario trae `p_heat_30c`, `p_heat_32c`,
`p_heat_35c` y `p_heat_38c`.

**Suelo y humedad.** Cada capa de `soil.layers` trae en `uncertainty` el rango P05-P95 de cada
propiedad: es la incertidumbre del modelo SoilGrids, no la variación dentro de la zona.
`water.soil_moisture.by_month` da percentiles (`percentile_p10`, `p50`, `p90`, de 0 a 100) y su
`source_id` es la fuente efectivamente usada.

**Vacíos (`gaps`).** Lo que los datos no permiten afirmar. Los códigos son estables:

| Código | Severidad | Cuándo aparece |
|---|---|---|
| `zonal_resolution_9km` | medium | Siempre: los datos son de la zona, no de la parcela |
| `no_lab_analysis` | low | Siempre: el suelo es una estimación, no un análisis de laboratorio |
| `synthetic_data` | high | El entorno sirve datos sintéticos de prueba |
| `shared_climate_series` | medium | Varias celdas comparten la misma serie de clima |
| `elevation_mismatch` | medium | La elevación de la celda difiere más de 300 m de la del cuadro climático |
| `soil_moisture_from_model` | low | La humedad viene de un modelo y no de SMAP |
| `ndvi_not_available` | medium | Sin NDVI: `vegetation` es `null` |
| `no_soil_data` | high | Sin suelo: `soil` es `null` |
| `no_elevation_data` | low | Sin elevación: `terrain` es `null` |
| `no_wind_data` | low | Sin viento: `climate.wind` es `null` |
| `no_daily_series` | low | Sin serie diaria: no hay récords ni fechas de helada |
| `no_slope_data` | low | Siempre: `terrain.slope_pct` es `null` |
| `no_groundwater_source` | medium | Siempre: `water.groundwater` es `null` |
| `no_light_data` | low | Siempre: `climate.light` es `null` |
| `no_land_use_history` | low | Siempre: `land_use` es `null` |
| `no_hail_product` | medium | Siempre: `hazards.hail` es `null` |

## Escenarios

Aptitud (parámetros de consulta) y rotaciones (objeto `scenario` del cuerpo) aceptan
`delta_t_c` de −2 a +5 °C y `delta_p_pct` de −50 a +50 %; fuera de rango responden `422`. Los
valores se redondean a pasos de 0.5 °C y 5 %. Toda respuesta trae el bloque `scenario`: con un
escenario distinto de cero indica los valores aplicados, `daily_origin` (de dónde salió la serie
diaria), `not_recomputed` (lo que el escenario no cambia) y `note`, un aviso de que es un escenario
hipotético y no un pronóstico. Con ambos valores en cero, el resultado es idéntico al de una
petición sin escenario. Si la serie diaria no está disponible, un escenario distinto de cero
responde `503 daily_unavailable`.

## Chat con el asistente agrónomo

Requiere `CHAT_ENABLED=true` en el entorno; si no, todas las rutas responden `503 chat_disabled`.
El modelo es de Amazon Bedrock (API Converse) y se elige con `BEDROCK_MODEL_ID`.

| Método y ruta | Qué hace |
|---|---|
| `POST /chat/conversations` | Crea una conversación, opcionalmente con `field_id` (geocerca activa). `201` con `conversation_id` (`conv_...`) |
| `GET /chat/conversations/{id}` | Historial visible: mensajes del usuario y del asistente con su texto, tarjetas, citas y estado (`done` o `failed`). Nunca incluye resultados de herramientas en bruto |
| `POST /chat/conversations/{id}/messages` | Cuerpo `{"text": "...", "field_id": "..."}` (`field_id` opcional, cambia la geocerca activa). Responde un flujo `text/event-stream` |

Los errores previos al flujo usan el sobre JSON común (`404`, `409 conversation_full`,
`422 message_too_long`, `429 rate_limited` con `Retry-After`, `503 chat_budget_exhausted`).
Límites por defecto: 6 mensajes por minuto y 80 por día por cliente, 1,500 al día en total, 2,000
caracteres por mensaje y 40 mensajes del usuario por conversación.

**Eventos del flujo.** Cada evento es `event: <tipo>` y `data: <JSON>`; las líneas `: ping` son
latidos (uno cada 15 s como mínimo) y se ignoran.

| Evento | Datos | Cuándo |
|---|---|---|
| `status` | `state`, `label` | Siempre el primero |
| `tool` | `name`, `label` (en el idioma de la petición), `state`: `running`, `done` o `failed` | Al empezar y al terminar cada consulta del asistente |
| `card` | `type`, `payload` | Cuando una consulta devuelve una evaluación o una comparación |
| `text` | `delta` | Fragmentos de la respuesta, en orden |
| `citation` | `source_id`, `label` (nombre y periodo) | Una por fuente usada, sin repetir, al final |
| `done` | `message_id`, `usage` (`input_tokens`, `output_tokens`) | Final correcto |
| `error` | `code` (`llm_unavailable`, `refused`, `internal_error`), `message` | Final con error; no hay `done` |

**Tarjetas.** `payload` es exactamente la respuesta del endpoint equivalente:

| `type` | Esquema | Endpoint equivalente |
|---|---|---|
| `suitability` | `SuitabilityDetail` | `GET /fields/{id}/suitability?crop_id=...&planting_month=...` |
| `suitability_matrix` | `SuitabilityMatrix` | `GET /fields/{id}/suitability` |
| `rotations` | `RotationResponse` | `POST /fields/{id}/rotations` |

**Herramientas del asistente.** Operan solo sobre las geocercas del cliente de la conversación y
devuelven lo mismo que su endpoint: `list_user_fields`, `get_field_profile`, `get_risk_calendar`,
`evaluate_crop`, `suitability_matrix`, `compare_rotations` y `list_crops`. Como máximo 8 por mensaje.

Ejemplo de consumo con `fetch`:

```js
const response = await fetch(`${API}/api/v1/chat/conversations/${id}/messages`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Client-Id": clientId, "Accept-Language": "es" },
  body: JSON.stringify({ text: "¿Puedo sembrar maíz en abril?" }),
});
const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
let buffer = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += value;
  const chunks = buffer.split("\n\n");
  buffer = chunks.pop();
  for (const chunk of chunks) {
    if (chunk.startsWith(":")) continue; // latido
    const event = chunk.match(/^event: (.*)$/m)[1];
    const data = JSON.parse(chunk.match(/^data: (.*)$/m)[1]);
    handle(event, data); // status, tool, card, text, citation, done o error
  }
}
```

## Análisis de suelo de laboratorio

`POST /fields/{id}/soil-report` recibe un archivo (`multipart/form-data`, campo `file`): PDF, JPG o
PNG de hasta 10 MB. Un modelo de Bedrock con entrada de documentos (`BEDROCK_EXTRACT_MODEL_ID`) lee
laboratorio, fecha, profundidad, textura, pH, materia orgánica, conductividad eléctrica, CIC,
nitrógeno, fósforo y potasio, en unidades normalizadas (`om_pct`, `ec_ds_m`, `cec_cmol_kg`,
`n_mg_kg`, `p_mg_kg`, `k_mg_kg`). Los valores fuera de un rango plausible se descartan
(pH 3-11, materia orgánica 0-20 %, CE 0-20 dS/m, CIC 0-100 cmol/kg, N ≤ 10,000, P ≤ 2,000 y
K ≤ 10,000 mg/kg) y aparecen en `unreadable_fields` con su motivo.

Con al menos un valor aceptado, la geocerca guarda `soil_lab`; el perfil muestra esos valores en
`soil.lab` con confianza `high`, añade la fuente `lab_report` y retira el vacío
`no_lab_analysis`; la aptitud usa el pH de laboratorio en el factor suelo y lo dice en su detalle.
El archivo se guarda en el almacenamiento privado del entorno, bajo un prefijo del cliente, sin URL
pública. Requiere `CHAT_ENABLED=true` (si no, `503 chat_disabled`).

**No subas documentos con datos personales** (nombre, domicilio, RFC): el modelo los leería.

## Encabezados

| Encabezado | Sentido | Uso |
|---|---|---|
| `X-Client-Id` | Petición | UUID que genera el frontend y guarda en `localStorage`. Obligatorio en todas las rutas de `/fields`. No hace falta en `/crops`, `/sources`, `/health` ni `/ready` |
| `Accept-Language` | Petición | `es` (por defecto) o `en`. Cualquier otro idioma se responde en español. Afecta a los `message` de errores y de `gaps` y a los textos explicativos |
| `Content-Type` | Petición | `application/json` en `POST` y `PATCH` |
| `X-Fieldshift-Mock` | Respuesta | `1` cuando la respuesta es fija. CORS lo expone para que el navegador pueda leerlo |

**`X-Client-Id` no es autenticación.** Solo separa los datos de cada navegador. Quien conozca el UUID de otra persona puede ver y borrar sus geocercas. Es un límite aceptado para el hackathon: no se guardan datos personales y no hay que usar el identificador como secreto.

CORS admite `GET`, `POST`, `PATCH`, `DELETE` y `OPTIONS` desde los orígenes configurados en el entorno (`CORS_ORIGINS`). Un origen no configurado no recibe encabezados de permiso.

## Errores

Todo error, también los de validación, usa el mismo sobre:

```json
{
  "error": {
    "code": "out_of_region",
    "message": "El terreno está fuera de las zonas cubiertas.",
    "details": {}
  }
}
```

`code` es estable y es lo que debe leer el frontend. `message` está en el idioma de la petición y puede cambiar. `details` siempre es un objeto.

## Códigos de error

| Código | Estado | Cuándo | `details` |
|---|---|---|---|
| `validation_error` | 422 | El cuerpo o los parámetros no cumplen el esquema | `fields`: lista de `{field, type, message}`; `field` es la ruta, p. ej. `body.geometry` |
| `invalid_geometry` | 422 | La geometría no es un polígono válido (ver [Geometría](#geometría-y-celda)) | `reason` y datos del límite incumplido |
| `crop_not_found` | 404 | `crop_id` no existe en el catálogo de cultivos | `crop_id` |
| `current_rotation_required` | 422 | Se pidieron rotaciones para una geocerca sin `current_rotation` con algún cultivo | — |
| `not_a_greenhouse` | 409 | Se pidió `/greenhouse` para una geocerca cuyo `kind` no es `greenhouse` | — |
| `chat_disabled` | 503 | El chat está apagado en el entorno (`CHAT_ENABLED=false`) | — |
| `chat_budget_exhausted` | 503 | Se alcanzó el presupuesto diario de mensajes de todos los clientes; vuelve al día siguiente (UTC) | `reason`, `retry_after`; cabecera `Retry-After` |
| `conversation_full` | 409 | La conversación ya tiene 40 mensajes del usuario; hay que abrir otra | — |
| `field_required` | 422 | Una herramienta del chat necesita una geocerca y no hay ninguna activa | `hint` |
| `message_too_long` | 422 | El mensaje del chat supera los 2,000 caracteres | — |
| `rate_limited` | 429 | El cliente superó su límite de mensajes de chat por minuto o por día | `reason` (`per_minute` o `per_day`), `retry_after`; cabecera `Retry-After` |
| `unsupported_file_type` | 415 | El análisis de suelo no es un PDF, JPG o PNG (se comprueba el contenido, no el nombre) | — |
| `file_too_large` | 413 | El análisis de suelo supera los 10 MB | — |
| `not_a_soil_report` | 422 | El documento subido no es un análisis de suelo; la geocerca no cambia | — |
| `llm_unavailable` | 503 | El modelo que lee el análisis de suelo no respondió | — |
| `out_of_region` | 422 | La celda de la geocerca no pertenece a ninguna zona publicada | `cell_id` y `zones`: lista de `{zone_id, name, bbox}` |
| `missing_client_id` | 400 | Falta `X-Client-Id` en una ruta de `/fields` | — |
| `invalid_client_id` | 400 | `X-Client-Id` no es un UUID | — |
| `not_found` | 404 | La ruta no existe, o la geocerca no existe para este cliente | `field_id` cuando aplica |
| `method_not_allowed` | 405 | La ruta no admite ese método | — |
| `field_limit_reached` | 409 | El cliente ya tiene 50 geocercas | `limit` |
| `bad_request` | 4xx | Cualquier otro error de la petición | — |
| `daily_unavailable` | 503 | Se pidió un escenario distinto de cero y la serie diaria de la zona no está disponible; sin escenario la petición funciona | — |
| `data_unavailable` | 503 | El proveedor de datos aún no terminó su primera carga (`/ready`) | — |
| `internal_error` | 500 | Error inesperado. El cuerpo nunca incluye trazas ni nombres internos | — |

## Ciclo de vida de una geocerca

1. `POST /fields` con nombre, tipo y geometría. La API valida la geometría, calcula superficie y centroide, asigna celda y zona y responde `201`. El `id` empieza por `fld_` y es ordenable por fecha de creación.
2. `GET /fields` lista las geocercas del cliente, de la más reciente a la más antigua. `GET /fields/{id}` devuelve una.
3. `PATCH /fields/{id}` cambia solo los campos enviados entre `name`, `geometry`, `current_rotation`, `irrigation`, `livestock` y `greenhouse`. Enviar `null` borra un campo opcional. `kind` no se puede cambiar. Si cambia la geometría se recalculan superficie, centroide, celda y zona; si la geometría nueva es inválida o queda fuera de cobertura, la geocerca no cambia.
4. `DELETE /fields/{id}` responde `204`. Una segunda llamada responde `404`.

Reglas:

- Un invernadero (`kind: "greenhouse"`) necesita el objeto `greenhouse`, al crear y al editar.
- Una geocerca de otro cliente se comporta como si no existiera: `404 not_found`.
- Tope de 50 geocercas por cliente (`409 field_limit_reached`).
- Con la variable `APP_TABLE` las geocercas se guardan en la tabla DynamoDB del entorno y sobreviven a reinicios y despliegues. Sin ella (desarrollo local, y los entornos que aún no tienen tabla) se guardan en memoria y se pierden al reiniciar el proceso.

## Geometría y celda

Se acepta GeoJSON `Polygon` o `MultiPolygon` en WGS84, con posiciones `[lon, lat]`. Se rechaza con `422 invalid_geometry` y un `details.reason`:

| `reason` | Regla |
|---|---|
| `unsupported_type` | Solo `Polygon` y `MultiPolygon` |
| `malformed_coordinates` | Cada punto es `[lon, lat]` con números finitos (se admite una altitud, que se ignora) |
| `coordinates_out_of_range` | Longitud entre −180 y 180, latitud entre −90 y 90. `details.expected_order` recuerda el orden `[lon, lat]`: es el error típico de enviar `[lat, lon]` |
| `ring_too_short` | Cada anillo tiene al menos 4 puntos |
| `ring_not_closed` | El primer y el último punto de cada anillo coinciden |
| `too_many_vertices` | Como máximo 2,000 vértices en total |
| `self_intersection` | El polígono no se cruza consigo mismo y sus partes no se solapan |
| `empty_area` | El polígono tiene superficie |
| `too_large` | Como máximo 10,000 hectáreas |

**Superficie y centroide.** `area_ha` es la superficie geodésica sobre el elipsoide WGS84. `centroid` es `[lon, lat]`.

**Regla de celda dominante.** La geocerca se asigna a **la celda que contiene su centroide**, aunque el polígono se extienda sobre varias; la respuesta lo indica con `cell_assignment: "centroid"`. La malla es EASE-Grid 2.0 global de 9 km (EPSG:6933), la misma del pipeline de datos, y el identificador es `E9_r{fila:04d}_c{columna:04d}`.

**Cobertura.** Hay datos para 136 celdas en cuatro zonas de Coahuila. Si la celda del centroide no es una de ellas, la respuesta es `422 out_of_region` y `details.zones` trae las zonas disponibles con su recuadro `[lon_min, lat_min, lon_max, lat_max]`:

| `zone_id` | Zona | Recuadro |
|---|---|---|
| `coah-sureste` | Sureste | −101.6, 25.2, −100.7, 25.6 |
| `coah-laguna` | La Laguna | −103.5, 25.45, −102.9, 25.85 |
| `coah-norte` | Norte (Cinco Manantiales) | −101.0, 28.15, −100.6, 28.55 |
| `coah-centro` | Centro-Desierto | −102.2, 26.85, −101.4, 27.15 |

Una celda pertenece a una zona cuando su centroide cae dentro del recuadro, así que una geocerca cerca del borde de un recuadro puede quedar dentro o fuera según su celda.

**Contexto administrativo.** `country` y `admin.state` salen de la zona. `admin.municipality` es `null`: una zona abarca varios municipios y no hay límites municipales para decidir con certeza.

## Disponibilidad

- `GET /health`: `200` siempre que el proceso responda. No depende de datos ni de AWS.
- `GET /ready`: `200` con `data_version` cuando el proveedor de datos está listo; `503 data_unavailable` mientras no lo esté.

## Ejemplos

```bash
API=https://URL-DEL-ENTORNO
CID=3f2b8c1e-7a4d-4e9b-9c55-0d1e2f3a4b5c   # un UUID cualquiera, siempre el mismo
```

Catálogos:

```bash
curl "$API/api/v1/crops"
curl "$API/api/v1/sources"
```

Crear una geocerca en Saltillo:

```bash
curl -X POST "$API/api/v1/fields" \
  -H "X-Client-Id: $CID" -H "Content-Type: application/json" \
  -d '{
    "name": "Rancho Los Nogales - Parcela 1",
    "kind": "field",
    "geometry": {"type": "Polygon", "coordinates": [[[-101.02,25.41],[-101.00,25.41],[-101.00,25.43],[-101.02,25.43],[-101.02,25.41]]]},
    "current_rotation": [
      {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
      {"year": 1, "season": "fall_winter", "crop_id": null}
    ],
    "irrigation": {"available": true, "source": "well", "max_mm_per_year": 400}
  }'
```

La respuesta trae `"cell_id": "E9_r0463_c0846"` y `"zone_id": "coah-sureste"`. Guarda el `id` para las llamadas siguientes:

```bash
FID=fld_...

curl "$API/api/v1/fields" -H "X-Client-Id: $CID"
curl "$API/api/v1/fields/$FID" -H "X-Client-Id: $CID"

curl -X PATCH "$API/api/v1/fields/$FID" \
  -H "X-Client-Id: $CID" -H "Content-Type: application/json" \
  -d '{"current_rotation": [{"year": 1, "season": "spring_summer", "crop_id": "sorgo"}]}'

curl "$API/api/v1/fields/$FID/profile" -H "X-Client-Id: $CID" -H "Accept-Language: en"

curl "$API/api/v1/fields/$FID/suitability" -H "X-Client-Id: $CID"
curl "$API/api/v1/fields/$FID/suitability?crop_id=maiz&planting_month=4&delta_t_c=2&delta_p_pct=-20" \
  -H "X-Client-Id: $CID"

curl -X POST "$API/api/v1/fields/$FID/rotations" \
  -H "X-Client-Id: $CID" -H "Content-Type: application/json" \
  -d '{
    "priorities": {"save_water": 5, "income": 3, "soil_health": 4, "forage": 2, "pest_break": 3, "low_labor": 1},
    "constraints": {"irrigation_mm_per_year": 400, "exclude_crops": [], "horizon_years": 4},
    "scenario": {"delta_t_c": 0, "delta_p_pct": 0},
    "max_strategies": 4
  }'

curl -X DELETE "$API/api/v1/fields/$FID" -H "X-Client-Id: $CID"
```

Una geocerca fuera de cobertura (Nevada) responde `422 out_of_region`:

```bash
curl -X POST "$API/api/v1/fields" \
  -H "X-Client-Id: $CID" -H "Content-Type: application/json" \
  -d '{"name": "Nevada", "geometry": {"type": "Polygon", "coordinates": [[[-117.02,39.41],[-117.00,39.41],[-117.00,39.43],[-117.02,39.43],[-117.02,39.41]]]}}'
```

Notas sobre los parámetros:

- `suitability`: `crop_id` y `planting_month` se envían juntos (detalle) o ninguno (matriz). `delta_t_c` admite de −10 a 10 y `delta_p_pct` de −100 a 100.
- `rotations`: todos los campos del cuerpo son opcionales; `{}` usa prioridades iguales, sin restricciones y sin escenario. La respuesta siempre trae al menos 3 estrategias, incluida la actual (`is_current: true`).

## Cambiar el contrato

Tras modificar una ruta o un esquema, regenera el documento y súbelo en el mismo PR:

```bash
python scripts/export_openapi.py
```

Las comprobaciones de CI lo regeneran y fallan si difiere del que está en el repositorio. Ante un conflicto de fusión en `contracts/openapi.json`, no lo resuelvas a mano: actualiza la rama y vuelve a ejecutar el script. No renombres ni quites campos sin avisar al frontend.
