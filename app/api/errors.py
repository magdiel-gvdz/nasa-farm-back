"""Sobre de error único: `{"error": {"code", "message", "details"}}`."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.data import DataUnavailableError
from app.engines.scenario import DailyUnavailableError as ScenarioDailyUnavailableError
from app.geo.geometry import GeometryError
from app.geo.locate import OutOfRegionError
from app.i18n import resolve_language, translate

logger = logging.getLogger(__name__)

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


class ApiError(Exception):
    """Error de aplicación con código estable; el mensaje sale del catálogo de idiomas."""

    def __init__(
        self,
        code: str,
        status_code: int,
        *,
        details: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.params = params or {}
        self.headers = headers


def error_response(
    request: Request,
    code: str,
    status_code: int,
    *,
    details: dict | None = None,
    message_key: str | None = None,
    params: dict | None = None,
    headers: dict | None = None,
) -> JSONResponse:
    language = resolve_language(request.headers.get("accept-language"))
    message = translate(message_key or f"error.{code}", language, **(params or {}))
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
        headers=headers,
    )


def register_error_handlers(api: FastAPI) -> None:
    @api.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return error_response(
            request,
            exc.code,
            exc.status_code,
            details=exc.details,
            params=exc.params,
            headers=exc.headers,
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Solo campo, tipo y mensaje: `input` y `ctx` pueden no ser serializables.
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "type": error["type"],
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return error_response(request, "validation_error", 422, details={"fields": fields})

    @api.exception_handler(GeometryError)
    async def invalid_geometry(request: Request, exc: GeometryError):
        return error_response(
            request,
            "invalid_geometry",
            422,
            details={"reason": exc.reason, **exc.details},
            message_key=f"geometry.{exc.reason}",
            params=exc.details,
        )

    @api.exception_handler(OutOfRegionError)
    async def out_of_region(request: Request, exc: OutOfRegionError):
        zones = [
            {"zone_id": zone.zone_id, "name": zone.name, "bbox": list(zone.bbox)}
            for zone in exc.zones
        ]
        return error_response(
            request, "out_of_region", 422, details={"cell_id": exc.cell_id, "zones": zones}
        )

    @api.exception_handler(ScenarioDailyUnavailableError)
    async def daily_unavailable(request: Request, _exc: ScenarioDailyUnavailableError):
        return error_response(request, "daily_unavailable", 503)

    @api.exception_handler(DataUnavailableError)
    async def data_unavailable(request: Request, _exc: DataUnavailableError):
        return error_response(request, "data_unavailable", 503)

    @api.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        fallback = "internal_error" if exc.status_code >= 500 else "bad_request"
        code = _HTTP_CODES.get(exc.status_code, fallback)
        return error_response(request, code, exc.status_code, headers=exc.headers)

    @api.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        # La traza queda en los logs; el cuerpo no revela nada interno.
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return error_response(request, "internal_error", 500)
