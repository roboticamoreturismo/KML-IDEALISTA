"""Implementación del Paso 2: enriquecimiento inteligente del anuncio."""

from __future__ import annotations

import importlib
import io
import logging
import re
from statistics import mean
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
from unidecode import unidecode

from .data_models import PropertyRecord
from .llm_clients import LLMClient, build_llm_from_selection

LOGGER = logging.getLogger(__name__)

_bs4_spec = importlib.util.find_spec("bs4")
if _bs4_spec is not None:
    from bs4 import BeautifulSoup
else:
    BeautifulSoup = None  # type: ignore

_pillow_spec = importlib.util.find_spec("PIL")
if _pillow_spec is not None:
    from PIL import Image
    from PIL import ImageStat
else:
    Image = None  # type: ignore
    ImageStat = None  # type: ignore


class PropertyEnricher:
    """Amplía la información disponible de una propiedad."""

    def __init__(
        self,
        language_model_provider: str = "openai",
        language_model_name: str = "gpt-4o-mini",
        language_model_api_key: Optional[str] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.llm_client = llm_client or build_llm_from_selection(
            language_model_provider, language_model_name, language_model_api_key
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            }
        )

    def enrich(self, records: Iterable[PropertyRecord]) -> List[PropertyRecord]:
        enriched_records: List[PropertyRecord] = []
        for record in records:
            enriched_records.append(self.enrich_property(record))
        return enriched_records

    def enrich_property(self, record: PropertyRecord) -> PropertyRecord:
        page_content = self._fetch_listing_page(record.url_anuncio)
        if page_content:
            self._parse_listing_page(record, page_content)
        self._enhance_from_description(record)
        self._analyse_images(record)
        self._llm_enrichment(record)
        return record

    def _fetch_listing_page(self, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            response = self.session.get(url, timeout=15)
        except requests.RequestException as exc:  # noqa: PERF203 - queremos registrar cualquier fallo
            LOGGER.warning("No se pudo acceder a %s: %s", url, exc)
            return None
        if response.status_code != 200:
            LOGGER.warning("Respuesta inesperada (%s) al acceder a %s", response.status_code, url)
            return None
        return response.text

    def _parse_listing_page(self, record: PropertyRecord, page_content: str) -> None:
        if BeautifulSoup is None:
            LOGGER.debug("BeautifulSoup no está disponible, se omite el scraping del anuncio.")
            return

        soup = BeautifulSoup(page_content, "html.parser")
        agency = soup.select_one("[data-testid='agency-name'], .about-advertiser-name")
        if agency and not record.agencia:
            record.agencia = agency.get_text(strip=True)

        phone = soup.find(string=re.compile(r"\+?\d[\d\s]{6,}"))
        if phone and not record.telefono:
            record.telefono = re.sub(r"\s+", "", phone)

        date_tag = soup.select_one("[data-testid='publication-date'], time[itemprop='datePublished']")
        if date_tag and not record.fecha_publicacion:
            record.fecha_publicacion = date_tag.get_text(strip=True)

        tags = [tag.get_text(strip=True) for tag in soup.select(".listing-tags span, .tag-text")]
        if tags:
            record.caracteristicas_extra.setdefault("etiquetas", ", ".join(tags))

        legal_status = soup.find(string=re.compile(r"ocupad|rentabilidad|alquilad", re.IGNORECASE))
        if legal_status:
            record.caracteristicas_extra.setdefault("estado_legal", legal_status.strip())

        id_match = re.search(r"/inmueble/(\d+)/", record.url_anuncio)
        if id_match:
            record.caracteristicas_extra.setdefault("id_anuncio", id_match.group(1))

    def _enhance_from_description(self, record: PropertyRecord) -> None:
        description = record.descripcion_limpia
        if not description:
            return

        normalized = unidecode(description.lower())
        feature_keywords = {
            "orientacion": ["orientacion", "orientado"],
            "reformas": ["reforma", "reformado", "actualizado"],
            "luminosidad": ["luminoso", "luz natural"],
            "vistas": ["vistas", "panoramica", "mar"],
            "exterior": ["exterior", "terraza", "balcon", "jardin"],
            "distribucion": ["distribucion", "planta", "habitaciones"],
        }
        extracted: Dict[str, List[str]] = {}
        for label, keywords in feature_keywords.items():
            phrases = [sentence.strip() for sentence in re.split(r"[\.;]", description) if sentence.strip()]
            matches = [phrase for phrase in phrases if any(keyword in unidecode(phrase.lower()) for keyword in keywords)]
            if matches:
                extracted[label] = matches
        if extracted:
            for key, values in extracted.items():
                record.caracteristicas_extra[key] = " | ".join(values)

        orientation = self._detect_orientation(normalized)
        if orientation and not record.caracteristicas_extra.get("orientacion_principal"):
            record.caracteristicas_extra["orientacion_principal"] = orientation

        entorno = self._detect_environment_hints(normalized)
        if entorno:
            record.caracteristicas_extra["entorno_textual"] = "; ".join(entorno)

        if not record.estado_general:
            record.estado_general = self._detect_condition(normalized)

    def _llm_enrichment(self, record: PropertyRecord) -> None:
        if not self.llm_client or not self.llm_client.is_ready():
            return
        prompt = (
            "Eres un asistente inmobiliario. Resume en viñetas breves las "
            "características diferenciales del siguiente anuncio.\n"
            "Descripción:\n"
            f"{record.descripcion_limpia}\n"
            "Devuelve 3 viñetas concisas en español."
        )
        summary = self.llm_client.complete(prompt)
        if summary:
            record.caracteristicas_extra["resumen_llm"] = summary

    def _analyse_images(self, record: PropertyRecord) -> None:
        if not record.imagenes:
            return
        classifications: Dict[str, str] = {}
        luminosities: List[float] = []
        for image_url in record.imagenes:
            room_type = self._classify_image_by_name(image_url)
            if room_type:
                classifications[image_url] = room_type
            brightness = self._estimate_brightness(image_url)
            if brightness is not None:
                luminosities.append(brightness)
        if classifications:
            record.clasificacion_imagenes.update(classifications)
        if luminosities:
            record.luminosidad_media = round(mean(luminosities), 2)
            record.entorno_visual = self._classify_environment_from_images(luminosities)

    def _classify_image_by_name(self, image_url: str) -> str:
        lowered = image_url.lower()
        mappings = {
            "cocina": ["kitchen", "cocina"],
            "baño": ["bath", "ban"],
            "salón": ["living", "salon"],
            "dormitorio": ["bed", "dorm"],
            "fachada": ["facade", "exterior", "front"],
            "plano": ["plan", "plano"],
        }
        for label, keywords in mappings.items():
            if any(keyword in lowered for keyword in keywords):
                return label
        return ""

    def _estimate_brightness(self, image_url: str) -> Optional[float]:
        if Image is None or ImageStat is None:
            return None
        try:
            response = self.session.get(image_url, timeout=10)
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None
        try:
            with Image.open(io.BytesIO(response.content)) as img:  # type: ignore[name-defined]
                grayscale = img.convert("L")
                stat = ImageStat.Stat(grayscale)
                return stat.mean[0] / 255 * 100
        except Exception:  # noqa: BLE001 - la librería PIL puede lanzar múltiples excepciones
            return None

    def _classify_environment_from_images(self, luminosities: List[float]) -> str:
        avg = mean(luminosities)
        if avg > 70:
            return "luminoso"
        if avg > 40:
            return "intermedio"
        return "oscuro"

    def _detect_orientation(self, normalized_description: str) -> str:
        orientations = {
            "norte": ["norte"],
            "sur": ["sur"],
            "este": ["este"],
            "oeste": ["oeste"],
        }
        detected = [name for name, keywords in orientations.items() if any(keyword in normalized_description for keyword in keywords)]
        return ", ".join(sorted(set(detected)))

    def _detect_environment_hints(self, normalized_description: str) -> List[str]:
        hints = []
        patterns = [
            (r"cerca de [a-záéíóúñ\s]+", "proximidad"),
            (r"a \d+ min", "tiempo desplazamiento"),
            (r"zona [a-záéíóúñ\s]+", "zona"),
            (r"junto a [a-záéíóúñ\s]+", "referencia"),
        ]
        for pattern, label in patterns:
            matches = re.findall(pattern, normalized_description)
            if matches:
                hints.extend(f"{label}: {match}" for match in matches)
        return hints

    def _detect_condition(self, normalized_description: str) -> str:
        if any(keyword in normalized_description for keyword in ["reformado", "actualizado", "rehabilitado"]):
            return "reformado"
        if "para reformar" in normalized_description or "reforma integral" in normalized_description:
            return "necesita reforma"
        if any(keyword in normalized_description for keyword in ["a estrenar", "obra nueva"]):
            return "obra nueva"
        if any(keyword in normalized_description for keyword in ["lista para entrar", "excelente", "inmejorable"]):
            return "buen estado"
        return ""


def records_to_dataframe(records: Iterable[PropertyRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.__dict__ for record in records])
