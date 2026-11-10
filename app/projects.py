from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("projects", __name__)


@bp.get("/projects")
@login_required
def index():
    return render_template("projects/list.html")
