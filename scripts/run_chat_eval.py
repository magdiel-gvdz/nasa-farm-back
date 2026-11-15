"""Evalúa el asistente agrónomo contra un entorno con el chat activo.

Siembra las geocercas de demostración, envía cada pregunta de `evals/chat/questions.yaml` en una
conversación nueva, recoge los eventos y aplica las comprobaciones automáticas. Escribe un informe
JSON y un resumen en Markdown.

Uso: python scripts/run_chat_eval.py --base-url https://... [--out build/chat-eval]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.events import parse_sse  # noqa: E402
from scripts import seed_demo  # noqa: E402

QUESTIONS = ROOT / "evals" / "chat" / "questions.yaml"
CHECKS = {
    "citation_when_numbers",
    "language",
    "zonal_language",
    "no_numbers",
    "mentions",
    "local_review",
}
PLOT_CLAIMS = re.compile(r"tu parcela tiene|tu terreno tiene|your plot has|your field has", re.I)
LOCAL_REVIEW = re.compile(r"agr[oó]nom|productor|t[eé]cnico|experto|agronomist|grower|local", re.I)
# Palabras muy frecuentes de cada idioma: basta para distinguir español de inglés.
_SPANISH = {"de", "la", "que", "el", "en", "los", "tu", "para", "con", "es", "una", "zona"}
_ENGLISH = {"the", "and", "your", "is", "to", "of", "in", "for", "with", "zone", "it"}
NUMBER = re.compile(r"\d")


def load_questions(path: Path = QUESTIONS) -> list[dict]:
    """Preguntas validadas: campos obligatorios, comprobaciones conocidas, ids únicos."""
    questions = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or len(questions) < 10:
        raise ValueError("se esperan al menos 10 preguntas")
    seen = set()
    for question in questions:
        for key in ("id", "question", "language", "field", "expected_tools", "checks"):
            if key not in question:
                raise ValueError(f"{question.get('id', '?')}: falta {key}")
        if question["id"] in seen:
            raise ValueError(f"id repetido: {question['id']}")
        seen.add(question["id"])
        if question["language"] not in {"es", "en"} or question["field"] not in {"active", "none"}:
            raise ValueError(f"{question['id']}: language o field no válidos")
        unknown = set(question["checks"]) - CHECKS
        if unknown:
            raise ValueError(f"{question['id']}: comprobaciones desconocidas {unknown}")
        if "mentions" in question["checks"] and not question.get("mentions"):
            raise ValueError(f"{question['id']}: falta la lista mentions")
    return questions


def language_of(text: str) -> str:
    words = re.findall(r"[a-záéíóúñ]+", text.lower())
    spanish = sum(word in _SPANISH for word in words)
    english = sum(word in _ENGLISH for word in words)
    return "es" if spanish >= english else "en"


def evaluate(question: dict, events: list[tuple[str, dict]]) -> dict:
    """Resultado de una pregunta a partir de los eventos de su respuesta."""
    text = "".join(data["delta"] for name, data in events if name == "text")
    tools = [data["name"] for name, data in events if name == "tool" and data["state"] == "running"]
    citations = [data["source_id"] for name, data in events if name == "citation"]
    final = events[-1][0] if events else "none"
    results = {"finished": final == "done"}
    expected = question["expected_tools"]
    results["expected_tools"] = (
        (not tools) if not expected else any(tool in tools for tool in expected)
    )
    for check in question["checks"]:
        if check == "citation_when_numbers":
            results[check] = not NUMBER.search(text) or bool(citations)
        elif check == "language":
            results[check] = language_of(text) == question["language"]
        elif check == "zonal_language":
            results[check] = not PLOT_CLAIMS.search(text)
        elif check == "no_numbers":
            results[check] = not re.search(r"\d+(?:[.,]\d+)?\s*(?:%|mg|ppm|kg|mm|°)", text)
        elif check == "mentions":
            results[check] = any(term.lower() in text.lower() for term in question["mentions"])
        elif check == "local_review":
            results[check] = bool(LOCAL_REVIEW.search(text))
    return {
        "id": question["id"],
        "question": question["question"],
        "answer": text,
        "tools": tools,
        "citations": citations,
        "final_event": final,
        "checks": results,
        "passed": all(results.values()),
    }


def run(client: httpx.Client, questions: list[dict]) -> list[dict]:
    demo = seed_demo.load_demo()
    headers = {"X-Client-Id": demo["client_id"]}
    fields = seed_demo.seed(client, demo)
    reports = []
    for question in questions:
        body = {"field_id": fields[0]["id"]} if question["field"] == "active" else {}
        conversation = client.post("/api/v1/chat/conversations", json=body, headers=headers)
        conversation.raise_for_status()
        started = time.perf_counter()
        response = client.post(
            f"/api/v1/chat/conversations/{conversation.json()['conversation_id']}/messages",
            json={"text": question["question"]},
            headers={**headers, "Accept-Language": question["language"]},
        )
        events = parse_sse(response.text) if response.status_code == 200 else []
        report = evaluate(question, events)
        report["seconds"] = round(time.perf_counter() - started, 1)
        report["http_status"] = response.status_code
        reports.append(report)
        print(
            f"{'OK  ' if report['passed'] else 'FAIL'} {question['id']:<22} {report['seconds']:>5}s  {report['tools']}"
        )
    return reports


def summary(reports: list[dict]) -> str:
    passed = sum(report["passed"] for report in reports)
    lines = [
        f"# Evaluación del chat: {passed}/{len(reports)} preguntas superan todas las comprobaciones",
        "",
    ]
    for report in reports:
        failed = [name for name, ok in report["checks"].items() if not ok]
        lines += [
            f"## {report['id']} — {'OK' if report['passed'] else 'FALLA: ' + ', '.join(failed)}",
            "",
            f"**Pregunta:** {report['question']}",
            "",
            f"**Herramientas:** {', '.join(report['tools']) or 'ninguna'} · "
            f"**Fuentes citadas:** {', '.join(report['citations']) or 'ninguna'} · {report['seconds']} s",
            "",
            report["answer"] or "_(sin respuesta)_",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", default=str(ROOT / "build" / "chat-eval"))
    args = parser.parse_args(argv)
    questions = load_questions()
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120) as client:
        reports = run(client, questions)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out / "report.md").write_text(summary(reports), encoding="utf-8")
    passed = sum(report["passed"] for report in reports)
    print(f"{passed}/{len(reports)} preguntas superan todas las comprobaciones. Informe: {out}")
    return 0 if passed == len(reports) else 1


if __name__ == "__main__":
    sys.exit(main())
