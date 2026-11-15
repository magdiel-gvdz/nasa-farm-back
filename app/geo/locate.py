"""Sitúa una geocerca en la malla de análisis y en las zonas cubiertas."""

from dataclasses import dataclass
from typing import Protocol

from app.geo import grid
from app.geo.geometry import MAX_AREA_HA, GeometryError, area_ha, centroid, parse_geometry
from app.geo.zones import CellCatalog, Zone


@dataclass(frozen=True)
class Location:
    area_ha: float
    centroid: tuple[float, float]  # lon, lat
    cell_id: str
    zone_id: str
    country: str
    state: str
    municipality: str | None = None
    cell_assignment: str = "centroid"


class OutOfRegionError(Exception):
    """La celda de la geocerca no pertenece a ninguna zona publicada."""

    def __init__(self, cell_id: str | None, zones: tuple[Zone, ...]):
        super().__init__(cell_id)
        self.cell_id = cell_id
        self.zones = zones


class Locator(Protocol):
    def __call__(self, geometry: dict) -> Location: ...


class GridLocator:
    """Celda dominante = la que contiene el centroide de la geocerca."""

    def __init__(self, catalog: CellCatalog):
        self._catalog = catalog

    def __call__(self, geometry: dict) -> Location:
        shape = parse_geometry(geometry)
        hectares = area_ha(shape)
        if hectares > MAX_AREA_HA:
            raise GeometryError("too_large", max_area_ha=MAX_AREA_HA, area_ha=round(hectares, 1))
        lon, lat = centroid(shape)
        try:
            cell = grid.lonlat_to_cell_id(lon, lat)
        except grid.OutsideGridError:
            raise OutOfRegionError(None, self._catalog.zones()) from None
        zone = self._catalog.zone_of(cell)
        if zone is None:
            raise OutOfRegionError(cell, self._catalog.zones())
        return Location(
            area_ha=round(hectares, 4),
            centroid=(round(lon, 6), round(lat, 6)),
            cell_id=cell,
            zone_id=zone.zone_id,
            country=zone.country,
            state=zone.state,
            # Una zona abarca varios municipios; sin límites municipales no hay certeza.
            municipality=None,
        )
