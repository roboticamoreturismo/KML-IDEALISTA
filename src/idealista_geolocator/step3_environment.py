"""Implementación del Paso 3: análisis del entorno geográfico."""

from __future__ import annotations

import importlib
import logging
from typing import Dict, Iterable, List, Optional, Tuple

from geopy.distance import geodesic

from .data_models import PropertyRecord

LOGGER = logging.getLogger(__name__)

_googlemaps_spec = importlib.util.find_spec("googlemaps")
if _googlemaps_spec is not None:
    googlemaps = importlib.import_module("googlemaps")
else:
    googlemaps = None

_osmnx_spec = importlib.util.find_spec("osmnx")
if _osmnx_spec is not None:
    osmnx = importlib.import_module("osmnx")
else:
    osmnx = None

_geopy_spec = importlib.util.find_spec("geopy")
if _geopy_spec is not None:
    from geopy.geocoders import Nominatim
else:
    Nominatim = None  # type: ignore


CATEGORIES = {
    "salud": ["hospital", "clinic", "doctors", "pharmacy"],
    "movilidad": ["bus_station", "train_station", "subway_station", "parking"],
    "educacion": ["school", "university", "kindergarten"],
    "comercio": ["supermarket", "shopping_mall", "store"],
    "ocio_deporte": ["restaurant", "cafe", "gym", "stadium"],
    "naturaleza": ["park", "garden", "beach"],
    "infraestructura": ["police", "fire_station", "city_hall", "courthouse"],
}


class EnvironmentAnalyzer:
    """Calcula servicios cercanos y clasifica el entorno."""

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        geopy_user_agent: str = "idealista-geolocator",
    ) -> None:
        self.google_maps_client = None
        if googlemaps is not None and google_maps_api_key:
            self.google_maps_client = googlemaps.Client(key=google_maps_api_key)
        self.geopy_user_agent = geopy_user_agent

    def analyze(self, records: Iterable[PropertyRecord]) -> List[PropertyRecord]:
        analyzed_records: List[PropertyRecord] = []
        for record in records:
            analyzed_records.append(self.analyze_property(record))
        return analyzed_records

    def analyze_property(self, record: PropertyRecord) -> PropertyRecord:
        if record.latitud is None or record.longitud is None:
            LOGGER.warning("La propiedad %s no tiene coordenadas para analizar el entorno.", record.id_interno)
            return record

        location = (record.latitud, record.longitud)
        entorno = {radius: self._collect_services(location, radius) for radius in (500, 1000, 1500)}
        record.entorno_servicios = self._summarize_services(entorno)
        record.clasificacion_zona = self._classify_zone(record.entorno_servicios)
        record.distancias_relevantes = self._calculate_distances(location, record.direccion_detectada, entorno)
        return record

    def _collect_services(self, location: Tuple[float, float], radius: int) -> Dict[str, List[Dict[str, str]]]:
        services: Dict[str, List[Dict[str, str]]] = {category: [] for category in CATEGORIES}
        if self.google_maps_client is not None:
            for category, types in CATEGORIES.items():
                aggregated: List[Dict[str, str]] = []
                for place_type in types:
                    results = self.google_maps_client.places_nearby(
                        location=location, radius=radius, type=place_type
                    )
                    for result in results.get("results", []):
                        aggregated.append(
                            {
                                "nombre": result.get("name", ""),
                                "direccion": result.get("vicinity", ""),
                                "tipo": place_type,
                            }
                        )
                services[category] = aggregated
            return services

        if osmnx is not None:
            point = (location[0], location[1])
            for category, tags in CATEGORIES.items():
                osm_tags = {"amenity": tags}
                try:
                    gdf = osmnx.features_from_point(point, tags=osm_tags, dist=radius)
                except Exception:  # noqa: BLE001
                    gdf = None
                if gdf is not None and not gdf.empty:
                    services[category] = [
                        {
                            "nombre": row.get("name", ""),
                            "direccion": row.get("addr:street", ""),
                            "tipo": row.get("amenity", ""),
                        }
                        for _, row in gdf.iterrows()
                    ]
        return services

    def _summarize_services(self, raw_services: Dict[int, Dict[str, List[Dict[str, str]]]]) -> Dict[str, List[Dict[str, str]]]:
        summary: Dict[str, List[Dict[str, str]]] = {category: [] for category in CATEGORIES}
        for radius, categories in raw_services.items():
            for category, services in categories.items():
                limited = services[:5]
                for service in limited:
                    service_copy = service.copy()
                    service_copy["radio_m"] = radius
                    summary[category].append(service_copy)
        return summary

    def _classify_zone(self, services: Dict[str, List[Dict[str, str]]]) -> Dict[str, str]:
        counts = {category: len(items) for category, items in services.items()}
        total = sum(counts.values()) or 1
        residential_score = counts["educacion"] + counts["salud"] + counts["naturaleza"]
        commercial_score = counts["comercio"] + counts["ocio_deporte"]
        industrial_score = counts["infraestructura"]

        classification = {
            "predominio": max(
                [
                    ("residencial", residential_score),
                    ("comercial", commercial_score),
                    ("institucional", industrial_score),
                ],
                key=lambda item: item[1],
            )[0],
            "densidad_servicios": "alta" if total > 20 else "media" if total > 8 else "baja",
            "tranquilidad": self._infer_noise_level(counts),
        }
        return classification

    def _infer_noise_level(self, counts: Dict[str, int]) -> str:
        ocio = counts.get("ocio_deporte", 0)
        movilidad = counts.get("movilidad", 0)
        if ocio + movilidad > 15:
            return "muy transitada"
        if ocio + movilidad > 6:
            return "ruidosa"
        if ocio + movilidad > 2:
            return "moderada"
        return "tranquila"

    def _calculate_distances(
        self,
        location: Tuple[float, float],
        address_hint: str,
        collected_services: Dict[int, Dict[str, List[Dict[str, str]]]],
    ) -> Dict[str, float]:
        distances: Dict[str, float] = {}
        if Nominatim is not None and address_hint:
            geolocator = Nominatim(user_agent=self.geopy_user_agent)
            municipality = self._extract_municipality(address_hint)
            if municipality:
                loc = geolocator.geocode(municipality)
                if loc:
                    distances["centro_municipio_km"] = round(
                        geodesic(location, (loc.latitude, loc.longitude)).kilometers, 2
                    )
        for radius, services in collected_services.items():
            distances[f"servicios_{radius}m"] = sum(len(items) for items in services.values())
        return distances

    def _extract_municipality(self, address_hint: str) -> str:
        tokens = address_hint.split(",")
        if len(tokens) > 1:
            return tokens[-1].strip()
        return address_hint
