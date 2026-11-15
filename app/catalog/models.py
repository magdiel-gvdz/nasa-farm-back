"""Modelo de un cultivo del catálogo: lo que necesita y lo que aporta.

El esquema está congelado para los motores (`d2`, `d3`) y el chat (`e2`): añadir campos es
compatible; renombrarlos no. La definición y unidad de cada campo está en
docs/crop-catalog.md.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

CropRole = Literal["cash", "legume", "cover", "forage", "deep_root", "drought_tolerant"]
CropFamily = Literal[
    "poaceae",
    "fabaceae",
    "solanaceae",
    "cucurbitaceae",
    "brassicaceae",
    "amaranthaceae",
    "asteraceae",
    "malvaceae",
    "amaryllidaceae",
    "apiaceae",
    "rosaceae",
    "juglandaceae",
    "vitaceae",
]
Residue = Literal["low", "medium", "high"]
RootDepth = Literal["shallow", "medium", "deep"]
Equipment = Literal[
    "tractor",
    "planter",
    "seed_drill",
    "combine",
    "forage_harvester",
    "baler",
    "manual_harvest",
]

# Roles sin los que el motor de rotaciones no puede armar una estrategia.
REQUIRED_ROLES: tuple[CropRole, ...] = ("cash", "legume", "cover", "forage", "drought_tolerant")


def _ordered(value: tuple[float, float]) -> tuple[float, float]:
    if value[0] > value[1]:
        raise ValueError(f"el mínimo ({value[0]}) es mayor que el máximo ({value[1]})")
    return value


IntRange = Annotated[tuple[int, int], AfterValidator(_ordered)]
FloatRange = Annotated[tuple[float, float], AfterValidator(_ordered)]
CropCoefficient = Annotated[float, Field(gt=0, le=1.5)]


class CatalogModel(BaseModel):
    # Una clave mal escrita en el YAML es un error, no un campo que se ignora.
    model_config = ConfigDict(extra="forbid")


class LocalizedName(CatalogModel):
    es: str = Field(min_length=1)
    en: str = Field(min_length=1)


class CropCoefficients(CatalogModel):
    """Coeficientes de cultivo de FAO-56 por etapa."""

    ini: CropCoefficient
    mid: CropCoefficient
    end: CropCoefficient


class Crop(CatalogModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: LocalizedName
    family: CropFamily
    roles: list[CropRole] = Field(min_length=1)
    cycle_days: IntRange = Field(description="Días de siembra a cosecha: mínimo y máximo")
    temp_opt_c: FloatRange = Field(description="Temperatura media óptima")
    temp_abs_c: FloatRange = Field(description="Temperaturas límite que el cultivo soporta")
    frost_tolerant: bool
    heat_critical_c: float = Field(description="Tmax a partir de la cual el cultivo sufre daño")
    water_need_mm: FloatRange = Field(description="Agua por ciclo")
    ph: FloatRange
    kc: CropCoefficients
    n_fixing: bool
    n_balance_kg_ha: float = Field(
        description="Balance aproximado de nitrógeno por ciclo; positivo si el cultivo aporta"
    )
    residue: Residue = Field(description="Rastrojo que deja en el suelo")
    root_depth: RootDepth
    equipment: list[Equipment]
    margin_index: float | None = Field(
        default=None, ge=0, description="Margen relativo entre cultivos; sin unidad"
    )
    source_id: str = Field(min_length=1, description="Fuente bibliográfica de los valores")
    reviewed: bool = Field(description="Si el rol científico revisó los valores")

    @model_validator(mode="after")
    def _consistent(self) -> "Crop":
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("roles: hay roles repetidos")
        if self.cycle_days[0] <= 0:
            raise ValueError("cycle_days: el ciclo debe durar al menos un día")
        if self.ph[0] < 0 or self.ph[1] > 14:
            raise ValueError("ph: debe estar entre 0 y 14")
        if self.temp_abs_c[0] > self.temp_opt_c[0] or self.temp_abs_c[1] < self.temp_opt_c[1]:
            raise ValueError("temp_abs_c: debe contener el rango óptimo temp_opt_c")
        if "legume" in self.roles and not (self.n_fixing and self.n_balance_kg_ha > 0):
            raise ValueError(
                "n_fixing: una leguminosa debe fijar nitrógeno y tener n_balance_kg_ha positivo"
            )
        return self
