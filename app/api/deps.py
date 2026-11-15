"""Dependencias comunes de las rutas: identidad, idioma y servicios de la aplicación."""

import uuid
from typing import Annotated

from fastapi import Depends, Header, Request

from app.api.errors import ApiError
from app.geo.locate import Locator
from app.i18n import resolve_language
from app.store.base import Repository


def client_id(
    x_client_id: Annotated[
        str | None,
        Header(description="UUID que genera el frontend; separa los datos de cada cliente"),
    ] = None,
) -> str:
    """Identidad sin inicio de sesión. No es autenticación: quien conoce el UUID ve sus datos."""
    if x_client_id is None or not x_client_id.strip():
        raise ApiError("missing_client_id", 400)
    try:
        return str(uuid.UUID(x_client_id.strip()))
    except ValueError:
        raise ApiError("invalid_client_id", 400) from None


def language(
    accept_language: Annotated[str | None, Header(description="`es` (por defecto) o `en`")] = None,
) -> str:
    return resolve_language(accept_language)


def repository(request: Request) -> Repository:
    return request.app.state.repository


def locator(request: Request) -> Locator:
    return request.app.state.locator


ClientId = Annotated[str, Depends(client_id)]
Language = Annotated[str, Depends(language)]
Repo = Annotated[Repository, Depends(repository)]
Locate = Annotated[Locator, Depends(locator)]
