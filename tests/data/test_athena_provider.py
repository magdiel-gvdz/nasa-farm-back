import json
import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data import DataUnavailableError, UnknownCellError, create_provider
from app.data.athena import (
    AthenaProvider,
    DailyUnavailableError,
    SnapshotError,
    check_query,
    load_snapshot,
)
from app.main import create_app
from app.profile.builder import build_profile
from tests.data.conformance import check_provider
from tests.helpers import field_payload

SAMPLE = Path(__file__).resolve().parents[2] / "docs" / "data_sample"
SALTILLO = "E9_r0463_c0845"
LA_LAGUNA = "E9_r0461_c0822"
SNAPSHOT_VIEWS = (
    "v_cells",
    "v_cell_profile",
    "v_cell_indicators",
    "v_cell_year",
    "v_cell_soil",
    "v_sources",
)


def _as_text(value):
    """Athena entrega cada valor como texto; un nulo no trae valor."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def sample_rows(view: str) -> list[dict]:
    rows = json.loads((SAMPLE / f"{view}.json").read_text(encoding="utf-8"))
    return [{key: _as_text(value) for key, value in row.items()} for row in rows]


class FakeExecutor:
    """Sirve la muestra real de DATA y anota cada consulta."""

    def __init__(self):
        self.views = {view: sample_rows(view) for view in (*SNAPSHOT_VIEWS, "v_cell_daily")}
        self.queries: list[tuple[str, tuple]] = []
        self.failures: dict[str, Exception] = {}
        self.after_query = None

    def run(self, sql, parameters=()):
        view = check_query(sql)
        self.queries.append((sql, tuple(parameters)))
        if self.after_query:
            self.after_query(view)
        if view in self.failures:
            raise self.failures[view]
        rows = self.views[view]
        if parameters:
            rows = [row for row in rows if row["cell_id"] == parameters[0]]
        return [dict(row) for row in rows]


class FakeVersions:
    def __init__(self, version="2026111500"):
        self.version = version
        self.reads = 0

    def current(self):
        self.reads += 1
        if isinstance(self.version, Exception):
            raise self.version
        return self.version


@pytest.fixture
def executor():
    return FakeExecutor()


@pytest.fixture
def versions():
    return FakeVersions()


@pytest.fixture
def provider(executor, versions):
    provider = AthenaProvider(executor, versions)
    assert provider.refresh() is True
    return provider


# ---------------------------------------------------------------- carga


def test_only_selects_over_published_views_are_issued(provider, executor):
    assert [sql for sql, _ in executor.queries] == [
        "SELECT * FROM v_cells",
        "SELECT * FROM v_sources",
    ]
    provider.climatology(SALTILLO)
    per_cell = sorted(sql for sql, _ in executor.queries[2:])
    assert per_cell == [
        "SELECT * FROM v_cell_indicators WHERE cell_id = ?",
        "SELECT * FROM v_cell_profile WHERE cell_id = ?",
        "SELECT * FROM v_cell_soil WHERE cell_id = ?",
        "SELECT * FROM v_cell_year WHERE cell_id = ?",
    ]
    assert all(parameters == (SALTILLO,) for _, parameters in executor.queries[2:])


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM indicators_decade",
        "CREATE TABLE x AS SELECT * FROM v_cells",
        "UNLOAD (SELECT * FROM v_cells) TO 's3://bucket/'",
        "SELECT * FROM v_cells; DROP VIEW v_cells",
        "SELECT * FROM v_cells WHERE cell_id = 'x'",
        "INSERT INTO v_cells SELECT * FROM v_cells",
    ],
)
def test_anything_else_is_refused_before_reaching_athena(sql):
    with pytest.raises(ValueError):
        check_query(sql)


def test_provider_with_the_real_sample_conforms_to_the_interface(provider):
    check_provider(provider)
    assert provider.data_version() == "2026111500"
    assert {cell.cell_id for cell in provider.cells()} == {SALTILLO, LA_LAGUNA}
    assert len(provider.indicators(SALTILLO)) == 360
    assert provider.soil(SALTILLO)[0].awc_mm_per_m is not None
    assert [row.depth_cm for row in provider.soil(LA_LAGUNA)] == ["0-5", "5-15", "15-30"]


def test_nan_fills_and_empty_values_become_none(executor, versions):
    executor.views["v_cell_indicators"][0]["ndvi_mean"] = "NaN"
    executor.views["v_cell_indicators"][1]["smp_mean"] = "-999"
    executor.views["v_cell_indicators"][2]["wind_max_ms"] = ""
    provider = AthenaProvider(executor, versions)
    provider.refresh()
    first = provider.indicators(executor.views["v_cell_indicators"][0]["cell_id"])
    assert all(row.ndvi_mean is None for row in first)
    assert sum(row.smp_mean is None for row in first) == 1
    assert sum(row.wind_max_ms is None for row in first) == 1
    assert isinstance(first[0].frost_days, int) and isinstance(first[0].complete, bool)


def test_source_data_class_is_normalized_to_the_api_values(provider):
    classes = {source.source_id: source.data_class for source in provider.sources()}
    assert set(classes.values()) <= {"observation", "model", "estimate", "derived"}
    assert classes["nasa_power"] == "model"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("modelo (reanálisis MERRA-2)", "model"),
        ("observación asimilada en modelo", "observation"),
        ("estimación (modelo sobre perfiles de suelo)", "estimate"),
        ("derivado", "derived"),
        ("algo nuevo", "estimate"),
    ],
)
def test_free_text_data_classes_map_by_their_first_word(text, expected):
    from app.data.athena import _data_class

    assert _data_class(text) == expected


def test_missing_required_column_is_reported_naming_view_and_column(provider, executor, caplog):
    for row in executor.views["v_cell_profile"]:
        del row["frost_prob"]
    with caplog.at_level(logging.ERROR), pytest.raises(DataUnavailableError):
        provider.climatology(SALTILLO)
    assert "v_cell_profile" in caplog.text and "frost_prob" in caplog.text


def test_missing_column_in_a_snapshot_view_rejects_the_load(executor, versions, caplog):
    for row in executor.views["v_cells"]:
        del row["power_elev_m"]
    provider = AthenaProvider(executor, versions)
    with caplog.at_level(logging.ERROR):
        assert provider.refresh() is False
    assert not provider.is_ready()
    assert "v_cells" in caplog.text and "power_elev_m" in caplog.text


def test_extra_columns_are_ignored(executor, versions):
    for row in executor.views["v_cells"]:
        row["new_column_from_data"] = "42"
    provider = AthenaProvider(executor, versions)
    assert provider.refresh() is True and provider.is_ready()


@pytest.mark.parametrize("view", ["v_cells", "v_sources"])
def test_empty_view_rejects_the_load(executor, view):
    executor.views[view] = []
    with pytest.raises(SnapshotError, match=view):
        load_snapshot(executor, "v1")


def test_cell_without_its_36_decades_is_not_served(provider, executor):
    executor.views["v_cell_profile"] = [
        row
        for row in executor.views["v_cell_profile"]
        if not (row["cell_id"] == SALTILLO and row["decade"] == "36")
    ]
    with pytest.raises(DataUnavailableError):
        provider.climatology(SALTILLO)
    assert len(provider.climatology(LA_LAGUNA)) == 36


def test_null_in_a_required_column_rejects_the_load(executor):
    executor.views["v_cells"][0]["zone_id"] = None
    with pytest.raises(SnapshotError, match="zone_id"):
        load_snapshot(executor, "v1")


# ---------------------------------------------------------------- ciclo de vida


def test_a_cell_is_read_once_and_then_served_from_memory(provider, executor):
    build_profile(provider, SALTILLO, "es")
    executor.queries.clear()
    build_profile(provider, SALTILLO, "es")
    provider.climatology(SALTILLO)
    provider.sources()
    provider.cells()
    assert executor.queries == []


def test_new_version_does_not_reuse_cell_data(provider, executor, versions):
    before = provider.climatology(SALTILLO)
    versions.version = "2026111612"
    provider.refresh()
    executor.queries.clear()
    after = provider.climatology(SALTILLO)
    assert after is not before and len(executor.queries) == 4


def test_same_version_does_not_run_any_query(provider, executor, versions):
    executor.queries.clear()
    assert provider.refresh() is False
    assert executor.queries == [] and versions.reads >= 1


def test_new_version_is_loaded_and_swapped(provider, executor, versions):
    executor.views["v_cells"][0]["cell_elev_m"] = "1234.5"
    versions.version = "2026111612"
    assert provider.refresh() is True
    assert provider.data_version() == "2026111612"
    assert provider.cell(executor.views["v_cells"][0]["cell_id"]).cell_elev_m == 1234.5


def test_failed_reload_keeps_the_last_good_snapshot(provider, executor, versions, caplog):
    executor.failures["v_sources"] = RuntimeError("Access denied on gold/")
    versions.version = "2026111612"
    with caplog.at_level(logging.ERROR):
        assert provider.refresh() is False
    assert provider.is_ready() and provider.data_version() == "2026111500"
    assert "v_sources" in caplog.text and "Access denied" in caplog.text
    del executor.failures["v_sources"]
    assert provider.refresh() is True and provider.data_version() == "2026111612"


def test_failed_initial_load_leaves_data_unavailable(executor, versions):
    executor.failures["v_cells"] = RuntimeError("workgroup not found")
    provider = AthenaProvider(executor, versions)
    assert provider.refresh() is False
    assert not provider.is_ready() and provider.data_version() is None
    for query in (provider.cells, provider.sources, lambda: provider.cell(SALTILLO)):
        with pytest.raises(DataUnavailableError):
            query()


@pytest.mark.parametrize("unpublished", [None, RuntimeError("ssm throttled")])
def test_no_publication_waits_without_querying_views(executor, unpublished):
    versions = FakeVersions(unpublished)
    provider = AthenaProvider(executor, versions)
    assert provider.refresh() is False
    assert executor.queries == [] and not provider.is_ready()
    versions.version = "2026111500"
    assert provider.refresh() is True and provider.is_ready()


def test_previous_snapshot_survives_when_the_parameter_goes_back_to_none(provider, versions):
    versions.version = None
    assert provider.refresh() is False
    assert provider.is_ready() and provider.data_version() == "2026111500"


def test_version_changing_during_the_load_is_not_accepted(executor, versions):
    def publish(view):
        if view == "v_sources":
            versions.version = "2026111612"

    executor.after_query = publish
    provider = AthenaProvider(executor, versions)
    assert provider.refresh() is False and not provider.is_ready()
    executor.after_query = None
    assert provider.refresh() is True and provider.data_version() == "2026111612"


def test_load_is_logged_with_version_cells_and_duration(executor, versions, caplog):
    with caplog.at_level(logging.INFO):
        AthenaProvider(executor, versions).refresh()
    assert "2026111500" in caplog.text and "2 celdas" in caplog.text


def test_background_loop_makes_the_provider_ready(executor, versions):
    provider = AthenaProvider(executor, versions, poll_seconds=0.01)
    provider.start()
    try:
        deadline = time.monotonic() + 5
        while not provider.is_ready() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert provider.is_ready()
        versions.version = "2026111612"
        while provider.data_version() != "2026111612" and time.monotonic() < deadline:
            time.sleep(0.01)
        assert provider.data_version() == "2026111612"
    finally:
        provider.stop()


# ---------------------------------------------------------------- serie diaria


def test_daily_series_is_read_on_demand_and_cached_per_cell(provider, executor):
    executor.queries.clear()
    series = provider.daily(SALTILLO)
    assert series[0].date == "2025-01-01" and series[-1].date == "2025-12-31"
    assert [row.date for row in series] == sorted(row.date for row in series)
    assert provider.daily(SALTILLO) is series
    assert executor.queries == [
        ("SELECT * FROM v_cell_daily WHERE cell_id = ? ORDER BY date", (SALTILLO,))
    ]
    with pytest.raises(UnknownCellError):
        provider.daily("E9_r0001_c0001")


def test_daily_fill_values_become_none(provider, executor):
    row = next(r for r in executor.views["v_cell_daily"] if r["cell_id"] == SALTILLO)
    row["precip_mm"] = "-999"
    assert provider.daily(SALTILLO)[0].precip_mm is None


def test_new_version_does_not_reuse_the_daily_cache(provider, executor, versions):
    before = provider.daily(SALTILLO)
    versions.version = "2026111612"
    provider.refresh()
    executor.queries.clear()
    after = provider.daily(SALTILLO)
    assert after is not before and len(executor.queries) == 1


@pytest.mark.parametrize(
    ("error", "cause"),
    [
        (
            RuntimeError("TABLE_NOT_FOUND: line 1:15: Table 'v_cell_daily' does not exist"),
            "la vista no existe",
        ),
        (RuntimeError("Access denied when reading gold/daily"), "Access denied"),
    ],
)
def test_daily_failures_are_reported_with_their_cause(provider, executor, caplog, error, cause):
    executor.failures["v_cell_daily"] = error
    with caplog.at_level(logging.ERROR), pytest.raises(DailyUnavailableError):
        provider.daily(SALTILLO)
    assert cause in caplog.text


def test_profile_still_answers_without_the_daily_series(provider, executor):
    executor.failures["v_cell_daily"] = RuntimeError("timeout")
    profile = build_profile(provider, SALTILLO, "es")
    assert profile["status"] == "ready" and profile["data_version"] == "2026111500"
    assert profile["climate"]["frost"]["last_spring_frost"] is None
    assert "no_daily_series" in {gap["code"] for gap in profile["gaps"]}
    assert "synthetic_data" not in {gap["code"] for gap in profile["gaps"]}


# ---------------------------------------------------------------- activación y API


def test_athena_without_its_variables_does_not_start(caplog):
    settings = Settings(
        data_provider="athena", data_region="us-west-2", athena_workgroup="fieldshift"
    )
    with pytest.raises(ValueError, match="ATHENA_DATABASE, DATA_VERSION_PARAMETER"):
        create_provider(settings)
    assert "ATHENA_DATABASE" in caplog.text


def test_health_answers_while_the_data_loads_and_ready_follows(executor, settings, headers):
    versions = FakeVersions(None)
    provider = AthenaProvider(executor, versions)
    client = TestClient(create_app(settings, data_provider=provider))
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    for path in (f"/api/v1/fields/{field['id']}/profile", "/api/v1/sources"):
        response = client.get(path, headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "data_unavailable"
    versions.version = "2026111500"
    provider.refresh()
    ready = client.get("/ready")
    assert ready.status_code == 200 and ready.json()["data_version"] == "2026111500"
    sources = client.get("/api/v1/sources").json()
    assert {source["id"] for source in sources} >= {"nasa_power", "soilgrids"}
    assert "smap_l4" not in {source["id"] for source in sources}
    assert "synthetic" not in {source["data_class"] for source in sources}


# ---------------------------------------------------------------- protocolo de versión


def with_version(executor, version="2026111500", views=None):
    for view, rows in executor.views.items():
        if views is None or view in views:
            for row in rows:
                row["data_version"] = version
    return executor


def test_rows_of_the_served_version_are_accepted(executor, versions):
    provider = AthenaProvider(with_version(executor), versions)
    assert provider.refresh() is True
    assert len(provider.climatology(SALTILLO)) == 36
    assert provider.daily(SALTILLO)[0].date == "2025-01-01"


def test_snapshot_with_rows_of_another_version_is_rejected(executor, versions, caplog):
    with_version(executor)
    with_version(executor, "2026111612", views={"v_sources"})
    provider = AthenaProvider(executor, versions)
    with caplog.at_level(logging.ERROR):
        assert provider.refresh() is False
    assert not provider.is_ready()
    assert "v_sources" in caplog.text and "2026111612" in caplog.text


def test_cell_read_during_a_publication_is_not_mixed(executor, versions):
    provider = AthenaProvider(with_version(executor), versions)
    provider.refresh()
    # DATA recrea las vistas con la versión nueva antes de actualizar el parámetro.
    with_version(executor, "2026111612", views={"v_cell_profile", "v_cell_daily"})
    with pytest.raises(DataUnavailableError, match="versión nueva"):
        provider.climatology(SALTILLO)
    with pytest.raises(DailyUnavailableError, match="versión nueva"):
        provider.daily(SALTILLO)
    assert provider._wake.is_set()
    # Cuando DATA actualiza el parámetro, la API carga la versión nueva completa.
    with_version(executor, "2026111612")
    versions.version = "2026111612"
    assert provider.refresh() is True
    assert len(provider.climatology(SALTILLO)) == 36


def test_views_without_the_column_are_accepted_with_a_warning(provider, caplog):
    from app.data import athena

    athena._warned_without_version.clear()
    with caplog.at_level(logging.WARNING):
        provider.climatology(LA_LAGUNA)
    assert "no trae data_version" in caplog.text


def test_configured_cells_are_warmed_after_a_load(executor, versions):
    provider = AthenaProvider(executor, versions, warm_cells=[SALTILLO, "E9_r0001_c0001"])
    assert provider.refresh() is True
    deadline = time.monotonic() + 5
    while provider._daily.get("2026111500", SALTILLO) is None and time.monotonic() < deadline:
        time.sleep(0.01)
    executor.queries.clear()
    provider.climatology(SALTILLO)
    provider.daily(SALTILLO)
    assert executor.queries == []
