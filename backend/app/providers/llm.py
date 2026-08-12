"""Structured Groq-primary LLM providers built on LangChain."""

from __future__ import annotations

import logging
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_openrouter import ChatOpenRouter
from pydantic import BaseModel

from app.models import ChatPlan, EvidenceItem, FinalChatAnswer, HealthResearchDecision
from app.utils.errors import ServiceError

LOGGER = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

GROUNDED_SYSTEM_PROMPT = """You are MediVita, an informational health research assistant.
Use only the supplied evidence. Never diagnose, estimate a probability, calculate a health score,
or promise that an action is safe. State uncertainty and evidence limits. Do not invent facts,
source URLs, evidence IDs, or source endorsements. Every factual health claim in a final answer
must be materially supported by the supplied evidence. Do not add specific medications, doses,
devices, statistics, warning signs, or medical triggers unless the evidence supports them. For
decision=answer, used_evidence_ids must contain at least one exact supplied evidence ID that was
materially used. Never cite an ID merely because it was supplied. Encourage qualified professional
care for persistent, worsening, or concerning symptoms. For possible emergencies, advise urgent
medical help or local emergency services without naming a country-specific number. Keep self-care
conservative and conditional.

On the first round, return decision=answer with a complete answer when the evidence is sufficient.
If the evidence cannot support a useful factual answer, return decision=search_more with at most four
narrow searches, each targeting one of the enabled source IDs. On a required-final round, decision
must be answer even when evidence is limited; keep the answer within what the evidence supports and
clearly explain those limits. Never request a third round."""

CHAT_PLANNER_SYSTEM_PROMPT = """You are MediVita's bounded chat planner. Return only the
requested structured operational plan. Never reveal, summarize, or store chain-of-thought,
private reasoning, hidden analysis, or evidence content.

Safety screening has already run and always takes precedence. Use the recent conversation history
to interpret follow-ups. Choose exactly one action:
- direct: greetings, thanks, ordinary conversation, MediVita product help, clearly unrelated
  requests that need a brief boundary response, or responses that only restate already established
  context without adding factual health claims. Put the complete user-facing reply in
  direct_response. Do not make new health claims or claim that research occurred.
- clarify: a useful answer or safe targeted search depends on missing meaning, subject, or context.
  Ask one concise user-facing question in clarification_question.
- research: factual health information, health guidance, current medical claims, or a health
  follow-up that needs external evidence. Provide one to four narrow targeted searches using only
  enabled source IDs. Queries must be ordinary search terms without site: operators or raw URLs.

For direct and clarify, searches must be empty. For research, direct_response and
clarification_question must be empty. Never include explanations for why a search was selected."""

CHAT_ANSWER_SYSTEM_PROMPT = """You are MediVita, an informational health research assistant.
Use only the supplied evidence. Never diagnose, estimate a probability, calculate a health score,
or promise that an action is safe. State uncertainty and evidence limits. Do not invent facts,
source URLs, evidence IDs, or source endorsements. Every factual health claim must be materially
supported by supplied evidence. Do not add medications, doses, devices, statistics, warning signs,
or medical triggers unless the evidence supports them. used_evidence_ids must contain at least one
exact supplied evidence ID that materially supports the answer. Never cite an ID merely because it
was supplied. Encourage qualified professional care for persistent, worsening, or concerning
symptoms. For possible emergencies, advise urgent medical help or local emergency services without
naming a country-specific number. Keep self-care conservative and conditional. Return the complete
four-section answer in the requested schema. Never request more research."""


class StructuredLLMProvider:
    def __init__(
        self,
        *,
        chat_model,
        provider_name: str,
        model_name: str,
        structured_strict: bool | None = None,
    ):
        self.chat = chat_model
        self.provider_name = provider_name
        self.model_name = model_name
        self.structured_strict = structured_strict
        self.grounded_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", GROUNDED_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{request}"),
            ]
        )
        self.planner_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHAT_PLANNER_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{request}"),
            ]
        )
        self.chat_answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHAT_ANSWER_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{request}"),
            ]
        )

    def chat_plan(
        self,
        question: str,
        history: list[dict[str, str]],
        enabled_source_ids: list[str],
    ) -> ChatPlan:
        request = (
            "Task: Select a bounded action for the latest user message.\n"
            f"Latest user message: {question}\n"
            f"Enabled source IDs: {sorted(set(enabled_source_ids))}"
        )
        messages = self.planner_prompt.invoke(
            {"history": _history_messages(history), "request": request}
        ).to_messages()
        return self._invoke_structured(ChatPlan, messages)

    def chat_answer(
        self,
        question: str,
        history: list[dict[str, str]],
        evidence: list[EvidenceItem],
        enabled_source_ids: list[str],
    ) -> FinalChatAnswer:
        request = (
            f"Task: Answer the health-information question.\nQuestion: {question}\n"
            f"Enabled source IDs: {sorted(set(enabled_source_ids))}\n"
            f"Evidence:\n{_format_evidence(evidence)}"
        )
        messages = self.chat_answer_prompt.invoke(
            {"history": _history_messages(history), "request": request}
        ).to_messages()
        return self._invoke_structured(FinalChatAnswer, messages)

    def health_decision(
        self,
        description: str,
        evidence: list[EvidenceItem],
        enabled_source_ids: list[str],
        require_answer: bool,
    ) -> HealthResearchDecision:
        request = (
            "Task: Organize the user's reported details into a non-diagnostic health summary. "
            "Do not infer symptoms the user did not report.\n"
            f"User description: {description}\n"
            f"Enabled source IDs: {sorted(set(enabled_source_ids))}\n"
            f"Required final round: {require_answer}\nEvidence:\n{_format_evidence(evidence)}"
        )
        messages = self.grounded_prompt.invoke({"history": [], "request": request}).to_messages()
        return self._invoke_structured(HealthResearchDecision, messages)

    def _invoke_structured(self, schema: type[SchemaT], messages: list[BaseMessage]) -> SchemaT:
        try:
            options: dict[str, object] = {"method": "json_schema"}
            if self.structured_strict is not None:
                options["strict"] = self.structured_strict
            runnable = self.chat.with_structured_output(schema, **options)
            return runnable.invoke(messages)
        except ServiceError:
            raise
        except Exception as error:
            status = _status_code(error)
            error_type = type(error).__name__.lower()
            LOGGER.warning(
                "LLM request failed (provider=%s, status=%s, type=%s)",
                self.provider_name,
                status,
                type(error).__name__,
            )
            if status == 429:
                raise ServiceError(
                    "AI_RATE_LIMITED",
                    "The AI provider is temporarily rate limited. Please try again shortly.",
                    429,
                ) from error
            if "timeout" in error_type:
                raise ServiceError(
                    "AI_TIMEOUT",
                    "The AI provider took too long to respond. Please try again.",
                    504,
                ) from error
            raise ServiceError(
                "AI_PROVIDER_ERROR",
                "The AI provider could not complete this request.",
                503,
            ) from error


