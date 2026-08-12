"""MediVita Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.routes.api import api
from app.utils.errors import ServiceError


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )
    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error={"code": "PAYLOAD_TOO_LARGE", "message": "Request payload is too large."}), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error={"code": "NOT_FOUND", "message": "The requested endpoint was not found."}), 404

    @app.errorhandler(ServiceError)
    def service_error(error):
        return jsonify(error={"code": error.code, "message": error.message}), error.status

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unexpected API error", exc_info=error)
        return jsonify(error={"code": "INTERNAL_ERROR", "message": "MediVita could not complete the request."}), 500

    app.logger.info(
        "MediVita API starting (llm=%s, search=%s, news=%s)",
        app.config["LLM_PROVIDER"],
        app.config["SEARCH_PROVIDER"],
        app.config["NEWS_PROVIDER"],
    )
    return app
