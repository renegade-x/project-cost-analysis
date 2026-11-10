"""Registration and session authentication."""
import secrets
from urllib.parse import unquote, urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import EqualTo, InputRequired, Length, Regexp

from .extensions import db, limiter
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")
# Unknown usernames still pay the password-check cost.
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        InputRequired(), Length(min=3, max=50),
        Regexp(r"^[A-Za-z0-9_]+$", message="Use letters, numbers, and underscores only."),
    ])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[
        InputRequired(), EqualTo("password", message="Passwords must match."),
    ])
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(max=50)])
    password = PasswordField("Password", validators=[InputRequired(), Length(max=128)])
    submit = SubmitField("Sign in")


def safe_next(value: str | None) -> str | None:
    """Only local absolute paths; browsers normalize backslashes and controls."""
    if not value:
        return None
    decoded = unquote(unquote(value))
    if (not decoded.startswith("/") or decoded.startswith("//")
            or "\\" in decoded or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
        return None
    try:
        parsed = urlsplit(decoded)
    except ValueError:
        return None
    return value if not parsed.scheme and not parsed.netloc else None


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"], override_defaults=False)
def register() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("projects.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Unable to register with those details.", "error")
        else:
            flash("Account created. Sign in to get started.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"], override_defaults=False)
def login() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("projects.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        valid = check_password_hash(
            user.password_hash if user else _DUMMY_HASH, form.password.data
        )
        if user and valid:
            session.clear()
            login_user(user)
            session.permanent = True
            return redirect(safe_next(request.args.get("next")) or url_for("projects.index"))
        flash("Invalid username or password", "error")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout() -> ResponseReturnValue:
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
