# Guion de la demo

Dos geocercas preparadas en `demo/fields.json`, con una historia agronómica clara cada una. Se
siembran en el entorno con un `X-Client-Id` fijo, así que la demo no depende de dibujar un polígono
en directo.

## Antes de presentar

1. Sembrar las geocercas (idempotente: se puede repetir sin duplicar):

   ```powershell
   .\.venv\Scripts\python.exe scripts/seed_demo.py --base-url https://<url-de-dev>
   ```

   Imprime el `X-Client-Id` de la demo (`de000000-0000-4000-8000-000000000001`) y el `id` de cada
   geocerca. El frontend debe usar ese `X-Client-Id` (guardarlo en `localStorage`) para verlas.
2. Comprobar el recorrido: `scripts/smoke_e2e.py --base-url <dev> --zone sureste` y `--zone laguna`
   terminan con `OK` (ver [smoke.md](smoke.md)).
3. Anotar la versión de datos que informa `GET /ready` (`data_version`). Con `fixture` los datos son
   sintéticos: hay que decirlo al presentar.

En las llamadas de abajo, `$API` es la URL del entorno, `$CID` el `X-Client-Id` de la demo y `$FID`
el `id` de la geocerca que imprime el script.

## 1. Rancho Los Nogales, Saltillo (Sureste)

**Historia.** Maíz en primavera-verano y el suelo descubierto en invierno, con heladas frecuentes.
Riego de pozo limitado a 400 mm al año. ¿Qué alternativa cubre el suelo y aporta nitrógeno sin pedir
más agua?

| Paso | Qué se muestra | Llamada | Qué se espera |
|---|---|---|---|
| 1 | La geocerca y su celda de 9 km | `GET /api/v1/fields/$FID` | Celda `E9_r0463_c0846`, zona `coah-sureste` |
| 2 | Perfil: calendario de riesgos | `GET /api/v1/fields/$FID/profile` | Decenas vulnerables por helada de diciembre a febrero; vacíos `zonal_resolution_9km` y `no_lab_analysis` |
| 3 | ¿Maíz en abril? | `GET .../suitability?crop_id=maiz&planting_month=4` | `marginal`: calor en floración, agua y pH en aviso, cada motivo con su fuente |
| 4 | Matriz de aptitud | `GET .../suitability` | Cultivos de invierno (avena, veza) aptos de octubre a enero; maíz no apto en invierno |
| 5 | Rotaciones | `POST .../rotations` con `rotations_request` del archivo | Tres o más estrategias con la actual como línea base; con datos sintéticos se recomienda `legume` |
| 6 | Escenario +2 °C y −20 % de lluvia | El mismo `POST` con `"scenario": {"delta_t_c": 2, "delta_p_pct": -20}` | Más necesidad de riego en todas las estrategias; bloque `scenario` con el aviso de que no es un pronóstico |

## 2. Ejido San Isidro, La Laguna

**Historia.** Maíz y avena forrajera para 40 cabezas de ganado, con calor extremo en verano y lluvia
escasa. Riego de 500 mm al año. ¿Qué rotación da forraje y aguanta el verano con el agua disponible?

| Paso | Qué se muestra | Llamada | Qué se espera |
|---|---|---|---|
| 1 | La geocerca y su celda | `GET /api/v1/fields/$FID` | Celda `E9_r0461_c0822`, zona `coah-laguna` |
| 2 | Perfil | `GET .../profile` | Muchos días sobre 35 y 38 °C en verano; decenas vulnerables por estrés hídrico |
| 3 | ¿Sorgo en mayo? | `GET .../suitability?crop_id=sorgo&planting_month=5` | Calor en floración en `bad`; el detalle dice qué umbral se usó |
| 4 | Rotaciones con prioridad de agua y forraje | `POST .../rotations` con `rotations_request` | La necesidad de riego supera los 500 mm: aparece como riesgo con los milímetros que faltan |
| 5 | Escenario +2 °C y −20 % de lluvia | Igual, con `scenario` | La necesidad de riego sube en todas las estrategias |

## Frases sobre los límites de los datos

Decirlas al presentar; todas salen de la propia respuesta de la API.

- "Los datos describen la zona, una celda de 9 km, no la parcela." (`gaps`, `zonal_resolution_9km`)
- "La lluvia y el viento vienen de un cuadro climático de unos 55 km que comparten varias celdas."
  (`shared_climate_series`)
- "No hay análisis de laboratorio del suelo: pH, nitrógeno y materia orgánica son estimaciones."
- "Plagas, enfermedades y mercado no se ven desde satélite: cada estrategia trae lo que un agrónomo
  local debe validar." (`risks_local_review`)
- "Un escenario desplaza el clima histórico; no es un pronóstico." (`scenario.note`)
- Con `fixture`: "Este entorno usa datos sintéticos de prueba." (`synthetic_data`)

## Pendiente de revisión con SCI

Los resultados de arriba son los de los datos sintéticos y el catálogo de ejemplo sin revisar. Antes
de la demo, el rol científico debe revisarlos con los datos reales. Observaciones abiertas:

1. En Saltillo, la estrategia `legume` sustituye el segundo maíz por veza **sembrada en mayo**. La
   veza es una leguminosa de invierno: es más defendible el frijol en primavera-verano o la veza en
   otoño-invierno. Puede requerir ajustar el catálogo o la plantilla.
2. En La Laguna, el sorgo en mayo sale `suitable` (70) con el factor de calor en `bad`. El calor no es
   un factor excluyente en `config/engine.yaml`; SCI debe decidir si debe serlo.
3. Ningún cultivo tiene `margin_index`, así que la prioridad de ingreso no entra en el puntaje.

Tras corregir, regenerar las instantáneas de los motores
(`python -m tests.engines.test_agronomy_cases`) y revisar el diff.
