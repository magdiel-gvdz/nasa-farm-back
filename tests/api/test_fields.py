import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import locator
from app.api.routes.fields import FIELD_LIMIT
from app.geo.locate import Location, OutOfRegionError
from app.geo.zones import PILOT_ZONES
from app.main import create_app
from tests.helpers import field_payload, square

URL = "/api/v1/fields"
GREENHOUSE = {"structure": "multitunel", "cover": "polietileno", "rated_wind_kmh": 100}
NEVADA = square(lon=-117.02, lat=39.41)
LAGUNA = square(lon=-103.30, lat=25.60)


def other_client() -> dict:
    return {"X-Client-Id": str(uuid.uuid4())}


def error_code(response) -> str:
    return response.json()["error"]["code"]


# ---------------------------------------------------------------- alta


def test_create_returns_location_and_identifier(client, headers):
    response = client.post(URL, json=field_payload(), headers=headers)
    assert response.status_code == 201
    field = response.json()
    assert field["id"].startswith("fld_") and len(field["id"]) == 30
    assert field["cell_id"] == "E9_r0463_c0846"
    assert field["zone_id"] == "coah-sureste"
    assert field["cell_assignment"] == "centroid"
    assert field["area_ha"] > 0
    assert field["centroid"] == [-101.01, 25.42]
    assert field["profile_status"] == "ready"
    assert (field["country"], field["admin"]) == (
        "MX",
        {"state": "Coahuila", "municipality": None},
    )
    assert field["created_at"].endswith("Z")
    assert field["kind"] == "field"


def test_create_keeps_the_declared_details(client, headers):
    payload = field_payload(
        kind="greenhouse",
        greenhouse=GREENHOUSE,
        current_rotation=[{"year": 1, "season": "fall_winter", "crop_id": None}],
        irrigation={"available": True, "source": "well", "max_mm_per_year": 400},
        livestock={"species": "bovino", "head": 40},
    )
    field = client.post(URL, json=payload, headers=headers).json()
    assert field["greenhouse"] == {**GREENHOUSE, "heated": False, "co2_enrichment": False}
    assert field["current_rotation"] == payload["current_rotation"]
    assert field["irrigation"] == payload["irrigation"]
    assert field["livestock"] == payload["livestock"]
    assert client.get(f"{URL}/{field['id']}", headers=headers).json() == field


