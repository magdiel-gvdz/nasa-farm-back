"""Chat con el asistente agrónomo: conversaciones, historial y mensajes en streaming (SSE)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import Field as F

from app.agent.context import system_blocks, user_message
from app.agent.limits import LimitExceeded
from app.agent.stream import TurnInputs, event_stream
from app.agent.tools.registry import ToolContext
from app.api.deps import ClientId, Crops, Data, Engine, Language, Profiles, Repo, Scenarios
from app.api.errors import ApiError
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse, RequestModel, ResponseModel
from app.data import DataUnavailableError
from app.store.conversations import ConversationFullError, ConversationStore

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


class ConversationCreate(RequestModel):
    field_id: str | None = F(default=None, description="Geocerca activa de la conversación")


class Conversation(ResponseModel):
    conversation_id: str
    field_id: str | None
    created_at: str


class MessageCreate(RequestModel):
    text: str = F(min_length=1, description="Hasta 2,000 caracteres")
    field_id: str | None = F(
        default=None, description="Cambia la geocerca activa para este mensaje"
    )


class VisibleMessage(ResponseModel):
    role: str
    text: str
    cards: list[dict] = []
    citations: list[dict] = []
    status: str | None = None
    message_id: str | None = None
    created_at: str


class ConversationHistory(Conversation):
    messages: list[VisibleMessage]


def chat(request: Request):
    """Servicios del chat; `chat_disabled` si está apagado por configuración."""
    services = request.app.state.chat
    if services is None:
        raise ApiError("chat_disabled", 503)
    return services


Chat = Annotated[object, Depends(chat)]


def _conversation(services, client_id: str, conversation_id: str) -> dict:
    conversation = services.store.get(client_id, conversation_id)
    if conversation is None:
        raise ApiError("not_found", 404, details={"conversation_id": conversation_id[:64]})
    return conversation


@router.post(
    "/conversations",
    status_code=201,
    response_model=Conversation,
    summary="Crear una conversación, opcionalmente ligada a una geocerca",
)
def create_conversation(body: ConversationCreate, client_id: ClientId, repo: Repo, services: Chat):
    if body.field_id is not None:
        load_field(repo, client_id, body.field_id)
    return services.store.create(client_id, body.field_id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistory,
    summary="Historial visible de una conversación",
)
def get_conversation(conversation_id: str, client_id: ClientId, services: Chat):
    conversation = _conversation(services, client_id, conversation_id)
    messages = []
    for exchange in services.store.exchanges(client_id, conversation_id):
        messages.append(
            {"role": "user", "text": exchange.user_text, "created_at": exchange.created_at}
        )
        if exchange.status != "pending" or exchange.assistant_text:
            messages.append(
                {
                    "role": "assistant",
                    "text": exchange.assistant_text,
                    "cards": exchange.cards or [],
                    "citations": exchange.citations or [],
                    "status": exchange.status,
                    "message_id": exchange.message_id,
                    "created_at": exchange.created_at,
                }
            )
    return {**conversation, "messages": messages}


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Enviar un mensaje; la respuesta llega como flujo de eventos (SSE)",
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "Eventos `status`, `tool`, `text`, `card`, `citation` y un `done` o `error` final"
            ),
        },
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def send_message(
    conversation_id: str,
    body: MessageCreate,
    client_id: ClientId,
    language: Language,
    repo: Repo,
    data: Data,
    catalog: Crops,
    engine: Engine,
    profiles: Profiles,
    scenarios: Scenarios,
    services: Chat,
):
    limits = services.limits
    if len(body.text) > limits.max_message_chars:
        raise ApiError("message_too_long", 422, params={"max_chars": limits.max_message_chars})
    conversation = _conversation(services, client_id, conversation_id)
    field_id = body.field_id or conversation.get("field_id")
    field = load_field(repo, client_id, field_id) if field_id else None
    if conversation["user_messages"] >= services.store_limit:
        raise ApiError("conversation_full", 409)
    try:
        services.rate_limiter.check(client_id)
    except LimitExceeded as error:
        raise ApiError(
            error.code,
            error.status_code,
            details={"reason": error.reason, "retry_after": error.retry_after},
            headers={"Retry-After": str(error.retry_after)},
        ) from None
    try:
        exchange = services.store.start_exchange(client_id, conversation, body.text)
    except ConversationFullError:
        raise ApiError("conversation_full", 409) from None
    try:
        source_labels = {
            source.source_id: f"{source.name} ({source.period})" for source in data.sources()
        }
    except DataUnavailableError:
        source_labels = {}
    inputs = TurnInputs(
        client=services.client,
        store=services.store,
        registry=services.registry,
        tool_context=ToolContext(
            client_id=client_id,
            language=language,
            repo=repo,
            data=data,
            catalog=catalog,
            engine=engine,
            profiles=profiles,
            scenarios=scenarios,
            active_field_id=field["id"] if field else None,
        ),
        system=system_blocks(),
        history=services.store.model_history(client_id, conversation_id),
        user_message=user_message(body.text, field, language),
        exchange=exchange,
        conversation_id=conversation_id,
        source_labels=source_labels,
        max_tokens=limits.max_output_tokens,
        heartbeat_seconds=services.heartbeat_seconds,
    )
    return StreamingResponse(
        event_stream(inputs),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ChatServices:
    """Lo que el chat necesita en cada petición; se crea al arrancar si el chat está activo."""

    def __init__(
        self, *, client, store: ConversationStore, registry, rate_limiter, limits, heartbeat_seconds
    ):
        from app.store.conversations import MAX_USER_MESSAGES

        self.client = client
        self.store = store
        self.registry = registry
        self.rate_limiter = rate_limiter
        self.limits = limits
        self.heartbeat_seconds = heartbeat_seconds
        self.store_limit = MAX_USER_MESSAGES
