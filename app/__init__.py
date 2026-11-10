"""Flask application factory."""
from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user
from dotenv import load_dotenv

from .config import Config, configure_environment
from .extensions import csrf, db, limiter, login_manager


def create_app(config_object=None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    configure_environment(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"

    from . import models  # Register tables before create_all.
    from .auth import bp as auth_bp
    from .projects import bp as projects_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)

    @app.get("/")
    def index():
        return redirect(url_for("projects.index" if current_user.is_authenticated else "auth.login"))

    @app.get("/healthz")
    @limiter.exempt
    def healthz():
        return {"status": "ok"}

    messages = {
        400: "The request could not be accepted. Refresh the page and try again.",
        403: "You do not have permission to access this project.",
        404: "We could not find that page or project.",
        413: "The upload is too large. Use a file smaller than 2 MB.",
        429: "Too many requests. Please wait a moment before trying again.",
        500: "Something went wrong. Please try again later.",
    }

    def error_page(error):
        code = error.code
        if code == 500:
            db.session.rollback()
        app.logger.warning("Request rejected with status %d", code)
        return render_template("errors/error.html", code=code, message=messages[code]), code

    for code in messages:
        app.register_error_handler(code, error_page)

    @app.after_request
    def security_headers(response):
        response.headers.update({
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        })
        if app.config["PRODUCTION"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if (current_user.is_authenticated or request.path.startswith("/auth/")
                or response.mimetype in {"application/pdf", "text/csv"} or response.status_code >= 400):
            response.headers["Cache-Control"] = "no-store"
        response.headers.pop("Server", None)
        return response

    with app.app_context():
        db.create_all()
    return app
