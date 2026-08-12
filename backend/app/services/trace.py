"""Request-local operational research traces; never model reasoning or evidence content."""

from __future__ import annotations

import re
from collections.abc import Callable
from threading import Lock
from time import monotonic

TraceCallback = Callable[[dict[str, object]], None]

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_STAGES = {
    "safety",
    "planning",
    "search",
    "page_retrieval",
    "evidence",
    "research_decision",
    "generation",
    "citation",
    "complete",
}
_STATUSES = {"pending", "running", "completed", "warning", "failed"}


class ResearchTraceEmitter:
    """Collect and optionally publish a normalized, privacy-bounded activity trace."""

    def __init__(self, callback: TraceCallback | None = None):
        self.callback = callback
        self.started = monotonic()
        self.summary: dict[str, int] = {}
        self._events: dict[str, dict[str, object]] = {}
        self._counter = 0
        self._lock = Lock()

    @property
    def events(self) -> list[dict[str, object]]:
        with self._lock:
            return [dict(event) for event in self._events.values()]

    def next_id(self, stage: str) -> str:
        with self._lock:
            self._counter += 1
            return f"{stage}-{self._counter}"

    def emit(
        self,
        *,
        stage: str,
        status: str,
        label: str,
        event_id: str | None = None,
        tool: str | None = None,
        round: int | None = None,
        source_id: str | None = None,
        source_name: str | None = None,
        backend: str | None = None,
        query: str | None = None,
        result_count: int | None = None,
        page_count: int | None = None,
        evidence_count: int | None = None,
        citation_count: int | None = None,
        model: str | None = None,
        provider: str | None = None,
        retrieval_type: str | None = None,
        elapsed_ms: int | None = None,
        message: str | None = None,
    ) -> str:
        if stage not in _STAGES or status not in _STATUSES:
            raise ValueError("Unsupported research trace stage or status.")
        trace_id = event_id or self.next_id(stage)
        event: dict[str, object] = {
            "id": trace_id,
            "stage": stage,
            "status": status,
            "label": _safe_text(label, 120),
        }
        optional = {
            "tool": _safe_text(tool, 80),
            "round": round,
            "source_id": _safe_text(source_id, 60),
            "source_name": _safe_text(source_name, 100),
            "backend": _safe_text(backend, 80),
            "query": _safe_text(query, 300),
            "result_count": result_count,
            "page_count": page_count,
            "evidence_count": evidence_count,
            "citation_count": citation_count,
            "model": _safe_text(model, 100),
            "provider": _safe_text(provider, 60),
            "retrieval_type": _safe_text(retrieval_type, 40),
            "elapsed_ms": elapsed_ms,
            "message": _safe_text(message, 180),
        }
        event.update({key: value for key, value in optional.items() if value is not None})
        with self._lock:
            self._events[trace_id] = event
        if self.callback:
            self.callback(dict(event))
        return trace_id

    def finish(
        self,
        *,
        rounds: int,
        evidence_count: int,
        citation_count: int,
        label: str = "Research complete",
    ) -> None:
        total_ms = round((monotonic() - self.started) * 1000)
        self.summary = {
            "rounds": rounds,
            "evidence_count": evidence_count,
            "citation_count": citation_count,
            "total_ms": total_ms,
        }
        self.emit(
            stage="complete",
            status="completed",
            label=label,
            round=rounds,
            evidence_count=evidence_count,
            citation_count=citation_count,
            elapsed_ms=total_ms,
        )

    def finish_demo(self) -> None:
        total_ms = round((monotonic() - self.started) * 1000)
        self.summary = {
            "rounds": 0,
            "evidence_count": 0,
            "citation_count": 0,
            "total_ms": total_ms,
        }
        self.emit(
            stage="complete",
            status="completed",
            label="Demo mode",
            tool="Deterministic response",
            elapsed_ms=total_ms,
            message="No external tools called",
        )


def _safe_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return _CONTROL_CHARACTERS.sub(" ", str(value)).strip()[:limit]
