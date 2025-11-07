"""Orquestador principal de la automatización."""
from __future__ import annotations

from typing import Dict

import pandas as pd

from .client_parser import parse_client_profile
from .data_models import ClientProfile
from .exporters import generar_excel, generar_kml, generar_mapa_html
from .matching import generar_tabla_matching
from .property_transformer import transformar_registros


class IdealistaAutomation:
    """Coordina el procesamiento de datos de Idealista y clientes."""

    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = output_dir

    def procesar(self, propiedades_df: pd.DataFrame, cliente_nombre: str, cliente_texto: str) -> Dict[str, str]:
        """Ejecuta todo el flujo y devuelve rutas a los artefactos generados."""
        propiedades = transformar_registros(propiedades_df)
        cliente = parse_client_profile(cliente_nombre, cliente_texto)
        matching = generar_tabla_matching(propiedades, cliente)

        excel_path = generar_excel(propiedades, matching, cliente, self.output_dir)
        kml_path = generar_kml(propiedades, self.output_dir)
        mapa_path = generar_mapa_html(propiedades, self.output_dir)

        return {
            "excel": excel_path,
            "kml": kml_path,
            "mapa": mapa_path,
            "cliente": cliente.__dict__,
            "matching_registros": matching.to_dict(orient="records"),
        }

    def resumen_cliente(self, cliente: ClientProfile) -> Dict[str, str]:
        return cliente.__dict__
