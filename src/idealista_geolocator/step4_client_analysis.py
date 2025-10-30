"""Implementación del Paso 4: análisis del cliente a partir de conversación."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Iterable, List, Optional, Tuple

import pandas as pd
from unidecode import unidecode

from .data_models import ClientProfile
from .llm_clients import LLMClient, build_llm_from_selection

LOGGER = logging.getLogger(__name__)


class ClientAnalyzer:
    """Convierte una transcripción en un perfil estructurado del cliente."""

    def __init__(
        self,
        language_model_provider: str = "openai",
        language_model_name: str = "gpt-4o-mini",
        language_model_api_key: Optional[str] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.llm_client = llm_client or build_llm_from_selection(
            language_model_provider, language_model_name, language_model_api_key
        )

    def analyze(self, transcript: str, nombre_cliente: str = "Cliente") -> ClientProfile:
        normalized = unidecode(transcript.lower())
        profile = ClientProfile(nombre_cliente=nombre_cliente)
        profile.nivel_decision = self._detect_decision_level(normalized)
        profile.motivaciones = self._detect_motivations(normalized)
        profile.flexibilidad = self._detect_flexibility(normalized)
        profile.estilo_comunicacion = self._detect_communication_style(normalized)
        profile.prioridades_emocionales = self._detect_emotional_priorities(normalized)
        (
            profile.tipo_vivienda,
            profile.habitaciones_min,
            profile.banos_min,
            profile.superficie_min,
        ) = self._detect_house_needs(normalized)
        profile.caracteristicas_deseadas = self._detect_desired_features(normalized)
        profile.orientacion_preferida = self._detect_orientation(normalized)
        profile.ubicaciones_preferidas = self._detect_locations(normalized)
        profile.presupuesto_max = self._detect_budget(normalized)
        profile.acepta_reformas = self._detect_refurbishment(normalized)
        profile.comentarios_adicionales = transcript.strip()
        self._llm_enrichment(profile, transcript)
        return profile

    def to_dataframe(self, profile: ClientProfile) -> pd.DataFrame:
        return pd.DataFrame([asdict(profile)])

    def _detect_decision_level(self, text: str) -> str:
        if "decidido" in text or "claro" in text:
            return "decidido"
        if any(keyword in text for keyword in ["duda", "no se", "veremos", "quizas"]):
            return "indeciso"
        return "en evaluación"

    def _detect_motivations(self, text: str) -> List[str]:
        motivations = []
        if any(keyword in text for keyword in ["familia", "hijos", "ninos"]):
            motivations.append("familia")
        if "inversion" in text or "rentabilidad" in text:
            motivations.append("inversión")
        if "jubil" in text or "tranquil" in text:
            motivations.append("estilo de vida")
        if "teletrabajo" in text or "oficina" in text:
            motivations.append("trabajo")
        return motivations

    def _detect_flexibility(self, text: str) -> str:
        if any(keyword in text for keyword in ["nos adaptamos", "flexible", "podria ser"]):
            return "flexible"
        if any(keyword in text for keyword in ["imprescindible", "necesitamos", "si o si"]):
            return "estricto"
        return "moderado"

    def _detect_communication_style(self, text: str) -> str:
        if any(keyword in text for keyword in ["creo", "siento", "emocion"]):
            return "emocional"
        if any(keyword in text for keyword in ["numeros", "rentabilidad", "datos"]):
            return "analítico"
        return "directo"

    def _detect_emotional_priorities(self, text: str) -> List[str]:
        priorities = []
        if "luz" in text or "luminos" in text:
            priorities.append("luminosidad")
        if "vista" in text or "panoram" in text or "mar" in text:
            priorities.append("vistas")
        if "tranquil" in text or "silencio" in text:
            priorities.append("zona tranquila")
        if "centro" in text or "servicios" in text:
            priorities.append("cercanía a servicios")
        return priorities

    def _detect_house_needs(self, text: str) -> Tuple[List[str], Optional[int], Optional[int], Optional[float]]:
        property_types = []
        mapping = {
            "chalet": ["chalet", "casa"],
            "piso": ["piso", "apartamento"],
            "atico": ["atico"],
            "duplex": ["duplex"],
            "finca": ["finca"],
        }
        for tipo, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                property_types.append(tipo)

        rooms_match = re.search(r"(\d+)\s*(habitaciones|cuartos|dormitorios)", text)
        baths_match = re.search(r"(\d+)\s*(banos|baños)", text)
        area_match = re.search(r"(\d{2,4})\s*m2", text)

        habitaciones = int(rooms_match.group(1)) if rooms_match else None
        banos = int(baths_match.group(1)) if baths_match else None
        superficie = float(area_match.group(1)) if area_match else None

        return property_types, habitaciones, banos, superficie

    def _detect_desired_features(self, text: str) -> List[str]:
        features = {
            "terraza": ["terraza", "balcon"],
            "jardin": ["jardin", "patio"],
            "piscina": ["piscina", "pool"],
            "garaje": ["garaje", "aparcamiento"],
            "trastero": ["trastero", "almacen"],
        }
        desired = [feature for feature, keywords in features.items() if any(keyword in text for keyword in keywords)]
        return desired

    def _detect_orientation(self, text: str) -> List[str]:
        orientations = [orient for orient in ["norte", "sur", "este", "oeste"] if orient in text]
        return orientations

    def _detect_locations(self, text: str) -> List[str]:
        patterns = re.findall(r"zona de ([a-záéíóúñ\s]+)", text)
        patterns += re.findall(r"en ([a-záéíóúñ\s]+) ciudad", text)
        cleaned = [pattern.strip() for pattern in patterns]
        unique = list(dict.fromkeys(cleaned))
        return unique

    def _detect_budget(self, text: str) -> Optional[float]:
        match = re.search(r"(\d{2,3}[\.\d{3}]*)\s*euros", text)
        if match:
            amount = match.group(1).replace(".", "")
            return float(amount)
        return None

    def _detect_refurbishment(self, text: str) -> Optional[bool]:
        if "no queremos reformar" in text or "lista para entrar" in text:
            return False
        if "no importa reformar" in text or "aceptamos reforma" in text:
            return True
        return None

    def _llm_enrichment(self, profile: ClientProfile, transcript: str) -> None:
        if not self.llm_client or not self.llm_client.is_ready():
            return
        prompt = (
            "Resume en un párrafo breve las prioridades del cliente para una vivienda "
            "a partir del siguiente texto. Usa un tono profesional en español.\n\n"
            f"Transcripción:\n{transcript}"
        )
        summary = self.llm_client.complete(prompt)
        if summary:
            profile.comentarios_adicionales = summary


def profiles_to_dataframe(profiles: Iterable[ClientProfile]) -> pd.DataFrame:
    return pd.DataFrame([asdict(profile) for profile in profiles])
