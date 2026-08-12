"""News filtering and normalization service."""

from flask import current_app

from app.providers.news import build_news_provider

CATEGORIES = {"all", "research", "nutrition", "mental-health", "public-health", "medicine"}


class NewsService:
    def __init__(self):
        self.provider = build_news_provider(current_app.config["NEWS_PROVIDER"], current_app.config)

    def list_articles(self, category: str, limit: int) -> list[dict[str, str]]:
        if category not in CATEGORIES:
            raise ValueError("Unsupported news category.")
        return self.provider.articles(category, limit)
