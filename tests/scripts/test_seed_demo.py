from app.api.schemas.fields import FieldCreate
from app.api.schemas.rotations import RotationRequest
from scripts import seed_demo


def test_demo_fields_are_valid_requests():
    demo = seed_demo.load_demo()
    assert len(demo["fields"]) == 2
    for entry in demo["fields"]:
        FieldCreate.model_validate(entry["field"])
        RotationRequest.model_validate(entry["rotations_request"])
        assert entry["story"] and entry["field"]["current_rotation"]


def test_seeding_twice_does_not_duplicate(client):
    first = seed_demo.seed(client)
    second = seed_demo.seed(client)
    assert [field["id"] for field in first] == [field["id"] for field in second]
    headers = {"X-Client-Id": seed_demo.load_demo()["client_id"]}
    assert len(client.get("/api/v1/fields", headers=headers).json()) == 2


def test_seeding_restores_an_edited_field(client):
    demo = seed_demo.load_demo()
    headers = {"X-Client-Id": demo["client_id"]}
    field = seed_demo.seed(client)[0]
    client.patch(f"/api/v1/fields/{field['id']}", json={"irrigation": None}, headers=headers)
    restored = seed_demo.seed(client)[0]
    assert restored["irrigation"] == demo["fields"][0]["field"]["irrigation"]


def test_each_demo_story_runs_end_to_end(client):
    demo = seed_demo.load_demo()
    headers = {"X-Client-Id": demo["client_id"]}
    for entry, field in zip(demo["fields"], seed_demo.seed(client), strict=True):
        base = f"/api/v1/fields/{field['id']}"
        assert client.get(f"{base}/profile", headers=headers).status_code == 200
        detail = client.get(
            f"{base}/suitability", params=entry["suitability_example"], headers=headers
        )
        assert detail.status_code == 200
        rotations = client.post(
            f"{base}/rotations", json=entry["rotations_request"], headers=headers
        )
        assert rotations.status_code == 200 and len(rotations.json()["strategies"]) >= 3
        scenario = {**entry["rotations_request"], "scenario": {"delta_t_c": 2, "delta_p_pct": -20}}
        assert client.post(f"{base}/rotations", json=scenario, headers=headers).status_code == 200
