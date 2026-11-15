"""Prueba de humo del recorrido completo del usuario contra una URL de la API.

Recorre catálogo, fuentes, alta de geocerca, perfil, aptitud, rotaciones, escenario y
borrado; valida cada respuesta contra `contracts/openapi.json` y dice qué pasos siguen
siendo respuestas fijas (`X-Fieldshift-Mock`). Crea y borra una geocerca con un
`X-Client-Id` propio en cada ejecución.

Uso: python scripts/smoke_e2e.py --base-url https://... [--zone laguna] [--require-real]
"""

import argparse
import json
import re
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"
MOCK_HEADER = "x-fieldshift-mock"
API = "/api/v1"

# Cuadrados de ~2 km dentro de cada zona piloto: (lon, lat) de la esquina suroeste.
ZONES = {"sureste": (-101.02, 25.41), "laguna": (-103.22, 25.56)}
# Fuera de las cuatro zonas de Coahuila (Monterrey).
OUT_OF_REGION = (-100.32, 25.67)

_JSON_TYPES: dict[str, Callable[[object], bool]] = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "string": lambda value: isinstance(value, str),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
    "integer": lambda value: (
        isinstance(value, int) and not isinstance(value, bool) or _is_whole_float(value)
    ),
    "number": lambda value: isinstance(value, int | float) and not isinstance(value, bool),
}


def _is_whole_float(value: object) -> bool:
    return isinstance(value, float) and value.is_integer()


