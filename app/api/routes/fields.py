"""Geocercas e invernaderos de un cliente."""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.api.deps import ClientId, Locate, Repo
from app.api.errors import ApiError
from app.api.schemas.common import ErrorResponse
from app.api.schemas.fields import Field, FieldCreate, FieldUpdate
from app.geo.locate import Location
from app.store.base import Repository
from app.store.ids import new_field_id

FIELD_PREFIX = "field#"
FIELD_LIMIT = 50
_FIELD_ID = re.compile(r"^fld_[0-9A-HJKMNP-TV-Z]{26}$")

_CLIENT_ERRORS = {400: {"model": ErrorResponse, "description": "Falta `X-Client-Id` o no es UUID"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "No existe para este cliente"}}

router = APIRouter(prefix="/fields", tags=["fields"], responses=_CLIENT_ERRORS)


def load_field(repo: Repository, client_id: str, field_id: str) -> dict:
    """Documento de la geocerca del cliente; `not_found` también si es de otro cliente."""
    document = repo.get(client_id, FIELD_PREFIX + field_id) if _FIELD_ID.match(field_id) else None
    if document is None:
        raise ApiError("not_found", 404, details={"field_id": field_id[:64]})
    return document


def _location_fields(location: Location) -> dict:
    return {
        "area_ha": location.area_ha,
        "centroid": list(location.centroid),
        "cell_id": location.cell_id,
        "zone_id": location.zone_id,
        "cell_assignment": location.cell_assignment,
        "country": location.country,
        "admin": {"state": location.state, "municipality": location.municipality},
    }


def _save(repo: Repository, client_id: str, document: dict) -> Field:
    field = Field.model_validate(document)
    repo.put(
        client_id,
        FIELD_PREFIX + field.id,
        field.model_dump(mode="json"),
        attributes={
            "cell_id": field.cell_id,
            "kind": field.kind,
            "created_at": document["created_at"],
        },
    )
    return field


@router.post(
    "",
    response_model=Field,
    status_code=201,
    summary="Crear una geocerca o un invernadero",
    responses={409: {"model": ErrorResponse, "description": "Tope de geocercas alcanzado"}},
)
def create_field(body: FieldCreate, client_id: ClientId, repo: Repo, locate: Locate):
    location = locate(body.geometry.model_dump())
    if repo.count_prefix(client_id, FIELD_PREFIX) >= FIELD_LIMIT:
        raise ApiError(
            "field_limit_reached",
            409,
            details={"limit": FIELD_LIMIT},
            params={"limit": FIELD_LIMIT},
        )
    document = {
        "id": new_field_id(),
        **body.model_dump(mode="json"),
        **_location_fields(location),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile_status": "ready",
    }
    return _save(repo, client_id, document)


@router.get("", response_model=list[Field], summary="Listar las geocercas del cliente")
def list_fields(client_id: ClientId, repo: Repo):
    return repo.list_prefix(client_id, FIELD_PREFIX, newest_first=True)


@router.get("/{field_id}", response_model=Field, summary="Detalle", responses=_NOT_FOUND)
def get_field(field_id: str, client_id: ClientId, repo: Repo):
    return load_field(repo, client_id, field_id)


@router.patch(
    "/{field_id}", response_model=Field, summary="Editar los campos enviados", responses=_NOT_FOUND
)
def update_field(field_id: str, body: FieldUpdate, client_id: ClientId, repo: Repo, locate: Locate):
    document = load_field(repo, client_id, field_id)
    changes = body.model_dump(mode="json", exclude_unset=True)
    if "geometry" in changes:
        # Si la geometría nueva no es válida o cae fuera de cobertura, no se guarda nada.
        changes.update(_location_fields(locate(changes["geometry"])))
    document.update(changes)
    if document["kind"] == "greenhouse" and document.get("greenhouse") is None:
        raise ApiError(
            "validation_error",
            422,
            details={
                "fields": [
                    {
                        "field": "body.greenhouse",
                        "type": "missing",
                        "message": "greenhouse es obligatorio cuando kind es greenhouse",
                    }
                ]
            },
        )
    return _save(repo, client_id, document)


@router.delete("/{field_id}", status_code=204, summary="Borrar", responses=_NOT_FOUND)
def delete_field(field_id: str, client_id: ClientId, repo: Repo):
    if not (_FIELD_ID.match(field_id) and repo.delete(client_id, FIELD_PREFIX + field_id)):
        raise ApiError("not_found", 404, details={"field_id": field_id[:64]})
    return Response(status_code=204)
