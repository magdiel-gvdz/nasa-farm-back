from typing import Protocol


class DataUnavailableError(Exception):
    """The environment has no usable published data."""


class DataStatus(Protocol):
    """Lo mínimo que `/ready` necesita del proveedor de datos."""

    def is_ready(self) -> bool: ...

    def data_version(self) -> str | None: ...


class StaticDataStatus:
    """Provisional hasta `c1-data-provider`: las respuestas fijas siempre están listas."""

    def __init__(self, ready: bool = True, version: str | None = "fixtures-v0"):
        self._ready = ready
        self._version = version

    def is_ready(self) -> bool:
        return self._ready

    def data_version(self) -> str | None:
        return self._version if self._ready else None
