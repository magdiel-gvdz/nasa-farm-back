"""Estrategias candidatas: la rotación actual y las alternativas que salen de plantillas.

Cada plantilla transforma la rotación actual con una intención agronómica clara. No se
enumeran todas las secuencias posibles: el resultado sería difícil de explicar.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from app.catalog.loader import Catalog
from app.catalog.models import Crop
from app.engines.config import EngineConfig
from app.engines.suitability import CellData, Evaluation, FieldContext, evaluate

SEASONS = ("spring_summer", "fall_winter")
# Niveles de relajación, en orden: sin relajar, admitir cultivos marginales, variar el mes de
# siembra dentro de la temporada y, como último recurso, admitir cualquier cultivo.
STRICT, MARGINAL, ANY_MONTH, ANY_STATUS = range(4)
_ALLOWED_STATUS = {
    STRICT: {"suitable"},
    MARGINAL: {"suitable", "marginal"},
    ANY_MONTH: {"suitable", "marginal"},
    ANY_STATUS: {"suitable", "marginal", "unsuitable"},
}


class CurrentRotationRequiredError(ValueError):
    """La geocerca no declara una rotación actual con al menos un cultivo."""


class UnknownCropError(KeyError):
    def __init__(self, crop_id: str):
        super().__init__(crop_id)
        self.crop_id = crop_id


@dataclass(frozen=True)
class Slot:
    """Una temporada de la secuencia. `crop` es `None` cuando el suelo queda en barbecho."""

    year: int
    season: str
    crop: Crop | None = None
    planting_month: int | None = None
    role: str = "bare"
    evaluation: Evaluation | None = None


@dataclass(frozen=True)
class Candidate:
    id: str
    slots: tuple[Slot, ...]
    is_current: bool = False
    relaxation: int = STRICT
    # Cultivo que introduce la plantilla y cultivo principal de la rotación actual.
    introduced: Crop | None = None
    main: Crop | None = None

    @property
    def years(self) -> int:
        return max(slot.year for slot in self.slots)

    @property
    def crop_slots(self) -> list[Slot]:
        return [slot for slot in self.slots if slot.crop is not None]

    def signature(self) -> tuple:
        return tuple(
            (slot.year, slot.season, slot.crop.id if slot.crop else None) for slot in self.slots
        )


@dataclass(frozen=True)
class Constraints:
    exclude_crops: frozenset[str] = frozenset()
    # Vacío = el agricultor no declaró su equipo: no se restringe.
    equipment: frozenset[str] = frozenset()
    has_livestock: bool = False


class Planner:
    """Evalúa cultivos en la celda y arma los candidatos."""

    def __init__(
        self,
        catalog: Catalog,
        cell_data: CellData,
        field_context: FieldContext,
        config: EngineConfig,
        constraints: Constraints,
    ):
        self._catalog = catalog
        self._cell = cell_data
        self._context = field_context
        self._config = config
        self._constraints = constraints
        self._evaluations: dict[tuple[str, int], Evaluation] = {}

    def evaluate(self, crop: Crop, month: int) -> Evaluation:
        key = (crop.id, month)
        if key not in self._evaluations:
            self._evaluations[key] = evaluate(
                crop, month, self._cell, self._context, config=self._config.suitability
            )
        return self._evaluations[key]

    def _planted(self, year: int, season: str, crop: Crop, role: str, month: int | None = None):
        month = month or self._config.rotation.planting_months[season]
        return Slot(year, season, crop, month, role, self.evaluate(crop, month))

    # ------------------------------------------------------------ rotación actual

    def current(self, rotation: Sequence[dict] | None) -> Candidate:
        """Normaliza la rotación declarada: años completos, dos temporadas y barbechos."""
        declared = {
            (entry["year"], entry["season"]): entry.get("crop_id") for entry in rotation or []
        }
        if not any(declared.values()):
            raise CurrentRotationRequiredError
        years = sorted({year for year, _ in declared})
        slots = []
        for position, year in enumerate(years, start=1):
            for season in SEASONS:
                crop_id = declared.get((year, season))
                if crop_id is None:
                    slots.append(Slot(position, season))
                    continue
                crop = self._catalog.get(crop_id)
                if crop is None:
                    raise UnknownCropError(crop_id)
                slots.append(self._planted(position, season, crop, crop.roles[0]))
        main = _main_crop(slots)
        return Candidate("current", tuple(slots), is_current=True, main=main)

    # ------------------------------------------------------------ elección de cultivo

    def _allowed(self, crop: Crop) -> bool:
        if crop.id in self._constraints.exclude_crops:
            return False
        equipment = self._constraints.equipment
        return not equipment or set(crop.equipment) <= equipment

    def best(self, role: str | None, season: str, level: int, skip: Callable[[Crop], bool]):
        """Cultivo permitido de mayor aptitud para la temporada, con su mes de siembra."""
        rotation = self._config.rotation
        months = (
            rotation.season_windows[season]
            if level >= ANY_MONTH
            else [rotation.planting_months[season]]
        )
        options = []
        for crop in self._catalog:
            if (role and role not in crop.roles) or not self._allowed(crop) or skip(crop):
                continue
            for month in months:
                evaluation = self.evaluate(crop, month)
                if evaluation.status in _ALLOWED_STATUS[level]:
                    options.append((evaluation.score, crop, month))
        if not options:
            return None
        # Mayor puntaje; en empate, el primero del catálogo y el mes por defecto.
        _, crop, month = max(options, key=lambda option: option[0])
        return crop, month

    # ------------------------------------------------------------ plantillas

    def _replace_main(self, current: Candidate, role: str | None, level: int, template: str, skip):
        """Sustituye el último ciclo del cultivo principal por el mejor cultivo del rol."""
        slots = list(current.slots)
        positions = [
            i for i, slot in enumerate(slots) if slot.crop and slot.crop.id == current.main.id
        ]
        if len(positions) < 2:
            # Con un solo ciclo del cultivo principal se alarga la rotación para alternar.
            years = current.years
            slots += [replace(slot, year=slot.year + years) for slot in current.slots]
            positions = [
                i for i, slot in enumerate(slots) if slot.crop and slot.crop.id == current.main.id
            ]
        target = slots[positions[-1]]
        choice = self.best(role, target.season, level, skip)
        if choice is None:
            return None
        crop, month = choice
        slots[positions[-1]] = self._planted(
            target.year, target.season, crop, role or crop.roles[0], month
        )
        return Candidate(
            template, tuple(slots), relaxation=level, introduced=crop, main=current.main
        )

    def legume(self, current: Candidate, level: int) -> Candidate | None:
        return self._replace_main(
            current, "legume", level, "legume", lambda crop: crop.id == current.main.id
        )

    def diversify(self, current: Candidate, level: int) -> Candidate | None:
        """Último recurso: alternar con cualquier cultivo permitido de otra familia."""
        return self._replace_main(
            current, None, level, "diversify", lambda crop: crop.family == current.main.family
        )

    def _fill_fallow(self, current: Candidate, role: str, level: int, template: str):
        slots, introduced = [], None
        for slot in current.slots:
            if slot.crop is None:
                choice = self.best(role, slot.season, level, lambda crop: False)
                if choice is not None:
                    introduced = introduced or choice[0]
                    slot = self._planted(slot.year, slot.season, choice[0], role, choice[1])
            slots.append(slot)
        if introduced is None:
            return None
        return Candidate(
            template, tuple(slots), relaxation=level, introduced=introduced, main=current.main
        )

    def cover(self, current: Candidate, level: int) -> Candidate | None:
        return self._fill_fallow(current, "cover", level, "cover")

    def forage(self, current: Candidate, level: int) -> Candidate | None:
        if not self._constraints.has_livestock:
            return None
        return self._fill_fallow(current, "forage", level, "forage")

    def drought(self, current: Candidate, level: int) -> Candidate | None:
        """Cambia el cultivo principal, en todos sus ciclos, por el tolerante a sequía más apto."""
        if "drought_tolerant" in current.main.roles:
            return None
        slots, introduced = [], None
        for slot in current.slots:
            if slot.crop and slot.crop.id == current.main.id:
                choice = self.best(
                    "drought_tolerant", slot.season, level, lambda crop: crop.id == current.main.id
                )
                if choice is None:
                    return None
                introduced = introduced or choice[0]
                slot = self._planted(
                    slot.year, slot.season, choice[0], "drought_tolerant", choice[1]
                )
            slots.append(slot)
        return Candidate(
            "drought", tuple(slots), relaxation=level, introduced=introduced, main=current.main
        )

    def rest(self, current: Candidate, which: int) -> Candidate:
        """Relleno: deja en barbecho un ciclo. Solo se usa si no hay otra alternativa posible."""
        slots = list(current.slots)
        positions = [i for i, slot in enumerate(slots) if slot.crop is not None]
        if len(positions) < 2:
            years = current.years
            slots += [replace(slot, year=slot.year + years) for slot in current.slots]
            positions = [i for i, slot in enumerate(slots) if slot.crop is not None]
        index = positions[-1] if which == 0 else positions[0]
        slots[index] = Slot(slots[index].year, slots[index].season)
        template = "rest" if which == 0 else "rest_early"
        return Candidate(template, tuple(slots), relaxation=ANY_STATUS, main=current.main)

    def alternatives(self, current: Candidate) -> list[Candidate]:
        """Alternativas distintas de la actual; al menos dos, relajando solo si hace falta."""
        templates = (self.legume, self.cover, self.drought, self.forage)
        found: dict[tuple, Candidate] = {}

        def add(candidate: Candidate | None) -> None:
            if candidate is None or candidate.signature() == current.signature():
                return
            if candidate.id in {known.id for known in found.values()}:
                return
            found.setdefault(candidate.signature(), candidate)

        for level in (STRICT, MARGINAL, ANY_MONTH, ANY_STATUS):
            for template in templates:
                add(template(current, level))
            if len(found) >= 2:
                break
        if len(found) < 2:
            for level in (STRICT, MARGINAL, ANY_MONTH, ANY_STATUS):
                add(self.diversify(current, level))
        for which in (0, 1):
            if len(found) < 2:
                add(self.rest(current, which))
        return list(found.values())


def _main_crop(slots: Sequence[Slot]) -> Crop:
    """El cultivo con más ciclos; en empate, el que aparece primero."""
    counts = Counter(slot.crop.id for slot in slots if slot.crop)
    top = max(counts.values())
    return next(slot.crop for slot in slots if slot.crop and counts[slot.crop.id] == top)
