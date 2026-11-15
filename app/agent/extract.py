"""Lectura de un análisis de suelo de laboratorio (PDF o imagen) con un modelo de Bedrock.

Se envía el documento con la API Converse y se fuerza una herramienta cuyo esquema es el de los
valores que interesan, para obtener JSON estructurado. Después se normalizan y se validan por
rangos: un valor imposible se descarta en lugar de llegar al perfil.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

TOOL_NAME = "record_soil_report"
# Campo → (mínimo, máximo) plausibles en la unidad pedida al modelo.
RANGES = {
    "ph": (3.0, 11.0),
    "om_pct": (0.0, 20.0),
    "ec_ds_m": (0.0, 20.0),
    "cec_cmol_kg": (0.0, 100.0),
    "n_mg_kg": (0.0, 10_000.0),
    "p_mg_kg": (0.0, 2_000.0),
    "k_mg_kg": (0.0, 10_000.0),
}
TEXT_FIELDS = ("lab", "sample_date", "depth_cm", "texture")
ALL_FIELDS = (*TEXT_FIELDS, *RANGES)
SCHEMA = {
    "type": "object",
    "properties": {
        "is_soil_report": {
            "type": "boolean",
            "description": "true solo si el documento es un análisis de suelo de laboratorio",
        },
        "lab": {"type": ["string", "null"], "description": "Nombre del laboratorio"},
        "sample_date": {"type": ["string", "null"], "description": "Fecha de muestreo, AAAA-MM-DD"},
        "depth_cm": {
            "type": ["string", "null"],
            "description": "Profundidad de la muestra, p. ej. 0-30",
        },
        "texture": {"type": ["string", "null"], "description": "Clase textural tal como aparece"},
        "ph": {"type": ["number", "null"], "description": "pH en agua"},
        "om_pct": {"type": ["number", "null"], "description": "Materia orgánica en %"},
        "ec_ds_m": {
            "type": ["number", "null"],
            "description": "Conductividad eléctrica en dS/m (= mS/cm)",
        },
        "cec_cmol_kg": {
            "type": ["number", "null"],
            "description": "CIC en cmol(+)/kg (= meq/100 g)",
        },
        "n_mg_kg": {
            "type": ["number", "null"],
            "description": "Nitrógeno (inorgánico o total) en mg/kg (= ppm)",
        },
        "p_mg_kg": {"type": ["number", "null"], "description": "Fósforo en mg/kg (= ppm)"},
        "k_mg_kg": {"type": ["number", "null"], "description": "Potasio en mg/kg (= ppm)"},
    },
    "required": ["is_soil_report", *ALL_FIELDS],
}
INSTRUCTIONS = (
    "Lee el documento adjunto. Si es un análisis de suelo de laboratorio, extrae los valores con "
    f"la herramienta {TOOL_NAME}, convertidos a las unidades que pide su esquema. Usa null para "
    "todo valor que no aparezca o no puedas leer con seguridad; no inventes ni estimes. Si el "
    "documento no es un análisis de suelo, llama a la herramienta con is_soil_report=false."
)
# Factores de conversión a mg/kg desde unidades frecuentes en los informes.
_PERCENT_TO_MG_KG = 10_000


class ExtractionError(Exception):
    """El modelo no pudo leer el documento o no está disponible."""


@dataclass(frozen=True)
class Extraction:
    is_soil_report: bool
    values: dict
    unreadable: list[dict]


class SoilExtractor(Protocol):
    def raw(self, data: bytes, kind: str) -> dict:
        """Argumentos de la herramienta tal como los devuelve el modelo. `kind`: pdf, png, jpeg."""
        ...


class BedrockSoilExtractor:
    def __init__(self, model_id: str, region: str):
        import boto3
        from botocore.config import Config

        self._model_id = model_id
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(read_timeout=120, retries={"max_attempts": 2}),
        )

    def raw(self, data: bytes, kind: str) -> dict:
        from botocore.exceptions import BotoCoreError, ClientError

        if kind == "pdf":
            attachment = {
                "document": {"format": "pdf", "name": "analisis", "source": {"bytes": data}}
            }
        else:
            attachment = {"image": {"format": kind, "source": {"bytes": data}}}
        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=[{"role": "user", "content": [attachment, {"text": INSTRUCTIONS}]}],
                toolConfig={
                    "tools": [
                        {
                            "toolSpec": {
                                "name": TOOL_NAME,
                                "description": "Registra los valores del análisis de suelo",
                                "inputSchema": {"json": SCHEMA},
                            }
                        }
                    ],
                    "toolChoice": {"tool": {"name": TOOL_NAME}},
                },
                inferenceConfig={"maxTokens": 1000, "temperature": 0},
            )
        except (BotoCoreError, ClientError) as error:
            logger.error("Extracción del análisis de suelo fallida: %s", error)
            raise ExtractionError(str(error)) from error
        for block in response["output"]["message"]["content"]:
            if "toolUse" in block:
                return block["toolUse"]["input"]
        raise ExtractionError("el modelo no devolvió los valores")


def normalize(raw: dict) -> Extraction:
    """Valores aceptados y campos no leídos con su motivo: `missing`, `out_of_range` o `invalid`."""
    values, unreadable = {}, []
    for name in TEXT_FIELDS:
        value = raw.get(name)
        if isinstance(value, str) and value.strip():
            values[name] = value.strip()
        else:
            values[name] = None
            unreadable.append({"field": name, "reason": "missing"})
    for name, (low, high) in RANGES.items():
        value = raw.get(name)
        if value is None:
            values[name] = None
            unreadable.append({"field": name, "reason": "missing"})
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            values[name] = None
            unreadable.append({"field": name, "reason": "invalid"})
            continue
        if not low <= number <= high:
            values[name] = None
            unreadable.append({"field": name, "reason": "out_of_range"})
            continue
        values[name] = round(number, 3)
    return Extraction(bool(raw.get("is_soil_report")), values, unreadable)


def accepted(values: dict) -> dict:
    """Solo los valores numéricos aceptados (los que cambian el perfil)."""
    return {name: values[name] for name in RANGES if values.get(name) is not None}
