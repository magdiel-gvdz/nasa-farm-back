# Evaluación del asistente agrónomo

`evals/chat/questions.yaml` tiene 10 preguntas de un agrónomo (siembra de avena, helada tardía,
calor en floración, rotación con menos agua, escenario de −20 % de lluvia, fósforo, granizo, una en
inglés, sin geocerca activa y un tema ajeno). Cada una indica qué herramientas debe usar el
asistente y qué comprobaciones automáticas debe pasar su respuesta.

## Ejecutar

Contra un entorno con `CHAT_ENABLED=true` (un preview o `dev`):

```powershell
.\.venv\Scripts\python.exe scripts/run_chat_eval.py --base-url https://<url-del-entorno>
```

El script siembra las geocercas de demostración (`demo/fields.json`), envía cada pregunta en una
conversación nueva y escribe `build/chat-eval/report.json` y `build/chat-eval/report.md`. Termina
con código 0 solo si todas las preguntas pasan todas sus comprobaciones. Cada ejecución cuenta 10
mensajes contra los límites del chat del cliente de la demo (80 al día).

## Comprobaciones

| Comprobación | Pasa si |
|---|---|
| `finished` | El flujo termina con `done` |
| `expected_tools` | Se usó al menos una de las herramientas esperadas (o ninguna, si la lista está vacía) |
| `citation_when_numbers` | Si la respuesta tiene cifras, el flujo cita al menos una fuente |
| `language` | La respuesta está en el idioma de la pregunta |
| `zonal_language` | La respuesta no afirma valores de la parcela ("tu parcela tiene…") |
| `no_numbers` | La respuesta no da cantidades (el sistema no tiene ese dato) |
| `mentions` | La respuesta menciona alguno de los textos esperados |
| `local_review` | La respuesta remite a un agrónomo o productor local |

## Cómo leer el informe

`report.md` muestra, por pregunta, las comprobaciones que fallan, las herramientas usadas, las
fuentes citadas, el tiempo y la respuesta completa. Las comprobaciones automáticas no detectan una
cifra inventada que además cite una fuente: por eso cada respuesta se revisa también a mano,
comparando sus cifras con los resultados de las herramientas. Si hay alguna sin respaldo, se ajustan
las instrucciones (`app/agent/prompts/system.md`) y se repite la evaluación.
