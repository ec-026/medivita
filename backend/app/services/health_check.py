"""Non-diagnostic structured health summary service."""

from __future__ import annotations

import re

from flask import current_app

from app.providers.search import as_source_reference, build_search_provider
from app.services.factory import build_research_controller
from app.services.trace import ResearchTraceEmitter
from app.sources import validate_source_ids
from app.utils.safety import URGENT_NOTICE, has_urgent_signal

SYMPTOM_LABELS = {
    "headache": ("headache", "migraine"), "fatigue": ("fatigue", "tired", "exhausted"),
    "cough": ("cough",), "fever": ("fever", "temperature"), "nausea": ("nausea", "nauseous"),
    "dizziness": ("dizzy", "dizziness", "lightheaded"), "sore throat": ("sore throat",),
    "congestion": ("congestion", "stuffy", "blocked nose"), "pain": ("pain",),
}


class HealthCheckService:
    def __init__(self):
        self.config = current_app.config

    def summarize(
        self,
        description: str,
        enabled_sources: list[str],
        trace: ResearchTraceEmitter | None = None,
    ) -> dict:
        source_ids = validate_source_ids(enabled_sources)
        if not source_ids:
            raise ValueError("No supported trusted sources were selected.")
        urgent = has_urgent_signal(description)
        if trace:
            trace.emit(
                stage="safety",
                status="completed",
                label="Safety signal detected" if urgent else "Safety screening complete",
                tool="Deterministic safety rules",
                message="Urgent-care notice added" if urgent else None,
            )
        if self.config["LLM_PROVIDER"] != "demo":
            if self.config["SEARCH_PROVIDER"] != "duckduckgo":
                raise ValueError("Connected mode requires SEARCH_PROVIDER=duckduckgo.")
            controller = (
                build_research_controller(self.config, trace)
                if trace
                else build_research_controller(self.config)
            )
            final, references, _rounds = controller.health(description, source_ids)
            seek_attention = list(final.seek_medical_attention)
            if urgent and URGENT_NOTICE not in seek_attention:
                seek_attention.insert(0, URGENT_NOTICE)
            response = {
                "summary": final.summary,
                "reported_symptoms": final.reported_symptoms,
                "general_considerations": final.general_considerations,
                "self_care": final.self_care,
                "seek_medical_attention": seek_attention,
                "safety_notice": URGENT_NOTICE if urgent else None,
                "sources": [reference.to_dict() for reference in references],
                "mode": "connected",
            }
            if trace:
                response["research_trace"] = trace.events
                response["research_summary"] = trace.summary
            return response

        lowered = description.lower()
        symptoms = [label for label, words in SYMPTOM_LABELS.items() if any(word in lowered for word in words)]
        if not symptoms:
            symptoms = ["No specific symptom keywords identified; your full description remains important"]
        duration = self._duration(description)
        references = [
            as_source_reference(item)
            for item in build_search_provider("demo").search(description, source_ids)
        ]
        response = {
            "summary": "This demo summary organizes the details you reported; it does not diagnose or calculate a health score. " + (f"You mentioned a possible duration of {duration}." if duration else "Duration and symptom pattern are useful details to track."),
            "reported_symptoms": symptoms,
            "general_considerations": ["Many symptoms have multiple possible causes, so timing, severity, triggers and associated changes matter.", "A clinician can place these details in context with your medical history, medicines and an examination."],
            "self_care": ["Record changes in symptoms, temperature and any clear triggers.", "Prioritize rest, fluids and regular meals when these are appropriate for you.", "Ask a clinician or pharmacist before changing medicines or supplements."],
            "seek_medical_attention": [URGENT_NOTICE if urgent else "Arrange medical advice if symptoms are persistent, worsening, recurring or affecting daily activities.", "Seek urgent evaluation for sudden severe symptoms, breathing difficulty, fainting, new confusion or other rapid deterioration."],
            "safety_notice": URGENT_NOTICE if urgent else None,
            "sources": [reference.to_dict() for reference in references],
            "mode": "demo",
        }
        if trace:
            trace.finish_demo()
            response["research_trace"] = trace.events
            response["research_summary"] = trace.summary
        return response

    @staticmethod
    def _duration(description: str) -> str | None:
        match = re.search(r"\b(?:for\s+)?(\d+|a|one|two|three|four|five|six|seven)\s+(hour|day|week|month)s?\b", description, re.I)
        return " ".join(match.groups()) if match else None
