# Revisión técnica del catálogo de cultivos

Revisión del 15 de noviembre de 2026 de [`data/crops.yaml`](../data/crops.yaml) y de los umbrales
de aptitud de [`config/engine.yaml`](../config/engine.yaml). Con ella los 14 cultivos pasan a
`reviewed: true`.

## Alcance

- **Cultivos.** Los anuales relevantes para el Sureste (Saltillo, Arteaga, Ramos Arizpe) y La
  Laguna (Torreón, Matamoros, San Pedro) de Coahuila:
  - **Cereales de verano:** maíz y sorgo.
  - **Cereales de invierno y forrajes:** trigo, cebada, avena forrajera y triticale.
  - **Leguminosas:** frijol, garbanzo y veza.
  - **Industriales y hortalizas:** algodón, girasol, melón, chile y papa.
- **Fuera por ahora:** los perennes (alfalfa, nogal, vid, nopal), porque los motores evalúan un
  ciclo de siembra a cosecha.

## Fuentes

| Valor | Fuente |
|---|---|
| Rangos de temperatura, pH, agua y ciclo | FAO EcoCrop |
| Coeficientes `kc` y duraciones | FAO-56, tablas 11 y 12 |
| `heat_critical_c` | Literatura agronómica sobre daño por calor en floración: trigo y cebada ~35 °C en antesis, frijol ~35 °C, papa ~30-32 °C en tuberización, cultivos de clima cálido 38-40 °C |
| `n_balance_kg_ha` | Orden de magnitud: lo que extrae la cosecha retirada, con el residuo incorporado. Las leguminosas de grano dejan poco (frijol +20, garbanzo +30); la veza como abono verde deja casi todo (+80) |

El rango `ph` es el tolerado en campo, no el óptimo. Por eso el maíz llega a 8.0 y la cebada a 8.5:
los dos se cultivan en los suelos calcáreos de Coahuila.

## Decisiones

1. **La temperatura crítica es la de daño en un solo día.** DATA publica la probabilidad de que en
   una decena haya al menos un día sobre 30, 32, 35 o 38 °C. En los datos reales, superar 30 o
   32 °C ocurre casi todos los años en toda la temporada cálida de Coahuila. Con temperaturas
   óptimas como umbral, el motor descartaba los cultivos de verano en todas partes.
2. **Umbrales de helada: aviso 0.1 y descarte 0.3.** Para un cultivo sensible, una helada 1 año de
   cada 10 ya es un aviso y 3 de cada 10 lo descartan. Antes eran 0.2 y 0.5, y el motor admitía
   siembras de maíz en marzo en Saltillo.
3. **Umbrales de calor: aviso 0.3 y descarte 0.9.** Un día sobre la temperatura crítica solo es grave
   si llega casi todos los años.
4. **El calor extremo también descarta.** `exclusive_factors` pasa a ser `[frost, heat]`: un cultivo
   cuya floración cae casi siempre en calor dañino no es apto aunque tenga agua y buen suelo.

## Validación con datos reales

Matrices de aptitud con los datos de Athena (versión `2026111508`) en cinco celdas. Cada letra es un
mes de enero a diciembre: `s` apto, `m` marginal, `u` no apto. La primera columna es con riego de
500 mm y la segunda en temporal.

### Saltillo (`E9_r0463_c0846`, pH 8.0)

```
maiz               uusssssuuuuu   uummsssuuuuu
sorgo              uussssssuuuu   uummsssmuuuu
trigo              ssssssssssss   mmmmmmsmmmmm
cebada             ssssssssssss   mmmmmmsmmmmm
avena_forrajera    ssuuuussssss   mmuuuummmmmm
triticale          ssuusussssss   mmuumummmmmm
frijol             uussssssuuuu   uummmmssuuuu
garbanzo           ssssssssssss   mmmmmmsmmmmm
veza               suuusussssss   muuumummmmmm
algodon            uumsssuuuuuu   uumsssuuuuuu
girasol            uussssssuuuu   uumssssmuuuu
melon              uusssssssuuu   uummmsssmuuu
chile              uumssssuuuuu   uummmmsuuuuu
papa               uuuuuussuuuu   uuuuuummuuuu
```

### La Laguna (`E9_r0461_c0822`, pH 8.3)

```
maiz               smmmmsssssss   mmmmmmmmmmmm
sorgo              ssssssssssss   mmmmmmsmmmmm
trigo              suuuuussssss   muuuuummmmmm
cebada             ssuuuussssss   mmuuuummmmmm
avena_forrajera    uuuuuuuussss   uuuuuuuummmm
triticale          uuuuuuuussss   uuuuuuuummmm
frijol             ssuuuuusssss   mmuuuuummmmm
garbanzo           ssuuuussssss   mmuuuummmmmm
veza               uuuuuuuusssm   uuuuuuuummmu
algodon            mmmmmsssssss   mmmmmmmmmmmm
girasol            ssssssssssss   mmmmmmmmmmmm
melon              ssssssssssss   mmmmmmmmmmmm
chile              muuuuussssss   uuuuuummmmmm
papa               uuuuuuuummmm   uuuuuuuuummu
```

### Lectura

- **Saltillo.** Maíz, frijol y sorgo son aptos de marzo-abril a julio, como en el calendario de
  siembra de primavera-verano. La papa solo es apta a mitad de año, en la ventana entre heladas
  tardías y calor. Los cereales de invierno son aptos en otoño.
- **La Laguna.** La avena, el triticale y la veza son aptos de septiembre a diciembre, cuando se
  siembran en la Comarca. Los cultivos de calor (sorgo, melón, algodón, girasol) son aptos en
  primavera-verano.
- **Norte, Carbonífera y Centro (Allende, Sabinas y Monclova).** Las ventanas son más estrechas,
  por el calor del verano y la helada del invierno. Encajan con las siembras de otoño de cereales y
  las de verano tardío de sorgo y girasol.

### Rotaciones de los campos de demostración

| Campo | Rotación actual | Recomendada | Puntaje |
|---|---|---|---|
| Saltillo (riego 400 mm) | maíz y barbecho de invierno | `legume`: maíz y frijol en años alternos | 68 contra 58 |
| La Laguna (riego 500 mm, con ganado) | maíz y avena forrajera | `drought`: girasol y avena forrajera | 62 contra 44 |

Las dos recomendaciones son agronómicamente razonables. En Saltillo la leguminosa reduce el déficit
de nitrógeno (−50 contra −120 kg/ha al año) y el riego. En La Laguna el girasol pide menos agua que
el maíz (756 contra 896 mm al año) en un acuífero sobreexplotado.

## Limitaciones conocidas

- **Frío sin helada.** El motor no penaliza el frío que no llega a helar. En La Laguna algunos
  cultivos de calor (melón, girasol, maíz) salen aptos en otoño-invierno aunque en la práctica no se
  siembran entonces.
- **Calor por encima de 38 °C.** Es el umbral más alto que publica DATA, así que para algodón,
  sorgo y melón (40 °C) el factor de calor es conservador.
- **Balances de nitrógeno y pH.** Los balances son de orden de magnitud y el pH es el de SoilGrids
  para la zona, no un análisis de suelo.
- **Sin margen económico.** `margin_index` es `null` en todos los cultivos.
