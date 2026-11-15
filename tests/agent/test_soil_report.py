import uuid

import pytest
from fastapi.testclient import TestClient

from app.agent.client import ScriptedClient
from app.agent.extract import ExtractionError, normalize
from app.api.routes.soil import UploadStore
from app.api.schemas.profile import FieldProfile
from app.config import Settings
from app.main import create_app
from tests.helpers import field_payload

PDF = b"%PDF-1.4\n% analisis\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
JPG = b"\xff\xd8\xff\xe0" + b"0" * 20
GOOD = {
    "is_soil_report": True,
    "lab": "Laboratorio del Norte",
    "sample_date": "2026-10-02",
    "depth_cm": "0-30",
    "texture": "Franco arcilloso",
    "ph": 6.8,
    "om_pct": 1.9,
    "ec_ds_m": 1.2,
    "cec_cmol_kg": 22.5,
    "n_mg_kg": 18,
    "p_mg_kg": 12,
    "k_mg_kg": 410,
}


class FakeExtractor:
    def __init__(self, raw=None, error=False):
        self.raw_result = raw if raw is not None else GOOD
        self.error = error
        self.calls = []

    def raw(self, data, kind):
        self.calls.append(kind)
        if self.error:
            raise ExtractionError("timeout")
        return dict(self.raw_result)


@pytest.fixture
def headers():
    return {"X-Client-Id": str(uuid.uuid4())}


def app_with(extractor, tmp_path, enabled=True):
    settings = Settings(chat_enabled=enabled, bedrock_model_id="m", cors_origins=["*"])
    return TestClient(
        create_app(
            settings,
            model_client=ScriptedClient(),
            soil_extractor=extractor if enabled else None,
            uploads=UploadStore(root=tmp_path),
        )
    )


def upload(client, headers, field_id, data=PDF, name="analisis.pdf"):
    return client.post(
        f"/api/v1/fields/{field_id}/soil-report", files={"file": (name, data)}, headers=headers
    )


def test_ph_81_is_discarded_and_limits_are_inclusive():
    result = normalize({**GOOD, "ph": 81, "om_pct": 20, "ec_ds_m": "x", "k_mg_kg": None})
    assert result.values["ph"] is None and result.values["om_pct"] == 20
    reasons = {item["field"]: item["reason"] for item in result.unreadable}
    assert reasons == {"ph": "out_of_range", "ec_ds_m": "invalid", "k_mg_kg": "missing"}
    assert normalize({**GOOD, "ph": 3.0}).values["ph"] == 3.0


