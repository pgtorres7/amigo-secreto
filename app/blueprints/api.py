from __future__ import annotations

import hashlib
import hmac

from flask import Blueprint, current_app, jsonify, request, session
from flask_wtf.csrf import generate_csrf

from ..security import admin_required_api
from ..services import (
    add_participants,
    admin_participant_rows,
    check_participant_password,
    clear_all,
    delete_participant,
    get_participant_by_name,
    list_participants_for_draw,
    perform_draw,
    regenerate_password,
    reset_draws,
    status_summary,
)

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/csrf")
def csrf_token():
    return jsonify({"csrf_token": generate_csrf()})


@bp.get("/status")
def status():
    summary = status_summary()
    return jsonify(
        {
            **summary,
            "participants": list_participants_for_draw(),
            "admin": bool(session.get("admin_authenticated")),
        }
    )


@bp.post("/sortear")
def draw():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    password = str(data.get("password") or "")

    if not name:
        return jsonify({"error": "Selecione o seu nome."}), 400

    participant = get_participant_by_name(name)
    if not participant:
        return jsonify({"error": "Nome não encontrado. Peça ao organizador para te cadastrar."}), 404

    if not check_participant_password(participant, password):
        return jsonify({"error": "Senha de acesso incorreta."}), 401

    try:
        result = perform_draw(participant)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "giver": participant["name"],
            "receiver": result["receiver"],
            "already_drawn": result["already_drawn"],
            "message": (
                "Você já tinha sorteado. Aqui está o seu amigo secreto novamente."
                if result["already_drawn"]
                else "Sorteio realizado com sucesso!"
            ),
        }
    )


@bp.post("/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    provided = str(data.get("password") or "")
    expected = current_app.config["ADMIN_PASSWORD"]
    provided_digest = hashlib.sha256(provided.encode("utf-8")).digest()
    expected_digest = hashlib.sha256(expected.encode("utf-8")).digest()
    if not hmac.compare_digest(provided_digest, expected_digest):
        return jsonify({"error": "Senha inválida."}), 401

    session.clear()
    session["admin_authenticated"] = True
    session.permanent = True
    return jsonify({"ok": True})


@bp.post("/admin/logout")
@admin_required_api
def admin_logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/admin/participants")
@admin_required_api
def admin_participants():
    return jsonify(
        {
            "participants": admin_participant_rows(),
            "stats": status_summary(),
        }
    )


@bp.post("/admin/participants")
@admin_required_api
def admin_add_participants():
    data = request.get_json(silent=True) or {}
    names = data.get("names") or ""
    result = add_participants(str(names))
    return jsonify(
        {
            "ok": True,
            "added": len(result["added"]),
            "skipped": result["skipped"],
            "passwords": result.get("passwords", []),
            "participants": admin_participant_rows(),
            "stats": status_summary(),
        }
    )


@bp.post("/admin/participants/<participant_id>/password")
@admin_required_api
def admin_regenerate_password(participant_id: str):
    password = regenerate_password(participant_id)
    if not password:
        return jsonify({"error": "Participante não encontrado."}), 404
    rows = admin_participant_rows()
    name = next((p["name"] for p in rows if p["id"] == participant_id), "Participante")
    return jsonify(
        {
            "ok": True,
            "password": {"id": participant_id, "name": name, "password": password},
            "participants": rows,
            "stats": status_summary(),
        }
    )


@bp.delete("/admin/participants/<participant_id>")
@admin_required_api
def admin_delete_participant(participant_id: str):
    ok, message = delete_participant(participant_id)
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify(
        {
            "ok": True,
            "message": message,
            "participants": admin_participant_rows(),
            "stats": status_summary(),
        }
    )


@bp.post("/admin/reset-draws")
@admin_required_api
def admin_reset_draws():
    reset_draws()
    return jsonify({"ok": True, "message": "Sorteios reiniciados.", "stats": status_summary(), "participants": admin_participant_rows()})


@bp.post("/admin/clear-all")
@admin_required_api
def admin_clear_all():
    clear_all()
    return jsonify({"ok": True, "message": "Lista e sorteios limpos.", "stats": status_summary(), "participants": []})
