"""Herramientas del asistente: definición, registro y ejecución con el contexto del cliente.

Cada herramienta llama a la misma función que su endpoint, así que devuelve exactamente lo
mismo que la API. El `client_id` sale de la conversación, nunca de los argumentos del modelo:
una herramienta no puede leer geocercas de otro cliente.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.api.errors import ApiError
from app.data import DataUnavailableError

MAX_RESULT_CHARS = 12_000


class ToolInputError(ValueError):
    """Los argumentos del modelo no cumplen el esquema de la herramienta."""


@dataclass(frozen=True)
class ToolContext:
    client_id: str
    language: str
    repo: Any
    data: Any
    catalog: Any
    engine: Any
    profiles: Any
    scenarios: Any
    active_field_id: str | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict
    run: Callable[[ToolContext, dict], Any]
    label: dict[str, str]
    card_type: str | None = None

    def spec(self) -> dict:
        """Definición para la API Converse de Bedrock."""
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {"json": self.schema},
            }
        }


def validate(schema: dict, arguments: Any) -> dict:
    """Validación estricta del subconjunto de JSON Schema que usan las herramientas."""
    if not isinstance(arguments, dict):
        raise ToolInputError("los argumentos deben ser un objeto")
    properties = schema.get("properties", {})
    unknown = set(arguments) - set(properties)
    if unknown:
        raise ToolInputError(f"argumentos desconocidos: {', '.join(sorted(unknown))}")
    missing = [name for name in schema.get("required", []) if name not in arguments]
    if missing:
        raise ToolInputError(f"faltan argumentos: {', '.join(missing)}")
    checked = {}
    for name, value in arguments.items():
        rule = properties[name]
        kind = rule.get("type")
        if kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int | float) or int(value) != value:
                raise ToolInputError(f"{name} debe ser un entero")
            value = int(value)
        elif kind == "number":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ToolInputError(f"{name} debe ser un número")
        elif kind == "string" and not isinstance(value, str):
            raise ToolInputError(f"{name} debe ser texto")
        elif kind == "array" and not isinstance(value, list):
            raise ToolInputError(f"{name} debe ser una lista")
        if "enum" in rule and value not in rule["enum"]:
            raise ToolInputError(f"{name} debe ser uno de {rule['enum']}")
        if "minimum" in rule and value < rule["minimum"]:
            raise ToolInputError(f"{name} debe ser al menos {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            raise ToolInputError(f"{name} debe ser como mucho {rule['maximum']}")
        if kind == "array" and "items" in rule and "enum" in rule["items"]:
            bad = [item for item in value if item not in rule["items"]["enum"]]
            if bad:
                raise ToolInputError(f"{name} contiene valores no válidos: {bad}")
        checked[name] = value
    return checked


def jsonable(value: Any) -> Any:
    """Resultado como JSON puro (los modelos Pydantic de las rutas se convierten)."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def fit(result: Any, limit: int = MAX_RESULT_CHARS) -> Any:
    """Recorta listas de textos largos hasta que el resultado cabe, sin tocar valores ni fuentes."""
    if len(json.dumps(result, ensure_ascii=False)) <= limit:
        return result
    trimmable = ("why", "benefits", "gaps", "risks_local_review", "recommendations", "evidence")

    def trim(node, keep):
        if isinstance(node, dict):
            return {
                key: (
                    value[:keep]
                    if key in trimmable and isinstance(value, list)
                    else trim(value, keep)
                )
                for key, value in node.items()
            }
        if isinstance(node, list):
            return [trim(item, keep) for item in node]
        return node

    for keep in (2, 1, 0):
        result = trim(result, keep)
        if len(json.dumps(result, ensure_ascii=False)) <= limit:
            return result
    return result


def source_ids(node: Any) -> set[str]:
    """`source_id` citados en un resultado y los `id` de sus listas `sources`."""
    found: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get("source_id"), str):
            found.add(node["source_id"])
        if isinstance(node.get("sources"), list):
            found |= {
                item["id"] for item in node["sources"] if isinstance(item, dict) and "id" in item
            }
        for value in node.values():
            found |= source_ids(value)
    elif isinstance(node, list):
        for value in node:
            found |= source_ids(value)
    return found


def describe_sources(context: "ToolContext", ids: set[str]) -> list[dict]:
    """Nombre y periodo de cada fuente, para que el modelo los cite sin inventarlos."""
    try:
        known = {source.source_id: source for source in context.data.sources()}
    except Exception:
        known = {}
    described = []
    for source_id in sorted(ids):
        source = known.get(source_id)
        if source is not None:
            described.append({"id": source_id, "name": source.name, "period": source.period})
        elif source_id == "lab_report":
            described.append(
                {"id": source_id, "name": "Análisis de laboratorio del agricultor", "period": None}
            )
    return described


@dataclass(frozen=True)
class ToolOutcome:
    ok: bool
    result: Any
    card: dict | None = None


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool.name: tool for tool in tools}

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[dict]:
        return [tool.spec() for tool in self._tools.values()]

    def label(self, name: str, language: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return name
        return tool.label.get(language, tool.label["es"])

    def execute(self, context: ToolContext, name: str, arguments: Any) -> ToolOutcome:
        tool = self._tools.get(name)
        if tool is None:
            return ToolOutcome(False, {"error": "unknown_tool", "message": f"No existe {name}"})
        try:
            result = jsonable(tool.run(context, validate(tool.schema, arguments)))
        except ToolInputError as error:
            return ToolOutcome(False, {"error": "invalid_arguments", "message": str(error)})
        except ApiError as error:
            return ToolOutcome(False, {"error": error.code, "details": error.details})
        except DataUnavailableError as error:
            return ToolOutcome(False, {"error": "data_unavailable", "message": str(error)})
        payload = (
            {key: value for key, value in result.items() if key != "sources"}
            if isinstance(result, dict)
            else result
        )
        card = {"type": tool.card_type, "payload": payload} if tool.card_type else None
        ids = source_ids(result)
        if ids and isinstance(result, dict):
            result = {**result, "cite_sources": describe_sources(context, ids)}
        return ToolOutcome(True, fit(result), card)
