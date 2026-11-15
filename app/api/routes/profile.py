"""Perfil agroclimático de la zona de una geocerca."""

from fastapi import APIRouter

from app.api.deps import ClientId, Language, Profiles, Repo
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.profile import FieldProfile
from app.data import DataUnavailableError, UnknownCellError

router = APIRouter(
    prefix="/fields",
    tags=["profile"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


@router.get(
    "/{field_id}/profile",
    response_model=FieldProfile,
    summary="Perfil de la zona (celda de 9 km), en una sola llamada",
)
def get_profile(
    field_id: str, client_id: ClientId, repo: Repo, language: Language, profiles: Profiles
):
    field = load_field(repo, client_id, field_id)
    try:
        profile = profiles.for_cell(field["cell_id"], language)
    except UnknownCellError:
        # La geocerca está en una zona piloto, pero los datos activos no traen su celda.
        raise DataUnavailableError(f"Sin datos para la celda {field['cell_id']}") from None
    return {**profile, "field_id": field["id"]}
