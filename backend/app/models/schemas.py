"""Domain and structured-output schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class MedicalSource:
    id: str
    name: str
    domain: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SourceReference:
    name: str
    domain: str
    title: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    source_name: str
    domain: str
    title: str
    url: str
    snippet: str
    query: str
    result_type: str = "web"
    backend: str = ""


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    source_id: str
    source_name: str
    domain: str
    title: str
    url: str
    snippet: str
    content: str
    query: str
    result_type: str


class TargetedSearch(BaseModel):
    source_id: str = Field(description="One enabled source ID")
    query: str = Field(min_length=3, max_length=300)
    reason: str = Field(default="", max_length=300)


class FinalChatAnswer(BaseModel):
    overview: str = Field(min_length=1)
    possible_considerations: str = Field(min_length=1)
    what_may_help: str = Field(min_length=1)
    when_to_seek_medical_care: str = Field(min_length=1)
    used_evidence_ids: list[str] = Field(
        description="Evidence IDs materially used to support the final answer."
    )


class ChatResearchDecision(BaseModel):
    decision: Literal["answer", "search_more"]
    answer: FinalChatAnswer | None = None
    missing_information: list[str] = Field(default_factory=list, max_length=4)
    follow_up_searches: list[TargetedSearch] = Field(default_factory=list, max_length=4)


class FinalHealthCheckAnswer(BaseModel):
    summary: str = Field(min_length=1)
    reported_symptoms: list[str] = Field(default_factory=list)
    general_considerations: list[str] = Field(default_factory=list)
    self_care: list[str] = Field(default_factory=list)
    seek_medical_attention: list[str] = Field(default_factory=list)
    used_evidence_ids: list[str] = Field(
        description="Evidence IDs materially used to support the final summary."
    )


class HealthResearchDecision(BaseModel):
    decision: Literal["answer", "search_more"]
    answer: FinalHealthCheckAnswer | None = None
    missing_information: list[str] = Field(default_factory=list, max_length=4)
    follow_up_searches: list[TargetedSearch] = Field(default_factory=list, max_length=4)
