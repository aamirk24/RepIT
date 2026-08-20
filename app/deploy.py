from contextlib import contextmanager

import click
from flask import current_app
from flask_migrate import upgrade
from sqlalchemy import text

from . import db
from .seed import seed_exercises


DEPLOY_LOCK_ID = 7_350_421_891


@contextmanager
def deployment_lock():
    """Serialize migration and catalogue preparation across PostgreSQL instances."""
    if db.engine.dialect.name != "postgresql":
        yield
        return
    connection = db.engine.connect()
    try:
        connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": DEPLOY_LOCK_ID})
        yield
    finally:
        connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": DEPLOY_LOCK_ID})
        connection.close()


def register_deployment_commands(app):
    @app.cli.command("prepare-deploy")
    def prepare_deploy():
        """Apply migrations and synchronise the pinned exercise catalogue safely."""
        with deployment_lock():
            current_app.logger.info("deployment_prepare_started", extra={"event": "deployment_prepare_started"})
            upgrade()
            result = seed_exercises()
            current_app.logger.info(
                "deployment_prepare_completed",
                extra={
                    "event": "deployment_prepare_completed",
                    "catalogue_created": result.created,
                    "catalogue_updated": result.updated,
                    "catalogue_retired": result.retired,
                },
            )
        click.echo(
            f"Deployment prepared: {result.created} exercises added, "
            f"{result.updated} updated, {result.retired} retired."
        )
