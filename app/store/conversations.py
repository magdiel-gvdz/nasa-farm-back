"""Conversaciones del chat sobre el repositorio de la tabla del entorno.

- `conv#<id>`: la conversación (geocerca, fecha, número de mensajes del usuario).
- `msg#<id>#<nnnn>`: cada intercambio. Guarda el contenido íntegro en formato Converse
  (`model`: mensaje del usuario, turnos del asistente con usos de herramientas, resultados y
  razonamiento) y la vista visible (`visible`: texto, tarjetas, citas, estado).

Un intercambio fallido o interrumpido se guarda marcado y no se reenvía al modelo, así que
nunca deja un turno incompleto que impida continuar.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from app.store.base import Repository

CONVERSATION_PREFIX = "conv#"
MESSAGE_PREFIX = "msg#"
MAX_USER_MESSAGES = 40


class ConversationFullError(Exception):
    pass


def new_conversation_id() -> str:
    return "conv_" + secrets.token_hex(10)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Exchange:
    """Un mensaje del usuario y la respuesta del asistente."""

    number: int
    user_text: str
    status: str  # pending | done | failed
    model: list[dict]
    assistant_text: str = ""
    cards: list[dict] | None = None
    citations: list[dict] | None = None
    created_at: str = ""
    message_id: str = ""

    def to_document(self) -> dict:
        return {
            "number": self.number,
            "user_text": self.user_text,
            "status": self.status,
            "model": self.model,
            "assistant_text": self.assistant_text,
            "cards": self.cards or [],
            "citations": self.citations or [],
            "created_at": self.created_at,
            "message_id": self.message_id,
        }


class ConversationStore:
    def __init__(self, repo: Repository):
        self._repo = repo

    def create(self, client_id: str, field_id: str | None) -> dict:
        conversation = {
            "conversation_id": new_conversation_id(),
            "field_id": field_id,
            "created_at": _now(),
            "user_messages": 0,
        }
        self._repo.put(
            client_id, CONVERSATION_PREFIX + conversation["conversation_id"], conversation
        )
        return conversation

    def get(self, client_id: str, conversation_id: str) -> dict | None:
        if not conversation_id.startswith("conv_") or len(conversation_id) > 40:
            return None
        return self._repo.get(client_id, CONVERSATION_PREFIX + conversation_id)

    def exchanges(self, client_id: str, conversation_id: str) -> list[Exchange]:
        documents = self._repo.list_prefix(client_id, f"{MESSAGE_PREFIX}{conversation_id}#")
        return [Exchange(**document) for document in documents]

    def model_history(self, client_id: str, conversation_id: str) -> list[dict]:
        """Mensajes para el modelo, íntegros y en orden; sin los intercambios fallidos."""
        history = []
        for exchange in self.exchanges(client_id, conversation_id):
            if exchange.status == "done":
                history.extend(exchange.model)
        return history

    def start_exchange(self, client_id: str, conversation: dict, user_text: str) -> Exchange:
        if conversation["user_messages"] >= MAX_USER_MESSAGES:
            raise ConversationFullError
        conversation["user_messages"] += 1
        self._repo.put(
            client_id, CONVERSATION_PREFIX + conversation["conversation_id"], conversation
        )
        exchange = Exchange(
            number=conversation["user_messages"],
            user_text=user_text,
            status="pending",
            model=[],
            created_at=_now(),
            message_id=f"msg_{secrets.token_hex(8)}",
        )
        self.save(client_id, conversation["conversation_id"], exchange)
        return exchange

    def save(self, client_id: str, conversation_id: str, exchange: Exchange) -> None:
        self._repo.put(
            client_id,
            f"{MESSAGE_PREFIX}{conversation_id}#{exchange.number:04d}",
            exchange.to_document(),
        )
