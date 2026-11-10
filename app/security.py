"""Shared authorization and input boundaries."""
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
