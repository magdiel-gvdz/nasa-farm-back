"""Datos sintéticos de referencia: una serie diaria con semilla fija y sus indicadores.

No son observaciones. Sirven para construir y probar la API sin AWS con las mismas
columnas, unidades y definiciones que publica DATA (docs/data_contract.md §2 y §3).
Los indicadores, la climatología y las series anuales se calculan desde la serie diaria,
así que `daily` siempre es coherente con el resto.
"""

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache

SEED = 20261115
FIRST_YEAR, LAST_YEAR = 2016, 2025
LAPSE_RATE_C_PER_KM = 6.5

# Umbrales de diseño de DATA (docs/data_contract.md §2).
FROST_C, HARD_FROST_C = 0.0, -2.0
HOT_C = (30, 32, 35, 38)
HEAVY_RAIN_MM = 25.0
DRY_DAY_MM = 1.0
WATER_STRESS_PCTL = 20.0
WINDY_MS = 10.0
VULNERABLE_FLOOR = 0.2


@dataclass(frozen=True)
class CellSpec:
    """Clima y suelo inventados para una celda; las temperaturas son las de POWER sin ajustar."""

    cell_id: str
    zone_id: str
    zone_name: str
    lat: float
    lon: float
    bounds: tuple[float, float, float, float]  # oeste, norte, este, sur
    cell_elev_m: float
    power_cell_lat: float
    power_cell_lon: float
    power_elev_m: float
    climate_shared_by_n_cells: int
    tmax_mean_c: float
    tmax_amplitude_c: float
    tmin_mean_c: float
    tmin_amplitude_c: float
    temp_noise_c: float
    wet_day_prob_dry_season: float
    wet_day_prob_peak: float
    wet_day_mean_mm: float
    wind_mean_ms: float
    rh_base_pct: float
    soil_top: dict[str, float]
    texture_class: str

    @property
    def temp_offset_c(self) -> float:
        return LAPSE_RATE_C_PER_KM * (self.power_elev_m - self.cell_elev_m) / 1000


CELL_SPECS: dict[str, CellSpec] = {
    spec.cell_id: spec
    for spec in (
        # Saltillo: altiplano templado, heladas de noviembre a marzo, lluvia de verano.
        CellSpec(
            cell_id="E9_r0463_c0846",
            zone_id="coah-sureste",
            zone_name="Sureste",
            lat=25.412697,
            lon=-100.969917,
            bounds=(-101.016598, 25.451695, -100.923237, 25.373712),
            cell_elev_m=1620.0,
            power_cell_lat=25.5,
            power_cell_lon=-101.25,
            power_elev_m=1712.0,
            climate_shared_by_n_cells=20,
            tmax_mean_c=24.0,
            tmax_amplitude_c=6.5,
            tmin_mean_c=9.4,
            tmin_amplitude_c=7.6,
            temp_noise_c=2.9,
            wet_day_prob_dry_season=0.03,
            wet_day_prob_peak=0.32,
            wet_day_mean_mm=7.0,
            wind_mean_ms=2.4,
            rh_base_pct=42.0,
            soil_top={
                "clay_pct": 29.0,
                "sand_pct": 33.0,
                "soc_g_kg": 14.5,
                "nitrogen_g_kg": 1.6,
                "cec_cmol_kg": 21.0,
                "ph": 7.9,
                "bdod_kg_dm3": 1.32,
            },
            texture_class="clay loam",
        ),
        # La Laguna: desierto cálido, calor extremo en verano y lluvia escasa.
        CellSpec(
            cell_id="E9_r0461_c0822",
            zone_id="coah-laguna",
            zone_name="La Laguna",
            lat=25.568761,
            lon=-103.210581,
            bounds=(-103.257261, 25.607808, -103.1639, 25.529727),
            cell_elev_m=1131.6,
            power_cell_lat=25.5,
            power_cell_lon=-103.125,
            power_elev_m=1222.8,
            climate_shared_by_n_cells=24,
            tmax_mean_c=29.6,
            tmax_amplitude_c=8.4,
            tmin_mean_c=13.9,
            tmin_amplitude_c=8.6,
            temp_noise_c=2.6,
            wet_day_prob_dry_season=0.015,
            wet_day_prob_peak=0.17,
            wet_day_mean_mm=6.0,
            wind_mean_ms=2.1,
            rh_base_pct=30.0,
            soil_top={
                "clay_pct": 24.5,
                "sand_pct": 41.0,
                "soc_g_kg": 9.8,
                "nitrogen_g_kg": 1.1,
                "cec_cmol_kg": 18.0,
                "ph": 8.3,
                "bdod_kg_dm3": 1.41,
            },
            texture_class="loam",
        ),
    )
}

