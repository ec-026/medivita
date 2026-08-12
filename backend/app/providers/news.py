"""Normalized health-news providers, including live DDGS news search."""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlparse

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from app.utils.cache import TTLCache
from app.utils.errors import ServiceError
from app.utils.text import normalize_text
from app.utils.url_safety import canonical_url, is_allowed_https_url

LOGGER = logging.getLogger(__name__)
CATEGORY_QUERIES = {
    "research": "medical health research study",
    "nutrition": "nutrition health research guidance",
    "mental-health": "mental health research guidance",
    "public-health": "public health guidance outbreak prevention",
    "medicine": "medicine treatment clinical research",
}
PUBLISHER_DOMAINS = {
    "apnews.com",
    "bmj.com",
    "cdc.gov",
    "clevelandclinic.org",
    "healthline.com",
    "mayoclinic.org",
    "medicalnewstoday.com",
    "nature.com",
    "nejm.org",
    "nhs.uk",
    "nih.gov",
    "reuters.com",
    "science.org",
    "statnews.com",
    "webmd.com",
    "who.int",
}


@lru_cache(maxsize=8)
def _news_cache(ttl_seconds: int) -> TTLCache[list[dict[str, str]]]:
    return TTLCache(ttl_seconds)


class NewsProvider(ABC):
    @abstractmethod
    def articles(self, category: str, limit: int) -> list[dict[str, str]]:
        raise NotImplementedError


class DemoNewsProvider(NewsProvider):
    def articles(self, category: str, limit: int) -> list[dict[str, str]]:
        now = datetime.now(UTC).replace(microsecond=0)
        items = [
            ("research", "How everyday movement supports long-term brain health", "A look at how researchers study the relationship between regular activity and healthy aging.", "MediVita Research Desk", 2),
            ("nutrition", "Reading nutrition labels with more confidence", "Practical context for comparing serving sizes, fiber, added sugar and sodium.", "MediVita Nutrition Brief", 7),
            ("mental-health", "Why consistent sleep routines matter for emotional wellbeing", "Researchers continue to explore the two-way relationship between sleep quality and mood.", "MediVita Health Brief", 12),
            ("public-health", "Preparing for seasonal respiratory illness", "Simple prevention habits can help communities reduce the spread of common respiratory infections.", "MediVita Public Health", 26),
            ("medicine", "Understanding how medicines move from trials to patients", "An accessible overview of clinical trial phases, review and ongoing safety monitoring.", "MediVita Medicine Desk", 38),
            ("research", "What scientists are learning about the gut microbiome", "Current research is mapping associations while many clinical questions remain open.", "MediVita Research Desk", 50),
            ("nutrition", "Hydration needs can change with activity and climate", "Fluid needs vary with exertion, environment, health conditions and individual factors.", "MediVita Nutrition Brief", 74),
            ("mental-health", "Small social connections can support wellbeing", "Everyday contact and supportive relationships are an important part of whole-person health.", "MediVita Health Brief", 96),
        ]
        articles = [
            {
                "id": f"demo-{index + 1}",
                "title": title,
                "summary": summary,
                "category": item_category,
                "publisher": publisher,
                "published_at": (now - timedelta(hours=hours)).isoformat(),
                "url": "https://www.who.int/news-room",
            }
            for index, (item_category, title, summary, publisher, hours) in enumerate(items)
            if category == "all" or category == item_category
        ]
        return articles[:limit]


