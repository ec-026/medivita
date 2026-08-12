"""Manually test configured DDGS text backends without invoking an LLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
load_dotenv(REPOSITORY_ROOT / ".env", override=False)
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Config  # noqa: E402
from app.sources import get_source, list_sources  # noqa: E402
from app.utils.url_safety import is_trusted_https_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-id",
        default="mayo-clinic",
        choices=[source.metadata.id for source in list_sources()],
    )
    parser.add_argument(
        "--query",
        default="general health information",
        help="Use synthetic, non-identifying text only.",
    )
    args = parser.parse_args()
    source = get_source(args.source_id)
    if source is None:
        return 2
    domain = source.metadata.domain
    discovery_query = f"site:{domain} {args.query}"
    outcomes = []
    for backend in Config.DDGS_TEXT_BACKENDS:
        try:
            raw_results = DDGS(timeout=Config.SEARCH_TIMEOUT).text(
                discovery_query,
                safesearch="moderate",
                max_results=Config.SEARCH_RESULTS_PER_SOURCE,
                backend=backend,
            )
            valid_count = sum(
                1
                for item in raw_results
                if isinstance(item, dict)
                and is_trusted_https_url(str(item.get("href") or item.get("url") or ""), domain)
            )
            outcomes.append(
                {
                    "backend": backend,
                    "status": "ok" if valid_count else "empty",
                    "raw_results": len(raw_results),
                    "valid_trusted_results": valid_count,
                }
            )
        except DDGSException as error:
            outcomes.append(
                {
                    "backend": backend,
                    "status": "failed",
                    "error_type": type(error).__name__,
                }
            )
        except Exception as error:
            outcomes.append(
                {
                    "backend": backend,
                    "status": "failed",
                    "error_type": type(error).__name__,
                }
            )
    print(json.dumps({"source_id": args.source_id, "domain": domain, "backends": outcomes}, indent=2))
    return 0 if any(item.get("valid_trusted_results", 0) for item in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
