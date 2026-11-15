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
        """Ordenadas por fecha; `DailySeries` indica además su origen."""
        ...


_ATHENA_SETTINGS = {
    "data_region": "DATA_REGION",
    "athena_workgroup": "ATHENA_WORKGROUP",
    "athena_database": "ATHENA_DATABASE",
    "data_version_parameter": "DATA_VERSION_PARAMETER",
}


def _power_source(settings):
    from app.data.power import LocalCache, PowerClient, PowerDailySource, S3Cache

    cache = S3Cache(settings.app_bucket) if settings.app_bucket else LocalCache()
    return PowerDailySource(PowerClient(cache), settings.lapse_rate_c_per_km)


def create_provider(settings) -> DataProvider:
    """Proveedor elegido por `DATA_PROVIDER`. Un valor desconocido impide arrancar."""
    name = settings.data_provider
    if name == "fixture":
        from app.data.fixture import FixtureProvider

        return FixtureProvider()
    if name == "athena":
        from app.data.athena import AthenaProvider, BotoAthenaExecutor, SsmVersionSource

        missing = [
            variable
            for attribute, variable in _ATHENA_SETTINGS.items()
            if not getattr(settings, attribute)
        ]
        if missing:
            logger.error("DATA_PROVIDER=athena necesita las variables: %s", ", ".join(missing))
            raise ValueError(f"Faltan variables para DATA_PROVIDER=athena: {', '.join(missing)}")
        return AthenaProvider(
            BotoAthenaExecutor(
                settings.data_region, settings.athena_workgroup, settings.athena_database
            ),
            SsmVersionSource(settings.data_region, settings.data_version_parameter),
            poll_seconds=settings.data_poll_seconds,
            power=_power_source(settings),
        )
    logger.error("DATA_PROVIDER=%r no es válido; valores admitidos: 'fixture', 'athena'", name)
    raise ValueError(f"DATA_PROVIDER no admitido: {name!r}")
