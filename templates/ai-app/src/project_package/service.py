"""Voorbeeldlogica los van de gekozen client."""

from project_package.client import MockClient, TextClient
from project_package.config import Settings


def generate_reply(prompt: str, settings: Settings, client: TextClient | None = None) -> str:
    """Controleer invoer en gebruik standaard uitsluitend de lokale nepclient."""
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("De prompt mag niet leeg zijn.")
    if settings.mode != "mock":
        raise ValueError("Alleen de offline mock-modus is beschikbaar.")
    selected = MockClient() if client is None else client
    return selected.complete(cleaned, model=settings.model)
