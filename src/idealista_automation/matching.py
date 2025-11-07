"""Lógica de matching entre cliente e inmuebles."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .data_models import ClientProfile, MatchResult


def _puntuacion_simple(condicion: bool, valor_true: int = 5, valor_false: int = 1) -> int:
    return valor_true if condicion else valor_false


def _comparar_precio(precio: float, maximo: float) -> int:
    if precio <= maximo:
        return 5
    exceso = (precio - maximo) / maximo
    if exceso <= 0.1:
        return 4
    if exceso <= 0.2:
        return 3
    if exceso <= 0.3:
        return 2
    return 1


def _comparar_superficie(ofrecida: float, requerida: float) -> int:
    if ofrecida >= requerida:
        return 5
    deficit = (requerida - ofrecida) / requerida
    if deficit <= 0.1:
        return 4
    if deficit <= 0.2:
        return 3
    if deficit <= 0.3:
        return 2
    return 1


def _calcular_porcentaje(puntuaciones: List[int]) -> float:
    return round(sum(puntuaciones) / (len(puntuaciones) * 5) * 100, 2)


def _redondear_indice(porcentaje: float) -> int:
    if porcentaje >= 90:
        return 5
    if porcentaje >= 75:
        return 4
    if porcentaje >= 60:
        return 3
    if porcentaje >= 40:
        return 2
    return 1


def evaluar_propiedad(propiedad: Dict, cliente: ClientProfile) -> MatchResult:
    puntuaciones = {}

    tipo_match = cliente.tipologia and propiedad.get("tipo_inmueble")
    puntuaciones["af_tipo_vivienda"] = _puntuacion_simple(
        tipo_match and cliente.tipologia.lower() in propiedad.get("tipo_inmueble", "").lower()
    ) if cliente.tipologia else 3

    zona_match = cliente.ubicacion_preferida and propiedad.get("barrio")
    puntuaciones["af_zona"] = _puntuacion_simple(
        zona_match and cliente.ubicacion_preferida.lower() in propiedad.get("direccion_completa", "").lower()
    ) if cliente.ubicacion_preferida else 3

    precio = propiedad.get("precio_eur")
    if precio and cliente.presupuesto_max:
        puntuaciones["af_precio"] = _comparar_precio(precio, cliente.presupuesto_max)
    else:
        puntuaciones["af_precio"] = 3

    sup_util = propiedad.get("sup_util_m2") or propiedad.get("sup_construida_m2")
    if sup_util and cliente.superficie_util_min:
        puntuaciones["af_sup_util"] = _comparar_superficie(sup_util, cliente.superficie_util_min)
    else:
        puntuaciones["af_sup_util"] = 3

    dormitorios = propiedad.get("dormitorios")
    if dormitorios and cliente.dormitorios_min:
        puntuaciones["af_dorm"] = _puntuacion_simple(dormitorios >= cliente.dormitorios_min, 5, 2)
    else:
        puntuaciones["af_dorm"] = 3

    banos = propiedad.get("banos")
    if banos and cliente.banos_min:
        puntuaciones["af_banos"] = _puntuacion_simple(banos >= cliente.banos_min, 5, 2)
    else:
        puntuaciones["af_banos"] = 3

    estado = propiedad.get("estado_conservacion")
    if estado and cliente.estado_preferido:
        puntuaciones["af_estado"] = _puntuacion_simple(cliente.estado_preferido.lower() in estado.lower(), 5, 2)
    else:
        puntuaciones["af_estado"] = 3

    if cliente.caracteristicas_clave:
        coincidencias = sum(
            1 for car in cliente.caracteristicas_clave if car.lower() in (propiedad.get("desc_breve", "").lower())
        )
        ratio = coincidencias / len(cliente.caracteristicas_clave)
        if ratio >= 1:
            puntuaciones["af_features"] = 5
        elif ratio >= 0.5:
            puntuaciones["af_features"] = 4
        elif ratio > 0:
            puntuaciones["af_features"] = 3
        else:
            puntuaciones["af_features"] = 1
    else:
        puntuaciones["af_features"] = 3

    orientacion = propiedad.get("orientacion")
    if orientacion and cliente.accesibilidad:
        puntuaciones["af_orientacion"] = 4
    else:
        puntuaciones["af_orientacion"] = 3

    if cliente.eficiencia_costes:
        puntuaciones["af_eficiencia_costes"] = 3
    else:
        puntuaciones["af_eficiencia_costes"] = 3

    porcentaje = _calcular_porcentaje(list(puntuaciones.values()))
    indice = _redondear_indice(porcentaje)

    mejoras = []
    if puntuaciones["af_precio"] <= 3 and cliente.presupuesto_max and precio:
        mejoras.append("Negociar precio o valorar financiación adicional")
    if puntuaciones["af_sup_util"] <= 3 and cliente.superficie_util_min:
        mejoras.append("Revisar opciones de ampliación o redistribución")

    justificacion = (
        f"Afinidad global del {porcentaje}%. "
        f"Tipo: {puntuaciones['af_tipo_vivienda']}/5. "
        f"Zona: {puntuaciones['af_zona']}/5. Precio: {puntuaciones['af_precio']}/5."
    )

    return MatchResult(
        property_id=propiedad.get("id_idealista"),
        titulo=propiedad.get("titulo", ""),
        af_tipo_vivienda=puntuaciones["af_tipo_vivienda"],
        af_zona=puntuaciones["af_zona"],
        af_precio=puntuaciones["af_precio"],
        af_sup_util=puntuaciones["af_sup_util"],
        af_dorm=puntuaciones["af_dorm"],
        af_banos=puntuaciones["af_banos"],
        af_estado=puntuaciones["af_estado"],
        af_features=puntuaciones["af_features"],
        af_orientacion=puntuaciones["af_orientacion"],
        af_eficiencia_costes=puntuaciones["af_eficiencia_costes"],
        afinidad_pct=porcentaje,
        afinidad_idx=indice,
        afinidad_justificacion=justificacion,
        afinidad_mejoras="; ".join(mejoras) if mejoras else "",
    )


def generar_tabla_matching(propiedades: List[Dict], cliente: ClientProfile) -> pd.DataFrame:
    resultados = [evaluar_propiedad(propiedad, cliente).__dict__ for propiedad in propiedades]
    return pd.DataFrame(resultados)
