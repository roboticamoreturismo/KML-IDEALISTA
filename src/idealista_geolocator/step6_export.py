"""Implementación del Paso 6: exportación a KML y Excel."""

from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from .data_models import PropertyRecord

LOGGER = logging.getLogger(__name__)


_simplekml_spec = importlib.util.find_spec("simplekml")
if _simplekml_spec is not None:
    simplekml = __import__("simplekml")
else:
    simplekml = None  # type: ignore


class Exporter:
    """Genera archivos KML y Excel listos para entregar al cliente."""

    def __init__(self, output_root: str = "clientes") -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def export(self, records: Iterable[PropertyRecord], client_description: str) -> Path:
        today = datetime.utcnow().strftime("%y%m%d")
        safe_description = "_".join(client_description.lower().split())[:40]
        folder = self.output_root / f"{today}_{safe_description}"
        folder.mkdir(parents=True, exist_ok=True)

        records_list = list(records)
        df = pd.DataFrame([record.__dict__ for record in records_list])
        excel_path = folder / f"{today}_{safe_description}.xlsx"
        df.to_excel(excel_path, index=False)
        LOGGER.info("Excel generado en %s", excel_path)

        if simplekml is not None:
            kml_path = self._create_kml(records_list, folder, today, safe_description)
        else:
            LOGGER.warning("simplekml no está instalado; se omite la exportación KML.")
            kml_path = None

        resumen_path = folder / "resumen.json"
        with resumen_path.open("w", encoding="utf-8") as handler:
            json.dump([record.__dict__ for record in records_list], handler, ensure_ascii=False, indent=2)

        LOGGER.info("Resumen JSON generado en %s", resumen_path)
        return excel_path if kml_path is None else kml_path

    def _create_kml(self, records: List[PropertyRecord], folder: Path, date_prefix: str, description: str) -> Path:
        kml = simplekml.Kml()
        for record in records:
            if record.latitud is None or record.longitud is None:
                continue
            marker = kml.newpoint()
            marker.name = f"Afinidad {record.afinidad or '-'}"
            marker.coords = [(record.longitud, record.latitud)]
            marker.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"
            marker.style.iconstyle.color = self._color_from_price(record.precio_total)
            marker.description = self._build_marker_description(record)
        kml_path = folder / f"{date_prefix}_{description}.kml"
        kml.save(str(kml_path))
        LOGGER.info("KML generado en %s", kml_path)
        return kml_path

    def _build_marker_description(self, record: PropertyRecord) -> str:
        parts = [
            f"<h3>{record.titulo}</h3>",
            f"<p><strong>Precio:</strong> {record.precio_total or 'N/D'} €</p>",
            f"<p><strong>€/m²:</strong> {record.precio_m2 or 'N/D'}</p>",
            f"<p><strong>Superficie:</strong> {record.superficie_m2 or 'N/D'} m²</p>",
            f"<p><strong>Habitaciones:</strong> {record.habitaciones or 'N/D'}</p>",
            f"<p><strong>Estado:</strong> {record.estado_general or 'N/D'}</p>",
            f"<p><strong>Afinidad:</strong> {record.afinidad_porcentaje or 'N/D'}%</p>",
        ]
        if record.justificacion_afinidad:
            parts.append(f"<p>{record.justificacion_afinidad}</p>")
        if record.propuestas_mejora:
            parts.append("<ul>" + "".join(f"<li>{proposal}</li>" for proposal in record.propuestas_mejora) + "</ul>")
        if record.url_anuncio:
            parts.append(f"<p><a href='{record.url_anuncio}'>Ver anuncio</a></p>")
        if record.imagenes:
            parts.append(f"<img src='{record.imagenes[0]}' width='200' />")
        return "".join(parts)

    def _color_from_price(self, price: Optional[float]) -> str:
        if price is None:
            return "ff00ff00"  # Verde por defecto
        if price < 150000:
            return "ff66ff66"
        if price < 300000:
            return "ff009900"
        return "ff006600"
