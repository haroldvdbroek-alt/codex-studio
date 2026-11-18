"""Een verwisselbaar contract en een lokale, deterministische nepclient."""

from typing import Protocol


class TextClient(Protocol):
    def complete(self, prompt: str, *, model: str) -> str:
        """Geef een antwoord op een prompt."""
        ...


class MockClient:
    """Boots een antwoord na; gebruikt geen API-sleutel, netwerk of AI-model."""

    def complete(self, prompt: str, *, model: str) -> str:
        return f"[demo:{model}] {prompt}"
