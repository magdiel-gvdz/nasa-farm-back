"""Instrucciones del asistente y contexto variable de cada mensaje.

Las instrucciones y las herramientas son siempre las mismas, para que el modelo pueda reutilizar
su caché; lo que cambia (geocerca activa, fecha, idioma) va al final, dentro del mensaje del
usuario, como un bloque "Contexto".
"""

from datetime import UTC, datetime
from functools import cache
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system.md"


class PromptError(RuntimeError):
    pass


@cache
def system_prompt(path: Path = PROMPT_PATH) -> str:
    """Instrucciones del asistente. La aplicación no arranca si faltan o están vacías."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise PromptError(f"No se pudo leer {path}: {error}") from error
    if not text:
        raise PromptError(f"{path} está vacío")
    return text


def system_blocks() -> list[dict]:
    return [{"text": system_prompt()}]


def context_block(field: dict | None, language: str, today: str | None = None) -> str:
    """Bloque de contexto que acompaña al mensaje del usuario."""
    today = today or datetime.now(UTC).strftime("%Y-%m-%d")
    lines = ["[Contexto]", f"Fecha: {today}", f"Idioma de la interfaz: {language}"]
    if field is None:
        lines.append("Geocerca activa: ninguna")
    else:
        rotation = ", ".join(
            f"año {slot['year']} {slot['season']}: {slot['crop_id'] or 'barbecho'}"
            for slot in field.get("current_rotation") or []
        )
        lines += [
            f"Geocerca activa: {field['name']} (field_id {field['id']})",
            f"Zona: {field['zone_id']}, celda {field['cell_id']}, {field['area_ha']} ha",
            f"Rotación actual: {rotation or 'no declarada'}",
        ]
        irrigation = field.get("irrigation")
        if irrigation:
            lines.append(
                f"Riego: {'sí' if irrigation['available'] else 'no'}"
                + (
                    f", hasta {irrigation['max_mm_per_year']} mm/año"
                    if irrigation.get("max_mm_per_year")
                    else ""
                )
            )
    return "\n".join(lines)


def user_message(text: str, field: dict | None, language: str) -> dict:
    """Mensaje del usuario en formato Converse: su texto y, después, el contexto."""
    return {"role": "user", "content": [{"text": text}, {"text": context_block(field, language)}]}
