from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for

from ..forms import DrawByNameForm
from ..services import (
    check_participant_password,
    get_participant_by_name,
    list_participants_for_draw,
    perform_draw,
    status_summary,
)

bp = Blueprint("main", __name__)


def _build_draw_form(selected: str | None = None) -> DrawByNameForm:
    form = DrawByNameForm()
    people = list_participants_for_draw()
    form.name.choices = [("", "Selecione o seu nome")] + [
        (person["name"], f'{person["name"]}{" (já sorteou)" if person["has_drawn"] else ""}')
        for person in people
    ]
    if selected:
        form.name.data = selected
    return form


@bp.get("/")
def home():
    form = _build_draw_form()
    return render_template("home.html", form=form, stats=status_summary())


@bp.post("/sortear")
def draw():
    form = _build_draw_form()
    if not form.validate_on_submit() or not form.name.data:
        return render_template(
            "home.html",
            form=form,
            stats=status_summary(),
            error="Selecione o seu nome e informe a senha de acesso.",
            show_password=True,
        ), 400

    participant = get_participant_by_name(form.name.data)
    if not participant:
        return render_template(
            "home.html",
            form=_build_draw_form(),
            stats=status_summary(),
            error="Nome não encontrado. Peça ao organizador para te cadastrar.",
        ), 404

    if not check_participant_password(participant, form.access_password.data or ""):
        bad_form = _build_draw_form(participant["name"])
        return render_template(
            "home.html",
            form=bad_form,
            stats=status_summary(),
            error="Senha de acesso incorreta.",
            show_password=True,
        ), 401

    try:
        result = perform_draw(participant)
    except ValueError as exc:
        return render_template(
            "home.html",
            form=_build_draw_form(participant["name"]),
            stats=status_summary(),
            participant_name=participant["name"],
            error=str(exc),
            show_password=True,
        ), 400

    return render_template(
        "home.html",
        form=_build_draw_form(participant["name"]),
        stats=status_summary(),
        participant_name=participant["name"],
        receiver_name=result["receiver"],
        already_drawn=result["already_drawn"],
        show_password=True,
        success=(
            "Você já tinha sorteado. Aqui está o seu amigo secreto novamente."
            if result["already_drawn"]
            else "Sorteio realizado com sucesso!"
        ),
    )


@bp.get("/painel")
def panel_redirect():
    return redirect(url_for("main.home"))
