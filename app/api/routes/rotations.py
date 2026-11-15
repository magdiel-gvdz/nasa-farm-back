"""Comparación de estrategias de rotación."""

from fastapi import APIRouter

from app.api.deps import ClientId, Crops, Data, Engine, Language, Repo
from app.api.errors import ApiError
from app.api.routes.fields import load_field
from app.api.routes.suitability import cell_data, field_context
from app.api.schemas.common import ErrorResponse
from app.api.schemas.rotations import RotationRequest, RotationResponse
from app.engines.rotation import (
    Constraints,
    CurrentRotationRequiredError,
    UnknownCropError,
    compare,
)
from app.engines.suitability import FieldContext

router = APIRouter(
    prefix="/fields",
    tags=["rotations"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
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
    data: Data,
    catalog: Crops,
    engine: Engine,
):
    field = load_field(repo, client_id, field_id)
    context = field_context(field, language)
    limit = body.constraints.irrigation_mm_per_year
    if limit is not None:
        # El límite de la petición sustituye al riego declarado en la geocerca.
        context = FieldContext(irrigation_declared=True, irrigation_mm=limit, language=language)
    elif context.irrigation_declared:
        limit = context.irrigation_mm
    try:
        result = compare(
            catalog=catalog,
            cell_data=cell_data(data, field["cell_id"]),
            field_context=context,
            config=engine,
            current_rotation=field.get("current_rotation"),
            constraints=Constraints(
                exclude_crops=frozenset(body.constraints.exclude_crops),
                equipment=frozenset(body.constraints.equipment),
                has_livestock=field.get("livestock") is not None,
            ),
            weights=body.priorities.model_dump(),
            irrigation_limit_mm=limit,
            horizon_years=body.constraints.horizon_years,
            max_strategies=body.max_strategies,
        )
    except CurrentRotationRequiredError:
        raise ApiError("current_rotation_required", 422) from None
    except UnknownCropError as error:
        raise ApiError("crop_not_found", 404, details={"crop_id": error.crop_id}) from None
    return {**result, "scenario": body.scenario.model_dump()}
