"""Implementación del Paso 1: extracción estructurada y geolocalización inicial."""

from __future__ import annotations

import importlib
import logging
import re
import uuid
from dataclasses import asdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from unidecode import unidecode

from .address_normalizer import AddressNormalizer
from .config import settings
from .data_models import PropertyRecord

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

_googlemaps_spec = importlib.util.find_spec("googlemaps")
if _googlemaps_spec is not None:
    googlemaps = importlib.import_module("googlemaps")
else:
    googlemaps = None

_geopy_spec = importlib.util.find_spec("geopy")
if _geopy_spec is not None:
    geopy = importlib.import_module("geopy")
    try:
        from geopy.geocoders import Bing, Nominatim
    except ImportError:  # pragma: no cover - dependiente de versión
        Bing = None  # type: ignore
        Nominatim = None  # type: ignore
else:
    geopy = None
    Nominatim = None  # type: ignore
    Bing = None  # type: ignore

_osmnx_spec = importlib.util.find_spec("osmnx")
if _osmnx_spec is not None:
    osmnx = importlib.import_module("osmnx")
else:
    osmnx = None


class PropertyExtractor:
    """Procesa texto libre y genera registros estructurados con geolocalización."""

    def __init__(
        self,
        google_maps_api_keys: Optional[List[str]] = None,
        bing_maps_api_keys: Optional[List[str]] = None,
        geopy_user_agent: str = "idealista-geolocator",
    ) -> None:
        self.address_normalizer = AddressNormalizer()
        self.geopy_user_agent = geopy_user_agent
        self.google_api_keys = google_maps_api_keys or settings.google_maps_keys.keys
        self.bing_api_keys = bing_maps_api_keys or settings.bing_maps_keys.keys
        self.google_clients = [
            googlemaps.Client(key=api_key)
            for api_key in self.google_api_keys
            if googlemaps is not None and api_key
        ]
        self.bing_geocoders = [
            Bing(api_key=api_key)  # type: ignore[misc]
            for api_key in self.bing_api_keys
            if Bing is not None and api_key
        ]
        self.catastro_base_url = settings.catastro_base_url
        self.catastro_token = settings.catastro_token
        self.http_session = requests.Session()

    def parse_properties(self, raw_text: str) -> Tuple[List[PropertyRecord], pd.DataFrame]:
        """Convierte un bloque de texto en registros estructurados.

        Parameters
        ----------
        raw_text:
            Texto pegado por el usuario con varias propiedades.

        Returns
        -------
        Tuple[List[PropertyRecord], pd.DataFrame]
            Lista de dataclasses y un DataFrame listo para exportar.
        """

        chunks = self._split_properties(raw_text)
        records: List[PropertyRecord] = []
        for chunk in chunks:
            metadata = self._extract_metadata(chunk)
            record = self._build_record(metadata)
            record = self._infer_location(record)
            record.descripcion_limpia = metadata.get("descripcion", "").strip()
            records.append(record)

        df = pd.DataFrame([asdict(record) for record in records])
        return records, df

    def export_json(self, records: Iterable[PropertyRecord], output_path: str) -> None:
        """Guarda los registros en formato JSON legible."""

        payload = [asdict(record) for record in records]
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(payload, json_file, ensure_ascii=False, indent=2)
        LOGGER.info("Archivo JSON creado en %s", output_path)

    def _split_properties(self, raw_text: str) -> List[str]:
        """Divide el texto original en bloques por propiedad."""

        sanitized = raw_text.replace("\r", "\n")
        blocks = [block.strip() for block in sanitized.split("\n\n") if block.strip()]
        LOGGER.debug("%s bloques detectados", len(blocks))
        return blocks

    def _extract_metadata(self, block: str) -> Dict[str, str]:
        """Extrae campos básicos usando expresiones regulares heurísticas."""

        metadata: Dict[str, str] = {}
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        url_pattern = re.compile(r"https?://\S+")
        price_pattern = re.compile(r"([0-9]{1,3}(?:[\.\s][0-9]{3})*)(?:\s*€)?", re.IGNORECASE)
        surface_pattern = re.compile(r"(\d+[\.,]?\d*)\s*m²", re.IGNORECASE)
        rooms_pattern = re.compile(r"(\d+)\s*h[ai]b", re.IGNORECASE)
        price_m2_pattern = re.compile(r"(\d+[\.,]?\d*)\s*€/m²", re.IGNORECASE)

        metadata["imagenes"] = []
        for line in lines:
            if not metadata.get("url_anuncio"):
                url_match = url_pattern.search(line)
                if url_match:
                    metadata["url_anuncio"] = url_match.group(0)
                    continue

            if "€" in line and not metadata.get("precio_total"):
                price_match = price_pattern.search(line.replace(",", "."))
                if price_match:
                    metadata["precio_total"] = price_match.group(1)

            if "€/m" in line and not metadata.get("precio_m2"):
                pm2_match = price_m2_pattern.search(line.replace(",", "."))
                if pm2_match:
                    metadata["precio_m2"] = pm2_match.group(1)

            if "m²" in line and not metadata.get("superficie_m2"):
                surface_match = surface_pattern.search(line.replace(",", "."))
                if surface_match:
                    metadata["superficie_m2"] = surface_match.group(1)

            if re.search(r"hab\.", line, re.IGNORECASE) and not metadata.get("habitaciones"):
                rooms_match = rooms_pattern.search(line)
                if rooms_match:
                    metadata["habitaciones"] = rooms_match.group(1)

            if any(keyword in line.lower() for keyword in ["http://", "https://"]):
                # Muchas veces las imágenes llegan en líneas separadas
                if line not in metadata.get("url_anuncio", ""):
                    metadata.setdefault("imagenes", []).extend(url_pattern.findall(line))

        metadata["titulo"] = lines[0] if lines else ""
        descripcion = []
        for line in lines[1:]:
            if line == metadata.get("url_anuncio"):
                continue
            if url_pattern.search(line):
                continue
            descripcion.append(line)
        metadata["descripcion"] = " ".join(descripcion)

        direccion = self._infer_address_from_text(metadata)
        metadata["direccion"] = direccion

        return metadata

    def _infer_address_from_text(self, metadata: Dict[str, str]) -> str:
        """Intenta deducir una dirección aproximada desde el texto."""

        title = metadata.get("titulo", "")
        descripcion = metadata.get("descripcion", "")
        raw_address = ""

        address_keywords = [
            r"calle [^,\.]+", r"avenida [^,\.]+", r"barrio [^,\.]+", r"zona [^,\.]+",
            r"municipio [^,\.]+", r"\b[a-záéíóúñ\s]+\s*\(.*?\)"
        ]
        for pattern in address_keywords:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if match:
                raw_address = match.group(0)
                break
        if not raw_address:
            for pattern in address_keywords:
                match = re.search(pattern, descripcion, flags=re.IGNORECASE)
                if match:
                    raw_address = match.group(0)
                    break

        normalized = self.address_normalizer.normalize(raw_address.strip())
        return normalized or raw_address.strip()

    def _build_record(self, metadata: Dict[str, str]) -> PropertyRecord:
        """Genera un dataclass PropertyRecord a partir de un diccionario intermedio."""

        precio_total = self._parse_float(metadata.get("precio_total"))
        precio_m2 = self._parse_float(metadata.get("precio_m2"))
        superficie = self._parse_float(metadata.get("superficie_m2"))
        habitaciones = self._parse_int(metadata.get("habitaciones"))

        record = PropertyRecord(
            id_interno=str(uuid.uuid4()),
            titulo=metadata.get("titulo", ""),
            direccion_detectada=metadata.get("direccion", ""),
            url_anuncio=metadata.get("url_anuncio", ""),
            precio_total=precio_total,
            precio_m2=precio_m2,
            superficie_m2=superficie,
            habitaciones=habitaciones,
            descripcion_limpia=metadata.get("descripcion", ""),
            tipo_vivienda=self._classify_property_type(metadata.get("titulo", ""), metadata.get("descripcion", "")),
            imagenes=metadata.get("imagenes", []),
        )
        record.estado_general = self._infer_condition(metadata.get("descripcion", ""))
        return record

    def _classify_property_type(self, title: str, description: str) -> str:
        """Clasifica el tipo de vivienda usando palabras clave."""

        text = f"{title} {description}".lower()
        keywords = {
            "chalet": ["chalet", "adosado", "pareado"],
            "ático": ["ático"],
            "finca": ["finca", "rustica"],
            "dúplex": ["dúplex", "duplex"],
            "piso": ["piso", "apartamento", "vivienda"],
            "estudio": ["estudio"],
        }
        for tipo, palabras in keywords.items():
            if any(palabra in text for palabra in palabras):
                return tipo
        return ""

    def _infer_condition(self, description: str) -> str:
        """Determina el estado general según la descripción."""

        mapping = {
            "reformado": ["reformado", "rehabilitado", "actualizado"],
            "necesita reforma": ["reformar", "rehabilitar", "para reformar"],
            "obra nueva": ["obra nueva", "a estrenar"],
            "buen estado": ["buen estado", "listo para entrar", "excelente"],
        }
        lower_desc = unidecode(description.lower())
        for estado, keywords in mapping.items():
            if any(keyword in lower_desc for keyword in keywords):
                return estado
        return ""

    def _infer_location(self, record: PropertyRecord) -> PropertyRecord:
        """Calcula latitud y longitud basándose en la dirección disponible."""

        if not record.direccion_detectada:
            record.nivel_precision_ubicacion = "baja"
            record.ubicacion_inferida = "No se detectó dirección en el texto original."
            record.requiere_revision = True
            record.motivos_revision.append("Sin dirección detectada")
            return record

        normalized_address = self._normalize_address(record.direccion_detectada)
        lat_lon, fuente = self._geocode_with_fallbacks(normalized_address, record)

        if lat_lon is not None:
            record.latitud, record.longitud = lat_lon
            record.fuente_geolocalizacion = fuente
            record.nivel_precision_ubicacion = self.address_normalizer.detect_precision_hint(normalized_address)
            record.ubicacion_inferida = self._describe_location_inference(normalized_address)
            if not self._coords_look_confident(record):
                record.requiere_revision = True
                record.motivos_revision.append("Coordenadas requieren validación manual")
        else:
            record.nivel_precision_ubicacion = "baja"
            record.ubicacion_inferida = (
                "No se pudo geocodificar la dirección automáticamente. Revisar manualmente."
            )
            record.requiere_revision = True
            record.motivos_revision.append("Geocodificación sin resultado")
        return record

    def _normalize_address(self, detected: str) -> str:
        cleaned = self.address_normalizer.normalize(detected)
        return cleaned or detected

    def _geocode_with_fallbacks(
        self, address: str, record: PropertyRecord
    ) -> Tuple[Optional[Tuple[float, float]], str]:
        strategies: List[Tuple[str, Callable[[str], Optional[Tuple[float, float]]]]] = []
        strategies.extend(("Google Maps", lambda addr, client=client: self._geocode_google(client, addr)) for client in self.google_clients)
        strategies.extend(("Bing Maps", lambda addr, geocoder=geocoder: self._geocode_geopy(geocoder, addr)) for geocoder in self.bing_geocoders)
        if Nominatim is not None:
            strategies.append(("OpenStreetMap", self._geocode_nominatim))
        if osmnx is not None:
            strategies.append(("OSMnx", self._geocode_osmnx))
        if self.catastro_base_url:
            strategies.append(("Catastro", self._geocode_catastro))

        for source, strategy in strategies:
            try:
                result = strategy(address)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Fallo en geocodificador %s para %s: %s", source, record.id_interno, exc)
                continue
            if result:
                LOGGER.info("Dirección %s resuelta con %s", address, source)
                return result, source
        return None, ""

    def _geocode_google(self, client: "googlemaps.Client", address: str) -> Optional[Tuple[float, float]]:
        geocode_result = client.geocode(address)
        if not geocode_result:
            return None
        location = geocode_result[0]["geometry"]["location"]
        return (location["lat"], location["lng"])

    def _geocode_geopy(self, geocoder: "geopy.geocoders.base.Geocoder", address: str) -> Optional[Tuple[float, float]]:
        if geocoder is None:
            return None
        location = geocoder.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None

    def _geocode_nominatim(self, address: str) -> Optional[Tuple[float, float]]:
        if Nominatim is None:
            return None
        geolocator = Nominatim(user_agent=self.geopy_user_agent, timeout=10)
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None

    def _geocode_osmnx(self, address: str) -> Optional[Tuple[float, float]]:
        try:
            geocode = osmnx.geocoder.geocode(address)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            geocode = None
        if geocode:
            if isinstance(geocode, tuple):
                return (geocode[0], geocode[1])
            if hasattr(geocode, "y") and hasattr(geocode, "x"):
                return (geocode.y, geocode.x)
        return None

    def _geocode_catastro(self, address: str) -> Optional[Tuple[float, float]]:
        if not self.catastro_base_url:
            return None
        params = {"q": address}
        if self.catastro_token:
            params["token"] = self.catastro_token
        try:
            response = self.http_session.get(self.catastro_base_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return None
        data = response.json()
        coords = data.get("coordinates") if isinstance(data, dict) else None
        if coords and "lat" in coords and "lon" in coords:
            return (float(coords["lat"]), float(coords["lon"]))
        return None

    def _assess_precision(self, address: str) -> str:
        """Evalúa el nivel de precisión en función del detalle de la dirección."""

        address_lower = address.lower()
        if re.search(r"\d", address_lower):
            return "alta"
        if any(keyword in address_lower for keyword in ["calle", "avenida", "plaza"]):
            return "media"
        if any(keyword in address_lower for keyword in ["barrio", "zona", "municipio"]):
            return "media"
        return "baja"

    def _describe_location_inference(self, address: str) -> str:
        """Genera una explicación textual de la inferencia realizada."""

        if re.search(r"\d", address):
            return "Dirección con número, se tomó el punto exacto proporcionado por el geocodificador."
        if re.search(r"calle|avenida|plaza", address, flags=re.IGNORECASE):
            return "Solo se disponía de nombre de vía, se posicionó en el centro aproximado de la calle."
        if re.search(r"barrio|zona", address, flags=re.IGNORECASE):
            return "Referencia a barrio o zona, se estimó el centro geográfico del área."
        return "Se utilizó el centro del municipio como aproximación."

    def _coords_look_confident(self, record: PropertyRecord) -> bool:
        if record.latitud is None or record.longitud is None:
            return False
        if not (-90 <= record.latitud <= 90) or not (-180 <= record.longitud <= 180):
            record.motivos_revision.append("Coordenadas fuera de rango WGS84")
            return False
        if abs(record.latitud) < 0.001 and abs(record.longitud) < 0.001:
            record.motivos_revision.append("Coordenadas cercanas a origen (0,0)")
            return False
        if record.nivel_precision_ubicacion == "baja":
            return False
        return True

    def _parse_float(self, raw_value: Optional[str]) -> Optional[float]:
        if not raw_value:
            return None
        sanitized = raw_value.replace("€", "").replace(".", "").replace(",", ".")
        sanitized = re.sub(r"[^0-9\.]+", "", sanitized)
        return float(sanitized) if sanitized else None

    def _parse_int(self, raw_value: Optional[str]) -> Optional[int]:
        if not raw_value:
            return None
        digits = re.sub(r"[^0-9]+", "", raw_value)
        return int(digits) if digits else None


def export_dataframe_to_file(df: pd.DataFrame, output_path: str) -> None:
    """Función auxiliar para exportar un DataFrame a CSV o Excel según extensión."""

    extension = output_path.split(".")[-1].lower()
    if extension == "csv":
        df.to_csv(output_path, index=False)
    elif extension in {"xlsx", "xls"}:
        df.to_excel(output_path, index=False)
    else:
        raise ValueError("Extensión no soportada: %s" % extension)
    LOGGER.info("Datos exportados a %s", output_path)
