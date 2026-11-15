"""Comparación de estrategias de rotación, el resultado central del reto."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.api.schemas.common import (
    Confidence,
    MonthDay,
    RequestModel,
    ResponseModel,
    Scenario,
    ScenarioApplied,
)
from app.api.schemas.fields import Season

Weight = Annotated[int, Field(ge=0, le=5)]
PriorityScore = Annotated[float, Field(ge=0, le=5)]


class Priorities(RequestModel):
    """Pesos de 0 a 5 que el agricultor asigna a cada prioridad."""

    save_water: Weight = 3
    income: Weight = 3
    soil_health: Weight = 3
    forage: Weight = 3
    pest_break: Weight = 3
    low_labor: Weight = 3


class Constraints(RequestModel):
    irrigation_mm_per_year: float | None = Field(default=None, ge=0)
    equipment: list[str] = Field(default_factory=list, max_length=30)
    exclude_crops: list[str] = Field(default_factory=list, max_length=50)
    horizon_years: int = Field(default=4, ge=1, le=6)


class RotationRequest(RequestModel):
    priorities: Priorities = Field(default_factory=Priorities)
    constraints: Constraints = Field(default_factory=Constraints)
    scenario: Scenario = Field(default_factory=Scenario)
    max_strategies: int = Field(default=4, ge=3, le=6)


class SequenceStep(ResponseModel):
    year: int = Field(ge=1)
    season: Season
    crop_id: str | None = Field(description="`null` = suelo desnudo")
    role: str = Field(examples=["cash", "legume", "cover", "forage", "bare"])
    plant: MonthDay | None = None
    harvest: MonthDay | None = None


class StrategyMetrics(ResponseModel):
    water_demand_mm_per_year: float
    irrigation_need_mm_per_year: float
    n_balance_kg_ha_per_year: float
    om_trend: Literal["declining", "stable", "improving"]
    erosion_exposure_index: float = Field(
        ge=0, description="Decenas descubiertas × probabilidad de lluvia intensa"
    )
    bare_soil_days_per_year: float = Field(ge=0)
    pest_break_score: float
    gross_margin_index: float | None


class StrategyScores(ResponseModel):
    save_water: PriorityScore
    income: PriorityScore | None = Field(
        description="`null` si el catálogo no trae índice de margen"
    )
    soil_health: PriorityScore
    forage: PriorityScore
    pest_break: PriorityScore
    low_labor: PriorityScore
    overall: float = Field(ge=0, le=100)


class Evidence(ResponseModel):
    claim: str
    source_id: str | None


class Strategy(ResponseModel):
    id: str
    name: str
    is_current: bool
    sequence: list[SequenceStep]
    metrics: StrategyMetrics
    scores: StrategyScores
    why: list[str]
    evidence: list[Evidence]
    benefits: list[str]
    gaps: list[str]
    risks_local_review: list[str]
    confidence: Confidence


class RotationResponse(ResponseModel):
    scenario: ScenarioApplied
    strategies: list[Strategy] = Field(min_length=3)
    recommended_id: str
    disclaimer: str

    @model_validator(mode="after")
    def includes_current_and_recommended(self):
        if not any(strategy.is_current for strategy in self.strategies):
            raise ValueError("strategies debe incluir la rotación actual")
        if self.recommended_id not in {strategy.id for strategy in self.strategies}:
            raise ValueError("recommended_id debe ser una de las estrategias")
        return self
