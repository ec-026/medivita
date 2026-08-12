from dataclasses import replace

from ddgs.exceptions import DDGSException

from app.models import SearchResult, TargetedSearch
from app.providers.search import DuckDuckGoSearchProvider, SearchProvider, as_source_reference
from app.services.retrieval import RetrievalService, merge_evidence
from app.utils.text import extract_readable_text, select_relevant_text
from app.utils.url_safety import canonical_url, is_trusted_https_url


class BackendDDGS:
    calls = []
    behaviors = {}

    def __init__(self, **_kwargs):
        pass

    def text(self, query, **kwargs):
        backend = kwargs["backend"]
        self.calls.append((query, backend))
        behavior = self.behaviors.get(backend, [])
        for key, configured_behavior in self.behaviors.items():
            if not isinstance(key, tuple):
                continue
            domain, configured_backend = key
            if configured_backend == backend and domain in query:
                behavior = configured_behavior
                break
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


def configure_ddgs(behaviors):
    BackendDDGS.calls = []
    BackendDDGS.behaviors = behaviors


def healthline_result(url="https://www.healthline.com/health/sleep"):
    return {"title": "Healthline", "href": url, "body": "sleep body"}


def cleveland_result():
    return {"title": "Clinic", "href": "https://my.clevelandclinic.org/health/sleep", "body": "clinic"}


def result(source_id="healthline", url="https://www.healthline.com/health/sleep", snippet="fallback snippet"):
    return SearchResult(
        source_id=source_id,
        source_name="Healthline",
        domain="healthline.com",
        title="Sleep information",
        url=url,
        snippet=snippet,
        query="sleep",
    )


class StaticSearch(SearchProvider):
    def __init__(self, results):
        self.results = results

    def search(self, _query, _enabled_sources):
        return self.results


class StubRetrievalService(RetrievalService):
    def __init__(self, results, pages):
        super().__init__(StaticSearch(results), cache_ttl=0, total_chars=500, per_source_chars=300)
        self.pages = pages

    def _fetch_page(self, item):
        value = self.pages.get(item.url, "")
        if isinstance(value, Exception):
            raise value
        return value


