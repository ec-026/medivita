"""Trusted web-search provider contracts and DDGS implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from app.models import SearchResult, SourceReference, TargetedSearch
from app.services.trace import ResearchTraceEmitter
from app.sources import get_source
from app.utils.cache import TTLCache
from app.utils.text import normalize_text
from app.utils.url_safety import canonical_url, is_trusted_https_url

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _search_cache(ttl_seconds: int) -> TTLCache[list[SearchResult]]:
    return TTLCache(ttl_seconds)


class SearchProvider(ABC):
    @abstractmethod
    def search(
        self, query: str, enabled_sources: list[str], *, round_number: int = 1
    ) -> list[SearchResult]:
        raise NotImplementedError

    def search_targeted(
        self, searches: list[TargetedSearch], *, round_number: int = 2
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for search in searches:
            results.extend(self.search(search.query, [search.source_id], round_number=round_number))
        return results


class DemoSearchProvider(SearchProvider):
    def search(
        self, query: str, enabled_sources: list[str], *, round_number: int = 1
    ) -> list[SearchResult]:
        topic = _topic_label(query)
        results = []
        for source_id in enabled_sources[:3]:
            source = get_source(source_id)
            if source:
                reference = source.demo_reference(topic)
                results.append(
                    SearchResult(
                        source_id=source_id,
                        source_name=reference.name,
                        domain=reference.domain,
                        title=reference.title,
                        url=reference.url,
                        snippet="Demo source homepage; no live article was retrieved.",
                        query=query,
                        result_type="demo",
                    )
                )
        return results


class DuckDuckGoSearchProvider(SearchProvider):
    def __init__(
        self,
        *,
        results_per_source: int = 2,
        max_workers: int = 4,
        timeout: float = 8,
        cache_ttl: int = 900,
        backends: tuple[str, ...] = ("brave", "bing", "duckduckgo"),
        ddgs_factory=DDGS,
        trace: ResearchTraceEmitter | None = None,
    ):
        self.results_per_source = max(1, min(results_per_source, 5))
        self.max_workers = max(1, min(max_workers, 8))
        self.timeout = timeout
        self.cache = _search_cache(cache_ttl)
        self.backends = tuple(dict.fromkeys(backend.strip().lower() for backend in backends if backend.strip()))
        if not self.backends:
            self.backends = ("brave", "bing", "duckduckgo")
        self.ddgs_factory = ddgs_factory
        self.trace = trace

    def search(
        self, query: str, enabled_sources: list[str], *, round_number: int = 1
    ) -> list[SearchResult]:
        jobs = [(source_id, query) for source_id in enabled_sources]
        return self._run_jobs(jobs, round_number)

    def search_targeted(
        self, searches: list[TargetedSearch], *, round_number: int = 2
    ) -> list[SearchResult]:
        return self._run_jobs(
            [(search.source_id, search.query) for search in searches], round_number
        )

    def _run_jobs(self, jobs: list[tuple[str, str]], round_number: int) -> list[SearchResult]:
        if not jobs:
            return []
        completed: dict[int, list[SearchResult]] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(jobs))) as pool:
            futures = {
                pool.submit(self._search_source, source_id, query, round_number): index
                for index, (source_id, query) in enumerate(jobs)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    completed[index] = future.result()
                except Exception as error:  # DDGS backends can fail independently.
                    source_id = jobs[index][0]
                    LOGGER.warning("Trusted search failed (source_id=%s, type=%s)", source_id, type(error).__name__)
                    completed[index] = []
        return [item for index in range(len(jobs)) for item in completed.get(index, [])]

    def _search_source(
        self, source_id: str, query: str, round_number: int
    ) -> list[SearchResult]:
        source = get_source(source_id)
        if source is None:
            return []
        discovery_query = f"site:{source.metadata.domain} {query}"
        trace_id = None
        if self.trace:
            trace_id = self.trace.emit(
                stage="search",
                status="running",
                label=f"Searching {source.metadata.name}",
                tool="DDGS Search",
                source_id=source_id,
                source_name=source.metadata.name,
                query=discovery_query,
                round=round_number,
            )
        cache_key = (
            f"{source_id}|{query.strip().lower()}|{self.results_per_source}|{','.join(self.backends)}"
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._emit_search_complete(
                trace_id, source_id, source.metadata.name, discovery_query, cached, round_number
            )
            return list(cached)
        domain = source.metadata.domain
        normalized: list[SearchResult] = []
        seen_urls: set[str] = set()
        for backend in self.backends:
            try:
                raw_results = self.ddgs_factory(timeout=self.timeout).text(
                    discovery_query,
                    safesearch="moderate",
                    max_results=self.results_per_source,
                    backend=backend,
                )
            except DDGSException as error:
                _log_backend_failure(source_id, backend, error)
                self._emit_backend_warning(source_id, source.metadata.name, backend, round_number)
                continue
            except Exception as error:  # Keep one backend implementation from blocking fallback.
                _log_backend_failure(source_id, backend, error)
                self._emit_backend_warning(source_id, source.metadata.name, backend, round_number)
                continue
            valid_count_before = len(normalized)
            if isinstance(raw_results, list):
                for item in raw_results:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("href") or item.get("url") or "")
                    if not is_trusted_https_url(url, domain):
                        continue
                    url_key = canonical_url(url)
                    if url_key in seen_urls:
                        continue
                    seen_urls.add(url_key)
                    normalized.append(
                        SearchResult(
                            source_id=source_id,
                            source_name=source.metadata.name,
                            domain=domain,
                            title=normalize_text(str(item.get("title") or source.metadata.name)),
                            url=url,
                            snippet=normalize_text(str(item.get("body") or item.get("snippet") or "")),
                            query=query,
                            result_type="web",
                            backend=backend,
                        )
                    )
                    if len(normalized) >= self.results_per_source:
                        break
            if len(normalized) >= self.results_per_source:
                break
            if len(normalized) == valid_count_before:
                LOGGER.info(
                    "Trusted search backend returned no valid results (source_id=%s, backend=%s)",
                    source_id,
                    backend,
                )
        if normalized:
            self.cache.set(cache_key, normalized)
        self._emit_search_complete(
            trace_id, source_id, source.metadata.name, discovery_query, normalized, round_number
        )
        return normalized

    def _emit_backend_warning(
        self, source_id: str, source_name: str, backend: str, round_number: int
    ) -> None:
        if self.trace:
            self.trace.emit(
                stage="search",
                status="warning",
                label=f"{backend.title()} unavailable",
                tool="DDGS Search",
                source_id=source_id,
                source_name=source_name,
                backend=backend,
                round=round_number,
                message="Search backend fallback used",
            )

    def _emit_search_complete(
        self,
        trace_id: str | None,
        source_id: str,
        source_name: str,
        discovery_query: str,
        results: list[SearchResult],
        round_number: int,
    ) -> None:
        if not self.trace or not trace_id:
            return
        backends = list(dict.fromkeys(item.backend for item in results if item.backend))
        self.trace.emit(
            event_id=trace_id,
            stage="search",
            status="completed" if results else "warning",
            label=f"{source_name} search complete" if results else f"No {source_name} results",
            tool="DDGS Search",
            source_id=source_id,
            source_name=source_name,
            backend=" + ".join(backends) if backends else None,
            query=discovery_query,
            result_count=len(results),
            round=round_number,
        )


def build_search_provider(
    name: str,
    config: dict | None = None,
    trace: ResearchTraceEmitter | None = None,
) -> SearchProvider:
    if name == "demo":
        return DemoSearchProvider()
    if name == "duckduckgo":
        values = config or {}
        return DuckDuckGoSearchProvider(
            results_per_source=values.get("SEARCH_RESULTS_PER_SOURCE", 2),
            max_workers=values.get("SEARCH_MAX_WORKERS", 4),
            timeout=values.get("SEARCH_TIMEOUT", 8),
            cache_ttl=values.get("RETRIEVAL_CACHE_TTL_SECONDS", 900),
            backends=values.get("DDGS_TEXT_BACKENDS", ("brave", "bing", "duckduckgo")),
            trace=trace,
        )
    raise ValueError(f"Unsupported search provider: {name}")


def as_source_reference(item: SearchResult) -> SourceReference:
    return SourceReference(
        name=item.source_name,
        domain=item.domain,
        title=item.title,
        url=item.url,
    )


def _log_backend_failure(source_id: str, backend: str, error: Exception) -> None:
    LOGGER.warning(
        "Trusted search backend failed (source_id=%s, backend=%s, type=%s)",
        source_id,
        backend,
        type(error).__name__,
    )


def _topic_label(query: str) -> str:
    lowered = query.lower()
    for keyword, label in (
        ("migraine", "Migraine"),
        ("headache", "Headache"),
        ("ibuprofen", "Ibuprofen"),
        ("insulin", "Insulin resistance"),
        ("sleep", "Sleep health"),
        ("vitamin d", "Vitamin D"),
        ("allerg", "Seasonal allergies"),
    ):
        if keyword in lowered:
            return label
    return "General health"
