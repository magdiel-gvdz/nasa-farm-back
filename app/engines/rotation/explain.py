"""Explicación determinista de cada estrategia.

Cada frase sale de una regla: una condición sobre las métricas y una clave de texto del
catálogo de `app/i18n.py` con los valores interpolados. No interviene ningún modelo de
lenguaje. Los textos hablan de la zona (celda de 9 km), no de la parcela.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.engines.rotation.candidates import ANY_STATUS, MARGINAL, STRICT, Candidate
from app.engines.rotation.simulate import Metrics
from app.i18n import translate

CLIMATE_SOURCE = "nasa_power"
SOIL_SOURCE = "soilgrids"


@dataclass(frozen=True)
class Context:
    """Todo lo que una regla puede consultar."""

    candidate: Candidate
    metrics: Metrics
    baseline: Metrics  # métricas de la rotación actual
    irrigation_limit_mm: float | None
    soil_ph: float | None
    language: str

    def crop_name(self, crop) -> str:
        return getattr(crop.name, self.language, crop.name.es)

    @property
    def introduced(self) -> str:
        crop = self.candidate.introduced
        return self.crop_name(crop) if crop else ""

    @property
    def main(self) -> str:
        return self.crop_name(self.candidate.main)

    @property
    def irrigation_excess_mm(self) -> float:
        if self.irrigation_limit_mm is None:
            return 0.0
        return max(0.0, self.metrics.irrigation_need_mm_per_year - self.irrigation_limit_mm)

    @property
    def weak_crops(self) -> list:
        """Cultivos de la secuencia que no son plenamente aptos en la zona, sin repetir."""
        seen, weak = set(), []
        for slot in self.candidate.crop_slots:
            if slot.evaluation.status != "suitable" and slot.crop.id not in seen:
                seen.add(slot.crop.id)
                weak.append(slot)
        return weak


@dataclass(frozen=True)
class Rule:
    key: str
    applies: Callable[[Context], bool]
    params: Callable[[Context], dict] = lambda context: {}
    source_id: str | None = None

    def text(self, context: Context) -> str:
        return translate(f"rotation.{self.key}", context.language, **self.params(context))


def _is(*templates: str) -> Callable[[Context], bool]:
    return lambda context: context.candidate.id in templates


def _water(context: Context) -> dict:
    return {
        "need": round(context.metrics.irrigation_need_mm_per_year),
        "baseline": round(context.baseline.irrigation_need_mm_per_year),
        "demand": round(context.metrics.water_demand_mm_per_year),
    }


def _nitrogen(context: Context) -> dict:
    return {
        "crop": context.introduced,
        "balance": round(context.metrics.n_balance_kg_ha_per_year),
        "baseline": round(context.baseline.n_balance_kg_ha_per_year),
    }


def _bare(context: Context) -> dict:
    return {
        "crop": context.introduced,
        "days": round(context.metrics.bare_soil_days_per_year),
        "baseline": round(context.baseline.bare_soil_days_per_year),
        "share": round(context.metrics.erosion_exposure_index * 100),
    }


def _pests(context: Context) -> dict:
    return {
        "score": f"{context.metrics.pest_break_score:g}",
        "baseline": f"{context.baseline.pest_break_score:g}",
    }


def _crops(context: Context) -> dict:
    return {"crop": context.introduced, "main": context.main}


WHY = (
    Rule("why.current", _is("current")),
    Rule("why.legume", _is("legume"), _nitrogen),
    Rule("why.cover", _is("cover"), _bare),
    Rule("why.drought", _is("drought"), lambda c: {**_crops(c), **_water(c)}),
    Rule("why.forage", _is("forage"), _crops),
    Rule("why.diversify", _is("diversify"), _crops),
    Rule("why.rest", _is("rest", "rest_early"), _water),
    Rule(
        "why.pest_break",
        lambda c: (
            not c.candidate.is_current and c.metrics.pest_break_score > c.baseline.pest_break_score
        ),
        _pests,
    ),
)

EVIDENCE = (
    Rule("evidence.water", lambda c: True, _water, CLIMATE_SOURCE),
    Rule("evidence.bare_soil", lambda c: True, _bare, CLIMATE_SOURCE),
    Rule(
        "evidence.soil_ph",
        lambda c: c.soil_ph is not None,
        lambda c: {"ph": f"{c.soil_ph:.1f}"},
        SOIL_SOURCE,
    ),
)

BENEFITS = (
    Rule("benefit.current", _is("current")),
    Rule(
        "benefit.less_irrigation",
        lambda c: c.metrics.irrigation_need_mm_per_year < c.baseline.irrigation_need_mm_per_year,
        lambda c: {
            "saving": round(
                c.baseline.irrigation_need_mm_per_year - c.metrics.irrigation_need_mm_per_year
            )
        },
    ),
    Rule(
        "benefit.more_nitrogen",
        lambda c: c.metrics.n_balance_kg_ha_per_year > c.baseline.n_balance_kg_ha_per_year,
        lambda c: {
            "gain": round(c.metrics.n_balance_kg_ha_per_year - c.baseline.n_balance_kg_ha_per_year)
        },
    ),
    Rule(
        "benefit.less_bare_soil",
        lambda c: c.metrics.bare_soil_days_per_year < c.baseline.bare_soil_days_per_year,
        _bare,
    ),
    Rule(
        "benefit.pest_break",
        lambda c: c.metrics.pest_break_score > c.baseline.pest_break_score,
        _pests,
    ),
    Rule(
        "benefit.forage",
        lambda c: c.metrics.forage_cycles_per_year > c.baseline.forage_cycles_per_year,
    ),
    Rule(
        "benefit.organic_matter",
        lambda c: not c.candidate.is_current and c.metrics.om_trend == "improving",
    ),
)
# Si ninguna regla de beneficio aplica, la estrategia mantiene al menos el cultivo principal.
BENEFIT_FALLBACK = Rule("benefit.keeps_main", lambda c: True, lambda c: {"main": c.main})

GAPS = (
    Rule("gap.zonal", lambda c: True),
    Rule("gap.no_lab", lambda c: True),
    Rule("gap.no_margin", lambda c: c.metrics.gross_margin_index is None),
    Rule(
        "gap.unreviewed_crops", lambda c: any(not s.crop.reviewed for s in c.candidate.crop_slots)
    ),
)

RISKS = (
    Rule("risk.local_review", lambda c: True),
    Rule(
        "risk.irrigation",
        lambda c: c.irrigation_excess_mm > 0,
        lambda c: {
            "need": round(c.metrics.irrigation_need_mm_per_year),
            "limit": round(c.irrigation_limit_mm),
            "deficit": round(c.irrigation_excess_mm),
        },
    ),
    Rule(
        "risk.relaxed_marginal",
        lambda c: c.candidate.relaxation == MARGINAL,
        lambda c: {"crop": c.introduced},
    ),
    Rule(
        "risk.relaxed_month",
        lambda c: (
            STRICT < c.candidate.relaxation < ANY_STATUS and c.candidate.relaxation != MARGINAL
        ),
        lambda c: {"crop": c.introduced},
    ),
    Rule(
        "risk.relaxed_any",
        lambda c: c.candidate.relaxation == ANY_STATUS and c.candidate.introduced is not None,
        lambda c: {"crop": c.introduced},
    ),
    Rule("risk.rest", _is("rest", "rest_early")),
)


def _apply(rules, context: Context) -> list[Rule]:
    return [rule for rule in rules if rule.applies(context)]


def _weak_crop_risks(context: Context) -> list[str]:
    return [
        translate(
            "rotation.risk.weak_crop",
            context.language,
            crop=context.crop_name(slot.crop),
            month=translate(f"month.{slot.planting_month}", context.language),
            score=round(slot.evaluation.score),
        )
        for slot in context.weak_crops
    ]


def explain(context: Context) -> dict:
    benefits = _apply(BENEFITS, context) or [BENEFIT_FALLBACK]
    return {
        "why": [rule.text(context) for rule in _apply(WHY, context)],
        "evidence": [
            {"claim": rule.text(context), "source_id": rule.source_id}
            for rule in _apply(EVIDENCE, context)
        ],
        "benefits": [rule.text(context) for rule in benefits],
        "gaps": [rule.text(context) for rule in _apply(GAPS, context)],
        "risks_local_review": [rule.text(context) for rule in _apply(RISKS, context)]
        + _weak_crop_risks(context),
    }


def strategy_name(candidate: Candidate, language: str) -> str:
    fallow = translate("rotation.fallow", language)
    return " – ".join(
        getattr(slot.crop.name, language, slot.crop.name.es) if slot.crop else fallow
        for slot in candidate.slots
    )


def rule_keys() -> list[str]:
    """Todas las claves de texto que puede usar el motor."""
    rules = (*WHY, *EVIDENCE, *BENEFITS, BENEFIT_FALLBACK, *GAPS, *RISKS)
    return [f"rotation.{rule.key}" for rule in rules] + [
        "rotation.risk.weak_crop",
        "rotation.fallow",
        "rotation.disclaimer",
    ]
