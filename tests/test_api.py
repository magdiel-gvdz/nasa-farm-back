from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_does_not_need_aws_credentials(client):
    assert client.get("/health").json() == {
        "status": "ok",
        "environment": "pr-42",
        "version": "0.1.0",
    }


def test_cors_accepts_any_origin_when_wildcard_is_configured():
    client = TestClient(create_app(Settings(cors_origins=["*"])))
    response = client.options(
        "/health",
        headers={"Origin": "https://frontend.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