SOURCES: list[dict] = [
    {
        "source_id": "nasa_power",
        "name": "NASA POWER Daily (comunidad AG)",
        "organization": "NASA LaRC",
        "product_version": "POWER Daily v2",
        "url": "https://power.larc.nasa.gov/",
        "resolution": "0.5° x 0.625° (~55 km), diaria",
        "used_for": "clima diario: temperatura, lluvia, radiación, humedad y viento",
    },
    {
        "source_id": "smap_l4",
        "name": "SMAP L4 Global Soil Moisture",
        "organization": "NASA JPL/GSFC, NSIDC",
        "product_version": "SPL4SMGP.008",
        "url": "https://nsidc.org/data/spl4smgp",
        "resolution": "9 km, cada 3 h",
        "used_for": "humedad del suelo en la zona de raíces",
    },
    {
        "source_id": "copernicus_dem_glo90",
        "name": "Copernicus DEM GLO-90",
        "organization": "ESA / Copernicus",
        "product_version": "GLO-90",
        "url": "https://registry.opendata.aws/copernicus-dem/",
        "resolution": "~90 m, estático",
        "used_for": "elevación media por celda para corregir la temperatura por altura",
    },
    {
        "source_id": "modis_ndvi",
        "name": "MODIS Vegetation Indices",
        "organization": "NASA, LP DAAC",
        "product_version": "MOD13Q1.061",
        "url": "https://lpdaac.usgs.gov/products/mod13q1v061/",
        "resolution": "250 m, 16 días",
        "used_for": "cobertura vegetal y suelo descubierto",
    },
    {
        "source_id": "soilgrids",
        "name": "SoilGrids 2.0",
        "organization": "ISRIC",
        "product_version": "2.0",
        "url": "https://soilgrids.org/",
        "resolution": "250 m",
        "used_for": "textura, pH, carbono orgánico y nutrientes del suelo",
    },
]


def decade_of(day: date) -> int:
    """Decena del año, de 1 a 36; la tercera de cada mes llega hasta fin de mes."""
    return (day.month - 1) * 3 + min((day.day - 1) // 10, 2) + 1


def _season(day_of_year: int, peak_day: int) -> float:
    return math.cos(2 * math.pi * (day_of_year - peak_day) / 365.25)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@cache
def daily_rows(cell_id: str) -> tuple[dict, ...]:
    """Serie diaria 2016-2025 de la celda, con las columnas de `v_cell_daily`."""
    spec = CELL_SPECS[cell_id]
    rng = random.Random(f"{SEED}:{cell_id}")
    offset = spec.temp_offset_c
    anomaly, root_wetness = 0.0, 0.42
    rows = []
    day = date(FIRST_YEAR, 1, 1)
    while day.year <= LAST_YEAR:
        doy = day.timetuple().tm_yday
        anomaly = 0.6 * anomaly + rng.gauss(0, spec.temp_noise_c * 0.8)
        monsoon = max(0.0, _season(doy, 225)) ** 1.5
        wet_prob = spec.wet_day_prob_dry_season + monsoon * (
            spec.wet_day_prob_peak - spec.wet_day_prob_dry_season
        )
        wet = rng.random() < wet_prob
        precip = round(rng.expovariate(1 / spec.wet_day_mean_mm) + 1.0, 2) if wet else 0.0
        tmax = spec.tmax_mean_c + spec.tmax_amplitude_c * _season(doy, 170) + anomaly
        tmin = (
            spec.tmin_mean_c
            + spec.tmin_amplitude_c * _season(doy, 195)
            + 0.7 * anomaly
            + rng.gauss(0, 1.2)
        )
        if wet:
            tmax, tmin = tmax - 2.5, tmin + 1.0
        tmax, tmin = round(tmax, 2), round(min(tmin, tmax - 2.0), 2)
        tmean = round((tmax + tmin) / 2, 2)
        radiation = 14.5 + 7.0 * _season(doy, 172) - (5.0 if wet else 0.0) + rng.gauss(0, 1.2)
        humidity = spec.rh_base_pct + 18 * monsoon + (25 if wet else 0) + rng.gauss(0, 6)
        wind = max(0.3, rng.gauss(spec.wind_mean_ms, 0.8))
        gusts = wind * 2.0 + abs(rng.gauss(0, 1.5)) + 2.0 * max(0.0, _season(doy, 75))
        root_wetness = _clamp(root_wetness * 0.985 + precip * 0.006, 0.15, 0.95)
        rows.append(
            {
                "cell_id": spec.cell_id,
                "zone_id": spec.zone_id,
                "date": day.isoformat(),
                "tmax_c": tmax,
                "tmin_c": tmin,
                "tmean_c": tmean,
                "tmax_adj_c": round(tmax + offset, 6),
                "tmin_adj_c": round(tmin + offset, 6),
                "tmean_adj_c": round(tmean + offset, 6),
                "temp_adj_applied": True,
                "precip_mm": precip,
                "rad_mj_m2": round(max(3.0, radiation), 2),
                "rh_pct": round(_clamp(humidity, 5, 100), 2),
                "wind_ms": round(wind, 2),
                "wind_max_ms": round(gusts, 2),
                "gwetroot_frac": round(root_wetness, 2),
            }
        )
        day += timedelta(days=1)
    return tuple(rows)


def _extraterrestrial_radiation(lat_deg: float, day_of_year: int) -> float:
    """Ra en MJ/m²/día (FAO-56, ecuación 21)."""
    lat = math.radians(lat_deg)
    inverse_distance = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset = math.acos(-math.tan(lat) * math.tan(declination))
    return (
        (24 * 60 / math.pi)
        * 0.0820
        * inverse_distance
        * (
            sunset * math.sin(lat) * math.sin(declination)
            + math.cos(lat) * math.cos(declination) * math.sin(sunset)
        )
    )


def _et0_mm(lat_deg: float, day: date, tmax: float, tmin: float, tmean: float) -> float:
    """ET de referencia de un día, Hargreaves-Samani (FAO-56, ecuación 52)."""
    radiation = _extraterrestrial_radiation(lat_deg, day.timetuple().tm_yday)
    return 0.0023 * 0.408 * radiation * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0))


