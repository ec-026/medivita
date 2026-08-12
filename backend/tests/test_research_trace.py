import json

from ddgs.exceptions import DDGSException

from app import create_app
from app.config import TestConfig
from app.models import (
    ChatResearchDecision,
    EvidenceItem,
    FinalChatAnswer,
    SearchResult,
    TargetedSearch,
)
from app.providers.search import DuckDuckGoSearchProvider, SearchProvider
from app.services.research import BoundedResearchController
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

    def retrieve_targeted(self, _searches):
        return self.additions


class FakeLLM:
    provider_name = "groq"
    model_name = "openai/gpt-oss-20b"

    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = 0

    def chat_decision(self, *_args):
        decision = self.decisions[self.calls]
        self.calls += 1
        return decision


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
    llm = FakeLLM([ChatResearchDecision(decision="answer", answer=final_answer())])
    BoundedResearchController(FakeRetrieval(), llm, trace=trace).chat(
        "question", ["healthline"], []
    )
    generation = [event for event in trace.events if event["stage"] == "generation"]
    assert len(generation) == 1
    assert generation[0]["provider"] == "groq"
    assert generation[0]["model"] == "openai/gpt-oss-20b"
    assert generation[0]["round"] == 1
    assert trace.summary == {
        "rounds": 1,
        "evidence_count": 1,
        "citation_count": 1,
        "total_ms": trace.summary["total_ms"],
    }


def test_second_research_round_is_traced_only_when_controller_requests_it():
    trace = ResearchTraceEmitter()
    llm = FakeLLM(
        [
            ChatResearchDecision(
                decision="search_more",
                follow_up_searches=[
                    TargetedSearch(source_id="healthline", query="migraine warning signs")
                ],
            ),
            ChatResearchDecision(decision="answer", answer=final_answer()),
        ]
    )
    BoundedResearchController(FakeRetrieval([evidence("E2")]), llm, trace=trace).chat(
        "question", ["healthline"], []
    )
    assert llm.calls == 2
    assert any(event.get("round") == 2 for event in trace.events)
    assert any(event["label"] == "Additional research requested" for event in trace.events)
    assert trace.summary["rounds"] == 2


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