def test_greenhouse_requires_structure_data(client, headers):
    response = client.post(URL, json=field_payload(kind="greenhouse"), headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "validation_error"
    assert client.get(URL, headers=headers).json() == []


# ---------------------------------------------------------------- aislamiento y listado


def test_list_is_newest_first_and_only_own_fields(client, headers):
    stranger = other_client()
    client.post(URL, json=field_payload(name="Ajena"), headers=stranger)
    names = ["Primera", "Segunda", "Tercera"]
    for name in names:
        assert client.post(URL, json=field_payload(name=name), headers=headers).status_code == 201
    assert [field["name"] for field in client.get(URL, headers=headers).json()] == names[::-1]
    assert [field["name"] for field in client.get(URL, headers=stranger).json()] == ["Ajena"]


def test_other_clients_cannot_read_edit_or_delete(client, headers, field):
    stranger = other_client()
    path = f"{URL}/{field['id']}"
    attempts = [
        client.get(path, headers=stranger),
        client.patch(path, json={"name": "Robada"}, headers=stranger),
        client.delete(path, headers=stranger),
        client.get(f"{path}/profile", headers=stranger),
        client.post(f"{path}/rotations", json={}, headers=stranger),
    ]
    for response in attempts:
        assert response.status_code == 404
        assert error_code(response) == "not_found"
    assert client.get(path, headers=headers).json() == field


@pytest.mark.parametrize(
    "field_id", ["nope", "fld_short", "fld_" + "0" * 400, "fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9I"]
)
def test_malformed_identifiers_are_not_found(client, headers, field_id):
    for method in ("get", "delete"):
        response = client.request(method, f"{URL}/{field_id}", headers=headers)
        assert response.status_code == 404
        assert error_code(response) == "not_found"


# ---------------------------------------------------------------- edición


def test_patch_changes_only_the_sent_fields(client, headers, field):
    rotation = [
        {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
        {"year": 1, "season": "fall_winter", "crop_id": None},
    ]
    response = client.patch(
        f"{URL}/{field['id']}", json={"current_rotation": rotation}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {**field, "current_rotation": rotation}
    assert client.get(f"{URL}/{field['id']}", headers=headers).json() == response.json()


def test_patch_null_clears_optional_fields(client, headers):
    created = client.post(
        URL, json=field_payload(livestock={"species": "bovino", "head": 40}), headers=headers
    ).json()
    patched = client.patch(f"{URL}/{created['id']}", json={"livestock": None}, headers=headers)
    assert patched.json() == {**created, "livestock": None}


def test_patch_geometry_recalculates_the_location(client, headers, field):
    response = client.patch(f"{URL}/{field['id']}", json={"geometry": LAGUNA}, headers=headers)
    assert response.status_code == 200
    moved = response.json()
    assert moved["zone_id"] == "coah-laguna"
    assert moved["cell_id"] != field["cell_id"]
    assert moved["centroid"] == [-103.29, 25.61]
    assert moved["area_ha"] != field["area_ha"]
    assert (moved["id"], moved["name"], moved["created_at"]) == (
        field["id"],
        field["name"],
        field["created_at"],
    )


def test_patch_outside_coverage_leaves_the_field_untouched(client, headers, field):
    response = client.patch(
        f"{URL}/{field['id']}", json={"name": "Movida", "geometry": NEVADA}, headers=headers
    )
    assert response.status_code == 422
    assert error_code(response) == "out_of_region"
    assert client.get(f"{URL}/{field['id']}", headers=headers).json() == field


def test_patch_invalid_geometry_leaves_the_field_untouched(client, headers, field):
    broken = square()
    broken["coordinates"][0].pop()
    response = client.patch(f"{URL}/{field['id']}", json={"geometry": broken}, headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "invalid_geometry"
    assert client.get(f"{URL}/{field['id']}", headers=headers).json() == field


def test_patch_cannot_remove_greenhouse_data_from_a_greenhouse(client, headers):
    created = client.post(
        URL, json=field_payload(kind="greenhouse", greenhouse=GREENHOUSE), headers=headers
    ).json()
    response = client.patch(f"{URL}/{created['id']}", json={"greenhouse": None}, headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "validation_error"
    assert client.get(f"{URL}/{created['id']}", headers=headers).json() == created


@pytest.mark.parametrize(
    "body", [{"kind": "greenhouse"}, {"id": "fld_x"}, {"cell_id": "E9_r0000_c0000"}]
)
def test_patch_rejects_fields_that_cannot_be_edited(client, headers, field, body):
    response = client.patch(f"{URL}/{field['id']}", json=body, headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "validation_error"


# ---------------------------------------------------------------- borrado


def test_delete_then_everything_is_not_found(client, headers, field):
    path = f"{URL}/{field['id']}"
    assert client.delete(path, headers=headers).status_code == 204
    assert client.delete(path, headers=headers).status_code == 404
    for response in (
        client.get(path, headers=headers),
        client.patch(path, json={"name": "Fantasma"}, headers=headers),
    ):
        assert response.status_code == 404
        assert error_code(response) == "not_found"
    assert client.get(URL, headers=headers).json() == []


# ---------------------------------------------------------------- tope


def test_the_51st_field_is_rejected(client, headers):
    for index in range(FIELD_LIMIT):
        assert (
            client.post(URL, json=field_payload(name=f"P{index}"), headers=headers).status_code
            == 201
        )
    response = client.post(URL, json=field_payload(name="De más"), headers=headers)
    assert response.status_code == 409
    assert error_code(response) == "field_limit_reached"
    assert response.json()["error"]["details"] == {"limit": 50}
    assert "50" in response.json()["error"]["message"]
    assert len(client.get(URL, headers=headers).json()) == FIELD_LIMIT
    # El tope es por cliente y se libera al borrar.
    assert client.post(URL, json=field_payload(), headers=other_client()).status_code == 201
    oldest = client.get(URL, headers=headers).json()[-1]
    client.delete(f"{URL}/{oldest['id']}", headers=headers)
    assert client.post(URL, json=field_payload(), headers=headers).status_code == 201


# ---------------------------------------------------------------- localización


def test_out_of_region_lists_the_available_zones(client, headers):
    response = client.post(URL, json=field_payload(geometry=NEVADA), headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "out_of_region"
    details = response.json()["error"]["details"]
    assert [zone["zone_id"] for zone in details["zones"]] == [
        "coah-sureste",
        "coah-laguna",
        "coah-norte",
        "coah-centro",
    ]
    assert details["zones"][0] == {
        "zone_id": "coah-sureste",
        "name": "Sureste",
        "bbox": [-101.6, 25.2, -100.7, 25.6],
    }
    assert details["cell_id"].startswith("E9_r")
    assert client.get(URL, headers=headers).json() == []


def test_swapped_coordinates_hint_the_expected_order(client, headers):
    swapped = square()
    swapped["coordinates"][0] = [[lat, lon] for lon, lat in swapped["coordinates"][0]]
    response = client.post(URL, json=field_payload(geometry=swapped), headers=headers)
    assert response.status_code == 422
    assert error_code(response) == "invalid_geometry"
    assert response.json()["error"]["details"]["expected_order"] == "[lon, lat]"


def test_geometry_messages_follow_the_language(client, headers):
    point = {"type": "Point", "coordinates": [-101.0, 25.4]}
    spanish = client.post(URL, json=field_payload(geometry=point), headers=headers)
    english = client.post(
        URL, json=field_payload(geometry=point), headers={**headers, "Accept-Language": "en"}
    )
    assert error_code(spanish) == error_code(english) == "invalid_geometry"
    assert spanish.json()["error"]["details"]["reason"] == "unsupported_type"
    assert "debe ser" in spanish.json()["error"]["message"]
    assert "must be" in english.json()["error"]["message"]


def test_tests_can_replace_the_locator(app, headers):
    fake = Location(
        area_ha=12.5,
        centroid=(-100.0, 20.0),
        cell_id="E9_r0001_c0002",
        zone_id="zona-de-prueba",
        country="MX",
        state="Prueba",
    )
    app.dependency_overrides[locator] = lambda: lambda _geometry: fake
    field = TestClient(app).post(URL, json=field_payload(geometry=NEVADA), headers=headers).json()
    assert (field["cell_id"], field["zone_id"], field["area_ha"]) == (
        "E9_r0001_c0002",
        "zona-de-prueba",
        12.5,
    )


def test_the_locator_can_be_injected_at_startup(settings, headers):
    def nowhere(_geometry):
        raise OutOfRegionError(None, PILOT_ZONES)

    client = TestClient(create_app(settings, locator=nowhere))
    response = client.post(URL, json=field_payload(), headers=headers)
    assert error_code(response) == "out_of_region"
    assert response.json()["error"]["details"]["cell_id"] is None
