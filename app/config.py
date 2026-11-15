import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "local"))
    data_lake_bucket: str = field(default_factory=lambda: os.getenv("DATA_LAKE_BUCKET", ""))
    manifest_key: str = field(
        default_factory=lambda: os.getenv("DATA_MANIFEST_KEY", "manifests/manifest.json")
    )
    # Tabla DynamoDB del entorno; vacía = repositorio en memoria (local y pruebas).
    app_table: str = field(default_factory=lambda: os.getenv("APP_TABLE", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:5173"]'))
    )
