"""Proveedor de datos que lee las vistas `v_*` de DATA en Athena y las sirve desde memoria.

Las seis vistas de la instantánea se cargan completas al arrancar y cada vez que cambia la
versión publicada (parámetro SSM). `v_cell_daily` se consulta bajo demanda, por celda.
Solo se emiten `SELECT` sobre vistas `v_*`: sin CTAS, sin UNLOAD, sin reutilización de
resultados y sin `OutputLocation` propio (lo fija el workgroup de DATA).
"""

import dataclasses
import logging
import math
import re
import threading
import time
import types
import typing
import unicodedata
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
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
from app.data.provider import DataUnavailableError, UnknownCellError

logger = logging.getLogger(__name__)

Row = dict[str, str | None]
# Solo consultas de lectura sobre una vista publicada.
_ALLOWED_QUERY = re.compile(
    r"^SELECT \* FROM (v_[a-z_]+)( WHERE cell_id = \?)?( ORDER BY [a-z_, ]+)?$"
)
_FILL_VALUES = {-999.0, -9999.0}
# Valor inicial del parámetro: hay infraestructura, pero DATA aún no ha publicado.
NO_PUBLICATION = "none"
DAILY_CACHE_CELLS = 32
_DATA_CLASSES = {
    "observacion": "observation",
    "modelo": "model",
    "estimacion": "estimate",
    "derivado": "derived",
}


class DailyUnavailableError(DataUnavailableError):
    """La serie diaria no se pudo obtener; el resto de los datos sigue disponible."""


class SnapshotError(Exception):
    """Lo publicado no supera la validación; el mensaje nombra la vista y la causa."""


class QueryExecutor(Protocol):
    def run(self, sql: str, parameters: Sequence[str] = ()) -> list[Row]:
        """Filas de un `SELECT`, con cada valor como texto o `None`."""
        ...


class VersionSource(Protocol):
    def current(self) -> str | None:
        """Versión publicada por DATA; `None` si todavía no hay ninguna."""
        ...


def check_query(sql: str) -> str:
    """Nombre de la vista consultada; rechaza todo lo que no sea un SELECT sobre `v_*`."""
    match = _ALLOWED_QUERY.match(sql)
    if not match:
        raise ValueError(f"Consulta no permitida: {sql!r}")
    return match.group(1)


class BotoAthenaExecutor:
    """Ejecuta consultas en el workgroup de DATA con boto3, en la región de los datos."""

    def __init__(self, region: str, workgroup: str, database: str, timeout_s: float = 180):
        import boto3

        self._athena = boto3.client("athena", region_name=region)
        self._workgroup = workgroup
        self._database = database
        self._timeout_s = timeout_s

    def run(self, sql: str, parameters: Sequence[str] = ()) -> list[Row]:
        check_query(sql)
        request = {
            "QueryString": sql,
            "QueryExecutionContext": {"Database": self._database},
            "WorkGroup": self._workgroup,
            # Athena no detecta que cambió el dato debajo de una vista: nunca reutilizar.
            "ResultReuseConfiguration": {"ResultReuseByAgeConfiguration": {"Enabled": False}},
        }
        if parameters:
            request["ExecutionParameters"] = [f"'{value}'" for value in parameters]
        query_id = self._athena.start_query_execution(**request)["QueryExecutionId"]
        deadline = time.monotonic() + self._timeout_s
        while True:
            status = self._athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"][
                "Status"
            ]
            if status["State"] == "SUCCEEDED":
                break
            if status["State"] in {"FAILED", "CANCELLED"}:
                raise RuntimeError(status.get("StateChangeReason", status["State"]))
            if time.monotonic() > deadline:
                self._athena.stop_query_execution(QueryExecutionId=query_id)
                raise TimeoutError(f"La consulta superó {self._timeout_s:.0f} s")
            time.sleep(0.5)
        rows: list[Row] = []
        header: list[str] | None = None
        paginator = self._athena.get_paginator("get_query_results")
        for page in paginator.paginate(QueryExecutionId=query_id):
            for raw in page["ResultSet"]["Rows"]:
                values = [cell.get("VarCharValue") for cell in raw["Data"]]
                if header is None:
                    header = values
                else:
                    rows.append(dict(zip(header, values, strict=True)))
        return rows


class SsmVersionSource:
    def __init__(self, region: str, parameter: str):
        import boto3

        self._ssm = boto3.client("ssm", region_name=region)
        self._parameter = parameter

    def current(self) -> str | None:
        try:
            value = self._ssm.get_parameter(Name=self._parameter)["Parameter"]["Value"]
        except self._ssm.exceptions.ParameterNotFound:
            return None
        value = value.strip()
        return None if not value or value.lower() == NO_PUBLICATION else value


# ---------------------------------------------------------------- conversión de filas


