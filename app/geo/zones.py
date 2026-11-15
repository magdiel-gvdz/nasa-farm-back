"""Zonas piloto y catálogo de celdas publicadas.

Hasta que exista el proveedor de datos (`c1-data-provider`) el catálogo se deriva de los
recuadros de docs/fuentes_de_datos.md §2 con la regla de DATA: una celda pertenece a una zona
cuando su centroide cae dentro del recuadro. Eso reproduce las 136 celdas publicadas.
"""

from dataclasses import dataclass
from typing import Protocol

from app.geo import grid


@dataclass(frozen=True)
class Zone:
    zone_id: str
    name: str
    state: str
    country: str
    municipalities: tuple[str, ...]
    bbox: tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max


PILOT_ZONES: tuple[Zone, ...] = (
    Zone(
        "coah-sureste",
        "Sureste",
        "Coahuila",
        "MX",
        ("Saltillo", "Arteaga", "General Cepeda"),
        (-101.6, 25.2, -100.7, 25.6),
    ),
    Zone(
        "coah-laguna",
        "La Laguna",
        "Coahuila",
        "MX",
        ("Torreón", "Matamoros", "Francisco I. Madero", "San Pedro"),
        (-103.5, 25.45, -102.9, 25.85),
    ),
    Zone(
        "coah-norte",
        "Norte (Cinco Manantiales)",
        "Coahuila",
        "MX",
        ("Allende", "Nava", "Morelos", "Zaragoza"),
        (-101.0, 28.15, -100.6, 28.55),
    ),
    Zone(
        "coah-centro",
        "Centro-Desierto",
        "Coahuila",
        "MX",
        ("Cuatro Ciénegas", "San Buenaventura", "Frontera"),
        (-102.2, 26.85, -101.4, 27.15),
    ),
)


class CellCatalog(Protocol):
    """Qué celdas están publicadas y a qué zona pertenecen."""

    def zones(self) -> tuple[Zone, ...]: ...

    def zone_of(self, cell_id: str) -> Zone | None: ...


class BBoxCellCatalog:
    """Catálogo fijo calculado desde los recuadros de las zonas."""

    def __init__(self, zones: tuple[Zone, ...] = PILOT_ZONES):
        self._zones = zones
        self._by_cell: dict[str, Zone] = {}
        for zone in zones:
            for row, col in grid.cells_in_bbox(*zone.bbox):
                self._by_cell.setdefault(grid.cell_id(row, col), zone)

    def zones(self) -> tuple[Zone, ...]:
        return self._zones

    def zone_of(self, cell_id: str) -> Zone | None:
        return self._by_cell.get(cell_id)

    def cell_ids(self) -> list[str]:
        return sorted(self._by_cell)


class ProviderCellCatalog:
    """Celdas y regiones que publica DATA, leídas del proveedor de datos activo.

    Las regiones de DATA son rectángulos aproximados y la malla incluye celdas de estados
    vecinos: `zone_id` es una etiqueta para agrupar, no un dato administrativo.
    """

    def __init__(self, provider, state: str = "Coahuila", country: str = "MX"):
        self._provider = provider
        self._state = state
        self._country = country

    def _zone(self, zone_id: str, name: str, cells) -> Zone:
        lons = [cell.lon for cell in cells]
        lats = [cell.lat for cell in cells]
        bbox = (min(lons), min(lats), max(lons), max(lats))
        return Zone(zone_id, name, self._state, self._country, (), bbox)

    def zones(self) -> tuple[Zone, ...]:
        by_zone: dict[str, list] = {}
        for cell in self._provider.cells():
            by_zone.setdefault(cell.zone_id, []).append(cell)
        return tuple(
            self._zone(zone_id, cells[0].zone_name, cells) for zone_id, cells in by_zone.items()
        )

    def zone_of(self, cell_id: str) -> Zone | None:
        from app.data import UnknownCellError

        try:
            cell = self._provider.cell(cell_id)
        except UnknownCellError:
            return None
        return Zone(cell.zone_id, cell.zone_name, self._state, self._country, (), (0, 0, 0, 0))
