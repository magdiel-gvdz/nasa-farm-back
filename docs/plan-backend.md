# Field Shift — Plan del backend para el hackathon

> **Fecha:** sáb 14-nov-2026, 14:45 (H5.7; H0 = sáb 09:00). Congelación de datos: H32 (dom 17:00). Quedan ~26 h útiles.
> **Insumos:** [fuentes_de_datos.md](fuentes_de_datos.md) (documento de DATA) y [backend-handoff.md](backend-handoff.md) (documento de diseño del backend).
> **Qué es esto:** qué toma el backend de cada documento, qué se construye, en qué orden y qué puede hacerse en paralelo.

---

## 1. Resumen

- **Datos:** se usa el pipeline de DATA (gold precalculado por celda de 9 km, 4 zonas de Coahuila, vistas de Athena). No se usa Google Earth Engine ni cálculo por polígono bajo demanda.
- **API:** se usa la forma del contrato del handoff (`/api/v1`, `X-Client-Id`, geocercas, perfil, aptitud, rotaciones con razones/evidencia/vacíos/riesgos, escenarios).
- **Motor:** determinista y explicable (reglas + puntaje), como piden ambos documentos. El chat con Claude solo explica y cita lo que devuelven las herramientas; nunca calcula.
- **Plataforma:** contenedor Docker en **ECS Express Mode** (Fargate), Python 3.13, Terraform. Se retiran Lambda, Mangum y API Gateway. App Runner no está disponible en la cuenta (ver abajo).
- **MVP:** despliegue + geocercas + perfil + aptitud + 3 rotaciones + escenarios + fuentes. El chat es la primera extensión; invernadero y análisis de suelo, la segunda. ML, capas de zonas, demo de EE. UU. y calidad de agua quedan fuera.

**App Runner no se puede usar.** AWS lo cerró a clientes nuevos el 30-abr-2026 ([aviso oficial](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)) y la cuenta del proyecto no lo había usado: `aws apprunner list-services` responde `SubscriptionRequiredException` en us-east-1 y en us-west-2 (comprobado el 14-nov a las 14:50 con el perfil del proyecto). El reemplazo que recomienda AWS es **ECS Express Mode**: mismo modelo (una imagen, una URL HTTPS, balanceador administrado) sobre Fargate. El plan lo adopta; todo lo demás (Docker, Python, Terraform, SSE) no cambia.

---

## 2. Qué se toma de cada documento

| Tema | Documento de DATA | Handoff | Decisión |
|---|---|---|---|
| Origen de los datos | Gold precalculado, 136 celdas, Athena | FieldProfile por polígono con GEE y APIs en vivo | **DATA.** Es lo único que llega a tiempo y la demo de Saltillo queda cubierta |
| Cobertura | 4 zonas de Coahuila | México + Nevada | **DATA.** Fuera de zona → error `OUT_OF_REGION`. La segunda demo es La Laguna, no Nevada |
| Resolución | Zonal, "en tu zona (celda de 9 km)" | Estadísticas del polígono + grilla de 30 m | **DATA.** Todo texto de la API habla de zona, no de parcela; se declara en `gaps` |
| Forma de la API | 6 vistas, `WHERE cell_id = ?` | Contrato REST completo (§6) | **Handoff**, recortado al MVP (ver §4) |
| Grano temporal | 36 decenas | 52 semanas y 12 meses | **Decenas** para el calendario de riesgos; los meses se agregan desde decenas. Avisar a FE |
| Periodo | Ventana común 2016-2025 | 1991-2025 | **2016-2025** para probabilidades. Fechas de helada P10/P50/P90 con la serie diaria larga de POWER si DATA la expone (tarea P3) |
| Umbrales | `config/thresholds.yaml`, aprueba SCI | Anexo B | **DATA/SCI.** La API devuelve el umbral que usó; no lo fija en código |
| Motor | Reglas + puntaje, sin ML ni IA generativa | Reglas + ML de rendimiento + chat | Reglas y puntaje. **Sin ML.** Chat como extensión, solo para explicar |
| Cómputo | Lambda | App Runner | **Contenedor en ECS Express Mode**, porque App Runner está cerrado para la cuenta. Permite SSE y caché en memoria igual que App Runner |
| Estado | Sin DynamoDB | DynamoDB | **DynamoDB**, una sola tabla, para geocercas y conversaciones |
| IaC | CloudFormation (pila de datos) | Sin definir | **Terraform** para el backend. La pila de DATA sigue aparte; no se migra |
| Región | us-west-2 | us-east-1 | Backend en **us-east-1** (ya está el bootstrap). Los clientes de Athena, S3 y SSM apuntan a us-west-2 con `DATA_REGION` |
| Trazabilidad | Fuente, resolución y clase de dato por cifra | `source_id` + `confidence` + `gaps` | Ambas: `source_id` apunta a `v_sources`, que ya trae la clase de dato |