def _field_types(model: type) -> dict[str, tuple[type, bool]]:
    """Tipo base y si admite nulo de cada columna del modelo."""
    hints = typing.get_type_hints(model)
    result = {}
    for column in dataclasses.fields(model):
        hint = hints[column.name]
        if isinstance(hint, types.UnionType):
            base = next(arg for arg in typing.get_args(hint) if arg is not type(None))
            result[column.name] = (base, True)
        else:
            result[column.name] = (hint, False)
    return result


def _convert(value: str | None, base: type):
    if value is None:
        return None
    if base is str:
        # Una cadena vacía es un valor (por ejemplo, sin motivos de vulnerabilidad).
        return value
    if value == "":
        return None
    if base is bool:
        return value.strip().lower() == "true"
    number = float(value)
    # Athena devuelve NaN en columnas vacías; DATA nunca publica valores de relleno.
    if math.isnan(number) or number in _FILL_VALUES:
        return None
    return int(number) if base is int else number


def build_rows(view: str, model: type, rows: Sequence[Row], renames: dict[str, str] | None = None):
    """Filas tipadas de una vista; las columnas que el modelo no usa se ignoran."""
    if not rows:
        raise SnapshotError(f"{view}: la vista no tiene filas")
    columns = {renames.get(name, name) if renames else name for name in rows[0]}
    kinds = _field_types(model)
    missing = sorted(set(kinds) - columns)
    if missing:
        raise SnapshotError(f"{view}: faltan columnas obligatorias: {', '.join(missing)}")
    built = []
    for row in rows:
        values = {}
        for name, (base, nullable) in kinds.items():
            value = _convert(row.get(name), base)
            if value is None and not nullable:
                raise SnapshotError(f"{view}: la columna {name} no puede ser nula")
            values[name] = value
        built.append(model(**values))
    return built


def _data_class(value: str) -> str:
    """Clase de dato del contrato de la API a partir del texto libre de DATA.

    DATA escribe, por ejemplo, "modelo (reanálisis MERRA-2)" u "observación asimilada en
    modelo": manda la primera palabra. Un texto desconocido se trata como estimación, que
    es la afirmación más prudente.
    """
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    for prefix, data_class in _DATA_CLASSES.items():
        if plain.startswith(prefix):
            return data_class
    logger.warning("Clase de dato desconocida en v_sources: %r", value)
    return "estimate"


# ---------------------------------------------------------------- instantánea


@dataclass(frozen=True)
class Snapshot:
    """Datos de una publicación, inmutables e indexados por celda."""

    version: str
    cells: dict[str, Cell]
    climatology: dict[str, tuple[ClimatologyDecade, ...]]
    indicators: dict[str, tuple[IndicatorDecade, ...]]
    years: dict[str, tuple[IndicatorYear, ...]]
    soil: dict[str, tuple[SoilLayer, ...]]
    sources: tuple[Source, ...]


def _by_cell(rows: Sequence, order) -> dict[str, tuple]:
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.cell_id, []).append(row)
    return {cell_id: tuple(sorted(group, key=order)) for cell_id, group in grouped.items()}


def load_snapshot(executor: QueryExecutor, version: str) -> Snapshot:
    """Lee las seis vistas y valida lo publicado. Lanza `SnapshotError` si no es utilizable."""

    def read(view: str, model: type) -> list:
        try:
            rows = executor.run(f"SELECT * FROM {view}")
        except Exception as error:
            raise SnapshotError(f"{view}: {error}") from error
        return build_rows(view, model, rows)

    cells = {cell.cell_id: cell for cell in read("v_cells", Cell)}
    climatology = _by_cell(read("v_cell_profile", ClimatologyDecade), lambda row: row.decade)
    for cell_id, decades in climatology.items():
        if [row.decade for row in decades] != list(range(1, 37)):
            raise SnapshotError(f"v_cell_profile: la celda {cell_id} no tiene las 36 decenas")
    sources = [
        dataclasses.replace(source, data_class=_data_class(source.data_class))
        for source in read("v_sources", Source)
    ]
    return Snapshot(
        version=version,
        cells=cells,
        climatology=climatology,
        indicators=_by_cell(
            read("v_cell_indicators", IndicatorDecade), lambda row: (row.year, row.decade)
        ),
        years=_by_cell(read("v_cell_year", IndicatorYear), lambda row: row.year),
        soil=_by_cell(read("v_cell_soil", SoilLayer), lambda row: row.depth_top_cm),
        sources=tuple(sources),
    )


def _is_missing_view(error: Exception) -> bool:
    """Athena informa una vista inexistente con estos textos; un fallo de permisos, no."""
    text = str(error).lower()
    return "does not exist" in text or "table_not_found" in text or "table not found" in text


# ---------------------------------------------------------------- proveedor


