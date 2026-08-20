from pathlib import Path
import re
import secrets
import time
import uuid

from flask import Flask, g, render_template, request
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import CONFIGS
from .observability import configure_logging, configure_sentry, release_version


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
    app.config["APP_VERSION"] = release_version()

    if app.config["PROXY_FIX_HOPS"]:
        hops = app.config["PROXY_FIX_HOPS"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    configure_logging(app)
    configure_sentry(app)

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

    from .deploy import register_deployment_commands

    register_deployment_commands(app)

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
        return {"status": "ok", "version": app.config["APP_VERSION"]}

    @app.get("/health/ready")
    def readiness():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            app.logger.warning("readiness_check_failed", extra={"event": "readiness_check_failed"})
            return {"status": "unavailable"}, 503
        return {"status": "ready", "version": app.config["APP_VERSION"]}

    @app.before_request
    def prepare_request_context():
        g.csp_nonce = secrets.token_urlsafe(18)
        supplied_request_id = request.headers.get("X-Request-ID", "")
        g.request_id = supplied_request_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id) else uuid.uuid4().hex
        g.request_started_at = time.perf_counter()

    @app.after_request
    def add_security_headers(response):
        request_id = getattr(g, "request_id", uuid.uuid4().hex)
        response.headers["X-Request-ID"] = request_id
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
        if request.endpoint == "static":
            response.headers["Cache-Control"] = "public, max-age=3600"
        else:
            response.headers.setdefault("Cache-Control", "no-store")
        if request.endpoint not in {"static", "health", "readiness"}:
            app.logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "route": request.url_rule.rule if request.url_rule else "unmatched",
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000, 2),
                },
            )
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", user=current_user, status_code=404, title="Page not found", message="The page you requested does not exist."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error("unhandled_application_error", exc_info=(type(error), error, error.__traceback__), extra={"event": "unhandled_application_error", "request_id": getattr(g, "request_id", None)})
        return render_template("error.html", user=current_user, status_code=500, title="Something went wrong", message="The request could not be completed. Please try again."), 500

    return app
