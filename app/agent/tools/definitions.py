"""Las herramientas del asistente agrónomo. Cada una reutiliza la función de su endpoint."""

from app.agent.tools.registry import Tool, ToolContext, ToolRegistry
from app.api.routes.catalog import list_crops
from app.api.routes.fields import list_fields
from app.api.routes.profile import get_profile
from app.api.routes.rotations import compare_rotations
from app.api.routes.suitability import get_suitability
from app.api.schemas.rotations import RotationRequest

PROFILE_SECTIONS = [
    "climate",
    "soil",
    "terrain",
    "water",
    "vegetation",
    "hazards",
    "gaps",
    "sources",
]
CLIMATE_PARTS = ["frost", "rain", "heat", "wind"]
_FIELD_ID = {
    "type": "string",
    "description": "Identificador de la geocerca (fld_...). Si se omite, se usa la geocerca activa.",
}
_SCENARIO = {
    "delta_t_c": {
        "type": "number",
        "minimum": -2,
        "maximum": 5,
        "description": "Cambio de temperatura en °C",
    },
    "delta_p_pct": {
        "type": "number",
        "minimum": -50,
        "maximum": 50,
        "description": "Cambio de lluvia en %",
    },
}


def _field_id(context: ToolContext, arguments: dict) -> str:
    field_id = arguments.get("field_id") or context.active_field_id
    if not field_id:
        from app.api.errors import ApiError

        raise ApiError("field_required", 422, details={"hint": "usa list_user_fields"})
    return field_id


def _list_user_fields(context: ToolContext, arguments: dict):
    return [
        {
            "field_id": field["id"],
            "name": field["name"],
            "kind": field["kind"],
            "zone_id": field["zone_id"],
            "cell_id": field["cell_id"],
            "area_ha": field["area_ha"],
            "current_rotation": field.get("current_rotation"),
            "irrigation": field.get("irrigation"),
            "livestock": field.get("livestock"),
            "active": field["id"] == context.active_field_id,
        }
        for field in list_fields(context.client_id, context.repo)
    ]


def _profile(context: ToolContext, arguments: dict) -> dict:
    return get_profile(
        _field_id(context, arguments),
        context.client_id,
        context.repo,
        context.language,
        context.profiles,
    )


def _get_field_profile(context: ToolContext, arguments: dict):
    profile = _profile(context, arguments)
    sections = arguments.get("sections") or ["climate", "soil", "water", "gaps"]
    result = {
        key: profile[key]
        for key in ("field_id", "cell_id", "zone_id", "resolution_m", "data_version")
    }
    for section in sections:
        value = profile.get(section)
        if section == "climate" and value is not None:
            # El calendario de 36 decenas tiene su propia herramienta.
            value = {key: item for key, item in value.items() if key != "risk_calendar"}
        result[section] = value
    result["sources"] = profile["sources"]
    return result


def _get_risk_calendar(context: ToolContext, arguments: dict):
    profile = _profile(context, arguments)
    first = arguments.get("from_decade", 1)
    last = arguments.get("to_decade", 36)
    return {
        "field_id": profile["field_id"],
        "zone_id": profile["zone_id"],
        "note": "Decenas: 1 = 1-10 de enero, 2 = 11-20, 3 = 21-31, ... 36 = 21-31 de diciembre.",
        "decades": [
            entry
            for entry in profile["climate"]["risk_calendar"]
            if first <= entry["decade"] <= last
        ],
        "sources": [source for source in profile["sources"] if source["id"] == "nasa_power"],
    }


def _suitability(context: ToolContext, arguments: dict, **query):
    return get_suitability(
        _field_id(context, arguments),
        context.client_id,
        context.repo,
        context.language,
        context.data,
        context.catalog,
        context.engine,
        context.scenarios,
        delta_t_c=arguments.get("delta_t_c", 0),
        delta_p_pct=arguments.get("delta_p_pct", 0),
        **query,
    )


def _evaluate_crop(context: ToolContext, arguments: dict):
    return _suitability(
        context,
        arguments,
        crop_id=arguments["crop_id"],
        planting_month=arguments["planting_month"],
    )


def _suitability_matrix(context: ToolContext, arguments: dict):
    return _suitability(context, arguments, crop_id=None, planting_month=None)


def _compare_rotations(context: ToolContext, arguments: dict):
    body = RotationRequest.model_validate(
        {
            "priorities": arguments.get("priorities") or {},
            "constraints": {
                key: arguments[key]
                for key in ("exclude_crops", "irrigation_mm_per_year", "horizon_years")
                if key in arguments
            },
            "scenario": {
                key: arguments[key] for key in ("delta_t_c", "delta_p_pct") if key in arguments
            },
        }
    )
    return compare_rotations(
        _field_id(context, arguments),
        body,
        context.client_id,
        context.repo,
        context.language,
        context.data,
        context.catalog,
        context.engine,
        context.scenarios,
    )


