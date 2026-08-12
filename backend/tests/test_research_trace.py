import json

from ddgs.exceptions import DDGSException

from app import create_app
from app.config import TestConfig
from app.models import (
    ChatPlan,
    EvidenceItem,
    FinalChatAnswer,
    SearchResult,
    TargetedSearch,
)
from app.providers.search import DuckDuckGoSearchProvider, SearchProvider
from app.services.chat import ChatService
from app.services.research import BoundedResearchController, ChatControllerAnswer
from app.services.retrieval import RetrievalService
from app.services.trace import ResearchTraceEmitter


def final_answer(ids=None):
    return FinalChatAnswer(
        overview="Grounded overview.",
        possible_considerations="Grounded considerations.",
        what_may_help="Grounded conservative information.",
        when_to_seek_medical_care="Grounded care guidance.",
        used_evidence_ids=ids or ["E1"],
    )


def evidence(item_id="E1"):
    return EvidenceItem(
        id=item_id,
        source_id="healthline",
        source_name="Healthline",
        domain="healthline.com",
        title="Trusted article",
        url=f"https://healthline.com/{item_id.lower()}",
        snippet="Trusted snippet.",
        content="Evidence content must not appear in trace output.",
        query="migraine",
        result_type="page",
    )


class TraceDDGS:
    def __init__(self, **_kwargs):
        pass

    def text(self, _query, **kwargs):
        if kwargs["backend"] == "brave":
            raise DDGSException("raw provider failure must stay private")
        return [
            {
                "title": "Trusted article",
                "href": "https://www.healthline.com/health/migraine",
                "body": "search result body",
            }
        ]


class StaticSearch(SearchProvider):
    def __init__(self, results):
        self.results = results

    def search(self, _query, _enabled_sources, *, round_number=1):
        return self.results


class PageRetrieval(RetrievalService):
    def __init__(self, results, pages, trace):
        super().__init__(StaticSearch(results), fetch_per_source=2, cache_ttl=0, trace=trace)
        self.pages = pages

    def _fetch_page(self, result):
        return self.pages.get(result.url, "")


class FakeRetrieval:
    def __init__(self, additions=None):
        self.additions = additions or []

    def retrieve(self, *_args):
        return [evidence()]

    def retrieve_targeted(self, _searches, *, round_number=2):
        return self.additions or [evidence()]


class FakeLLM:
    provider_name = "groq"
    model_name = "openai/gpt-oss-20b"

    def __init__(self, plan, answer=None):
        self.plan = plan
        self.answer = answer
        self.plan_calls = 0
        self.answer_calls = 0

    def chat_plan(self, *_args):
        self.plan_calls += 1
        return self.plan

    def chat_answer(self, *_args):
        self.answer_calls += 1
        return self.answer


def research_plan():
    return ChatPlan(
        action="research",
        intent="health_information",
        searches=[
            TargetedSearch(source_id="healthline", query="migraine warning signs")
        ],
    )


def test_search_trace_exposes_real_backend_query_count_and_only_enabled_source():
    trace = ResearchTraceEmitter()
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=TraceDDGS,
        cache_ttl=0,
        results_per_source=1,
        trace=trace,
    )
    provider.search("migraine symptoms", ["healthline"])
    serialized = json.dumps(trace.events)
    completed = next(
        event
        for event in trace.events
        if event["stage"] == "search" and event["status"] == "completed"
    )
    assert completed["backend"] == "bing"
    assert completed["query"] == "site:healthline.com migraine symptoms"
    assert completed["result_count"] == 1
    assert completed["source_name"] == "Healthline"
    assert "webmd" not in serialized.lower()
    assert "raw provider failure" not in serialized


