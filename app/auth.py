from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .forms import LogInForm, SignUpForm
from .models import User


auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    form = LogInForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(db.select(User).where(func.lower(User.email) == email))
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            flash("Logged in successfully.", "success")
            return redirect(url_for("views.dashboard"))
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
            login_user(user)
            flash("Welcome to RepIT.", "success")
            return redirect(url_for("views.dashboard"))
    return render_template("signup.html", form=form, user=current_user)
