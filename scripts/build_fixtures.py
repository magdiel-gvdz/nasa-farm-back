"""Regenera los datos sintéticos de `app/data/fixtures/` (semilla fija, resultado idéntico).

Uso: `python scripts/build_fixtures.py` escribe los archivos; con `--check` falla si los
archivos guardados no coinciden con lo que genera el código.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.data import synthetic  # noqa: E402

FIXTURES = ROOT / "app" / "data" / "fixtures"


def _per_cell(build) -> list[dict]:
    return [row for cell_id in synthetic.CELL_SPECS for row in build(cell_id)]


def render() -> dict[str, str]:
    """Contenido de cada archivo, una fila por línea para que los diffs sean legibles."""
    tables = {
        "cells": [synthetic.cell_row(cell_id) for cell_id in synthetic.CELL_SPECS],
        "climatology": _per_cell(synthetic.climatology_rows),
        "indicators": _per_cell(synthetic.indicator_rows),
        "years": _per_cell(synthetic.year_rows),
        "soil": _per_cell(synthetic.soil_rows),
        "sources": synthetic.source_rows(),
    }
    return {
        name: "[\n" + ",\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n]\n"
        for name, rows in tables.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail instead of writing on drift")
    args = parser.parse_args()
    stale = []
    for name, content in render().items():
        path = FIXTURES / f"{name}.json"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.name)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        print(f"Datos sintéticos desactualizados: {', '.join(stale)}")
        print("Ejecutar scripts/build_fixtures.py")
        return 1
    if not args.check:
        print(f"Datos sintéticos: {FIXTURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