class RedirectResponse:
    status_code = 302
    headers = {"location": "https://evil.example/stolen"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class RedirectClient:
    calls = []

    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def stream(self, _method, url):
        self.calls.append(url)
        return RedirectResponse()


def test_ddgs_searches_each_selected_source_and_filters_spoofed_domains():
    configure_ddgs(
        {
            ("healthline.com", "brave"): [
                healthline_result("https://healthline.com.evil.example/health"),
                healthline_result(),
            ],
            ("clevelandclinic.org", "brave"): [cleveland_result()],
        }
    )
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    results = provider.search("sleep", ["healthline", "cleveland-clinic"])
    assert [item.source_id for item in results] == ["healthline", "cleveland-clinic"]
    assert len(BackendDDGS.calls) == 2
    assert all("site:" in query for query, _backend in BackendDDGS.calls)
    assert not any("webmd.com" in query for query, _backend in BackendDDGS.calls)


def test_ddgs_partial_source_failure_keeps_successful_sources():
    configure_ddgs(
        {
            ("healthline.com", "brave"): DDGSException("failed"),
            ("healthline.com", "bing"): DDGSException("failed"),
            ("healthline.com", "duckduckgo"): DDGSException("failed"),
            ("clevelandclinic.org", "brave"): [cleveland_result()],
        }
    )
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    results = provider.search("sleep", ["healthline", "cleveland-clinic"])
    assert [item.source_id for item in results] == ["cleveland-clinic"]


def test_brave_success_stops_before_other_text_backends():
    configure_ddgs({"brave": [healthline_result()]})
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    assert provider.search("sleep", ["healthline"])
    assert [backend for _query, backend in BackendDDGS.calls] == ["brave"]


def test_brave_failure_falls_back_to_bing():
    configure_ddgs(
        {
            "brave": DDGSException("blocked"),
            "bing": [healthline_result()],
        }
    )
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    assert provider.search("sleep", ["healthline"])
    assert [backend for _query, backend in BackendDDGS.calls] == ["brave", "bing"]


def test_brave_and_bing_fail_then_duckduckgo_succeeds():
    configure_ddgs(
        {
            "brave": DDGSException("blocked"),
            "bing": DDGSException("unsupported"),
            "duckduckgo": [healthline_result()],
        }
    )
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    results = provider.search("sleep", ["healthline"])
    assert [backend for _query, backend in BackendDDGS.calls] == ["brave", "bing", "duckduckgo"]
    assert as_source_reference(results[0]).url == "https://www.healthline.com/health/sleep"


def test_all_text_backends_fail_cleanly():
    configure_ddgs(
        {
            "brave": DDGSException("blocked"),
            "bing": DDGSException("unsupported"),
            "duckduckgo": DDGSException("rate limited"),
        }
    )
    provider = DuckDuckGoSearchProvider(ddgs_factory=BackendDDGS, cache_ttl=0)
    assert provider.search("sleep", ["healthline"]) == []
    assert [backend for _query, backend in BackendDDGS.calls] == ["brave", "bing", "duckduckgo"]


def test_malformed_and_lookalike_results_trigger_next_backend():
    configure_ddgs(
        {
            "brave": ["not-a-result", healthline_result("https://healthline.com.evil.example/")],
            "bing": [healthline_result()],
        }
    )
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    results = provider.search("sleep", ["healthline"])
    assert [backend for _query, backend in BackendDDGS.calls] == ["brave", "bing"]
    assert [item.url for item in results] == ["https://www.healthline.com/health/sleep"]


def test_url_validation_requires_https_exact_domain_or_subdomain():
    assert is_trusted_https_url("https://my.clevelandclinic.org/health", "clevelandclinic.org")
    assert not is_trusted_https_url("http://healthline.com/health", "healthline.com")
    assert not is_trusted_https_url("https://healthline.com.evil.example/", "healthline.com")
    assert not is_trusted_https_url("https://user:pass@healthline.com/", "healthline.com")


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url("https://WWW.Healthline.com/a/?utm_source=x&b=2#top") == "https://www.healthline.com/a?b=2"


def test_html_extraction_removes_navigation_and_ranks_relevant_text():
    html = "<nav>Ignore navigation words forever and ever.</nav><main><p>Sleep schedules can affect daily alertness and general wellbeing.</p><p>Hydration is another general health topic with different considerations.</p></main>"
    text = extract_readable_text(html)
    selected = select_relevant_text(text, "sleep schedule", "Sleep", 100)
    assert "navigation" not in text
    assert selected.startswith("Sleep schedules")


def test_retrieval_uses_page_text_and_assigns_backend_evidence_ids():
    item = result()
    service = StubRetrievalService([item], {item.url: "Sleep routines can support regular rest and daily functioning."})
    evidence = service.retrieve("sleep", ["healthline"])
    assert evidence[0].id == "E1"
    assert evidence[0].result_type == "page"
    assert "Sleep routines" in evidence[0].content


def test_retrieval_falls_back_to_search_snippet_when_page_fails():
    item = result()
    service = StubRetrievalService([item], {item.url: RuntimeError("fetch failed")})
    evidence = service.retrieve("sleep", ["healthline"])
    assert evidence[0].content == "fallback snippet"
    assert evidence[0].result_type == "snippet"


def test_page_fetch_rejects_redirect_that_leaves_trusted_domain():
    RedirectClient.calls = []
    service = RetrievalService(
        StaticSearch([]),
        client_factory=RedirectClient,
        cache_ttl=0,
    )
    assert service._fetch_page(result()) == ""
    assert RedirectClient.calls == ["https://www.healthline.com/health/sleep"]


def test_merge_evidence_deduplicates_canonical_urls_and_reassigns_stable_ids():
    service = StubRetrievalService([result()], {result().url: "Useful sleep information for general education and context."})
    first = service.retrieve("sleep", ["healthline"])[0]
    duplicate = replace(first, id="E99", url=f"{first.url}/?utm_source=test")
    second = replace(first, id="E1", url="https://www.healthline.com/health/other", title="Other")
    merged = merge_evidence([first], [duplicate, second], 1000)
    assert [item.id for item in merged] == ["E1", "E2"]


def test_targeted_search_interface_preserves_source_query_pairs():
    configure_ddgs({"brave": [healthline_result()]})
    provider = DuckDuckGoSearchProvider(
        ddgs_factory=BackendDDGS,
        cache_ttl=0,
        results_per_source=1,
    )
    results = provider.search_targeted([TargetedSearch(source_id="healthline", query="sleep duration")])
    assert results[0].query == "sleep duration"
