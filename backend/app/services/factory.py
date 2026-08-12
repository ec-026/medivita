"""Composition root for the connected research workflow."""

from app.providers.llm import build_llm_provider
from app.providers.search import build_search_provider
from app.services.research import BoundedResearchController
from app.services.retrieval import RetrievalService
from app.services.trace import ResearchTraceEmitter


def build_research_controller(
    config: dict, trace: ResearchTraceEmitter | None = None
) -> BoundedResearchController:
    search = build_search_provider(config["SEARCH_PROVIDER"], config, trace)
    retrieval = RetrievalService(
        search,
        fetch_per_source=config["SEARCH_FETCH_PER_SOURCE"],
        max_workers=config["SEARCH_MAX_WORKERS"],
        fetch_timeout=config["PAGE_FETCH_TIMEOUT"],
        max_bytes=config["PAGE_MAX_BYTES"],
        redirect_limit=config["PAGE_REDIRECT_LIMIT"],
        per_source_chars=config["EVIDENCE_CHARS_PER_SOURCE"],
        total_chars=config["EVIDENCE_TOTAL_CHARS"],
        cache_ttl=config["RETRIEVAL_CACHE_TTL_SECONDS"],
        user_agent=config["EXTERNAL_USER_AGENT"],
        trace=trace,
    )
    llm = build_llm_provider(config["LLM_PROVIDER"], config)
    return BoundedResearchController(
        retrieval,
        llm,
        total_chars=config["EVIDENCE_TOTAL_CHARS"],
        trace=trace,
    )
