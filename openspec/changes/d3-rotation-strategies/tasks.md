# Tasks

## 1. Candidatos

- [x] 1.1 Implementar en `app/engines/rotation/candidates.py` la normalización de la rotación actual (años, temporadas, barbechos) y el error `current_rotation_required`; verificar con pruebas de una rotación de un año y de una de dos años
- [x] 1.2 Implementar las plantillas `legume` y `cover` eligiendo el cultivo de mayor aptitud para la temporada, con exclusiones y equipo; verificar con datos sintéticos de Saltillo que se obtienen dos alternativas distintas de la actual y que un cultivo excluido no aparece
- [x] 1.3 Implementar las plantillas `drought` y `forage` (esta solo con ganado declarado) y el recorte a `max_strategies` por puntaje; verificar con pruebas con y sin ganado
- [x] 1.4 Implementar la relajación ordenada cuando hay menos de dos alternativas y su marca para los riesgos; verificar con un catálogo reducido que la respuesta mantiene tres estrategias

## 2. Simulación

- [x] 2.1 Implementar en `simulate.py` el calendario por decenas de cada estrategia sobre el horizonte, con fechas de siembra y cosecha; verificar con una prueba que el número de días sin cultivo de maíz-barbecho coincide con el cálculo manual
- [x] 2.2 Implementar las métricas de agua (reutilizando `app/engines/water.py`) y de nitrógeno; verificar con la prueba de la leguminosa
- [x] 2.3 Implementar días de suelo descubierto, índice de exposición a erosión y tendencia de materia orgánica; verificar con la prueba del cultivo de cobertura
- [x] 2.4 Implementar el puntaje de ruptura de plagas por familia y el índice de margen opcional; verificar con la prueba de la misma familia repetida y con un catálogo sin `margin_index`

## 3. Puntaje

- [x] 3.1 Implementar en `score.py` la normalización de métricas a puntajes de 0 a 5 con referencias en `config/engine.yaml`, el puntaje global ponderado y `recommended_id`; verificar con las pruebas de `save_water` con peso 5 y de pesos en cero
- [x] 3.2 Implementar la confianza de la estrategia; verificar con una prueba de estrategia con relajación

## 4. Explicación

- [x] 4.1 Implementar en `explain.py` el mecanismo de reglas (condición sobre métricas → clave de texto con valores) y los catálogos es/en; verificar con una prueba que toda clave existe en ambos idiomas
- [x] 4.2 Escribir las reglas de `why`, `benefits` y `evidence` (con `source_id`) para cada plantilla y para la rotación actual; verificar con una prueba que toda estrategia tiene las tres listas no vacías y toda evidencia cita una fuente existente
- [x] 4.3 Escribir las reglas de `gaps` y `risks_local_review` (mínimos garantizados, riego insuficiente, relajación, sin margen) y el `disclaimer`; verificar con las pruebas de riego de 500 frente a 400 mm y del aviso en inglés
- [ ] 4.4 Revisar con SCI los textos generados para las dos geocercas de demostración y corregir; verificar con la aprobación de SCI en el PR
  - Bloqueada: requiere la revisión del rol científico y las geocercas de demostración de `g2`

## 5. Endpoint

- [x] 5.1 Conectar `POST /fields/{id}/rotations`, quitar la respuesta fija y regenerar `contracts/openapi.json` si cambió el modelo; verificar con pruebas de API de `200`, `404` y `422`
- [x] 5.2 Verificar con una prueba que dos llamadas iguales devuelven cuerpos idénticos y que la respuesta tarda menos de 1 s con el catálogo completo
- [x] 5.3 Añadir a `docs/engines.md` las plantillas, las fórmulas de cada métrica, la normalización y el orden de relajación; verificar que cada métrica del modelo de respuesta aparece en el documento
