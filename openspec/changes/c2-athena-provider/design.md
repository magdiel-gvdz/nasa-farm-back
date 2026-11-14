# Design

## Context

DATA publica en la base `fieldshift_gold` seis vistas (`v_cells`, `v_cell_profile`, `v_cell_indicators`, `v_cell_year`, `v_cell_soil`, `v_sources`) que filtran por dentro la versión vigente y no la exponen. La versión vigente está en el parámetro SSM `/fieldshift/data_version`. El contenedor es de larga vida, con 2 GB de memoria. La vista más grande, `v_cell_indicators`, tiene unas 49,000 filas.

## Goals / Non-Goals

**Goals:**
- Ninguna petición de usuario espera a Athena.
- Tras una publicación de DATA, la API sirve la versión nueva en menos de 10 minutos sin redesplegar.

**Non-Goals:**
- Consultar tablas de silver o gold directamente, o escribir en el lake.
- Escalar a miles de celdas; a esa escala habría que volver a consultas por celda con caché.

## Decisions

- **Carga completa en memoria en lugar de consulta por petición.** Seis consultas sin `WHERE` al arrancar y en cada recarga. Alternativa descartada: `WHERE cell_id = ?` por petición con caché, que mantiene la latencia de Athena en el primer acceso a cada celda y depende de la reutilización de resultados de 60 minutos.
- **Arranque no bloqueante.** La carga corre en segundo plano; `/health` responde desde el primer momento (la plataforma lo usa para dar por sano el contenedor) y `/ready` responde `503` hasta completar la primera carga.
- **Instantánea inmutable con intercambio atómico.** Cada carga construye un objeto nuevo indexado por `cell_id` y solo al terminar y validar sustituye la referencia vigente. Una petición en curso nunca ve datos mezclados de dos versiones.
- **Detección de versión por SSM, no por tiempo.** Un bucle revisa el parámetro cada 5 minutos y recarga solo si cambió. Las consultas de carga se lanzan sin reutilización de resultados para no recibir la versión anterior.
- **Validación de esquema por vista:** lista de columnas obligatorias por vista (las que usan perfil y motores). Columnas adicionales se ignoran, de acuerdo con la regla de DATA de que agregar columnas no rompe el contrato.
- **`awswrangler`** para ejecutar y leer resultados, con sesión de boto3 en `DATA_REGION`. La conversión de rellenos y tipos (`NaN` a nulo) se hace una vez, al construir la instantánea.
- **Vista opcional `v_cell_daily`:** si existe se carga bajo demanda por celda (ver `c4-daily-series`), no en la instantánea.

## Risks / Trade-offs

- [La carga inicial tarda decenas de segundos] → `/ready` lo refleja; la prueba de humo del despliegue usa `/health`.
- [DATA publica una versión con una columna renombrada] → La validación rechaza la carga, la API sigue con la versión anterior y registra qué columna falta.
- [Dos tareas del servicio recargan en momentos distintos] → Durante minutos pueden responder versiones diferentes; `data_version` aparece en `/ready` y en el perfil para poder detectarlo.
- [Permisos entre regiones mal configurados] → El primer arranque en un preview lo revela; el error de acceso se registra con el recurso denegado.

## Migration Plan

1. Fusionar con `DATA_PROVIDER=fixture` en todos los entornos.
2. Cuando DATA publique gold V0, cambiar la variable de repositorio a `athena` y redesplegar `dev`.
3. Vuelta atrás: devolver la variable a `fixture`.