def _percentile(values: list[float], q: float) -> float:
    """Percentil con interpolación lineal entre los valores ordenados."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _moisture_percentiles(days: list[dict]) -> list[float]:
    """Percentil (0-100) de la humedad de cada día dentro de su misma decena, entre años."""
    by_decade: dict[int, list[float]] = {}
    for row in days:
        by_decade.setdefault(row["decade"], []).append(row["gwetroot_frac"])
    percentiles = []
    for row in days:
        values = by_decade[row["decade"]]
        below = sum(value < row["gwetroot_frac"] for value in values)
        equal = sum(value == row["gwetroot_frac"] for value in values)
        percentiles.append(100 * (below + 0.5 * equal) / len(values))
    return percentiles


def _event_counts(days: list[dict]) -> dict:
    return {
        "frost_days": sum(row["tmin_adj_c"] < FROST_C for row in days),
        "frost_days_m2": sum(row["tmin_adj_c"] < HARD_FROST_C for row in days),
        **{f"hot_days_{t}": sum(row["tmax_adj_c"] > t for row in days) for t in HOT_C},
    }


def _water_and_wind(days: list[dict]) -> dict:
    precip = sum(row["precip_mm"] for row in days)
    et0 = sum(row["et0_mm"] for row in days)
    return {
        "precip_mm": round(precip, 2),
        "et0_mm": round(et0, 6),
        "p_minus_et0_mm": round(precip - et0, 6),
        "heavy_rain_days": sum(row["precip_mm"] > HEAVY_RAIN_MM for row in days),
        "dry_spell_max_d": max(row["dry_spell_d"] for row in days),
    }


def _enriched_days(spec: CellSpec) -> list[dict]:
    days = [dict(row) for row in daily_rows(spec.cell_id)]
    dry_spell = 0
    for row in days:
        day = date.fromisoformat(row["date"])
        dry_spell = dry_spell + 1 if row["precip_mm"] < DRY_DAY_MM else 0
        row.update(
            year=day.year,
            decade=decade_of(day),
            dry_spell_d=dry_spell,
            et0_mm=_et0_mm(spec.lat, day, row["tmax_adj_c"], row["tmin_adj_c"], row["tmean_adj_c"]),
        )
    for row, percentile in zip(days, _moisture_percentiles(days), strict=True):
        row["moisture_pctl"] = percentile
    return days


def indicator_rows(cell_id: str) -> list[dict]:
    """`v_cell_indicators`: una fila por año y decena."""
    spec = CELL_SPECS[cell_id]
    groups: dict[tuple[int, int], list[dict]] = {}
    for row in _enriched_days(spec):
        groups.setdefault((row["year"], row["decade"]), []).append(row)
    rows = []
    for (year, decade), days in sorted(groups.items()):
        counts = _event_counts(days)
        water = _water_and_wind(days)
        rows.append(
            {
                "cell_id": spec.cell_id,
                "zone_id": spec.zone_id,
                "year": year,
                "decade": decade,
                "month": (decade - 1) // 3 + 1,
                "n_days": len(days),
                "tmax_mean": round(sum(row["tmax_adj_c"] for row in days) / len(days), 6),
                "tmin_mean": round(sum(row["tmin_adj_c"] for row in days) / len(days), 6),
                **counts,
                **water,
                "smp_mean": round(sum(row["moisture_pctl"] for row in days) / len(days), 2),
                "ws_days": sum(row["moisture_pctl"] < WATER_STRESS_PCTL for row in days),
                "wind_max_ms": max(row["wind_max_ms"] for row in days),
                "windy_days": sum(row["wind_max_ms"] > WINDY_MS for row in days),
                "ndvi_mean": None,
                "bare_obs": None,
                "precip_src": "power",
                "sm_src": "power_gwetroot",
                "temp_adj_applied": True,
                "complete": True,
            }
        )
    return rows


def year_rows(cell_id: str) -> list[dict]:
    """`v_cell_year`: una fila por año."""
    spec = CELL_SPECS[cell_id]
    groups: dict[int, list[dict]] = {}
    for row in _enriched_days(spec):
        groups.setdefault(row["year"], []).append(row)
    rows = []
    for year, days in sorted(groups.items()):
        rows.append(
            {
                "cell_id": spec.cell_id,
                "zone_id": spec.zone_id,
                "year": year,
                "tmax_mean": round(sum(row["tmax_adj_c"] for row in days) / len(days), 6),
                "tmin_mean": round(sum(row["tmin_adj_c"] for row in days) / len(days), 6),
                **_event_counts(days),
                **_water_and_wind(days),
                "ws_days": sum(row["moisture_pctl"] < WATER_STRESS_PCTL for row in days),
                "wind_max_ms": max(row["wind_max_ms"] for row in days),
                "windy_days": sum(row["wind_max_ms"] > WINDY_MS for row in days),
                "n_decades_complete": 36,
                "complete_year": True,
                "source_flags": "precip=power;sm=power_gwetroot;temp=elevation_adjusted",
            }
        )
    return rows


# Probabilidad que decide cada motivo de vulnerabilidad (el calor usa el umbral de 35 °C).
_VULNERABLE_REASONS = {
    "frost": "frost_prob",
    "heat": "hot_prob_35",
    "water_stress": "ws_prob",
    "heavy_rain": "heavy_rain_prob",
}


def climatology_rows(cell_id: str) -> list[dict]:
    """`v_cell_profile`: 36 filas; probabilidad = fracción de años con al menos un evento."""
    spec = CELL_SPECS[cell_id]
    by_decade: dict[int, list[dict]] = {}
    for row in indicator_rows(cell_id):
        by_decade.setdefault(row["decade"], []).append(row)

    def probability(years: list[dict], column: str) -> float:
        return round(sum(row[column] > 0 for row in years) / len(years), 1)

    rows = []
    for decade, years in sorted(by_decade.items()):
        precip = [row["precip_mm"] for row in years]
        moisture = [row["smp_mean"] for row in years]
        rows.append(
            {
                "cell_id": spec.cell_id,
                "zone_id": spec.zone_id,
                "decade": decade,
                "month": (decade - 1) // 3 + 1,
                "frost_prob": probability(years, "frost_days"),
                "frost_m2_prob": probability(years, "frost_days_m2"),
                **{f"hot_prob_{t}": probability(years, f"hot_days_{t}") for t in HOT_C},
                "ws_prob": probability(years, "ws_days"),
                "bare_prob": None,
                "heavy_rain_prob": probability(years, "heavy_rain_days"),
                "windy_prob": probability(years, "windy_days"),
                "precip_p10": round(_percentile(precip, 10), 3),
                "precip_p50": round(_percentile(precip, 50), 3),
                "precip_p90": round(_percentile(precip, 90), 3),
                "et0_p50": round(_percentile([row["et0_mm"] for row in years], 50), 6),
                "smp_p10": round(_percentile(moisture, 10), 3),
                "smp_p50": round(_percentile(moisture, 50), 3),
                "smp_p90": round(_percentile(moisture, 90), 3),
                "n_years": len(years),
            }
        )
    # Decena vulnerable: probabilidad sobre el percentil 75 de la celda y de al menos 0.2.
    thresholds = {
        column: _percentile([row[column] for row in rows], 75)
        for column in _VULNERABLE_REASONS.values()
    }
    for row in rows:
        reasons = [
            reason
            for reason, column in _VULNERABLE_REASONS.items()
            if row[column] > thresholds[column] and row[column] >= VULNERABLE_FLOOR
        ]
        row["vulnerable"] = bool(reasons)
        row["vulnerable_reasons"] = ",".join(reasons)
    return rows


def cell_row(cell_id: str) -> dict:
    """`v_cells`."""
    spec = CELL_SPECS[cell_id]
    west, north, east, south = spec.bounds
    ring = [(west, north), (east, north), (east, south), (west, south), (west, north)]
    return {
        "cell_id": spec.cell_id,
        "zone_id": spec.zone_id,
        "zone_name": spec.zone_name,
        "lat": spec.lat,
        "lon": spec.lon,
        "geometry_wkt": "POLYGON((" + ", ".join(f"{lon:.6f} {lat:.6f}" for lon, lat in ring) + "))",
        "cell_elev_m": spec.cell_elev_m,
        "cell_elev_source": "copernicus_dem_glo90",
        "power_cell_lat": spec.power_cell_lat,
        "power_cell_lon": spec.power_cell_lon,
        "power_elev_m": spec.power_elev_m,
        "climate_shared_by_n_cells": spec.climate_shared_by_n_cells,
    }


# Cómo cambia cada propiedad con la profundidad respecto a la capa 0-5 cm.
_SOIL_DEPTHS = (("0-5", 0, 5, 1.0), ("5-15", 5, 15, 0.82), ("15-30", 15, 30, 0.64))
_UNCERTAINTY = {"ph": (0.92, 1.07), "bdod_kg_dm3": (0.78, 1.22)}


def soil_rows(cell_id: str) -> list[dict]:
    """`v_cell_soil`: tres profundidades con la incertidumbre del modelo (`_p05`, `_p95`)."""
    spec = CELL_SPECS[cell_id]
    rows = []
    for depth, top, bottom, organic_factor in _SOIL_DEPTHS:
        values = dict(spec.soil_top)
        for column in ("soc_g_kg", "nitrogen_g_kg"):
            values[column] *= organic_factor
        values["clay_pct"] += (1 - organic_factor) * 8
        values["bdod_kg_dm3"] += (1 - organic_factor) * 0.2
        values["silt_pct"] = 100 - values["clay_pct"] - values["sand_pct"]
        row = {
            "cell_id": spec.cell_id,
            "zone_id": spec.zone_id,
            "depth_cm": depth,
            "depth_top_cm": top,
            "depth_bottom_cm": bottom,
        }
        for column in (
            "clay_pct",
            "sand_pct",
            "silt_pct",
            "soc_g_kg",
            "nitrogen_g_kg",
            "cec_cmol_kg",
            "ph",
            "bdod_kg_dm3",
        ):
            low, high = _UNCERTAINTY.get(column, (0.45, 1.75))
            row[column] = round(values[column], 3)
            row[f"{column}_p05"] = round(values[column] * low, 3)
            row[f"{column}_p95"] = round(values[column] * high, 3)
        row["om_pct_est"] = round(values["soc_g_kg"] * 1.724 / 10, 3)
        row["texture_class"] = spec.texture_class
        row["valid_pixel_pct"] = 96.0
        row["low_coverage"] = False
        rows.append(row)
    return rows


def source_rows() -> list[dict]:
    """`v_sources`, con todas las fuentes marcadas como dato sintético."""
    return [
        {
            "source_id": source["source_id"],
            "name": source["name"],
            "organization": source["organization"],
            "product_version": source["product_version"],
            "url": source["url"],
            "resolution": source["resolution"],
            "period": f"{FIRST_YEAR}-{LAST_YEAR}",
            "access_date": None,
            "license": "Datos sintéticos de prueba; no proceden de esta fuente",
            "data_class": "synthetic",
            "status": "in_use",
            "used_for": source["used_for"],
        }
        for source in SOURCES
    ]
