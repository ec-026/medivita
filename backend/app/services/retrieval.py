"""Secure page retrieval and compact request-local evidence construction."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from time import monotonic
from urllib.parse import urljoin

import httpx

from app.models import EvidenceItem, SearchResult, TargetedSearch
from app.providers.search import SearchProvider
from app.services.trace import ResearchTraceEmitter
from app.utils.cache import TTLCache
from app.utils.text import extract_readable_text, select_relevant_text
from app.utils.url_safety import canonical_url, is_trusted_https_url

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _page_cache(ttl_seconds: int) -> TTLCache[str]:
    return TTLCache(ttl_seconds)


class RetrievalService:
    def __init__(
        self,
        search: SearchProvider,
        *,
        fetch_per_source: int = 1,
        max_workers: int = 4,
        fetch_timeout: float = 8,
        max_bytes: int = 1_000_000,
        redirect_limit: int = 3,
        per_source_chars: int = 3500,
        total_chars: int = 12000,
        cache_ttl: int = 900,
        user_agent: str = "MediVita/1.0",
        client_factory=httpx.Client,
        trace: ResearchTraceEmitter | None = None,
    ):
        self.search = search
        self.fetch_per_source = max(1, min(fetch_per_source, 3))
        self.max_workers = max(1, min(max_workers, 8))
        self.fetch_timeout = fetch_timeout
        self.max_bytes = max_bytes
        self.redirect_limit = redirect_limit
        self.per_source_chars = per_source_chars
        self.total_chars = total_chars
        self.page_cache = _page_cache(cache_ttl)
        self.user_agent = user_agent
        self.client_factory = client_factory
        self.trace = trace

    def retrieve(self, query: str, source_ids: list[str]) -> list[EvidenceItem]:
        return self._to_evidence(
            self.search.search(query, source_ids), round_number=1
        )

    def retrieve_targeted(self, searches: list[TargetedSearch]) -> list[EvidenceItem]:
        return self._to_evidence(
            self.search.search_targeted(searches), round_number=2
        )

    def _to_evidence(
        self, results: list[SearchResult], *, round_number: int
    ) -> list[EvidenceItem]:
        started = monotonic()
        chosen: list[SearchResult] = []
        counts: dict[str, int] = {}
        for result in results:
            count = counts.get(result.source_id, 0)
            if count < self.fetch_per_source:
                chosen.append(result)
                counts[result.source_id] = count + 1
        if not chosen:
            self._emit_evidence_count(0, round_number)
            return []
        pages: dict[int, str] = {}
        page_trace_ids: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(chosen))) as pool:
            if self.trace:
                for index, result in enumerate(chosen):
                    page_trace_ids[index] = self.trace.emit(
                        stage="page_retrieval",
                        status="running",
                        label=f"Retrieving {result.source_name} evidence",
                        tool="HTTP Page Retriever",
                        source_id=result.source_id,
                        source_name=result.source_name,
                        round=round_number,
                    )
            futures = {pool.submit(self._fetch_page, result): index for index, result in enumerate(chosen)}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    pages[index] = future.result()
                except Exception as error:
                    LOGGER.warning(
                        "Trusted page fetch failed (source_id=%s, type=%s)",
                        chosen[index].source_id,
                        type(error).__name__,
                    )
                    pages[index] = ""
        evidence: list[EvidenceItem] = []
        remaining = self.total_chars
        for index, result in enumerate(chosen):
            page_text = pages.get(index, "")
            limit = min(self.per_source_chars, remaining)
            content = select_relevant_text(page_text, result.query, result.title, limit)
            result_type = "page" if content else "snippet"
            content = content or result.snippet[:limit]
            if not content:
                self._emit_page_result(
                    page_trace_ids.get(index), result, "unavailable", round_number
                )
                continue
            self._emit_page_result(
                page_trace_ids.get(index), result, result_type, round_number
            )
            remaining -= len(content)
            evidence.append(
                EvidenceItem(
                    id=f"E{len(evidence) + 1}",
                    source_id=result.source_id,
                    source_name=result.source_name,
                    domain=result.domain,
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    content=content,
                    query=result.query,
                    result_type=result_type,
                )
            )
            if remaining <= 0:
                break
        LOGGER.info(
            "Page evidence complete (candidates=%s, evidence=%s, elapsed_ms=%s)",
            len(chosen),
            len(evidence),
            round((monotonic() - started) * 1000),
        )
        self._emit_evidence_count(len(evidence), round_number)
        return evidence

    def _emit_page_result(
        self,
        event_id: str | None,
        result: SearchResult,
        retrieval_type: str,
        round_number: int,
    ) -> None:
        if not self.trace or not event_id:
            return
        snippet = retrieval_type == "snippet"
        self.trace.emit(
            event_id=event_id,
            stage="page_retrieval",
            status="warning" if snippet or retrieval_type == "unavailable" else "completed",
            label=(
                f"{result.source_name} search snippet retained"
                if snippet
                else f"{result.source_name} evidence retrieved"
                if retrieval_type == "page"
                else f"{result.source_name} evidence unavailable"
            ),
            tool="HTTP Page Retriever",
            source_id=result.source_id,
            source_name=result.source_name,
            page_count=1 if retrieval_type == "page" else 0,
            retrieval_type=retrieval_type,
            round=round_number,
            message="Page access limited; trusted search snippet retained" if snippet else None,
        )

    def _emit_evidence_count(self, count: int, round_number: int) -> None:
        if self.trace:
            self.trace.emit(
                stage="evidence",
                status="completed" if count else "warning",
                label="Relevant evidence selected" if count else "No usable evidence selected",
                tool="MediVita Evidence Ranker",
                evidence_count=count,
                round=round_number,
            )

    def _fetch_page(self, result: SearchResult) -> str:
        cache_key = canonical_url(result.url)
        cached = self.page_cache.get(cache_key)
        if cached is not None:
            return cached
        current_url = result.url
        with self.client_factory(
            timeout=self.fetch_timeout,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=False,
        ) as client:
            for redirect_count in range(self.redirect_limit + 1):
                if not is_trusted_https_url(current_url, result.domain):
                    return ""
                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count >= self.redirect_limit:
                            return ""
                        location = response.headers.get("location", "")
                        next_url = urljoin(current_url, location)
                        if not is_trusted_https_url(next_url, result.domain):
                            return ""
                        current_url = next_url
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type:
                        return ""
                    declared_size = int(response.headers.get("content-length", "0") or 0)
                    if declared_size > self.max_bytes:
                        return ""
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_bytes:
                            return ""
                    html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                    text = extract_readable_text(html)
                    self.page_cache.set(cache_key, text)
                    return text
        return ""


def merge_evidence(existing: list[EvidenceItem], additions: list[EvidenceItem], total_chars: int) -> list[EvidenceItem]:
    merged: list[EvidenceItem] = []
    seen: set[str] = set()
    used_chars = 0
    for item in [*existing, *additions]:
        key = canonical_url(item.url)
        if key in seen or used_chars >= total_chars:
            continue
        content = item.content[: total_chars - used_chars]
        if not content:
            continue
        seen.add(key)
        used_chars += len(content)
        merged.append(
            EvidenceItem(
                id=f"E{len(merged) + 1}",
                source_id=item.source_id,
                source_name=item.source_name,
                domain=item.domain,
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                content=content,
                query=item.query,
                result_type=item.result_type,
            )
        )
    return merged
