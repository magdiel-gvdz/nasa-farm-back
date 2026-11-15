"""Respuestas fijas de referencia (celda de Saltillo) para endpoints aún sin implementación.

Un texto traducible se escribe como `{"$t": {"es": "...", "en": "..."}}` y se resuelve al
idioma de la petición. Toda respuesta que salga de aquí lleva `X-Fieldshift-Mock: 1`.
"""

import json
from functools import cache
from importlib import resources
from typing import Any

from fastapi import Response

from app.i18n import DEFAULT_LANGUAGE

MOCK_HEADER = "X-Fieldshift-Mock"
FIXTURE_NAMES = (
    "profile",
    "suitability_detail",
    "suitability_matrix",
    "rotations",
)


@cache
def _raw(name: str) -> str:
    return resources.files(__package__).joinpath(f"{name}.json").read_text(encoding="utf-8")


def _localize(node: Any, language: str) -> Any:
    if isinstance(node, dict):
        if set(node) == {"$t"}:
            texts = node["$t"]
            return texts.get(language, texts[DEFAULT_LANGUAGE])
        return {key: _localize(value, language) for key, value in node.items()}
    if isinstance(node, list):
        return [_localize(value, language) for value in node]
    return node


def load_fixture(name: str, language: str = DEFAULT_LANGUAGE) -> Any:
    """Copia nueva de la respuesta fija, con los textos en `language`."""
    return _localize(json.loads(_raw(name)), language)


def mark_mock(response: Response) -> None:
    response.headers[MOCK_HEADER] = "1"
