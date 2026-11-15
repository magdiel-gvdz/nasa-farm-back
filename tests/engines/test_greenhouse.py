import dataclasses
import math
import random

import pytest
from fastapi.testclient import TestClient

from app.api.schemas.greenhouse import GreenhouseAssessment
from app.data import DataUnavailableError
from app.data.fixture import FixtureProvider
from app.data.models import DailyRow
from app.engines.config import load_config
from app.engines.greenhouse import annual_maxima, assess, fit_gumbel, riskiest_months
from app.main import create_app
from tests.helpers import field_payload

SALTILLO = "E9_r0463_c0846"


@pytest.fixture(scope="module")
def config():
    return load_config().greenhouse


def series(years: int, *, wind=lambda year, day: 8.0, days_per_year: int = 365) -> list[DailyRow]:
    rows = []
    for year in range(2000, 2000 + years):
        for day in range(days_per_year):
            month = min(12, day // 31 + 1)
            rows.append(
                DailyRow(
                    cell_id="c",
                    zone_id="z",
                    date=f"{year}-{month:02d}-{day % 28 + 1:02d}",
                    tmax_c=None,
                    tmin_c=None,
                    tmean_c=None,
                    tmax_adj_c=None,
                    tmin_adj_c=None,
                    tmean_adj_c=None,
                    temp_adj_applied=False,
                    precip_mm=None,
                    rad_mj_m2=None,
                    rh_pct=None,
                    wind_ms=None,
                    wind_max_ms=wind(year, day),
                    gwetroot_frac=None,
                )
            )
    return rows


# ---------------------------------------------------------------- motor


def test_gumbel_recovers_known_parameters():
    rng = random.Random(7)
    location, scale = 60.0, 8.0
    sample = [location - scale * math.log(-math.log(rng.random())) for _ in range(2000)]
    fitted = fit_gumbel(sample)
    for period in (10, 25, 50):
        theoretical = location - scale * math.log(-math.log(1 - 1 / period))
        assert fitted.return_level(period) == pytest.approx(theoretical, rel=0.10)


def test_return_levels_and_exceedance_by_hand():
    gumbel = fit_gumbel([50.0, 60.0, 70.0])
    # σ = 10 → β = √6·10/π = 7.797; μ = 60 − 0.5772·7.797 = 55.50
    assert gumbel.scale == pytest.approx(7.797, abs=0.001)
    assert gumbel.location == pytest.approx(55.50, abs=0.01)
    assert gumbel.return_level(10) == pytest.approx(55.50 + 7.797 * 2.2504, abs=0.02)
    assert gumbel.exceedance_probability(gumbel.return_level(50)) == pytest.approx(0.02, abs=1e-9)


def test_only_years_with_360_days_count():
    rows = series(3) + series(1, days_per_year=300)
    assert len(annual_maxima(rows, 360)) == 3


def test_ten_years_is_low_confidence_with_the_gap(config):
    rows = series(10, wind=lambda year, day: 10 + (year % 5) + (day == 40) * 5)
    result = assess(rows, 100, config, "es")
    levels = result["wind"]["return_levels_kmh"]
    assert [level["return_period_years"] for level in levels] == [10, 25, 50]
    assert levels[0]["sustained_kmh"] < levels[1]["sustained_kmh"] < levels[2]["sustained_kmh"]
    for level in levels:
        assert level["estimated_gust_kmh"] == pytest.approx(level["sustained_kmh"] * 1.4, abs=0.1)
    assert result["confidence"] == "low"
    gap = next(gap for gap in result["gaps"] if gap["code"] == "short_wind_record")
    assert "10 años" in gap["message"]
    assert result["wind"]["status"] in {"ok", "warn", "bad"}
    assert 0 <= result["wind"]["annual_exceedance_probability"] <= 1


def test_long_record_is_medium_confidence(config):
    rows = series(20, wind=lambda year, day: 10 + (year % 7))
    assert assess(rows, 100, config, "es")["confidence"] == "medium"


def test_four_years_gives_no_return_levels(config):
    result = assess(series(4), 100, config, "es")
    assert result["wind"]["return_levels_kmh"] is None
    assert result["wind"]["status"] is None
    assert "insufficient_wind_record" in {gap["code"] for gap in result["gaps"]}


def test_without_rated_wind_status_is_null(config):
    result = assess(series(10, wind=lambda year, day: 10 + year % 3), None, config, "en")
    assert result["wind"]["return_levels_kmh"] is not None
    assert (
        result["wind"]["status"] is None and result["wind"]["annual_exceedance_probability"] is None
    )
    assert "no_rated_wind" in {gap["code"] for gap in result["gaps"]}


@pytest.mark.parametrize(("rated", "status"), [(400, "ok"), (78, "bad")])
def test_status_follows_the_probability_cuts(config, rated, status):
    rows = series(20, wind=lambda year, day: 12 + (year % 7) * 0.8)
    assert assess(rows, rated, config, "es")["wind"]["status"] == status


def test_windiest_months_come_first():
    rows = series(5, wind=lambda year, day: 20.0 if day // 31 + 1 == 3 else 8.0)
    assert riskiest_months(rows)[0] == 3


# ---------------------------------------------------------------- endpoint


GREENHOUSE = {"structure": "multitunel", "cover": "polietileno", "rated_wind_kmh": 100}


def test_greenhouse_endpoint(client, headers):
    payload = field_payload(kind="greenhouse", greenhouse=GREENHOUSE)
    field = client.post("/api/v1/fields", json=payload, headers=headers).json()
    response = client.get(f"/api/v1/fields/{field['id']}/greenhouse", headers=headers)
    assert response.status_code == 200
    body = GreenhouseAssessment.model_validate(response.json())
    assert body.wind.rated_wind_kmh == 100 and body.wind.gust_factor_assumed == 1.4
    assert body.wind.daily_origin == "synthetic" and body.confidence == "low"
    assert body.light is None and body.hail is None
    codes = {gap.code for gap in body.gaps}
    assert {"short_wind_record", "no_light_assessment", "no_hail_assessment"} <= codes
    assert "55 km" in body.wind.note and "fabricante" in body.wind.note
    assert len(body.recommendations) >= 2


def test_field_that_is_not_a_greenhouse_is_409(client, headers, field):
    response = client.get(f"/api/v1/fields/{field['id']}/greenhouse", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_a_greenhouse"


class NoDaily(FixtureProvider):
    def daily(self, cell_id):
        raise DataUnavailableError("sin serie diaria")


def test_without_daily_series_is_503(settings, headers):
    client = TestClient(create_app(settings, data_provider=NoDaily()))
    payload = field_payload(kind="greenhouse", greenhouse=GREENHOUSE)
    field = client.post("/api/v1/fields", json=payload, headers=headers).json()
    response = client.get(f"/api/v1/fields/{field['id']}/greenhouse", headers=headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "daily_unavailable"


def test_real_length_record_gives_medium_confidence(config):
    daily = FixtureProvider().daily(SALTILLO)
    # La serie sintética trae 10 años; replicada a 30 imita la vista real 1991-2025.
    long = [
        dataclasses.replace(row, date=f"{int(row.date[:4]) - 10 * k}{row.date[4:]}")
        for k in range(3)
        for row in daily
    ]
    assert assess(long, 100, config, "es")["confidence"] == "medium"
