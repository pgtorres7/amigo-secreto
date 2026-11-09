from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

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
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    limiter.init_app(app)

    from .blueprints.api import bp as api_bp
    from .blueprints.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    limiter.limit("20 per minute")(app.view_functions["api.draw"])
    limiter.limit("10 per minute")(app.view_functions["api.admin_login"])

    @app.before_request
    def _force_https():
        if app.config.get("FORCE_HTTPS") or os.getenv("VERCEL"):
            proto = request.headers.get("X-Forwarded-Proto", request.scheme)
            if proto != "https":
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)
        return None

    @app.after_request
    def _set_security_headers(response):
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    @app.errorhandler(400)
    def bad_request(err):
        description = getattr(err, "description", "Requisição inválida.")
        if request.path.startswith("/api/"):
            return jsonify({"error": description}), 400
        return render_template("index.html"), 400

    with app.app_context():
        ensure_schema()

    return app
