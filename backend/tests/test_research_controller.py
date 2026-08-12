import logging

import pytest

from app.models import (
    ChatResearchDecision,
    EvidenceItem,
    FinalChatAnswer,
    FinalHealthCheckAnswer,
    HealthResearchDecision,
    TargetedSearch,
)
from app.services.research import BoundedResearchController
from app.utils.errors import ServiceError


def evidence(
    item_id="E1",
    source_id="healthline",
    url="https://healthline.com/a",
    domain="healthline.com",
):
    return EvidenceItem(
        id=item_id,
        source_id=source_id,
        source_name="Healthline",
        domain=domain,
        title="Evidence title",
        url=url,
        snippet="snippet",
        content="Grounded general health evidence.",
        query="question",
        result_type="page",
    )


def chat_answer(ids=None):
    return FinalChatAnswer(
        overview="Overview.",
        possible_considerations="Considerations.",
        what_may_help="Conservative steps.",
        when_to_seek_medical_care="Seek care if concerning.",
        used_evidence_ids=["E1"] if ids is None else ids,
    )


class FakeRetrieval:
    def __init__(self, initial=None, additions=None):
        self.initial = [evidence()] if initial is None else initial
        self.additions = additions or []
        self.targeted = []

    def retrieve(self, _query, _source_ids):
        return self.initial

    def retrieve_targeted(self, searches):
        self.targeted = searches
        return self.additions


class FakeLLM:
    def __init__(self, chat=None, health=None):
        self.chat_responses = list(chat or [])
        self.health_responses = list(health or [])
        self.chat_calls = 0
        self.health_calls = 0

    def chat_decision(self, *_args):
        response = self.chat_responses[self.chat_calls]
        self.chat_calls += 1
        return response

    def health_decision(self, *_args):
        response = self.health_responses[self.health_calls]
        self.health_calls += 1
        return response


def test_direct_answer_uses_one_llm_call_and_ignores_fake_evidence_ids():
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer(["E1", "FAKE"]))])
    answer, sources, rounds = BoundedResearchController(FakeRetrieval(), llm).chat("question", ["healthline"], [])
    assert answer.overview == "Overview."
    assert rounds == 1
    assert llm.chat_calls == 1
    assert [source.url for source in sources] == ["https://healthline.com/a"]


def test_search_more_runs_one_followup_and_caps_filters_queries():
    requested = [
        TargetedSearch(source_id="healthline", query=f"query {index}")
        for index in range(5)
    ] + [TargetedSearch(source_id="webmd", query="disabled source")]
    llm = FakeLLM(
        chat=[
            ChatResearchDecision.model_construct(decision="search_more", answer=None, follow_up_searches=requested),
            ChatResearchDecision(decision="answer", answer=chat_answer()),
        ]
    )
    retrieval = FakeRetrieval()
    _answer, _sources, rounds = BoundedResearchController(retrieval, llm).chat(
        "question", ["healthline"], []
    )
    assert rounds == 2
    assert llm.chat_calls == 2
    assert len(retrieval.targeted) == 4
    assert all(search.source_id == "healthline" for search in retrieval.targeted)


def test_second_search_more_is_rejected_without_third_call():
    search_more = ChatResearchDecision(
        decision="search_more",
        follow_up_searches=[TargetedSearch(source_id="healthline", query="more evidence")],
    )
    llm = FakeLLM(chat=[search_more, search_more])
    with pytest.raises(ServiceError, match="usable grounded answer") as raised:
        BoundedResearchController(FakeRetrieval(), llm).chat("question", ["healthline"], [])
    assert raised.value.code == "AI_INVALID_RESPONSE"
    assert llm.chat_calls == 2


def test_no_evidence_fails_before_llm_call():
    llm = FakeLLM()
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(FakeRetrieval(initial=[]), llm).chat("question", ["healthline"], [])
    assert raised.value.code == "RETRIEVAL_UNAVAILABLE"
    assert llm.chat_calls == 0


def test_empty_model_evidence_ids_fall_back_to_top_ranked_context_evidence():
    initial = [
        evidence(f"E{index}", url=f"https://healthline.com/{index}")
        for index in range(1, 5)
    ]
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer([]))])
    _answer, sources, rounds = BoundedResearchController(FakeRetrieval(initial=initial), llm).chat(
        "question", ["healthline"], []
    )
    assert rounds == 1
    assert [source.url for source in sources] == [
        "https://healthline.com/1",
        "https://healthline.com/2",
        "https://healthline.com/3",
    ]