### Cambios al contrato del handoff que FE debe conocer

1. `risk_calendar` tiene 36 decenas (`decade` 1-36), no 52 semanas.
2. `POST /fields` puede responder `422 OUT_OF_REGION`. La respuesta trae `cell_id` y `zone_id`.
3. El perfil se responde en una sola llamada (`200`, `status: "ready"`); no hay `202` ni progreso por fuente, porque los datos ya están calculados.
4. Métricas de rotación que no tienen dato detrás se quitan o cambian: `erosion_t_ha_per_year` → `erosion_exposure_index` (decenas descubiertas × probabilidad de lluvia intensa); `gross_margin_index` solo si SCI entrega un índice relativo por cultivo.
5. Secciones del perfil que no existen en el MVP y van como `null` + entrada en `gaps`: `terrain.slope_pct`, `water.groundwater`, `land_use`, `hazards.hail`, `climate.light`.

---

## 3. Arquitectura objetivo

```
Frontend (React, CloudFront)
        │ HTTPS JSON + SSE, header X-Client-Id
        ▼
ECS Express Mode (Fargate + balanceador administrado): contenedor FastAPI (Python 3.13, uvicorn, puerto 8080)   us-east-1
  app/api/      rutas /api/v1
  app/store/    geocercas y conversaciones → DynamoDB (tabla única por entorno)
  app/data/     DataProvider: fixtures | Athena (gold) | POWER en vivo (respaldo)
  app/profile/  arma el FieldProfile a partir de gold
  app/engines/  suitability, rotation, scenario
  app/agent/    Bedrock + herramientas + SSE (extensión)
        │ solo lectura
        ▼
Vistas v_* en Athena (fieldshift_gold) + SSM /fieldshift/data_version   us-west-2 (DATA)
```

- **Carga de datos:** al arrancar, el contenedor lee las 6 vistas completas a memoria (136 celdas; `v_cell_indicators` son ~49,000 filas). Las peticiones no esperan a Athena. Se vuelve a cargar cuando cambia `/fieldshift/data_version` (revisión cada 5 min), lo que además evita servir la versión anterior tras una publicación.
- **Entornos:** `dev` y `pr-N` como hoy. Todos leen el mismo lake de DATA en solo lectura, así que los previews tienen datos reales.
- **El bucket por entorno** que ya existe se queda para `uploads/` y `cache/`. El manifiesto en S3 se retira: `/sources` sale de `v_sources`.

---

## 4. Alcance

| Nivel | Contenido | Tareas |
|---|---|---|
| **MVP** (listo en H24) | Docker + ECS Express Mode + CI; `/health`, `/ready`, `/crops`, `/sources`; CRUD de `/fields`; `/fields/{id}/profile`; `/fields/{id}/suitability`; `POST /fields/{id}/rotations`; escenarios `delta_t_c` y `delta_p_pct` | P, A, B, C, D, G |
| **Extensión 1** (H18-H28) | Chat agrónomo con Bedrock, herramientas y SSE | E |
| **Extensión 2** (si sobra tiempo) | Viento para invernaderos (Gumbel); subida del análisis de suelo | F |
| **Fuera** | ML de rendimiento, GEE, IMERG, GRACE, ECOSTRESS, OCO-2, CDL/SSURGO y demo de EE. UU., calidad de agua, capas PNG de zonas, perfil asíncrono | — |

Lo que queda fuera se declara en `gaps` y en la presentación como límite conocido; el reto pide mostrar los vacíos de información.

---

## 5. Tareas

Cada tarea tiene su spec de OpenSpec en `openspec/changes/<id>-<nombre>/` (propuesta, requisitos con escenarios y lista de tareas verificables); se aplica con `$openspec-apply-change`. Cada tarea es un PR pequeño hacia `main` (regla del repo). Abrir los PR como **borrador** mientras se trabaja: el workflow no crea el entorno efímero para borradores, y cada preview en ECS tarda varios minutos en crearse.

### P. Prerrequisitos (personas, ahora mismo; no son código)

