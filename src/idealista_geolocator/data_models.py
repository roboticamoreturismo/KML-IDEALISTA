"""Modelos de datos compartidos por los distintos pasos del sistema."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PropertyRecord:
    """Representa una propiedad a lo largo del flujo de procesamiento.

    Los campos cubren toda la información solicitada en los pasos 1 a 5. Se
    inicializan con valores básicos para evitar errores cuando un paso todavía
    no ha rellenado un dato determinado.
    """

    id_interno: str
    titulo: str = ""
    direccion_detectada: str = ""
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    url_anuncio: str = ""
    precio_total: Optional[float] = None
    precio_m2: Optional[float] = None
    superficie_m2: Optional[float] = None
    habitaciones: Optional[int] = None
    descripcion_limpia: str = ""
    tipo_vivienda: str = ""
    estado_general: str = ""
    imagenes: List[str] = field(default_factory=list)
    ubicacion_inferida: str = ""
    fuente_geolocalizacion: str = ""
    nivel_precision_ubicacion: str = ""
    # Campos enriquecidos en paso 2
    agencia: str = ""
    telefono: str = ""
    fecha_publicacion: str = ""
    caracteristicas_extra: Dict[str, str] = field(default_factory=dict)
    clasificacion_imagenes: Dict[str, str] = field(default_factory=dict)
    entorno_visual: str = ""
    luminosidad_media: Optional[float] = None
    # Campos del paso 3
    entorno_servicios: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    clasificacion_zona: Dict[str, str] = field(default_factory=dict)
    distancias_relevantes: Dict[str, float] = field(default_factory=dict)
    # Paso 5
    afinidad: Optional[int] = None
    afinidad_porcentaje: Optional[float] = None
    justificacion_afinidad: str = ""
    propuestas_mejora: List[str] = field(default_factory=list)
    requiere_revision: bool = False
    motivos_revision: List[str] = field(default_factory=list)


@dataclass
class ClientProfile:
    """Estructura que resume el análisis del cliente (paso 4)."""

    nombre_cliente: str
    nivel_decision: str = ""
    motivaciones: List[str] = field(default_factory=list)
    flexibilidad: str = ""
    estilo_comunicacion: str = ""
    prioridades_emocionales: List[str] = field(default_factory=list)
    tipo_vivienda: List[str] = field(default_factory=list)
    habitaciones_min: Optional[int] = None
    banos_min: Optional[int] = None
    superficie_min: Optional[float] = None
    caracteristicas_deseadas: List[str] = field(default_factory=list)
    orientacion_preferida: List[str] = field(default_factory=list)
    ubicaciones_preferidas: List[str] = field(default_factory=list)
    presupuesto_max: Optional[float] = None
    acepta_reformas: Optional[bool] = None
    comentarios_adicionales: str = ""
    fecha_analisis: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MatchResult:
    """Resultado del cruce entre una propiedad y el perfil del cliente."""

    id_interno: str
    afinidad: int
    afinidad_porcentaje: float
    coincidencias: Dict[str, str]
    discrepancias: Dict[str, str]
    justificacion: str
    propuestas_mejora: List[str]


@dataclass
class ExportResult:
    """Resultado de la exportación de ficheros del paso 6."""

    carpeta: Path
    excel_path: Path
    resumen_json_path: Path
    kml_path: Optional[Path] = None
