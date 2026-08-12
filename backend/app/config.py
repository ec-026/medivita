"""Environment-driven application configuration."""

from __future__ import annotations

import os


def _csv_setting(name: str, default: str) -> tuple[str, ...]:
    values = [item.strip().lower() for item in os.getenv(name, default).split(",")]
    return tuple(dict.fromkeys(item for item in values if item))


class Config:
    MAX_CONTENT_LENGTH = 64 * 1024
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "demo").lower()
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "demo").lower()
    NEWS_PROVIDER = os.getenv("NEWS_PROVIDER", "demo").lower()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low")
    GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", "35"))
    GROQ_MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "1"))
    GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1800"))
    # Optional secondary provider; never selected automatically.
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
    OPENROUTER_REASONING_EFFORT = os.getenv("OPENROUTER_REASONING_EFFORT", "low")
    OPENROUTER_PROVIDER_SORT = os.getenv("OPENROUTER_PROVIDER_SORT", "latency")
    OPENROUTER_DATA_COLLECTION = os.getenv("OPENROUTER_DATA_COLLECTION", "").lower()
    OPENROUTER_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT", "35"))
    OPENROUTER_MAX_RETRIES = int(os.getenv("OPENROUTER_MAX_RETRIES", "1"))
    OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "1800"))
    SEARCH_RESULTS_PER_SOURCE = int(os.getenv("SEARCH_RESULTS_PER_SOURCE", "2"))
    SEARCH_FETCH_PER_SOURCE = int(os.getenv("SEARCH_FETCH_PER_SOURCE", "1"))
    SEARCH_MAX_WORKERS = int(os.getenv("SEARCH_MAX_WORKERS", "4"))
    SEARCH_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT", "8"))
    DDGS_TEXT_BACKENDS = _csv_setting("DDGS_TEXT_BACKENDS", "brave,bing,duckduckgo")
    DDGS_NEWS_BACKENDS = _csv_setting("DDGS_NEWS_BACKENDS", "bing,yahoo,duckduckgo")
    PAGE_FETCH_TIMEOUT = float(os.getenv("PAGE_FETCH_TIMEOUT", "8"))
    PAGE_MAX_BYTES = int(os.getenv("PAGE_MAX_BYTES", str(1_000_000)))
    PAGE_REDIRECT_LIMIT = int(os.getenv("PAGE_REDIRECT_LIMIT", "3"))
    EVIDENCE_CHARS_PER_SOURCE = int(os.getenv("EVIDENCE_CHARS_PER_SOURCE", "3500"))
    EVIDENCE_TOTAL_CHARS = int(os.getenv("EVIDENCE_TOTAL_CHARS", "12000"))
    RETRIEVAL_CACHE_TTL_SECONDS = int(
        os.getenv("RETRIEVAL_CACHE_TTL_SECONDS", os.getenv("CACHE_TTL_SECONDS", "900"))
    )
    NEWS_RESULTS_LIMIT = int(os.getenv("NEWS_RESULTS_LIMIT", "30"))
    EXTERNAL_USER_AGENT = os.getenv(
        "EXTERNAL_USER_AGENT", "MediVita/1.0 (+https://github.com/medivita)"
    )


class TestConfig(Config):
    TESTING = True
    LLM_PROVIDER = "demo"
    SEARCH_PROVIDER = "demo"
    NEWS_PROVIDER = "demo"
