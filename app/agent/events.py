"""Eventos del flujo del chat y su serialización como Server-Sent Events.

Cada evento es `event: <tipo>` y `data: <JSON en una línea>`. Los latidos son comentarios SSE
(`: ping`), que el navegador ignora y que evitan que el balanceador corte la conexión.
"""

import json

EVENT_TYPES = ("status", "tool", "text", "citation", "card", "done", "error")
HEARTBEAT = ": ping\n\n"


def sse(event: str, data: dict) -> str:
    if event not in EVENT_TYPES:
        raise ValueError(f"Evento desconocido: {event}")
    return (
        f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """Eventos de un cuerpo SSE completo, sin los latidos. Útil en pruebas y en la evaluación."""
    events = []
    for chunk in body.split("\n\n"):
        lines = [line for line in chunk.split("\n") if line and not line.startswith(":")]
        if not lines:
            continue
        name = next(line[7:] for line in lines if line.startswith("event: "))
        data = next(line[6:] for line in lines if line.startswith("data: "))
        events.append((name, json.loads(data)))
    return events
