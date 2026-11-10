import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Project, User


@pytest.fixture
def app():
    application = create_app(TestConfig)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def create(username="alice", password="strong-password"):
        with app.app_context():
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            db.session.expunge(user)
            return user
    return create


@pytest.fixture
def login(make_user):
    def sign_in(client, username="alice", password="strong-password"):
        return client.post("/auth/login", data={"username": username, "password": password})
    return sign_in


@pytest.fixture
def owned_project(app, client, make_user, login):
    user = make_user()
    login(client)
    with app.app_context():
        project = Project(name="Campus renovation", user_id=user.id)
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)
        db.session.expunge(project)
        return project


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """The developer's .env and credentials must never influence isolated tests."""
    monkeypatch.setattr("app.load_dotenv", lambda: None)
    for name in ("SECRET_KEY", "DATABASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL", "APP_ENV"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    """A missing mock must fail immediately, never call Gemini or any other service."""
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not make real network calls")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
