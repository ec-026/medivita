"""API validation helpers."""

from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    pass


def require_json_object(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    return payload


def require_text(payload: dict, field: str, *, minimum: int = 2, maximum: int = 4000) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be a string.")
    value = value.strip()
    if len(value) < minimum:
        raise ValidationError(f"'{field}' must contain at least {minimum} characters.")
    if len(value) > maximum:
        raise ValidationError(f"'{field}' must contain no more than {maximum} characters.")
    return value


def require_source_list(payload: dict) -> list[str]:
    value = payload.get("enabled_sources")
    if not isinstance(value, list) or not value:
        raise ValidationError("'enabled_sources' must contain at least one source.")
    if not all(isinstance(item, str) for item in value):
        raise ValidationError("'enabled_sources' must contain source identifiers.")
    return value


def clean_history(payload: dict) -> list[dict[str, str]]:
    history = payload.get("history", [])
    if not isinstance(history, list):
        raise ValidationError("'history' must be an array.")
    clean = []
    for item in history[-8:]:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            clean.append({"role": role, "content": content.strip()[:2000]})
    return clean
