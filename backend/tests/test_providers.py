import pytest
from ddgs.exceptions import DDGSException

from app.models import ChatPlan, FinalChatAnswer, HealthResearchDecision
from app.providers.llm import GroqProvider, OpenRouterProvider
from app.providers.news import DuckDuckGoNewsProvider
from app.utils.errors import ServiceError


class RaisingRunnable:
    def __init__(self, error):
        self.error = error

    def invoke(self, _messages):
        raise self.error


class RaisingChat:
    def __init__(self, error):
        self.error = error

    def with_structured_output(self, *_args, **_kwargs):
        return RaisingRunnable(self.error)


class StatusError(RuntimeError):
    status_code = 429


class TimeoutFailure(RuntimeError):
    pass


class NewsDDGS:
    def __init__(self, **_kwargs):
        pass

    def news(self, _query, **_kwargs):
        return [
            {
                "title": "Trusted health report",
                "body": "A concise report about public health research.",
                "url": "https://www.reuters.com/world/health-report",
                "source": "Reuters",
                "date": "2026-08-10T10:00:00+00:00",
            },
            {
                "title": "Untrusted report",
                "body": "This should be excluded from connected news.",
                "url": "https://unknown.example/health",
                "source": "Unknown",
                "date": "2026-08-11T10:00:00+00:00",
            },
        ]


class EmptyNewsDDGS(NewsDDGS):
    def news(self, _query, **_kwargs):
        return []


class FallbackNewsDDGS(NewsDDGS):
    calls = []

    def news(self, query, **kwargs):
        backend = kwargs["backend"]
        self.calls.append(backend)
        if backend == "bing":
            raise DDGSException("blocked")
        if backend == "yahoo":
            return super().news(query, **kwargs)
        return []


def test_groq_requires_key_without_making_request():
    with pytest.raises(ServiceError) as raised:
        GroqProvider(api_key="", model="openai/gpt-oss-20b")
    assert raised.value.code == "INVALID_CONFIGURATION"
    assert "GROQ_API_KEY" in raised.value.message


def test_groq_normalizes_rate_limit():
    provider = GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        chat_model=RaisingChat(StatusError("limited")),
    )
    with pytest.raises(ServiceError) as raised:
        provider.chat_plan("question", [], ["healthline"])
    assert raised.value.code == "AI_RATE_LIMITED"
    assert raised.value.status == 429


def test_groq_normalizes_timeout():
    provider = GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        chat_model=RaisingChat(TimeoutFailure("timeout")),
    )
    with pytest.raises(ServiceError) as raised:
        provider.chat_plan("question", [], ["healthline"])
    assert raised.value.code == "AI_TIMEOUT"
    assert raised.value.status == 504


def test_groq_configuration_uses_requested_model_and_hidden_low_reasoning(monkeypatch):
    captured = {}

    class CapturingChat:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.providers.llm.ChatGroq", CapturingChat)
    GroqProvider(api_key="test-key", model="openai/gpt-oss-20b")
    assert captured["model"] == "openai/gpt-oss-20b"
    assert captured["reasoning_effort"] == "low"
    assert captured["reasoning_format"] == "hidden"
    assert captured["max_retries"] == 1


def test_openrouter_remains_an_explicit_optional_provider(monkeypatch):
    captured = {}

    class CapturingChat:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.providers.llm.ChatOpenRouter", CapturingChat)
    OpenRouterProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b:free",
        data_collection="deny",
    )
    assert captured["openrouter_provider"] == {"sort": "latency", "data_collection": "deny"}


def test_final_answer_schemas_require_used_evidence_ids_field():
    chat_schema = FinalChatAnswer.model_json_schema()
    health_schema = HealthResearchDecision.model_json_schema()["$defs"]["FinalHealthCheckAnswer"]
    assert "used_evidence_ids" in chat_schema["required"]
    assert "used_evidence_ids" in health_schema["required"]


def test_chat_plan_schema_contains_no_reasoning_or_explanation_fields():
    serialized = str(ChatPlan.model_json_schema()).lower()
    assert "reasoning" not in serialized
    assert "chain_of_thought" not in serialized
    assert "missing_information" not in serialized
    assert "reason" not in ChatPlan.model_json_schema()["$defs"]["TargetedSearch"]["properties"]


def test_live_news_uses_actual_allowlisted_urls():
    provider = DuckDuckGoNewsProvider(ddgs_factory=NewsDDGS, cache_ttl=0)
    articles = provider.articles("research", 10)
    assert len(articles) == 1
    assert articles[0]["publisher"] == "Reuters"
    assert articles[0]["url"].startswith("https://www.reuters.com/")


def test_live_news_fails_cleanly_instead_of_returning_demo_data():
    provider = DuckDuckGoNewsProvider(ddgs_factory=EmptyNewsDDGS, cache_ttl=0)
    with pytest.raises(ServiceError) as raised:
        provider.articles("research", 10)
    assert raised.value.code == "NEWS_UNAVAILABLE"


def test_live_news_falls_back_between_individual_backends():
    FallbackNewsDDGS.calls = []
    provider = DuckDuckGoNewsProvider(
        ddgs_factory=FallbackNewsDDGS,
        cache_ttl=0,
        results_limit=1,
    )
    articles = provider.articles("research", 1)
    assert len(articles) == 1
    assert FallbackNewsDDGS.calls == ["bing", "yahoo"]


def test_health_metadata_never_contains_api_keys(client):
    body = client.get("/api/health").get_json()
    assert "key" not in str(body).lower()