| ID | Tarea | Quién | Bloquea |
|---|---|---|---|
| P1 | ~~Comprobar acceso a App Runner~~ **Hecho: no hay acceso.** Queda: crear a mano un servicio de ECS Express Mode de prueba con una imagen pública para confirmar que funciona en la cuenta y medir cuánto tarda; borrarlo después | TL | A3 |
| P2 | Pedir acceso al modelo de Claude en Bedrock en us-east-1 | TL | E |
| P3 | Responder a DATA (su §13): misma cuenta AWS para lake y API; se aceptan vistas sin `data_version`; pedir una vista nueva `v_cell_daily` (serie diaria de POWER por celda con temperaturas ajustadas, idealmente 1991-2025) | TL + DATA | C4, D4 |
| P4 | Acordar con FE los 5 cambios de contrato de §2 | BE + FE | B1 |
| P5 | SCI entrega el catálogo de 12-15 cultivos para Coahuila con el esquema de `GET /crops` más coeficientes de N, residuo y familia; confirma umbrales | SCI | D1 |
| P6 | Confirmar dónde vive el código de DATA (`ingest/common/grid.py`, funciones de indicadores) para reutilizarlo | DATA | B4, D4 |

### A. Plataforma: Docker, Terraform y CI

| ID | Tarea | Depende | Horas | Hecho cuando |
|---|---|---|---|---|
| A1 | `Dockerfile` (python:3.13-slim, usuario sin root, uvicorn en 8080) y `.dockerignore`. Mangum y `scripts/package_lambda.py` se quedan hasta A4, porque el despliegue actual los usa. `docker build` en `check.yml`. En esta máquina `docker` no está en el PATH: instalar o arrancar Docker Desktop, o validar la imagen solo en CI | — | 1 | La imagen arranca y `/health` responde |
| A2 | `infra/bootstrap`: repositorio ECR compartido; permisos del rol de despliegue para ECR, ECS, balanceador, DynamoDB y los roles del servicio (ejecución, tarea e infraestructura); ampliar el límite de permisos de ejecución (DynamoDB, Athena, Glue, S3 del lake en lectura, bucket de resultados de Athena, SSM, Bedrock). **Conservar los permisos de Lambda y API Gateway** hasta que dev haya migrado, para que Terraform pueda destruirlos. Requiere `terraform apply` manual con credenciales de administrador | P1 | 2 | Bootstrap aplicado; el rol de CI puede crear un servicio |
| A3 | `infra/environment`: reemplazar Lambda + API Gateway por el servicio de ECS Express Mode (imagen de ECR, health check en `/health`, 1 vCPU / 2 GB, 1 tarea), con rol de ejecución, rol de tarea y rol de infraestructura. Confirmar el nombre del recurso en el proveedor AWS 6.73 fijado en el repo (`aws_ecs_express_gateway_service`); si no existe en esa versión, subir el proveedor o usar ECS Fargate + ALB clásico. Subir el tiempo de inactividad del balanceador o enviar latidos para el SSE del chat; tabla DynamoDB (`client_id`, `sk`, pago por petición); variables `image_tag`, `data_region`, nombres del workgroup y del lake; actualizar `tests/environments.tftest.hcl` y salidas | A2 | 3.5 | `terraform test` pasa; plan limpio |
| A4 | `infrastructure.yml`: construir y subir la imagen (etiqueta = SHA) antes de Terraform; adaptar `destroy-preview` y `cleanup-preview.yml`; quitar Mangum y el empaquetador de Lambda. Va en la misma rama y PR que A3 | A1, A3 | 1.5 | Un PR crea `pr-N` con su URL HTTPS y la prueba de humo pasa |
| A5 | Migrar `dev` (merge del PR; destruye la Lambda `nasa-farm-dev-api` que hoy está desplegada), comprobar URL y pasar `VITE_API_URL` a FE. Después, quitar del bootstrap los permisos de Lambda y API Gateway | A4 | 0.5 | `dev` responde desde ECS |
| A6 | Actualizar `README.md` y `openspec/config.yaml` (todavía dicen Lambda/Mangum) | A5 | 0.5 | — |

Notas: el balanceador no tiene el límite de peticiones que daba API Gateway; la protección de costo del chat va en la aplicación (E5). CORS debe permitir `PATCH`, `DELETE` y los headers `X-Client-Id` y `Accept-Language`; hoy solo permite `GET`/`POST` y `Content-Type`/`Authorization` (se corrige en B2).

### B. Esqueleto y contrato de la API