class DuckDuckGoNewsProvider(NewsProvider):
    def __init__(
        self,
        *,
        results_limit: int = 30,
        timeout: float = 8,
        cache_ttl: int = 900,
        backends: tuple[str, ...] = ("bing", "yahoo", "duckduckgo"),
        ddgs_factory=DDGS,
    ):
        self.results_limit = max(1, min(results_limit, 50))
        self.timeout = timeout
        self.cache = _news_cache(cache_ttl)
        self.backends = tuple(dict.fromkeys(backend.strip().lower() for backend in backends if backend.strip()))
        if not self.backends:
            self.backends = ("bing", "yahoo", "duckduckgo")
        self.ddgs_factory = ddgs_factory

    def articles(self, category: str, limit: int) -> list[dict[str, str]]:
        categories = list(CATEGORY_QUERIES) if category == "all" else [category]
        results: dict[int, list[dict[str, str]]] = {}
        with ThreadPoolExecutor(max_workers=min(4, len(categories))) as pool:
            futures = {
                pool.submit(self._category_articles, item_category): index
                for index, item_category in enumerate(categories)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    results[index] = future.result()
                except Exception as error:
                    LOGGER.warning("News search failed (type=%s)", type(error).__name__)
                    results[index] = []
        deduplicated: list[dict[str, str]] = []
        seen: set[str] = set()
        for index in range(len(categories)):
            for article in results.get(index, []):
                key = canonical_url(article["url"])
                if key in seen:
                    continue
                seen.add(key)
                deduplicated.append(article)
        deduplicated.sort(key=lambda item: item["published_at"], reverse=True)
        if not deduplicated:
            raise ServiceError(
                "NEWS_UNAVAILABLE",
                "Live health news is temporarily unavailable. Please try again later.",
                503,
            )
        return deduplicated[:limit]

    def _category_articles(self, category: str) -> list[dict[str, str]]:
        cache_key = f"news|{category}|{self.results_limit}|{','.join(self.backends)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return list(cached)
        articles: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for backend in self.backends:
            try:
                raw_results = self.ddgs_factory(timeout=self.timeout).news(
                    CATEGORY_QUERIES[category],
                    safesearch="moderate",
                    timelimit="m",
                    max_results=self.results_limit,
                    backend=backend,
                )
            except DDGSException as error:
                _log_news_backend_failure(category, backend, error)
                continue
            except Exception as error:  # Keep one backend implementation from blocking fallback.
                _log_news_backend_failure(category, backend, error)
                continue
            valid_count_before = len(articles)
            if isinstance(raw_results, list):
                for item in raw_results:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("url") or item.get("href") or "")
                    if not is_allowed_https_url(url, PUBLISHER_DOMAINS):
                        continue
                    url_key = canonical_url(url)
                    if url_key in seen_urls:
                        continue
                    domain = (urlparse(url).hostname or "").removeprefix("www.")
                    title = normalize_text(str(item.get("title") or ""))
                    summary = normalize_text(str(item.get("body") or item.get("snippet") or ""))
                    if not title or not summary:
                        continue
                    seen_urls.add(url_key)
                    articles.append(
                        {
                            "id": hashlib.sha256(url_key.encode()).hexdigest()[:16],
                            "title": title,
                            "summary": summary,
                            "category": category,
                            "publisher": normalize_text(str(item.get("source") or domain)),
                            "published_at": str(item.get("date") or ""),
                            "url": url,
                        }
                    )
                    if len(articles) >= self.results_limit:
                        break
            if len(articles) >= self.results_limit:
                break
            if len(articles) == valid_count_before:
                LOGGER.info(
                    "News backend returned no valid results (category=%s, backend=%s)",
                    category,
                    backend,
                )
        if articles:
            self.cache.set(cache_key, articles)
        return articles


def build_news_provider(name: str, config: dict | None = None) -> NewsProvider:
    if name == "demo":
        return DemoNewsProvider()
    if name == "duckduckgo":
        values = config or {}
        return DuckDuckGoNewsProvider(
            results_limit=values.get("NEWS_RESULTS_LIMIT", 30),
            timeout=values.get("SEARCH_TIMEOUT", 8),
            cache_ttl=values.get("RETRIEVAL_CACHE_TTL_SECONDS", 900),
            backends=values.get("DDGS_NEWS_BACKENDS", ("bing", "yahoo", "duckduckgo")),
        )
    raise ValueError(f"Unsupported news provider: {name}")


def _log_news_backend_failure(category: str, backend: str, error: Exception) -> None:
    LOGGER.warning(
        "News backend failed (category=%s, backend=%s, type=%s)",
        category,
        backend,
        type(error).__name__,
    )
