"""Riesgo de viento para geocercas de tipo invernadero."""

from fastapi import APIRouter

from app.api.deps import ClientId, Data, Engine, Language, Repo
from app.api.errors import ApiError
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.greenhouse import GreenhouseAssessment
from app.data import DataUnavailableError, UnknownCellError
from app.engines.greenhouse import assess
from app.engines.scenario import DailyUnavailableError
from app.i18n import translate

router = APIRouter(
    prefix="/fields",
    tags=["greenhouse"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
CLIMATE_SOURCE = "nasa_power"
OUT_OF_SCOPE = ("light", "heating", "co2", "hail")


@router.get(
    "/{field_id}/greenhouse",
    response_model=GreenhouseAssessment,
    summary="Riesgo de viento para la estructura de un invernadero",
)
def get_greenhouse(
    field_id: str, client_id: ClientId, repo: Repo, language: Language, data: Data, engine: Engine
):
    field = load_field(repo, client_id, field_id)
    if field.get("kind") != "greenhouse":
        raise ApiError("not_a_greenhouse", 409)
    try:
        daily = data.daily(field["cell_id"])
    except UnknownCellError:
        raise DataUnavailableError(f"Sin datos para la celda {field['cell_id']}") from None
    except DataUnavailableError as error:
        raise DailyUnavailableError(str(error)) from error
    structure = field["greenhouse"]
    result = assess(daily, structure.get("rated_wind_kmh"), engine.greenhouse, language)
    gaps = result["gaps"] + [
        {
            "code": f"no_{section}_assessment",
            "severity": "low",
            "message": translate(f"greenhouse.gap.no_{section}_assessment", language),
        }
        for section in OUT_OF_SCOPE
    ]
    return {
        "field_id": field["id"],
        "cell_id": field["cell_id"],
        "structure": structure,
        "wind": {
            **result["wind"],
            "source_id": CLIMATE_SOURCE,
            "daily_origin": getattr(daily, "origin", None),
        },
        "recommendations": result["recommendations"],
        "confidence": result["confidence"],
        "gaps": gaps,
    }
