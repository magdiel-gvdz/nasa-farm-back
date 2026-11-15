"""Catálogo de cultivos."""

from typing import Literal

from pydantic import Field

from app.api.schemas.common import ResponseModel

CropRole = Literal["cash", "legume", "cover", "forage", "deep_root", "drought_tolerant"]


class LocalizedName(ResponseModel):
    es: str
    en: str


class CropCoefficients(ResponseModel):
    ini: float = Field(gt=0)
    mid: float = Field(gt=0)
    end: float = Field(gt=0)


class Crop(ResponseModel):
    id: str
    name: LocalizedName
    family: str
    roles: list[CropRole] = Field(min_length=1)
    cycle_days: tuple[int, int]
    temp_opt_c: tuple[float, float]
    temp_abs_c: tuple[float, float]
    frost_tolerant: bool
    heat_critical_c: float = Field(description="Tmax a partir de la cual el cultivo sufre daño")
    water_need_mm: tuple[float, float]
    ph: tuple[float, float]
    kc: CropCoefficients
    n_fixing: bool
