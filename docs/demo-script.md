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
3. Anotar la versión de datos que informa `GET /ready` (`data_version`). Los resultados de abajo son
   los de `dev` con datos reales de Athena (versión `2026111508`) y el catálogo revisado
   ([crop-catalog-review.md](crop-catalog-review.md)); con otra versión las cifras pueden moverse un
   poco. Con `fixture` los datos son sintéticos: hay que decirlo al presentar.

En las llamadas de abajo, `$API` es la URL del entorno, `$CID` el `X-Client-Id` de la demo y `$FID`
el `id` de la geocerca que imprime el script.

## 1. Rancho Los Nogales, Saltillo (Sureste)

**Historia.** Maíz en primavera-verano y el suelo descubierto en invierno, con heladas frecuentes.
Riego de pozo limitado a 400 mm al año. ¿Qué alternativa cubre el suelo y aporta nitrógeno sin pedir
más agua?

| Paso | Qué se muestra | Llamada | Qué se espera |
|---|---|---|---|
| 1 | La geocerca y su celda de 9 km | `GET /api/v1/fields/$FID` | Celda `E9_r0463_c0846`, zona `coah-sureste` |
| 2 | Perfil: calendario de riesgos | `GET /api/v1/fields/$FID/profile` | Decenas vulnerables por helada de diciembre a febrero, por calor de abril a julio y por estrés hídrico en primavera; vacíos `zonal_resolution_9km` y `no_lab_analysis` |
| 3 | ¿Maíz en abril? | `GET .../suitability?crop_id=maiz&planting_month=4` | `suitable` (76): helada, calor y pH bien, pero el agua en `bad`: con 400 mm de riego faltan unos 170 mm. Cada motivo con su fuente |
| 4 | Matriz de aptitud | `GET .../suitability` | Maíz, frijol y sorgo aptos de abril a julio; trigo, cebada, avena, triticale y veza aptos en otoño-invierno; la papa solo a mitad de año |
| 5 | Rotaciones | `POST .../rotations` con `rotations_request` del archivo | Cuatro estrategias con la actual (44) como línea base; se recomienda `legume` (66): maíz y frijol en años alternos, balance de nitrógeno de −120 a −50 kg/ha al año y 54 mm menos de riego. `cover` (triticale en invierno) cubre el suelo pero pide 756 mm de riego |
| 6 | Escenario +2 °C y −20 % de lluvia | El mismo `POST` con `"scenario": {"delta_t_c": 2, "delta_p_pct": -20}` | Más necesidad de riego en todas las estrategias (la actual pasa de 509 a 562 mm); sigue ganando `legume`; bloque `scenario` con el aviso de que no es un pronóstico |

## 2. Ejido San Isidro, La Laguna

**Historia.** Maíz y avena forrajera para 40 cabezas de ganado, con calor extremo en verano y lluvia
escasa. Riego de 500 mm al año. ¿Qué rotación da forraje y aguanta el verano con el agua disponible?

| Paso | Qué se muestra | Llamada | Qué se espera |
|---|---|---|---|
| 1 | La geocerca y su celda | `GET /api/v1/fields/$FID` | Celda `E9_r0461_c0822`, zona `coah-laguna` |
| 2 | Perfil | `GET .../profile` | Decenas vulnerables por calor de mayo a agosto y por estrés hídrico en julio-agosto |
| 3 | ¿Sorgo en mayo? | `GET .../suitability?crop_id=sorgo&planting_month=5` | `suitable` (87) con el calor en aviso: en 60 % de los años se superan 38 °C en floración; el detalle dice que la temperatura crítica del sorgo es 40 °C y que se usó el umbral de 38 °C |
| 4 | Rotaciones con prioridad de agua y forraje | `POST .../rotations` con `rotations_request` | Se recomienda `drought` (61 contra 49 de la actual): girasol en lugar de maíz, 140 mm menos de riego. Todas las estrategias superan los 500 mm: aparece como riesgo con los milímetros que faltan |
| 5 | Escenario +2 °C y −20 % de lluvia | Igual, con `scenario` | La necesidad de riego sube en todas las estrategias (la actual de 896 a 956 mm); sigue ganando `drought` |

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

## Revisión científica

El rol científico revisó los resultados con datos reales el 15 de noviembre de 2026
([crop-catalog-review.md](crop-catalog-review.md)). Lo que se corrigió respecto a la versión con
datos sintéticos:

1. En Saltillo, `legume` usaba veza sembrada en mayo. Con el catálogo revisado usa frijol en
   primavera-verano.
2. El calor extremo en floración ahora es un factor excluyente (`exclusive_factors: [frost, heat]`).
   El sorgo en mayo en La Laguna queda en aviso, no en `bad`: su temperatura crítica es 40 °C.

Limitaciones que conviene decir si preguntan:

- Ningún cultivo tiene `margin_index`, así que la prioridad de ingreso no entra en el puntaje.
- En La Laguna, `legume` siembra garbanzo en julio y lo marca "con condiciones" y confianza baja:
  en la Comarca el garbanzo se siembra en invierno. No es la recomendada.
- El motor no penaliza el frío sin helada: algunos cultivos de calor salen aptos en invierno en La
  Laguna.
