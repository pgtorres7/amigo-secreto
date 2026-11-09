from __future__ import annotations

import hashlib
import hmac

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)

from ..forms import AddParticipantsForm, AdminLoginForm, ConfirmForm
from ..security import admin_required
from ..services import (
    add_participants,
    admin_participant_rows,
    clear_all,
    delete_participant,
    regenerate_password,
    reset_draws,
    status_summary,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/login")
def login():
    if session.get("admin_authenticated"):
        return redirect(url_for("admin.dashboard"))
    form = AdminLoginForm()
    return render_template("admin_login.html", form=form)


@bp.post("/login")
def login_post():
    form = AdminLoginForm()
    if not form.validate_on_submit():
        return render_template("admin_login.html", form=form, error="Dados inválidos."), 400

    expected = current_app.config["ADMIN_PASSWORD"]
    provided = form.password.data or ""
    provided_digest = hashlib.sha256(provided.encode("utf-8")).digest()
    expected_digest = hashlib.sha256(expected.encode("utf-8")).digest()
    if not hmac.compare_digest(provided_digest, expected_digest):
        return render_template("admin_login.html", form=form, error="Senha inválida."), 401

    session.clear()
    session["admin_authenticated"] = True
    session.permanent = True
    return redirect(url_for("admin.dashboard"))


@bp.post("/logout")
@admin_required
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@bp.get("/")
@admin_required
def dashboard():
    add_form = AddParticipantsForm()
    confirm_form = ConfirmForm()
    issued = session.pop("issued_passwords", None)
    return render_template(
        "admin.html",
        add_form=add_form,
        confirm_form=confirm_form,
        participants=admin_participant_rows(),
        stats=status_summary(),
        issued_passwords=issued or [],
    )


@bp.post("/participantes")
@admin_required
def participants_add():
    form = AddParticipantsForm()
    if not form.validate_on_submit():
        flash("Lista inválida.", "error")
        return redirect(url_for("admin.dashboard"))

    result = add_participants(form.names.data)
    session["issued_passwords"] = result.get("passwords", [])
    flash(
        f"{len(result['added'])} participante(s) adicionado(s)"
        + (f", {result['skipped']} ignorado(s)" if result["skipped"] else "")
        + ". Anote as senhas agora — elas não ficam salvas em texto puro.",
        "ok",
    )
    return redirect(url_for("admin.dashboard"))


@bp.post("/participantes/<participant_id>/senha")
@admin_required
def participants_password(participant_id: str):
    form = ConfirmForm()
    if not form.validate_on_submit():
        flash("Requisição inválida.", "error")
        return redirect(url_for("admin.dashboard"))

    password = regenerate_password(participant_id)
    if not password:
        flash("Participante não encontrado.", "error")
        return redirect(url_for("admin.dashboard"))

    name = next(
        (p["name"] for p in admin_participant_rows() if p["id"] == participant_id),
        "Participante",
    )
    session["issued_passwords"] = [{"id": participant_id, "name": name, "password": password}]
    flash("Nova senha gerada. Copie e envie para a pessoa.", "ok")
    return redirect(url_for("admin.dashboard"))


@bp.post("/participantes/<participant_id>/remover")
@admin_required
def participants_delete(participant_id: str):
    form = ConfirmForm()
    if not form.validate_on_submit():
        flash("Requisição inválida.", "error")
        return redirect(url_for("admin.dashboard"))

    ok, message = delete_participant(participant_id)
    flash(message, "ok" if ok else "error")
    return redirect(url_for("admin.dashboard"))


@bp.post("/reset-sorteios")
@admin_required
def reset():
    form = ConfirmForm()
    if not form.validate_on_submit():
        flash("Requisição inválida.", "error")
        return redirect(url_for("admin.dashboard"))
    reset_draws()
    flash("Sorteios reiniciados.", "ok")
    return redirect(url_for("admin.dashboard"))


@bp.post("/limpar")
@admin_required
def wipe():
    form = ConfirmForm()
    if not form.validate_on_submit():
        flash("Requisição inválida.", "error")
        return redirect(url_for("admin.dashboard"))
    clear_all()
    flash("Lista e sorteios limpos.", "ok")
    return redirect(url_for("admin.dashboard"))
