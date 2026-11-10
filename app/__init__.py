"""Flask application factory."""
from flask import Flask, redirect, render_template, url_for
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

    @app.errorhandler(413)
    def too_large(error):
        return render_template("errors/error.html", code=413, message="The upload is too large. Use a file smaller than 2 MB."), 413

    with app.app_context():
        db.create_all()
    return app
