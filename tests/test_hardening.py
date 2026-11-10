import pytest
from app import create_app
from app.config import ProductionConfig, TestConfig


@pytest.mark.parametrize("path", ["/healthz", "/auth/login", "/not-a-route", "/static/css/style.css"])
def test_headers_on_success_error_and_static(client, path):
    response = client.get(path)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "Strict-Transport-Security" not in response.headers


def test_no_store_and_session_flags(client, owned_project):
    for suffix in ("", "/chart-data", "/report.pdf", "/export.csv"):
        assert client.get(f"/projects/{owned_project.id}{suffix}").headers["Cache-Control"] == "no-store"


def test_production_requires_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(ProductionConfig)


def test_production_headers_and_cookies(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "isolated-production-test")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    application = create_app(ProductionConfig)
    assert application.config["SESSION_COOKIE_SECURE"] is True
    assert application.config["SESSION_COOKIE_HTTPONLY"] is True
    assert application.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert application.config["PERMANENT_SESSION_LIFETIME"].total_seconds() == 7200
    assert application.debug is False
    assert "max-age=31536000" in application.test_client().get("/healthz").headers["Strict-Transport-Security"]