def _list_crops(context: ToolContext, arguments: dict):
    return [
        {
            "id": crop.id,
            "name": getattr(crop.name, context.language, crop.name.es),
            "family": crop.family,
            "roles": crop.roles,
            "cycle_days": list(crop.cycle_days),
            "frost_tolerant": crop.frost_tolerant,
            "heat_critical_c": crop.heat_critical_c,
            "water_need_mm": list(crop.water_need_mm),
            "ph": list(crop.ph),
        }
        for crop in list_crops(context.catalog)
    ]


def build_registry(crop_ids: list[str]) -> ToolRegistry:
    month = {"type": "integer", "minimum": 1, "maximum": 12, "description": "Mes de siembra, 1-12"}
    crop = {"type": "string", "enum": crop_ids, "description": "Cultivo del catálogo"}
    return ToolRegistry(
        [
            Tool(
                "list_user_fields",
                "Lista las geocercas (terrenos) del usuario con su zona, rotación actual, riego y ganado.",
                {"type": "object", "properties": {}, "required": []},
                _list_user_fields,
                {"es": "Consultando tus terrenos", "en": "Checking your fields"},
            ),
            Tool(
                "get_field_profile",
                "Perfil agroclimático histórico de la zona (celda de 9 km) de una geocerca: heladas, "
                "lluvia, calor y viento por mes, suelo estimado, agua, vacíos de información y fuentes.",
                {
                    "type": "object",
                    "properties": {
                        "field_id": _FIELD_ID,
                        "sections": {
                            "type": "array",
                            "items": {"type": "string", "enum": PROFILE_SECTIONS},
                            "description": "Secciones a devolver; por defecto clima, suelo, agua y vacíos",
                        },
                    },
                    "required": [],
                },
                _get_field_profile,
                {"es": "Leyendo el perfil de tu zona", "en": "Reading your zone's profile"},
            ),
            Tool(
                "get_risk_calendar",
                "Calendario de riesgos por decena (periodos de 10 días): probabilidad de helada, calor, "
                "lluvia intensa y estrés hídrico, y decenas vulnerables con sus motivos.",
                {
                    "type": "object",
                    "properties": {
                        "field_id": _FIELD_ID,
                        "from_decade": {"type": "integer", "minimum": 1, "maximum": 36},
                        "to_decade": {"type": "integer", "minimum": 1, "maximum": 36},
                    },
                    "required": [],
                },
                _get_risk_calendar,
                {"es": "Consultando el calendario de riesgos", "en": "Checking the risk calendar"},
            ),
            Tool(
                "evaluate_crop",
                "Evalúa si conviene sembrar un cultivo en un mes en la zona de la geocerca: puntaje 0-100, "
                "estado y motivos (helada, calor, agua, suelo) con su fuente. Admite un escenario climático.",
                {
                    "type": "object",
                    "properties": {
                        "field_id": _FIELD_ID,
                        "crop_id": crop,
                        "planting_month": month,
                        **_SCENARIO,
                    },
                    "required": ["crop_id", "planting_month"],
                },
                _evaluate_crop,
                {"es": "Evaluando el cultivo", "en": "Evaluating the crop"},
                card_type="suitability",
            ),
            Tool(
                "suitability_matrix",
                "Puntaje de aptitud de todos los cultivos del catálogo para los 12 meses de siembra.",
                {
                    "type": "object",
                    "properties": {"field_id": _FIELD_ID, **_SCENARIO},
                    "required": [],
                },
                _suitability_matrix,
                {"es": "Calculando la aptitud de los cultivos", "en": "Computing crop suitability"},
                card_type="suitability_matrix",
            ),
            Tool(
                "compare_rotations",
                "Compara la rotación actual de la geocerca con al menos dos alternativas: agua, nitrógeno, "
                "suelo descubierto, plagas, puntajes por prioridad y recomendación, con explicación.",
                {
                    "type": "object",
                    "properties": {
                        "field_id": _FIELD_ID,
                        "exclude_crops": {
                            "type": "array",
                            "items": {"type": "string", "enum": crop_ids},
                        },
                        "irrigation_mm_per_year": {"type": "number", "minimum": 0, "maximum": 5000},
                        "horizon_years": {"type": "integer", "minimum": 1, "maximum": 6},
                        **_SCENARIO,
                    },
                    "required": [],
                },
                _compare_rotations,
                {"es": "Comparando rotaciones", "en": "Comparing rotations"},
                card_type="rotations",
            ),
            Tool(
                "list_crops",
                "Catálogo de cultivos con sus requisitos: ciclo, temperaturas, tolerancia a helada, agua y pH.",
                {"type": "object", "properties": {}, "required": []},
                _list_crops,
                {"es": "Consultando el catálogo de cultivos", "en": "Checking the crop catalog"},
            ),
        ]
    )
