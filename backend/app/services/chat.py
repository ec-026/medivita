"""Health-information chat orchestration."""

from __future__ import annotations

from flask import current_app

from app.providers.search import as_source_reference, build_search_provider
from app.services.factory import build_research_controller
from app.services.trace import ResearchTraceEmitter
from app.sources import validate_source_ids
from app.utils.safety import URGENT_NOTICE, has_urgent_signal

TOPICS = {
    "headache": {
        "keywords": ("headache", "migraine"),
        "overview": "Headaches are common and can have many triggers, including dehydration, sleep changes, stress, eye strain and migraine disorders.",
        "considerations": "Patterns matter: note timing, duration, location, intensity, associated nausea or light sensitivity, and recent changes in frequency.",
        "help": "Regular meals, hydration, a consistent sleep schedule and a brief symptom diary may help identify patterns. Medication choices should be discussed with a clinician or pharmacist when headaches recur.",
        "care": "Seek medical advice for new, worsening or frequent headaches. Sudden severe headache, weakness, confusion, fever with neck stiffness, or headache after a significant injury needs urgent evaluation.",
    },
    "ibuprofen": {
        "keywords": ("ibuprofen", "anti-inflammatory", "nsaid"),
        "overview": "Ibuprofen is a nonsteroidal anti-inflammatory drug used for short-term relief of pain, fever and inflammation.",
        "considerations": "It may not be suitable for everyone, including some people with stomach ulcers, kidney disease, cardiovascular risks, pregnancy, or certain medication combinations.",
        "help": "Follow the product label or a clinician's directions, use the lowest effective dose for the shortest practical time, and ask a pharmacist about interactions.",
        "care": "Get prompt help for signs of an allergic reaction, vomiting blood, black stools, severe stomach pain, chest pain or breathing difficulty.",
    },
    "insulin": {
        "keywords": ("insulin resistance", "insulin"),
        "overview": "Insulin resistance means the body's cells do not respond to insulin as efficiently, so more insulin may be needed to help manage blood glucose.",
        "considerations": "It can be associated with several metabolic factors and may exist without obvious symptoms. Clinical history and blood tests provide meaningful context.",
        "help": "Regular movement, balanced meals, adequate sleep and sustainable habits can support metabolic health. Individual advice should come from a qualified clinician.",
        "care": "Discuss concerns or abnormal glucose results with a healthcare professional, especially if you notice increased thirst, frequent urination or unexplained weight change.",
    },
    "sleep": {
        "keywords": ("sleep", "insomnia"),
        "overview": "Sleep supports cardiovascular, metabolic, immune and cognitive function. Both duration and regularity contribute to overall health.",
        "considerations": "Stress, schedules, light exposure, medications, pain and sleep disorders can all affect sleep quality.",
        "help": "A consistent wake time, a quiet dark room, morning daylight and limiting late caffeine can support a healthier sleep routine.",
        "care": "Seek advice when sleep problems persist, impair daytime function, or include loud snoring, gasping, unusual movements or safety concerns.",
    },
    "vitamin-d": {
        "keywords": ("vitamin d", "vit d"),
        "overview": "Vitamin D helps the body absorb calcium and supports bone, muscle and immune function.",
        "considerations": "Sun exposure, diet, skin pigmentation, age, geography and some health conditions can influence vitamin D status. A blood test is needed to interpret an individual level.",
        "help": "Food sources and supplements can help, but dosing should reflect personal needs because excessive supplementation can be harmful.",
        "care": "Review test results and supplement plans with a clinician, particularly with kidney disease, pregnancy, or medicines that affect calcium.",
    },
    "allergies": {
        "keywords": ("allergy", "allergies", "pollen", "hay fever"),
        "overview": "Seasonal allergies occur when the immune system reacts to airborne triggers such as pollen, often causing sneezing, congestion and itchy or watery eyes.",
        "considerations": "Timing, local pollen patterns, indoor exposures and symptoms such as fever or body aches can help distinguish common possibilities.",
        "help": "Reducing exposure, showering after outdoor activity and discussing suitable antihistamines or nasal treatments with a pharmacist may help.",
        "care": "Breathing difficulty, throat swelling or faintness requires urgent care. Persistent symptoms or wheezing should be assessed professionally.",
    },
}

GENERIC = {
    "overview": "Health questions often have more than one possible explanation, and personal context changes what information is most relevant.",
    "considerations": "Consider the timing, duration, severity, triggers, associated symptoms, medical history and any recent changes. These details help a healthcare professional assess the situation.",
    "help": "Keep a short record of the pattern, prioritize rest, hydration and regular meals where appropriate, and avoid starting or stopping medicines without professional guidance.",
    "care": "Seek professional advice for symptoms that persist, worsen, recur, or interfere with daily life. Sudden or severe symptoms may need urgent evaluation.",
}


class ChatService:
    def __init__(self):
        self.config = current_app.config

    def respond(
        self,
        message: str,
        enabled_sources: list[str],
        history: list[dict[str, str]],
        trace: ResearchTraceEmitter | None = None,
    ) -> dict:
        source_ids = validate_source_ids(enabled_sources)
        if not source_ids:
            raise ValueError("No supported trusted sources were selected.")
        urgent = has_urgent_signal(message)
        if trace:
            trace.emit(
                stage="safety",
                status="completed",
                label="Safety signal detected" if urgent else "Safety screening complete",
                tool="Deterministic safety rules",
                message="Urgent-care notice added" if urgent else None,
            )
        provider_name = self.config["LLM_PROVIDER"]
        if provider_name == "demo":
            search = build_search_provider("demo")
            references = [
                as_source_reference(item)
                for item in search.search(message, source_ids)
            ]
            content = self._demo_content(message)
            sections = [
                {"title": "Overview", "content": content["overview"]},
                {"title": "Possible considerations", "content": content["considerations"]},
                {"title": "What may help", "content": content["help"]},
                {"title": "When to seek medical care", "content": content["care"]},
            ]
            answer = content["overview"]
            if trace:
                trace.finish_demo()
        else:
            if self.config["SEARCH_PROVIDER"] != "duckduckgo":
                raise ValueError("Connected mode requires SEARCH_PROVIDER=duckduckgo.")
            controller = (
                build_research_controller(self.config, trace)
                if trace
                else build_research_controller(self.config)
            )
            final, references, _rounds = controller.chat(message, source_ids, history)
            answer = final.overview
            sections = [
                {"title": "Overview", "content": final.overview},
                {"title": "Possible considerations", "content": final.possible_considerations},
                {"title": "What may help", "content": final.what_may_help},
                {"title": "When to seek medical care", "content": final.when_to_seek_medical_care},
            ]
        response = {
            "answer": answer,
            "sections": sections,
            "sources": [reference.to_dict() for reference in references],
            "safety_notice": URGENT_NOTICE if urgent else None,
            "mode": "demo" if provider_name == "demo" else "connected",
            "disclaimer": "General health information only; not medical advice, diagnosis, or treatment.",
        }
        if trace:
            response["research_trace"] = trace.events
            response["research_summary"] = trace.summary
        return response

    @staticmethod
    def _demo_content(message: str) -> dict[str, str]:
        lowered = message.lower()
        for topic in TOPICS.values():
            if any(keyword in lowered for keyword in topic["keywords"]):
                return topic
        return GENERIC
