# Catálogo de cultivos

El catálogo vive en [`data/crops.yaml`](../data/crops.yaml). Es la única fuente de lo que cada
cultivo necesita y aporta: lo leen los motores de aptitud y de rotaciones y lo devuelve
`GET /api/v1/crops`. Para cambiar un valor basta editar ese archivo en un pull request; no hay
que tocar código.

La API valida el archivo completo al arrancar. Si algo no es válido, no arranca y el error
nombra el cultivo y el campo, por ejemplo: `Cultivo 'maiz': ph: el mínimo (7.5) es mayor que
el máximo (5.5)`. Las pruebas (`pytest tests/catalog`) hacen la misma validación antes de fusionar.

## Campos de cada cultivo

Un rango se escribe `[mínimo, máximo]`. Todos los campos son obligatorios salvo `margin_index`.

| Campo | Unidad o valores | Definición |
|---|---|---|
| `id` | texto | Identificador estable, en minúsculas y con guiones bajos (`avena_forrajera`). No se cambia una vez publicado: lo guardan las rotaciones de los usuarios |
| `name` | `{es, en}` | Nombre común en español y en inglés |
| `family` | lista cerrada | Familia botánica. El motor evita repetir familia en años seguidos |
| `roles` | lista cerrada | Papel en la rotación; al menos uno (ver abajo) |
| `cycle_days` | días, rango | De siembra a cosecha, del ciclo más corto al más largo |
| `temp_opt_c` | °C, rango | Temperatura media en la que el cultivo rinde bien |
| `temp_abs_c` | °C, rango | Temperaturas límite que soporta; debe contener a `temp_opt_c` |
| `frost_tolerant` | `true` / `false` | Si aguanta heladas ligeras (Tmin entre 0 y −2 °C) |
| `heat_critical_c` | °C | Tmax que en floración causa daño en un solo día (no la temperatura óptima). El motor usa el umbral de datos más cercano: 30, 32, 35 o 38 °C |
| `water_need_mm` | mm por ciclo, rango | Agua que consume el cultivo en un ciclo |
| `ph` | pH, rango | pH del suelo tolerado (entre 0 y 14) |
| `kc` | `{ini, mid, end}`, sin unidad | Coeficientes de cultivo de FAO-56 en las etapas inicial, media y final; cada uno mayor que 0 y hasta 1.5 |
| `n_fixing` | `true` / `false` | Si fija nitrógeno atmosférico |
| `n_balance_kg_ha` | kg N/ha por ciclo | Balance aproximado de nitrógeno que deja el cultivo: negativo si extrae, positivo si aporta |
| `residue` | `low`, `medium`, `high` | Rastrojo que queda sobre el suelo tras la cosecha |
| `root_depth` | `shallow`, `medium`, `deep` | Profundidad de raíz: menos de 0.6 m, de 0.6 a 1.2 m, más de 1.2 m |
| `equipment` | lista cerrada | Equipo que requiere; puede ir vacía |
| `margin_index` | sin unidad, ≥ 0, opcional | Margen económico relativo entre cultivos (1 = el de referencia). `null` si no hay dato |
| `source_id` | texto | Fuente bibliográfica de los valores (`fao_ecocrop`, o la que indique SCI) |
| `reviewed` | `true` / `false` | `true` cuando el rol científico revisó los valores del cultivo |

## Valores admitidos

- **`roles`:** `cash` (comercial), `legume` (leguminosa), `cover` (cobertura), `forage` (forraje),
  `deep_root` (raíz profunda), `drought_tolerant` (tolerante a sequía).
- **`family`:** `poaceae`, `fabaceae`, `solanaceae`, `cucurbitaceae`, `brassicaceae`,
  `amaranthaceae`, `asteraceae`, `malvaceae`, `amaryllidaceae`, `apiaceae`, `rosaceae`,
  `juglandaceae`, `vitaceae`.
- **`equipment`:** `tractor`, `planter` (sembradora de precisión), `seed_drill` (sembradora de
  grano fino), `combine` (trilladora), `forage_harvester` (ensiladora), `baler` (empacadora),
  `manual_harvest` (cosecha manual).

Si hace falta una familia, un rol o un equipo que no está en la lista, hay que añadirlo en
`app/catalog/models.py` en el mismo pull request.

## Reglas que comprueba la API

- Los identificadores no se repiten.
- En cada rango el mínimo no supera al máximo.
- Un cultivo con rol `legume` tiene `n_fixing: true` y `n_balance_kg_ha` positivo.
- El catálogo completo cubre los roles `cash`, `legume`, `cover`, `forage` y `drought_tolerant`;
  sin ellos el motor no puede armar rotaciones.
- No hay campos desconocidos: una clave mal escrita es un error.

## Estado del contenido

El catálogo tiene 14 cultivos relevantes para el Sureste y La Laguna de Coahuila: maíz, sorgo,
trigo, cebada, avena forrajera, triticale, frijol, garbanzo, veza, algodón, girasol, melón, chile y
papa. Los valores salen de FAO EcoCrop y FAO-56 y los revisó el rol científico el 15 de noviembre
de 2026 contra los datos reales de Athena (`reviewed: true`). La metodología, las fuentes y las
limitaciones están en [crop-catalog-review.md](crop-catalog-review.md).

Fuera del catálogo por ahora: perennes (alfalfa, nogal, vid, nopal), porque los motores evalúan un
ciclo de siembra a cosecha.
