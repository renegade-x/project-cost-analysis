from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, Length

from .extensions import db
from .models import Project
from .security import get_owned_project_or_403

bp = Blueprint("projects", __name__)


class ProjectForm(FlaskForm):
    name = StringField("Project name", filters=[lambda s: s.strip() if s else s], validators=[InputRequired(), Length(min=1, max=100)])
    submit = SubmitField("Create project")


@bp.route("/projects", methods=["GET", "POST"])
@login_required
def index():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(name=form.name.data, user_id=current_user.id)
        db.session.add(project)
        db.session.commit()
        flash("Project created. Add your first cost item below.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))
    projects = db.session.scalars(
        db.select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc(), Project.id.desc())
    ).all()
    return render_template("projects/list.html", projects=projects, form=form)


@bp.get("/projects/<int:project_id>")
@login_required
def detail(project_id):
    project = get_owned_project_or_403(project_id)
    return render_template("projects/detail.html", project=project)


@bp.post("/projects/<int:project_id>/delete")
@login_required
def delete(project_id):
    project = get_owned_project_or_403(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("projects.index"))
