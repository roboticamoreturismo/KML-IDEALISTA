"""Implementación del Paso 5: matching entre cliente y propiedades."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .data_models import ClientProfile, MatchResult, PropertyRecord

LOGGER = logging.getLogger(__name__)


class MatchingEngine:
    """Calcula la afinidad entre un perfil de cliente y varias propiedades."""

    def match(self, client: ClientProfile, properties: Iterable[PropertyRecord]) -> List[MatchResult]:
        results: List[MatchResult] = []
        for record in properties:
            score, percentage, coincidences, discrepancies, proposals = self._score_property(client, record)
            justification = self._build_justification(coincidences, discrepancies)
            record.afinidad = score
            record.afinidad_porcentaje = percentage
            record.justificacion_afinidad = justification
            record.propuestas_mejora = proposals
            results.append(
                MatchResult(
                    id_interno=record.id_interno,
                    afinidad=score,
                    afinidad_porcentaje=percentage,
                    coincidencias=coincidences,
                    discrepancias=discrepancies,
                    justificacion=justification,
                    propuestas_mejora=proposals,
                )
            )
        return results

    def to_dataframe(self, results: Iterable[MatchResult]) -> pd.DataFrame:
        return pd.DataFrame([result.__dict__ for result in results])

    def _score_property(
        self,
        client: ClientProfile,
        property_record: PropertyRecord,
    ) -> Tuple[int, float, Dict[str, str], Dict[str, str], List[str]]:
        checks: Dict[str, bool] = {}
        coincidences: Dict[str, str] = {}
        discrepancies: Dict[str, str] = {}
        proposals: List[str] = []

        if client.tipo_vivienda:
            match_type = property_record.tipo_vivienda in client.tipo_vivienda
            checks["tipo_vivienda"] = match_type
            if match_type:
                coincidences["tipo_vivienda"] = property_record.tipo_vivienda
            else:
                discrepancies["tipo_vivienda"] = property_record.tipo_vivienda or "desconocido"

        if client.habitaciones_min is not None:
            matches_rooms = (property_record.habitaciones or 0) >= client.habitaciones_min
            checks["habitaciones"] = matches_rooms
            if matches_rooms:
                coincidences["habitaciones"] = str(property_record.habitaciones)
            else:
                discrepancies["habitaciones"] = f"Tiene {property_record.habitaciones}"
                proposals.append("Valorar ampliación o redistribución para añadir dormitorios.")

        if client.banos_min is not None:
            actual_bathrooms = property_record.caracteristicas_extra.get("banos") or property_record.caracteristicas_extra.get("baños")
            if actual_bathrooms:
                actual = int(actual_bathrooms)
            else:
                actual = property_record.caracteristicas_extra.get("banos_detalle", client.banos_min)
                actual = int(actual) if isinstance(actual, (int, str)) and str(actual).isdigit() else client.banos_min
            matches_bath_bool = actual >= client.banos_min
            checks["baños"] = matches_bath_bool
            if matches_bath_bool:
                coincidences["baños"] = str(actual)
            else:
                discrepancies["baños"] = f"Tiene {actual}" if actual else "No especificado"

        if client.superficie_min is not None:
            surface = property_record.superficie_m2 or 0
            meets_surface = surface >= client.superficie_min
            checks["superficie"] = meets_surface
            if meets_surface:
                coincidences["superficie"] = f"{surface} m²"
            else:
                discrepancies["superficie"] = f"{surface} m²"
                proposals.append("Estudiar ampliación o descartar si la superficie es crítica.")

        if client.presupuesto_max is not None and property_record.precio_total is not None:
            within_budget = property_record.precio_total <= client.presupuesto_max
            checks["presupuesto"] = within_budget
            if within_budget:
                coincidences["presupuesto"] = f"{property_record.precio_total} €"
            else:
                discrepancies["presupuesto"] = f"{property_record.precio_total} €"
                proposals.append("Negociar precio o proponer financiación alternativa.")

        if client.caracteristicas_deseadas:
            available_features = set(property_record.caracteristicas_extra.keys())
            match_features = set(client.caracteristicas_deseadas) & available_features
            checks["caracteristicas"] = bool(match_features)
            if match_features:
                coincidences["caracteristicas"] = ", ".join(sorted(match_features))
            else:
                discrepancies["caracteristicas"] = "No se detectaron características destacadas"

        if client.ubicaciones_preferidas and property_record.direccion_detectada:
            match_location = any(zone.lower() in property_record.direccion_detectada.lower() for zone in client.ubicaciones_preferidas)
            checks["ubicacion"] = match_location
            if match_location:
                coincidences["ubicacion"] = property_record.direccion_detectada
            else:
                discrepancies["ubicacion"] = property_record.direccion_detectada

        if client.acepta_reformas is False and property_record.estado_general in {"necesita reforma", "para reformar"}:
            checks["reforma"] = False
            discrepancies["reforma"] = property_record.estado_general
            proposals.append("Buscar alternativas en mejor estado o presupuestar la reforma.")
        elif client.acepta_reformas is True and property_record.estado_general:
            checks["reforma"] = True
            coincidences["reforma"] = property_record.estado_general

        total_checks = len(checks) or 1
        passed_checks = sum(value for value in checks.values())
        percentage = passed_checks / total_checks * 100
        score = self._percentage_to_score(percentage)
        return score, round(percentage, 2), coincidences, discrepancies, proposals

    def _percentage_to_score(self, percentage: float) -> int:
        if percentage >= 90:
            return 5
        if percentage >= 75:
            return 4
        if percentage >= 60:
            return 3
        if percentage >= 40:
            return 2
        return 1

    def _build_justification(self, coincidences: Dict[str, str], discrepancies: Dict[str, str]) -> str:
        parts: List[str] = []
        if coincidences:
            parts.append("Coincidencias: " + "; ".join(f"{key}: {value}" for key, value in coincidences.items()))
        if discrepancies:
            parts.append("Pendientes: " + "; ".join(f"{key}: {value}" for key, value in discrepancies.items()))
        return " | ".join(parts)
