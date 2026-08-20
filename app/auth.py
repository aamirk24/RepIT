import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .forms import LogInForm, SignUpForm
from .models import LoginThrottle, User


auth = Blueprint("auth", __name__)


def utcnow():
    return datetime.now(timezone.utc)


def throttle_key(email):
    identity = f"{request.remote_addr or 'unknown'}|{email}".encode()
    return hashlib.sha256(identity).hexdigest()


def throttle_record(email):
    return db.session.get(LoginThrottle, throttle_key(email))


def is_blocked(record):
    if not record or not record.blocked_until:
        return False
    blocked_until = record.blocked_until
    if blocked_until.tzinfo is None:
        blocked_until = blocked_until.replace(tzinfo=timezone.utc)
    return blocked_until > utcnow()


def record_failed_login(email):
    now = utcnow()
    record = throttle_record(email)
    window = current_app.config["LOGIN_WINDOW"]
    if record is None:
        record = LoginThrottle(key_hash=throttle_key(email), failed_attempts=0, window_started_at=now)
        db.session.add(record)
    else:
        window_started = record.window_started_at
        if window_started.tzinfo is None:
            window_started = window_started.replace(tzinfo=timezone.utc)
        if now - window_started >= window:
            record.failed_attempts = 0
            record.window_started_at = now
            record.blocked_until = None
    record.failed_attempts += 1
    if record.failed_attempts >= current_app.config["LOGIN_MAX_ATTEMPTS"]:
        record.blocked_until = now + current_app.config["LOGIN_BLOCK_DURATION"]
    db.session.commit()


def clear_login_throttle(email):
    record = throttle_record(email)
    if record:
        db.session.delete(record)
        db.session.commit()


def prune_login_throttles():
    cutoff = utcnow() - timedelta(days=30)
    db.session.execute(db.delete(LoginThrottle).where(LoginThrottle.window_started_at < cutoff))
    db.session.commit()


def safe_next_url(target):
    if not target:
        return None
    host = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    if candidate.scheme in {"http", "https"} and candidate.netloc == host.netloc:
        return candidate.geturl()
    return None


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    form = LogInForm()
    if form.validate_on_submit():
        prune_login_throttles()
        email = form.email.data.strip().lower()
        if is_blocked(throttle_record(email)):
            flash("Too many login attempts. Please try again in 15 minutes.", "danger")
            return render_template("login.html", form=form, user=current_user), 429
        user = db.session.scalar(db.select(User).where(func.lower(User.email) == email))
        if user and check_password_hash(user.password, form.password.data):
            clear_login_throttle(email)
            session.clear()
            login_user(user, remember=form.remember.data, fresh=True)
            session.permanent = True
            flash("Logged in successfully.", "success")
            return redirect(safe_next_url(request.args.get("next")) or url_for("views.dashboard"))
        record_failed_login(email)
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form, user=current_user)


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("views.landing"))


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    form = SignUpForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        username = form.username.data.strip()
        if db.session.scalar(db.select(User).where(func.lower(User.email) == email)):
            flash("An account already uses that email.", "danger")
        elif db.session.scalar(db.select(User).where(func.lower(User.username) == username.lower())):
            flash("That username is already taken.", "danger")
        else:
            user = User(
                email=email,
                first_name=form.first_name.data.strip(),
                username=username,
                password=generate_password_hash(form.password.data),
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            login_user(user)
            session.permanent = True
            flash("Welcome to RepIT.", "success")
            return redirect(url_for("views.dashboard"))
    return render_template("signup.html", form=form, user=current_user)