def test_page_and_snippet_retrieval_emit_safe_events_and_evidence_count():
    trace = ResearchTraceEmitter()
    results = [
        SearchResult(
            source_id="healthline",
            source_name="Healthline",
            domain="healthline.com",
            title="Page article",
            url="https://healthline.com/page",
            snippet="fallback snippet",
            query="migraine",
        ),
        SearchResult(
            source_id="healthline",
            source_name="Healthline",
            domain="healthline.com",
            title="Snippet article",
            url="https://healthline.com/snippet",
            snippet="fallback snippet",
            query="migraine",
        ),
    ]
    PageRetrieval(
        results,
        {"https://healthline.com/page": "Readable page evidence about migraine patterns."},
        trace,
    ).retrieve("migraine", ["healthline"])
    retrieval_types = {
        event.get("retrieval_type")
        for event in trace.events
        if event["stage"] == "page_retrieval"
    }
    assert retrieval_types == {"page", "snippet"}
    assert any(
        event.get("evidence_count") == 2
        for event in trace.events
        if event["stage"] == "evidence"
    )
    serialized = json.dumps(trace.events)
    assert "Readable page evidence" not in serialized
    assert "fallback snippet" not in serialized


def test_generation_trace_has_groq_model_without_fake_second_round():
    trace = ResearchTraceEmitter()
    llm = FakeLLM(research_plan(), final_answer())
    BoundedResearchController(FakeRetrieval(), llm, trace=trace).chat(
        "question", ["healthline"], []
    )
    generation = [event for event in trace.events if event["stage"] == "generation"]
    assert len(generation) == 1
    assert generation[0]["provider"] == "groq"
    assert generation[0]["model"] == "openai/gpt-oss-20b"
    assert generation[0]["round"] == 1
    assert llm.plan_calls == 1
    assert llm.answer_calls == 1
    assert any(event["stage"] == "planning" for event in trace.events)
    assert trace.summary == {
        "rounds": 1,
        "evidence_count": 1,
        "citation_count": 1,
        "total_ms": trace.summary["total_ms"],
    }


def test_direct_trace_has_no_fake_search_retrieval_or_generation():
    trace = ResearchTraceEmitter()
    llm = FakeLLM(
        ChatPlan(
            action="direct",
            intent="greeting",
            direct_response="Hello! How can I help?",
        )
    )
    outcome, sources, calls = BoundedResearchController(
        FakeRetrieval(), llm, trace=trace
    ).chat("Hello", ["healthline"], [])
    assert outcome.response_kind == "direct"
    assert sources == []
    assert calls == 1
    assert llm.plan_calls == 1
    assert llm.answer_calls == 0
    assert not any(
        event["stage"] in {"search", "page_retrieval", "evidence", "generation", "citation"}
        for event in trace.events
    )
    assert any(event["label"] == "No research needed" for event in trace.events)
    assert trace.summary["rounds"] == 0


def test_trace_exposes_only_executed_targeted_searches_and_no_planner_explanation():
    trace = ResearchTraceEmitter()
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=TraceDDGS,
        cache_ttl=0,
        results_per_source=1,
        trace=trace,
    )
    retrieval = RetrievalService(provider, cache_ttl=0, trace=trace)
    retrieval._fetch_page = lambda _result: "Readable migraine evidence."
    llm = FakeLLM(research_plan(), final_answer())
    BoundedResearchController(retrieval, llm, trace=trace).chat(
        "raw user wording", ["healthline"], []
    )
    search_events = [
        event
        for event in trace.events
        if event["stage"] == "search" and event["status"] == "completed"
    ]
    assert search_events
    assert all("migraine warning signs" in str(event.get("query")) for event in search_events)
    serialized = json.dumps(trace.events).lower()
    assert "raw user wording" not in serialized
    assert "chain_of_thought" not in serialized
    assert "thought:" not in serialized
    assert "reasoning:" not in serialized
    assert '"reason"' not in serialized


