"""Riesgo de viento para la estructura de un invernadero."""

from typing import Literal

from pydantic import Field

from app.api.schemas.common import Confidence, Gap, Month, Probability, ResponseModel
from app.api.schemas.fields import Greenhouse


class ReturnLevel(ResponseModel):
    return_period_years: int
    sustained_kmh: float = Field(description="Máximo de medias horarias del modelo")
    estimated_gust_kmh: float = Field(description="Sostenido × `gust_factor_assumed`")


class GreenhouseWind(ResponseModel):
    source_id: str
    daily_origin: str | None
    years_used: int = Field(description="Años completos con dato de viento")
    gust_factor_assumed: float
    return_levels_kmh: list[ReturnLevel] | None = Field(
        description="10, 25 y 50 años; `null` si el registro es demasiado corto"
    )
    rated_wind_kmh: float | None
    annual_exceedance_probability: Probability | None = Field(
        description="Probabilidad anual de que la ráfaga estimada supere la resistencia"
    )
    status: Literal["ok", "warn", "bad"] | None
    riskiest_months: list[Month]
    note: str


class GreenhouseAssessment(ResponseModel):
    field_id: str
    cell_id: str
    structure: Greenhouse
    wind: GreenhouseWind
    light: None = Field(default=None, description="Fuera de alcance; ver `gaps`")
    heating: None = None
    co2: None = None
    hail: None = None
    recommendations: list[str]
    confidence: Confidence
    gaps: list[Gap]
