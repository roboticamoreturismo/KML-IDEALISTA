"""Parser sencillo para sintetizar las necesidades del cliente."""
from __future__ import annotations

import re
from typing import List, Optional

from .data_models import ClientProfile


def _buscar_numero(texto: str, patrones) -> Optional[float]:
    for patron in patrones:
        match = re.search(patron, texto, flags=re.IGNORECASE)
        if match:
            numero = match.group(1).replace(".", "").replace(",", ".")
            try:
                return float(numero)
            except ValueError:
                continue
    return None


def extraer_lista(texto: str, etiquetas: List[str]) -> List[str]:
    encontrados = []
    for etiqueta in etiquetas:
        if re.search(rf"\b{re.escape(etiqueta)}\b", texto, flags=re.IGNORECASE):
            encontrados.append(etiqueta.capitalize())
    return encontrados


def parse_client_profile(nombre: str, texto: str) -> ClientProfile:
    texto = texto or ""
    presupuesto = _buscar_numero(texto, [r"presupuesto\s*(?:máximo|max)?:?\s*(\d+[.,]?\d*)", r"hasta\s*(\d+[.,]?\d*)\s*euros"])
    superficie = _buscar_numero(texto, [r"(\d+[.,]?\d*)\s*m2\s*útil", r"mínimo\s*(\d+[.,]?\d*)\s*m2"])
    dormitorios = _buscar_numero(texto, [r"(\d+)\s*habi?taciones", r"(\d+)\s*dormitorios"])
    banos = _buscar_numero(texto, [r"(\d+)\s*bañ", r"(\d+)\s*wc"])

    ubicacion_match = re.search(r"zona\s*:?\s*([^.\n]+)", texto, flags=re.IGNORECASE)
    ubicacion = ubicacion_match.group(1).strip() if ubicacion_match else None

    finalidad_match = re.search(r"(residencia habitual|segunda residencia|inversión|inversion)", texto, flags=re.IGNORECASE)
    finalidad = finalidad_match.group(1).capitalize() if finalidad_match else None

    tipologia_match = re.search(r"busca\s*(un\s*)?(piso|ático|atico|bajo|adosado|chalet|loft)", texto, flags=re.IGNORECASE)
    tipologia = tipologia_match.group(2).capitalize() if tipologia_match else None

    estado_match = re.search(r"(obra nueva|entrar a vivir|reformar)", texto, flags=re.IGNORECASE)
    estado = estado_match.group(1).capitalize() if estado_match else None

    caracteristicas = extraer_lista(texto, ["terraza", "garaje", "trastero", "ascensor", "piscina", "vistas"])

    accesibilidad_match = re.search(r"(ascensor|planta baja|sin escaleras|accesible)", texto, flags=re.IGNORECASE)
    accesibilidad = accesibilidad_match.group(1) if accesibilidad_match else None

    eficiencia_match = re.search(r"(certificación energética [A-G]|gastos de comunidad [^.,\n]+)", texto, flags=re.IGNORECASE)
    eficiencia = eficiencia_match.group(1) if eficiencia_match else None

    plazos_match = re.search(r"(hipoteca[^.,\n]+|cierre[^.,\n]+|urgencia[^.,\n]+)", texto, flags=re.IGNORECASE)
    plazos = plazos_match.group(1) if plazos_match else None

    return ClientProfile(
        nombre=nombre,
        presupuesto_max=presupuesto,
        ubicacion_preferida=ubicacion,
        finalidad=finalidad,
        tipologia=tipologia,
        superficie_util_min=superficie,
        dormitorios_min=int(dormitorios) if dormitorios else None,
        banos_min=int(banos) if banos else None,
        estado_preferido=estado,
        caracteristicas_clave=caracteristicas,
        accesibilidad=accesibilidad,
        eficiencia_costes=eficiencia,
        plazos_financiacion=plazos,
    )
