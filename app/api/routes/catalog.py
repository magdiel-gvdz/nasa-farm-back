"""Catálogos públicos: no exigen `X-Client-Id`."""

from fastapi import APIRouter

from app.api.deps import Crops, Data
from app.api.schemas.common import Source
from app.api.schemas.crops import Crop

router = APIRouter(tags=["catalog"])


@router.get("/crops", response_model=list[Crop], summary="Catálogo de cultivos")
def list_crops(catalog: Crops):
    return list(catalog)


@router.get("/sources", response_model=list[Source], summary="Fuentes de datos del sistema")
def list_sources(data: Data):
    return [
        Source(
            id=source.source_id,
            name=source.name,
            organization=source.organization,
            product=source.product_version,
            url=source.url,
            resolution=source.resolution,
            period=source.period,
            license=source.license,
            data_class=source.data_class,
        )
        for source in data.sources()
        # DATA lista también fuentes previstas que el MVP no usa (SMAP, NDVI).
        if source.status == "in_use"
    ]