def test_wholly_invalid_model_evidence_ids_use_validated_fallback():
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer(["E999"]))])
    _answer, sources, _rounds = BoundedResearchController(FakeRetrieval(), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == ["https://healthline.com/a"]


def test_citation_resolution_logs_counts_without_content(caplog):
    caplog.set_level(logging.INFO, logger="app.services.research")
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer([]))])
    BoundedResearchController(FakeRetrieval(), llm).chat("question", ["healthline"], [])
    message = caplog.messages[-1]
    assert "evidence=1" in message
    assert "model_evidence_ids=0" in message
    assert "valid_model_evidence_ids=0" in message
    assert "sources=1" in message
    assert "citation_fallback=true" in message
    assert "rounds=1" in message


def test_valid_model_evidence_ids_preserve_exact_mapping_without_fallback_expansion():
    initial = [evidence("E1"), evidence("E2", url="https://healthline.com/b")]
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer(["E2"]))])
    _answer, sources, _rounds = BoundedResearchController(FakeRetrieval(initial=initial), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == ["https://healthline.com/b"]


def test_fallback_rejects_disabled_sources():
    initial = [
        evidence("E1", "webmd", "https://webmd.com/a", "webmd.com"),
        evidence("E2", "healthline", "https://healthline.com/b"),
    ]
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer([]))])
    _answer, sources, _rounds = BoundedResearchController(FakeRetrieval(initial=initial), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == ["https://healthline.com/b"]


def test_fallback_canonical_deduplicates_urls():
    initial = [
        evidence("E1", url="https://healthline.com/a?utm_source=search"),
        evidence("E2", url="https://healthline.com/a/"),
        evidence("E3", url="https://healthline.com/b"),
    ]
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer([]))])
    _answer, sources, _rounds = BoundedResearchController(FakeRetrieval(initial=initial), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == [
        "https://healthline.com/a?utm_source=search",
        "https://healthline.com/b",
    ]


def test_fallback_rejects_untrusted_urls_and_errors_if_none_are_citable():
    initial = [evidence("E1", url="http://healthline.com/a")]
    llm = FakeLLM(chat=[ChatResearchDecision(decision="answer", answer=chat_answer([]))])
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(FakeRetrieval(initial=initial), llm).chat(
            "question", ["healthline"], []
        )
    assert raised.value.code == "RETRIEVAL_UNAVAILABLE"


def test_health_check_uses_same_bounded_grounded_workflow():
    final = FinalHealthCheckAnswer(
        summary="Non-diagnostic summary.",
        reported_symptoms=["headache"],
        general_considerations=["Patterns matter."],
        self_care=["Track changes."],
        seek_medical_attention=["Seek care if worsening."],
        used_evidence_ids=["E1", "invented"],
    )
    llm = FakeLLM(health=[HealthResearchDecision(decision="answer", answer=final)])
    answer, sources, rounds = BoundedResearchController(FakeRetrieval(), llm).health(
        "headache for two days", ["healthline"]
    )
    assert answer.reported_symptoms == ["headache"]
    assert len(sources) == 1
    assert rounds == 1


@pytest.mark.parametrize("model_ids", [[], ["E999"]])
def test_health_check_uses_validated_citation_fallback(model_ids):
    final = FinalHealthCheckAnswer(
        summary="Non-diagnostic summary.",
        used_evidence_ids=model_ids,
    )
    llm = FakeLLM(health=[HealthResearchDecision(decision="answer", answer=final)])
    _answer, sources, _rounds = BoundedResearchController(FakeRetrieval(), llm).health(
        "headache for two days", ["healthline"]
    )
    assert [source.url for source in sources] == ["https://healthline.com/a"]


def test_health_check_no_evidence_fails_before_llm_call():
    llm = FakeLLM()
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(FakeRetrieval(initial=[]), llm).health(
            "headache for two days", ["healthline"]
        )
    assert raised.value.code == "RETRIEVAL_UNAVAILABLE"
    assert llm.health_calls == 0


def test_duplicate_followup_queries_are_removed():
    searches = [
        TargetedSearch(source_id="healthline", query="same query"),
        TargetedSearch(source_id="healthline", query="Same Query"),
    ]
    llm = FakeLLM(
        chat=[
            ChatResearchDecision(decision="search_more", follow_up_searches=searches),
            ChatResearchDecision(decision="answer", answer=chat_answer()),
        ]
    )
    retrieval = FakeRetrieval()
    BoundedResearchController(retrieval, llm).chat("question", ["healthline"], [])
    assert len(retrieval.targeted) == 1
