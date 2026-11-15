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
    "profile.gap.zonal_resolution_9km": {
        "es": "Los datos describen tu zona (celda de 9 km), no tu parcela.",
        "en": "The data describes your zone (9 km cell), not your individual plot.",
    },
    "profile.gap.no_lab_analysis": {
        "es": "No hay análisis de laboratorio del suelo; los valores de suelo son estimaciones para la zona.",
        "en": "There is no laboratory soil analysis; soil values are estimates for the zone.",
    },
    "profile.gap.synthetic_data": {
        "es": "Este entorno usa datos sintéticos de prueba: las cifras no son observaciones reales de la zona.",
        "en": "This environment uses synthetic test data: the figures are not real observations of the zone.",
    },
    "profile.gap.shared_climate_series": {
        "es": "La lluvia, el viento y la humedad vienen de un cuadro climático de ~55 km que comparten {n_cells} celdas de la zona.",
        "en": "Rain, wind and humidity come from a ~55 km climate grid box shared by {n_cells} cells in the zone.",
    },
    "profile.gap.elevation_mismatch": {
        "es": "La elevación de la zona difiere {difference_m} m de la del cuadro climático; las temperaturas son una estimación corregida por altura.",
        "en": "The elevation of the zone differs by {difference_m} m from the climate grid box; temperatures are an estimate corrected for altitude.",
    },
    "profile.gap.soil_moisture_from_model": {
        "es": "La humedad del suelo viene de un modelo (NASA POWER), no de SMAP; se expresa como percentil de la zona.",
        "en": "Soil moisture comes from a model (NASA POWER), not from SMAP; it is expressed as a percentile for the zone.",
    },
    "profile.gap.ndvi_not_available": {
        "es": "Aún no hay datos de vegetación (NDVI) para la zona; no se puede estimar el suelo descubierto.",
        "en": "There is no vegetation (NDVI) data for the zone yet; bare soil cannot be estimated.",
    },
    "profile.gap.no_soil_data": {
        "es": "No hay datos de suelo para la zona.",
        "en": "There is no soil data for the zone.",
    },
    "profile.gap.no_elevation_data": {
        "es": "No hay elevación de la zona; las temperaturas no llevan una corrección por altura verificable.",
        "en": "There is no elevation for the zone; temperatures carry no verifiable altitude correction.",
    },
    "profile.gap.no_wind_data": {
        "es": "No hay datos de viento para la zona.",
        "en": "There is no wind data for the zone.",
    },
    "profile.gap.no_daily_series": {
        "es": "Sin serie diaria: no se calculan récords de temperatura ni fechas de primera y última helada.",
        "en": "No daily series: temperature records and first and last frost dates are not computed.",
    },
    "profile.gap.no_slope_data": {
        "es": "La pendiente del terreno aún no está disponible.",
        "en": "Terrain slope is not available yet.",
    },
    "profile.gap.no_groundwater_source": {
        "es": "No hay fuente de agua subterránea para esta zona.",
        "en": "There is no groundwater source for this zone.",
    },
    "profile.gap.no_light_data": {
        "es": "La radiación y la luz diaria aún no están disponibles.",
        "en": "Solar radiation and daily light are not available yet.",
    },
    "profile.gap.no_land_use_history": {
        "es": "No hay historial satelital de cultivos para México; se usa la rotación declarada.",
        "en": "There is no satellite crop history for Mexico; the declared rotation is used.",
    },
    "profile.gap.no_hail_product": {
        "es": "No existe un producto NASA directo de granizo; consulta a productores locales.",
        "en": "There is no direct NASA hail product; ask local growers.",
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
