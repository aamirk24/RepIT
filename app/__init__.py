from pathlib import Path

from flask import Flask
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
        return db.session.get(User, int(user_id))

    from .seed import seed_exercises

    @app.cli.command("seed-exercises")
    def seed_exercises_command():
        """Synchronise the configured exercise catalogue into RepIT."""
        result = seed_exercises()
        print(f"Exercise catalogue synced: {result.created} added, {result.updated} updated.")

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": app.config["APP_ENV"]}

    return app
