"""Da de alta las geocercas de demostración de `demo/fields.json` contra una URL de la API.

Es idempotente: usa siempre el mismo `X-Client-Id` (el de `demo/fields.json`), busca cada
geocerca por nombre y, si ya existe, la deja como dice el archivo en lugar de duplicarla.

Uso: python scripts/seed_demo.py --base-url https://...
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

DEMO = Path(__file__).resolve().parents[1] / "demo" / "fields.json"
API = "/api/v1"
# Campos de la geocerca que se pueden cambiar con PATCH (`kind` no).
_PATCHABLE = ("name", "geometry", "current_rotation", "irrigation", "livestock", "greenhouse")


def load_demo() -> dict:
    return json.loads(DEMO.read_text(encoding="utf-8"))


def seed(client: httpx.Client, demo: dict | None = None) -> list[dict]:
    """Geocercas sembradas, en el orden del archivo. Lanza `RuntimeError` si una cae mal."""
    demo = demo or load_demo()
    headers = {"X-Client-Id": demo["client_id"]}
    response = client.get(f"{API}/fields", headers=headers)
    response.raise_for_status()
    existing = {field["name"]: field for field in response.json()}
    seeded = []
    for entry in demo["fields"]:
        wanted = entry["field"]
        current = existing.get(wanted["name"])
        if current is None:
            response = client.post(f"{API}/fields", json=wanted, headers=headers)
        else:
            changes = {key: wanted.get(key) for key in _PATCHABLE}
            response = client.patch(f"{API}/fields/{current['id']}", json=changes, headers=headers)
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"{wanted['name']}: HTTP {response.status_code} {response.text[:300]}"
            )
        field = response.json()
        if (
            field["cell_id"] != entry["expected_cell_id"]
            or field["zone_id"] != entry["expected_zone_id"]
        ):
            raise RuntimeError(
                f"{wanted['name']}: cayó en {field['cell_id']} ({field['zone_id']}), "
                f"se esperaba {entry['expected_cell_id']} ({entry['expected_zone_id']})"
            )
        seeded.append(field)
    return seeded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", required=True, help="URL de la API, sin /api/v1")
    args = parser.parse_args(argv)
    demo = load_demo()
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30) as client:
        try:
            fields = seed(client, demo)
        except (RuntimeError, httpx.HTTPError) as error:
            print(f"FALLO: {error}")
            return 1
    print(f"X-Client-Id: {demo['client_id']}")
    for field in fields:
        print(f"{field['id']}  {field['cell_id']}  {field['zone_id']}  {field['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
