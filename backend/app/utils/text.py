"""Lightweight HTML extraction and lexical evidence ranking."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

WORD_RE = re.compile(r"[a-z0-9]{2,}", re.I)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_readable_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "form", "nav", "header", "footer", "aside"]):
        node.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = [normalize_text(node.get_text(" ", strip=True)) for node in root.find_all(["p", "li", "h1", "h2", "h3"])]
    useful = [paragraph for paragraph in paragraphs if len(paragraph) >= 40]
    return "\n".join(dict.fromkeys(useful))


def select_relevant_text(text: str, query: str, title: str, max_chars: int) -> str:
    if not text or max_chars <= 0:
        return ""
    terms = set(WORD_RE.findall(f"{query} {title}".lower()))
    chunks = [chunk.strip() for chunk in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text) if len(chunk.strip()) >= 40]
    ranked = sorted(
        enumerate(chunks),
        key=lambda item: (-len(terms.intersection(WORD_RE.findall(item[1].lower()))), item[0]),
    )
    chosen: list[tuple[int, str]] = []
    used = 0
    for index, chunk in ranked:
        remaining = max_chars - used
        if remaining <= 0:
            break
        chosen.append((index, chunk[:remaining]))
        used += min(len(chunk), remaining) + 1
    return "\n".join(chunk for _, chunk in sorted(chosen))[:max_chars]
