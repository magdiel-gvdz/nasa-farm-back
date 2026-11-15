import copy

import pytest
from pydantic import ValidationError

from app.api.fixtures import load_fixture
from app.api.schemas.common import ErrorResponse, Gap, Scenario, Source
from app.api.schemas.crops import Crop
from app.api.schemas.fields import Field, FieldCreate, FieldUpdate
from app.api.schemas.profile import FieldProfile
from app.api.schemas.rotations import RotationRequest, RotationResponse
from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix
from app.catalog.loader import load_catalog
from tests.helpers import field_payload, reference_profile, square

SOURCE = {
    "id": "nasa_power",
    "name": "NASA POWER Daily (comunidad AG)",
    "organization": "NASA LaRC",
    "product": "POWER Daily v2",
    "url": "https://power.larc.nasa.gov/",
    "resolution": "0.5° x 0.625° (~55 km), diaria",
    "period": "2016-2025",
    "license": "Datos abiertos con atribución",
    "data_class": "model",
}
FIELD = {
    "id": "fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A",
    **field_payload(),
    "kind": "field",
    "current_rotation": None,
    "irrigation": None,
    "livestock": None,
    "greenhouse": None,
    "area_ha": 445.8,
    "centroid": [-101.01, 25.42],
    "cell_id": "E9_r0463_c0846",
    "zone_id": "coah-sureste",
    "cell_assignment": "centroid",
    "country": "MX",
    "admin": {"state": "Coahuila", "municipality": None},
    "created_at": "2026-11-14T20:00:00Z",
    "profile_status": "ready",
}


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Source, SOURCE),
        (Gap, {"code": "no_hail_product", "severity": "medium", "message": "Sin dato."}),
        (Scenario, {"delta_t_c": 2.0, "delta_p_pct": -20.0}),
        (
            ErrorResponse,
            {"error": {"code": "not_found", "message": "No existe.", "details": {}}},
        ),
    ],
)
def test_common_models_serialize(model, payload):
    assert model.model_validate(payload).model_dump(mode="json") == payload


def test_source_requires_a_known_data_class():
    with pytest.raises(ValidationError):
        Source.model_validate({**SOURCE, "data_class": "guess"})
    with pytest.raises(ValidationError):
        Source.model_validate({key: value for key, value in SOURCE.items() if key != "data_class"})


def test_scenario_defaults_to_no_change_and_bounds_deltas():
    assert Scenario().model_dump() == {"delta_t_c": 0, "delta_p_pct": 0}
    with pytest.raises(ValidationError):
        Scenario(delta_p_pct=-150)


def test_field_create_accepts_a_full_example():
    body = FieldCreate.model_validate(
        field_payload(
            current_rotation=[
                {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
                {"year": 1, "season": "fall_winter", "crop_id": None},
            ],
            irrigation={"available": True, "source": "well", "max_mm_per_year": 400},
            livestock={"species": "bovino", "head": 40},
        )
    )
    assert body.kind == "field"
    assert body.current_rotation[1].crop_id is None


@pytest.mark.parametrize(
    "payload",
    [
        {"geometry": square()},  # sin nombre
        field_payload(name="   "),
        field_payload(kind="orchard"),
        field_payload(currentRotation=[]),  # camelCase no es parte del contrato
        field_payload(kind="greenhouse"),  # invernadero sin datos de estructura
        field_payload(current_rotation=[{"year": 1, "season": "summer", "crop_id": "maiz"}]),
    ],
)
def test_field_create_rejects_invalid_examples(payload):
    with pytest.raises(ValidationError):
        FieldCreate.model_validate(payload)


def test_field_update_tracks_only_sent_fields_and_keeps_required_ones():
    update = FieldUpdate.model_validate({"irrigation": None})
    assert update.model_dump(exclude_unset=True) == {"irrigation": None}
    with pytest.raises(ValidationError):
        FieldUpdate.model_validate({"name": None})
    with pytest.raises(ValidationError):
        FieldUpdate.model_validate({"kind": "greenhouse"})


def test_field_response_validates():
    assert Field.model_validate(FIELD).cell_id == "E9_r0463_c0846"
    with pytest.raises(ValidationError):
        Field.model_validate({**FIELD, "area_ha": 0})


def test_crop_validates():
    crop = load_catalog().get("maiz").model_dump(mode="json")
    assert Crop.model_validate(crop).heat_critical_c == 35
    with pytest.raises(ValidationError):
        Crop.model_validate({**crop, "roles": ["ornamental"]})
    with pytest.raises(ValidationError):
        Crop.model_validate({key: value for key, value in crop.items() if key != "heat_critical_c"})


def _profile_with_calendar(mutate) -> dict:
    profile = reference_profile()
    mutate(profile["climate"]["risk_calendar"])
    return profile


@pytest.mark.parametrize(
    "mutate",
    [
        lambda calendar: calendar.pop(),  # 35 decenas
        lambda calendar: calendar.append({**calendar[-1], "decade": 37}),
        lambda calendar: calendar.__setitem__(1, {**calendar[1], "decade": 1}),  # repetida
        lambda calendar: calendar.reverse(),
    ],
)
def test_profile_rejects_a_calendar_without_36_unique_decades(mutate):
    with pytest.raises(ValidationError, match="risk_calendar"):
        FieldProfile.model_validate(_profile_with_calendar(mutate))


def test_profile_allows_missing_sections_as_null():
    profile = reference_profile()
    for section in ("soil", "terrain", "vegetation", "land_use"):
        profile[section] = None
    profile["water"]["soil_moisture"] = None
    assert FieldProfile.model_validate(profile).soil is None


def test_profile_rejects_incomplete_monthly_series():
    profile = reference_profile()
    profile["climate"]["rain"]["by_month"].pop()
    with pytest.raises(ValidationError):
        FieldProfile.model_validate(profile)


def test_suitability_models_validate():
    detail = load_fixture("suitability_detail")
    assert SuitabilityDetail.model_validate(detail).harvest_window.from_ == "08-10"
    with pytest.raises(ValidationError):
        SuitabilityDetail.model_validate({**detail, "score": 140})
    matrix = load_fixture("suitability_matrix")
    assert len(SuitabilityMatrix.model_validate(matrix).crops) == 5
    matrix["crops"][0]["scores"] = matrix["crops"][0]["scores"][:11]
    with pytest.raises(ValidationError):
        SuitabilityMatrix.model_validate(matrix)


def test_rotation_request_defaults_and_limits():
    request = RotationRequest.model_validate({})
    assert request.max_strategies == 4
    assert request.priorities.save_water == 3
    with pytest.raises(ValidationError):
        RotationRequest.model_validate({"priorities": {"save_water": 9}})
    with pytest.raises(ValidationError):
        RotationRequest.model_validate({"max_strategies": 2})


def test_rotation_response_needs_three_strategies_including_the_current_one():
    response = load_fixture("rotations")
    assert len(RotationResponse.model_validate(response).strategies) >= 3
    with pytest.raises(ValidationError):
        RotationResponse.model_validate({**response, "strategies": response["strategies"][:2]})
    with pytest.raises(ValidationError):
        RotationResponse.model_validate({**response, "recommended_id": "unknown"})
    without_current = copy.deepcopy(response)
    for strategy in without_current["strategies"]:
        strategy["is_current"] = False
    with pytest.raises(ValidationError):
        RotationResponse.model_validate(without_current)
