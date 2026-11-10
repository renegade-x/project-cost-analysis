"""Safe, reproducible demonstrations: pytest -v -s tests/test_security.py."""
from io import BytesIO
import re

from markupsafe import escape
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import CostItem, Project, User
from app.report import safe_text


def test_invalid_file_upload_demonstration(app, client, owned_project):
    cases = [(b"\x00\xffjunk", "fake.csv", 200), (b"safe text", "sample.exe", 200),
             (b"not a zip", "fake.xlsx", 200), (b"x" * (2 * 1024 * 1024 + 1), "large.csv", 413)]
    for content, filename, status in cases:
        response = client.post(f"/projects/{owned_project.id}/upload", data={"file": (BytesIO(content), filename)}, follow_redirects=True)
        assert response.status_code == status
        assert b"Imported" not in response.data
    with app.app_context():
        assert db.session.scalar(db.select(CostItem)) is None
    print("PASS: binary CSV, executable extension, fake XLSX, and oversized uploads rejected; no rows saved.")


def test_unauthorized_project_access_idor_demonstration(app, owned_project, make_user, login):
    make_user("bob")
    bob = app.test_client()
    login(bob, "bob")
    for method, suffix in [("get", ""), ("post", "/upload"), ("get", "/report.pdf"), ("post", "/delete")]:
        assert getattr(bob, method)(f"/projects/{owned_project.id}{suffix}").status_code == 403
    with app.app_context():
        assert db.session.get(Project, owned_project.id) is not None
    print("PASS: user B cannot open, upload to, download a report for, or delete user A's project (403).")


def test_excessive_login_requests_demonstration():
    class LimitedConfig(TestConfig):
        RATELIMIT_ENABLED = True

    app = create_app(LimitedConfig)
    client = app.test_client()
    responses = [client.post("/auth/login", data={"username": "unknown", "password": "wrong"}) for _ in range(20)]
    assert [response.status_code for response in responses[:5]] == [200] * 5
    assert all(b"Invalid username or password" in response.data for response in responses[:5])
    assert all(response.status_code == 429 for response in responses[5:])
    assert b"Too many requests" in responses[-1].data
    assert responses[-1].headers["X-Frame-Options"] == "DENY"
    print("PASS: 20 rapid login attempts: first 5 normal failures, remaining 15 blocked with 429.")


def test_csrf_missing_token_rejected_and_valid_token_accepted():
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfConfig)
    client = app.test_client()
    assert client.post("/auth/login", data={"username": "alice", "password": "wrong"}).status_code == 400
    page = client.get("/auth/login").data.decode()
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
    response = client.post("/auth/login", data={"username": "alice", "password": "wrong", "csrf_token": token})
    assert response.status_code == 200 and b"Invalid username or password" in response.data
    print("PASS: missing CSRF token rejected (400); valid token accepted.")


def test_xss_category_is_escaped(client, owned_project):
    payload = "<script>alert(1)</script>"
    response = client.post(f"/projects/{owned_project.id}/items", data=dict(category=payload, estimated=10, actual=12), follow_redirects=True)
    assert payload.encode() not in response.data
    assert str(escape(payload)).encode() in response.data
    print("PASS: script-shaped category rendered as escaped text.")


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_formula_injection_neutralized_in_database_html_csv_and_pdf(app, client, owned_project, monkeypatch, prefix):
    payload = prefix + "1+1"
    response = client.post(f"/projects/{owned_project.id}/items", data=dict(category=payload, estimated=10, actual=12), follow_redirects=True)
    with app.app_context():
        item = db.session.scalar(db.select(CostItem))
        assert item.category.startswith("'")
        stored = item.category
    assert str(escape(stored)).encode() in response.data
    assert stored in client.get(f"/projects/{owned_project.id}/export.csv").data.decode("utf-8-sig")
    assert safe_text(stored).startswith("'")
    import app.report as report_module
    actual_paragraph = report_module.Paragraph
    sources = []

    def record(text, *args, **kwargs):
        sources.append(text)
        return actual_paragraph(text, *args, **kwargs)

    monkeypatch.setattr(report_module, "Paragraph", record)
    assert client.get(f"/projects/{owned_project.id}/report.pdf").status_code == 200
    assert safe_text(stored) in sources
    print(f"PASS: formula prefix {prefix!r} neutralized in storage, HTML, CSV, and PDF source.")


