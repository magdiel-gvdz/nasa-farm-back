"""Comparación de estrategias de rotación."""

from fastapi import APIRouter, Response

from app.api.deps import ClientId, Language, Repo
from app.api.fixtures import load_fixture, mark_mock
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.rotations import RotationRequest, RotationResponse

router = APIRouter(
    prefix="/fields",
    tags=["rotations"],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)


@router.post(
    "/{field_id}/rotations",
    response_model=RotationResponse,
    summary="Al menos 3 estrategias, incluida la rotación actual",
)
def compare_rotations(
    field_id: str,
    body: RotationRequest,
    client_id: ClientId,
    repo: Repo,
    language: Language,
    response: Response,
):
    load_field(repo, client_id, field_id)
    mark_mock(response)
    return {**load_fixture("rotations", language), "scenario": body.scenario.model_dump()}
