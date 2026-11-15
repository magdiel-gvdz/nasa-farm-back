"""Aptitud de cultivos: detalle de un caso y matriz cultivo × mes de siembra."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from app.api.schemas.common import Confidence, Month, MonthDay, ResponseModel

SuitabilityStatus = Literal["suitable", "marginal", "unsuitable"]
Score = Annotated[float, Field(ge=0, le=100)]


class HarvestWindow(ResponseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: MonthDay = Field(alias="from")
    to: MonthDay


class SuitabilityReason(ResponseModel):
    factor: str = Field(examples=["frost", "heat", "water", "soil"])
    status: Literal["ok", "warn", "bad"]
    detail: str
    source_id: str | None


class SuitabilityDetail(ResponseModel):
    crop_id: str
    planting_month: Month
    status: SuitabilityStatus
    score: Score
    harvest_window: HarvestWindow | None
    reasons: list[SuitabilityReason]
    confidence: Confidence


class CropSuitabilityRow(ResponseModel):
    crop_id: str
    scores: list[Score] = Field(min_length=12, max_length=12)
    status: list[SuitabilityStatus] = Field(min_length=12, max_length=12)


class SuitabilityMatrix(ResponseModel):
    months: list[Month] = Field(min_length=12, max_length=12)
    crops: list[CropSuitabilityRow]
