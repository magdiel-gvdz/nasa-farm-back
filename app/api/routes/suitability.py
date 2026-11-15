"""Aptitud de cultivos: "¿puedo sembrar X en el mes Y?"."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ClientId, Crops, Data, Engine, Language, Repo
from app.api.errors import ApiError
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix
from app.data import DataProvider, DataUnavailableError, UnknownCellError
from app.engines.suitability import (
    CellData,
    Evaluation,
    FieldContext,
    evaluate,
    evaluate_matrix,
)

router = APIRouter(
    prefix="/fields",
    tags=["suitability"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


def cell_data(provider: DataProvider, cell_id: str) -> CellData:
    try:
        return CellData(climatology=provider.climatology(cell_id), soil=provider.soil(cell_id))
    except UnknownCellError:
        raise DataUnavailableError(f"Sin datos para la celda {cell_id}") from None


def field_context(field: dict, language: str) -> FieldContext:
    irrigation = field.get("irrigation")
    if irrigation is None:
        return FieldContext(irrigation_declared=False, irrigation_mm=0.0, language=language)
    available = irrigation.get("max_mm_per_year") if irrigation["available"] else 0.0
    return FieldContext(irrigation_declared=True, irrigation_mm=available, language=language)


def detail_response(evaluation: Evaluation) -> dict:
    return {
        "crop_id": evaluation.crop_id,
        "planting_month": evaluation.planting_month,
        "status": evaluation.status,
        "score": evaluation.score,
        "harvest_window": {
            "from": evaluation.harvest_window[0],
            "to": evaluation.harvest_window[1],
        },
        "reasons": [
            {
                "factor": reason.factor,
                "status": reason.status,
                "detail": reason.detail,
                "source_id": reason.source_id,
            }
            for reason in evaluation.reasons
        ],
        "confidence": evaluation.confidence,
    }


@router.get(
    "/{field_id}/suitability",
    response_model=SuitabilityDetail | SuitabilityMatrix,
    response_model_by_alias=True,
    summary="Matriz cultivo × mes, o el detalle si se envían crop_id y planting_month",
)
def get_suitability(
    field_id: str,
    client_id: ClientId,
    repo: Repo,
    language: Language,
    data: Data,
    catalog: Crops,
    engine: Engine,
    crop_id: Annotated[str | None, Query(max_length=60)] = None,
    planting_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    delta_t_c: Annotated[float, Query(ge=-10, le=10)] = 0,
    delta_p_pct: Annotated[float, Query(ge=-100, le=100)] = 0,
):
    field = load_field(repo, client_id, field_id)
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
    crop = catalog.get(crop_id) if crop_id is not None else None
    if crop_id is not None and crop is None:
        raise ApiError("crop_not_found", 404, details={"crop_id": crop_id})
    cell = cell_data(data, field["cell_id"])
    context = field_context(field, language)
    if crop is not None:
        evaluation = evaluate(crop, planting_month, cell, context, config=engine.suitability)
        return detail_response(evaluation)
    matrix = evaluate_matrix(list(catalog), cell, context, config=engine.suitability)
    return {
        "months": list(range(1, 13)),
        "crops": [
            {
                "crop_id": crop_id,
                "scores": [evaluation.score for evaluation in evaluations],
                "status": [evaluation.status for evaluation in evaluations],
            }
            for crop_id, evaluations in matrix.items()
        ],
    }
