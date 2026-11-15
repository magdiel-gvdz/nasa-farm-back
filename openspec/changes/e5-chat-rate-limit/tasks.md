# Tasks

## 1. Límites

- [x] 1.1 Implementar en `app/agent/limits.py` el contador por minuto en memoria por `client_id` y el contador diario por cliente en la tabla del entorno (incremento atómico, caducidad al día siguiente), con valores por defecto de 6 por minuto y 80 por día; verificar con pruebas de ráfaga, de límite diario y de independencia entre clientes
- [x] 1.2 Implementar el presupuesto diario global con un contador atómico en la tabla y valor por defecto de 1,500 mensajes; verificar con una prueba de presupuesto agotado y otra de dos instancias simuladas compartiendo contador
- [x] 1.3 Añadir la validación de 2,000 caracteres y pasar `CHAT_MAX_OUTPUT_TOKENS` al cliente del modelo; verificar con pruebas de mensaje largo y de que el cliente simulado recibe el tope

## 2. Integración

- [x] 2.1 Aplicar los límites en `POST /chat/conversations/{id}/messages` antes de abrir el flujo, con `429` y `Retry-After`, y `503` para el presupuesto; verificar con pruebas de API y de que el perfil sigue respondiendo para un cliente limitado
- [ ] 2.2 Añadir las cuatro variables a `infra/environment` con valores más bajos en previews, y al `README.md`; verificar con `terraform test` y con una ráfaga real contra un preview que el séptimo mensaje del minuto recibe `429`
- [ ] 2.3 Registrar cada rechazo con cliente abreviado y motivo, y el total diario al procesar cada mensaje; verificar en los registros del preview