| ID | Tarea | Depende | Horas | Hecho cuando |
|---|---|---|---|---|
| B1 | Modelos Pydantic de todo el contrato del MVP y rutas `/api/v1` que devuelven **respuestas fijas** (un JSON por endpoint, celda de Saltillo). Publicar `openapi.json` a FE | P4 | 2 | FE puede integrar contra el preview |
| B2 | Transversales: sobre de errores `{"error": {code, message, details}}`, dependencia `X-Client-Id`, `Accept-Language` (es/en), CORS corregido, `/ready` basado en el proveedor de datos | B1 | 1 | Pruebas de contrato pasan |
| B3 | `app/store`: interfaz de repositorio con implementación en memoria (local y pruebas) y DynamoDB. CRUD de `/fields` separado por `client_id` | B1 | 2 | CRUD probado con ambas implementaciones |
| B4 | `app/geo`: validar GeoJSON, área en ha, centroide, y polígono → `cell_id` con la malla EASE-Grid 2.0 de 9 km (portar `grid.py` de DATA con sus 7 pruebas). Celda dominante = la del centroide. Si la celda no está en `v_cells` → `OUT_OF_REGION` | B1, P6 | 2 | Un polígono en Saltillo da la misma celda que el CSV de DATA |

### C. Acceso a datos y perfil

| ID | Tarea | Depende | Horas | Hecho cuando |
|---|---|---|---|---|
| C1 | Protocolo `DataProvider` (`cell`, `profile_rows`, `indicators`, `year_rows`, `soil`, `sources`, `daily`) y `FixtureProvider` con datos sintéticos que siguen el contrato v0 de DATA (H8) | — | 1.5 | Los motores pueden probarse sin AWS |
| C2 | `AthenaProvider`: lee las 6 vistas a memoria al arrancar, recarga cuando cambia el parámetro SSM; `DATA_PROVIDER=fixture\|athena` por entorno | C1, A3, gold V0 (H15) | 2.5 | `dev` sirve datos reales de las 4 zonas |
| C3 | `app/profile`: gold → FieldProfile del contrato: heladas, lluvia, calor y viento por mes; `risk_calendar` de 36 decenas con decenas vulnerables y sus razones; suelo por profundidad; humedad y balance hídrico; NDVI y decenas descubiertas; `sources`; `gaps` (resolución de 9 km, clima compartido por N celdas, diferencia de elevación > 300 m, fuente de humedad usada, secciones sin dato) | C1, B1 | 3 | `GET /fields/{id}/profile` con fixtures cumple el esquema |
| C4 | Serie diaria por celda: desde `v_cell_daily` si DATA la publica; si no, adaptador de NASA POWER en vivo (el borrador del handoff, Anexo A) con caché en S3 por cuadro de 0.5° y la misma corrección por altura | C1, P3 | 2 | `provider.daily(cell_id)` devuelve la serie por cualquiera de las dos vías |

### D. Motores

| ID | Tarea | Depende | Horas | Hecho cuando |
|---|---|---|---|---|
| D1 | Catálogo `data/crops.yaml` + validación + `GET /crops`. Empezar con 5 cultivos de ejemplo y sustituir con lo de SCI | P5 (parcial) | 1 | El catálogo carga y valida |
| D2 | Aptitud (cultivo × mes de siembra): ventana sin heladas, calor en floración con el umbral `hot_days_*` más cercano a la temperatura crítica, agua (Kc × ET0 − lluvia efectiva vs riego disponible), pH y textura. Puntaje 0-100, estado, razones con `source_id`. Detalle y matriz | C1, D1 | 3 | Pruebas con fixtures; matriz completa en < 300 ms |
| D3 | Rotaciones: rotación actual + plantillas (leguminosa, cobertura en decenas descubiertas, tolerante a sequía, forraje si hay ganado) filtradas por aptitud y restricciones; simulación de 3-4 años (agua, balance de N, tendencia de materia orgánica, días de suelo descubierto, exposición a erosión, ruptura de plagas por familia); puntaje ponderado por prioridades; textos `why`, `evidence`, `benefits`, `gaps`, `risks_local_review` con plantillas es/en. Siempre ≥ 3 estrategias, incluida la actual | D2 | 5 | La demo de Saltillo devuelve 3 estrategias con evidencia citada |
| D4 | Escenarios: aplicar `delta_t_c` y `delta_p_pct` a la serie diaria y recalcular los indicadores con las mismas funciones que usa DATA en `gold_build`; alimentar aptitud y rotaciones. Prueba de paridad: con deltas en 0 el resultado coincide con gold | C4, D2, P6 | 3 | Respuesta con escenario en < 2 s |
| D5 | Pruebas de motor con series sintéticas (lista del handoff §12): lugar sin heladas, leguminosa sube el balance de N, misma familia en años seguidos penaliza | D2, D3 | 1.5 | En CI |

