import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.helpers import ORIGIN, field_payload


@pytest.fixture
def settings():
    return Settings(
        environment="pr-42", data_provider="fixture", app_table="", cors_origins=[ORIGIN]
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def headers():
    return {"X-Client-Id": str(uuid.uuid4())}


@pytest.fixture
def field(client, headers):
    response = client.post("/api/v1/fields", json=field_payload(), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
