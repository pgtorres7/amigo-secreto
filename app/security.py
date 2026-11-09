from __future__ import annotations

from functools import wraps

from flask import current_app, g, redirect, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .services import get_participant_by_id


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="amigo-secreto-participant-v1",
    )


def set_participant_cookie(response, participant_id: str):
    token = _serializer().dumps({"pid": str(participant_id)})
    response.set_cookie(
        current_app.config["PARTICIPANT_COOKIE_NAME"],
        token,
        max_age=current_app.config["PARTICIPANT_COOKIE_MAX_AGE"],
        httponly=True,
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        samesite="Lax",
        path="/",
    )
    return response


def clear_participant_cookie(response):
    response.delete_cookie(
        current_app.config["PARTICIPANT_COOKIE_NAME"],
        path="/",
    )
    return response


def load_participant_from_cookie():
    raw = request.cookies.get(current_app.config["PARTICIPANT_COOKIE_NAME"])
    if not raw:
        g.participant = None
        return None
    try:
        data = _serializer().loads(raw, max_age=current_app.config["PARTICIPANT_COOKIE_MAX_AGE"])
        participant = get_participant_by_id(data.get("pid"))
        g.participant = participant
        return participant
    except (BadSignature, SignatureExpired, TypeError, KeyError):
        g.participant = None
        return None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def participant_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        participant = getattr(g, "participant", None) or load_participant_from_cookie()
        if not participant:
            return redirect(url_for("main.home"))
        return view(*args, **kwargs)

    return wrapped


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # CSP sem 'unsafe-eval'. Scripts só do próprio domínio.
    "Content-Security-Policy": (
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    ),
}
