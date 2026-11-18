"""Configuratie via expliciete waarden of procesomgevingsvariabelen."""

from collections.abc import Mapping
from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    mode: str = "mock"
    model: str = "demo-model"
    # Voor een toekomstige provider; nooit nodig voor de lokale nepclient.
    api_key: str | None = field(default=None, repr=False)


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Lees alleen bekende variabelen; gebruik in tests altijd fictieve waarden."""
    source = os.environ if environ is None else environ
    mode = source.get("AI_MODE", "mock").strip()
    if mode != "mock":
        raise ValueError("AI_MODE ondersteunt alleen mock; echte providers zijn niet ingericht.")
    model = source.get("AI_MODEL", "demo-model").strip()
    if not model:
        raise ValueError("AI_MODEL mag niet leeg zijn.")
    api_key = source.get("AI_API_KEY", "").strip() or None
    return Settings(mode=mode, model=model, api_key=api_key)
