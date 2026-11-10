import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def create(username="alice", password="strong-password"):
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return create


@pytest.fixture
def login(make_user):
    def sign_in(client, username="alice", password="strong-password"):
        return client.post("/auth/login", data={"username": username, "password": password})
    return sign_in


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    """A missing mock must fail immediately, never call Gemini or any other service."""
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not make real network calls")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
