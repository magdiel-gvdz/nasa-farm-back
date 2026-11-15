import re
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.data.fixture import FixtureProvider
from app.i18n import MESSAGES, resolve_language, translate
from app.main import create_app
from tests.helpers import ORIGIN, field_payload

ROOT = Path(__file__).resolve().parents[2]


def assert_envelope(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert isinstance(body["error"]["details"], dict)
    return body["error"]


# ---------------------------------------------------------------- errores


def test_invalid_body_reports_the_fields(client, headers):
    response = client.post("/api/v1/fields", json={"name": "", "kind": "farm"}, headers=headers)
    error = assert_envelope(response, 422, "validation_error")
    assert {"body.name", "body.kind", "body.geometry"} <= {
        entry["field"] for entry in error["details"]["fields"]
    }


def test_malformed_json_uses_the_envelope(client, headers):
    response = client.post(
        "/api/v1/fields",
        content=b"{not json",
        headers={**headers, "Content-Type": "application/json"},
    )
    assert_envelope(response, 422, "validation_error")


def test_unknown_field_and_unknown_route_are_not_found(client, headers):
    missing = client.get("/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A", headers=headers)
    assert_envelope(missing, 404, "not_found")
    assert_envelope(client.get("/api/v1/nothing"), 404, "not_found")


def test_wrong_method_keeps_the_allow_header(client):
    response = client.put("/api/v1/crops")
    assert_envelope(response, 405, "method_not_allowed")
    assert "GET" in response.headers["allow"]


def test_other_http_errors_map_to_generic_codes(app):
    @app.get("/teapot")
    def teapot():
        raise HTTPException(status_code=418, detail="internal detail")

    @app.get("/gateway")
    def gateway():
        raise HTTPException(status_code=502, detail="upstream host name")

    client = TestClient(app)
    assert_envelope(client.get("/teapot"), 418, "bad_request")
    response = client.get("/gateway")
    assert_envelope(response, 502, "internal_error")
    assert "upstream" not in response.text


def test_unexpected_error_hides_internals(app, caplog):
    @app.get("/boom")
    def boom():
        raise RuntimeError("table nasa-farm-dev-app is unreachable")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert_envelope(response, 500, "internal_error")
    assert "nasa-farm" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
    assert "nasa-farm-dev-app" in caplog.text  # La traza queda en los logs.


# ---------------------------------------------------------------- identidad


def test_missing_client_id(client):
    assert_envelope(client.get("/api/v1/fields"), 400, "missing_client_id")
    assert_envelope(
        client.get("/api/v1/fields", headers={"X-Client-Id": " "}), 400, "missing_client_id"
    )


@pytest.mark.parametrize("value", ["abc", "1234", "not-a-uuid-at-all-but-36-characters!"])
def test_invalid_client_id(client, value):
    response = client.get("/api/v1/fields", headers={"X-Client-Id": value})
    assert_envelope(response, 400, "invalid_client_id")


def test_valid_client_id_is_case_insensitive(client):
    identity = str(uuid.uuid4())
    created = client.post(
        "/api/v1/fields", json=field_payload(), headers={"X-Client-Id": identity.upper()}
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/fields", headers={"X-Client-Id": identity})
    assert [field["id"] for field in listed.json()] == [created.json()["id"]]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/fields"),
        ("get", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A"),
        ("patch", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A"),
        ("delete", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A"),
        ("get", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/profile"),
        ("get", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/suitability"),
        ("post", "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/rotations"),
    ],
)
def test_every_field_route_requires_identity(client, method, path):
    body = {} if method in {"post", "patch"} else None
    assert_envelope(client.request(method, path, json=body), 400, "missing_client_id")


@pytest.mark.parametrize("path", ["/api/v1/crops", "/api/v1/sources", "/health", "/ready"])
def test_catalogs_and_probes_do_not_require_identity(client, path):
    assert client.get(path).status_code == 200


# ---------------------------------------------------------------- idioma


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "es"),
        ("", "es"),
        ("es", "es"),
        ("en", "en"),
        ("EN-us", "en"),
        ("fr", "es"),
        ("fr-CA, en;q=0.8, es;q=0.9", "es"),
        ("fr, en;q=0.5", "en"),
        ("en;q=0, es", "es"),
        ("en;q=abc", "es"),
        ("*", "es"),
    ],
)
def test_language_resolution(header, expected):
    assert resolve_language(header) == expected


def test_every_message_has_both_languages():
    for key, texts in MESSAGES.items():
        assert set(texts) == {"es", "en"}, key
    assert translate("error.field_limit_reached", "en", limit=50).startswith("The maximum of 50")
    assert translate("error.not_found", "pt") == MESSAGES["error.not_found"]["es"]


@pytest.mark.parametrize(
    ("language", "message"),
    [
        ("en", "The X-Client-Id header is missing."),
        ("es", "Falta el encabezado X-Client-Id."),
        ("fr", "Falta el encabezado X-Client-Id."),
        (None, "Falta el encabezado X-Client-Id."),
    ],
)
def test_error_messages_follow_accept_language(client, language, message):
    headers = {"Accept-Language": language} if language else {}
    assert client.get("/api/v1/fields", headers=headers).json()["error"]["message"] == message


@pytest.mark.parametrize(("language", "word"), [("en", "zone"), ("fr", "zona"), (None, "zona")])
def test_gap_messages_follow_accept_language(client, headers, field, language, word):
    if language:
        headers = {**headers, "Accept-Language": language}
    profile = client.get(f"/api/v1/fields/{field['id']}/profile", headers=headers).json()
    assert word in profile["gaps"][0]["message"]


# ---------------------------------------------------------------- CORS


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_preflight_allows_edit_methods_and_client_header(client, method):
    response = client.options(
        "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "x-client-id, content-type, accept-language",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert method in response.headers["access-control-allow-methods"]
    allowed = response.headers["access-control-allow-headers"].lower()
    assert all(name in allowed for name in ("x-client-id", "content-type", "accept-language"))


def test_preflight_rejects_headers_outside_the_list(client):
    response = client.options(
        "/api/v1/fields",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 400


def test_mock_header_is_exposed_to_the_browser(client):
    response = client.get("/api/v1/crops", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-fieldshift-mock" in response.headers["access-control-expose-headers"].lower()


def test_unknown_origin_gets_no_permission(client):
    origin = "https://untrusted.example"
    simple = client.get("/api/v1/crops", headers={"Origin": origin})
    assert "access-control-allow-origin" not in simple.headers
    preflight = client.options(
        "/api/v1/fields", headers={"Origin": origin, "Access-Control-Request-Method": "DELETE"}
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_errors_carry_cors_headers_for_known_origins(client):
    response = client.get("/api/v1/fields", headers={"Origin": ORIGIN})
    assert_envelope(response, 400, "missing_client_id")
    assert response.headers["access-control-allow-origin"] == ORIGIN


# ---------------------------------------------------------------- disponibilidad


class StubProvider(FixtureProvider):
    """Proveedor sustituible en pruebas: permite fijar la versión o dejarlo sin datos."""

    def __init__(self, ready: bool = True, version: str = "gold-v0"):
        super().__init__()
        self._ready, self._version = ready, version

    def is_ready(self) -> bool:
        return self._ready

    def data_version(self) -> str | None:
        return self._version if self._ready else None


def test_ready_reports_the_data_version_of_the_fixture_provider(client):
    assert client.get("/ready").json()["data_version"] == "fixture"


def test_ready_reports_the_loaded_data_version(settings):
    client = TestClient(create_app(settings, data_provider=StubProvider()))
    assert client.get("/ready").json() == {
        "status": "ready",
        "environment": "pr-42",
        "data_version": "gold-v0",
    }


def test_not_ready_is_503_while_health_stays_up(settings):
    client = TestClient(create_app(settings, data_provider=StubProvider(ready=False)))
    assert_envelope(client.get("/ready"), 503, "data_unavailable")
    assert client.get("/health").status_code == 200
    english = client.get("/ready", headers={"Accept-Language": "en"})
    assert english.json()["error"]["message"] == "Data is not available yet."


# ---------------------------------------------------------------- documentación


def documented_error_codes() -> set[str]:
    text = (ROOT / "docs" / "api-contract.md").read_text(encoding="utf-8")
    table = text.split("## Códigos de error", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([a-z_]+)` \|", table, flags=re.MULTILINE))


def test_error_table_matches_the_catalog():
    catalog = {key.removeprefix("error.") for key in MESSAGES if key.startswith("error.")}
    assert documented_error_codes() == catalog


def test_every_documented_error_code_is_exercised_by_a_test():
    tests = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "tests").rglob("test_*.py")
    )
    for code in documented_error_codes():
        assert f'"{code}"' in tests, code