def test_readable_report_updates_the_field_profile_and_suitability(tmp_path, headers):
    extractor = FakeExtractor()
    client = app_with(extractor, tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    base = f"/api/v1/fields/{field['id']}"
    before = client.get(f"{base}/profile", headers=headers).json()
    assert "no_lab_analysis" in {gap["code"] for gap in before["gaps"]}
    suitability_before = client.get(
        f"{base}/suitability", params={"crop_id": "maiz", "planting_month": 4}, headers=headers
    ).json()

    response = upload(client, headers, field["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["extracted"]["ph"] == 6.8 and body["extracted"]["om_pct"] == 1.9
    assert body["unreadable_fields"] == [] and body["applied"] is True
    assert extractor.calls == ["pdf"]

    profile = client.get(f"{base}/profile", headers=headers).json()
    FieldProfile.model_validate(profile)
    assert (
        profile["soil"]["lab"]["ph"] == 6.8
        and profile["soil"]["lab"]["sample_date"] == "2026-10-02"
    )
    assert profile["soil"]["confidence"] == "high"
    assert "no_lab_analysis" not in {gap["code"] for gap in profile["gaps"]}
    assert "lab_report" in {source["id"] for source in profile["sources"]}

    soil = client.get(
        f"{base}/suitability", params={"crop_id": "maiz", "planting_month": 4}, headers=headers
    ).json()["reasons"][3]
    estimated = suitability_before["reasons"][3]
    assert "7.9" in estimated["detail"] and estimated["source_id"] == "soilgrids"
    assert (
        "6.8" in soil["detail"]
        and "laboratorio" in soil["detail"]
        and soil["source_id"] == "lab_report"
    )
    assert soil["status"] == "ok"


def test_file_is_stored_privately_under_the_client(tmp_path, headers):
    client = app_with(FakeExtractor(), tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    upload(client, headers, field["id"])
    stored = client.get(f"/api/v1/fields/{field['id']}", headers=headers).json()["soil_lab"]
    assert stored["file_key"].startswith(f"uploads/{headers['X-Client-Id']}/{field['id']}/")
    assert (tmp_path / stored["file_key"]).read_bytes() == PDF
    other = {"X-Client-Id": str(uuid.uuid4())}
    assert upload(client, other, field["id"]).status_code == 404
    assert client.get(f"/api/v1/fields/{field['id']}/profile", headers=other).status_code == 404


@pytest.mark.parametrize(
    ("data", "name", "kind"), [(PNG, "foto.png", "png"), (JPG, "foto.jpg", "jpeg")]
)
def test_images_are_accepted(tmp_path, headers, data, name, kind):
    extractor = FakeExtractor()
    client = app_with(extractor, tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    assert upload(client, headers, field["id"], data, name).status_code == 200
    assert extractor.calls == [kind]


def test_other_files_are_415_and_large_ones_413(tmp_path, headers):
    client = app_with(FakeExtractor(), tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    docx = upload(client, headers, field["id"], b"PK\x03\x04 word", "informe.docx")
    assert docx.status_code == 415 and docx.json()["error"]["code"] == "unsupported_file_type"
    # Un .pdf de nombre que no es PDF también se rechaza: cuenta el contenido.
    assert upload(client, headers, field["id"], b"hola", "falso.pdf").status_code == 415
    big = upload(client, headers, field["id"], PDF + b"0" * (10 * 1024 * 1024))
    assert big.status_code == 413 and big.json()["error"]["code"] == "file_too_large"


def test_invoice_is_rejected_and_the_field_does_not_change(tmp_path, headers):
    client = app_with(
        FakeExtractor({**{key: None for key in GOOD}, "is_soil_report": False}), tmp_path
    )
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    response = upload(client, headers, field["id"])
    assert response.status_code == 422 and response.json()["error"]["code"] == "not_a_soil_report"
    assert client.get(f"/api/v1/fields/{field['id']}", headers=headers).json()["soil_lab"] is None


def test_unavailable_model_or_disabled_chat_is_503(tmp_path, headers):
    client = app_with(FakeExtractor(error=True), tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    response = upload(client, headers, field["id"])
    assert response.status_code == 503 and response.json()["error"]["code"] == "llm_unavailable"
    assert client.get(f"/api/v1/fields/{field['id']}", headers=headers).json()["soil_lab"] is None
    disabled = app_with(None, tmp_path, enabled=False)
    other = disabled.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    response = upload(disabled, headers, other["id"])
    assert response.status_code == 503 and response.json()["error"]["code"] == "chat_disabled"


def test_report_without_accepted_values_does_not_change_the_profile(tmp_path, headers):
    client = app_with(
        FakeExtractor({**{key: None for key in GOOD}, "is_soil_report": True, "ph": 81}), tmp_path
    )
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    body = upload(client, headers, field["id"]).json()
    assert (
        body["applied"] is False
        and {"field": "ph", "reason": "out_of_range"} in body["unreadable_fields"]
    )
    profile = client.get(f"/api/v1/fields/{field['id']}/profile", headers=headers).json()
    assert profile["soil"]["lab"] is None


def test_editing_the_field_keeps_the_lab_values(tmp_path, headers):
    client = app_with(FakeExtractor(), tmp_path)
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    upload(client, headers, field["id"])
    edited = client.patch(
        f"/api/v1/fields/{field['id']}", json={"name": "Nuevo nombre"}, headers=headers
    ).json()
    assert edited["soil_lab"]["values"]["ph"] == 6.8
