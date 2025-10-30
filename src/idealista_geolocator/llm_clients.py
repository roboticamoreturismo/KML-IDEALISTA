"""Clientes ligeros para modelos de lenguaje configurables."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Optional

from .config import settings

LOGGER = logging.getLogger(__name__)


_openai_spec = importlib.util.find_spec("openai")
if _openai_spec is not None:
    openai = importlib.import_module("openai")
else:
    openai = None  # type: ignore


class _PerplexityWrapper:
    """Cliente HTTP simple para la API de Perplexity."""

    def __init__(self, api_key: str, model: str) -> None:
        import requests

        self.api_key = api_key
        self.model = model
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        response = self.session.post("https://api.perplexity.ai/chat/completions", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


@dataclass
class LLMClient:
    """Interfaz unificada para modelos OpenAI o Perplexity."""

    provider: str
    model: str
    api_key: Optional[str] = None

    def __post_init__(self) -> None:
        self.provider = self.provider.lower()
        if not self.api_key:
            if self.provider == "openai":
                self.api_key = settings.openai_keys.next()
            elif self.provider == "perplexity":
                self.api_key = settings.perplexity_keys.next()
        if self.provider == "openai" and openai is not None and self.api_key:
            openai.api_key = self.api_key
        elif self.provider == "perplexity" and self.api_key:
            self._perplexity = _PerplexityWrapper(self.api_key, self.model)
        else:
            self._perplexity = None

    def is_ready(self) -> bool:
        if self.provider == "openai":
            return openai is not None and bool(self.api_key)
        if self.provider == "perplexity":
            return hasattr(self, "_perplexity") and self._perplexity is not None
        return False

    def complete(self, prompt: str, temperature: float = 0.2) -> str:
        if not self.is_ready():
            LOGGER.debug("Cliente LLM no configurado. Se devuelve cadena vacía.")
            return ""
        if self.provider == "openai":
            try:
                response = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Error llamando a OpenAI: %s", exc)
                return ""
            return response["choices"][0]["message"]["content"].strip()
        if self.provider == "perplexity" and hasattr(self, "_perplexity"):
            try:
                return self._perplexity.generate(prompt)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Error llamando a Perplexity: %s", exc)
                return ""
        return ""


def build_llm_from_selection(provider: str, model: str, api_key: Optional[str]) -> Optional[LLMClient]:
    client = LLMClient(provider=provider, model=model, api_key=api_key)
    return client if client.is_ready() else None

