"""Repositorio de documentos por cliente: interfaz e implementación en memoria.

Tabla única: clave de partición `client_id` y clave de orden `sk` (`field#<id>`,
`conv#<id>`, ...). El documento se guarda entero; `attributes` son campos de primer nivel
que acompañan al elemento para poder consultarlo sin abrirlo.
"""

import json
import threading
from typing import Protocol


def require_prefix(prefix: str) -> str:
    """DynamoDB no admite `begins_with` con cadena vacía; se exige en toda implementación."""
    if not prefix:
        raise ValueError("prefix no puede estar vacío")
    return prefix


class Repository(Protocol):
    def put(
        self, client_id: str, sk: str, document: dict, attributes: dict[str, str] | None = None
    ) -> None: ...

    def get(self, client_id: str, sk: str) -> dict | None: ...

    def list_prefix(self, client_id: str, prefix: str, *, newest_first: bool = False) -> list[dict]:
        """Documentos cuyo `sk` empieza por `prefix`, ordenados por `sk`."""
        ...

    def delete(self, client_id: str, sk: str) -> bool:
        """Devuelve `False` si el elemento no existía."""
        ...

    def count_prefix(self, client_id: str, prefix: str) -> int: ...

    def increment(self, client_id: str, sk: str, *, expires_at: int | None = None) -> int:
        """Suma 1 de forma atómica al contador `client_id`/`sk` y devuelve el valor nuevo."""
        ...


class MemoryRepository:
    """Para desarrollo local y pruebas; los datos se pierden al reiniciar el proceso."""

    def __init__(self):
        self._items: dict[tuple[str, str], str] = {}
        self._counters: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def put(
        self, client_id: str, sk: str, document: dict, attributes: dict[str, str] | None = None
    ) -> None:
        # Se serializa como en DynamoDB para no compartir objetos mutables con quien llama.
        body = json.dumps(document)
        with self._lock:
            self._items[(client_id, sk)] = body

    def get(self, client_id: str, sk: str) -> dict | None:
        with self._lock:
            body = self._items.get((client_id, sk))
        return None if body is None else json.loads(body)

    def list_prefix(self, client_id: str, prefix: str, *, newest_first: bool = False) -> list[dict]:
        require_prefix(prefix)
        with self._lock:
            matches = sorted(
                (
                    (sk, body)
                    for (owner, sk), body in self._items.items()
                    if owner == client_id and sk.startswith(prefix)
                ),
                reverse=newest_first,
            )
        return [json.loads(body) for _sk, body in matches]

    def delete(self, client_id: str, sk: str) -> bool:
        with self._lock:
            return self._items.pop((client_id, sk), None) is not None

    def increment(self, client_id: str, sk: str, *, expires_at: int | None = None) -> int:
        with self._lock:
            value = self._counters.get((client_id, sk), 0) + 1
            self._counters[(client_id, sk)] = value
            return value

    def count_prefix(self, client_id: str, prefix: str) -> int:
        require_prefix(prefix)
        with self._lock:
            return sum(
                1 for owner, sk in self._items if owner == client_id and sk.startswith(prefix)
            )
