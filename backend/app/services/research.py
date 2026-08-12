"""Strictly bounded retrieval/LLM controller shared by chat and health check."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import monotonic
from typing import Literal
from uuid import uuid4

from app.models import EvidenceItem, FinalChatAnswer, SourceReference, TargetedSearch
from app.services.retrieval import RetrievalService, merge_evidence
from app.services.trace import ResearchTraceEmitter
from app.utils.errors import ServiceError
from app.utils.url_safety import canonical_url, is_trusted_https_url

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitationResolution:
    references: list[SourceReference]
    valid_model_evidence_ids: int
    fallback_used: bool


@dataclass(frozen=True)
class ChatControllerAnswer:
    response_kind: Literal["direct", "researched", "clarification"]
    answer: str
    grounded_answer: FinalChatAnswer | None = None


class BoundedResearchController:
    def __init__(
        self,
        retrieval: RetrievalService,
        llm,
        *,
        total_chars: int = 12000,
        trace: ResearchTraceEmitter | None = None,
    ):
        self.retrieval = retrieval
        self.llm = llm
        self.total_chars = total_chars
        self.trace = trace

    def chat(
        self,
        question: str,
        source_ids: list[str],
        history: list[dict[str, str]],
    ) -> tuple[ChatControllerAnswer, list[SourceReference], int]:
        started = monotonic()
        request_id = uuid4().hex[:12]
        planning_started = monotonic()
        planning_id = self._planning_started()
        plan = self.llm.chat_plan(question, history, source_ids)
        planning_ms = (monotonic() - planning_started) * 1000
        calls = 1

        if plan.action == "direct":
            response = (plan.direct_response or "").strip()
            if not response:
                raise ServiceError(
                    "AI_INVALID_RESPONSE",
                    "The AI provider did not return a usable direct response.",
                    502,
                )
            self._planning_completed(planning_id, "No research needed", planning_ms)
            self._finish_non_research_trace()
            self._log_chat_completion(
                request_id=request_id,
                response_kind="direct",
                model_calls=calls,
                planning_ms=planning_ms,
                total_ms=(monotonic() - started) * 1000,
            )
            return ChatControllerAnswer("direct", response), [], calls

        if plan.action == "clarify":
            clarification = (plan.clarification_question or "").strip()
            if not clarification:
                raise ServiceError(
                    "AI_INVALID_RESPONSE",
                    "The AI provider did not return a usable clarification question.",
                    502,
                )
            self._planning_completed(planning_id, "Clarification needed", planning_ms)
            self._finish_non_research_trace()
            self._log_chat_completion(
                request_id=request_id,
                response_kind="clarification",
                model_calls=calls,
                planning_ms=planning_ms,
                total_ms=(monotonic() - started) * 1000,
            )
            return ChatControllerAnswer("clarification", clarification), [], calls

        searches = _allowed_searches(plan.searches, source_ids)
        if not searches:
            raise ServiceError(
                "AI_INVALID_RESPONSE",
                "The AI provider did not return a usable trusted-source research plan.",
                502,
            )
        self._planning_completed(
            planning_id,
            "Trusted-source research planned",
            planning_ms,
            message=f"{len(searches)} targeted search{'es' if len(searches) != 1 else ''} selected",
        )
        retrieval_started = monotonic()
        evidence = self.retrieval.retrieve_targeted(searches, round_number=1)
        retrieval_ms = (monotonic() - retrieval_started) * 1000
        if not evidence:
            raise ServiceError(
                "RETRIEVAL_UNAVAILABLE",
                "No usable trusted-source evidence could be retrieved. Please try again.",
                503,
            )
        llm_started = monotonic()
        generation_id = self._generation_started(1, "Generate grounded answer")
        answer = self.llm.chat_answer(question, history, evidence, source_ids)
        generation_ms = (monotonic() - llm_started) * 1000
        self._generation_completed(generation_id, 1, generation_ms)
        calls = 2
        citations = _resolve_references(answer.used_evidence_ids, evidence, source_ids)
        references = citations.references
        if not references:
            raise ServiceError(
                "RETRIEVAL_UNAVAILABLE",
                "No usable trusted-source evidence could be cited. Please try again.",
                503,
            )
        self._citation_event(len(references), citations.fallback_used, 1)
        if self.trace:
            self.trace.finish(
                rounds=1,
                evidence_count=len(evidence),
                citation_count=len(references),
            )
        self._log_chat_completion(
            request_id=request_id,
            response_kind="researched",
            model_calls=calls,
            planning_ms=planning_ms,
            total_ms=(monotonic() - started) * 1000,
            evidence_count=len(evidence),
            citation_count=len(references),
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            model_evidence_ids=len(answer.used_evidence_ids),
            valid_model_evidence_ids=citations.valid_model_evidence_ids,
            citation_fallback=citations.fallback_used,
        )
        return ChatControllerAnswer("researched", answer.overview, answer), references, calls

    def health(self, description: str, source_ids: list[str]) -> tuple[object, list[SourceReference], int]:
        started = monotonic()
        request_id = uuid4().hex[:12]
        retrieval_started = monotonic()
        evidence = self.retrieval.retrieve(description, source_ids)
        retrieval_ms = (monotonic() - retrieval_started) * 1000
        if not evidence:
            raise ServiceError(
                "RETRIEVAL_UNAVAILABLE",
                "No usable trusted-source evidence could be retrieved. Please try again.",
                503,
            )
        llm_started = monotonic()
        generation_id = self._generation_started(1, "Generate grounded health summary")
        first = self.llm.health_decision(description, evidence, source_ids, False)
        llm_ms = (monotonic() - llm_started) * 1000
        self._generation_completed(generation_id, 1, llm_ms)
        calls = 1
        if first.decision == "answer" and first.answer is not None:
            self._decision_event(1, additional_research=False)
            answer = first.answer
        else:
            self._decision_event(1, additional_research=True)
            searches = _allowed_searches(first.follow_up_searches, source_ids)
            retrieval_started = monotonic()
            additions = (
                self.retrieval.retrieve_targeted(searches, round_number=2)
                if searches
                else []
            )
            retrieval_ms += (monotonic() - retrieval_started) * 1000
            evidence = merge_evidence(evidence, additions, self.total_chars)
            llm_started = monotonic()
            generation_id = self._generation_started(2, "Generate final health summary")
            second = self.llm.health_decision(description, evidence, source_ids, True)
            second_llm_ms = (monotonic() - llm_started) * 1000
            llm_ms += second_llm_ms
            self._generation_completed(generation_id, 2, second_llm_ms)
            calls = 2
            if second.decision != "answer" or second.answer is None:
                raise ServiceError(
                    "AI_INVALID_RESPONSE",
                    "The AI provider did not return a usable grounded summary.",
                    502,
                )
            answer = second.answer
            self._decision_event(2, additional_research=False)
        citations = _resolve_references(answer.used_evidence_ids, evidence, source_ids)
        references = citations.references
        if not references:
            raise ServiceError(
                "RETRIEVAL_UNAVAILABLE",
                "No usable trusted-source evidence could be cited. Please try again.",
                503,
            )
        self._citation_event(len(references), citations.fallback_used, calls)
        if self.trace:
            self.trace.finish(
                rounds=calls,
                evidence_count=len(evidence),
                citation_count=len(references),
            )
        LOGGER.info(
            "Research complete (request_id=%s, kind=health, rounds=%s, evidence=%s, model_evidence_ids=%s, valid_model_evidence_ids=%s, sources=%s, citation_fallback=%s, retrieval_ms=%s, llm_ms=%s, total_ms=%s)",
            request_id,
            calls,
            len(evidence),
            len(answer.used_evidence_ids),
            citations.valid_model_evidence_ids,
            len(references),
            str(citations.fallback_used).lower(),
            round(retrieval_ms),
            round(llm_ms),
            round((monotonic() - started) * 1000),
        )
        return answer, references, calls

    def _planning_started(self) -> str | None:
        if not self.trace:
            return None
        return self.trace.emit(
            stage="planning",
            status="running",
            label="Understanding your question",
            tool="LangChain structured planning",
            provider=getattr(self.llm, "provider_name", None),
            model=getattr(self.llm, "model_name", None),
        )

    def _planning_completed(
        self,
        event_id: str | None,
        label: str,
        elapsed_ms: float,
        *,
        message: str | None = None,
    ) -> None:
        if self.trace and event_id:
            self.trace.emit(
                event_id=event_id,
                stage="planning",
                status="completed",
                label=label,
                tool="LangChain structured planning",
                provider=getattr(self.llm, "provider_name", None),
                model=getattr(self.llm, "model_name", None),
                elapsed_ms=round(elapsed_ms),
                message=message,
            )

    def _finish_non_research_trace(self) -> None:
        if self.trace:
            self.trace.finish(
                rounds=0,
                evidence_count=0,
                citation_count=0,
                label="Response ready",
            )

    @staticmethod
    def _log_chat_completion(
        *,
        request_id: str,
        response_kind: str,
        model_calls: int,
        planning_ms: float,
        total_ms: float,
        evidence_count: int = 0,
        citation_count: int = 0,
        retrieval_ms: float = 0,
        generation_ms: float = 0,
        model_evidence_ids: int = 0,
        valid_model_evidence_ids: int = 0,
        citation_fallback: bool = False,
    ) -> None:
        LOGGER.info(
            "Chat complete (request_id=%s, response_kind=%s, model_calls=%s, research_passes=%s, evidence=%s, model_evidence_ids=%s, valid_model_evidence_ids=%s, sources=%s, citation_fallback=%s, planning_ms=%s, retrieval_ms=%s, generation_ms=%s, total_ms=%s)",
            request_id,
            response_kind,
            model_calls,
            1 if response_kind == "researched" else 0,
            evidence_count,
            model_evidence_ids,
            valid_model_evidence_ids,
            citation_count,
            str(citation_fallback).lower(),
            round(planning_ms),
            round(retrieval_ms),
            round(generation_ms),
            round(total_ms),
        )

    def _generation_started(self, round_number: int, label: str) -> str | None:
        if not self.trace:
            return None
        return self.trace.emit(
            stage="generation",
            status="running",
            label=label,
            tool="LangChain structured generation",
            provider=getattr(self.llm, "provider_name", None),
            model=getattr(self.llm, "model_name", None),
            round=round_number,
        )

    def _generation_completed(
        self, event_id: str | None, round_number: int, elapsed_ms: float
    ) -> None:
        if self.trace and event_id:
            self.trace.emit(
                event_id=event_id,
                stage="generation",
                status="completed",
                label="Grounded generation complete",
                tool="LangChain structured generation",
                provider=getattr(self.llm, "provider_name", None),
                model=getattr(self.llm, "model_name", None),
                round=round_number,
                elapsed_ms=round(elapsed_ms),
            )

    def _decision_event(self, round_number: int, *, additional_research: bool) -> None:
        if self.trace:
            self.trace.emit(
                stage="research_decision",
                status="completed",
                label=(
                    "Additional research requested"
                    if additional_research
                    else "Evidence sufficiency check complete"
                ),
                tool="Bounded research controller",
                round=round_number,
                message=(
                    "A second and final research round will run"
                    if additional_research
                    else "Evidence was sufficient for the final response"
                ),
            )

    def _citation_event(self, count: int, fallback_used: bool, round_number: int) -> None:
        if self.trace:
            self.trace.emit(
                stage="citation",
                status="completed",
                label="Trusted citations prepared",
                tool="MediVita Citation Mapper",
                citation_count=count,
                round=round_number,
                message="Validated citation fallback used" if fallback_used else None,
            )


def _allowed_searches(searches: list[TargetedSearch], source_ids: list[str]) -> list[TargetedSearch]:
    allowed = set(source_ids)
    filtered: list[TargetedSearch] = []
    seen: set[tuple[str, str]] = set()
    for search in searches[:4]:
        key = (search.source_id, search.query.strip().lower())
        if search.source_id not in allowed or key in seen:
            continue
        seen.add(key)
        filtered.append(search)
    return filtered


def _resolve_references(
    evidence_ids: list[str],
    evidence: list[EvidenceItem],
    enabled_source_ids: list[str],
) -> CitationResolution:
    allowed_sources = set(enabled_source_ids)
    by_id = {item.id: item for item in evidence}
    model_items: list[EvidenceItem] = []
    valid_model_ids = 0
    for evidence_id in evidence_ids:
        item = by_id.get(evidence_id)
        if item is None or not _is_citable(item, allowed_sources):
            continue
        valid_model_ids += 1
        model_items.append(item)

    fallback_used = not model_items
    selected_items = model_items if model_items else evidence
    seen_urls: set[str] = set()
    references: list[SourceReference] = []
    for item in selected_items:
        if not _is_citable(item, allowed_sources):
            continue
        url_key = canonical_url(item.url)
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        references.append(
            SourceReference(
                name=item.source_name,
                domain=item.domain,
                title=item.title,
                url=item.url,
            )
        )
        if fallback_used and len(references) == 3:
            break
    return CitationResolution(references, valid_model_ids, fallback_used)


def _is_citable(item: EvidenceItem, allowed_sources: set[str]) -> bool:
    return item.source_id in allowed_sources and is_trusted_https_url(item.url, item.domain)
