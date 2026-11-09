from __future__ import annotations

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

from .config import Config
from .db import ensure_schema
from .security import SECURITY_HEADERS

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])


def create_app() -> Flask:
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config.from_object(Config)

    csrf.init_app(app)
    limiter.init_app(app)

    from .blueprints.admin import bp as admin_bp
    from .blueprints.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    limiter.limit("20 per minute")(app.view_functions["main.draw"])
    limiter.limit("10 per minute")(app.view_functions["admin.login_post"])

    @app.before_request
    def _force_https():
        if app.config.get("FORCE_HTTPS"):
            proto = request.headers.get("X-Forwarded-Proto", request.scheme)
            if proto != "https":
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)
        return None

    @app.after_request
    def _set_security_headers(response):
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    with app.app_context():
        ensure_schema()

    return app
