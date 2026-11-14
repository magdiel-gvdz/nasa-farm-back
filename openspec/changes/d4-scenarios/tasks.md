# Tasks

## 1. Indicadores

- [ ] 1.1 Incorporar el módulo de indicadores de DATA (anotando su commit de origen) o, si no está disponible, implementar en `app/engines/indicators.py` las definiciones de `docs/fuentes_de_datos.md` §8 con los umbrales de la configuración de DATA; verificar con las pruebas del módulo o con pruebas propias de heladas, calor, lluvia intensa y racha seca
- [ ] 1.2 Implementar ET0 de Hargreaves-Samani con radiación extraterrestre por latitud y día del año (FAO-56 ec. 21) si no viene en el módulo; verificar contra un valor de ejemplo de FAO-56 con tolerancia del 2 %
- [ ] 1.3 Implementar la agregación de indicadores por año y decena a climatología por decena (probabilidades y percentiles) con el mismo tipo que entrega el proveedor de datos; verificar con una prueba de 10 años sintéticos

## 2. Escenario

- [ ] 2.1 Implementar en `app/engines/scenario.py` la transformación de la serie diaria y la construcción de la climatología del escenario, manteniendo de gold los indicadores no recalculados; verificar con pruebas de monotonía para +2 °C y −20 % de lluvia
- [ ] 2.2 Escribir la prueba de paridad: climatología recalculada con deltas en cero frente a la del proveedor, tolerancia 0.1 por decena, para las celdas sintéticas; verificar que pasa y, con datos reales en un preview, anotar el resultado en el PR
- [ ] 2.3 Añadir la caché por celda, versión de datos y deltas redondeados (0.5 °C, 5 %), con 256 entradas; verificar con una prueba que la segunda petición igual no recalcula

## 3. Integración

- [ ] 3.1 Añadir la validación de rangos y el paso de la climatología del escenario a aptitud (parámetros de consulta) y a rotaciones (objeto `scenario`); verificar con pruebas de `200`, `422` y de igualdad entre escenario cero y sin escenario
- [ ] 3.2 Añadir a las respuestas el bloque `scenario` (valores, origen de la serie, `not_recomputed`, aviso es/en) y regenerar `contracts/openapi.json`; verificar con la prueba de contrato
- [ ] 3.3 Implementar el error `daily_unavailable` solo para escenarios distintos de cero; verificar con la prueba de serie diaria forzada a fallar
- [ ] 3.4 Medir en un preview dos escenarios seguidos para la geocerca de Saltillo y verificar que ambos responden en menos de 2 s; anotar los tiempos en el PR
- [ ] 3.5 Añadir a `docs/engines.md` qué se recalcula, qué no, la regla de paridad y los límites; verificar que coincide con `scenario.not_recomputed`
