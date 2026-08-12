import logging

import pytest

from app.models import (
    ChatPlan,
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
        query="targeted health query",
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


def direct_plan(text="Hello! How can I help?"):
    return ChatPlan(action="direct", intent="greeting", direct_response=text)


def research_plan(searches=None, intent="health_information"):
    return ChatPlan(
        action="research",
        intent=intent,
        searches=searches
        or [TargetedSearch(source_id="healthline", query="migraine symptoms guidance")],
    )


class FakeRetrieval:
    def __init__(self, initial=None, targeted=None):
        self.initial = [evidence()] if initial is None else initial
        self.targeted_evidence = [evidence()] if targeted is None else targeted
        self.raw_calls = []
        self.targeted_calls = []

    def retrieve(self, query, source_ids):
        self.raw_calls.append((query, source_ids))
        return self.initial

    def retrieve_targeted(self, searches, *, round_number=2):
        self.targeted_calls.append((searches, round_number))
        return self.targeted_evidence


class FakeLLM:
    provider_name = "groq"
    model_name = "openai/gpt-oss-20b"

    def __init__(self, plans=None, answers=None, health=None):
        self.plans = list(plans or [])
        self.answers = list(answers or [])
        self.health_responses = list(health or [])
        self.plan_calls = []
        self.answer_calls = []
        self.health_calls = 0

    def chat_plan(self, question, history, source_ids):
        self.plan_calls.append((question, history, source_ids))
        return self.plans[len(self.plan_calls) - 1]

    def chat_answer(self, question, history, evidence_items, source_ids):
        self.answer_calls.append((question, history, evidence_items, source_ids))
        return self.answers[len(self.answer_calls) - 1]

    def health_decision(self, *_args):
        response = self.health_responses[self.health_calls]
        self.health_calls += 1
        return response


@pytest.mark.parametrize(
    ("message", "plan"),
    [
        ("Hi", direct_plan()),
        ("Hello", direct_plan("Hello!")),
        ("Thanks", ChatPlan(action="direct", intent="conversation", direct_response="You're welcome.")),
        (
            "Who are you?",
            ChatPlan(action="direct", intent="product_help", direct_response="I'm MediVita, a health-information assistant."),
        ),
        (
            "Write a poem",
            ChatPlan(action="direct", intent="unrelated", direct_response="I focus on health information."),
        ),
    ],
)
def test_direct_intents_use_one_model_call_and_zero_retrieval(message, plan):
    retrieval = FakeRetrieval()
    llm = FakeLLM(plans=[plan])
    outcome, sources, calls = BoundedResearchController(retrieval, llm).chat(
        message, ["healthline"], []
    )
    assert outcome.response_kind == "direct"
    assert outcome.answer == plan.direct_response
    assert sources == []
    assert calls == 1
    assert len(llm.plan_calls) == 1
    assert llm.answer_calls == []
    assert retrieval.raw_calls == []
    assert retrieval.targeted_calls == []


def test_clarification_uses_one_model_call_and_zero_retrieval():
    plan = ChatPlan(
        action="clarify",
        intent="unclear",
        clarification_question="Which symptom or topic do you mean?",
    )
    retrieval = FakeRetrieval()
    outcome, sources, calls = BoundedResearchController(
        retrieval, FakeLLM(plans=[plan])
    ).chat("What about that?", ["healthline"], [])
    assert outcome.response_kind == "clarification"
    assert outcome.answer == "Which symptom or topic do you mean?"
    assert sources == []
    assert calls == 1
    assert retrieval.raw_calls == []
    assert retrieval.targeted_calls == []


def test_research_uses_only_planned_enabled_searches_and_two_model_calls():
    requested = [
        TargetedSearch(source_id="healthline", query=f"targeted query {index}")
        for index in range(5)
    ] + [TargetedSearch(source_id="webmd", query="disabled source query")]
    plan = ChatPlan.model_construct(
        action="research",
        intent="health_information",
        direct_response=None,
        clarification_question=None,
        searches=requested,
    )
    retrieval = FakeRetrieval()
    llm = FakeLLM(plans=[plan], answers=[chat_answer()])
    outcome, sources, calls = BoundedResearchController(retrieval, llm).chat(
        "raw user question must not be searched", ["healthline"], []
    )
    searches, round_number = retrieval.targeted_calls[0]
    assert outcome.response_kind == "researched"
    assert outcome.grounded_answer == chat_answer()
    assert calls == 2
    assert len(llm.plan_calls) == 1
    assert len(llm.answer_calls) == 1
    assert retrieval.raw_calls == []
    assert round_number == 1
    assert len(searches) == 4
    assert all(search.source_id == "healthline" for search in searches)
    assert all(search.query != "raw user question must not be searched" for search in searches)
    assert [source.url for source in sources] == ["https://healthline.com/a"]


def test_planner_may_search_a_subset_instead_of_every_enabled_source():
    searches = [
        TargetedSearch(source_id="mayo-clinic", query="migraine symptoms triggers"),
        TargetedSearch(source_id="cleveland-clinic", query="migraine common triggers"),
    ]
    targeted = [
        evidence("E1", "mayo-clinic", "https://mayoclinic.org/a", "mayoclinic.org"),
        evidence(
            "E2",
            "cleveland-clinic",
            "https://clevelandclinic.org/b",
            "clevelandclinic.org",
        ),
    ]
    enabled = ["healthline", "cleveland-clinic", "mayo-clinic", "webmd"]
    retrieval = FakeRetrieval(targeted=targeted)
    BoundedResearchController(
        retrieval,
        FakeLLM(plans=[research_plan(searches)], answers=[chat_answer(["E1", "E2"])]),
    ).chat("What are migraine triggers?", enabled, [])
    executed = retrieval.targeted_calls[0][0]
    assert [search.source_id for search in executed] == [
        "mayo-clinic",
        "cleveland-clinic",
    ]
    assert len(executed) < len(enabled)


def test_duplicate_planned_queries_are_removed():
    searches = [
        TargetedSearch(source_id="healthline", query="same query"),
        TargetedSearch(source_id="healthline", query="Same Query"),
    ]
    retrieval = FakeRetrieval()
    BoundedResearchController(
        retrieval,
        FakeLLM(plans=[research_plan(searches)], answers=[chat_answer()]),
    ).chat("question", ["healthline"], [])
    assert len(retrieval.targeted_calls[0][0]) == 1


def test_research_plan_without_an_allowed_search_fails_before_retrieval():
    plan = research_plan([TargetedSearch(source_id="webmd", query="disabled source query")])
    retrieval = FakeRetrieval()
    llm = FakeLLM(plans=[plan])
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(retrieval, llm).chat("question", ["healthline"], [])
    assert raised.value.code == "AI_INVALID_RESPONSE"
    assert len(llm.plan_calls) == 1
    assert llm.answer_calls == []
    assert retrieval.raw_calls == []
    assert retrieval.targeted_calls == []


def test_no_research_evidence_fails_without_final_model_call():
    retrieval = FakeRetrieval(targeted=[])
    llm = FakeLLM(plans=[research_plan()])
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(retrieval, llm).chat("question", ["healthline"], [])
    assert raised.value.code == "RETRIEVAL_UNAVAILABLE"
    assert len(llm.plan_calls) == 1
    assert llm.answer_calls == []


def test_planner_receives_recent_history_for_direct_follow_up_without_retrieval():
    history = [
        {"role": "user", "content": "What is sleep hygiene?"},
        {"role": "assistant", "content": "It describes habits supporting sleep."},
    ]
    retrieval = FakeRetrieval()
    llm = FakeLLM(
        plans=[
            ChatPlan(
                action="direct",
                intent="health_follow_up",
                direct_response="Yes, that is the topic we were discussing.",
            )
        ]
    )
    BoundedResearchController(retrieval, llm).chat("Is that what you meant?", ["healthline"], history)
    assert llm.plan_calls[0][1] == history
    assert retrieval.raw_calls == []
    assert retrieval.targeted_calls == []


def test_factual_follow_up_can_plan_research_using_history():
    history = [{"role": "user", "content": "We were discussing migraines."}]
    llm = FakeLLM(
        plans=[research_plan(intent="health_follow_up")],
        answers=[chat_answer()],
    )
    retrieval = FakeRetrieval()
    BoundedResearchController(retrieval, llm).chat(
        "What warning signs matter?", ["healthline"], history
    )
    assert llm.plan_calls[0][1] == history
    assert len(retrieval.targeted_calls) == 1


@pytest.mark.parametrize("model_ids", [[], ["E999"]])
def test_invalid_or_empty_model_evidence_ids_use_validated_fallback(model_ids):
    targeted = [
        evidence(f"E{index}", url=f"https://healthline.com/{index}")
        for index in range(1, 5)
    ]
    llm = FakeLLM(plans=[research_plan()], answers=[chat_answer(model_ids)])
    _, sources, _ = BoundedResearchController(
        FakeRetrieval(targeted=targeted), llm
    ).chat("question", ["healthline"], [])
    assert [source.url for source in sources] == [
        "https://healthline.com/1",
        "https://healthline.com/2",
        "https://healthline.com/3",
    ]


def test_valid_evidence_id_preserves_exact_citation_mapping():
    targeted = [evidence("E1"), evidence("E2", url="https://healthline.com/b")]
    llm = FakeLLM(plans=[research_plan()], answers=[chat_answer(["E2"])])
    _, sources, _ = BoundedResearchController(FakeRetrieval(targeted=targeted), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == ["https://healthline.com/b"]


def test_citation_fallback_rejects_disabled_duplicate_and_untrusted_urls():
    targeted = [
        evidence("E1", "webmd", "https://webmd.com/a", "webmd.com"),
        evidence("E2", url="https://healthline.com/a?utm_source=search"),
        evidence("E3", url="https://healthline.com/a/"),
        evidence("E4", url="http://healthline.com/b"),
        evidence("E5", url="https://healthline.com/c"),
    ]
    llm = FakeLLM(plans=[research_plan()], answers=[chat_answer([])])
    _, sources, _ = BoundedResearchController(FakeRetrieval(targeted=targeted), llm).chat(
        "question", ["healthline"], []
    )
    assert [source.url for source in sources] == [
        "https://healthline.com/a?utm_source=search",
        "https://healthline.com/c",
    ]


def test_research_logging_contains_counts_but_not_user_or_evidence_content(caplog):
    caplog.set_level(logging.INFO, logger="app.services.research")
    message = "private user message"
    BoundedResearchController(
        FakeRetrieval(),
        FakeLLM(plans=[research_plan()], answers=[chat_answer([])]),
    ).chat(message, ["healthline"], [])
    log_message = caplog.messages[-1]
    assert "model_calls=2" in log_message
    assert "research_passes=1" in log_message
    assert "evidence=1" in log_message
    assert "citation_fallback=true" in log_message
    assert message not in log_message
    assert "Grounded general health evidence" not in log_message


def test_health_check_preserves_initial_retrieval_and_grounded_workflow():
    final = FinalHealthCheckAnswer(
        summary="Non-diagnostic summary.",
        reported_symptoms=["headache"],
        general_considerations=["Patterns matter."],
        self_care=["Track changes."],
        seek_medical_attention=["Seek care if worsening."],
        used_evidence_ids=["E1", "invented"],
    )
    retrieval = FakeRetrieval()
    llm = FakeLLM(health=[HealthResearchDecision(decision="answer", answer=final)])
    answer, sources, rounds = BoundedResearchController(retrieval, llm).health(
        "headache for two days", ["healthline"]
    )
    assert answer.reported_symptoms == ["headache"]
    assert len(sources) == 1
    assert rounds == 1
    assert retrieval.raw_calls == [("headache for two days", ["healthline"])]


def test_health_check_still_allows_one_final_follow_up_round():
    final = FinalHealthCheckAnswer(summary="Summary.", used_evidence_ids=["E1"])
    first = HealthResearchDecision(
        decision="search_more",
        follow_up_searches=[
            TargetedSearch(source_id="healthline", query="headache warning signs")
        ],
    )
    second = HealthResearchDecision(decision="answer", answer=final)
    retrieval = FakeRetrieval()
    llm = FakeLLM(health=[first, second])
    _, _, rounds = BoundedResearchController(retrieval, llm).health(
        "headache", ["healthline"]
    )
    assert rounds == 2
    assert llm.health_calls == 2
    assert retrieval.raw_calls == [("headache", ["healthline"])]
    assert retrieval.targeted_calls[0][1] == 2


def test_health_check_no_evidence_fails_before_model_call():
    retrieval = FakeRetrieval(initial=[])
    llm = FakeLLM()
    with pytest.raises(ServiceError) as raised:
        BoundedResearchController(retrieval, llm).health(
            "headache for two days", ["healthline"]
        )
    assert raised.value.code == "RETRIEVAL_UNAVAILABLE"
    assert llm.health_calls == 0