def test_sql_injection_strings_cannot_bypass_login_or_break_entry(client, owned_project):
    attacker = "' OR 1=1 --"
    anonymous = client.application.test_client()
    response = anonymous.post("/auth/login", data=dict(username=attacker, password=attacker))
    assert b"Invalid username or password" in response.data
    assert anonymous.get("/projects").status_code == 302
    response = client.post(f"/projects/{owned_project.id}/items", data=dict(category=attacker, estimated=1, actual=2), follow_redirects=True)
    assert response.status_code == 200
    assert str(escape(attacker)).encode() in response.data
    print("PASS: SQL-shaped input stays data and cannot bypass authentication.")


def test_password_hash_and_generic_login_errors(app, client, make_user):
    user = make_user()
    assert user.password_hash != "strong-password" and user.check_password("strong-password")
    for username in ("alice", "unknown"):
        assert b"Invalid username or password" in client.post("/auth/login", data=dict(username=username, password="wrong")).data
    print("PASS: passwords hashed; unknown-user and wrong-password errors identical.")


def test_security_headers_on_normal_response(client):
    response = client.get("/healthz")
    for name in ("Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy"):
        assert name in response.headers
    print("PASS: CSP, nosniff, frame denial, referrer and permissions policies present.")


def test_internal_error_does_not_leak_stack_trace():
    class ErrorConfig(TestConfig):
        PROPAGATE_EXCEPTIONS = False

    app = create_app(ErrorConfig)

    @app.get("/test-only-error")
    def test_error():
        raise RuntimeError("PRIVATE_INTERNAL_PATH_AND_DETAILS")

    response = app.test_client().get("/test-only-error")
    assert response.status_code == 500
    assert b"PRIVATE_INTERNAL_PATH" not in response.data
    assert b"Traceback" not in response.data
    assert b"Something went wrong" in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert create_app(TestConfig).test_client().get("/test-only-error").status_code == 404
    print("PASS: forced internal error returns a generic 500 without internal paths or stack traces.")


@pytest.mark.parametrize("endpoint,limit", [("/auth/register", 10), ("/projects/1/upload", 10), ("/projects/1/analysis", 5)])
def test_other_sensitive_route_rate_limits(endpoint, limit):
    class LimitedConfig(TestConfig):
        RATELIMIT_ENABLED = True

    app = create_app(LimitedConfig)
    with app.app_context():
        user = User(username="alice")
        user.set_password("strong-password")
        db.session.add(user)
        db.session.flush()
        db.session.add(Project(name="Demo", user_id=user.id))
        db.session.commit()
    client = app.test_client()
    client.post("/auth/login", data=dict(username="alice", password="strong-password"))
    # Register as anonymous, because an authenticated user is redirected before form validation.
    if endpoint == "/auth/register":
        client = app.test_client()
    responses = [client.post(endpoint) for _ in range(limit + 1)]
    assert all(response.status_code != 429 for response in responses[:limit])
    assert responses[-1].status_code == 429
    print(f"PASS: {endpoint} enforced its {limit}-request limit.")


def test_global_limit_and_health_exemption():
    class LimitedConfig(TestConfig):
        RATELIMIT_ENABLED = True

    client = create_app(LimitedConfig).test_client()
    assert all(client.get("/healthz").status_code == 200 for _ in range(205))
    assert all(client.get("/auth/login").status_code == 200 for _ in range(200))
    assert client.get("/auth/login").status_code == 429
    print("PASS: global 200/hour limit enforced; health checks remain exempt.")
