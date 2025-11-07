"""Funciones de parsing y limpieza de datos de Idealista."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd

PREFIJO_MAP = {
    "c": "Calle",
    "c/": "Calle",
    "c.": "Calle",
    "calle": "Calle",
    "av": "Avenida",
    "av.": "Avenida",
    "avda": "Avenida",
    "avda.": "Avenida",
    "avd": "Avenida",
    "avenida": "Avenida",
}

PREPOSICIONES = {"de", "del", "la", "las", "los", "y", "el", "san", "santa"}


def _title_case_via(nombre: str) -> str:
    palabras = nombre.strip().split()
    normalizadas = []
    for palabra in palabras:
        palabra_base = palabra.lower()
        if palabra_base in PREPOSICIONES:
            normalizadas.append(palabra_base)
        else:
            normalizadas.append(palabra.capitalize())
    return " ".join(normalizadas)


def split_tipo_y_direccion(titulo: str) -> Tuple[Optional[str], Optional[str]]:
    """Separa el tipo de inmueble de la parte "en ..." del título."""
    if " en " not in titulo.lower():
        return titulo.strip(), None
    partes = re.split(r"\s+en\s+", titulo, flags=re.IGNORECASE)
    tipo = partes[0].strip()
    direccion = " en ".join(partes[1:]).strip()
    return tipo or None, direccion or None


def normalizar_prefijo(via: str) -> Tuple[Optional[str], str]:
    """Normaliza el prefijo de la vía y devuelve (prefijo, resto)."""
    via = via.strip()
    if not via:
        return None, ""
    match = re.match(r"([\w./]+)\s+(.*)", via)
    if match:
        prefijo_raw = match.group(1).lower().strip("./")
        resto = match.group(2).strip()
        prefijo = PREFIJO_MAP.get(prefijo_raw, prefijo_raw.capitalize())
        return prefijo, resto
    return None, via


def extraer_numero_via(texto: str) -> Tuple[str, Optional[str]]:
    """Extrae el número de portal si está presente."""
    match = re.search(r"(.*?)(\d+[a-zA-Z]?|s/?n)\b", texto)
    if match:
        nombre = match.group(1).strip(", -")
        numero = match.group(2).replace("/", "").lower()
        if numero == "sn":
            numero = "s/n"
        return nombre.strip(), numero
    return texto.strip(), None


def parse_direccion(desde_titulo: Optional[str], descripcion: str) -> Dict[str, Optional[str]]:
    """Construye la dirección completa usando el título y la descripción."""
    if not desde_titulo:
        return {key: None for key in [
            "via_prefijo",
            "via_nombre",
            "via_numero",
            "barrio",
            "ciudad",
            "provincia",
            "cp",
            "direccion_completa",
        ]}

    partes = [p.strip() for p in desde_titulo.split(",") if p.strip()]
    via_raw = partes[0] if partes else ""
    prefijo, resto_via = normalizar_prefijo(via_raw)
    via_nombre, numero = extraer_numero_via(resto_via)
    via_nombre = _title_case_via(via_nombre)

    barrio = partes[1] if len(partes) > 1 else None
    ciudad = partes[-2] if len(partes) > 2 else (partes[1] if len(partes) > 1 else None)
    provincia = partes[-1] if len(partes) > 1 else ciudad

    cp = inferir_cp(barrio, ciudad, provincia, descripcion)

    segmentos = [
        "{}".format(f"{prefijo} {via_nombre}".strip()) if prefijo or via_nombre else None,
        numero,
        barrio,
        ciudad,
        provincia,
        cp,
    ]
    direccion_completa = ", ".join([seg for seg in segmentos if seg]) or None

    return {
        "via_prefijo": prefijo,
        "via_nombre": via_nombre or None,
        "via_numero": numero,
        "barrio": barrio,
        "ciudad": ciudad,
        "provincia": provincia,
        "cp": cp,
        "direccion_completa": direccion_completa,
    }


def inferir_cp(barrio: Optional[str], ciudad: Optional[str], provincia: Optional[str], descripcion: str) -> Optional[str]:
    """Heurísticas básicas para deducir códigos postales conocidos."""
    if not ciudad or not provincia:
        return None
    clave = f"{barrio}-{ciudad}-{provincia}".lower()
    if "almería" in clave and barrio and "cañada" in barrio.lower():
        return "04120"
    match = re.search(r"\b(\d{5})\b", descripcion)
    if match:
        return match.group(1)
    return None


def extraer_id_desde_url(url: Optional[str]) -> Optional[int]:
    if not url:
        return None
    match = re.search(r"inmueble/(\d+)/?", url)
    if match:
        return int(match.group(1))
    return None


def limpiar_precio(valor: Optional[str]) -> Optional[float]:
    if not valor:
        return None
    solo_num = re.sub(r"[^0-9]", "", valor)
    return float(solo_num) if solo_num else None


def limpiar_superficie(valor: Optional[str]) -> Optional[float]:
    if not valor:
        return None
    match = re.search(r"(\d+[.,]?\d*)", valor)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def limpiar_entero(valor: Optional[str]) -> Optional[int]:
    if not valor:
        return None
    match = re.search(r"(\d+)", valor)
    if match:
        return int(match.group(1))
    return None


def limpiar_bool_texto(valor: Optional[str]) -> Optional[bool]:
    if not valor:
        return None
    valor_lower = valor.lower()
    if any(palabra in valor_lower for palabra in ["incluido", "sí", "si"]):
        return True
    if any(palabra in valor_lower for palabra in ["no", "sin"]):
        return False
    return None


def parse_fecha_publicacion(texto: Optional[str]) -> Optional[pd.Timestamp]:
    if not texto:
        return None
    for patron in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return pd.to_datetime(datetime.strptime(texto, patron))
        except ValueError:
            continue
    try:
        return pd.to_datetime(texto)
    except (ValueError, TypeError):
        return None


def extraer_coordenadas(map_src: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Obtiene latitud/longitud a partir del src del mapa estático de Idealista."""
    if not map_src:
        return None, None
    match = re.search(r"center=(-?\d+\.\d+),(-?\d+\.\d+)", map_src)
    if match:
        return float(match.group(1)), float(match.group(2))
    match = re.search(r"markers=(-?\d+\.\d+),(-?\d+\.\d+)", map_src)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura que el DataFrame de entrada contenga las columnas esperadas."""
    df = df.copy()
    df.columns = [col.strip() for col in df.columns]
    return df
