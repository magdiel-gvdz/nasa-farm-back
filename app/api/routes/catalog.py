"""Catálogos públicos: no exigen `X-Client-Id`."""

from fastapi import APIRouter, Response

from app.api.fixtures import load_fixture, mark_mock
from app.api.schemas.common import Source
from app.api.schemas.crops import Crop

router = APIRouter(tags=["catalog"])


@router.get("/crops", response_model=list[Crop], summary="Catálogo de cultivos")
def list_crops(response: Response):
    mark_mock(response)
    return load_fixture("crops")


@router.get("/sources", response_model=list[Source], summary="Fuentes de datos del sistema")
def list_sources(response: Response):
    mark_mock(response)
    return load_fixture("sources")
