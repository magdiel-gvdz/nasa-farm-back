# Tasks

## 1. Extracción

- [x] 1.1 Consultar en la documentación vigente de Bedrock cómo enviar un PDF y una imagen al modelo con la API Converse y cómo pedir salida con esquema JSON (herramienta forzada), y anotarlo en el PR; verificar con una llamada mínima con un análisis de ejemplo
  - API Converse de Bedrock: el PDF va como bloque `document` (`format: pdf`) y la imagen como bloque `image` (`png`/`jpeg`); la salida estructurada se obtiene forzando una herramienta con el esquema (`toolChoice.tool`). Modelo `amazon.nova-pro-v1:0` (Qwen3 Next no admite documentos). Llamada mínima con un análisis de ejemplo en PDF: los 11 campos leídos correctamente en 4.2 s; una factura se reconoció como `is_soil_report=false`
- [x] 1.2 Implementar en `app/agent/extract.py` la llamada con el documento y el esquema de `extracted`, más la señal de "no es un análisis de suelo", detrás de la interfaz del cliente del modelo; verificar con el cliente simulado
- [x] 1.3 Implementar la normalización de unidades y la validación por rangos (pH 3-11, materia orgánica 0-20 %, CE 0-20 dS/m, CIC 0-100 cmol/kg, N, P y K no negativos con máximos amplios); verificar con pruebas de pH 81 y de valores en el límite

## 2. Endpoint y almacenamiento

- [x] 2.1 Implementar `POST /fields/{id}/soil-report` (multipart) con comprobación de tipo real del archivo y de tamaño, y los errores `unsupported_file_type`, de tamaño, `not_a_soil_report` y `chat_disabled`; verificar con pruebas de API de cada caso
- [x] 2.2 Guardar el archivo en `uploads/<client_id>/<field_id>/` del bucket del entorno (directorio local sin bucket) y los valores aceptados en la geocerca; verificar con una prueba que el objeto existe y que otro cliente recibe `404`

## 3. Efecto en perfil y aptitud

- [x] 3.1 Mostrar `soil.lab`, confianza alta, fuente `lab_report` y retirar el vacío de laboratorio en el perfil, invalidando su caché para esa geocerca; verificar con una prueba de perfil antes y después
- [x] 3.2 Usar el pH de laboratorio en el factor suelo con su texto es/en; verificar con la prueba de 7.9 frente a 6.8
- [x] 3.3 Regenerar `contracts/openapi.json` y documentar el endpoint en `docs/api-contract.md`, incluida la advertencia de no subir documentos con datos personales; verificar que la comprobación del contrato pasa
- [ ] 3.4 En un preview, subir un análisis real en PDF y otro en foto y verificar a mano los valores extraídos contra el documento; anotar las discrepancias en el PR
