from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, Optional


class SignUpForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=254)])
    first_name = StringField("First name", validators=[InputRequired(), Length(min=1, max=100)])
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo("confirm")])
    confirm = PasswordField("Confirm password", validators=[InputRequired()])
    submit = SubmitField("Create account")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Log in")


class UpdateForm(FlaskForm):
    first_name = StringField("First name", validators=[InputRequired(), Length(max=100)])
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=50)])
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
