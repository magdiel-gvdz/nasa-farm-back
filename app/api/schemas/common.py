"""Objetos compartidos del contrato: procedencia, vacíos, confianza, escenario y errores."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Confidence = Literal["high", "medium", "low"]
Severity = Literal["low", "medium", "high"]
# Clase de dato de DATA: observación, modelo, derivado o estimación.
DataClass = Literal["observation", "model", "derived", "estimate"]
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
    dataset: str
    provider: str
    resolution: str
    period: str
    url: str
    data_class: DataClass


class Gap(ResponseModel):
    code: str
    severity: Severity
    message: str


class Scenario(RequestModel):
    delta_t_c: float = Field(default=0, ge=-10, le=10)
    delta_p_pct: float = Field(default=0, ge=-100, le=100)


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
