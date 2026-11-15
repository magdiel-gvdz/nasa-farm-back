"""Subida del análisis de suelo de laboratorio de una geocerca."""

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from app.agent.extract import ExtractionError, accepted, normalize
from app.api.deps import ClientId, Repo
from app.api.errors import ApiError
from app.api.routes.fields import _save, load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.fields import SoilReportResult

logger = logging.getLogger(__name__)
MAX_BYTES = 10 * 1024 * 1024
# Tipo real del archivo por sus primeros bytes, no por su nombre ni su cabecera.
_SIGNATURES = (
    (b"%PDF-", "pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png", "png"),
    (b"\xff\xd8\xff", "jpeg", "jpg"),
)

router = APIRouter(
    prefix="/fields",
    tags=["soil"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


class UploadStore:
    """`uploads/<client_id>/<field_id>/` del bucket del entorno, o un directorio local."""

    def __init__(self, bucket: str = "", root: Path | None = None):
        self._bucket = bucket
        self._root = root or Path(tempfile.gettempdir()) / "fieldshift-uploads"
        if bucket:
            import boto3

            self._s3 = boto3.client("s3")

    def save(self, key: str, data: bytes, content_type: str) -> str:
        if self._bucket:
            # Privado: sin ACL pública ni URL firmada; solo lo lee la API.
            self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        else:
            path = self._root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return key

    def exists(self, key: str) -> bool:
        if self._bucket:
            try:
                self._s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except self._s3.exceptions.ClientError:
                return False
        return (self._root / key).exists()


def file_kind(data: bytes) -> tuple[str, str] | None:
    for signature, kind, extension in _SIGNATURES:
        if data.startswith(signature):
            return kind, extension
    return None


@router.post(
    "/{field_id}/soil-report",
    response_model=SoilReportResult,
    summary="Subir el análisis de suelo de laboratorio (PDF, JPG o PNG, hasta 10 MB)",
    responses={422: {"model": ErrorResponse}},
)
async def upload_soil_report(
    field_id: str,
    request: Request,
    client_id: ClientId,
    repo: Repo,
    file: Annotated[
        UploadFile, File(description="Análisis en PDF, JPG o PNG; sin datos personales")
    ],
):
    field = load_field(repo, client_id, field_id)
    extractor = request.app.state.soil_extractor
    if extractor is None:
        raise ApiError("chat_disabled", 503)
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError("file_too_large", 413, params={"max_mb": MAX_BYTES // (1024 * 1024)})
    kind = file_kind(data)
    if kind is None:
        raise ApiError("unsupported_file_type", 415)
    try:
        extraction = normalize(extractor.raw(data, kind[0]))
    except ExtractionError:
        raise ApiError("llm_unavailable", 503) from None
    if not extraction.is_soil_report:
        raise ApiError("not_a_soil_report", 422)
    uploaded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    key = request.app.state.uploads.save(
        f"uploads/{client_id}/{field['id']}/{uploaded_at.replace(':', '')}.{kind[1]}",
        data,
        "application/pdf" if kind[0] == "pdf" else f"image/{kind[0]}",
    )
    values = accepted(extraction.values)
    if values:
        field["soil_lab"] = {
            "values": values,
            "lab": extraction.values["lab"],
            "sample_date": extraction.values["sample_date"],
            "depth_cm": extraction.values["depth_cm"],
            "texture": extraction.values["texture"],
            "uploaded_at": uploaded_at,
            "file_key": key,
        }
        _save(repo, client_id, field)
    logger.info("Análisis de suelo de %s: %d valores aceptados", field["id"], len(values))
    return {
        "field_id": field["id"],
        "extracted": extraction.values,
        "unreadable_fields": extraction.unreadable,
        "applied": bool(values),
    }