D3 es la tarea más larga y es el resultado central del reto: asignarle a la persona que más domine el dominio y empezarla en cuanto D2 tenga la firma de sus funciones, no cuando esté terminada.

### E. Chat agrónomo (extensión 1)

| ID | Tarea | Depende | Horas | Hecho cuando |
|---|---|---|---|---|
| E1 | Cliente de Bedrock con streaming y endpoint SSE (`status`, `tool`, `text`, `citation`, `card`, `done`, `error`). Verificar nombres del SDK y del modelo contra la documentación al implementar | P2, A5 | 2.5 | Un mensaje se transmite de punta a punta en `dev` |
| E2 | Herramientas que envuelven lo que ya existe: `list_user_fields`, `get_field_profile`, `get_risk_calendar`, `evaluate_crop`, `suitability_matrix`, `compare_rotations`, `list_crops` | E1, C3, D2, D3 | 2 | El modelo responde con cifras que salen de herramientas |
| E3 | Conversaciones en DynamoDB guardando el contenido completo de cada turno; `GET` del historial | E1, B3 | 1.5 | Recargar la página conserva el chat |
| E4 | Prompt de sistema (habla de zona, cita fuente y periodo, pide validación local) y revisión con 10 preguntas del agrónomo | E2 | 1.5 | Sin cifras inventadas en las 10 |
| E5 | Límite por `X-Client-Id` (mensajes por minuto y por día) y tope de tokens por respuesta | E1 | 1 | Un cliente no puede agotar el presupuesto |

### F. Extensión 2

| ID | Tarea | Depende | Horas |
|---|---|---|---|
| F1 | `GET /fields/{id}/greenhouse`: Gumbel sobre el máximo anual de viento de la serie diaria, niveles de retorno a 10/25/50 años y comparación con la resistencia declarada. Solo tiene sentido con la serie larga (C4) | C4 | 2.5 |
| F2 | `POST /fields/{id}/soil-report`: extracción con Claude y salida estructurada, validación por rangos, `soil.lab` en el perfil | E1 | 3 |

### G. Integración y demo

| ID | Tarea | Depende | Horas |
|---|---|---|---|
| G1 | Script de humo de punta a punta contra una URL: crear geocerca → perfil → aptitud → rotaciones → escenario. Se corre contra cada preview y contra `dev` | B1 | 1.5 |
| G2 | Dos demos sembradas y revisadas con SCI: rancho en Saltillo (heladas) y parcela en La Laguna (calor y agua) | C2, D3 | 1.5 |
| G3 | Tras cada publicación de DATA (V0, +SMAP, +NDVI): confirmar recarga y volver a correr G1 | C2 | 0.5 c/u |
| G4 | Congelación en H30: solo correcciones; `dev` es el entorno de la demo | todo | — |

---

## 6. Qué corre en paralelo

El detalle por tarea (qué necesita cada una para empezar y para terminar, oleadas, caminos críticos y archivos compartidos) está en [orden-tareas.md](orden-tareas.md).

Tres interfaces se fijan primero (antes de H9) y a partir de ahí los carriles no se estorban:

1. **Modelos del contrato** (B1) — de ellos dependen FE, el perfil, los motores y el chat.
2. **`DataProvider` + fixtures** (C1) — de él dependen el perfil y los motores; nadie espera a Athena ni a DATA.
3. **Esquema del catálogo de cultivos** (D1) — de él dependen los motores y SCI.

```
P1 ─► A2 ─► A3 ─► A4 ─► A5 ──────────────────────────► E1 ─► E2 ─► E4
A1 ───────────────┘                                     │
                                                         └─► E3, E5
P4 ─► B1 ─┬─► B2
          ├─► B3 ────────────────────────────────────► E3
          ├─► B4
          └─► G1
C1 ─┬─► C3 ──────────────────────────────────────────► E2
    ├─► C4 ─► D4, F1
    └─► D2 ─► D3 ─► D5, G2
C1 + A3 + gold V0 ─► C2 ─► G2, G3
```

