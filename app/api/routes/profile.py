"""Perfil agroclimático de la zona de una geocerca."""

from fastapi import APIRouter

from app.api.deps import ClientId, Language, Profiles, Repo
from app.api.routes.fields import load_field
from app.api.schemas.common import ErrorResponse
from app.api.schemas.profile import FieldProfile
from app.data import DataUnavailableError, UnknownCellError
from app.engines.suitability import LAB_SOURCE
from app.i18n import translate

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
    return with_lab({**profile, "field_id": field["id"]}, field.get("soil_lab"), language)


def with_lab(profile: dict, lab: dict | None, language: str) -> dict:
    """Añade el análisis de laboratorio del agricultor al perfil de la zona."""
    if not lab:
        return profile
    soil = dict(
        profile["soil"]
        or {"source_id": "soilgrids", "texture_class": None, "layers": [], "k_factor": None}
    )
    soil["lab"] = {
        "source_id": LAB_SOURCE,
        "lab": lab.get("lab"),
        "sample_date": lab.get("sample_date"),
        "depth_cm": lab.get("depth_cm"),
        "texture": lab.get("texture"),
        **lab["values"],
    }
    soil["confidence"] = "high"
    return {
        **profile,
        "soil": soil,
        "sources": [*profile["sources"], lab_source(lab, language)],
        "gaps": [
            gap for gap in profile["gaps"] if gap["code"] not in {"no_lab_analysis", "no_soil_data"}
        ],
    }


def lab_source(lab: dict, language: str) -> dict:
    return {
        "id": LAB_SOURCE,
        "name": translate("soil.lab_source", language),
        "organization": lab.get("lab") or translate("soil.lab_unknown", language),
        "product": translate("soil.lab_product", language),
        "url": "",
        "resolution": translate("soil.lab_resolution", language),
        "period": lab.get("sample_date") or lab["uploaded_at"][:10],
        "license": translate("soil.lab_license", language),
        "data_class": "observation",
    }
