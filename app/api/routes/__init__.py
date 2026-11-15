"""Enrutadores de `/api/v1`, un módulo por recurso."""

from fastapi import APIRouter

from app.api.routes import catalog, fields, profile, rotations, suitability
from app.api.schemas.common import ErrorResponse

API_PREFIX = "/api/v1"

# Todo error usa el sobre común, también el 422 de validación.
router = APIRouter(prefix=API_PREFIX, responses={422: {"model": ErrorResponse}})
for module in (catalog, fields, profile, suitability, rotations):
    router.include_router(module.router)
