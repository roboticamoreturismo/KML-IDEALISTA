"""Reglas heurísticas para enriquecer la información de los inmuebles."""
from __future__ import annotations

import re
from typing import Dict, List, Optional


def extraer_bullets(descripcion: str) -> List[str]:
    """Convierte el texto libre en viñetas destacadas."""
    if not descripcion:
        return []
    frases = re.split(r"(?<=[.!?])\s+", descripcion.strip())
    bullets = [f"• {frase.strip()}" for frase in frases if frase]
    return bullets[:7]


def detectar_sotano(texto: str) -> Optional[bool]:
    if not texto:
        return None
    texto = texto.lower()
    if "sótano" in texto or "sotano" in texto or "semisótano" in texto:
        return True
    return None


def inferir_orientacion(texto: str) -> Optional[str]:
    if not texto:
        return None
    texto = texto.lower()
    orientaciones = {
        "norte": "N",
        "sur": "S",
        "este": "E",
        "oeste": "O",
        "sureste": "SE",
        "suroeste": "SO",
        "noreste": "NE",
        "noroeste": "NO",
    }
    encontrados = [abreviatura for clave, abreviatura in orientaciones.items() if clave in texto]
    if not encontrados:
        return None
    return "/".join(sorted(set(encontrados)))


def inferir_estado(texto: str) -> Optional[str]:
    if not texto:
        return None
    texto = texto.lower()
    if any(p in texto for p in ["reformar", "obra", "rehabilitar"]):
        return "A reformar"
    if any(p in texto for p in ["estrenar", "nuevo"]):
        return "A estrenar"
    if any(p in texto for p in ["perfecto estado", "impecable", "lista para entrar"]):
        return "Entrar a vivir"
    return None


def inferir_entorno(descripcion: str) -> Dict[str, Optional[str]]:
    descripcion_lower = descripcion.lower() if descripcion else ""
    proximidades = []
    if "universidad" in descripcion_lower or "ual" in descripcion_lower:
        proximidades.append("Cerca de la Universidad de Almería")
    if any(palabra in descripcion_lower for palabra in ["mar", "playa", "costa"]):
        proximidades.append("Cercanía al mar")
    if "servicios" in descripcion_lower:
        proximidades.append("Servicios cercanos")
    entorno_tipo = None
    if any(palabra in descripcion_lower for palabra in ["tranquil", "residencial"]):
        entorno_tipo = "Zona tranquila"
    if "urbano" in descripcion_lower:
        entorno_tipo = "Entorno urbano"
    if "rural" in descripcion_lower or "campo" in descripcion_lower:
        entorno_tipo = "Entorno rural"

    tiempo_capital = None
    match = re.search(r"a\s*(\d+)\s*min\b.*?almer[ií]a", descripcion_lower)
    if match:
        tiempo_capital = f"{match.group(1)} min a Almería"

    luminosidad = None
    if "luminos" in descripcion_lower:
        luminosidad = "Alta"
    elif "oscuro" in descripcion_lower:
        luminosidad = "Baja"

    return {
        "entorno_proximidades": "; ".join(proximidades) if proximidades else None,
        "entorno_tiempo_capital": tiempo_capital,
        "entorno_tipo": entorno_tipo,
        "luminosidad_nivel": luminosidad,
    }


def inferir_caracteristicas_extra(descripcion: str) -> Dict[str, Optional[str]]:
    descripcion_lower = descripcion.lower() if descripcion else ""
    redistribucion = None
    if "redistrib" in descripcion_lower or "dividir" in descripcion_lower:
        redistribucion = "Posibilidad de redistribución"

    elementos = []
    if "parcela" in descripcion_lower:
        elementos.append("Parcela")
    if "terraza" in descripcion_lower:
        elementos.append("Terraza")
    if "jardín" in descripcion_lower or "jardin" in descripcion_lower:
        elementos.append("Jardín")

    caracteristicas = []
    if "mármol" in descripcion_lower:
        caracteristicas.append("Suelos de mármol")
    if "climalit" in descripcion_lower:
        caracteristicas.append("Carpintería Climalit")

    uso = None
    if "restaurante" in descripcion_lower or "negocio" in descripcion_lower:
        uso = "Uso mixto residencial + negocio"

    return {
        "redistribucion_posible": redistribucion,
        "elementos_edificio": "; ".join(elementos) if elementos else None,
        "caracteristicas_extra": "; ".join(caracteristicas) if caracteristicas else None,
        "uso_actividad": uso,
    }
