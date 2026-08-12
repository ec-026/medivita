"""Opt-in smoke check for a locally running connected-mode API.

Run only with synthetic, non-identifying text after configuring the backend yourself.
"""

from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:5000/api"


def request(path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    method = "POST" if body else "GET"
    with urlopen(
        Request(
            f"{BASE_URL}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        ),
        timeout=60,
    ) as response:
        return json.load(response)


def main() -> int:
    try:
        health = request("/health")
        if health.get("mode") != "connected":
            print("API is healthy but not in connected mode.")
            return 2
        sources = [item["id"] for item in request("/sources")["sources"][:2]]
        chat = request(
            "/chat",
            {
                "message": "What general information is available about consistent sleep routines?",
                "enabled_sources": sources,
                "history": [],
            },
        )
        summary = request(
            "/health-check",
            {
                "description": "For two days I have noticed a mild headache after short sleep.",
                "enabled_sources": sources,
            },
        )
        news = request("/news?category=research&limit=2")
        print(
            json.dumps(
                {
                    "health": health,
                    "chat_source_count": len(chat.get("sources", [])),
                    "health_check_source_count": len(summary.get("sources", [])),
                    "news_article_count": len(news.get("articles", [])),
                },
                indent=2,
            )
        )
        return 0
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Connected smoke check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