class ContractValidator:
    """Validador mínimo de JSON Schema para lo que usa el contrato OpenAPI de la API."""

    def __init__(self, document: dict):
        self._document = document

    def response_schema(self, method: str, path: str, status: int) -> dict | None:
        operation = self._document["paths"][path][method]
        content = operation["responses"][str(status)].get("content", {})
        return content.get("application/json", {}).get("schema")

    def errors(self, value: object, schema: dict, where: str = "$") -> list[str]:
        if "$ref" in schema:
            return self.errors(value, self._resolve(schema["$ref"]), where)
        problems: list[str] = []
        for key in ("anyOf", "oneOf"):
            if key in schema:
                attempts = [self.errors(value, option, where) for option in schema[key]]
                if not any(not attempt for attempt in attempts):
                    closest = min(attempts, key=len)
                    problems.append(f"{where}: no cumple ninguna alternativa ({closest[0]})")
        for option in schema.get("allOf", []):
            problems += self.errors(value, option, where)
        kinds = schema.get("type")
        if kinds is not None:
            kinds = [kinds] if isinstance(kinds, str) else kinds
            if not any(_JSON_TYPES[kind](value) for kind in kinds):
                return [*problems, f"{where}: se esperaba {' o '.join(kinds)}"]
        if "enum" in schema and value not in schema["enum"]:
            problems.append(f"{where}: {value!r} no está entre {schema['enum']}")
        if "const" in schema and value != schema["const"]:
            problems.append(f"{where}: se esperaba {schema['const']!r}")
        if isinstance(value, dict):
            problems += self._object_errors(value, schema, where)
        elif isinstance(value, list):
            problems += self._array_errors(value, schema, where)
        elif isinstance(value, str):
            problems += self._string_errors(value, schema, where)
        elif isinstance(value, int | float) and not isinstance(value, bool):
            problems += self._number_errors(value, schema, where)
        return problems

    def _resolve(self, reference: str) -> dict:
        node = self._document
        for part in reference.removeprefix("#/").split("/"):
            node = node[part]
        return node

    def _object_errors(self, value: dict, schema: dict, where: str) -> list[str]:
        problems = [
            f"{where}: falta {name!r}" for name in schema.get("required", []) if name not in value
        ]
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                problems += self.errors(item, properties[name], f"{where}.{name}")
            elif extra is False:
                problems.append(f"{where}: clave no prevista {name!r}")
            elif isinstance(extra, dict):
                problems += self.errors(item, extra, f"{where}.{name}")
        return problems

    def _array_errors(self, value: list, schema: dict, where: str) -> list[str]:
        problems = []
        if len(value) < schema.get("minItems", 0):
            problems.append(f"{where}: {len(value)} elementos, mínimo {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            problems.append(f"{where}: {len(value)} elementos, máximo {schema['maxItems']}")
        prefix = schema.get("prefixItems", [])
        for index, item in enumerate(value):
            if index < len(prefix):
                problems += self.errors(item, prefix[index], f"{where}[{index}]")
            elif isinstance(schema.get("items"), dict):
                problems += self.errors(item, schema["items"], f"{where}[{index}]")
        return problems

    @staticmethod
    def _string_errors(value: str, schema: dict, where: str) -> list[str]:
        problems = []
        if len(value) < schema.get("minLength", 0):
            problems.append(f"{where}: texto más corto que {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            problems.append(f"{where}: texto más largo que {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            problems.append(f"{where}: {value!r} no cumple {schema['pattern']}")
        return problems

    @staticmethod
    def _number_errors(value: float, schema: dict, where: str) -> list[str]:
        checks = (
            ("minimum", lambda limit: value >= limit),
            ("maximum", lambda limit: value <= limit),
            ("exclusiveMinimum", lambda limit: value > limit),
            ("exclusiveMaximum", lambda limit: value < limit),
        )
        return [
            f"{where}: {value} incumple {name} {schema[name]}"
            for name, holds in checks
            if name in schema and not holds(schema[name])
        ]


def check_profile(profile: dict) -> list[str]:
    decades = [entry.get("decade") for entry in profile["climate"]["risk_calendar"]]
    if decades != list(range(1, 37)):
        return [f"risk_calendar debe traer las decenas 1 a 36 en orden; trae {len(decades)}"]
    return []


def check_rotations(rotations: dict, source_ids: set[str]) -> list[str]:
    strategies = rotations["strategies"]
    problems = []
    if len(strategies) < 3:
        problems.append(f"se esperaban al menos 3 estrategias; hay {len(strategies)}")
    if sum(strategy["is_current"] for strategy in strategies) != 1:
        problems.append("debe haber exactamente una estrategia con is_current")
    for strategy in strategies:
        for evidence in strategy["evidence"]:
            source_id = evidence["source_id"]
            if source_id is not None and source_id not in source_ids:
                problems.append(
                    f"estrategia {strategy['id']!r}: evidence cita {source_id!r}, "
                    "que no está en /sources"
                )
    return problems


def square(corner: tuple[float, float], side_deg: float = 0.02) -> dict:
    lon, lat = corner
    east, north = round(lon + side_deg, 6), round(lat + side_deg, 6)
    ring = [[lon, lat], [east, lat], [east, north], [lon, north], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


def field_payload(zone: str) -> dict:
    return {
        "name": f"smoke-e2e {zone}",
        "kind": "field",
        "geometry": square(ZONES[zone]),
        # Maíz en primavera-verano y barbecho en otoño-invierno.
        "current_rotation": [
            {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
            {"year": 1, "season": "fall_winter", "crop_id": None},
        ],
        "irrigation": {"available": True, "source": "well", "max_mm_per_year": 400},
    }


@dataclass
class StepResult:
    name: str
    status: str  # ok | fail | skip
    duration_ms: int
    mock: bool
    detail: str = ""


class Smoke:
    """Ejecuta el recorrido con un cliente HTTP ya configurado con la URL base."""

    # Pasos del MVP que deben dejar de ser respuesta fija para pasar `--require-real`.
    MVP_STEPS = (
        "crops",
        "sources",
        "create_field",
        "profile",
        "suitability_matrix",
        "suitability_detail",
        "rotations",
    )

    def __init__(self, client: httpx.Client, validator: ContractValidator, zone: str = "sureste"):
        self._client = client
        self._validator = validator
        self._zone = zone
        self._headers = {"X-Client-Id": str(uuid.uuid4())}
        self.results: list[StepResult] = []

    def run(self) -> list[StepResult]:
        self._step("health", "get", "/health", "/health", 200)
        self._step("ready", "get", "/ready", "/ready", 200)
        self._step("crops", "get", f"{API}/crops", f"{API}/crops", 200)
        sources = self._step("sources", "get", f"{API}/sources", f"{API}/sources", 200)
        source_ids = {source["id"] for source in sources or []}
        field = self._step(
            "create_field",
            "post",
            f"{API}/fields",
            f"{API}/fields",
            201,
            json=field_payload(self._zone),
        )
        if field is None:
            return self.results
        try:
            self._field_steps(field["id"], source_ids)
        finally:
            # El borrado se ejecuta siempre para no dejar geocercas de prueba.
            self._step(
                "delete_field",
                "delete",
                f"{API}/fields/{field['id']}",
                f"{API}/fields/{{field_id}}",
                204,
            )
        return self.results

    def _field_steps(self, field_id: str, source_ids: set[str]) -> None:
        base = f"{API}/fields/{field_id}"
        template = f"{API}/fields/{{field_id}}"
        self._step(
            "profile", "get", f"{base}/profile", f"{template}/profile", 200, sense=check_profile
        )
        self._step(
            "suitability_matrix", "get", f"{base}/suitability", f"{template}/suitability", 200
        )
        detail = {"crop_id": "maiz", "planting_month": 4}
        self._step(
            "suitability_detail",
            "get",
            f"{base}/suitability",
            f"{template}/suitability",
            200,
            params=detail,
        )
        self._step(
            "rotations",
            "post",
            f"{base}/rotations",
            f"{template}/rotations",
            200,
            json={},
            sense=lambda body: check_rotations(body, source_ids),
        )
        # Un escenario solo dice algo cuando la aptitud ya se calcula con datos.
        self._step(
            "scenario",
            "get",
            f"{base}/suitability",
            f"{template}/suitability",
            200,
            params={**detail, "delta_t_c": 2},
            skip_if_mock=True,
        )
        self._step(
            "out_of_region",
            "post",
            f"{API}/fields",
            f"{API}/fields",
            422,
            json={**field_payload(self._zone), "geometry": square(OUT_OF_REGION)},
            sense=lambda body: (
                [] if body["error"]["code"] == "out_of_region" else [f"código {body['error']}"]
            ),
        )

    def _step(
        self,
        name: str,
        method: str,
        url: str,
        template: str,
        expected: int,
        *,
        sense: Callable[[dict], list[str]] | None = None,
        skip_if_mock: bool = False,
        **request,
    ):
        started = time.perf_counter()
        body, mock, problems = None, False, []
        try:
            response = self._client.request(method, url, headers=self._headers, **request)
            mock = MOCK_HEADER in response.headers
            if response.status_code != expected:
                problems.append(f"HTTP {response.status_code}, se esperaba {expected}")
            else:
                body = response.json() if response.content else None
                schema = self._validator.response_schema(method, template, expected)
                if schema is not None:
                    problems += self._validator.errors(body, schema)
                if sense is not None and not problems:
                    problems += sense(body)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            problems.append(f"{type(error).__name__}: {error}")
        duration = round((time.perf_counter() - started) * 1000)
        if skip_if_mock and mock:
            result = StepResult(name, "skip", duration, mock, "el endpoint aún es respuesta fija")
        elif problems:
            result = StepResult(name, "fail", duration, mock, "; ".join(problems[:5]))
        else:
            result = StepResult(name, "ok", duration, mock)
        self.results.append(result)
        return body if result.status == "ok" else None


def still_mock(results: list[StepResult]) -> list[str]:
    return [result.name for result in results if result.name in Smoke.MVP_STEPS and result.mock]


def report(results: list[StepResult]) -> str:
    lines = [f"{'paso':<20} {'estado':<6} {'ms':>6}  respuesta"]
    for result in results:
        kind = "fija" if result.mock else "real"
        detail = f"  {result.detail}" if result.detail else ""
        lines.append(
            f"{result.name:<20} {result.status:<6} {result.duration_ms:>6}  {kind}{detail}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", required=True, help="URL de la API, sin /api/v1")
    parser.add_argument("--zone", choices=sorted(ZONES), default="sureste")
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="falla si algún paso del MVP sigue siendo una respuesta fija",
    )
    args = parser.parse_args(argv)
    validator = ContractValidator(json.loads(CONTRACT.read_text(encoding="utf-8")))
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30) as client:
        results = Smoke(client, validator, args.zone).run()
    print(report(results))
    failed = [result.name for result in results if result.status == "fail"]
    skipped = [result.name for result in results if result.status == "skip"]
    if skipped:
        print(f"Aviso: pasos omitidos por ser respuesta fija: {', '.join(skipped)}")
    if failed:
        print(f"FALLO: {', '.join(failed)}")
        return 1
    mock = still_mock(results)
    if args.require_real and mock:
        print(f"FALLO (--require-real): siguen siendo respuesta fija: {', '.join(mock)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
