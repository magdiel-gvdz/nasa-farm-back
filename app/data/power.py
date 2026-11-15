"""Respaldo de la serie diaria con NASA POWER en vivo, para instalaciones sin `v_cell_daily`.

Se pide una vez cada cuadro POWER (las coordenadas `power_cell_lat` y `power_cell_lon` que
publica DATA, sin redondear) y periodo, y la respuesta original se guarda en `cache/power/`
del bucket del entorno o en un directorio local. La corrección por altura se aplica por
celda después de leer la caché, así que dos celdas del mismo cuadro comparten la descarga.
"""

import hashlib
import json
import logging
import math
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Protocol

from app.data.models import Cell, DailyRow, Source

logger = logging.getLogger(__name__)

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = (
    "T2M_MAX",
    "T2M_MIN",
    "T2M",
    "PRECTOTCORR",
    "ALLSKY_SFC_SW_DWN",
    "RH2M",
    "WS2M",
    "WS10M_MAX",
)
TIMEOUT_S = 20
RETRY_PAUSE_S = 2
CACHE_PREFIX = "cache/power/"
DEFAULT_LAPSE_RATE_C_PER_KM = 6.5
_FILL = -999.0

POWER_LIVE_SOURCE = Source(
    source_id="power_live",
    name="NASA POWER Daily (consulta en vivo)",
    organization="NASA LaRC",
    product_version="POWER Daily API, comunidad AG",
    url="https://power.larc.nasa.gov/",
    resolution="0.5° x 0.625° (~55 km), diaria",
    period="",
    access_date=None,
    license="Datos abiertos de NASA; citar NASA POWER",
    data_class="model",
    status="in_use",
    used_for=(
        "serie diaria cuando DATA no publica v_cell_daily; las temperaturas ajustadas "
        "por altura son una estimación (6.5 °C/km)"
    ),
)


class PowerUnavailableError(Exception):
    """NASA POWER no respondió a tiempo o devolvió un error."""


class RawCache(Protocol):
    def get(self, key: str) -> bytes | None: ...

    def put(self, key: str, body: bytes) -> None: ...


class LocalCache:
    def __init__(self, root: Path | None = None):
        self._root = root or Path(tempfile.gettempdir()) / "fieldshift-power"

    def get(self, key: str) -> bytes | None:
        path = self._root / key
        return path.read_bytes() if path.exists() else None

    def put(self, key: str, body: bytes) -> None:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


class S3Cache:
    """`cache/power/` del bucket del entorno: sobrevive a reinicios y despliegues."""

    def __init__(self, bucket: str):
        import boto3

        self._s3 = boto3.client("s3")
        self._bucket = bucket

    def get(self, key: str) -> bytes | None:
        try:
            return self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        except self._s3.exceptions.NoSuchKey:
            return None

    def put(self, key: str, body: bytes) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=body, ContentType="application/json")


def cache_key(lat: float, lon: float, start: int, end: int) -> str:
    """Clave por coordenadas exactas del cuadro, periodo y parámetros consultados."""
    query = f"{lat!r}|{lon!r}|{start}|{end}|{','.join(PARAMETERS)}|AG|UTC"
    digest = hashlib.sha256(query.encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}{lat:g}_{lon:g}_{start}-{end}_{digest}.json"


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response:  # noqa: S310 (URL fija)
        return response.read()


