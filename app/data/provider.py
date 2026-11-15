"""Interfaz única de lectura de los datos de DATA y selección de su implementación."""

import logging
from collections.abc import Sequence
from typing import Protocol

from app.data.models import (
    Cell,
    ClimatologyDecade,
    DailyRow,
    IndicatorDecade,
    IndicatorYear,
    SoilLayer,
    Source,
    Zone,
)

logger = logging.getLogger(__name__)


class DataUnavailableError(Exception):
    """The environment has no usable published data."""


class UnknownCellError(KeyError):
    """La celda no está publicada; la API lo traduce a `out_of_region` o `not_found`."""

    def __init__(self, cell_id: str):
        super().__init__(cell_id)
        self.cell_id = cell_id


class DataProvider(Protocol):
    """Todas las consultas por celda lanzan `UnknownCellError` si la celda no existe."""

    def is_ready(self) -> bool: ...

    def data_version(self) -> str | None:
        """Versión publicada que se está sirviendo; `None` mientras no hay datos."""
        ...

    def cells(self) -> Sequence[Cell]: ...

    def zones(self) -> Sequence[Zone]: ...

    def cell(self, cell_id: str) -> Cell: ...

    def climatology(self, cell_id: str) -> Sequence[ClimatologyDecade]:
        """36 filas, `decade` de 1 a 36."""
        ...

    def indicators(self, cell_id: str) -> Sequence[IndicatorDecade]:
        """Ordenadas por año y decena."""
        ...

    def years(self, cell_id: str) -> Sequence[IndicatorYear]: ...

    def soil(self, cell_id: str) -> Sequence[SoilLayer]:
        """De la capa más superficial a la más profunda."""
        ...

    def sources(self) -> Sequence[Source]: ...

    def daily(self, cell_id: str) -> Sequence[DailyRow]:
        """Ordenadas por fecha."""
        ...


def create_provider(name: str) -> DataProvider:
    """Proveedor elegido por `DATA_PROVIDER`. Un valor desconocido impide arrancar."""
    if name == "fixture":
        from app.data.fixture import FixtureProvider

        return FixtureProvider()
    logger.error("DATA_PROVIDER=%r no es válido; valores admitidos: 'fixture'", name)
    raise ValueError(f"DATA_PROVIDER no admitido: {name!r}")
