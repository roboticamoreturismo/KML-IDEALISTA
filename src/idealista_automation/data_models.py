"""Modelos de datos tipados utilizados por la automatización de Idealista.

Estos modelos permiten que el resto del código sea más expresivo y
mantenible, evitando depender de estructuras de datos genéricas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class PropertyRecord:
    """Representa la información enriquecida de un inmueble.

    Los campos cubren tanto los datos obtenidos del scraping como la
    información generada a partir de reglas heurísticas o análisis NLP.
    """

    # Identificación y enlaces
    id_idealista: Optional[int]
    titulo: str
    tipo_inmueble: Optional[str]
    link_anuncio: Optional[str]
    link_video: Optional[str]
    img_principal: Optional[str]
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Dirección y localización
    via_prefijo: Optional[str]
    via_nombre: Optional[str]
    via_numero: Optional[str]
    barrio: Optional[str]
    ciudad: Optional[str]
    provincia: Optional[str]
    cp: Optional[str]
    direccion_completa: Optional[str]
    precision_ubicacion: Optional[str]

    # Precios y superficies
    precio_eur: Optional[float]
    sup_construida_m2: Optional[float]
    sup_util_m2: Optional[float]
    sup_parcela_m2: Optional[float]
    precio_m2: Optional[float]

    # Programa y características
    dormitorios: Optional[int]
    banos: Optional[int]
    garaje_incluido: Optional[bool]
    garaje_capacidad: Optional[int]
    sotano: Optional[bool]
    plantas: Optional[str]
    orientacion: Optional[str]
    estado_conservacion: Optional[str]
    etiquetas_estado: Optional[str]
    necesidad_reforma: Optional[str]
    composicion_estancias: Optional[str]
    elementos_edificio: Optional[str]
    caracteristicas_extra: Optional[str]

    # Medios y contenido
    fotos_num: Optional[int]
    desc_breve: Optional[str]
    desc_bullets: List[str] = field(default_factory=list)

    # Cronología y agencia
    agencia_nombre: Optional[str]
    fecha_publicacion: Optional[date]
    anio_construccion: Optional[str]
    uso_actividad: Optional[str]
    redistribucion_posible: Optional[str]
    n_viviendas_finca: Optional[int]
    invernadero: Optional[str]

    # Entorno
    entorno_proximidades: Optional[str]
    entorno_tiempo_capital: Optional[str]
    entorno_tipo: Optional[str]
    luminosidad_nivel: Optional[str]


@dataclass
class ClientProfile:
    """Perfil sintetizado del cliente comprador."""

    nombre: str
    presupuesto_max: Optional[float]
    ubicacion_preferida: Optional[str]
    finalidad: Optional[str]
    tipologia: Optional[str]
    superficie_util_min: Optional[float]
    dormitorios_min: Optional[int]
    banos_min: Optional[int]
    estado_preferido: Optional[str]
    caracteristicas_clave: List[str]
    accesibilidad: Optional[str]
    eficiencia_costes: Optional[str]
    plazos_financiacion: Optional[str]


@dataclass
class MatchResult:
    """Resultado de la comparación entre un inmueble y el perfil de cliente."""

    property_id: Optional[int]
    titulo: str
    af_tipo_vivienda: int
    af_zona: int
    af_precio: int
    af_sup_util: int
    af_dorm: int
    af_banos: int
    af_estado: int
    af_features: int
    af_orientacion: int
    af_eficiencia_costes: int
    afinidad_pct: float
    afinidad_idx: int
    afinidad_justificacion: str
    afinidad_mejoras: str


__all__ = [
    "PropertyRecord",
    "ClientProfile",
    "MatchResult",
]
