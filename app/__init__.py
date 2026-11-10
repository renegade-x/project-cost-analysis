"""Flask application factory."""
from flask import Flask
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

    @app.get("/healthz")
    @limiter.exempt
    def healthz():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()
    return app
