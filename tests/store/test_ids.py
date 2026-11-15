import re

from app.store import ids

FIELD_ID = re.compile(r"^fld_[0-9A-HJKMNP-TV-Z]{26}$")


def test_field_ids_are_prefixed_ulids():
    assert FIELD_ID.match(ids.new_field_id())


def test_consecutive_ids_are_distinct_and_sortable():
    generated = [ids.new_field_id() for _ in range(2000)]
    assert len(set(generated)) == len(generated)
    assert generated == sorted(generated)


def test_ids_sort_by_creation_time(monkeypatch):
    monkeypatch.setattr(ids, "_last_ms", -1)  # Se restaura al terminar la prueba.
    clock = iter([1_700_000_000_000, 1_700_000_000_001, 1_800_000_000_000])
    monkeypatch.setattr(ids.time, "time_ns", lambda: next(clock) * 1_000_000)
    first, second, third = (ids.new_ulid() for _ in range(3))
    assert first < second < third
    assert first[:10] != third[:10]  # Los 10 primeros caracteres codifican el instante.


def test_ids_stay_ordered_when_the_clock_goes_back(monkeypatch):
    monkeypatch.setattr(ids, "_last_ms", -1)
    clock = iter([1_900_000_000_000, 1_899_999_999_000])
    monkeypatch.setattr(ids.time, "time_ns", lambda: next(clock) * 1_000_000)
    assert ids.new_ulid() < ids.new_ulid()