class AthenaProvider:
    """Sirve la última instantánea válida y la renueva cuando DATA publica otra versión."""

    def __init__(self, executor: QueryExecutor, versions: VersionSource, poll_seconds: float = 300):
        self._executor = executor
        self._versions = versions
        self._poll_seconds = poll_seconds
        self._snapshot: Snapshot | None = None
        self._daily: OrderedDict[tuple[str, str], tuple[DailyRow, ...]] = OrderedDict()
        self._daily_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------ ciclo de vida

    def start(self) -> None:
        """Lanza la carga inicial y la comprobación periódica en segundo plano."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="athena-provider", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.refresh()
            self._stop.wait(self._poll_seconds)

    def refresh(self) -> bool:
        """Comprueba la versión publicada y recarga si cambió. Devuelve si hubo carga nueva.

        Nunca lanza: ante cualquier fallo se conserva la última instantánea válida.
        """
        try:
            version = self._versions.current()
        except Exception:
            logger.exception("No se pudo leer la versión publicada por DATA")
            return False
        if version is None:
            logger.info("DATA aún no ha publicado ninguna versión; se reintentará")
            return False
        if self._snapshot is not None and self._snapshot.version == version:
            return False
        started = time.monotonic()
        try:
            snapshot = load_snapshot(self._executor, version)
            # Una publicación durante la carga puede mezclar vistas de dos versiones. Esta
            # comprobación la detecta solo si el parámetro ya cambió: no es una garantía.
            if self._versions.current() != version:
                raise SnapshotError("la versión publicada cambió durante la carga")
        except Exception as error:
            logger.error("Carga de datos %s rechazada: %s", version, error)
            return False
        self._snapshot = snapshot
        logger.info(
            "Datos %s cargados: %d celdas en %.1f s",
            version,
            len(snapshot.cells),
            time.monotonic() - started,
        )
        return True

    # ------------------------------------------------------------ lectura

    def is_ready(self) -> bool:
        return self._snapshot is not None

    def data_version(self) -> str | None:
        return self._snapshot.version if self._snapshot else None

    def _current(self) -> Snapshot:
        if self._snapshot is None:
            raise DataUnavailableError("Todavía no hay datos cargados")
        return self._snapshot

    def cells(self) -> Sequence[Cell]:
        return tuple(self._current().cells.values())

    def zones(self) -> Sequence[Zone]:
        zones: dict[str, Zone] = {}
        for cell in self._current().cells.values():
            known = zones.get(cell.zone_id)
            zones[cell.zone_id] = Zone(
                cell.zone_id, cell.zone_name, known.n_cells + 1 if known else 1
            )
        return tuple(zones.values())

    def cell(self, cell_id: str) -> Cell:
        try:
            return self._current().cells[cell_id]
        except KeyError:
            raise UnknownCellError(cell_id) from None

    def _rows(self, table: str, cell_id: str) -> tuple:
        snapshot = self._current()
        if cell_id not in snapshot.cells:
            raise UnknownCellError(cell_id)
        return getattr(snapshot, table).get(cell_id, ())

    def climatology(self, cell_id: str) -> Sequence[ClimatologyDecade]:
        return self._rows("climatology", cell_id)

    def indicators(self, cell_id: str) -> Sequence[IndicatorDecade]:
        return self._rows("indicators", cell_id)

    def years(self, cell_id: str) -> Sequence[IndicatorYear]:
        return self._rows("years", cell_id)

    def soil(self, cell_id: str) -> Sequence[SoilLayer]:
        return self._rows("soil", cell_id)

    def sources(self) -> Sequence[Source]:
        return self._current().sources

    def daily(self, cell_id: str) -> Sequence[DailyRow]:
        """Serie diaria de la celda, leída bajo demanda y guardada por versión y celda."""
        snapshot = self._current()
        if cell_id not in snapshot.cells:
            raise UnknownCellError(cell_id)
        key = (snapshot.version, cell_id)
        with self._daily_lock:
            if key in self._daily:
                self._daily.move_to_end(key)
                return self._daily[key]
        try:
            rows = self._executor.run(
                "SELECT * FROM v_cell_daily WHERE cell_id = ? ORDER BY date", [cell_id]
            )
            series = tuple(sorted(build_rows("v_cell_daily", DailyRow, rows), key=lambda r: r.date))
        except Exception as error:
            cause = "la vista no existe" if _is_missing_view(error) else str(error)
            logger.error("Serie diaria de %s no disponible: %s", cell_id, cause)
            raise DailyUnavailableError(f"Serie diaria no disponible: {cause}") from error
        with self._daily_lock:
            self._daily[key] = series
            # Las series de versiones anteriores no se reutilizan: se descartan.
            for stale in [k for k in self._daily if k[0] != snapshot.version]:
                del self._daily[stale]
            while len(self._daily) > DAILY_CACHE_CELLS:
                self._daily.popitem(last=False)
        return series