class PowerClient:
    """Descarga y guarda la respuesta diaria de un cuadro POWER."""

    def __init__(
        self,
        cache: RawCache,
        *,
        first_year: int = 2016,
        last_year: int | None = None,
        download: Callable[[str], bytes] = _download,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._cache = cache
        self._first_year = first_year
        # El último año completo: POWER publica con unos días de retraso.
        self._last_year = last_year or date.today().year - 1
        self._download = download
        self._sleep = sleep

    def url(self, lat: float, lon: float) -> str:
        query = {
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "latitude": repr(lat),
            "longitude": repr(lon),
            "start": f"{self._first_year}0101",
            "end": f"{self._last_year}1231",
            "format": "JSON",
            "time-standard": "UTC",
        }
        return f"{ENDPOINT}?{urllib.parse.urlencode(query)}"

    def raw(self, lat: float, lon: float) -> dict:
        key = cache_key(lat, lon, self._first_year, self._last_year)
        cached = self._cache.get(key)
        if cached is not None:
            logger.info("POWER %s,%s desde caché", lat, lon)
            return json.loads(cached)
        url = self.url(lat, lon)
        body = None
        for attempt in (1, 2):
            try:
                body = self._download(url)
                break
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                logger.warning("POWER %s,%s intento %d falló: %s", lat, lon, attempt, error)
                if attempt == 1:
                    self._sleep(RETRY_PAUSE_S)
        if body is None:
            raise PowerUnavailableError(f"NASA POWER no respondió para {lat},{lon}")
        document = json.loads(body)
        if "properties" not in document:
            raise PowerUnavailableError(f"Respuesta de NASA POWER sin datos: {body[:200]!r}")
        self._cache.put(key, body)
        logger.info("POWER %s,%s descargado y guardado en %s", lat, lon, key)
        return document


def _value(series: dict, day: str) -> float | None:
    value = series.get(day)
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) or number <= _FILL else number


def to_daily_rows(
    document: dict, cell: Cell, lapse_rate_c_per_km: float = DEFAULT_LAPSE_RATE_C_PER_KM
) -> tuple[tuple[DailyRow, ...], bool]:
    """Filas diarias de la celda y si las temperaturas llevan la corrección por altura.

    `t_adj = t − tasa × (elevación de la celda − elevación del cuadro) / 1000`. Si falta
    alguna elevación, las temperaturas ajustadas son las originales.
    """
    parameters = document["properties"]["parameter"]
    coordinates = document.get("geometry", {}).get("coordinates", [])
    box_elevation = coordinates[2] if len(coordinates) > 2 else None
    if box_elevation is None or cell.cell_elev_m is None:
        offset, adjusted = 0.0, False
    else:
        offset = -lapse_rate_c_per_km * (cell.cell_elev_m - float(box_elevation)) / 1000
        adjusted = True

    def shifted(value: float | None) -> float | None:
        return None if value is None else round(value + offset, 6)

    rows = []
    for day in sorted(parameters["T2M_MAX"]):
        tmax = _value(parameters["T2M_MAX"], day)
        tmin = _value(parameters["T2M_MIN"], day)
        tmean = _value(parameters["T2M"], day)
        rows.append(
            DailyRow(
                cell_id=cell.cell_id,
                zone_id=cell.zone_id,
                date=f"{day[:4]}-{day[4:6]}-{day[6:]}",
                tmax_c=tmax,
                tmin_c=tmin,
                tmean_c=tmean,
                tmax_adj_c=shifted(tmax),
                tmin_adj_c=shifted(tmin),
                tmean_adj_c=shifted(tmean),
                temp_adj_applied=adjusted,
                precip_mm=_value(parameters["PRECTOTCORR"], day),
                rad_mj_m2=_value(parameters["ALLSKY_SFC_SW_DWN"], day),
                rh_pct=_value(parameters["RH2M"], day),
                wind_ms=_value(parameters["WS2M"], day),
                wind_max_ms=_value(parameters["WS10M_MAX"], day),
                gwetroot_frac=None,
            )
        )
    return tuple(rows), adjusted


class PowerDailySource:
    """Serie diaria de una celda a partir de su cuadro POWER."""

    def __init__(
        self, client: PowerClient, lapse_rate_c_per_km: float = DEFAULT_LAPSE_RATE_C_PER_KM
    ):
        self._client = client
        self._lapse_rate = lapse_rate_c_per_km

    def daily(self, cell: Cell) -> tuple[tuple[DailyRow, ...], bool]:
        document = self._client.raw(cell.power_cell_lat, cell.power_cell_lon)
        return to_daily_rows(document, cell, self._lapse_rate)
