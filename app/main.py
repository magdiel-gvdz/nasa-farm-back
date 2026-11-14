import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.data import DataUnavailableError, EvidenceSource, load_manifest

logging.basicConfig(level=logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    api = FastAPI(title="Field Shift API", version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @api.exception_handler(DataUnavailableError)
    async def unavailable_handler(_request: Request, _exc: DataUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"detail": "DATA_UNAVAILABLE", "environment": config.environment},
        )

    @api.get("/health")
    def health():
        return {"status": "ok", "environment": config.environment, "version": "0.1.0"}

    @api.get("/ready")
    def ready():
        manifest = load_manifest(config)
        return {
            "status": "ready",
            "environment": config.environment,
            "data_manifest_version": manifest.version,
        }

    @api.get("/v1/sources")
    def sources() -> list[EvidenceSource]:
        return load_manifest(config).sources

    return api


app = create_app()
