"""Carga de configuración y API keys desde ficheros .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from itertools import cycle
from typing import Iterable, Iterator, List, Optional

from dotenv import load_dotenv

load_dotenv()


def _parse_keys(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class ApiKeyPool:
    """Gestiona listas de claves API y permite rotación simple."""

    keys: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._iterator: Iterator[str] = cycle(self.keys) if self.keys else iter(())

    def next(self) -> Optional[str]:
        try:
            return next(self._iterator)
        except StopIteration:
            return None

    def has_keys(self) -> bool:
        return bool(self.keys)


@dataclass
class Settings:
    """Representa la configuración global del paquete."""

    google_maps_keys: ApiKeyPool = field(default_factory=lambda: ApiKeyPool(_parse_keys(os.getenv("GOOGLE_MAPS_API_KEYS"))))
    bing_maps_keys: ApiKeyPool = field(default_factory=lambda: ApiKeyPool(_parse_keys(os.getenv("BING_MAPS_API_KEYS"))))
    openai_keys: ApiKeyPool = field(default_factory=lambda: ApiKeyPool(_parse_keys(os.getenv("OPENAI_API_KEYS"))))
    perplexity_keys: ApiKeyPool = field(default_factory=lambda: ApiKeyPool(_parse_keys(os.getenv("PERPLEXITY_API_KEYS"))))
    catastro_base_url: str = field(default_factory=lambda: os.getenv("CATASTRO_BASE_URL", ""))
    catastro_token: str = field(default_factory=lambda: os.getenv("CATASTRO_API_TOKEN", ""))
    default_output_root: str = field(default_factory=lambda: os.getenv("OUTPUT_ROOT", "clientes"))

    def any_ai_key(self) -> bool:
        return self.openai_keys.has_keys() or self.perplexity_keys.has_keys()

    def available_models(self) -> Iterable[str]:
        models = [
            os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
            os.getenv("PERPLEXITY_DEFAULT_MODEL", "sonar-small-chat"),
        ]
        return [model for model in models if model]


settings = Settings()

