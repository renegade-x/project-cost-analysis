import pytest
from app.extensions import db
from app.models import User


def registration(client, **changes):
    data = dict(username="alice", password="strong-password", confirm_password="strong-password")
    data.update(changes)
    return client.post("/auth/register", data=data, follow_redirects=True)


def test_register_success(client):
    assert b"Account created" in registration(client).data
    assert db.session.scalar(db.select(User)).check_password("strong-password")


def test_duplicate_username_is_generic(client, make_user):
    make_user()
    assert b"Unable to register with those details" in registration(client).data


@pytest.mark.parametrize("changes", [{"password": "short"}, {"username": "bad name"}, {"username": "ab"}, {"confirm_password": "different"}])
def test_registration_validation(client, changes):
    registration(client, **changes)
    assert db.session.scalar(db.select(User)) is None


def test_login_and_logout(client, make_user, login):
    make_user()
    assert login(client).location.endswith("/projects")
    assert client.get("/projects").status_code == 200
    assert client.get("/auth/logout").status_code == 405
    assert client.post("/auth/logout").location.endswith("/auth/login")
    assert client.get("/projects").status_code == 302


def test_login_failure_is_generic(client, make_user):
    make_user()
    for username in ("alice", "unknown"):
        response = client.post("/auth/login", data={"username": username, "password": "wrong"})
        assert b"Invalid username or password" in response.data


@pytest.mark.parametrize("target", ["https://evil.test", "//evil.test", "/\\evil.test", "/%5cevil.test", "///evil.test", "/%0a/evil.test"])
def test_open_redirect_rejected(client, make_user, target):
    make_user()
    response = client.post("/auth/login", query_string={"next": target}, data={"username": "alice", "password": "strong-password"})
    assert response.location == "/projects"


def test_local_redirect_allowed(client, make_user):
    make_user()
    response = client.post("/auth/login?next=/projects?tab=recent", data={"username": "alice", "password": "strong-password"})
    assert response.location == "/projects?tab=recent"


def test_anonymous_and_home_redirect(client):
    assert "/auth/login" in client.get("/projects").location
    assert client.get("/").location.endswith("/auth/login")
