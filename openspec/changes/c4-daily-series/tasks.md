# Tasks

## 1. Serie desde gold

- [x] 1.1 Añadir a `AthenaProvider` la detección de `v_cell_daily` en la carga y la lectura bajo demanda por celda con caché en memoria (máximo 32 celdas); verificar con el ejecutor simulado los casos de vista presente y ausente
- [x] 1.2 Convertir las filas a `DailyRow` (fechas UTC, nulos, orden); verificar con una prueba de orden y de relleno a nulo

## 2. Respaldo NASA POWER

- [x] 2.1 Implementar en `app/data/power.py` el cliente del endpoint diario por punto (parámetros `T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M,WS10M_MAX`, comunidad `AG`, `time-standard=UTC`, 2016 al último año completo o desde 1991 si se configura), con tiempo límite de 20 s, un reintento y pausa de 2 s entre llamadas; verificar con una respuesta grabada como dato de prueba
- [x] 2.2 Implementar la clave de caché por `power_cell_lat`, `power_cell_lon`, periodo y parámetros de consulta (cuadro de 0.5° × 0.625°, sin redondear coordenadas), guardando la respuesta original en `cache/power/` del bucket del entorno o en un directorio local; verificar con pruebas de dos celdas del mismo cuadro (una llamada) y de segunda lectura sin llamada
- [x] 2.3 Convertir la respuesta a `DailyRow` (`-999` a nulo, unidades) y aplicar la corrección por altura con la tasa de configuración, usando la elevación del cuadro que devuelve POWER y la de la celda; verificar con el caso de 400 m y el de elevación desconocida
- [x] 2.4 Añadir `power_live` a las fuentes devueltas cuando se usa el respaldo, con clase de dato "modelo" y nota de estimación en las temperaturas ajustadas; verificar con una prueba de `sources`

## 3. Integración

- [x] 3.1 Implementar `daily(cell_id)` en el proveedor con la precedencia gold → POWER, el campo de origen y el error `daily_unavailable`; verificar con pruebas de las tres ramas
- [x] 3.2 Verificar con una prueba de API que, con la serie diaria forzada a fallar, el perfil responde `200`
- [ ] 3.3 En un preview, pedir la serie de una celda de Saltillo por el respaldo y verificar que el objeto aparece en `cache/power/` y que la segunda llamada no sale a Internet (registro); documentar en `README.md` la variable de la tasa y el origen de la serie
  - Documentado en `README.md`. La verificación en un preview requiere `DATA_PROVIDER=athena` sin `v_cell_daily`; DATA ya publica la vista, así que el respaldo no se activa en ningún entorno y se verificó con pruebas y una descarga real desde local

## 4. Coherencia con el contrato publicado

- [x] 4.1 Distinguir vista ausente de errores de permisos o transitorios; probar que solo la ausencia activa el respaldo POWER y que los demás casos devuelven `daily_unavailable`
- [x] 4.2 Indexar la caché gold por `data_version` y `cell_id`, coordinando las consultas diarias con el protocolo de publicación de C2; probar que una recarga no reutiliza series de la versión anterior
- [x] 4.3 Guardar POWER crudo y ajustar temperaturas por celda después de leer la caché; probar dos celdas del mismo cuadro y distinta elevación con una sola descarga
