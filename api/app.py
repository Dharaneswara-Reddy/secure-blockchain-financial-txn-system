"""
Flask application factory.

Usage::

    # Development server
    flask --app api/app.py run --debug

    # In tests
    from api.app import create_app
    client = create_app().test_client()
"""

from flask import Flask

from api.routes.blocks import blocks_bp
from api.routes.chain import chain_bp
from api.routes.tamper import tamper_bp
from api.routes.transactions import transactions_bp


def create_app() -> Flask:
    """Create and configure the Flask application.

    All routes are registered under ``/api``.
    The root ``/`` serves the Block Explorer SPA from ``api/static/``.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__, static_folder="static", static_url_path="")

    app.register_blueprint(blocks_bp, url_prefix="/api")
    app.register_blueprint(transactions_bp, url_prefix="/api")
    app.register_blueprint(chain_bp, url_prefix="/api")
    app.register_blueprint(tamper_bp, url_prefix="/api")

    @app.route("/")
    def index():  # type: ignore[return-value]
        return app.send_static_file("index.html")

    return app
