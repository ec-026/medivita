"""Thin REST and NDJSON streaming route layer."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from queue import Queue
from threading import Thread

from flask import Blueprint, Response, current_app, jsonify, request

from app.providers.llm import configured_model
from app.services.chat import ChatService
from app.services.health_check import HealthCheckService
from app.services.news import NewsService
from app.services.trace import ResearchTraceEmitter
from app.sources import list_sources
from app.utils.validation import (
    ValidationError,
    clean_history,
    require_json_object,
    require_source_list,
    require_text,
)

api = Blueprint("api", __name__)


def error_response(code: str, message: str, status: int):
    return jsonify(error={"code": code, "message": message}), status


@api.get("/health")
def health():
    mode = "demo" if current_app.config["LLM_PROVIDER"] == "demo" else "connected"
    return jsonify(
        status="ok",
        service="medivita-api",
        mode=mode,
        providers={
            "llm": current_app.config["LLM_PROVIDER"],
            "search": current_app.config["SEARCH_PROVIDER"],
            "news": current_app.config["NEWS_PROVIDER"],
            "model": configured_model(current_app.config),
        },
    )


@api.get("/sources")
def sources():
    return jsonify(sources=[source.metadata.to_dict() for source in list_sources()])


@api.post("/chat")
def chat():
    try:
        payload = require_json_object(request.get_json(silent=True))
        result = ChatService().respond(require_text(payload, "message", maximum=3000), require_source_list(payload), clean_history(payload))
        return jsonify(result)
    except ValidationError as error:
        return error_response("VALIDATION_ERROR", str(error), 400)
    except ValueError as error:
        return error_response("INVALID_CONFIGURATION", str(error), 400)


@api.post("/chat/stream")
def chat_stream():
    try:
        payload = require_json_object(request.get_json(silent=True))
        message = require_text(payload, "message", maximum=3000)
        source_ids = require_source_list(payload)
        history = clean_history(payload)
        return _ndjson_response(
            lambda trace: ChatService().respond(message, source_ids, history, trace)
        )
    except ValidationError as error:
        return error_response("VALIDATION_ERROR", str(error), 400)
    except ValueError as error:
        return error_response("INVALID_CONFIGURATION", str(error), 400)


@api.post("/health-check")
def health_check():
    try:
        payload = require_json_object(request.get_json(silent=True))
        result = HealthCheckService().summarize(require_text(payload, "description", minimum=10, maximum=4000), require_source_list(payload))
        return jsonify(result)
    except ValidationError as error:
        return error_response("VALIDATION_ERROR", str(error), 400)
    except ValueError as error:
        return error_response("INVALID_CONFIGURATION", str(error), 400)


@api.post("/health-check/stream")
def health_check_stream():
    try:
        payload = require_json_object(request.get_json(silent=True))
        description = require_text(payload, "description", minimum=10, maximum=4000)
        source_ids = require_source_list(payload)
        return _ndjson_response(
            lambda trace: HealthCheckService().summarize(description, source_ids, trace)
        )
    except ValidationError as error:
        return error_response("VALIDATION_ERROR", str(error), 400)
    except ValueError as error:
        return error_response("INVALID_CONFIGURATION", str(error), 400)


@api.get("/news")
def news():
    category = request.args.get("category", "all").lower()
    try:
        limit = int(request.args.get("limit", "12"))
        if not 1 <= limit <= 50:
            raise ValueError("'limit' must be between 1 and 50.")
        mode = "demo" if current_app.config["NEWS_PROVIDER"] == "demo" else "connected"
        return jsonify(articles=NewsService().list_articles(category, limit), mode=mode)
    except ValueError as error:
        return error_response("VALIDATION_ERROR", str(error), 400)


def _ndjson_response(run: Callable[[ResearchTraceEmitter], dict]) -> Response:
    app = current_app._get_current_object()
    messages: Queue[dict[str, object]] = Queue()

    def publish(event: dict[str, object]) -> None:
        messages.put({"event": "trace", "data": event})

    def worker() -> None:
        with app.app_context():
            try:
                result = run(ResearchTraceEmitter(publish))
                messages.put({"event": "result", "data": result})
            except ValidationError as error:
                messages.put(
                    {"event": "error", "data": {"code": "VALIDATION_ERROR", "message": str(error)}}
                )
            except ValueError as error:
                messages.put(
                    {
                        "event": "error",
                        "data": {"code": "INVALID_CONFIGURATION", "message": str(error)},
                    }
                )
            except Exception as error:
                code = getattr(error, "code", "INTERNAL_ERROR")
                message = getattr(error, "message", "MediVita could not complete the request.")
                if code == "INTERNAL_ERROR":
                    app.logger.exception("Unexpected streaming API error", exc_info=error)
                messages.put({"event": "error", "data": {"code": code, "message": message}})
            finally:
                messages.put({"event": "done"})

    def generate() -> Iterator[str]:
        Thread(target=worker, daemon=True).start()
        while True:
            item = messages.get()
            yield json.dumps(item, separators=(",", ":")) + "\n"
            if item["event"] == "done":
                break

    return Response(
        generate(),
        content_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
