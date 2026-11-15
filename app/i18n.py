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
    "month.1": {
        "es": "enero",
        "en": "January",
    },
    "month.2": {
        "es": "febrero",
        "en": "February",
    },
    "month.3": {
        "es": "marzo",
        "en": "March",
    },
    "month.4": {
        "es": "abril",
        "en": "April",
    },
    "month.5": {
        "es": "mayo",
        "en": "May",
    },
    "month.6": {
        "es": "junio",
        "en": "June",
    },
    "month.7": {
        "es": "julio",
        "en": "July",
    },
    "month.8": {
        "es": "agosto",
        "en": "August",
    },
    "month.9": {
        "es": "septiembre",
        "en": "September",
    },
    "month.10": {
        "es": "octubre",
        "en": "October",
    },
    "month.11": {
        "es": "noviembre",
        "en": "November",
    },
    "month.12": {
        "es": "diciembre",
        "en": "December",
    },
    "error.crop_not_found": {
        "es": "El cultivo no existe en el catálogo.",
        "en": "The crop is not in the catalog.",
    },
    "suitability.frost.ok": {
        "es": "Riesgo bajo de helada durante el ciclo en tu zona: como máximo {pct} % de los años hiela (Tmin < {threshold} °C) en la decena del {decade}.",
        "en": "Low frost risk during the cycle in your zone: at most {pct}% of years have frost (Tmin < {threshold} °C) in the ten-day period starting {decade}.",
    },
    "suitability.frost.warn": {
        "es": "En tu zona hiela (Tmin < {threshold} °C) en {pct} % de los años en la decena del {decade}, dentro del ciclo.",
        "en": "In your zone there is frost (Tmin < {threshold} °C) in {pct}% of years in the ten-day period starting {decade}, within the cycle.",
    },
    "suitability.frost.bad": {
        "es": "En tu zona hiela (Tmin < {threshold} °C) en {pct} % de los años en la decena del {decade}, dentro del ciclo, y el cultivo no tolera heladas.",
        "en": "In your zone there is frost (Tmin < {threshold} °C) in {pct}% of years in the ten-day period starting {decade}, within the cycle, and the crop does not tolerate frost.",
    },
    "suitability.frost.tolerant_ok": {
        "es": "El cultivo tolera heladas ligeras; las heladas fuertes (Tmin < {threshold} °C) ocurren como máximo en {pct} % de los años en la decena del {decade}.",
        "en": "The crop tolerates light frost; hard frost (Tmin < {threshold} °C) happens in at most {pct}% of years in the ten-day period starting {decade}.",
    },
    "suitability.frost.tolerant_warn": {
        "es": "El cultivo tolera heladas ligeras, pero en tu zona hay heladas fuertes (Tmin < {threshold} °C) en {pct} % de los años en la decena del {decade}.",
        "en": "The crop tolerates light frost, but your zone has hard frost (Tmin < {threshold} °C) in {pct}% of years in the ten-day period starting {decade}.",
    },
    "suitability.frost.unknown": {
        "es": "No hay datos de heladas para la zona.",
        "en": "There is no frost data for the zone.",
    },
    "suitability.heat.ok": {
        "es": "Poco calor en la floración: como máximo {pct} % de los años superan {threshold} °C en la decena del {decade} (temperatura crítica del cultivo: {critical} °C; umbral usado: {threshold} °C).",
        "en": "Little heat at flowering: at most {pct}% of years exceed {threshold} °C in the ten-day period starting {decade} (crop critical temperature: {critical} °C; threshold used: {threshold} °C).",
    },
    "suitability.heat.warn": {
        "es": "La floración cae en la decena del {decade}: en {pct} % de los años tu zona supera {threshold} °C (temperatura crítica del cultivo: {critical} °C; umbral usado: {threshold} °C).",
        "en": "Flowering falls in the ten-day period starting {decade}: in {pct}% of years your zone exceeds {threshold} °C (crop critical temperature: {critical} °C; threshold used: {threshold} °C).",
    },
    "suitability.heat.bad": {
        "es": "La floración cae en la decena del {decade}: en {pct} % de los años tu zona supera {threshold} °C, lo que daña la floración (temperatura crítica del cultivo: {critical} °C; umbral usado: {threshold} °C).",
        "en": "Flowering falls in the ten-day period starting {decade}: in {pct}% of years your zone exceeds {threshold} °C, which damages flowering (crop critical temperature: {critical} °C; threshold used: {threshold} °C).",
    },
    "suitability.heat.unknown": {
        "es": "No hay datos de calor para la zona.",
        "en": "There is no heat data for the zone.",
    },
    "suitability.water.ok": {
        "es": "Demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona y {irrigation} mm de riego: déficit de {deficit} mm.",
        "en": "Demand of {demand} mm versus {rain} mm of effective rain in your zone and {irrigation} mm of irrigation: deficit of {deficit} mm.",
    },
    "suitability.water.warn": {
        "es": "Demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona y {irrigation} mm de riego: déficit de {deficit} mm.",
        "en": "Demand of {demand} mm versus {rain} mm of effective rain in your zone and {irrigation} mm of irrigation: deficit of {deficit} mm.",
    },
    "suitability.water.bad": {
        "es": "Demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona y {irrigation} mm de riego: déficit de {deficit} mm, el riego disponible no alcanza.",
        "en": "Demand of {demand} mm versus {rain} mm of effective rain in your zone and {irrigation} mm of irrigation: deficit of {deficit} mm, the available irrigation is not enough.",
    },
    "suitability.water.rainfed_ok": {
        "es": "Sin riego declarado, se evalúa en temporal: demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona; déficit de {deficit} mm.",
        "en": "No irrigation declared, evaluated as rainfed: demand of {demand} mm versus {rain} mm of effective rain in your zone; deficit of {deficit} mm.",
    },
    "suitability.water.rainfed_warn": {
        "es": "Sin riego declarado, se evalúa en temporal: demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona; déficit de {deficit} mm.",
        "en": "No irrigation declared, evaluated as rainfed: demand of {demand} mm versus {rain} mm of effective rain in your zone; deficit of {deficit} mm.",
    },
    "suitability.water.rainfed_bad": {
        "es": "Sin riego declarado, se evalúa en temporal: demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona; déficit de {deficit} mm, la lluvia no alcanza.",
        "en": "No irrigation declared, evaluated as rainfed: demand of {demand} mm versus {rain} mm of effective rain in your zone; deficit of {deficit} mm, rain is not enough.",
    },
    "suitability.water.unlimited_irrigation": {
        "es": "Demanda de {demand} mm frente a {rain} mm de lluvia efectiva en tu zona; harían falta {irrigation} mm de riego. Declaraste riego sin indicar cuánto: confirma que alcanza.",
        "en": "Demand of {demand} mm versus {rain} mm of effective rain in your zone; {irrigation} mm of irrigation would be needed. You declared irrigation without an amount: confirm it is enough.",
    },
    "suitability.water.unknown": {
        "es": "No hay datos de lluvia o evapotranspiración para la zona.",
        "en": "There is no rain or evapotranspiration data for the zone.",
    },
    "suitability.soil.ph_ok": {
        "es": "pH estimado de {ph} en tu zona, dentro del rango del cultivo ({low}-{high}).",
        "en": "Estimated pH of {ph} in your zone, within the crop range ({low}-{high}).",
    },
    "suitability.soil.ph_warn": {
        "es": "pH estimado de {ph} en tu zona, ligeramente fuera del rango del cultivo ({low}-{high}).",
        "en": "Estimated pH of {ph} in your zone, slightly outside the crop range ({low}-{high}).",
    },
    "suitability.soil.ph_bad": {
        "es": "pH estimado de {ph} en tu zona, fuera del rango del cultivo ({low}-{high}).",
        "en": "Estimated pH of {ph} in your zone, outside the crop range ({low}-{high}).",
    },
    "suitability.soil.texture": {
        "es": "La textura estimada ({texture}) complica el manejo del agua.",
        "en": "The estimated texture ({texture}) makes water management harder.",
    },
    "suitability.soil.unknown": {
        "es": "No hay datos de suelo para la zona.",
        "en": "There is no soil data for the zone.",
    },
    "error.current_rotation_required": {
        "es": "La geocerca no tiene una rotación actual declarada; añade al menos un cultivo en `current_rotation`.",
        "en": "The field has no current rotation declared; add at least one crop to `current_rotation`.",
    },
    "rotation.fallow": {
        "es": "barbecho",
        "en": "fallow",
    },
    "rotation.disclaimer": {
        "es": "Herramienta de apoyo: describe tu zona (celda de 9 km) con datos históricos y no sustituye el juicio de un agrónomo o productor local.",
        "en": "Decision-support tool: it describes your zone (9 km cell) with historical data and does not replace the judgment of a local agronomist or grower.",
    },
    "rotation.why.current": {
        "es": "Es tu rotación actual: sirve de línea base para comparar las alternativas.",
        "en": "This is your current rotation: it is the baseline the alternatives are compared against.",
    },
    "rotation.why.legume": {
        "es": "{crop} es una leguminosa que fija nitrógeno: el balance aproximado pasa de {baseline} a {balance} kg N/ha al año.",
        "en": "{crop} is a legume that fixes nitrogen: the approximate balance goes from {baseline} to {balance} kg N/ha per year.",
    },
    "rotation.why.cover": {
        "es": "{crop} cubre el suelo en la temporada que hoy queda en barbecho: los días de suelo descubierto bajan de {baseline} a {days} al año.",
        "en": "{crop} covers the soil in the season that is now fallow: bare-soil days drop from {baseline} to {days} per year.",
    },
    "rotation.why.drought": {
        "es": "{crop} tolera la sequía y sustituye a {main}: la necesidad de riego estimada pasa de {baseline} a {need} mm al año.",
        "en": "{crop} is drought tolerant and replaces {main}: the estimated irrigation need goes from {baseline} to {need} mm per year.",
    },
    "rotation.why.forage": {
        "es": "{crop} aprovecha la temporada en barbecho para producir forraje para tu ganado.",
        "en": "{crop} uses the fallow season to produce forage for your livestock.",
    },
    "rotation.why.diversify": {
        "es": "Alterna {main} con {crop}, de otra familia botánica, para no repetir el mismo cultivo.",
        "en": "Alternates {main} with {crop}, from another botanical family, to avoid repeating the same crop.",
    },
    "rotation.why.rest": {
        "es": "Deja descansar el suelo un ciclo: la necesidad de riego estimada pasa de {baseline} a {need} mm al año.",
        "en": "Rests the soil for one cycle: the estimated irrigation need goes from {baseline} to {need} mm per year.",
    },
    "rotation.why.pest_break": {
        "es": "Alternar familias botánicas rompe ciclos de plagas: el puntaje de ruptura pasa de {baseline} a {score} sobre 5.",
        "en": "Alternating botanical families breaks pest cycles: the break score goes from {baseline} to {score} out of 5.",
    },
    "rotation.evidence.water": {
        "es": "Demanda de agua de {demand} mm al año y necesidad de riego de {need} mm, con la evapotranspiración y la lluvia mediana de tu zona.",
        "en": "Water demand of {demand} mm per year and irrigation need of {need} mm, with the evapotranspiration and median rain of your zone.",
    },
    "rotation.evidence.bare_soil": {
        "es": "La secuencia deja {days} días de suelo descubierto al año; en esas decenas cae el {share} % del riesgo de lluvia intensa de tu zona.",
        "en": "The sequence leaves {days} bare-soil days per year; {share}% of the heavy-rain risk of your zone falls in those ten-day periods.",
    },
    "rotation.evidence.soil_ph": {
        "es": "El pH estimado del suelo de tu zona es {ph}.",
        "en": "The estimated soil pH of your zone is {ph}.",
    },
    "rotation.benefit.current": {
        "es": "No requiere cambios de manejo, semilla ni equipo.",
        "en": "It needs no change in management, seed or equipment.",
    },
    "rotation.benefit.less_irrigation": {
        "es": "Necesita {saving} mm menos de riego al año que tu rotación actual.",
        "en": "It needs {saving} mm less irrigation per year than your current rotation.",
    },
    "rotation.benefit.more_nitrogen": {
        "es": "Deja unos {gain} kg N/ha más al año que tu rotación actual.",
        "en": "It leaves about {gain} kg N/ha more per year than your current rotation.",
    },
    "rotation.benefit.less_bare_soil": {
        "es": "Reduce el suelo descubierto de {baseline} a {days} días al año.",
        "en": "It cuts bare soil from {baseline} to {days} days per year.",
    },
    "rotation.benefit.pest_break": {
        "es": "Mejora la ruptura de ciclos de plagas de {baseline} a {score} sobre 5.",
        "en": "It improves the pest-cycle break from {baseline} to {score} out of 5.",
    },
    "rotation.benefit.forage": {
        "es": "Añade producción de forraje.",
        "en": "It adds forage production.",
    },
    "rotation.benefit.organic_matter": {
        "es": "Más cobertura y rastrojo: la materia orgánica tiende a mejorar.",
        "en": "More cover and residue: organic matter tends to improve.",
    },
    "rotation.benefit.keeps_main": {
        "es": "Mantiene {main} como cultivo principal.",
        "en": "It keeps {main} as the main crop.",
    },
    "rotation.gap.zonal": {
        "es": "Los cálculos usan datos de tu zona (celda de 9 km), no mediciones de tu parcela.",
        "en": "The calculations use data for your zone (9 km cell), not measurements from your plot.",
    },
    "rotation.gap.no_lab": {
        "es": "No hay análisis de laboratorio del suelo: el nitrógeno y la materia orgánica son aproximaciones.",
        "en": "There is no laboratory soil analysis: nitrogen and organic matter are approximations.",
    },
    "rotation.gap.no_margin": {
        "es": "No hay datos de margen económico de los cultivos: la prioridad de ingreso no entra en el puntaje.",
        "en": "There is no economic margin data for the crops: the income priority is left out of the score.",
    },
    "rotation.gap.unreviewed_crops": {
        "es": "Los requisitos de algunos cultivos son valores iniciales sin revisar por un especialista.",
        "en": "The requirements of some crops are initial values not yet reviewed by a specialist.",
    },
    "rotation.risk.local_review": {
        "es": "Plagas, enfermedades, variedades y mercado local no se observan desde satélite: valida la rotación con un agrónomo o productor local.",
        "en": "Pests, diseases, varieties and the local market cannot be seen from satellites: validate the rotation with a local agronomist or grower.",
    },
    "rotation.risk.irrigation": {
        "es": "Necesita {need} mm de riego al año y tu límite es de {limit} mm: faltan {deficit} mm.",
        "en": "It needs {need} mm of irrigation per year and your limit is {limit} mm: {deficit} mm are missing.",
    },
    "rotation.risk.relaxed_marginal": {
        "es": "{crop} se admite con condiciones: su aptitud en tu zona es marginal.",
        "en": "{crop} is admitted with conditions: its suitability in your zone is marginal.",
    },
    "rotation.risk.relaxed_month": {
        "es": "{crop} se admite con condiciones: solo es viable moviendo la fecha de siembra dentro de la temporada.",
        "en": "{crop} is admitted with conditions: it is only viable by moving the planting date within the season.",
    },
    "rotation.risk.relaxed_any": {
        "es": "{crop} se admite con condiciones: no hay un cultivo apto para esta función con tus restricciones.",
        "en": "{crop} is admitted with conditions: no crop is suitable for this role under your constraints.",
    },
    "rotation.risk.rest": {
        "es": "Dejar un ciclo en barbecho reduce la producción; se propone solo porque tus restricciones no dejan otra alternativa.",
        "en": "Leaving one cycle fallow reduces production; it is proposed only because your constraints leave no other alternative.",
    },
    "rotation.risk.weak_crop": {
        "es": "{crop} sembrado en {month} no es plenamente apto en tu zona (puntaje {score} de 100).",
        "en": "{crop} planted in {month} is not fully suitable in your zone (score {score} out of 100).",
    },
    "error.daily_unavailable": {
        "es": "La serie diaria de la zona no está disponible: no se puede calcular el escenario. Sin escenario la petición funciona.",
        "en": "The daily series for the zone is not available: the scenario cannot be computed. Without a scenario the request works.",
    },
    "scenario.note": {
        "es": "Escenario hipotético, no un pronóstico: desplaza el clima histórico de tu zona de forma uniforme. La humedad del suelo, el suelo descubierto y el viento se mantienen como en los datos publicados.",
        "en": "Hypothetical scenario, not a forecast: it shifts the historical climate of your zone uniformly. Soil moisture, bare soil and wind stay as in the published data.",
    },
    "error.not_a_greenhouse": {
        "es": "La geocerca no es un invernadero (`kind` debe ser `greenhouse`).",
        "en": "The field is not a greenhouse (`kind` must be `greenhouse`).",
    },
    "greenhouse.wind_note": {
        "es": "El viento procede de un modelo a escala de unos 55 km y es el máximo de medias horarias, no la ráfaga instantánea; la topografía local puede aumentarlo. Valida la resistencia con el fabricante o con registros locales.",
        "en": "Wind comes from a model at a scale of about 55 km and is the maximum of hourly means, not the instantaneous gust; local topography can increase it. Validate the rating with the manufacturer or with local records.",
    },
    "greenhouse.gap.short_wind_record": {
        "es": "Solo hay {years} años completos de viento en tu zona: los niveles de retorno son poco fiables.",
        "en": "There are only {years} complete years of wind data for your zone: return levels are unreliable.",
    },
    "greenhouse.gap.insufficient_wind_record": {
        "es": "Solo hay {years} años completos de viento en tu zona: no alcanzan para estimar niveles de retorno.",
        "en": "There are only {years} complete years of wind data for your zone: not enough to estimate return levels.",
    },
    "greenhouse.gap.no_rated_wind": {
        "es": "No se declaró la resistencia al viento de la estructura (`rated_wind_kmh`): no se puede calcular la probabilidad de superarla.",
        "en": "The structure's wind rating (`rated_wind_kmh`) was not declared: the probability of exceeding it cannot be computed.",
    },
    "greenhouse.gap.no_light_assessment": {
        "es": "La luz dentro del invernadero no se evalúa.",
        "en": "Light inside the greenhouse is not assessed.",
    },
    "greenhouse.gap.no_heating_assessment": {
        "es": "Las necesidades de calefacción no se evalúan.",
        "en": "Heating needs are not assessed.",
    },
    "greenhouse.gap.no_co2_assessment": {
        "es": "El enriquecimiento con CO₂ no se evalúa.",
        "en": "CO₂ enrichment is not assessed.",
    },
    "greenhouse.gap.no_hail_assessment": {
        "es": "No existe un producto NASA directo de granizo; consulta a productores locales.",
        "en": "There is no direct NASA hail product; ask local growers.",
    },
    "greenhouse.recommend.anchors": {
        "es": "Revisa anclajes, cubierta y ventilas antes de los meses de más viento en tu zona: {months}.",
        "en": "Check anchors, cover and vents before the windiest months in your zone: {months}.",
    },
    "greenhouse.recommend.manufacturer": {
        "es": "Confirma con el fabricante la resistencia de la estructura y de la cubierta a ráfagas.",
        "en": "Confirm with the manufacturer the gust rating of the structure and the cover.",
    },
    "greenhouse.recommend.warn": {
        "es": "Hay un {pct} % de probabilidad al año de que una ráfaga supere los {rated} km/h de la estructura: refuerza anclajes y valida con el fabricante.",
        "en": "There is a {pct}% annual probability that a gust exceeds the structure's {rated} km/h: reinforce anchors and validate with the manufacturer.",
    },
    "greenhouse.recommend.bad": {
        "es": "Hay un {pct} % de probabilidad al año de que una ráfaga supere los {rated} km/h de la estructura: es un riesgo alto; considera una estructura más resistente.",
        "en": "There is a {pct}% annual probability that a gust exceeds the structure's {rated} km/h: the risk is high; consider a stronger structure.",
    },
    "error.chat_disabled": {
        "es": "El chat no está activo en este entorno.",
        "en": "Chat is not enabled in this environment.",
    },
    "error.conversation_full": {
        "es": "La conversación llegó al máximo de mensajes. Abre una conversación nueva para seguir.",
        "en": "The conversation reached its message limit. Open a new conversation to continue.",
    },
    "error.rate_limited": {
        "es": "Enviaste demasiados mensajes. Inténtalo de nuevo más tarde; si alcanzaste el límite diario, podrás seguir mañana.",
        "en": "You sent too many messages. Try again later; if you reached the daily limit, you can continue tomorrow.",
    },
    "error.chat_budget_exhausted": {
        "es": "El chat alcanzó su uso máximo de hoy. Vuelve a intentarlo mañana; el resto de la herramienta sigue disponible.",
        "en": "Chat reached today's maximum usage. Try again tomorrow; the rest of the tool is still available.",
    },
    "error.message_too_long": {
        "es": "El mensaje supera los {max_chars} caracteres.",
        "en": "The message exceeds {max_chars} characters.",
    },
    "error.field_required": {
        "es": "Hace falta indicar una geocerca.",
        "en": "A field is required.",
    },
    "chat.thinking": {
        "es": "Pensando",
        "en": "Thinking",
    },
    "chat.refused": {
        "es": "No puedo responder a eso. Pregúntame sobre tu terreno, tus cultivos o el clima de tu zona.",
        "en": "I can't answer that. Ask me about your field, your crops or your zone's climate.",
    },
    "chat.llm_unavailable": {
        "es": "El asistente no está disponible en este momento. Inténtalo de nuevo en unos minutos.",
        "en": "The assistant is not available right now. Please try again in a few minutes.",
    },
    "chat.tool_limit": {
        "es": "Se alcanzó el máximo de consultas para este mensaje: responde con la información que ya tienes.",
        "en": "The maximum number of lookups for this message was reached: answer with the information you already have.",
    },
    "error.unsupported_file_type": {
        "es": "Solo se admiten archivos PDF, JPG o PNG.",
        "en": "Only PDF, JPG or PNG files are accepted.",
    },
    "error.file_too_large": {
        "es": "El archivo supera los {max_mb} MB.",
        "en": "The file exceeds {max_mb} MB.",
    },
    "error.not_a_soil_report": {
        "es": "El documento no parece un análisis de suelo de laboratorio. La geocerca no cambió.",
        "en": "The document does not look like a laboratory soil analysis. The field was not changed.",
    },
    "error.llm_unavailable": {
        "es": "El servicio que lee los documentos no está disponible. Inténtalo de nuevo en unos minutos.",
        "en": "The document reading service is not available. Please try again in a few minutes.",
    },
    "soil.lab_source": {
        "es": "Análisis de suelo del agricultor",
        "en": "Farmer's soil analysis",
    },
    "soil.lab_unknown": {
        "es": "Laboratorio no indicado",
        "en": "Laboratory not stated",
    },
    "soil.lab_product": {
        "es": "Informe de laboratorio subido por el agricultor",
        "en": "Laboratory report uploaded by the farmer",
    },
    "soil.lab_resolution": {
        "es": "Muestra de la parcela",
        "en": "Sample from the plot",
    },
    "soil.lab_license": {
        "es": "Datos del agricultor; uso privado",
        "en": "Farmer's data; private use",
    },
    "suitability.soil.lab_ph_ok": {
        "es": "pH de {ph} según tu análisis de laboratorio, dentro del rango del cultivo ({low}-{high}).",
        "en": "pH of {ph} according to your laboratory analysis, within the crop range ({low}-{high}).",
    },
    "suitability.soil.lab_ph_warn": {
        "es": "pH de {ph} según tu análisis de laboratorio, ligeramente fuera del rango del cultivo ({low}-{high}).",
        "en": "pH of {ph} according to your laboratory analysis, slightly outside the crop range ({low}-{high}).",
    },
    "suitability.soil.lab_ph_bad": {
        "es": "pH de {ph} según tu análisis de laboratorio, fuera del rango del cultivo ({low}-{high}).",
        "en": "pH of {ph} according to your laboratory analysis, outside the crop range ({low}-{high}).",
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
