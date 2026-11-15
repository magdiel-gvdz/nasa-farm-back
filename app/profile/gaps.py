"""Vacíos de información del perfil: lo que los datos no permiten afirmar.

Cada regla produce un código estable; el texto sale del catálogo de `app/i18n.py` con la
clave `profile.gap.<código>` y siempre habla de la zona (celda de 9 km), no de la parcela.
"""

from dataclasses import dataclass

from app.data.models import Cell
from app.i18n import translate

ELEVATION_MISMATCH_M = 300

# Código → severidad. Es la lista completa de códigos que puede traer `gaps`.
GAP_SEVERITY = {
    "zonal_resolution_9km": "medium",
    "no_lab_analysis": "low",
    "synthetic_data": "high",
    "shared_climate_series": "medium",
    "elevation_mismatch": "medium",
    "soil_moisture_from_model": "low",
    "ndvi_not_available": "medium",
    "no_soil_data": "high",
    "no_elevation_data": "low",
    "no_wind_data": "low",
    "no_daily_series": "low",
    "no_slope_data": "low",
    "no_groundwater_source": "medium",
    "no_light_data": "low",
    "no_land_use_history": "low",
    "no_hail_product": "medium",
}


@dataclass(frozen=True)
class ProfileFacts:
    """Lo que las reglas necesitan saber del perfil ya construido."""

    cell: Cell
    synthetic: bool
    soil_moisture_source: str | None
    has_soil: bool
    has_vegetation: bool
    has_wind: bool
    has_daily: bool


def _gap(code: str, language: str, **params) -> dict:
    return {
        "code": code,
        "severity": GAP_SEVERITY[code],
        "message": translate(f"profile.gap.{code}", language, **params),
    }


def build_gaps(facts: ProfileFacts, language: str) -> list[dict]:
    cell = facts.cell
    gaps = [_gap("zonal_resolution_9km", language), _gap("no_lab_analysis", language)]
    if facts.synthetic:
        gaps.append(_gap("synthetic_data", language))
    if cell.climate_shared_by_n_cells > 1:
        gaps.append(_gap("shared_climate_series", language, n_cells=cell.climate_shared_by_n_cells))
    if cell.cell_elev_m is None:
        gaps.append(_gap("no_elevation_data", language))
    else:
        difference = abs(cell.cell_elev_m - cell.power_elev_m)
        if difference > ELEVATION_MISMATCH_M:
            gaps.append(_gap("elevation_mismatch", language, difference_m=round(difference)))
    if facts.soil_moisture_source != "smap_l4":
        gaps.append(_gap("soil_moisture_from_model", language))
    if not facts.has_vegetation:
        gaps.append(_gap("ndvi_not_available", language))
    if not facts.has_soil:
        gaps.append(_gap("no_soil_data", language))
    if not facts.has_wind:
        gaps.append(_gap("no_wind_data", language))
    if not facts.has_daily:
        gaps.append(_gap("no_daily_series", language))
    # Secciones que el MVP nunca tiene.
    for code in (
        "no_slope_data",
        "no_groundwater_source",
        "no_light_data",
        "no_land_use_history",
        "no_hail_product",
    ):
        gaps.append(_gap(code, language))
    return gaps
