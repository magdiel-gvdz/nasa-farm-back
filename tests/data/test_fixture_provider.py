import dataclasses
import typing
from datetime import date

import pytest

from app.config import Settings
from app.data import create_provider, models, synthetic
from app.data.fixture import FixtureProvider
from scripts import build_fixtures
from tests.data.conformance import check_provider

SALTILLO = "E9_r0463_c0846"
LA_LAGUNA = "E9_r0461_c0822"
MODELS = (
    models.Cell,
    models.Zone,
    models.ClimatologyDecade,
    models.IndicatorDecade,
    models.IndicatorYear,
    models.SoilLayer,
    models.Source,
    models.DailyRow,
)


@pytest.fixture(scope="module")
def provider():
    return FixtureProvider()


@pytest.mark.parametrize("model", MODELS)
def test_models_accept_missing_values_as_none(model):
    hints = typing.get_type_hints(model)
    values = {}
    for column in dataclasses.fields(model):
        nullable = type(None) in typing.get_args(hints[column.name])
        base = next(t for t in (typing.get_args(hints[column.name]) or (hints[column.name],)))
        values[column.name] = None if nullable else base()
    row = model(**values)
    assert any(value is None for value in dataclasses.astuple(row)) or model is models.Zone


def test_fixture_provider_conforms_to_the_interface(provider):
    check_provider(provider)


def test_default_provider_is_the_fixture_one():
    assert Settings().data_provider == "fixture"
    assert isinstance(create_provider(Settings().data_provider), FixtureProvider)


def test_unknown_provider_name_is_rejected(caplog):
    with pytest.raises(ValueError, match="athena-v9"):
        create_provider("athena-v9")
    assert "athena-v9" in caplog.text


def test_reference_cells_cover_both_zones_for_ten_years(provider):
    zones = {cell.cell_id: cell.zone_id for cell in provider.cells()}
    assert zones == {SALTILLO: "coah-sureste", LA_LAGUNA: "coah-laguna"}
    for cell_id in zones:
        assert len(provider.climatology(cell_id)) == 36
        assert len(provider.indicators(cell_id)) == 360
        assert [row.year for row in provider.years(cell_id)] == list(range(2016, 2026))
        assert [row.depth_cm for row in provider.soil(cell_id)] == ["0-5", "5-15", "15-30"]
        assert provider.daily(cell_id)[0].date == "2016-01-01"
        assert provider.daily(cell_id)[-1].date == "2025-12-31"


def test_ndvi_is_missing_rather_than_filled(provider):
    assert all(row.ndvi_mean is None for row in provider.indicators(SALTILLO))
    assert all(row.bare_prob is None for row in provider.climatology(SALTILLO))


def test_sources_are_flagged_as_synthetic(provider):
    assert provider.data_version() == "fixture"
    assert {source.data_class for source in provider.sources()} == {"synthetic"}


def test_saltillo_has_frost_only_from_november_to_march(provider):
    frost_months = {row.month for row in provider.climatology(SALTILLO) if row.frost_prob}
    assert {12, 1, 2} <= frost_months <= {11, 12, 1, 2, 3}


def test_la_laguna_is_hotter_and_drier_than_saltillo(provider):
    def yearly_mean(cell_id, column):
        years = provider.years(cell_id)
        return sum(getattr(row, column) for row in years) / len(years)

    assert yearly_mean(LA_LAGUNA, "hot_days_38") > 20 > yearly_mean(SALTILLO, "hot_days_38")
    assert yearly_mean(LA_LAGUNA, "precip_mm") < 250 < yearly_mean(SALTILLO, "precip_mm")


def test_committed_files_match_the_generator():
    first, second = build_fixtures.render(), build_fixtures.render()
    assert first == second
    for name, content in first.items():
        path = build_fixtures.FIXTURES / f"{name}.json"
        assert path.read_text(encoding="utf-8") == content, f"{name}.json: regenerar"


def test_two_providers_return_identical_rows():
    first, second = FixtureProvider(), FixtureProvider()
    assert first.indicators(SALTILLO) == second.indicators(SALTILLO)
    assert first.daily(LA_LAGUNA) == second.daily(LA_LAGUNA)


def test_daily_series_agrees_with_the_indicators(provider):
    for row in provider.indicators(SALTILLO)[:72]:
        days = [
            day
            for day in provider.daily(SALTILLO)
            if day.date.startswith(str(row.year))
            and synthetic.decade_of(date.fromisoformat(day.date)) == row.decade
        ]
        assert len(days) == row.n_days
        assert round(sum(day.precip_mm for day in days), 2) == row.precip_mm
        assert sum(day.tmin_adj_c < 0 for day in days) == row.frost_days
        assert sum(day.tmax_adj_c > 35 for day in days) == row.hot_days_35
        assert max(day.wind_max_ms for day in days) == row.wind_max_ms
