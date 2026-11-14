# Tasks

## 1. Esquema y carga

- [ ] 1.1 Definir en `app/catalog/models.py` el modelo de cultivo (campos del contrato más `heat_critical_c`, `n_balance_kg_ha`, `residue`, `root_depth`, `equipment`, `margin_index` opcional, `source_id`, `reviewed`) con sus validaciones y los conjuntos cerrados de roles y familias; verificar con pruebas de cada regla de invalidez
- [ ] 1.2 Implementar `app/catalog/loader.py` que lee `data/crops.yaml`, valida el conjunto (identificadores únicos, cobertura de roles) y se ejecuta al arrancar; verificar con pruebas de catálogo válido, identificador repetido y rango invertido
- [ ] 1.3 Asegurar que `data/crops.yaml` se copia a la imagen Docker; verificar que el contenedor arranca y `/api/v1/crops` responde

## 2. Contenido

- [ ] 2.1 Escribir 5 cultivos de ejemplo (maíz, frijol, avena forrajera, sorgo, veza) con valores de FAO EcoCrop y Kc de FAO-56, marcados `reviewed: false`; verificar que el catálogo carga y cubre los cinco roles
- [ ] 2.2 Sustituir y ampliar con los 12-15 cultivos de SCI cuando los entregue, marcando `reviewed: true`; verificar que el catálogo carga y que SCI aprueba el archivo en la revisión del PR
- [ ] 2.3 Escribir `docs/crop-catalog.md` con la definición y unidad de cada campo para que SCI pueda editar el archivo; verificar que cada campo del modelo aparece en el documento

## 3. Endpoint

- [ ] 3.1 Conectar `GET /api/v1/crops` al catálogo, quitar `X-Fieldshift-Mock` y regenerar `contracts/openapi.json`; verificar con la prueba de contrato
