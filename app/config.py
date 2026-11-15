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
