# Tasks

## 1. Almacenamiento

- [x] 1.1 Implementar `app/store/conversations.py` sobre el repositorio existente: conversación en `conv#<id>` (geocerca, fecha, contador) y turnos en `msg#<id>#<n>` con el contenido íntegro serializado y la vista visible (texto, tarjetas, citas, estado); verificar con pruebas en memoria y en DynamoDB simulado
- [x] 1.2 Sustituir la conversación en memoria de `e1` por este almacén mediante la misma interfaz; verificar que las pruebas de `e1` siguen pasando

## 2. Uso en el flujo

- [x] 2.1 Cargar el historial íntegro al recibir un mensaje y reenviarlo al modelo sin modificar; verificar con el cliente simulado que recibe los turnos anteriores byte a byte
- [x] 2.2 Guardar el mensaje del usuario al recibirlo y el turno del asistente solo al emitir `done`; en error o desconexión, guardar una marca de respuesta fallida que no se reenvía al modelo; verificar con pruebas de fallo y de mensaje posterior
- [x] 2.3 Implementar el tope de 40 mensajes y `conversation_full`; verificar con una prueba

## 3. Endpoint e integración

- [x] 3.1 Implementar `GET /chat/conversations/{id}` con la vista visible y el aislamiento por cliente; verificar con pruebas de historial ordenado, de ausencia de bloques de razonamiento y de `404` para otro cliente
- [x] 3.2 Actualizar `contracts/openapi.json` y `docs/api-contract.md`; verificar que la comprobación del contrato pasa
- [ ] 3.3 En un preview, mantener una conversación de dos turnos con una pregunta de seguimiento, forzar un redespliegue entre ambos y verificar que el asistente conserva el contexto
