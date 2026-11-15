"""Objetos compartidos del contrato: procedencia, vacíos, confianza, escenario y errores."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Confidence = Literal["high", "medium", "low"]
Severity = Literal["low", "medium", "high"]
# Clase de dato de DATA: observación, modelo, derivado o estimación. `synthetic` marca los
# datos de prueba que sirve la API cuando no lee los datos publicados.
DataClass = Literal["observation", "model", "derived", "estimate", "synthetic"]
Month = Annotated[int, Field(ge=1, le=12)]
MonthDay = Annotated[str, StringConstraints(pattern=r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")]
Probability = Annotated[float, Field(ge=0, le=1)]


class RequestModel(BaseModel):
    """Los cuerpos de petición rechazan claves desconocidas (p. ej. en camelCase)."""

    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    pass


class Source(ResponseModel):
    id: str
    name: str
    organization: str
    product: str
    url: str
    resolution: str
    period: str
    license: str
    data_class: DataClass


class Gap(ResponseModel):
    code: str
    severity: Severity
    message: str


DeltaT = Annotated[float, Field(ge=-2, le=5, description="Cambio de temperatura en °C")]
DeltaP = Annotated[float, Field(ge=-50, le=50, description="Cambio de lluvia en %")]


class Scenario(RequestModel):
    delta_t_c: DeltaT = 0
    delta_p_pct: DeltaP = 0


class ScenarioApplied(ResponseModel):
    """Escenario con el que se calculó la respuesta. Es hipotético, no un pronóstico."""

    delta_t_c: float
    delta_p_pct: float
    daily_origin: str | None = Field(
        description=(
            "Origen de la serie diaria: `gold`, `power_live` o `synthetic`; `null` sin escenario"
        )
    )
    not_recomputed: list[str] = Field(
        description="Indicadores que el escenario no cambia y se toman de los datos publicados"
    )
    note: str | None


class ErrorBody(ResponseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(ResponseModel):
    error: ErrorBody


def check_months(entries: list) -> list:
    """Valida que una serie mensual tenga los meses 1 a 12, una vez cada uno y en orden."""
    if [entry.month for entry in entries] != list(range(1, 13)):
        raise ValueError("se esperan 12 elementos con month de 1 a 12 en orden")
    return entries
