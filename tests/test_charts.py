from app.extensions import db
from app.models import CostItem


def test_chart_data_empty(client, owned_project):
    response = client.get(f"/projects/{owned_project.id}/chart-data")
    assert response.json == dict(labels=[], estimated=[], actual=[], variance=[])


def test_chart_data_aggregates(app, client, owned_project):
    with app.app_context():
        db.session.add_all([CostItem(project_id=owned_project.id, category="A", estimated=100, actual=120), CostItem(project_id=owned_project.id, category="A", estimated=50, actual=40)])
        db.session.commit()
    assert client.get(f"/projects/{owned_project.id}/chart-data").json == dict(labels=["A"], estimated=[150], actual=[160], variance=[10])


def test_vendored_chart_library(client):
    response = client.get("/static/vendor/chart.umd.min.js")
    assert response.status_code == 200
    assert b"Chart.js v4.4.9" in response.data
