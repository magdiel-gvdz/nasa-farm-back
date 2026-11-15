import asyncio
import copy
import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.agent import context as chat_context
from app.agent.client import ModelUnavailableError, ScriptedClient, ToolCall
from app.agent.events import HEARTBEAT, parse_sse, sse
from app.agent.limits import ChatLimits, LimitExceeded, RateLimiter
from app.agent.stream import MAX_TOOL_CALLS, TurnInputs, event_stream
from app.agent.tools.definitions import build_registry
from app.agent.tools.registry import ToolContext, fit, validate
from app.api.schemas.rotations import RotationResponse
from app.api.schemas.suitability import SuitabilityDetail
from app.config import Settings
from app.main import create_app
from app.store.base import MemoryRepository
from app.store.conversations import MAX_USER_MESSAGES, ConversationStore, Exchange
from tests.helpers import MAIZE_FALLOW, field_payload

CHAT = "/api/v1/chat/conversations"


def chat_app(model, **settings):
    values = {
        "environment": "pr-42",
        "app_table": "",
        "cors_origins": ["http://localhost:5173"],
        "chat_enabled": True,
        "bedrock_model_id": "qwen.qwen3-next-80b-a3b",
        "chat_heartbeat_seconds": 5,
        **settings,
    }
    return TestClient(create_app(Settings(**values), model_client=model))


@pytest.fixture
def headers():
    return {"X-Client-Id": str(uuid.uuid4())}


def new_field(client, headers, **overrides):
    payload = field_payload(current_rotation=MAIZE_FALLOW, **overrides)
    return client.post("/api/v1/fields", json=payload, headers=headers).json()


