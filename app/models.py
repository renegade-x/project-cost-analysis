"""Owned project data; all queries use SQLAlchemy's parameterized ORM."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    projects = db.relationship("Project", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    ai_summary = db.Column(db.Text, nullable=True)
    ai_summary_source = db.Column(db.String(20), nullable=True)
    ai_summary_at = db.Column(db.DateTime(timezone=True), nullable=True)
    user = db.relationship("User", back_populates="projects")
    items = db.relationship(
        "CostItem", back_populates="project", cascade="all, delete-orphan",
        order_by="CostItem.id",
    )

    def clear_summary(self) -> None:
        self.ai_summary = self.ai_summary_source = self.ai_summary_at = None


class CostItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category = db.Column(db.String(100), nullable=False)
    estimated = db.Column(db.Float, nullable=False)
    actual = db.Column(db.Float, nullable=False)
    project = db.relationship("Project", back_populates="items")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None
