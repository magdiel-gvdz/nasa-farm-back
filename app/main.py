import logging
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.errors import register_error_handlers
from app.api.fixtures import MOCK_HEADER
from app.api.routes import router as api_router
from app.api.schemas.common import ErrorResponse
from app.catalog.loader import Catalog, load_catalog
from app.config import Settings
from app.data import DataProvider, DataUnavailableError, create_provider
from app.engines.config import EngineConfig, load_config
from app.engines.scenario import ScenarioService
from app.geo.locate import GridLocator, Locator
from app.geo.zones import BBoxCellCatalog, ProviderCellCatalog
from app.profile.builder import ProfileService
from app.store.base import MemoryRepository, Repository
from app.store.dynamodb import DynamoRepository

logging.basicConfig(level=logging.INFO)

API_VERSION = "0.1.0"


class Health(BaseModel):
    status: Literal["ok"]
    environment: str
    version: str


class Ready(BaseModel):
    status: Literal["ready"]
    environment: str
    data_version: str


def build_chat(config: Settings, repository: Repository, catalog: Catalog, model_client=None):
    """Servicios del chat, o `None` si está apagado. Con el chat activo, falta el modelo = error."""
    if not config.chat_enabled:
        return None
    from app.agent.client import BedrockConverseClient
    from app.agent.context import system_prompt
    from app.agent.limits import ChatLimits, RateLimiter
    from app.agent.tools.definitions import build_registry
    from app.api.routes.chat import ChatServices
    from app.store.conversations import ConversationStore

    if model_client is None:
        if not config.bedrock_model_id:
            raise ValueError("CHAT_ENABLED=true necesita BEDROCK_MODEL_ID")
        model_client = BedrockConverseClient(config.bedrock_model_id, config.bedrock_region)
    system_prompt()  # Las instrucciones deben existir: si no, la aplicación no arranca.
    limits = ChatLimits(
        per_minute=config.chat_rate_per_minute,
        per_day=config.chat_rate_per_day,
        daily_budget=config.chat_daily_budget,
        max_output_tokens=config.chat_max_output_tokens,
    )
    return ChatServices(
        client=model_client,
        store=ConversationStore(repository),
        registry=build_registry([crop.id for crop in catalog]),
        rate_limiter=RateLimiter(repository, limits),
        limits=limits,
        heartbeat_seconds=config.chat_heartbeat_seconds,
    )


def create_app(
    settings: Settings | None = None,
    *,
    repository: Repository | None = None,
    locator: Locator | None = None,
    data_provider: DataProvider | None = None,
    catalog: Catalog | None = None,
    engine_config: EngineConfig | None = None,
    model_client=None,
    soil_extractor=None,
    uploads=None,
) -> FastAPI:
    config = settings or Settings()
    api = FastAPI(title="Field Shift API", version=API_VERSION)
    api.state.repository = repository or (
        DynamoRepository(config.app_table) if config.app_table else MemoryRepository()
    )
    provider = data_provider or create_provider(config)
    if data_provider is None and hasattr(provider, "start"):
        # Carga en segundo plano: `/health` responde ya y `/ready` espera a los datos.
        provider.start()
    api.state.data_provider = provider
    # Con los datos de DATA, las celdas publicadas son las suyas; con datos sintéticos se
    # usan los recuadros de las zonas piloto.
    published = (
        ProviderCellCatalog(provider) if config.data_provider == "athena" else BBoxCellCatalog()
    )
    api.state.locator = locator or GridLocator(published)
    api.state.profiles = ProfileService(provider)
    api.state.scenarios = ScenarioService(provider)
    # Un catálogo inválido impide arrancar: el error nombra el cultivo y el campo.
    api.state.catalog = catalog or load_catalog()
    api.state.engine_config = engine_config or load_config()
    api.state.chat = build_chat(config, api.state.repository, api.state.catalog, model_client)
    api.state.soil_extractor = soil_extractor
    if soil_extractor is None and config.chat_enabled:
        from app.agent.extract import BedrockSoilExtractor

        api.state.soil_extractor = BedrockSoilExtractor(
            config.bedrock_extract_model_id, config.bedrock_region
        )
    from app.api.routes.soil import UploadStore

    api.state.uploads = uploads or UploadStore(config.app_bucket)

    api.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Client-Id", "Accept-Language"],
        expose_headers=[MOCK_HEADER],
    )
    register_error_handlers(api)

    @api.get("/health", response_model=Health, tags=["platform"])
    def health():
        return {"status": "ok", "environment": config.environment, "version": API_VERSION}

    @api.get(
        "/ready", response_model=Ready, tags=["platform"], responses={503: {"model": ErrorResponse}}
    )
    def ready():
        version = provider.data_version() if provider.is_ready() else None
        if version is None:
            raise DataUnavailableError("Data provider is not ready")
        return {"status": "ready", "environment": config.environment, "data_version": version}

    api.include_router(api_router)
    return api


app = create_app()
