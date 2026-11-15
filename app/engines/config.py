"""Carga y valida `config/engine.yaml`. La aplicación no arranca con parámetros inválidos."""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "engine.yaml"

Fraction = Annotated[float, Field(ge=0, le=1)]
Score = Annotated[float, Field(ge=0, le=100)]
Factor = Literal["frost", "heat", "water", "soil"]


class EngineConfigError(ValueError):
    """`config/engine.yaml` no se puede usar; el mensaje nombra el parámetro."""


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StatusCuts(ConfigModel):
    suitable: Score
    marginal: Score

    @model_validator(mode="after")
    def _ordered(self):
        if self.marginal >= self.suitable:
            raise ValueError("marginal debe ser menor que suitable")
        return self


class ProbabilityThresholds(ConfigModel):
    warn_prob: Fraction
    bad_prob: Fraction

    @model_validator(mode="after")
    def _ordered(self):
        if self.warn_prob >= self.bad_prob:
            raise ValueError("warn_prob debe ser menor que bad_prob")
        return self


class HeatConfig(ProbabilityThresholds):
    flowering_window: tuple[Fraction, Fraction]

    @model_validator(mode="after")
    def _window(self):
        if self.flowering_window[0] >= self.flowering_window[1]:
            raise ValueError("flowering_window debe ir de menor a mayor")
        return self


class StageFractions(ConfigModel):
    ini: Fraction
    mid: Fraction
    end: Fraction

    @model_validator(mode="after")
    def _sum(self):
        if abs(self.ini + self.mid + self.end - 1) > 1e-6:
            raise ValueError("ini, mid y end deben sumar 1")
        return self


class WaterConfig(ConfigModel):
    effective_rain_fraction: Fraction
    stage_fractions: StageFractions
    warn_deficit_fraction: Fraction
    bad_deficit_fraction: Fraction

    @model_validator(mode="after")
    def _ordered(self):
        if self.warn_deficit_fraction >= self.bad_deficit_fraction:
            raise ValueError("warn_deficit_fraction debe ser menor que bad_deficit_fraction")
        return self


class SoilConfig(ConfigModel):
    ph_tolerance: float = Field(gt=0, le=3)
    difficult_textures: list[str]


class SuitabilityConfig(ConfigModel):
    status_cuts: StatusCuts
    weights: dict[Factor, Fraction]
    exclusive_factors: list[Factor]
    exclusive_score_cap: Score
    score_at_warn: Score
    score_at_bad: Score
    frost: ProbabilityThresholds
    heat: HeatConfig
    water: WaterConfig
    soil: SoilConfig

    @model_validator(mode="after")
    def _consistent(self):
        if set(self.weights) != {"frost", "heat", "water", "soil"}:
            raise ValueError("weights debe tener frost, heat, water y soil")
        if abs(sum(self.weights.values()) - 1) > 1e-6:
            raise ValueError("weights debe sumar 1")
        if self.exclusive_score_cap >= self.status_cuts.marginal:
            raise ValueError("exclusive_score_cap debe quedar por debajo de status_cuts.marginal")
        if not self.score_at_bad < self.score_at_warn:
            raise ValueError("score_at_bad debe ser menor que score_at_warn")
        return self


Season = Literal["spring_summer", "fall_winter"]
MonthNumber = Annotated[int, Field(ge=1, le=12)]


class RotationReferences(ConfigModel):
    irrigation_mm: float = Field(gt=0)
    n_balance_low_kg_ha: float
    n_balance_high_kg_ha: float
    forage_cycles_per_year: float = Field(gt=0)
    max_cycles_per_year: float = Field(gt=1)
    margin_index: float = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self):
        if self.n_balance_low_kg_ha >= self.n_balance_high_kg_ha:
            raise ValueError("n_balance_low_kg_ha debe ser menor que n_balance_high_kg_ha")
        return self


class OrganicMatterTrend(ConfigModel):
    improving_from: Fraction
    stable_from: Fraction

    @model_validator(mode="after")
    def _ordered(self):
        if self.stable_from >= self.improving_from:
            raise ValueError("stable_from debe ser menor que improving_from")
        return self


class RotationConfig(ConfigModel):
    planting_months: dict[Season, MonthNumber]
    season_windows: dict[Season, list[MonthNumber]]
    references: RotationReferences
    om_trend: OrganicMatterTrend

    @model_validator(mode="after")
    def _seasons(self):
        seasons = {"spring_summer", "fall_winter"}
        if set(self.planting_months) != seasons or set(self.season_windows) != seasons:
            raise ValueError("planting_months y season_windows deben tener las dos temporadas")
        for season, month in self.planting_months.items():
            if month not in self.season_windows[season]:
                raise ValueError(f"planting_months.{season} debe estar en season_windows.{season}")
        return self


class GreenhouseConfig(ConfigModel):
    gust_factor: float = Field(ge=1, le=3)
    warn_probability: Fraction
    bad_probability: Fraction
    min_days_per_year: int = Field(ge=200, le=366)
    reliable_years: int = Field(ge=2)
    minimum_years: int = Field(ge=2)

    @model_validator(mode="after")
    def _ordered(self):
        if self.warn_probability >= self.bad_probability:
            raise ValueError("warn_probability debe ser menor que bad_probability")
        if self.minimum_years > self.reliable_years:
            raise ValueError("minimum_years no puede superar reliable_years")
        return self


class EngineConfig(ConfigModel):
    suitability: SuitabilityConfig
    rotation: RotationConfig
    greenhouse: GreenhouseConfig


def parse_config(document: object) -> EngineConfig:
    try:
        return EngineConfig.model_validate(document)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in detail['loc'])}: "
            f"{detail['msg'].removeprefix('Value error, ')}"
            for detail in error.errors()
        )
        raise EngineConfigError(f"config/engine.yaml no es válido: {problems}") from None


def load_config(path: Path = DEFAULT_PATH) -> EngineConfig:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise EngineConfigError(f"No se pudo leer {path}: {error}") from error
    return parse_config(document)
