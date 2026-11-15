import pytest
from pydantic import TypeAdapter

from app.api.fixtures import FIXTURE_NAMES, load_fixture
from app.api.schemas.rotations import RotationResponse
from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix
from tests.helpers import SNAKE_CASE, keys

MODELS = {
    "suitability_detail": SuitabilityDetail,
    "suitability_matrix": SuitabilityMatrix,
    "rotations": RotationResponse,
}


def test_every_fixture_has_a_model():
    assert set(MODELS) == set(FIXTURE_NAMES)


@pytest.mark.parametrize("language", ["es", "en"])
@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_matches_its_model_exactly(name, language):
    data = load_fixture(name, language)
    adapter = TypeAdapter(MODELS[name])
    parsed = adapter.validate_python(data)
    # La ida y vuelta detecta claves sobrantes o mal escritas, que el modelo ignoraría.
    assert adapter.dump_python(parsed, mode="json", by_alias=True) == data


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_keys_are_snake_case(name):
    assert [key for key in keys(load_fixture(name)) if not SNAKE_CASE.match(key)] == []


def test_fixture_texts_follow_the_language():
    spanish = load_fixture("rotations", "es")
    english = load_fixture("rotations", "en")
    assert spanish["disclaimer"].startswith("Herramienta de apoyo")
    assert english["disclaimer"].startswith("Decision-support tool")
    assert load_fixture("rotations", "fr") == spanish


def test_fixture_copies_are_independent():
    load_fixture("suitability_matrix").clear()
    assert len(load_fixture("suitability_matrix")["crops"]) == 5
