"""Aptitud de cultivos: "¿puedo sembrar X en el mes Y?"."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import ClientId, Language, Repo
from app.api.errors import ApiError
from app.api.fixtures import load_fixture, mark_mock
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix

router = APIRouter(
    prefix="/fields",
    tags=["suitability"],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)


@router.get(
    "/{field_id}/suitability",
    response_model=SuitabilityDetail | SuitabilityMatrix,
    summary="Matriz cultivo × mes, o el detalle si se envían crop_id y planting_month",
)
def get_suitability(
    field_id: str,
    client_id: ClientId,
    repo: Repo,
    language: Language,
    response: Response,
    crop_id: Annotated[str | None, Query(max_length=60)] = None,
    planting_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    delta_t_c: Annotated[float, Query(ge=-10, le=10)] = 0,
    delta_p_pct: Annotated[float, Query(ge=-100, le=100)] = 0,
):
    load_field(repo, client_id, field_id)
    if (crop_id is None) != (planting_month is None):
        missing = "planting_month" if planting_month is None else "crop_id"
        raise ApiError(
            "validation_error",
            422,
            details={
                "fields": [
                    {
                        "field": f"query.{missing}",
                        "type": "missing",
                        "message": "crop_id y planting_month se envían juntos",
                    }
                ]
            },
        )
    mark_mock(response)
    if crop_id is None:
        return load_fixture("suitability_matrix", language)
    detail = load_fixture("suitability_detail", language)
    return {**detail, "crop_id": crop_id, "planting_month": planting_month}