class GroqProvider(StructuredLLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str = "low",
        timeout: float = 35,
        max_retries: int = 1,
        max_tokens: int = 1800,
        chat_model=None,
    ):
        if not api_key:
            raise ServiceError(
                "INVALID_CONFIGURATION",
                "GROQ_API_KEY is required when LLM_PROVIDER=groq.",
                400,
            )
        chat = chat_model or ChatGroq(
            model=model,
            api_key=api_key,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max(0, min(max_retries, 2)),
            reasoning_effort=reasoning_effort,
            reasoning_format="hidden",
        )
        super().__init__(
            chat_model=chat,
            provider_name="groq",
            model_name=model,
            structured_strict=False,
        )


class OpenRouterProvider(StructuredLLMProvider):
    """Optional provider selected explicitly with LLM_PROVIDER=openrouter."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str = "low",
        provider_sort: str = "latency",
        data_collection: str = "",
        timeout: float = 35,
        max_retries: int = 1,
        max_tokens: int = 1800,
        chat_model=None,
    ):
        if not api_key:
            raise ServiceError(
                "INVALID_CONFIGURATION",
                "OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter.",
                400,
            )
        provider_routing = {"sort": provider_sort}
        if data_collection in {"allow", "deny"}:
            provider_routing["data_collection"] = data_collection
        chat = chat_model or ChatOpenRouter(
            model=model,
            api_key=api_key,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=int(timeout),
            max_retries=max(0, min(max_retries, 2)),
            reasoning={"effort": reasoning_effort},
            openrouter_provider=provider_routing,
        )
        super().__init__(
            chat_model=chat,
            provider_name="openrouter",
            model_name=model,
        )


def _history_messages(history: list[dict[str, str]]) -> list[tuple[str, str]]:
    return [(item["role"], item["content"]) for item in history[-6:]]


def _format_evidence(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "No usable evidence was retrieved."
    return "\n\n".join(
        f"[{item.id}] source_id={item.source_id}; source={item.source_name}; title={item.title}; "
        f"type={item.result_type}\n{item.content}"
        for item in evidence
    )


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def build_llm_provider(name: str, config: dict) -> StructuredLLMProvider:
    if name == "groq":
        return GroqProvider(
            api_key=config.get("GROQ_API_KEY", ""),
            model=config.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            reasoning_effort=config.get("GROQ_REASONING_EFFORT", "low"),
            timeout=config.get("GROQ_TIMEOUT", 35),
            max_retries=config.get("GROQ_MAX_RETRIES", 1),
            max_tokens=config.get("GROQ_MAX_TOKENS", 1800),
        )
    if name == "openrouter":
        return OpenRouterProvider(
            api_key=config.get("OPENROUTER_API_KEY", ""),
            model=config.get("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
            reasoning_effort=config.get("OPENROUTER_REASONING_EFFORT", "low"),
            provider_sort=config.get("OPENROUTER_PROVIDER_SORT", "latency"),
            data_collection=config.get("OPENROUTER_DATA_COLLECTION", ""),
            timeout=config.get("OPENROUTER_TIMEOUT", 35),
            max_retries=config.get("OPENROUTER_MAX_RETRIES", 1),
            max_tokens=config.get("OPENROUTER_MAX_TOKENS", 1800),
        )
    raise ValueError(f"Unsupported LLM provider: {name}")


def configured_model(config: dict) -> str | None:
    provider = config.get("LLM_PROVIDER", "demo")
    if provider == "groq":
        return config.get("GROQ_MODEL", "openai/gpt-oss-20b")
    if provider == "openrouter":
        return config.get("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
    return None
