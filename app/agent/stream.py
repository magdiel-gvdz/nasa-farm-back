"""Un mensaje del chat como flujo de eventos: modelo, herramientas, tarjetas, citas y final.

El bucle (modelo ↔ herramientas) corre en un hilo, porque el cliente de Bedrock es síncrono, y
pasa los eventos a la respuesta por una cola. Mientras tanto se envía un latido cada pocos
segundos. Si el cliente se desconecta se activa `cancel` y el bucle deja de generar.
"""

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.agent.client import ModelClient, ModelUnavailableError, TextDelta, TurnEnd
from app.agent.events import HEARTBEAT, sse
from app.agent.tools.registry import ToolContext, ToolRegistry
from app.i18n import translate
from app.store.conversations import ConversationStore, Exchange

logger = logging.getLogger(__name__)
MAX_TOOL_CALLS = 8
_END = object()


@dataclass
class TurnInputs:
    client: ModelClient
    store: ConversationStore
    registry: ToolRegistry
    tool_context: ToolContext
    system: list[dict]
    history: list[dict]
    user_message: dict
    exchange: Exchange
    conversation_id: str
    source_labels: dict[str, str]
    max_tokens: int
    heartbeat_seconds: float = 15.0
    max_tool_calls: int = MAX_TOOL_CALLS
    cancel: threading.Event = field(default_factory=threading.Event)


def _source_ids(node) -> set[str]:
    if isinstance(node, dict):
        found = set()
        for key, value in node.items():
            if key in {"source_id", "id"} and isinstance(value, str) and key == "source_id":
                found.add(value)
            found |= _source_ids(value)
        if "sources" in node and isinstance(node["sources"], list):
            found |= {
                item["id"] for item in node["sources"] if isinstance(item, dict) and "id" in item
            }
        return found
    if isinstance(node, list):
        return set().union(*(_source_ids(item) for item in node)) if node else set()
    return set()


def run_turn(inputs: TurnInputs, emit) -> None:
    """Bucle síncrono del mensaje. `emit(evento, datos)` envía cada evento del flujo."""
    language = inputs.tool_context.language
    messages = [*inputs.history, inputs.user_message]
    new_messages = [inputs.user_message]
    text_parts: list[str] = []
    cards: list[dict] = []
    sources: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    calls = 0
    exchange = inputs.exchange
    try:
        while True:
            end: TurnEnd | None = None
            for event in inputs.client.stream(
                system=inputs.system,
                messages=messages,
                tools=inputs.registry.specs(),
                max_tokens=inputs.max_tokens,
                cancel=inputs.cancel,
            ):
                if inputs.cancel.is_set():
                    break
                if isinstance(event, TextDelta):
                    text_parts.append(event.text)
                    emit("text", {"delta": event.text})
                else:
                    end = event
            if inputs.cancel.is_set():
                logger.info("Chat cancelado por desconexión del cliente")
                exchange.status = "failed"
                inputs.store.save(inputs.tool_context.client_id, inputs.conversation_id, exchange)
                return
            if end is None:
                raise ModelUnavailableError("el modelo cortó la respuesta")
            for key in usage:
                usage[key] += end.usage.get(key, 0)
            if end.refused:
                emit("error", {"code": "refused", "message": translate("chat.refused", language)})
                exchange.status = "failed"
                inputs.store.save(inputs.tool_context.client_id, inputs.conversation_id, exchange)
                return
            messages.append(end.message)
            new_messages.append(end.message)
            tool_calls = end.tool_calls
            if not tool_calls:
                break
            results = []
            for call in tool_calls:
                calls += 1
                if calls > inputs.max_tool_calls:
                    # Tope por mensaje: el modelo recibe el aviso y responde con lo que ya tiene.
                    results.append(
                        {
                            "toolResult": {
                                "toolUseId": call.id,
                                "status": "error",
                                "content": [
                                    {
                                        "json": {
                                            "error": "tool_limit_reached",
                                            "message": translate("chat.tool_limit", language),
                                        }
                                    }
                                ],
                            }
                        }
                    )
                    continue
                label = inputs.registry.label(call.name, language)
                emit("tool", {"name": call.name, "label": label, "state": "running"})
                outcome = inputs.registry.execute(inputs.tool_context, call.name, call.input)
                emit(
                    "tool",
                    {
                        "name": call.name,
                        "label": label,
                        "state": "done" if outcome.ok else "failed",
                    },
                )
                if outcome.card:
                    cards.append(outcome.card)
                    emit("card", outcome.card)
                if outcome.ok:
                    for source_id in sorted(_source_ids(outcome.result)):
                        if source_id not in sources:
                            sources.append(source_id)
                results.append(
                    {
                        "toolResult": {
                            "toolUseId": call.id,
                            "status": "success" if outcome.ok else "error",
                            "content": [
                                {
                                    "json": outcome.result
                                    if isinstance(outcome.result, dict)
                                    else {"items": outcome.result}
                                }
                            ],
                        }
                    }
                )
            tool_message = {"role": "user", "content": results}
            messages.append(tool_message)
            new_messages.append(tool_message)
            if calls > inputs.max_tool_calls + 2:
                raise ModelUnavailableError("el modelo no deja de pedir herramientas")
    except ModelUnavailableError as error:
        logger.error("Chat: modelo no disponible: %s", error)
        emit(
            "error",
            {"code": "llm_unavailable", "message": translate("chat.llm_unavailable", language)},
        )
        exchange.status = "failed"
        exchange.assistant_text = "".join(text_parts)
        inputs.store.save(inputs.tool_context.client_id, inputs.conversation_id, exchange)
        return
    except Exception:
        logger.exception("Chat: error interno")
        emit(
            "error",
            {"code": "internal_error", "message": translate("error.internal_error", language)},
        )
        exchange.status = "failed"
        inputs.store.save(inputs.tool_context.client_id, inputs.conversation_id, exchange)
        return
    citations = [
        {"source_id": source_id, "label": inputs.source_labels.get(source_id, source_id)}
        for source_id in sources
    ]
    for citation in citations:
        emit("citation", citation)
    exchange.status = "done"
    exchange.model = new_messages
    exchange.assistant_text = "".join(text_parts)
    exchange.cards = cards
    exchange.citations = citations
    inputs.store.save(inputs.tool_context.client_id, inputs.conversation_id, exchange)
    emit("done", {"message_id": exchange.message_id, "usage": usage})


async def event_stream(inputs: TurnInputs) -> AsyncIterator[str]:
    """Respuesta SSE: `status` primero, eventos del bucle según llegan y latidos entre medias."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(event: str, data: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, sse(event, data))

    def worker() -> None:
        try:
            run_turn(inputs, emit)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _END)

    language = inputs.tool_context.language
    yield sse("status", {"state": "thinking", "label": translate("chat.thinking", language)})
    thread = threading.Thread(target=worker, name="chat-turn", daemon=True)
    thread.start()
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=inputs.heartbeat_seconds)
            except TimeoutError:
                yield HEARTBEAT
                continue
            if item is _END:
                return
            yield item
    finally:
        # Desconexión o fin: el hilo deja de generar en cuanto vea la señal.
        inputs.cancel.set()
