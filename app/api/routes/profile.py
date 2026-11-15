"""Perfil agroclimático de la zona de una geocerca."""

from fastapi import APIRouter, Response

from app.api.deps import ClientId, Language, Repo
from app.api.fixtures import load_fixture, mark_mock
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.profile import FieldProfile

router = APIRouter(
    prefix="/fields",
    tags=["profile"],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)


@router.get(
    "/{field_id}/profile",
    response_model=FieldProfile,
    summary="Perfil de la zona (celda de 9 km), en una sola llamada",
)
def get_profile(
    field_id: str, client_id: ClientId, repo: Repo, language: Language, response: Response
):
    field = load_field(repo, client_id, field_id)
    mark_mock(response)
    return {**load_fixture("profile", language), "field_id": field["id"]}
