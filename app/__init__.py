from pathlib import Path
import secrets

from flask import Flask, g
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from .config import CONFIGS


db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()


def create_app(test_config=None, environment=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    import os

    environment = environment or os.environ.get("APP_ENV", "development").lower()
    config_class = CONFIGS.get(environment)
    if config_class is None:
        raise RuntimeError(f"Unknown APP_ENV '{environment}'.")
    app.config.from_object(config_class)
    app.config["APP_ENV"] = environment
    if environment == "development":
        app.config["SQLALCHEMY_DATABASE_URI"] = config_class.database_uri(app.instance_path)
    elif environment == "production":
        app.config.update(config_class.validate(app.instance_path))
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from .auth import auth
    from .views import views

    app.register_blueprint(auth)
    app.register_blueprint(views)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            raw_id, raw_version = user_id.split(":", 1)
            user = db.session.get(User, int(raw_id))
            if user and user.session_version == int(raw_version):
                return user
        except (AttributeError, TypeError, ValueError):
            return None
        return None

    from .seed import seed_exercises

    @app.cli.command("seed-exercises")
    def seed_exercises_command():
        """Synchronise the configured exercise catalogue into RepIT."""
        result = seed_exercises()
        print(
            f"Exercise catalogue synced: {result.created} added, "
            f"{result.updated} updated, {result.retired} retired."
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": app.config["APP_ENV"]}

    @app.before_request
    def create_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(18)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            f"default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://unpkg.com; script-src 'self' 'nonce-{g.csp_nonce}' https://cdn.jsdelivr.net; connect-src 'self'",
        )
        if app.config["APP_ENV"] == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    return app
