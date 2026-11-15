import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "local"))
    # Origen de los datos agroclimáticos; `fixture` sirve datos sintéticos sin AWS.
    data_provider: str = field(default_factory=lambda: os.getenv("DATA_PROVIDER", "fixture"))
    # Tabla DynamoDB del entorno; vacía = repositorio en memoria (local y pruebas).
    app_table: str = field(default_factory=lambda: os.getenv("APP_TABLE", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:5173"]'))
    )
