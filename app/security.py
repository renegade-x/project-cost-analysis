"""Shared authorization and input boundaries."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import unicodedata
from flask import abort
from flask_login import current_user

from .extensions import db
from .models import Project


def get_owned_project_or_403(project_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if project is None:
        abort(404)
    if project.user_id != current_user.id:
        abort(403)
    return project


def sanitize_cell(value: str) -> str:
    """Neutralize spreadsheet formulas, preserving an existing protective quote."""
    text = str(value)
    dangerous = text.startswith(("=", "+", "-", "@", "\t", "\r"))
    clean = "".join(c for c in text if unicodedata.category(c) not in {"Cc", "Cf", "Cs"}).strip()
    if dangerous or clean.startswith(("=", "+", "-", "@")):
        return "'" + clean
    return clean


def validate_category(value: str) -> str:
    clean = sanitize_cell(value)
    if not clean or not clean.lstrip("'").strip():
        raise ValueError("Category is required.")
    if len(clean) > 100:
        raise ValueError("Category must be at most 100 characters after sanitizing.")
    return clean


def validate_amount(value) -> float:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid number.") from None
    if not amount.is_finite() or amount < 0 or amount > 1_000_000_000:
        raise ValueError("Enter a finite number between 0 and 1,000,000,000.")
    return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
