"""Cliente del modelo de lenguaje: interfaz propia, implementación de Bedrock y otra simulada.

La API habla con Amazon Bedrock mediante la API Converse, común a todos sus modelos: el
modelo se elige con `BEDROCK_MODEL_ID` y se puede cambiar sin tocar el código. Las rutas y el
bucle del chat solo conocen esta interfaz; las pruebas usan `ScriptedClient`.
"""

import json
import logging
import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

# Motivos de parada de Converse que significan que el modelo o un filtro se negó a responder.
REFUSAL_STOP_REASONS = {"content_filtered", "guardrail_intervened"}


class ModelUnavailableError(Exception):
    """El modelo no respondió, devolvió un error o se cortó a mitad de respuesta."""


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass(frozen=True)
class TurnEnd:
    """Fin de una respuesta del modelo con el mensaje íntegro en formato Converse."""

    stop_reason: str
    message: dict
    usage: dict = field(default_factory=dict)

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [
            ToolCall(
                block["toolUse"]["toolUseId"], block["toolUse"]["name"], block["toolUse"]["input"]
            )
            for block in self.message["content"]
            if "toolUse" in block
        ]

    @property
    def refused(self) -> bool:
        return self.stop_reason in REFUSAL_STOP_REASONS


ModelEvent = TextDelta | TurnEnd


class ModelClient(Protocol):
    def stream(
        self,
        *,
        system: Sequence[dict],
        messages: Sequence[dict],
        tools: Sequence[dict],
        max_tokens: int,
        cancel: threading.Event,
    ) -> Iterator[ModelEvent]:
        """Fragmentos de texto según llegan y, al final, un `TurnEnd`."""
        ...


class BedrockConverseClient:
    """Modelo de Bedrock con `converse_stream`."""

    def __init__(self, model_id: str, region: str, *, temperature: float | None = 0.3):
        import boto3
        from botocore.config import Config

        self._model_id = model_id
        self._temperature = temperature
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(read_timeout=120, connect_timeout=10, retries={"max_attempts": 2}),
        )

    def stream(self, *, system, messages, tools, max_tokens, cancel) -> Iterator[ModelEvent]:
        from botocore.exceptions import BotoCoreError, ClientError

        request = {
            "modelId": self._model_id,
            "system": list(system),
            "messages": list(messages),
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        if self._temperature is not None:
            request["inferenceConfig"]["temperature"] = self._temperature
        if tools:
            request["toolConfig"] = {"tools": list(tools)}
        try:
            response = self._client.converse_stream(**request)
            blocks: dict[int, dict] = {}
            stop_reason, usage = "end_turn", {}
            for event in response["stream"]:
                if cancel.is_set():
                    response["stream"].close()
                    return
                if "contentBlockStart" in event:
                    start = event["contentBlockStart"]
                    tool = start.get("start", {}).get("toolUse")
                    if tool:
                        blocks[start["contentBlockIndex"]] = {
                            "toolUse": {
                                "toolUseId": tool["toolUseId"],
                                "name": tool["name"],
                                "input": "",
                            }
                        }
                elif "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]
                    index, part = delta["contentBlockIndex"], delta["delta"]
                    if "text" in part:
                        blocks.setdefault(index, {"text": ""})["text"] += part["text"]
                        yield TextDelta(part["text"])
                    elif "toolUse" in part:
                        blocks[index]["toolUse"]["input"] += part["toolUse"].get("input", "")
                    elif "reasoningContent" in part:
                        reasoning = blocks.setdefault(
                            index, {"reasoningContent": {"reasoningText": {"text": ""}}}
                        )["reasoningContent"]["reasoningText"]
                        reasoning["text"] += part["reasoningContent"].get("text", "")
                        if "signature" in part["reasoningContent"]:
                            reasoning["signature"] = part["reasoningContent"]["signature"]
                elif "messageStop" in event:
                    stop_reason = event["messageStop"].get("stopReason", "end_turn")
                elif "metadata" in event:
                    usage = event["metadata"].get("usage", {})
        except (BotoCoreError, ClientError) as error:
            logger.error("Bedrock %s no respondió: %s", self._model_id, error)
            raise ModelUnavailableError(str(error)) from error
        content = []
        for index in sorted(blocks):
            block = blocks[index]
            if "toolUse" in block:
                raw = block["toolUse"]["input"] or "{}"
                try:
                    block["toolUse"]["input"] = json.loads(raw)
                except ValueError:
                    # Entrada mal formada: la herramienta la rechazará y el modelo podrá corregirse.
                    block["toolUse"]["input"] = {"_invalid_json": raw}
            if "text" in block and not block["text"]:
                continue
            content.append(block)
        if not content:
            content = [{"text": ""}]
        yield TurnEnd(
            stop_reason=stop_reason,
            message={"role": "assistant", "content": content},
            usage={
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
            },
        )


class ScriptedClient:
    """Cliente simulado: cada llamada reproduce el siguiente turno del guion.

    Un turno es una lista de cadenas (fragmentos de texto) y `ToolCall`, o una excepción que
    se lanza tras los fragmentos anteriores. Guarda lo que recibe cada llamada.
    """

    def __init__(self, *turns, delay: float = 0.0):
        self.turns = list(turns)
        self.calls: list[dict] = []
        self.delay = delay

    def stream(self, *, system, messages, tools, max_tokens, cancel) -> Iterator[ModelEvent]:
        import copy
        import time

        self.calls.append(
            {
                "system": copy.deepcopy(list(system)),
                "messages": copy.deepcopy(list(messages)),
                "tools": [tool["toolSpec"]["name"] for tool in tools],
                "max_tokens": max_tokens,
            }
        )
        turn = self.turns.pop(0) if self.turns else ["(sin guion)"]
        content, stop_reason = [], "end_turn"
        for step in turn:
            if self.delay:
                time.sleep(self.delay)
            if cancel.is_set():
                return
            if isinstance(step, Exception):
                raise step
            if isinstance(step, ToolCall):
                content.append(
                    {"toolUse": {"toolUseId": step.id, "name": step.name, "input": step.input}}
                )
                stop_reason = "tool_use"
            elif step == "<refuse>":
                stop_reason = "content_filtered"
            else:
                if content and "text" in content[-1]:
                    content[-1]["text"] += step
                else:
                    content.append({"text": step})
                yield TextDelta(step)
        yield TurnEnd(
            stop_reason=stop_reason,
            message={"role": "assistant", "content": content or [{"text": ""}]},
            usage={"input_tokens": 10, "output_tokens": 5},
        )
