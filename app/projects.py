from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

from .analysis import aggregate_by_category, compute_rows, compute_totals, detect_anomalies
from .ai_summary import generate_summary
from .extensions import db, limiter
from .models import CostItem, Project, utcnow
from .security import get_owned_project_or_403, validate_amount, validate_category
from .uploads import UploadError, parse_upload
from .report import build_csv, build_report

bp = Blueprint("projects", __name__)


class ProjectForm(FlaskForm):
    name = StringField("Project name", filters=[lambda s: s.strip() if s else s], validators=[InputRequired(), Length(min=1, max=100)])
    submit = SubmitField("Create project")


def _category(form, field):
    try:
        field.data = validate_category(field.data or "")
    except ValueError as error:
        raise ValidationError(str(error)) from error


def _amount(form, field):
    try:
        validate_amount(field.data)
    except ValueError as error:
        raise ValidationError(str(error)) from error


class ItemForm(FlaskForm):
    category = StringField("Category", validators=[InputRequired(), _category])
    estimated = StringField("Estimated", validators=[InputRequired(), _amount])
    actual = StringField("Actual", validators=[InputRequired(), _amount])
    submit = SubmitField("Add cost item")


class UploadForm(FlaskForm):
    file = FileField("CSV or Excel file")
    submit = SubmitField("Import spreadsheet")


def _dashboard(project, item_form=None):
    rows = compute_rows(project.items)
    return render_template(
        "projects/detail.html", project=project, item_form=item_form or ItemForm(),
        item_rows=list(zip(project.items, rows)), totals=compute_totals(rows), upload_form=UploadForm(),
        anomalies=detect_anomalies(rows),
    )


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
    return _dashboard(project)


@bp.post("/projects/<int:project_id>/delete")
@login_required
def delete(project_id):
    project = get_owned_project_or_403(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("projects.index"))


@bp.post("/projects/<int:project_id>/items")
@login_required
def add_item(project_id):
    project = get_owned_project_or_403(project_id)
    form = ItemForm()
    if not form.validate_on_submit():
        return _dashboard(project, item_form=form)
    project.items.append(CostItem(
        category=form.category.data, estimated=validate_amount(form.estimated.data),
        actual=validate_amount(form.actual.data),
    ))
    project.clear_summary()
    db.session.commit()
    flash("Cost item added.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@bp.post("/projects/<int:project_id>/items/<int:item_id>/delete")
@login_required
def delete_item(project_id, item_id):
    project = get_owned_project_or_403(project_id)
    item = db.session.scalar(db.select(CostItem).where(
        CostItem.project_id == project.id, CostItem.id == item_id,
    ))
    if item is None:
        abort(404)
    db.session.delete(item)
    project.clear_summary()
    db.session.commit()
    flash("Cost item deleted.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@bp.post("/projects/<int:project_id>/upload")
@login_required
@limiter.limit("10 per minute", override_defaults=False)
def upload(project_id):
    project = get_owned_project_or_403(project_id)
    try:
        rows = parse_upload(
            request.files.get("file"), max_rows=current_app.config["MAX_UPLOAD_ROWS"],
            max_bytes=current_app.config["MAX_CONTENT_LENGTH"],
        )
    except UploadError as error:
        flash(str(error), "error")
    else:
        project.items.extend(CostItem(**row) for row in rows)
        project.clear_summary()
        db.session.commit()
        flash(f"Imported {len(rows)} cost rows successfully.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@bp.get("/projects/<int:project_id>/chart-data")
@login_required
def chart_data(project_id):
    project = get_owned_project_or_403(project_id)
    categories = aggregate_by_category(compute_rows(project.items))
    return {
        "labels": [row["category"] for row in categories],
        "estimated": [row["estimated"] for row in categories],
        "actual": [row["actual"] for row in categories],
        "variance": [row["variance"] for row in categories],
    }


@bp.post("/projects/<int:project_id>/analysis")
@login_required
@limiter.limit("5 per minute", override_defaults=False)
def analysis(project_id):
    project = get_owned_project_or_403(project_id)
    if not project.items:
        flash("Add at least one cost item before generating a summary.", "error")
    else:
        project.ai_summary, project.ai_summary_source = generate_summary(project)
        project.ai_summary_at = utcnow()
        db.session.commit()
        flash("Cost analysis summary generated.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@bp.get("/projects/<int:project_id>/report.pdf")
@login_required
def report_pdf(project_id):
    project = get_owned_project_or_403(project_id)
    return send_file(build_report(project), mimetype="application/pdf", as_attachment=True,
                     download_name=f"cost-report-{project.id}.pdf")


@bp.get("/projects/<int:project_id>/export.csv")
@login_required
def export_csv(project_id):
    project = get_owned_project_or_403(project_id)
    return send_file(build_csv(project), mimetype="text/csv", as_attachment=True,
                     download_name=f"cost-report-{project.id}.csv")
