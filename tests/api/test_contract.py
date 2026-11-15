import pytest
from pydantic import TypeAdapter

from app.api.schemas.common import Source
from app.api.schemas.crops import Crop
from app.api.schemas.fields import Field
from app.api.schemas.profile import FieldProfile
from app.api.schemas.rotations import RotationResponse
from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix
from scripts import export_openapi
from tests.helpers import MAIZE_FALLOW, SNAKE_CASE, field_payload, keys

MOCK = "x-fieldshift-mock"
MVP_OPERATIONS = {
    ("get", "/api/v1/crops"),
    ("get", "/api/v1/sources"),
    ("post", "/api/v1/fields"),
    ("get", "/api/v1/fields"),
    ("get", "/api/v1/fields/{field_id}"),
    ("patch", "/api/v1/fields/{field_id}"),
    ("delete", "/api/v1/fields/{field_id}"),
    ("get", "/api/v1/fields/{field_id}/profile"),
    ("get", "/api/v1/fields/{field_id}/suitability"),
    ("post", "/api/v1/fields/{field_id}/rotations"),
}


def test_old_sources_route_is_gone(client):
    assert client.get("/v1/sources").status_code == 404


def test_crops_come_from_the_catalog(client):
    response = client.get("/api/v1/crops")
    assert response.status_code == 200
    assert MOCK not in response.headers
    crops = TypeAdapter(list[Crop]).validate_python(response.json())
    assert len(crops) >= 5
    for crop in response.json():
        assert crop["name"]["es"] and crop["name"]["en"]
        assert {"id", "family", "roles", "cycle_days", "kc", "source_id", "reviewed"} <= set(crop)
    roles = {role for crop in crops for role in crop.roles}
    assert {"cash", "legume", "cover", "forage", "drought_tolerant"} <= roles


def test_sources_come_from_the_data_provider(client):
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    assert MOCK not in response.headers
    sources = TypeAdapter(list[Source]).validate_python(response.json())
    assert {"nasa_power", "soilgrids"} <= {source.id for source in sources}
    for source in response.json():
        assert all(source.values()), source
        assert source["data_class"] == "synthetic"


def test_field_routes_are_real_and_follow_the_schema(client, headers):
    created = client.post("/api/v1/fields", json=field_payload(), headers=headers)
    assert created.status_code == 201
    field_id = Field.model_validate(created.json()).id
    listed = client.get("/api/v1/fields", headers=headers)
    detail = client.get(f"/api/v1/fields/{field_id}", headers=headers)
    patched = client.patch(f"/api/v1/fields/{field_id}", json={"name": "Otra"}, headers=headers)
    for response in (listed, detail, patched):
        assert response.status_code == 200
    TypeAdapter(list[Field]).validate_python(listed.json())
    Field.model_validate(detail.json())
    Field.model_validate(patched.json())
    deleted = client.delete(f"/api/v1/fields/{field_id}", headers=headers)
    assert deleted.status_code == 204
    # Datos reales: ninguna de estas respuestas es una respuesta fija.
    for response in (created, listed, detail, patched, deleted):
        assert MOCK not in response.headers


def test_profile_reference_response(client, headers, field):
    response = client.get(f"/api/v1/fields/{field['id']}/profile", headers=headers)
    assert response.status_code == 200
    assert MOCK not in response.headers
    profile = FieldProfile.model_validate(response.json())
    assert profile.status == "ready"
    assert profile.field_id == field["id"]
    assert [entry.decade for entry in profile.climate.risk_calendar] == list(range(1, 37))
    assert profile.water.groundwater is None
    assert any(gap.code == "no_groundwater_source" for gap in profile.gaps)
    assert [key for key in keys(response.json()) if not SNAKE_CASE.match(key)] == []


def test_suitability_reference_responses(client, headers, field):
    base = f"/api/v1/fields/{field['id']}/suitability"
    matrix = client.get(base, headers=headers)
    assert matrix.status_code == 200
    assert MOCK not in matrix.headers
    SuitabilityMatrix.model_validate(matrix.json())
    detail = client.get(
        base,
        params={"crop_id": "frijol", "planting_month": 6, "delta_t_c": 2, "delta_p_pct": -20},
        headers=headers,
    )
    assert detail.status_code == 200
    assert MOCK not in detail.headers
    parsed = SuitabilityDetail.model_validate(detail.json())
    assert (parsed.crop_id, parsed.planting_month) == ("frijol", 6)
    assert "from" in detail.json()["harvest_window"]


def test_suitability_needs_crop_and_month_together(client, headers, field):
    response = client.get(
        f"/api/v1/fields/{field['id']}/suitability", params={"crop_id": "maiz"}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]["fields"][0]["field"] == "query.planting_month"


def test_rotations_are_computed(client, headers):
    payload = field_payload(current_rotation=MAIZE_FALLOW)
    field = client.post("/api/v1/fields", json=payload, headers=headers).json()
    response = client.post(
        f"/api/v1/fields/{field['id']}/rotations",
        json={"scenario": {"delta_t_c": 2, "delta_p_pct": -20}},
        headers=headers,
    )
    assert response.status_code == 200
    assert MOCK not in response.headers
    rotations = RotationResponse.model_validate(response.json())
    assert len(rotations.strategies) >= 3
    assert any(strategy.is_current for strategy in rotations.strategies)
    assert rotations.scenario.delta_t_c == 2
    assert "erosion_exposure_index" in response.json()["strategies"][0]["metrics"]
    assert "erosion_t_ha_per_year" not in response.json()["strategies"][0]["metrics"]


@pytest.mark.parametrize("suffix", ["profile", "suitability"])
def test_field_resources_need_an_existing_field(client, headers, suffix):
    response = client.get(
        f"/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/{suffix}", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert MOCK not in response.headers


def test_openapi_describes_every_mvp_endpoint(client):
    document = client.get("/openapi.json").json()
    for method, path in MVP_OPERATIONS:
        operation = document["paths"][path][method]
        success = next(code for code in operation["responses"] if code.startswith("2"))
        if success != "204":
            assert "schema" in operation["responses"][success]["content"]["application/json"]
        if method in {"post", "patch"}:
            assert "schema" in operation["requestBody"]["content"]["application/json"]
    business = {path for path in document["paths"] if path not in {"/health", "/ready"}}
    assert all(path.startswith("/api/v1/") for path in business)
    # Los errores usan el sobre común, no el esquema de validación por defecto de FastAPI.
    assert "HTTPValidationError" not in document["components"]["schemas"]


def test_committed_contract_matches_the_application():
    committed = export_openapi.CONTRACT.read_text(encoding="utf-8")
    assert committed == export_openapi.render(), "ejecuta scripts/export_openapi.py"
    assert export_openapi.render() == export_openapi.render()


def test_contract_property_names_are_snake_case(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    names = {name for schema in schemas.values() for name in schema.get("properties", {})}
    assert len(names) > 100
    assert [name for name in sorted(names) if not SNAKE_CASE.match(name)] == []
