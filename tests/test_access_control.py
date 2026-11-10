import pytest
from app.extensions import db
from app.models import Project

PROJECT_ROUTES = [("get", ""), ("post", "/delete"), ("post", "/items"), ("post", "/items/1/delete"), ("post", "/upload"), ("get", "/chart-data"), ("post", "/analysis"), ("get", "/report.pdf"), ("get", "/export.csv")]


@pytest.mark.parametrize("method,suffix", PROJECT_ROUTES)
def test_other_user_cannot_access_project(app, owned_project, make_user, login, method, suffix):
    other = app.test_client()
    make_user("bob")
    login(other, "bob")
    assert getattr(other, method)(f"/projects/{owned_project.id}{suffix}").status_code == 403
    with app.app_context():
        assert db.session.get(Project, owned_project.id) is not None


@pytest.mark.parametrize("method,suffix", PROJECT_ROUTES)
def test_anonymous_project_access_redirects(app, owned_project, method, suffix):
    response = getattr(app.test_client(), method)(f"/projects/{owned_project.id}{suffix}")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_project_create_list_and_delete(app, client, owned_project, make_user):
    bob = make_user("bob")
    with app.app_context():
        db.session.add(Project(name="Private B project", user_id=bob.id))
        db.session.commit()
    response = client.get("/projects")
    assert b"Campus renovation" in response.data
    assert b"Private B project" not in response.data
    created = client.post("/projects", data={"name": " New project "})
    assert created.status_code == 302
    with app.app_context():
        assert db.session.scalar(db.select(Project).where(Project.name == "New project"))
    assert client.get("/projects/99999").status_code == 404
    assert client.post(f"/projects/{owned_project.id}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Project, owned_project.id) is None


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_project_name_validation(app, client, owned_project, name):
    client.post("/projects", data={"name": name})
    with app.app_context():
        assert len(db.session.scalars(db.select(Project)).all()) == 1
