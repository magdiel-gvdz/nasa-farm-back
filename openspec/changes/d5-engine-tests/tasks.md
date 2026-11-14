# Tasks

## 1. Datos de prueba

- [ ] 1.1 Crear en `tests/engines/builders.py` constructores de celdas sintéticas con parámetros (sin heladas, heladas todo el invierno, calor extremo, lluvia nula, suelo alcalino); verificar que cada constructor produce un objeto aceptado por la prueba de conformidad del proveedor

## 2. Casos agronómicos

- [ ] 2.1 Escribir casos de aptitud: lugar sin heladas (el factor helada nunca es `bad`), heladas todo el invierno (cultivo sensible sembrado en diciembre es `unsuitable`), calor extremo en floración, lluvia nula sin riego frente a con riego; verificar que pasan con `pytest tests/engines -q`
- [ ] 2.2 Escribir casos de rotaciones: introducir una leguminosa sube el balance de nitrógeno, un cultivo de cobertura reduce días de suelo descubierto y exposición a erosión, la misma familia en años seguidos da el mínimo de ruptura de plagas, un cultivo excluido nunca aparece; verificar que pasan
- [ ] 2.3 Escribir casos de escenarios si `d4-scenarios` está fusionado: +2 °C no reduce probabilidades de calor ni aumenta las de helada, −20 % de lluvia no reduce la necesidad de riego; verificar que pasan o dejar las pruebas marcadas como omitidas con el motivo

## 3. Instantáneas de la demo

- [ ] 3.1 Guardar instantáneas de aptitud (matriz) y rotaciones para las geocercas sintéticas de Saltillo y La Laguna, con un comando documentado para regenerarlas; verificar que la prueba falla al cambiar un peso en `config/engine.yaml` y pasa tras regenerar
- [ ] 3.2 Confirmar que la batería completa corre en el workflow de comprobaciones en menos de 60 s; verificar con la duración del paso en CI
