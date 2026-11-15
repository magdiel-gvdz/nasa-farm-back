import copy
import json

import pytest

from app.api.fixtures import load_fixture
from scripts import smoke_e2e
from scripts.smoke_e2e import ContractValidator, Smoke, check_profile, check_rotations
from tests.helpers import reference_profile

API = "/api/v1"


@pytest.fixture(scope="module")
def validator():
    return ContractValidator(json.loads(smoke_e2e.CONTRACT.read_text(encoding="utf-8")))


def schema_of(validator, name):
    return {"$ref": f"#/components/schemas/{name}"}


def test_valid_fixtures_pass_the_contract(validator):
    assert validator.errors(reference_profile(), schema_of(validator, "FieldProfile")) == []
    assert (
        validator.errors(load_fixture("rotations"), schema_of(validator, "RotationResponse")) == []
    )


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda body: body.pop("recommended_id"), "falta 'recommended_id'"),
        (lambda body: body["strategies"][0].update(confidence="total"), "confidence"),
        (lambda body: body["strategies"][0]["scores"].update(overall=140), "overall"),
        (lambda body: body["strategies"][0].update(why="porque sí"), "why"),
        (lambda body: body.update(strategies=body["strategies"][:2]), "mínimo 3"),
        (lambda body: body["scenario"].update(delta_t_c="2"), "delta_t_c"),
    ],
)
def test_invalid_responses_are_reported_with_their_location(validator, mutate, expected):
    body = load_fixture("rotations")
    mutate(body)
    problems = validator.errors(body, schema_of(validator, "RotationResponse"))
    assert problems and any(expected in problem for problem in problems), problems


def test_union_responses_accept_either_shape(validator):
    schema = validator.response_schema("get", f"{API}/fields/{{field_id}}/suitability", 200)
    assert validator.errors(load_fixture("suitability_matrix"), schema) == []
    assert validator.errors(load_fixture("suitability_detail"), schema) == []
    assert validator.errors({"crop_id": "maiz"}, schema)


def test_profile_needs_the_36_decades():
    profile = reference_profile()
    assert check_profile(profile) == []
    profile["climate"]["risk_calendar"].pop()
    assert check_profile(profile)


def test_rotations_need_three_strategies_one_current_and_known_sources():
    rotations = load_fixture("rotations")
    cited = {
        evidence["source_id"]
        for strategy in rotations["strategies"]
        for evidence in strategy["evidence"]
        if evidence["source_id"]
    }
    assert check_rotations(rotations, cited) == []
    assert any("no está en /sources" in problem for problem in check_rotations(rotations, set()))

    without_current = copy.deepcopy(rotations)
    for strategy in without_current["strategies"]:
        strategy["is_current"] = False
    assert any("is_current" in problem for problem in check_rotations(without_current, cited))

    too_few = {**rotations, "strategies": rotations["strategies"][:2]}
    assert any("al menos 3" in problem for problem in check_rotations(too_few, cited))


@pytest.mark.parametrize("zone", sorted(smoke_e2e.ZONES))
def test_full_route_passes_against_the_local_api(client, validator, zone):
    results = Smoke(client, validator, zone).run()
    assert [result.name for result in results if result.status == "fail"] == [], smoke_e2e.report(
        results
    )
    names = [result.name for result in results]
    assert names[-1] == "delete_field"
    assert {"profile", "suitability_matrix", "suitability_detail", "rotations"} <= set(names)
    by_name = {result.name: result for result in results}
    assert not by_name["crops"].mock and not by_name["create_field"].mock


def test_field_is_deleted_even_when_a_step_fails(client, validator, monkeypatch):
    monkeypatch.setattr(smoke_e2e, "check_profile", lambda profile: ["roto a propósito"])
    smoke = Smoke(client, validator)
    results = smoke.run()
    by_name = {result.name: result for result in results}
    assert by_name["profile"].status == "fail"
    assert by_name["delete_field"].status == "ok"
    assert client.get(f"{API}/fields", headers=smoke._headers).json() == []


def test_require_real_names_the_steps_that_are_still_fixed(client, validator):
    results = Smoke(client, validator).run()
    still = smoke_e2e.still_mock(results)
    # Mientras el perfil y los motores sean respuestas fijas, --require-real debe fallar.
    assert set(still) <= {"profile", "suitability_matrix", "suitability_detail", "rotations"}
    assert all(result.status == "skip" for result in results if result.name == "scenario") or (
        "suitability_detail" not in still
    )


def test_help_describes_the_arguments(capsys):
    with pytest.raises(SystemExit) as exit_info:
        smoke_e2e.main(["--help"])
    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    for argument in ("--base-url", "--zone", "--require-real"):
        assert argument in output
