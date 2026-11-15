from fastapi.testclient import TestClient

from app.agent.client import ScriptedClient, ToolCall
from app.agent.events import parse_sse, sse
from app.config import Settings
from app.main import create_app
from scripts import run_chat_eval


def test_questions_file_is_valid():
    questions = run_chat_eval.load_questions()
    assert len(questions) >= 10
    ids = {question["id"] for question in questions}
    assert {"phosphorus", "english", "no_active_field", "off_topic", "drier_scenario"} <= ids


def events_for(text, tools=(), citations=()):
    body = sse("status", {"state": "thinking"})
    for tool in tools:
        body += sse("tool", {"name": tool, "label": tool, "state": "running"})
        body += sse("tool", {"name": tool, "label": tool, "state": "done"})
    body += sse("text", {"delta": text})
    for source_id in citations:
        body += sse("citation", {"source_id": source_id, "label": source_id})
    return parse_sse(body + sse("done", {"message_id": "m", "usage": {}}))


def test_checks_detect_good_and_bad_answers():
    question = {
        "id": "late_frost",
        "question": "¿Helada en marzo?",
        "language": "es",
        "field": "active",
        "expected_tools": ["get_risk_calendar"],
        "checks": ["citation_when_numbers", "language", "zonal_language"],
    }
    good = run_chat_eval.evaluate(
        question,
        events_for(
            "En tu zona hiela en el 40 % de los años (NASA POWER).",
            ["get_risk_calendar"],
            ["nasa_power"],
        ),
    )
    assert good["passed"]
    bad = run_chat_eval.evaluate(question, events_for("Tu parcela tiene 40 % de heladas."))
    assert bad["checks"] == {
        "finished": True,
        "expected_tools": False,
        "citation_when_numbers": False,
        "language": True,
        "zonal_language": False,
    }


def test_no_numbers_and_english_checks():
    question = {
        "id": "p",
        "question": "phosphorus?",
        "language": "en",
        "field": "active",
        "expected_tools": [],
        "checks": ["no_numbers", "language"],
    }
    assert run_chat_eval.evaluate(
        question, events_for("I don't have phosphorus data for your zone; get a lab analysis.")
    )["passed"]
    assert not run_chat_eval.evaluate(
        question, events_for("Your soil has about 12 ppm of phosphorus.")
    )["passed"]


def test_runs_against_an_app_and_writes_a_report(tmp_path, monkeypatch):
    answers = [
        [ToolCall("t", "get_risk_calendar", {})],
        ["En tu zona hiela en marzo el 40 % de los años (NASA POWER, 2016-2025)."],
    ]
    model = ScriptedClient(*answers * 10)
    client = TestClient(
        create_app(
            Settings(chat_enabled=True, bedrock_model_id="m", cors_origins=["*"]),
            model_client=model,
        )
    )
    questions = [q for q in run_chat_eval.load_questions() if q["id"] == "late_frost"]
    reports = run_chat_eval.run(client, questions)
    assert reports[0]["passed"] and reports[0]["tools"] == ["get_risk_calendar"]
    assert "late_frost" in run_chat_eval.summary(reports)
    assert "Geocerca activa: Demo" in model.calls[0]["messages"][-1]["content"][1]["text"]