def test_urgent_safety_trace_precedes_planning_and_direct_response(monkeypatch):
    class ConnectedTestConfig(TestConfig):
        LLM_PROVIDER = "groq"
        SEARCH_PROVIDER = "duckduckgo"

    def build_controller(_config, trace=None):
        class Controller:
            def chat(self, *_args):
                trace.emit(
                    stage="planning",
                    status="completed",
                    label="No research needed",
                    tool="LangChain structured planning",
                )
                trace.finish(
                    rounds=0,
                    evidence_count=0,
                    citation_count=0,
                    label="Response ready",
                )
                return ChatControllerAnswer("direct", "Please seek urgent help."), [], 1

        return Controller()

    monkeypatch.setattr("app.services.chat.build_research_controller", build_controller)
    app = create_app(ConnectedTestConfig)
    trace = ResearchTraceEmitter()
    with app.app_context():
        result = ChatService().respond(
            "I cannot breathe",
            ["healthline"],
            [],
            trace,
        )
    assert [event["stage"] for event in trace.events][:2] == ["safety", "planning"]
    assert result["safety_notice"]
    assert result["response_kind"] == "direct"
    assert result["sources"] == []


def test_stream_endpoint_preserves_standard_contract_and_serializes_safe_trace(monkeypatch):
    response_body = {
        "answer": "Grounded overview.",
        "sections": [{"title": "Overview", "content": "Grounded overview."}],
        "sources": [],
        "safety_notice": None,
        "mode": "connected",
        "disclaimer": "General health information only.",
    }

    def respond(_self, _message, _sources, _history, trace=None):
        result = dict(response_body)
        if trace:
            trace.emit(
                stage="search",
                status="completed",
                label="Healthline search complete",
                tool="DDGS Search",
                source_id="healthline",
                source_name="Healthline",
                backend="bing",
                query="site:healthline.com migraine symptoms",
                result_count=1,
                round=1,
            )
            trace.finish(rounds=1, evidence_count=1, citation_count=1)
            result["research_trace"] = trace.events
            result["research_summary"] = trace.summary
        return result

    monkeypatch.setattr("app.routes.api.ChatService.respond", respond)
    client = create_app(TestConfig).test_client()
    payload = {
        "message": "What information is available about migraine symptoms?",
        "enabled_sources": ["healthline"],
        "history": [],
    }
    standard = client.post("/api/chat", json=payload).get_json()
    assert standard == response_body
    assert "research_trace" not in standard

    streamed = client.post("/api/chat/stream", json=payload)
    events = [json.loads(line) for line in streamed.get_data(as_text=True).splitlines()]
    assert streamed.content_type.startswith("application/x-ndjson")
    assert [event["event"] for event in events][-2:] == ["result", "done"]
    result = next(event["data"] for event in events if event["event"] == "result")
    for key, value in standard.items():
        assert result[key] == value
    serialized = json.dumps(events)
    assert "API_KEY" not in serialized
    assert "Authorization" not in serialized
    assert "Thought" not in serialized
    assert "chain_of_thought" not in serialized


def test_health_check_stream_reuses_the_normalized_trace_contract(monkeypatch):
    def summarize(_self, _description, _sources, trace=None):
        result = {
            "summary": "Non-diagnostic summary.",
            "reported_symptoms": ["headache"],
            "general_considerations": ["Patterns matter."],
            "self_care": ["Record changes."],
            "seek_medical_attention": ["Seek advice if symptoms worsen."],
            "sources": [],
            "safety_notice": None,
            "mode": "connected",
        }
        if trace:
            trace.emit(
                stage="evidence",
                status="completed",
                label="Relevant evidence selected",
                tool="MediVita Evidence Ranker",
                evidence_count=1,
                round=1,
            )
            trace.finish(rounds=1, evidence_count=1, citation_count=1)
            result["research_trace"] = trace.events
            result["research_summary"] = trace.summary
        return result

    monkeypatch.setattr("app.routes.api.HealthCheckService.summarize", summarize)
    client = create_app(TestConfig).test_client()
    response = client.post(
        "/api/health-check/stream",
        json={
            "description": "I have had a mild headache for two days.",
            "enabled_sources": ["healthline"],
        },
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines()]
    assert any(event["event"] == "trace" for event in events)
    result = next(event["data"] for event in events if event["event"] == "result")
    assert result["summary"] == "Non-diagnostic summary."
    assert result["research_summary"]["rounds"] == 1
