"""Utilidades para normalizar direcciones según nomenclatura española."""

from __future__ import annotations

import re
from typing import Dict

from unidecode import unidecode


NOMENCLATURE_GROUPS = {
    "calle": [
        "calle",
        "callejon",
        "calleja",
        "callecita",
        "callejilla",
        "callejuela",
        "callejon sin salida",
        "calle secundaria",
        "calle principal",
        "calle peatonal",
        "calle vieja",
        "calle nueva",
        "calle en cuesta",
        "calle adoquinada",
        "calle asfaltada",
        "calle de tierra",
        "calle urbana",
        "calle de montana",
        "calle interurbanas",
    ],
    "avenida": [
        "avenida",
        "avda",
        "av.",
        "avenidita",
        "avenidas principales",
        "avenida principal",
        "avenida arbolada",
    ],
    "bulevar": ["bulevar", "bulevarcito"],
    "paseo": [
        "paseo",
        "paseito",
        "paseillo",
        "paseadero",
        "paseo peatonal",
        "paseo arbolado",
        "paseo maritimo",
        "paseo central",
    ],
    "carretera": [
        "carretera",
        "carreterita",
        "ctra",
        "autopista",
        "autovia",
        "via rapida",
        "circunvalacion",
        "ronda",
        "ramal",
        "acceso",
        "bajada",
        "subida",
        "cuesta",
    ],
    "camino": [
        "camin",
        "camino",
        "caminico",
        "camino rural",
        "camino forestal",
        "vereda",
        "sendero",
        "senda",
        "trocha",
        "trochito",
        "veredita",
        "vereda real",
        "camino urbano",
    ],
    "plaza": ["plaza", "plazoleta", "plazuela", "explanada"],
    "parque": [
        "parque",
        "parquecito",
        "parquecillo",
        "zona verde",
        "jardin",
        "jardincillo",
    ],
    "urbanizacion": [
        "urbanizacion",
        "urba",
        "barriada",
        "barrio",
        "sector",
        "residencial",
        "comunidad",
        "conjunto residencial",
    ],
    "municipio": [
        "municipio",
        "ayuntamiento",
        "ciudad",
        "localidad",
        "pueblo",
        "villa",
        "aldea",
        "caserio",
        "nucl",
        "region",
        "comarca",
    ],
    "numero": [
        "numero",
        "num",
        "portal",
        "entrada",
        "planta",
        "piso",
        "puerta",
        "letra",
    ],
    "playa": ["playa", "playita", "cala", "caleta", "bahia", "ensenada"],
    "puerto": ["puerto", "muelle", "embarcadero", "darsena", "espigon"],
}


class AddressNormalizer:
    """Limpia y homogeneiza cadenas de dirección."""

    def __init__(self) -> None:
        self.replacements: Dict[str, str] = {}
        for canonical, variants in NOMENCLATURE_GROUPS.items():
            for variant in variants:
                normalized = unidecode(variant.lower())
                self.replacements[normalized] = canonical

    def normalize(self, raw_address: str) -> str:
        if not raw_address:
            return ""
        work = unidecode(raw_address.lower())
        work = re.sub(r"[,;]", " ", work)
        work = re.sub(r"\s+", " ", work)
        tokens = work.split()
        cleaned_tokens = []
        for token in tokens:
            replacement = self.replacements.get(token, token)
            cleaned_tokens.append(replacement)
        normalized = " ".join(cleaned_tokens)
        normalized = re.sub(r"\b(\d{1,5})\b", r" \1", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized.title()

    def detect_precision_hint(self, address: str) -> str:
        lowered = unidecode(address.lower())
        if re.search(r"\b\d{1,5}\b", lowered):
            return "alta"
        if any(keyword in lowered for keyword in ["calle", "avenida", "plaza", "camino"]):
            return "media"
        if any(keyword in lowered for keyword in ["barrio", "zona", "urbanizacion", "sector"]):
            return "media"
        if any(keyword in lowered for keyword in ["municipio", "ciudad", "pueblo", "provincia"]):
            return "baja"
        return "baja"

