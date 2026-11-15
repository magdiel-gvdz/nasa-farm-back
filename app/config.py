import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "local"))
    # Origen de los datos agroclimáticos; `fixture` sirve datos sintéticos sin AWS.
    data_provider: str = field(default_factory=lambda: os.getenv("DATA_PROVIDER", "fixture"))
    # Solo con `DATA_PROVIDER=athena`: dónde publica DATA (docs/data_access.md).
    data_region: str = field(default_factory=lambda: os.getenv("DATA_REGION", ""))
    athena_workgroup: str = field(default_factory=lambda: os.getenv("ATHENA_WORKGROUP", ""))
    athena_database: str = field(default_factory=lambda: os.getenv("ATHENA_DATABASE", ""))
    data_version_parameter: str = field(
        default_factory=lambda: os.getenv("DATA_VERSION_PARAMETER", "")
    )
    # Chat agrónomo (Bedrock, API Converse). Apagado salvo que se active explícitamente.
    chat_enabled: bool = field(
        default_factory=lambda: os.getenv("CHAT_ENABLED", "false").lower() == "true"
    )
    bedrock_model_id: str = field(default_factory=lambda: os.getenv("BEDROCK_MODEL_ID", ""))
    bedrock_region: str = field(default_factory=lambda: os.getenv("BEDROCK_REGION", "us-east-1"))
    # Modelo con entrada de documentos e imágenes para leer análisis de suelo.
    bedrock_extract_model_id: str = field(
        default_factory=lambda: os.getenv("BEDROCK_EXTRACT_MODEL_ID", "amazon.nova-pro-v1:0")
    )
    chat_rate_per_minute: int = field(
        default_factory=lambda: int(os.getenv("CHAT_RATE_PER_MINUTE", "6"))
    )
    chat_rate_per_day: int = field(
        default_factory=lambda: int(os.getenv("CHAT_RATE_PER_DAY", "80"))
    )
    chat_daily_budget: int = field(
        default_factory=lambda: int(os.getenv("CHAT_DAILY_BUDGET", "1500"))
    )
    chat_max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("CHAT_MAX_OUTPUT_TOKENS", "2048"))
    )
    chat_heartbeat_seconds: float = field(
        default_factory=lambda: float(os.getenv("CHAT_HEARTBEAT_SECONDS", "15"))
    )
    # Bucket del entorno: guarda las respuestas de NASA POWER en `cache/power/`.
    app_bucket: str = field(default_factory=lambda: os.getenv("APP_BUCKET", ""))
    # Tasa de corrección de temperatura por altura del respaldo NASA POWER (°C/km).
    lapse_rate_c_per_km: float = field(
        default_factory=lambda: float(os.getenv("LAPSE_RATE_C_PER_KM", "6.5"))
    )
    # Celdas que el proveedor Athena precarga al arrancar: las de las geocercas de demostración.
    data_warm_cells: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            cell
            for cell in os.getenv("DATA_WARM_CELLS", "E9_r0463_c0846,E9_r0461_c0822").split(",")
            if cell.strip()
        )
    )
    # Cada cuánto se comprueba si DATA publicó una versión nueva.
    data_poll_seconds: float = field(
        default_factory=lambda: float(os.getenv("DATA_POLL_SECONDS", "300"))
    )
    # Tabla DynamoDB del entorno; vacía = repositorio en memoria (local y pruebas).
    app_table: str = field(default_factory=lambda: os.getenv("APP_TABLE", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:5173"]'))
    )
