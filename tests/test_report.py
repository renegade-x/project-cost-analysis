from io import BytesIO
from types import SimpleNamespace
import pytest

from app.extensions import db
from app.models import CostItem, Project
from app.report import build_report, safe_text


@pytest.mark.parametrize("category", [None, "Materials", "<b>Special</b> & work", "'=" + "A" * 98])
def test_pdf_response(app, client, owned_project, category):
    if category:
        with app.app_context():
            db.session.add(CostItem(project_id=owned_project.id, category=category, estimated=100, actual=120))
            db.session.commit()
    response = client.get(f"/projects/{owned_project.id}/report.pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert "attachment" in response.headers["Content-Disposition"]
    assert f"cost-report-{owned_project.id}.pdf" in response.headers["Content-Disposition"]


def test_long_report_splits_pages():
    project = SimpleNamespace(name="Long project <>&", items=[dict(category="A long category " * 6, estimated=1e9, actual=1e9)] * 150, ai_summary=None, ai_summary_source=None)
    output = build_report(project).getvalue()
    assert output.startswith(b"%PDF")
    assert output.count(b"/Type /Page\n") >= 4


def test_report_source_escapes_and_neutralizes():
    assert safe_text("<b>A & B</b>") == "&lt;b&gt;A &amp; B&lt;/b&gt;"
    assert safe_text("=1+1") == "'=1+1"


def test_csv_download_and_injection(client, owned_project):
    client.post(f"/projects/{owned_project.id}/items", data=dict(category="=1+1", estimated=100, actual=120))
    response = client.get(f"/projects/{owned_project.id}/export.csv")
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "'=1+1,100.00,120.00,20.00" in response.data.decode("utf-8-sig")
