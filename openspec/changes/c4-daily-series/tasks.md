# Tasks

## 1. Serie desde gold

- [ ] 1.1 Añadir a `AthenaProvider` la detección de `v_cell_daily` en la carga y la lectura bajo demanda por celda con caché en memoria (máximo 32 celdas); verificar con el ejecutor simulado los casos de vista presente y ausente
- [ ] 1.2 Convertir las filas a `DailyRow` (fechas UTC, nulos, orden); verificar con una prueba de orden y de relleno a nulo

## 2. Respaldo NASA POWER

- [ ] 2.1 Implementar en `app/data/power.py` el cliente del endpoint diario por punto (parámetros `T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M,WS10M_MAX`, comunidad `AG`, `time-standard=UTC`, 2016 al último año completo o desde 1991 si se configura), con tiempo límite de 20 s, un reintento y pausa de 2 s entre llamadas; verificar con una respuesta grabada como dato de prueba
- [ ] 2.2 Implementar la clave de caché por centro de cuadro de 0.5° y periodo, guardando la respuesta original en `cache/power/` del bucket del entorno o en un directorio local; verificar con pruebas de dos celdas del mismo cuadro (una llamada) y de segunda lectura sin llamada
- [ ] 2.3 Convertir la respuesta a `DailyRow` (`-999` a nulo, unidades) y aplicar la corrección por altura con la tasa de configuración, usando la elevación del cuadro que devuelve POWER y la de la celda; verificar con el caso de 400 m y el de elevación desconocida
- [ ] 2.4 Añadir `power_live` a las fuentes devueltas cuando se usa el respaldo, con clase de dato "modelo" y nota de estimación en las temperaturas ajustadas; verificar con una prueba de `sources`

## 3. Integración

- [ ] 3.1 Implementar `daily(cell_id)` en el proveedor con la precedencia gold → POWER, el campo de origen y el error `daily_unavailable`; verificar con pruebas de las tres ramas
- [ ] 3.2 Verificar con una prueba de API que, con la serie diaria forzada a fallar, el perfil responde `200`
- [ ] 3.3 En un preview, pedir la serie de una celda de Saltillo por el respaldo y verificar que el objeto aparece en `cache/power/` y que la segunda llamada no sale a Internet (registro); documentar en `README.md` la variable de la tasa y el origen de la serie
