from app import create_app
from app.config import TestConfig


def test_healthz():
    app = create_app(TestConfig)
    assert app.test_client().get("/healthz").json == {"status": "ok"}
