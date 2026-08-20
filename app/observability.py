import json
import logging
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Emit one machine-readable event per line without request or user secrets."""

    reserved = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
        "name", "pathname", "process", "processName", "relativeCreated", "stack_info",
        "thread", "threadName", "taskName",
    }

    def format(self, record):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.reserved and not key.startswith("_"):
                event[key] = value
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str, separators=(",", ":"))


def configure_logging(app):
    level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if app.config["LOG_FORMAT"] == "json" else logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False


def configure_sentry(app):
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=app.config["APP_ENV"],
        release=app.config["APP_VERSION"],
        send_default_pii=False,
        traces_sample_rate=app.config["SENTRY_TRACES_SAMPLE_RATE"],
    )


def release_version():
    return os.environ.get("RENDER_GIT_COMMIT", os.environ.get("APP_VERSION", "development"))[:40]
