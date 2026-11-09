from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.get("/")
@bp.get("/admin")
@bp.get("/admin/")
@bp.get("/painel")
@bp.get("/sortear")
def index():
    """Uma única página com todas as telas (sorteio + admin)."""
    return render_template("index.html")
