import json
import logging
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)


class EvidenceSource(BaseModel):
    id: str
    name: str
    organization: str
    url: HttpUrl
    resolution: str
    period: str
    license: str


class DataManifest(BaseModel):
    version: str = Field(min_length=1)
    sources: list[EvidenceSource] = Field(min_length=1)


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


@lru_cache(maxsize=1)
def s3_client():
    return boto3.client(
        "s3",
        config=Config(connect_timeout=2, read_timeout=3, retries={"max_attempts": 1}),
    )


def load_manifest(settings: Settings) -> DataManifest:
    if not settings.data_lake_bucket:
        raise DataUnavailableError("Data lake is not configured")
    try:
        response = s3_client().get_object(
            Bucket=settings.data_lake_bucket, Key=settings.manifest_key
        )
        with response["Body"] as body:
            # Bound metadata reads; data arrays belong in curated Parquet, not the manifest.
            payload = body.read(1_048_577)
        if len(payload) > 1_048_576:
            raise DataUnavailableError("Data manifest exceeds the size limit")
        return DataManifest.model_validate(json.loads(payload))
    except (BotoCoreError, ClientError, ValueError, ValidationError) as exc:
        logger.warning("Data manifest unavailable: %s", type(exc).__name__)
        raise DataUnavailableError("No valid data manifest is available") from exc