def conversation(client, headers, field_id=None):
    response = client.post(CHAT, json={"field_id": field_id} if field_id else {}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["conversation_id"]


def send(client, headers, conversation_id, text="¿Puedo sembrar maíz en abril?", **extra):
    response = client.post(
        f"{CHAT}/{conversation_id}/messages", json={"text": text, **extra}, headers=headers
    )
    return response, parse_sse(response.text) if response.status_code == 200 else None


def names(events):
    return [name for name, _ in events]


# ---------------------------------------------------------------- eventos SSE


def test_sse_lines_are_named_and_one_line_json():
    assert (
        sse("text", {"delta": "Hola\nmundo"}) == 'event: text\ndata: {"delta":"Hola\\nmundo"}\n\n'
    )
    with pytest.raises(ValueError):
        sse("unknown", {})
    assert parse_sse(sse("status", {"state": "thinking"}) + HEARTBEAT + sse("done", {})) == [
        ("status", {"state": "thinking"}),
        ("done", {}),
    ]


# ---------------------------------------------------------------- conversación y flujo


def test_text_reply_streams_status_text_and_done(headers):
    model = ScriptedClient(["Sí, ", "en abril."])
    client = chat_app(model)
    response, events = send(client, headers, conversation(client, headers))
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert names(events) == ["status", "text", "text", "done"]
    assert "".join(data["delta"] for name, data in events if name == "text") == "Sí, en abril."
    done = events[-1][1]
    assert done["message_id"].startswith("msg_") and done["usage"]["output_tokens"] == 5


def test_conversation_linked_to_a_field_and_foreign_field(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    assert conversation(client, headers, field["id"]).startswith("conv_")
    other = {"X-Client-Id": str(uuid.uuid4())}
    response = client.post(CHAT, json={"field_id": field["id"]}, headers=other)
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_message_to_a_missing_or_foreign_conversation_is_json_404(headers):
    client = chat_app(ScriptedClient())
    conversation_id = conversation(client, headers)
    other = {"X-Client-Id": str(uuid.uuid4())}
    for who, target in ((headers, "conv_doesnotexist"), (other, conversation_id)):
        response, _ = send(client, who, target)
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["error"]["code"] == "not_found"


def test_disabled_chat_answers_503_and_the_rest_works(client, headers):
    response = client.post(CHAT, json={}, headers=headers)
    assert response.status_code == 503 and response.json()["error"]["code"] == "chat_disabled"
    assert client.get("/api/v1/crops").status_code == 200


def test_enabled_chat_without_a_model_does_not_start():
    with pytest.raises(ValueError, match="BEDROCK_MODEL_ID"):
        create_app(Settings(chat_enabled=True, bedrock_model_id=""))


def test_model_failure_after_text_ends_with_llm_unavailable(headers):
    client = chat_app(ScriptedClient(["Empiezo ", ModelUnavailableError("timeout")]))
    _, events = send(client, headers, conversation(client, headers))
    assert names(events) == ["status", "text", "error"]
    assert events[-1][1]["code"] == "llm_unavailable" and events[-1][1]["message"]


def test_refusal_ends_with_refused(headers):
    client = chat_app(ScriptedClient(["<refuse>"]))
    _, events = send(client, headers, conversation(client, headers))
    assert names(events)[-1] == "error" and events[-1][1]["code"] == "refused"
    assert "done" not in names(events)


def test_slow_model_gets_heartbeats(headers):
    client = chat_app(ScriptedClient(["a", "b", "c"], delay=0.3), chat_heartbeat_seconds=0.1)
    response, events = send(client, headers, conversation(client, headers))
    assert response.text.count(HEARTBEAT) >= 2
    assert names(events)[-1] == "done"


def test_disconnecting_cancels_the_generation():
    store = ConversationStore(MemoryRepository())
    conversation_data = store.create("c", None)
    exchange = store.start_exchange("c", conversation_data, "hola")
    model = ScriptedClient(["a"] * 50, delay=0.05)
    inputs = TurnInputs(
        client=model,
        store=store,
        registry=build_registry(["maiz"]),
        tool_context=ToolContext("c", "es", None, None, None, None, None, None),
        system=[{"text": "x"}],
        history=[],
        user_message={"role": "user", "content": [{"text": "hola"}]},
        exchange=exchange,
        conversation_id=conversation_data["conversation_id"],
        source_labels={},
        max_tokens=100,
    )

    async def consume_two():
        stream = event_stream(inputs)
        await stream.__anext__()
        await stream.__anext__()
        await stream.aclose()

    asyncio.run(consume_two())
    assert inputs.cancel.is_set()
    time.sleep(0.3)
    saved = store.exchanges("c", conversation_data["conversation_id"])[0]
    assert saved.status == "failed" and saved.model == []


# ---------------------------------------------------------------- herramientas


def tool_turns(*calls, final="Listo."):
    return [*[[call] for call in calls], [final]]


def test_tool_call_emits_tool_card_citation_and_matches_the_endpoint(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    model = ScriptedClient(
        [ToolCall("t1", "evaluate_crop", {"crop_id": "maiz", "planting_month": 4})],
        ["Con un puntaje de ", "60, es marginal."],
    )
    client.app.state.chat.client = model
    _, events = send(client, headers, conversation(client, headers, field["id"]))
    assert names(events) == [
        "status",
        "tool",
        "tool",
        "card",
        "text",
        "text",
        "citation",
        "citation",
        "done",
    ]
    tool_events = [data for name, data in events if name == "tool"]
    assert [event["state"] for event in tool_events] == ["running", "done"]
    assert tool_events[0]["label"] == "Evaluando el cultivo"
    card = next(data for name, data in events if name == "card")
    assert card["type"] == "suitability"
    SuitabilityDetail.model_validate(card["payload"])
    endpoint = client.get(
        f"/api/v1/fields/{field['id']}/suitability",
        params={"crop_id": "maiz", "planting_month": 4},
        headers=headers,
    ).json()
    assert card["payload"] == endpoint
    citations = [data for name, data in events if name == "citation"]
    assert {citation["source_id"] for citation in citations} == {"nasa_power", "soilgrids"}
    assert all(citation["label"] for citation in citations)
    tool_result = model.calls[1]["messages"][-1]["content"][0]["toolResult"]
    assert tool_result["status"] == "success" and tool_result["toolUseId"] == "t1"


def test_rotations_card_follows_the_schema(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    client.app.state.chat.client = ScriptedClient(
        *tool_turns(ToolCall("t1", "compare_rotations", {}))
    )
    _, events = send(client, headers, conversation(client, headers, field["id"]))
    card = next(data for name, data in events if name == "card")
    assert card["type"] == "rotations"
    RotationResponse.model_validate(card["payload"])


def test_tools_never_read_another_clients_field(headers):
    client = chat_app(ScriptedClient())
    foreign = new_field(client, {"X-Client-Id": str(uuid.uuid4())})
    model = ScriptedClient(
        *tool_turns(ToolCall("t1", "get_field_profile", {"field_id": foreign["id"]}))
    )
    client.app.state.chat.client = model
    _, events = send(client, headers, conversation(client, headers))
    assert [data["state"] for name, data in events if name == "tool"] == ["running", "failed"]
    result = model.calls[1]["messages"][-1]["content"][0]["toolResult"]
    assert result["status"] == "error" and result["content"][0]["json"]["error"] == "not_found"
    assert foreign["name"] not in str(result)
    assert names(events)[-1] == "done"


def test_unknown_crop_fails_the_tool_but_not_the_reply(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    model = ScriptedClient(
        *tool_turns(ToolCall("t1", "evaluate_crop", {"crop_id": "kiwi", "planting_month": 4}))
    )
    client.app.state.chat.client = model
    _, events = send(client, headers, conversation(client, headers, field["id"]))
    assert [data["state"] for name, data in events if name == "tool"] == ["running", "failed"]
    assert names(events)[-1] == "done"
    result = model.calls[1]["messages"][-1]["content"][0]["toolResult"]["content"][0]["json"]
    assert result["error"] == "invalid_arguments" and "crop_id" in result["message"]


def test_tool_calls_are_capped_per_message(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    calls = [ToolCall(f"t{n}", "list_crops", {}) for n in range(MAX_TOOL_CALLS + 2)]
    model = ScriptedClient(calls, ["Con lo obtenido: ..."])
    client.app.state.chat.client = model
    _, events = send(client, headers, conversation(client, headers, field["id"]))
    assert [data["state"] for name, data in events if name == "tool"].count(
        "running"
    ) == MAX_TOOL_CALLS
    results = model.calls[1]["messages"][-1]["content"]
    assert [item["toolResult"]["status"] for item in results][-2:] == ["error", "error"]
    assert names(events)[-1] == "done"


def test_tool_specs_are_valid_and_inputs_are_validated():
    registry = build_registry(["maiz", "frijol"])
    for spec in registry.specs():
        schema = spec["toolSpec"]["inputSchema"]["json"]
        assert spec["toolSpec"]["name"] and spec["toolSpec"]["description"]
        assert schema["type"] == "object" and set(schema["required"]) <= set(schema["properties"])
    schema = registry.get("evaluate_crop").schema
    assert validate(schema, {"crop_id": "maiz", "planting_month": 4.0}) == {
        "crop_id": "maiz",
        "planting_month": 4,
    }
    for bad in (
        {"crop_id": "maiz"},
        {"crop_id": "maiz", "planting_month": 13},
        {"crop_id": "x", "planting_month": 1},
        {"crop_id": "maiz", "planting_month": 1, "extra": 1},
        "texto",
    ):
        with pytest.raises(ValueError):
            validate(schema, bad)


def test_large_results_are_trimmed_keeping_values_and_sources():
    big = {
        "strategies": [
            {"id": f"s{n}", "why": ["x" * 400] * 6, "source_id": "nasa_power", "score": n}
            for n in range(20)
        ]
    }
    trimmed = fit(copy.deepcopy(big), limit=12_000)
    assert len(str(trimmed)) < len(str(big))
    assert [s["score"] for s in trimmed["strategies"]] == list(range(20))
    assert all(s["source_id"] == "nasa_power" for s in trimmed["strategies"])


# ---------------------------------------------------------------- historial


def test_follow_up_gets_the_previous_turns_unchanged(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    model = ScriptedClient(
        [ToolCall("t1", "evaluate_crop", {"crop_id": "maiz", "planting_month": 4})],
        ["En abril es marginal."],
        [ToolCall("t2", "evaluate_crop", {"crop_id": "maiz", "planting_month": 5})],
        ["En mayo mejora."],
    )
    client.app.state.chat.client = model
    conversation_id = conversation(client, headers, field["id"])
    send(client, headers, conversation_id)
    first_turn = model.calls[1]["messages"] + [
        {"role": "assistant", "content": [{"text": "En abril es marginal."}]}
    ]
    send(client, headers, conversation_id, "¿y en mayo?")
    assert model.calls[2]["messages"][: len(first_turn)] == first_turn


def test_visible_history_hides_tool_results_and_marks_failures(headers):
    client = chat_app(ScriptedClient())
    field = new_field(client, headers)
    model = ScriptedClient(
        [ToolCall("t1", "evaluate_crop", {"crop_id": "maiz", "planting_month": 4})],
        ["Marginal."],
        ["Corte ", ModelUnavailableError("x")],
        ["Sigo aquí."],
    )
    client.app.state.chat.client = model
    conversation_id = conversation(client, headers, field["id"])
    send(client, headers, conversation_id, "uno")
    send(client, headers, conversation_id, "dos")
    send(client, headers, conversation_id, "tres")
    # El intercambio fallido no se reenvía: el tercer mensaje sigue a la primera respuesta.
    texts = [
        block.get("text") for message in model.calls[3]["messages"] for block in message["content"]
    ]
    assert "dos" not in texts and "uno" in texts
    history = client.get(f"{CHAT}/{conversation_id}", headers=headers).json()
    assert [(m["role"], m.get("status")) for m in history["messages"]] == [
        ("user", None),
        ("assistant", "done"),
        ("user", None),
        ("assistant", "failed"),
        ("user", None),
        ("assistant", "done"),
    ]
    assert history["messages"][1]["cards"][0]["type"] == "suitability"
    assert history["messages"][1]["citations"]
    assert "toolResult" not in str(history) and "toolUse" not in str(history)
    other = {"X-Client-Id": str(uuid.uuid4())}
    assert client.get(f"{CHAT}/{conversation_id}", headers=other).status_code == 404


def test_history_survives_a_restart(headers):
    repo = MemoryRepository()
    settings = Settings(chat_enabled=True, bedrock_model_id="m", cors_origins=["*"])
    first = TestClient(
        create_app(settings, repository=repo, model_client=ScriptedClient(["Hola."]))
    )
    conversation_id = conversation(first, headers)
    send(first, headers, conversation_id, "primero")
    model = ScriptedClient(["Sigo."])
    second = TestClient(create_app(settings, repository=repo, model_client=model))
    send(second, headers, conversation_id, "segundo")
    assert model.calls[0]["messages"][0]["content"][0]["text"] == "primero"


def test_conversation_is_full_after_40_user_messages(headers):
    client = chat_app(ScriptedClient())
    conversation_id = conversation(client, headers)
    services = client.app.state.chat
    stored = services.store.get(headers["X-Client-Id"], conversation_id)
    stored["user_messages"] = MAX_USER_MESSAGES
    services.store._repo.put(headers["X-Client-Id"], "conv#" + conversation_id, stored)
    response, _ = send(client, headers, conversation_id)
    assert response.status_code == 409 and response.json()["error"]["code"] == "conversation_full"


def test_exchange_document_roundtrip():
    exchange = Exchange(
        1, "hola", "done", [{"role": "user", "content": [{"text": "hola"}]}], "Hola", [], []
    )
    assert Exchange(**exchange.to_document()) == exchange


# ---------------------------------------------------------------- límites


def test_seventh_message_in_a_minute_is_429_and_others_are_free(headers):
    client = chat_app(ScriptedClient(*[["ok"]] * 8))
    conversation_id = conversation(client, headers)
    statuses = [send(client, headers, conversation_id, f"m{n}")[0].status_code for n in range(7)]
    assert statuses == [200] * 6 + [429]
    response, _ = send(client, headers, conversation_id, "otra vez")
    assert response.json()["error"]["code"] == "rate_limited"
    assert 0 < int(response.headers["retry-after"]) <= 61
    other = {"X-Client-Id": str(uuid.uuid4())}
    assert send(client, other, conversation(client, other))[0].status_code == 200
    field = new_field(client, headers)
    assert client.get(f"/api/v1/fields/{field['id']}/profile", headers=headers).status_code == 200


def test_daily_limit_and_shared_global_budget():
    repo = MemoryRepository()
    now = [1_700_000_000.0]
    limiter = RateLimiter(
        repo, ChatLimits(per_minute=100, per_day=3, daily_budget=5), clock=lambda: now[0]
    )
    for _ in range(3):
        limiter.check("a")
    with pytest.raises(LimitExceeded) as error:
        limiter.check("a")
    assert error.value.reason == "per_day" and error.value.retry_after > 60
    # Dos instancias comparten la tabla: el presupuesto se cuenta en conjunto (3 de «a» + 1).
    other_instance = RateLimiter(
        repo, ChatLimits(per_minute=100, per_day=10, daily_budget=4), clock=lambda: now[0]
    )
    other_instance.check("b")
    with pytest.raises(LimitExceeded) as error:
        other_instance.check("c")
    assert error.value.code == "chat_budget_exhausted" and error.value.status_code == 503


def test_budget_exhausted_is_503(headers):
    client = chat_app(ScriptedClient(*[["ok"]] * 3), chat_daily_budget=1)
    conversation_id = conversation(client, headers)
    assert send(client, headers, conversation_id)[0].status_code == 200
    response, _ = send(client, headers, conversation_id)
    assert (
        response.status_code == 503 and response.json()["error"]["code"] == "chat_budget_exhausted"
    )


def test_long_messages_are_rejected_and_output_tokens_are_capped(headers):
    model = ScriptedClient(["ok"])
    client = chat_app(model, chat_max_output_tokens=777)
    conversation_id = conversation(client, headers)
    response, _ = send(client, headers, conversation_id, "x" * 5000)
    assert response.status_code == 422 and response.json()["error"]["code"] == "message_too_long"
    send(client, headers, conversation_id)
    assert model.calls[0]["max_tokens"] == 777


# ---------------------------------------------------------------- instrucciones y contexto


def test_instructions_load_and_a_missing_file_is_an_error(tmp_path):
    assert "zona" in chat_context.system_prompt()
    empty = tmp_path / "system.md"
    empty.write_text("  ", encoding="utf-8")
    with pytest.raises(chat_context.PromptError):
        chat_context.system_prompt.__wrapped__(empty)
    with pytest.raises(chat_context.PromptError):
        chat_context.system_prompt.__wrapped__(tmp_path / "missing.md")


def test_context_goes_last_so_the_prefix_stays_stable(headers):
    model = ScriptedClient(["a"], ["b"])
    client = chat_app(model)
    first = new_field(client, headers)
    second = new_field(client, headers, name="Otra parcela")
    send(client, headers, conversation(client, headers, first["id"]))
    send(client, headers, conversation(client, headers, second["id"]))
    assert model.calls[0]["system"] == model.calls[1]["system"]
    assert model.calls[0]["tools"] == model.calls[1]["tools"]
    first_user, second_user = (call["messages"][-1]["content"] for call in model.calls)
    assert first_user[0] == second_user[0]
    assert first["name"] in first_user[1]["text"] and "Otra parcela" in second_user[1]["text"]


def test_field_id_in_the_message_overrides_the_conversation_field(headers):
    model = ScriptedClient(["a"])
    client = chat_app(model)
    first = new_field(client, headers)
    second = new_field(client, headers, name="Otra parcela")
    send(client, headers, conversation(client, headers, first["id"]), field_id=second["id"])
    assert "Otra parcela" in model.calls[0]["messages"][-1]["content"][1]["text"]


def test_threads_do_not_leak(headers):
    before = threading.active_count()
    client = chat_app(ScriptedClient(*[["ok"]] * 3))
    conversation_id = conversation(client, headers)
    for _ in range(3):
        send(client, headers, conversation_id)
    time.sleep(0.2)
    assert threading.active_count() <= before + 2


def test_tools_without_an_active_field_ask_for_one(headers):
    model = ScriptedClient(
        [ToolCall("t1", "evaluate_crop", {"crop_id": "maiz", "planting_month": 4})],
        ["¿Cuál terreno?"],
    )
    client = chat_app(model)
    _, events = send(client, headers, conversation(client, headers))
    result = model.calls[1]["messages"][-1]["content"][0]["toolResult"]["content"][0]["json"]
    assert result["error"] == "field_required"
    assert names(events)[-1] == "done"
