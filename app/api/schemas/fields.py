"""Geocercas e invernaderos."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from pydantic import Field as F

from app.api.schemas.common import RequestModel, ResponseModel

FieldKind = Literal["field", "greenhouse"]
Season = Literal["spring_summer", "fall_winter"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


class Geometry(BaseModel):
    """GeoJSON `Polygon` o `MultiPolygon` en WGS84, posiciones `[lon, lat]`.

    El esquema solo fija la forma general; anillos, rangos, vértices y superficie se validan
    después y se informan con `invalid_geometry`.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = F(json_schema_extra={"enum": ["Polygon", "MultiPolygon"]})
    coordinates: list[Any]


class RotationSlot(RequestModel):
    year: int = F(ge=1, le=10)
    season: Season
    crop_id: ShortText | None = F(description="`null` = suelo desnudo")


class Irrigation(RequestModel):
    available: bool
    source: ShortText | None = None
    max_mm_per_year: float | None = F(default=None, ge=0)


class Livestock(RequestModel):
    species: ShortText
    head: int = F(ge=0)


class Greenhouse(RequestModel):
    structure: Literal["multitunel", "capilla", "macrotunel", "casa_sombra", "otro"]
    cover: Literal["polietileno", "policarbonato", "vidrio", "malla"]
    rated_wind_kmh: float | None = F(default=None, gt=0)
    heated: bool = False
    co2_enrichment: bool = False


class FieldCreate(RequestModel):
    name: Name
    kind: FieldKind = "field"
    geometry: Geometry
    current_rotation: list[RotationSlot] | None = F(default=None, max_length=40)
    irrigation: Irrigation | None = None
    livestock: Livestock | None = None
    greenhouse: Greenhouse | None = None

    @model_validator(mode="after")
    def greenhouse_needs_structure(self):
        if self.kind == "greenhouse" and self.greenhouse is None:
            raise ValueError("greenhouse es obligatorio cuando kind es greenhouse")
        return self


class FieldUpdate(RequestModel):
    """Solo se modifican los campos enviados; `null` borra un campo opcional."""

    name: Name | None = None
    geometry: Geometry | None = None
    current_rotation: list[RotationSlot] | None = F(default=None, max_length=40)
    irrigation: Irrigation | None = None
    livestock: Livestock | None = None
    greenhouse: Greenhouse | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self):
        for name in ("name", "geometry"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} no puede ser null")
        return self


class Admin(ResponseModel):
    state: str
    municipality: str | None


class SoilLab(ResponseModel):
    """Valores aceptados del análisis de laboratorio subido por el agricultor."""

    values: dict[str, float] = F(
        description="ph, om_pct, ec_ds_m, cec_cmol_kg, n_mg_kg, p_mg_kg, k_mg_kg"
    )
    lab: str | None
    sample_date: str | None
    depth_cm: str | None
    texture: str | None
    uploaded_at: str
    file_key: str


class UnreadableField(ResponseModel):
    field: str
    reason: Literal["missing", "out_of_range", "invalid"]


class SoilReportResult(ResponseModel):
    field_id: str
    extracted: dict[str, float | str | None] = F(
        description="Todos los campos; `null` si no se leyó"
    )
    unreadable_fields: list[UnreadableField]
    applied: bool = F(description="Si al menos un valor se guardó en la geocerca")


class Field(ResponseModel):
    id: str = F(examples=["fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A"])
    name: str
    kind: FieldKind
    geometry: Geometry
    current_rotation: list[RotationSlot] | None
    irrigation: Irrigation | None
    livestock: Livestock | None
    greenhouse: Greenhouse | None
    area_ha: float = F(gt=0)
    centroid: tuple[float, float] = F(description="`[lon, lat]`")
    cell_id: str = F(examples=["E9_r0463_c0846"])
    zone_id: str = F(examples=["coah-sureste"])
    cell_assignment: Literal["centroid"]
    country: str
    admin: Admin
    created_at: datetime
    profile_status: Literal["ready"]
    soil_lab: SoilLab | None = None
