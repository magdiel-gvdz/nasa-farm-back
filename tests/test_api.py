import io
import json
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from mangum import Mangum

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app(Settings(environment="pr-42", data_lake_bucket="test-data-lake")))


def test_health_does_not_need_aws_credentials(client):
    assert client.get("/health").json() == {
        "status": "ok",
        "environment": "pr-42",
        "version": "0.1.0",
    }


def test_missing_manifest_returns_503(client, monkeypatch):
    storage = Mock()
    storage.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
    )
    monkeypatch.setattr("app.data.s3_client", lambda: storage)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "DATA_UNAVAILABLE"


def test_published_manifest_and_bucket_binding(client, monkeypatch):
    manifest = {
        "version": "test-v1",
        "sources": [
            {
                "id": "test-source",
                "name": "Synthetic test fixture",
                "organization": "Test",
                "url": "https://example.com/source",
                "resolution": "test",
                "period": "test",
                "license": "test",
            }
        ],
    }
    storage = Mock()
    storage.get_object.side_effect = lambda **_: {"Body": io.BytesIO(json.dumps(manifest).encode())}
    monkeypatch.setattr("app.data.s3_client", lambda: storage)
    assert client.get("/ready").json()["data_manifest_version"] == "test-v1"
    assert client.get("/v1/sources").json()[0]["id"] == "test-source"
    storage.get_object.assert_called_with(Bucket="test-data-lake", Key="manifests/manifest.json")


@pytest.mark.parametrize("payload", [b"invalid", b"{}", b'{"version":"v1","sources":[]}'])
def test_invalid_manifest_is_not_reported_as_ready(client, monkeypatch, payload):
    storage = Mock()
    storage.get_object.return_value = {"Body": io.BytesIO(payload)}
    monkeypatch.setattr("app.data.s3_client", lambda: storage)
    assert client.get("/ready").status_code == 503


def test_cors_allows_only_configured_origins(client):
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options(
        "/health",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_api_gateway_v2_event_reaches_fastapi():
    handler = Mangum(create_app(Settings(environment="dev")), lifespan="off")
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "api.example.com"},
        "requestContext": {
            "http": {"method": "GET", "path": "/health", "sourceIp": "127.0.0.1"},
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }
    response = handler(event, {})
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["environment"] == "dev"
