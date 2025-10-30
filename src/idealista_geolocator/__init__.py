"""Módulo principal del sistema Geolocalizador Idealista para Google Earth.

Este paquete agrupa utilidades para procesar textos de anuncios inmobiliarios,
obtener coordenadas aproximadas, analizar el entorno y generar archivos para su
uso en Google Earth y hojas de cálculo. Cada submódulo representa un paso del
flujo descrito en la documentación del proyecto.
"""

from .config import settings
from .data_models import ExportResult, PropertyRecord, ClientProfile, MatchResult
from .step1_property_extractor import PropertyExtractor
from .step2_enrichment import PropertyEnricher
from .step3_environment import EnvironmentAnalyzer
from .step4_client_analysis import ClientAnalyzer
from .step5_matching import MatchingEngine
from .step6_export import Exporter

__all__ = [
    "PropertyRecord",
    "ClientProfile",
    "MatchResult",
    "ExportResult",
    "PropertyExtractor",
    "PropertyEnricher",
    "EnvironmentAnalyzer",
    "ClientAnalyzer",
    "MatchingEngine",
    "Exporter",
    "settings",
]
