"""Write the API contract to contracts/openapi.json deterministically.

Run it after changing any route or schema. CI regenerates the file and fails when it
differs from the committed one. With --check nothing is written; the exit code is 1 on drift.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

CONTRACT = ROOT / "contracts" / "openapi.json"


def render() -> str:
    # Fixed settings: the document must not depend on the caller's environment variables.
    settings = Settings(environment="local", data_lake_bucket="", app_table="", cors_origins=[])
    document = create_app(settings).openapi()
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail instead of writing on drift")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        current = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
        if current != rendered:
            print("contracts/openapi.json is stale; run scripts/export_openapi.py")
            return 1
        return 0
    CONTRACT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"OpenAPI contract: {CONTRACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
