import pytest
from app.extensions import db
from app.models import CostItem, Project


def add(client, project, **changes):
    data = dict(category="Materials", estimated="100", actual="120")
    data.update(changes)
    return client.post(f"/projects/{project.id}/items", data=data, follow_redirects=True)


def test_item_add_table_and_delete(app, client, owned_project):
    response = add(client, owned_project)
    assert b"+20.00" in response.data and b"Over budget" in response.data
    with app.app_context():
        item = db.session.scalar(db.select(CostItem))
        item_id = item.id
        assert item.actual == 120
    client.post(f"/projects/{owned_project.id}/items/{item_id}/delete")
    with app.app_context():
        assert db.session.get(CostItem, item_id) is None


@pytest.mark.parametrize("field,value", [(field, value) for field in ("estimated", "actual") for value in ("abc", "NaN", "Infinity", "-1", "1000000001", "")]+[("category", "   "), ("category", "x" * 101)])
def test_invalid_item_rejected(app, client, owned_project, field, value):
    add(client, owned_project, **{field: value})
    with app.app_context():
        assert db.session.scalar(db.select(CostItem)) is None


def test_xss_escaped(client, owned_project):
    response = add(client, owned_project, category="<script>alert(1)</script>")
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
    assert b"<script>alert(1)</script>" not in response.data


def test_item_cannot_be_deleted_through_another_project(app, client, owned_project):
    with app.app_context():
        other = Project(name="Other owned project", user_id=owned_project.user_id)
        other.items.append(CostItem(category="Protected", estimated=1, actual=1))
        db.session.add(other)
        db.session.commit()
        item_id = other.items[0].id
    assert client.post(f"/projects/{owned_project.id}/items/{item_id}/delete").status_code == 404
    with app.app_context():
        assert db.session.get(CostItem, item_id) is not None


def test_item_change_clears_summary(app, client, owned_project):
    with app.app_context():
        project = db.session.get(Project, owned_project.id)
        project.ai_summary = "Stale summary"
        project.ai_summary_source = "template"
        db.session.commit()
    add(client, owned_project)
    with app.app_context():
        assert db.session.get(Project, owned_project.id).ai_summary is None
