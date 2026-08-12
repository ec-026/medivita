from app import create_app
from app.config import TestConfig
from app.utils.errors import ServiceError


class MissingKeyConfig(TestConfig):
    LLM_PROVIDER = "groq"
    SEARCH_PROVIDER = "duckduckgo"
    NEWS_PROVIDER = "duckduckgo"
    GROQ_API_KEY = ""


def payload():
    return {
        "message": "What general information is available about sleep health?",
        "enabled_sources": ["healthline"],
        "history": [],
    }


def test_connected_api_reports_missing_key_without_searching_network():
    app = create_app(MissingKeyConfig)
    response = app.test_client().post("/api/chat", json=payload())
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CONFIGURATION"


def test_connected_api_preserves_normalized_provider_error(monkeypatch):
    class FailedController:
        def chat(self, *_args):
            raise ServiceError("AI_RATE_LIMITED", "Try again shortly.", 429)

    monkeypatch.setattr("app.services.chat.build_research_controller", lambda _config: FailedController())
    app = create_app(MissingKeyConfig)
    response = app.test_client().post("/api/chat", json=payload())
    assert response.status_code == 429
    assert response.get_json()["error"] == {
        "code": "AI_RATE_LIMITED",
        "message": "Try again shortly.",
    }


def test_connected_health_reports_provider_and_model_without_secret():
    app = create_app(MissingKeyConfig)
    body = app.test_client().get("/api/health").get_json()
    assert body["mode"] == "connected"
    assert body["providers"]["model"] == "openai/gpt-oss-20b"
    assert "GROQ_API_KEY" not in str(body)
