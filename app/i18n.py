"""Idioma de los textos de la API: español por defecto, inglés admitido.

Las claves llevan un prefijo por módulo (`error.`, `geometry.`, ...) para que cada cambio
añada las suyas sin tocar las de otros.
"""

SUPPORTED_LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"

MESSAGES: dict[str, dict[str, str]] = {
    "error.validation_error": {
        "es": "La petición no cumple el esquema.",
        "en": "The request does not match the schema.",
    },
    "error.not_found": {
        "es": "El recurso no existe.",
        "en": "The resource does not exist.",
    },
    "error.method_not_allowed": {
        "es": "Método no permitido para esta ruta.",
        "en": "Method not allowed for this route.",
    },
    "error.bad_request": {
        "es": "La petición no es válida.",
        "en": "The request is not valid.",
    },
    "error.internal_error": {
        "es": "Error interno. Inténtalo de nuevo.",
        "en": "Internal error. Please try again.",
    },
    "error.missing_client_id": {
        "es": "Falta el encabezado X-Client-Id.",
        "en": "The X-Client-Id header is missing.",
    },
    "error.invalid_client_id": {
        "es": "El encabezado X-Client-Id debe ser un UUID.",
        "en": "The X-Client-Id header must be a UUID.",
    },
    "error.data_unavailable": {
        "es": "Los datos aún no están disponibles.",
        "en": "Data is not available yet.",
    },
    "error.field_limit_reached": {
        "es": "Se alcanzó el máximo de {limit} geocercas por cliente.",
        "en": "The maximum of {limit} fields per client has been reached.",
    },
    "error.out_of_region": {
        "es": "El terreno está fuera de las zonas cubiertas.",
        "en": "The field is outside the covered zones.",
    },
    "error.invalid_geometry": {
        "es": "La geometría no es válida.",
        "en": "The geometry is not valid.",
    },
    "geometry.unsupported_type": {
        "es": "La geometría debe ser un Polygon o MultiPolygon de GeoJSON.",
        "en": "The geometry must be a GeoJSON Polygon or MultiPolygon.",
    },
    "geometry.malformed_coordinates": {
        "es": "Las coordenadas no tienen la estructura de GeoJSON; cada punto es [lon, lat].",
        "en": "The coordinates do not follow the GeoJSON structure; each point is [lon, lat].",
    },
    "geometry.coordinates_out_of_range": {
        "es": "Hay coordenadas fuera de rango; el orden esperado es [lon, lat].",
        "en": "Some coordinates are out of range; the expected order is [lon, lat].",
    },
    "geometry.ring_too_short": {
        "es": "Cada anillo necesita al menos 4 puntos.",
        "en": "Each ring needs at least 4 points.",
    },
    "geometry.ring_not_closed": {
        "es": "El primer y el último punto de cada anillo deben coincidir.",
        "en": "The first and last point of each ring must be the same.",
    },
    "geometry.too_many_vertices": {
        "es": "La geometría supera el máximo de {max_vertices} vértices.",
        "en": "The geometry exceeds the maximum of {max_vertices} vertices.",
    },
    "geometry.self_intersection": {
        "es": "El polígono se cruza consigo mismo o sus partes se solapan.",
        "en": "The polygon intersects itself or its parts overlap.",
    },
    "geometry.empty_area": {
        "es": "El polígono no tiene superficie.",
        "en": "The polygon has no area.",
    },
    "geometry.too_large": {
        "es": "El terreno supera el máximo de {max_area_ha} hectáreas.",
        "en": "The field exceeds the maximum of {max_area_ha} hectares.",
    },
}


def resolve_language(accept_language: str | None) -> str:
    """Primer idioma admitido de `Accept-Language` por preferencia; español si no hay ninguno."""
    candidates: list[tuple[float, int, str]] = []
    for position, part in enumerate((accept_language or "").split(",")):
        tag, _, params = part.strip().partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                continue
        primary = tag.strip().lower().split("-")[0]
        if primary in SUPPORTED_LANGUAGES and quality > 0:
            candidates.append((-quality, position, primary))
    return min(candidates)[2] if candidates else DEFAULT_LANGUAGE


def translate(key: str, language: str, **params) -> str:
    texts = MESSAGES[key]
    return texts.get(language, texts[DEFAULT_LANGUAGE]).format(**params)
