# Tasks

## 1. Instrucciones

- [ ] 1.1 Escribir `app/agent/prompts/system.md` con el papel del asistente, las reglas de cifras, lenguaje zonal, remisión local, idioma, ámbito y uso de herramientas, explicando el porqué de cada regla; verificar que se carga al arrancar y que una prueba detecta el archivo vacío o ausente
- [ ] 1.2 Implementar `app/agent/context.py` que añade al final del contexto la geocerca activa (nombre, zona, cultivo actual), la fecha y el idioma, dejando estables las instrucciones y las herramientas para aprovechar la caché del modelo; verificar con una prueba que dos mensajes con distinta geocerca comparten el mismo prefijo

## 2. Evaluación

- [ ] 2.1 Escribir `evals/chat/questions.yaml` con 10 preguntas del agrónomo (siembra de avena, helada tardía, calor en floración, rotación con menos agua, escenario de −20 % de lluvia, fósforo, granizo, pregunta en inglés, sin geocerca activa, tema ajeno) y, por cada una, herramientas esperadas y comprobaciones; verificar que el archivo valida contra su esquema
- [ ] 2.2 Implementar `scripts/run_chat_eval.py` que envía cada pregunta a una URL, recoge eventos y aplica comprobaciones automáticas (herramienta esperada usada, al menos una cita cuando hay cifras, idioma, ausencia de expresiones de parcela); verificar ejecutándolo contra un preview y guardando el informe
- [ ] 2.3 Revisar a mano las 10 respuestas con SCI buscando cifras sin respaldo en los resultados de herramientas, y ajustar las instrucciones hasta que no haya ninguna; verificar con el informe final adjunto al PR

## 3. Documentación

- [ ] 3.1 Escribir `docs/chat-eval.md` con cómo ejecutar la evaluación y cómo interpretar el informe; verificar que el comando documentado funciona tal como está escrito
