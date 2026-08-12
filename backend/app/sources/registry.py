"""Concrete source adapters and registry."""

from __future__ import annotations

from app.models import MedicalSource
from app.sources.base import HomepageMedicalSource


class HealthlineSource(HomepageMedicalSource):
    metadata = MedicalSource(
        id="healthline",
        name="Healthline",
        domain="healthline.com",
        description="Consumer-focused health information covering conditions, wellness and medications.",
    )


class ClevelandClinicSource(HomepageMedicalSource):
    metadata = MedicalSource(
        id="cleveland-clinic",
        name="Cleveland Clinic",
        domain="clevelandclinic.org",
        description="Patient-focused health information from Cleveland Clinic.",
    )


class MayoClinicSource(HomepageMedicalSource):
    metadata = MedicalSource(
        id="mayo-clinic",
        name="Mayo Clinic",
        domain="mayoclinic.org",
        description="Medical information covering diseases, symptoms, tests and treatments.",
    )


class WebMDSource(HomepageMedicalSource):
    metadata = MedicalSource(
        id="webmd",
        name="WebMD",
        domain="webmd.com",
        description="Consumer health information, medical references and wellness content.",
    )


_SOURCES = {
    source.metadata.id: source
    for source in (HealthlineSource(), ClevelandClinicSource(), MayoClinicSource(), WebMDSource())
}


def list_sources() -> list[HomepageMedicalSource]:
    return list(_SOURCES.values())


def get_source(source_id: str) -> HomepageMedicalSource | None:
    return _SOURCES.get(source_id)


def validate_source_ids(source_ids: list[str]) -> list[str]:
    return list(dict.fromkeys(source_id for source_id in source_ids if source_id in _SOURCES))
