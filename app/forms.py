from flask_wtf import FlaskForm
import re

from wtforms import BooleanField, DateField, FloatField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, Optional, ValidationError


def valid_username(_form, field):
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9_-]{1,28}[A-Za-z0-9])?", field.data or ""):
        raise ValidationError("Use 3–30 letters, numbers, underscores, or hyphens; start and end with a letter or number.")


def nontrivial_password(_form, field):
    value = field.data or ""
    if value.lower() in {"password1234", "qwerty123456", "letmein123456", "correct-horse"}:
        raise ValidationError("Choose a less predictable password.")


class SignUpForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=254)])
    first_name = StringField("First name", validators=[InputRequired(), Length(min=1, max=100)])
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=30), valid_username])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=12, max=128), nontrivial_password, EqualTo("confirm")])
    confirm = PasswordField("Confirm password", validators=[InputRequired()])
    submit = SubmitField("Create account")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Log in")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[InputRequired()])
    new_password = PasswordField(
        "New password",
        validators=[InputRequired(), Length(min=12, max=128), nontrivial_password, EqualTo("confirm_password")],
    )
    confirm_password = PasswordField("Confirm new password", validators=[InputRequired()])
    submit_password = SubmitField("Change password")


class DeleteAccountForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[InputRequired()])
    confirm_deletion = BooleanField("I understand this permanently deletes my account and fitness data.", validators=[InputRequired()])
    submit_delete = SubmitField("Delete account")


class UpdateForm(FlaskForm):
    first_name = StringField("First name", validators=[InputRequired(), Length(max=100)])
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=30), valid_username])
    birthdate = DateField("Birthdate", validators=[Optional()])
    gender = SelectField("Gender", validators=[Optional()], choices=[("", "Prefer not to say"), ("male", "Male"), ("female", "Female"), ("other", "Other")])
    city = StringField("City", validators=[Optional(), Length(max=150)])
    county = StringField("County", validators=[Optional(), Length(max=150)])
    country = StringField("Country", validators=[Optional(), Length(max=150)])
    submit = SubmitField("Save changes")


class WorkoutForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired(), Length(max=150)])
    description = StringField("Description", validators=[Optional(), Length(max=1000)])
    exercises = SelectMultipleField("Exercises", coerce=int, validators=[InputRequired()])
    submit = SubmitField("Create routine")


class HeightForm(FlaskForm):
    height = IntegerField("Height", validators=[InputRequired(), NumberRange(min=50, max=300)])
    date = DateField("Date", validators=[InputRequired()])
    submit = SubmitField("Log height")


class WeightForm(FlaskForm):
    weight = FloatField("Weight", validators=[InputRequired(), NumberRange(min=20, max=500)])
    date = DateField("Date", validators=[InputRequired()])
    submit = SubmitField("Log weight")
