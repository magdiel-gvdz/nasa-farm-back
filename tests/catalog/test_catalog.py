import copy
from pathlib import Path

import pytest
import yaml

from app.catalog.loader import DEFAULT_PATH, Catalog, CatalogError, load_catalog, parse_catalog
from app.catalog.models import REQUIRED_ROLES, Crop
from app.config import Settings
from app.main import create_app

DOCS = Path(__file__).resolve().parents[2] / "docs" / "crop-catalog.md"


@pytest.fixture
def entries():
    return yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))


def changed(entries, crop_id, **values):
    result = copy.deepcopy(entries)
    next(entry for entry in result if entry["id"] == crop_id).update(values)
    return result


def test_shipped_catalog_loads_and_covers_every_required_role():
    catalog = load_catalog()
    assert {"maiz", "frijol", "avena_forrajera", "sorgo", "veza"} <= {crop.id for crop in catalog}
    assert len(catalog) >= 12
    for role in REQUIRED_ROLES:
        assert catalog.with_role(role), role
    assert catalog.get("maiz").name.en == "Maize"
    assert catalog.get("no_existe") is None


def test_legumes_fix_nitrogen_and_leave_a_positive_balance():
    for crop in load_catalog().with_role("legume"):
        assert crop.n_fixing and crop.n_balance_kg_ha > 0


def test_crops_declare_their_source_and_are_reviewed():
    for crop in load_catalog():
        assert crop.source_id
        assert crop.reviewed is True


@pytest.mark.parametrize(
    ("values", "field"),
    [
        ({"ph": [7.5, 5.5]}, "ph"),
        ({"cycle_days": [150, 100]}, "cycle_days"),
        ({"temp_opt_c": [33, 18]}, "temp_opt_c"),
        ({"water_need_mm": [800, 500]}, "water_need_mm"),
        ({"temp_abs_c": [20, 30]}, "temp_abs_c"),
        ({"kc": {"ini": 0.3, "mid": 1.6, "end": 0.6}}, "kc.mid"),
        ({"kc": {"ini": 0, "mid": 1.2, "end": 0.6}}, "kc.ini"),
        ({"roles": ["cash", "ornamental"]}, "roles"),
        ({"roles": []}, "roles"),
        ({"family": "orchidaceae"}, "family"),
        ({"residue": "huge"}, "residue"),
        ({"equipment": ["drone"]}, "equipment"),
        ({"margin_index": -1}, "margin_index"),
        ({"ph": [5.5, 15]}, "ph"),
        ({"roles": ["cash", "legume"]}, "n_fixing"),
        ({"unknown_field": 1}, "unknown_field"),
    ],
)
def test_invalid_crop_is_rejected_naming_crop_and_field(entries, values, field):
    with pytest.raises(CatalogError) as error:
        parse_catalog(changed(entries, "maiz", **values))
    assert "'maiz'" in str(error.value)
    assert field in str(error.value)


@pytest.mark.parametrize("field", sorted(Crop.model_fields))
def test_required_fields_cannot_be_missing(entries, field):
    if not Crop.model_fields[field].is_required():
        pytest.skip("campo opcional")
    broken = copy.deepcopy(entries)
    del broken[1][field]
    with pytest.raises(CatalogError, match=field):
        parse_catalog(broken)


def test_repeated_identifier_is_rejected(entries):
    bean = next(entry for entry in entries if entry["id"] == "frijol")
    with pytest.raises(CatalogError, match="'frijol'"):
        parse_catalog([*entries, copy.deepcopy(bean)])


def test_catalog_without_a_required_role_is_rejected(entries):
    without_drought = [entry for entry in entries if "drought_tolerant" not in entry["roles"]]
    with pytest.raises(CatalogError, match="drought_tolerant"):
        parse_catalog(without_drought)


@pytest.mark.parametrize("content", ["", "maiz: 1", "- [unclosed"])
def test_unreadable_files_are_rejected(tmp_path, content):
    path = tmp_path / "crops.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CatalogError):
        load_catalog(path)
    with pytest.raises(CatalogError):
        load_catalog(tmp_path / "missing.yaml")


def test_app_does_not_start_with_an_invalid_catalog(monkeypatch, tmp_path, entries):
    path = tmp_path / "crops.yaml"
    path.write_text(yaml.safe_dump(changed(entries, "maiz", ph=[7.5, 5.5])), encoding="utf-8")
    monkeypatch.setattr("app.catalog.loader.DEFAULT_PATH", path)
    monkeypatch.setattr("app.main.load_catalog", lambda: load_catalog(path))
    with pytest.raises(CatalogError, match="'maiz'.*ph"):
        create_app(Settings())


def test_app_accepts_an_injected_catalog(entries):
    catalog = Catalog([Crop.model_validate(entry) for entry in entries])
    assert create_app(Settings(), catalog=catalog).state.catalog is catalog


@pytest.mark.parametrize("field", sorted(Crop.model_fields))
def test_every_field_is_documented(field):
    assert f"`{field}`" in DOCS.read_text(encoding="utf-8")
