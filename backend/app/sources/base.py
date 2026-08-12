"""Medical source adapter contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import MedicalSource, SourceReference


class BaseMedicalSource(ABC):
    metadata: MedicalSource

    @abstractmethod
    def demo_reference(self, topic: str) -> SourceReference:
        """Return a safe, deterministic reference for credential-free demo mode."""


class HomepageMedicalSource(BaseMedicalSource):
    def demo_reference(self, topic: str) -> SourceReference:
        return SourceReference(
            name=self.metadata.name,
            domain=self.metadata.domain,
            title=f"{topic} information — source homepage",
            url=f"https://{self.metadata.domain}/",
        )