| Carril | Tareas | Directorios (para no pisarse) |
|---|---|---|
| 1. Plataforma | A1-A6, luego E5 | `Dockerfile`, `infra/`, `.github/` |
| 2. API y estado | B1-B4, G1, luego E3 | `app/api/`, `app/store/`, `app/geo/`, `tests/api/` |
| 3. Datos y perfil | C1-C4, G3, luego F1 | `app/data/`, `app/profile/` |
| 4. Motores | D1-D5, G2 | `app/engines/`, `data/crops.yaml` |
| 5. Chat (cuando A5 y D2 existan) | E1, E2, E4, F2 | `app/agent/` |

Reparto para las **4 personas** del backend, una por carril; el chat y las extensiones se reparten cuando cada carril termina su parte del MVP:

| Persona | MVP | Después |
|---|---|---|
| 1. Plataforma | A1 → A2 → A3 + A4 → A5 → A6 | E1, E5, F2 |
| 2. API y estado | B1 → B2 → B3 → B4 → G1 | E3, E2 |
| 3. Datos y perfil | C1 → C3 → C4 → C2 (cuando haya gold V0) | G3, F1 |
| 4. Motores | D1 → D2 → D3 → D4 → D5 | G2, E4 |

La persona 1 necesita las credenciales de administrador para A2. La persona 4 tiene el camino más largo (D3 son 5 h): si la persona 2 o la 3 quedan libres antes, toman D4 o D5.

### Calendario

| Ventana | Qué pasa |
|---|---|
| **H6-H8** (sáb 15-17 h) | P1-P6. A1, B1, C1 y D1 arrancan a la vez. Al cierre: contrato fijo publicado para FE |
| **H8-H12** | A2 + A3 · B2 + B3 · C3 · D2. Llega el contrato v0 de DATA: ajustar fixtures |
| **H12-H15** | A4 + A5 (dev en ECS) · B4 + G1 · C4 · D3 empieza |
| **H15-H18** | Gold V0 publicado → C2. D3 sigue. E1 empieza si hay acceso a Bedrock |
| **H18-H24** | D3 termina, D4, D5. E2, E3, E5. G3 con SMAP. **MVP en `dev` en H24** |
| **H24-H30** | E4, G2 con SCI. F1 y F2 solo si el MVP está estable. G3 con NDVI |
| **H30-H32** | Congelación: solo correcciones; ensayo de la demo |

---

## 7. Riesgos

| Riesgo | Señal | Respuesta |
|---|---|---|
| ECS Express Mode falla o el proveedor de Terraform fijado no lo soporta | P1 o A3 no avanzan en 1 h | ECS Fargate + ALB clásico con la misma imagen (más Terraform: VPC por defecto, ALB, target group, servicio). Decidir antes de H9 |
| El bootstrap necesita credenciales de administrador y solo una persona las tiene | A2 detenida | Hacer A2 lo primero; las demás tareas siguen en local con fixtures |
| Gold V0 se retrasa más allá de H15 | Sin vistas en H17 | `dev` sirve fixtures + POWER en vivo (C4) con `confidence: low`; se cambia por configuración cuando llegue gold |
| DATA no puede publicar `v_cell_daily` | Respuesta negativa en P3 | C4 usa POWER en vivo; ~10-15 llamadas en total, con caché |
| D3 no termina | En H20 no hay 3 estrategias | Reducir a 2 plantillas (leguminosa y cobertura) y menos métricas; los textos explicativos no se recortan |
| Sin acceso a Bedrock | P2 sin respuesta en H18 | Se omite el chat; el MVP no depende de él |
| Demasiados previews simultáneos | CI lento | PR en borrador hasta que estén listos |
| Indicadores recalculados en escenarios no coinciden con gold | Falla la prueba de paridad de D4 | Usar exactamente el módulo de DATA; si no, mostrar el escenario como diferencia respecto a la línea base |

---

## 8. Preguntas abiertas

1. ~~¿Se acepta ECS Express Mode?~~ Confirmado: se usa ECS Express Mode.
2. ~~¿Lake y API en la misma cuenta?~~ Confirmado: misma cuenta. El lake de DATA y el workgroup `fieldshift` todavía no existen en us-west-2.
3. ~~¿Cuántas personas?~~ Confirmado: 4 personas en backend. Falta saber quién tiene credenciales de administrador durante el hackathon.
4. ¿Hora límite de entrega del proyecto? El calendario asume que coincide con la congelación de H32.
5. ¿El frontend ya tiene algo construido contra el contrato del handoff? El repo `nasa-farm-front` solo tiene el README, así que los cambios de §2 se asumen sin costo.
