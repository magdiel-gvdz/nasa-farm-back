# Spec Delta

## Purpose

Proporciona la serie meteorológica diaria de una celda para los cálculos que no pueden hacerse con indicadores ya agregados, como los escenarios de clima y el viento extremo.

## ADDED Requirements

### Requirement: Serie diaria por celda
El sistema SHALL entregar para una celda la serie diaria con fecha en UTC, temperatura máxima, mínima y media, temperaturas ajustadas por altura, lluvia, radiación, humedad relativa, viento medio y viento máximo, con las unidades del contrato de DATA y valores nulos donde no haya dato.

#### Scenario: Serie de una celda
- **WHEN** se pide la serie diaria de una celda existente
- **THEN** se obtiene una fila por día, ordenada por fecha, que cubre al menos de 2016 a 2025

#### Scenario: Valor de relleno
- **WHEN** la fuente entrega `-999` para un día
- **THEN** ese valor se entrega como nulo

### Requirement: Origen preferente y respaldo
El sistema SHALL usar la serie diaria publicada por DATA cuando exista y, en caso contrario, SHALL obtenerla de NASA POWER. El resultado SHALL indicar su origen como `gold` o `power_live`.

#### Scenario: Vista publicada
- **WHEN** DATA ha publicado la vista de serie diaria
- **THEN** la serie procede de ella y su origen es `gold`

#### Scenario: Vista ausente
- **WHEN** la vista no existe
- **THEN** la serie procede de NASA POWER y su origen es `power_live`

### Requirement: Uso responsable de NASA POWER
El respaldo SHALL pedir a NASA POWER como máximo una vez cada cuadro POWER identificado por `power_cell_lat` y `power_cell_lon` y periodo, guardar la respuesta y reutilizarla en peticiones posteriores, también después de reiniciar el servicio.

#### Scenario: Dos celdas del mismo cuadro
- **WHEN** se piden las series de dos celdas que comparten las coordenadas `power_cell_lat` y `power_cell_lon` del mismo cuadro POWER
- **THEN** se hace una sola llamada a NASA POWER

#### Scenario: Reinicio
- **WHEN** se reinicia el servicio y se vuelve a pedir una serie ya obtenida
- **THEN** no se hace ninguna llamada a NASA POWER

### Requirement: Corrección por altura coherente con DATA
El respaldo SHALL ajustar la temperatura con la fórmula `t_adj = t − tasa × (elevación de la celda − elevación del cuadro) / 1000`, con una tasa configurable de 6.5 °C/km por defecto. Si falta alguna elevación, MUST entregar la temperatura sin ajustar e indicarlo.

#### Scenario: Celda 400 m por encima del cuadro
- **WHEN** la celda está 400 m más alta que el cuadro y la mínima es 2.0 °C
- **THEN** la mínima ajustada es −0.6 °C

#### Scenario: Elevación desconocida
- **WHEN** la celda no tiene elevación publicada
- **THEN** las temperaturas ajustadas son iguales a las originales y el resultado indica `elevation_adjusted` falso

### Requirement: Fallo acotado
Si la serie diaria no puede obtenerse, el sistema SHALL informar un error identificable como `daily_unavailable`, y los endpoints que no la necesitan MUST seguir funcionando.

#### Scenario: NASA POWER no responde
- **WHEN** no hay vista publicada y NASA POWER devuelve error o no responde en 20 segundos
- **THEN** la petición de serie falla con `daily_unavailable` y `GET /api/v1/fields/{id}/profile` sigue respondiendo `200`

### Requirement: Contrato diario publicado y caché
`v_cell_daily` SHALL tratarse como parte del contrato actual de DATA y consultarse por `cell_id`, sin cargarla entera en la instantánea de C2. El respaldo POWER SHALL conservarse para instalaciones sin esa vista; un fallo de permisos o un error transitorio MUST NOT interpretarse como vista ausente ni activar silenciosamente el respaldo. La caché gold SHALL incluir `data_version` y `cell_id` y no reutilizar datos de una publicación anterior tras una recarga. La caché POWER SHALL usar las coordenadas de cuadro publicadas, periodo y parámetros de consulta, sin redondear a una cuadrícula de 0.5°: el contrato describe cuadros de 0.5° × 0.625°. SHALL guardar la respuesta sin ajuste; la corrección por altura SHALL aplicarse por celda después de leer la caché.

#### Scenario: Error de permisos
- **WHEN** Athena deniega la consulta diaria
- **THEN** se registra la causa y se devuelve `daily_unavailable`, sin pasar a POWER como si faltara la vista

#### Scenario: Nueva versión de gold
- **WHEN** cambia la versión de la instantánea y se pide una serie previamente consultada
- **THEN** no se sirve la entrada de caché gold de la versión anterior

#### Scenario: Dos elevaciones del mismo cuadro
- **WHEN** dos celdas comparten coordenadas POWER y periodo pero tienen elevaciones distintas
- **THEN** reutilizan la respuesta cruda y reciben temperaturas ajustadas individualmente
